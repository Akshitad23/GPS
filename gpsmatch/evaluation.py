"""Person 2 evaluation metrics, independent of the matcher.

Every function here consumes evaluation rows (dictionaries with the pipeline
row schema) or plain arrays. Nothing in this module runs inference or changes
predictions. Conventions:

* Correctness is physical-segment correctness (``row["correct"]``), and the
  confidence score refers to the same physical-segment label.
* Unmatched rows have no score. They are never accepted by a rejection rule,
  but they stay in every coverage denominator and count as not-correct in
  end-to-end accuracy.
* Probability metrics (Brier, log loss, ECE) are computed on matched rows only
  and must always be reported together with the matched fraction.
* Risk is undefined (``None``) when nothing is accepted.
"""
import csv
import math
import numpy as np

EPS = 1e-6
BOOL_FIELDS = ("burst", "true_segment_present", "nearest_correct", "correct")
FLOAT_FIELDS = ("timestamp", "true_x", "true_y", "gps_x", "gps_y", "confidence",
                "entropy", "selected_x", "selected_y", "bias_x", "bias_y")
INT_FIELDS = ("candidate_count", "state_count")


def parse_bool(text):
    """CSV booleans are the literal text True/False; never use truthiness."""
    if isinstance(text, bool):
        return text
    if text == "True":
        return True
    if text == "False":
        return False
    raise ValueError(f"Not a boolean field value: {text!r}")


def load_rows(path):
    """Load a predictions CSV with explicit typing; blank numeric fields -> None."""
    rows = []
    with open(path, newline="", encoding="utf8") as stream:
        for raw in csv.DictReader(stream):
            row = dict(raw)
            for key in BOOL_FIELDS:
                if key in row:
                    row[key] = parse_bool(row[key])
            for key in FLOAT_FIELDS:
                if key in row:
                    row[key] = float(row[key]) if row[key] != "" else None
            for key in INT_FIELDS:
                if key in row and row[key] != "":
                    row[key] = int(row[key])
            rows.append(row)
    return rows


def check_rows(rows):
    """Schema/convention checks; raises AssertionError on a violation."""
    for r in rows:
        matched = r["status"] == "matched"
        assert r["status"] in ("matched", "unmatched"), r["status"]
        if matched:
            assert r["confidence"] is not None and 0. <= r["confidence"] <= 1. + 1e-9
            assert r["entropy"] is not None and -1e-9 <= r["entropy"] <= 1. + 1e-9
            assert r["correct"] == (r["selected_segment"] == r["true_segment"])
            assert r["selected_segment"] != ""
            # Segment labels carry no direction; edge ids add a +/- suffix.
            assert r["selected_directed_edge"].rstrip("+-") == r["selected_segment"]
        else:
            assert r["confidence"] is None and r["entropy"] is None
            assert r["correct"] is False and r["selected_segment"] == ""
        assert r["true_directed_edge"].rstrip("+-") == r["true_segment"]
        if r["correct"]:
            assert r["true_segment_present"], "correct assignment without the true candidate"
    return True


# ---------------------------------------------------------------- scores

def score_values(rows, score="confidence", calibrator=None):
    """Score per row (higher = more trusted); None for unmatched rows.

    score="confidence": aggregated physical-segment posterior, optionally mapped
    by a fitted calibrator.  score="entropy": 1 - normalised entropy.
    """
    if score not in ("confidence", "entropy"):
        raise ValueError(score)
    values = []
    for r in rows:
        if r["status"] != "matched":
            values.append(None)
        elif score == "confidence":
            values.append(float(r["confidence"]))
        else:
            values.append(1. - float(r["entropy"]))
    if calibrator is not None and score == "confidence":
        index = [i for i, v in enumerate(values) if v is not None]
        if index:
            mapped = calibrator.predict([values[i] for i in index])
            for i, v in zip(index, mapped):
                values[i] = float(v)
    return values


# ---------------------------------------------------------------- point metrics

def point_metrics(rows):
    n = len(rows)
    matched = [r for r in rows if r["status"] == "matched"]
    return {
        "points": n,
        "matched_fraction": len(matched)/n if n else None,
        "unmatched_rate": 1. - len(matched)/n if n else None,
        "accuracy": sum(r["correct"] for r in matched)/n if n else None,
        "accuracy_given_match": sum(r["correct"] for r in matched)/len(matched) if matched else None,
        "nearest_accuracy": sum(r["nearest_correct"] for r in rows)/n if n else None,
        "candidate_recall": sum(r["true_segment_present"] for r in rows)/n if n else None,
        "trajectories": len({r["trajectory_id"] for r in rows}),
        "failed_trajectories": len({r["trajectory_id"] for r in rows if r["status"] != "matched"}),
    }


def probability_metrics(probabilities, correct, bins=10):
    """Brier, log loss and ECE on matched rows. Inputs exclude unmatched rows."""
    p = np.asarray(probabilities, dtype=float)
    y = np.asarray(correct, dtype=float)
    if len(p) == 0:
        return {"population": 0, "brier": None, "log_loss": None, "ece": None,
                "mean_confidence": None, "accuracy": None}
    clipped = np.clip(p, EPS, 1-EPS)
    table = reliability_table(p, y, bins)
    ece = sum(b["count"]*abs(b["mean_confidence"]-b["accuracy"]) for b in table if b["count"])/len(p)
    return {
        "population": int(len(p)),
        "brier": float(np.mean((p-y)**2)),
        "log_loss": float(np.mean(-y*np.log(clipped)-(1-y)*np.log(1-clipped))),
        "ece": float(ece),
        "mean_confidence": float(p.mean()),
        "accuracy": float(y.mean()),
    }


