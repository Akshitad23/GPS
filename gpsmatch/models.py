"""Alternative HMM-style candidate lattices; baseline remains in pipeline.py.

All motion estimates use GPS observations only. Bias hypotheses correct coordinates
BEFORE candidate projection. No true path, simulated speed or burst label is read.
"""
import numpy as np
from scipy.special import logsumexp
from .inference import infer, NoPathError


def motion_estimates(times, observations):
    """Robust multi-lag displacement estimates, in metres/second.

    Long-lag differences reduce independent jitter. Local medians preserve turns
    approximately, but can still be corrupted by a burst boundary or a long gap.
    """
    n = len(times)
    velocities = np.zeros((n, 2))
    for t in range(n):
        samples = []
        for lag in (3, 4, 5):
            for start in range(max(0, t-lag), min(t+1, n-lag)):
                end = start+lag
                samples.append((observations[end]-observations[start])/(times[end]-times[start]))
        if not samples:
            for start in range(max(0,t-1), min(n-1,t+1)):
                samples.append((observations[start+1]-observations[start])/(times[start+1]-times[start]))
        if samples:
            velocities[t] = np.median(samples, axis=0)
    speeds = np.linalg.norm(velocities, axis=1)
    return velocities, speeds


def distance_matrix(roads, previous, current):
    """Vectorised exact shortest legal distances between position candidates."""
    a, b = previous, current
    ai = np.array([c.offset for c in a])
    bj = np.array([c.offset for c in b])
    al = np.array([roads.length(c.edge) for c in a])
    bl = np.array([roads.length(c.edge) for c in b])
    reverse = {e.id: any(r.segment == e.segment and r.u == e.v and r.v == e.u
                        for r in roads.edges.values()) for e in roads.edges.values()}
    node_list = list(roads.nodes)
    node_index = {node:i for i,node in enumerate(node_list)}
    node_distances = np.array([[roads.shortest(u,v) for v in node_list] for u in node_list])
    result = np.full((len(a),len(b)), np.inf)
    for exit_start in (False,True):
        for entry_end in (False,True):
            nodes_a = [c.edge.u if exit_start else c.edge.v for c in a]
            nodes_b = [c.edge.v if entry_end else c.edge.u for c in b]
            first = ai if exit_start else al-ai
            last = bl-bj if entry_end else bj
            valid_a = np.array([not exit_start or reverse[c.edge.id] for c in a])
            valid_b = np.array([not entry_end or reverse[c.edge.id] for c in b])
            middle = node_distances[np.array([node_index[u] for u in nodes_a])[:,None],
                                    np.array([node_index[v] for v in nodes_b])[None,:]]
            values = first[:,None]+middle+last[None,:]
            values[~valid_a,:] = np.inf
            values[:,~valid_b] = np.inf
            result = np.minimum(result,values)
    same = np.array([[x.edge.segment == y.edge.segment for y in b] for x in a])
    aligned = np.array([[x.edge.u == y.edge.u for y in b] for x in a])
    delta = np.where(aligned,bj[None,:],bl[None,:]-bj[None,:])-ai[:,None]
    feasible = same & ((delta >= 0) | np.array([reverse[c.edge.id] for c in a])[:,None])
    result = np.minimum(result,np.where(feasible,np.abs(delta),np.inf))
    return result


def normalise_rows(scores):
    normalizer = logsumexp(scores,axis=1)
    finite = np.isfinite(normalizer)
    result = scores.copy()
    result[finite] -= normalizer[finite,None]
    return result


def emission_scores(residuals, sigma, kind="gaussian", df=4.):
    squared = (np.asarray(residuals)/sigma)**2
    if kind == "student":
        # Two-dimensional isotropic Student-t kernel; shared constants cancel.
        return -.5*(df+2.)*np.log1p(squared/df)
    return -.5*squared


