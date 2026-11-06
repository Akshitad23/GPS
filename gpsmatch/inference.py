"""Log-space inference for a variable-width candidate lattice."""
import numpy as np
from scipy.special import logsumexp


class NoPathError(ValueError):
    pass


def infer(log_initial, log_emissions, log_transitions):
    if not log_emissions or len(log_transitions) != len(log_emissions)-1:
        raise ValueError("Invalid lattice length")
    widths = [len(x) for x in log_emissions]
    if any(k == 0 for k in widths) or len(log_initial) != widths[0]:
        raise NoPathError("Empty candidate set")
    for t, matrix in enumerate(log_transitions):
        if matrix.shape != (widths[t], widths[t+1]):
            raise ValueError("Transition shape mismatch")
    for item in [log_initial, *log_emissions, *log_transitions]:
        if np.any(np.isnan(item)) or np.any(np.isposinf(item)):
            raise ValueError("Scores contain NaN or positive infinity")
    forward = [log_initial + log_emissions[0]]
    delta = forward[0].copy()
    backpointers = []
    for t, matrix in enumerate(log_transitions, 1):
        scores = delta[:, None] + matrix
        backpointers.append(np.argmax(scores, axis=0))
        delta = log_emissions[t] + np.max(scores, axis=0)
        forward.append(log_emissions[t] + logsumexp(forward[-1][:, None]+matrix, axis=0))
    evidence = float(logsumexp(forward[-1]))
    if not np.isfinite(evidence):
        raise NoPathError("No feasible complete path")
    path = [int(np.argmax(delta))]
    best_score = float(np.max(delta))
    for pointer in reversed(backpointers):
        path.append(int(pointer[path[-1]]))
    path.reverse()
    backward = [None]*len(widths)
    backward[-1] = np.zeros(widths[-1])
    for t in range(len(widths)-2, -1, -1):
        backward[t] = logsumexp(log_transitions[t] + log_emissions[t+1][None, :]
                               + backward[t+1][None, :], axis=1)
    posterior = []
    for alpha, beta in zip(forward, backward):
        values = alpha + beta
        posterior.append(np.exp(values-logsumexp(values)))
    return {"path": path, "posterior": posterior, "log_evidence": evidence,
            "log_best_score": best_score}