def reliability_table(probabilities, correct, bins=10):
    """Equal-width bins on [0,1]; the last bin is closed. Counts are reported."""
    p = np.asarray(probabilities, dtype=float)
    y = np.asarray(correct, dtype=float)
    edges = np.linspace(0., 1., bins+1)
    index = np.clip(np.searchsorted(edges, p, side="right")-1, 0, bins-1)
    table = []
    for b in range(bins):
        mask = index == b
        count = int(mask.sum())
        table.append({"low": float(edges[b]), "high": float(edges[b+1]), "count": count,
                      "mean_confidence": float(p[mask].mean()) if count else None,
                      "accuracy": float(y[mask].mean()) if count else None})
    return table


def matched_arrays(rows, score="confidence", calibrator=None):
    scores = score_values(rows, score, calibrator)
    keep = [i for i, s in enumerate(scores) if s is not None]
    return (np.array([scores[i] for i in keep], dtype=float),
            np.array([rows[i]["correct"] for i in keep], dtype=bool))


# ---------------------------------------------------------------- selective prediction

def risk_coverage(scores, correct, total):
    """Risk-coverage curve for the rule "accept if score >= t".

    ``scores``/``correct`` cover matched rows only; ``total`` is the number of
    ALL attempted observations, so unmatched rows lower the reachable coverage.
    Tied scores are accepted together: one curve point per distinct score.
    Returns arrays (thresholds, coverage, risk), ordered by increasing coverage.
    """
    if total <= 0:
        raise ValueError("total must be positive")
    s = np.asarray(scores, dtype=float)
    wrong = ~np.asarray(correct, dtype=bool)
    if len(s) == 0:
        return np.array([]), np.array([]), np.array([])
    order = np.argsort(-s, kind="stable")
    s, wrong = s[order], wrong[order]
    cumulative_wrong = np.cumsum(wrong)
    # Last index of each tie group in descending order.
    ends = np.flatnonzero(np.r_[s[1:] != s[:-1], True])
    accepted = ends+1
    return s[ends], accepted/total, cumulative_wrong[ends]/accepted


def risk_at_coverage(scores, correct, total, target):
    """Risk of the smallest tie-respecting acceptance set with coverage >= target.

    Returns (risk, achieved_coverage); (None, max_coverage) if unreachable.
    """
    _, coverage, risk = risk_coverage(scores, correct, total)
    reachable = np.flatnonzero(coverage >= target-1e-12)
    if len(reachable) == 0:
        return None, float(coverage[-1]) if len(coverage) else 0.
    i = reachable[0]
    return float(risk[i]), float(coverage[i])


def aurc(scores, correct, total):
    """Area under the step risk-coverage curve over reachable coverage."""
    _, coverage, risk = risk_coverage(scores, correct, total)
    if len(coverage) == 0:
        return None
    widths = np.diff(np.r_[0., coverage])
    return float(np.sum(widths*risk))


def threshold_for_risk(scores, correct, total, target_risk):
    """Lowest threshold whose accepted risk <= target, maximising coverage.

    Returns +inf (reject everything) when no nonempty acceptance set qualifies.
    """
    thresholds, coverage, risk = risk_coverage(scores, correct, total)
    ok = np.flatnonzero(risk <= target_risk+1e-12)
    return float(thresholds[ok[-1]]) if len(ok) else math.inf


def apply_threshold(scores, correct, total, threshold):
    """Coverage/accepted risk/overall accuracy for "accept if score >= threshold"."""
    s = np.asarray(scores, dtype=float)
    c = np.asarray(correct, dtype=bool)
    accepted = s >= threshold
    k = int(accepted.sum())
    return {"threshold": threshold, "accepted": k, "coverage": k/total if total else None,
            "accepted_risk": float((~c[accepted]).mean()) if k else None,
            "overall_accuracy": float(c.sum()/total) if total else None}


def selective_summary(rows, score="confidence", calibrator=None,
                      coverages=(.5, .6, .7, .8, .9)):
    s, c = matched_arrays(rows, score, calibrator)
    total = len(rows)
    out = {"aurc": aurc(s, c, total), "max_coverage": len(s)/total if total else None}
    for target in coverages:
        risk, achieved = risk_at_coverage(s, c, total, target)
        out[f"risk@{target:.2f}"] = risk
        out[f"coverage_used@{target:.2f}"] = achieved
    return out


# ---------------------------------------------------------------- bootstrap

def bootstrap_groups(groups, statistic, draws=1000, seed=20261110):
    """Percentile 95% interval resampling whole groups (journeys), not points.

    ``groups`` is a list of row-lists; ``statistic`` maps a pooled row list to a
    float (or None). Draws where the statistic is undefined are skipped.
    """
    rng = np.random.default_rng(seed)
    n = len(groups)
    values = []
    for _ in range(draws):
        pick = rng.integers(0, n, n)
        pooled = [row for i in pick for row in groups[i]]
        value = statistic(pooled)
        if value is not None and math.isfinite(value):
            values.append(value)
    if not values:
        return None
    low, high = np.quantile(values, [.025, .975])
    return [float(low), float(high)]
