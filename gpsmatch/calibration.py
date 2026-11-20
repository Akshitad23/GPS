"""Small post-hoc confidence calibration maps (Person 2).

Both maps transform the matcher's aggregated physical-segment confidence into a
new probability that the selected segment is correct. They never change the
selected segment. Fit them on calibration journeys only; unmatched rows (null
confidence) must be excluded by the caller and that exclusion reported.

* PlattCalibrator: sigmoid(a * logit(p) + b), two parameters. With a > 0 it is
  strictly increasing, so it preserves the ranking and the risk-coverage curve.
* IsotonicCalibrator: pool-adjacent-violators step function. It is
  nondecreasing but may merge distinct scores into ties, which can change a
  risk-coverage curve slightly (tie effects only, never a reordering).
"""
import numpy as np
from scipy.optimize import minimize
from scipy.special import expit, logit

EPS = 1e-6


def _logit(p):
    return logit(np.clip(np.asarray(p, dtype=float), EPS, 1-EPS))


class PlattCalibrator:
    kind = "platt"

    def __init__(self, a=1., b=0.):
        self.a, self.b = float(a), float(b)

    def fit(self, probabilities, correct):
        x = _logit(probabilities)
        y = np.asarray(correct, dtype=float)
        if len(x) == 0:
            raise ValueError("Cannot fit a calibrator on zero matched rows")

        def loss(theta):
            z = theta[0]*x+theta[1]
            # log(1+exp(z)) - y z, numerically stable.
            value = np.mean(np.logaddexp(0., z)-y*z)
            q = expit(z)
            grad = np.array([np.mean((q-y)*x), np.mean(q-y)])
            return value, grad

        result = minimize(loss, np.array([1., 0.]), jac=True, method="L-BFGS-B")
        self.a, self.b = map(float, result.x)
        self.fit_info = {"converged": bool(result.success), "train_log_loss": float(result.fun),
                         "train_population": int(len(x))}
        return self

    def predict(self, probabilities):
        return expit(self.a*_logit(probabilities)+self.b)

    def to_dict(self):
        return {"kind": self.kind, "a": self.a, "b": self.b, **getattr(self, "fit_info", {})}


class IsotonicCalibrator:
    kind = "isotonic"

    def __init__(self, thresholds=(), values=()):
        self.thresholds = np.asarray(thresholds, dtype=float)
        self.values = np.asarray(values, dtype=float)

    def fit(self, probabilities, correct):
        p = np.asarray(probabilities, dtype=float)
        y = np.asarray(correct, dtype=float)
        if len(p) == 0:
            raise ValueError("Cannot fit a calibrator on zero matched rows")
        order = np.argsort(p, kind="stable")
        p, y = p[order], y[order]
        unique, start = np.unique(p, return_index=True)
        sums = np.add.reduceat(y, start)
        counts = np.diff(np.r_[start, len(p)]).astype(float)
        # Pool adjacent violators over unique-x blocks.
        blocks = []  # [low_x, sum, count]
        for x, s, n in zip(unique, sums, counts):
            blocks.append([x, s, n])
            while len(blocks) > 1 and blocks[-2][1]/blocks[-2][2] >= blocks[-1][1]/blocks[-1][2]:
                x2, s2, n2 = blocks.pop()
                blocks[-1][1] += s2
                blocks[-1][2] += n2
        self.thresholds = np.array([b[0] for b in blocks])
        self.values = np.clip(np.array([b[1]/b[2] for b in blocks]), EPS, 1-EPS)
        self.fit_info = {"blocks": len(blocks), "train_population": int(len(p))}
        return self

    def predict(self, probabilities):
        p = np.asarray(probabilities, dtype=float)
        index = np.clip(np.searchsorted(self.thresholds, p, side="right")-1, 0, len(self.values)-1)
        return self.values[index]

    def to_dict(self):
        return {"kind": self.kind, "thresholds": self.thresholds.tolist(),
                "values": self.values.tolist(), **getattr(self, "fit_info", {})}


def from_dict(data):
    if data["kind"] == "platt":
        return PlattCalibrator(data["a"], data["b"])
    if data["kind"] == "isotonic":
        return IsotonicCalibrator(data["thresholds"], data["values"])
    raise ValueError(data["kind"])


CALIBRATORS = {"platt": PlattCalibrator, "isotonic": IsotonicCalibrator}
