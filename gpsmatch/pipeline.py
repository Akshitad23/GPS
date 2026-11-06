"""Public API. Ground truth is used only after matching for evaluation."""
from dataclasses import dataclass, asdict
from time import perf_counter
import math
import hashlib
import json
import numpy as np
from scipy.special import logsumexp
from .roads import synthetic_map
from .simulation import journey, corrupt
from .inference import infer, NoPathError


@dataclass(frozen=True)
class Config:
    noise_kind: str = "independent"
    noise_sigma: float = 8.
    assumed_sigma: float = 8.
    transition_beta: float = 15.
    candidate_radius: float = 60.
    max_speed: float = 35.
    projection_slack_sigma: float = 3.
    road_separation: float = 20.
    sample_interval: float = 1.
    speed: float = 8.
    burst_offset: float = 20.
    burst_points: int = 10
    gap_points: int = 6
    route_variant: int = 0

    model: str = "baseline"
    motion_scale: float = 10.
    speed_uncertainty: float = 2.
    heading_weight: float = .5
    student_df: float = 4.
    bias_levels: tuple = (-30., -15., 0., 15., 30.)
    bias_prior_sigma: float = 20.
    initial_bias_sigma: float = 5.
    bias_jump_probability: float = .04
    burst_angle_degrees: float = 90.
    burst_start_fraction: float = .5

    def validate(self):
        if self.model not in ("baseline","motion","robust","bias"):
            raise ValueError("Unknown model")
        for key in ("motion_scale","student_df","bias_prior_sigma","initial_bias_sigma"):
            if not math.isfinite(getattr(self,key)) or getattr(self,key)<=0:
                raise ValueError(f"{key} must be positive")
        for key in ("speed_uncertainty","heading_weight"):
            if not math.isfinite(getattr(self,key)) or getattr(self,key)<0:
                raise ValueError(f"{key} must be nonnegative")
        if not 0 < self.bias_jump_probability < 1:
            raise ValueError("bias_jump_probability must lie in (0,1)")
        if not self.bias_levels or 0. not in self.bias_levels or len(set(self.bias_levels)) != len(self.bias_levels):
            raise ValueError("bias_levels must be unique and include zero")
        if not all(math.isfinite(x) for x in self.bias_levels):
            raise ValueError("bias_levels must be finite")
        if not math.isfinite(self.burst_angle_degrees) or not 0<=self.burst_start_fraction<=1:
            raise ValueError("Invalid burst direction/start")
        positive = ("assumed_sigma", "transition_beta", "candidate_radius",
                    "max_speed", "road_separation", "sample_interval", "speed")
        for key in positive:
            value = getattr(self, key)
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"{key} must be finite and positive")
        if not math.isfinite(self.noise_sigma) or self.noise_sigma < 0:
            raise ValueError("noise_sigma must be finite and nonnegative")
        if not math.isfinite(self.projection_slack_sigma) or self.projection_slack_sigma < 0:
            raise ValueError("projection_slack_sigma must be finite and nonnegative")
        if not math.isfinite(self.burst_offset):
            raise ValueError("burst_offset must be finite")
        for key in ("burst_points", "gap_points", "route_variant"):
            if not isinstance(getattr(self, key), int) or getattr(self, key) < 0:
                raise ValueError(f"{key} must be a nonnegative integer")


def match(roads, times, observations, config):
    """Accept only observed coordinates/times and the map, never truth."""
    config.validate()
    if config.model != "baseline":
        from .models import alternative_match
        return alternative_match(roads,times,observations,config)
    times, observations = np.asarray(times), np.asarray(observations)
    if len(times) == 0 or observations.shape != (len(times), 2):
        raise ValueError("Expected nonempty observations shaped (T, 2)")
    if not np.all(np.isfinite(observations)) or not np.all(np.isfinite(times)):
        raise ValueError("Nonfinite input")
    if np.any(np.diff(times) <= 0):
        raise ValueError("Timestamps must increase")
    candidates = [roads.candidates(p, config.candidate_radius) for p in observations]
    if any(not c for c in candidates):
        raise NoPathError("At least one observation has no candidates")
    emissions = [np.array([-c.residual**2/(2*config.assumed_sigma**2) for c in row])
                 for row in candidates]
    transitions = []
    for t in range(1, len(times)):
        matrix = np.full((len(candidates[t-1]), len(candidates[t])), -np.inf)
        observed_distance = np.linalg.norm(observations[t]-observations[t-1])
        for i, a in enumerate(candidates[t-1]):
            for j, b in enumerate(candidates[t]):
                distance = roads.distance(a, b)
                if distance <= (config.max_speed*(times[t]-times[t-1])
                                + config.projection_slack_sigma*np.sqrt(2)*config.assumed_sigma + 1e-9):
                    matrix[i, j] = -abs(distance-observed_distance)/config.transition_beta
        norm = logsumexp(matrix, axis=1)
        reachable = np.isfinite(norm)
        matrix[reachable] -= norm[reachable, None]
        transitions.append(matrix)
    output = infer(np.full(len(candidates[0]), -np.log(len(candidates[0]))),
                   emissions, transitions)
    output["candidates"] = candidates
    output["transitions"] = transitions
    return output