def alternative_match(roads, times, observations, config):
    """Motion/robust/bias variants with a common motion compatibility term."""
    times, observations = np.asarray(times), np.asarray(observations)
    if len(times)==0 or observations.shape != (len(times),2):
        raise ValueError("Expected nonempty observations shaped (T, 2)")
    if not np.all(np.isfinite(observations)) or not np.all(np.isfinite(times)):
        raise ValueError("Nonfinite input")
    if np.any(np.diff(times)<=0):
        raise ValueError("Timestamps must increase")
    bias_model = config.model == "bias"
    biases = (np.array([(x,y) for x in config.bias_levels for y in config.bias_levels],dtype=float)
              if bias_model else np.zeros((1,2)))
    log_prior = -np.sum(biases**2,axis=1)/(2*config.bias_prior_sigma**2)
    log_prior -= logsumexp(log_prior)
    prior = np.exp(log_prior)
    # Persistence plus occasional prior-distributed jumps; dt-aware.
    candidates, bias_indices, emissions = [], [], []
    for point in observations:
        row, indices = [], []
        for bi,bias in enumerate(biases):
            found = roads.candidates(point-bias,config.candidate_radius)
            row.extend(found)
            indices.extend([bi]*len(found))
        if not row:
            raise NoPathError("At least one observation has no candidates")
        candidates.append(row)
        bias_indices.append(np.array(indices,dtype=int))
        emissions.append(emission_scores([c.residual for c in row],config.assumed_sigma,
                                        "student" if config.model=="robust" else "gaussian",
                                        config.student_df))
    velocities, speeds = motion_estimates(times,observations)
    transitions = []
    for t in range(1,len(times)):
        dt = times[t]-times[t-1]
        a,b = candidates[t-1],candidates[t]
        distances = distance_matrix(roads,a,b)
        target = .5*(speeds[t-1]+speeds[t])*dt
        # A time-scaled uncertainty allows gaps; projection allowance remains explicit.
        scale = config.motion_scale + config.speed_uncertainty*dt
        scores = -np.abs(distances-target)/scale
        bound = config.max_speed*dt+config.projection_slack_sigma*np.sqrt(2)*config.assumed_sigma
        scores[distances>bound+1e-9] = -np.inf
        # Angle-free displacement consistency: observed long-lag velocity supplies
        # direction; it cannot discriminate same-direction parallel roads.
        direction = .5*(velocities[t-1]+velocities[t])
        displacement = np.array([c.point for c in b])[None,:,:]-np.array([c.point for c in a])[:,None,:]
        dn = np.linalg.norm(displacement,axis=2)
        vn = float(np.linalg.norm(direction))
        if vn > 2.:
            cosine = np.sum(displacement*direction,axis=2)/(np.maximum(dn,1e-12)*vn)
            scores -= config.heading_weight*(1.-np.clip(cosine,-1,1))*np.minimum(dn/5.,1.)
        if bias_model:
            # Normalize road transitions CONDITIONAL ON destination bias, then
            # multiply by a normalized bias transition. Candidate count cannot
            # reward a bias merely for producing more hypotheses.
            joint = np.full_like(scores,-np.inf)
            jump = 1.-(1.-config.bias_jump_probability)**dt
            bias_transition = (1.-jump)*np.eye(len(biases))+jump*prior[None,:]
            for bi in range(len(biases)):
                columns = np.flatnonzero(bias_indices[t]==bi)
                if len(columns):
                    conditional = normalise_rows(scores[:,columns])
                    joint[:,columns] = conditional+np.log(bias_transition[bias_indices[t-1],bi])[:,None]
            # Recondition on biases having feasible outgoing road transitions.
            scores = normalise_rows(joint)
        else:
            scores = normalise_rows(scores)
        transitions.append(scores)
    initial_prior = -np.sum(biases**2,axis=1)/(2*config.initial_bias_sigma**2)
    initial_prior -= logsumexp(initial_prior)
    initial = np.array([initial_prior[bi]-np.log(np.count_nonzero(bias_indices[0]==bi))
                        for bi in bias_indices[0]])
    initial -= logsumexp(initial)
    output = infer(initial,emissions,transitions)
    output.update(candidates=candidates,transitions=transitions,
                  log_initial=initial,log_emissions=emissions,
                  state_biases=[biases[indices] for indices in bias_indices])
    return output