def summarise(rows):
    n = len(rows)
    good = [r for r in rows if r["status"] == "matched"]
    nearest = [r for r in rows if r["nearest_segment"]]
    return {
        "points": n,
        "matched_fraction": len(good)/n if n else None,
        "hmm_accuracy": sum(r["correct"] for r in good)/n if n else None,
        "hmm_accuracy_given_match": np.mean([r["correct"] for r in good]).item() if good else None,
        "nearest_accuracy": sum(r["nearest_correct"] for r in nearest)/n if n else None,
        "candidate_recall": sum(r["true_segment_present"] for r in rows)/n if n else None,
        "brier_given_match": np.mean([(r["confidence"]-r["correct"])**2 for r in good]).item() if good else None,
    }


def run_pipeline(config=None, seed=42):
    config = config or Config()
    config.validate()
    started = perf_counter()
    roads = synthetic_map(config.road_separation)
    truth_rng, noise_rng = [np.random.default_rng(s) for s in np.random.SeedSequence(seed).spawn(2)]
    truth = journey(roads, truth_rng, config.sample_interval, config.speed, config.route_variant)
    obs = corrupt(truth, noise_rng, config.noise_kind, config.noise_sigma,
                  config.burst_offset, config.burst_points, config.gap_points,
                  config.burst_angle_degrees, config.burst_start_fraction)
    failure = None
    try:
        matched = match(roads, obs["time"], obs["xy"], config)
        candidate_sets = matched["candidates"]
    except NoPathError as error:
        matched, failure = None, str(error)
        candidate_sets = [roads.candidates(p, config.candidate_radius) for p in obs["xy"]]
    raw_candidates = [roads.candidates(p, config.candidate_radius) for p in obs["xy"]]
    rows = []
    config_id = hashlib.sha256(json.dumps(asdict(config), sort_keys=True).encode()).hexdigest()[:10]
    trajectory_id = f"{config.noise_kind}_r{config.route_variant}_seed{seed}_{config_id}"
    for t, candidates in enumerate(candidate_sets):
        nearest = min(raw_candidates[t], key=lambda c: c.residual).edge.segment if raw_candidates[t] else ""
        row = {
            "trajectory_id": trajectory_id, "timestamp": float(obs["time"][t]),
            "true_x": float(obs["truth_xy"][t, 0]), "true_y": float(obs["truth_xy"][t, 1]),
            "gps_x": float(obs["xy"][t, 0]), "gps_y": float(obs["xy"][t, 1]),
            "true_segment": str(obs["segment"][t]), "true_directed_edge": str(obs["edge"][t]),
            "burst": bool(obs["burst"][t]), "candidate_count": len({c.edge.segment for c in candidates}),
            "state_count": len(candidates),
            "true_segment_present": any(c.edge.segment == obs["segment"][t] for c in candidates),
            "nearest_segment": nearest, "nearest_correct": nearest == obs["segment"][t],
            "selected_segment": "", "selected_directed_edge": "",
            "confidence": None, "entropy": None, "correct": False,
            "selected_x": None, "selected_y": None, "bias_x": None, "bias_y": None,
            "status": "unmatched" if matched is None else "matched",
        }
        if matched:
            chosen = candidates[matched["path"][t]]
            probabilities = {}
            for c, prob in zip(candidates, matched["posterior"][t]):
                probabilities[c.edge.segment] = probabilities.get(c.edge.segment, 0.)+float(prob)
            values = np.array(list(probabilities.values()))
            entropy = -float(np.sum(values[values>0]*np.log(values[values>0])))
            row.update(selected_segment=chosen.edge.segment, selected_directed_edge=chosen.edge.id,
                       selected_x=float(chosen.point[0]), selected_y=float(chosen.point[1]),
                       bias_x=float(matched["state_biases"][t][matched["path"][t]][0]) if "state_biases" in matched else 0.,
                       bias_y=float(matched["state_biases"][t][matched["path"][t]][1]) if "state_biases" in matched else 0.,
                       confidence=probabilities[chosen.edge.segment],
                       entropy=entropy/np.log(len(values)) if len(values)>1 else 0.,
                       correct=chosen.edge.segment == obs["segment"][t])
        rows.append(row)
    metrics = summarise(rows)
    metrics["gps_rmse"] = float(np.sqrt(np.mean(np.sum((obs["xy"]-obs["truth_xy"])**2, axis=1))))
    metrics["runtime_seconds"] = perf_counter()-started
    return {"config": asdict(config), "seed": seed, "trajectory_id": trajectory_id,
            "rows": rows, "metrics": metrics, "failure": failure, "roads": roads}
