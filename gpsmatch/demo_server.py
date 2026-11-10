"""Local interactive demo (offline, synthetic). Standard library only.

    python -m gpsmatch.demo_server            # then open http://127.0.0.1:8765

Every request calls the SAME ``run_pipeline`` used by the experiments, and the
displayed metrics come from ``gpsmatch.evaluation``. Nothing is precomputed or
edited for display. If a calibration study has been run, the fitted Platt map
(mixture population) can optionally be applied to the confidence score; it
never changes which segment is selected.
"""
import argparse
import json
import math
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from .pipeline import Config, run_pipeline
from . import evaluation as ev
from .calibration import from_dict

STATIC = Path(__file__).with_name("demo_static")
DEFAULT_STUDY = Path("results/calibration_study")
LIMITS = {"seed": (0, 10**9), "noise_sigma": (0., 40.), "burst_points": (0, 60),
          "burst_offset": (-60., 60.), "burst_angle_degrees": (-180., 180.),
          "route_variant": (0, 5), "threshold": (0., 1.)}


def _number(query, key, default, cast):
    try:
        value = cast(query.get(key, [default])[0])
    except (TypeError, ValueError):
        raise ValueError(f"Invalid {key}")
    low, high = LIMITS.get(key, (-math.inf, math.inf))
    if not (low <= value <= high) or (isinstance(value, float) and not math.isfinite(value)):
        raise ValueError(f"{key} must lie in [{low}, {high}]")
    return value


def load_calibrator(study_dir, model):
    path = Path(study_dir)/f"calibrators_{model}.json"
    if not path.exists():
        return None
    return from_dict(json.loads(path.read_text(encoding="utf8"))["platt_mixture"])


def run_demo(query, study_dir=DEFAULT_STUDY):
    model = query.get("model", ["baseline"])[0]
    noise_kind = query.get("noise_kind", ["burst"])[0]
    if model not in ("baseline", "motion", "robust", "bias"):
        raise ValueError("Unknown model")
    if noise_kind not in ("independent", "burst", "matched_iid", "gap"):
        raise ValueError("Unknown noise kind")
    seed = _number(query, "seed", 42, int)
    threshold = _number(query, "threshold", .9, float)
    config = replace(Config(), model=model, noise_kind=noise_kind,
                     noise_sigma=_number(query, "noise_sigma", 8., float),
                     burst_points=_number(query, "burst_points", 10, int),
                     burst_offset=_number(query, "burst_offset", 20., float),
                     burst_angle_degrees=_number(query, "burst_angle_degrees", 90., float),
                     route_variant=_number(query, "route_variant", 0, int))
    result = run_pipeline(config, seed)
    calibrator = load_calibrator(study_dir, model) if query.get("score", ["raw"])[0] == "calibrated" else None
    rows = result["rows"]
    scores = ev.score_values(rows, "confidence", calibrator)
    s, c = ev.matched_arrays(rows, "confidence", calibrator)
    selective = ev.apply_threshold(s, c, len(rows), threshold)
    roads = result["roads"]
    seen, segments = set(), []
    for edge in roads.edges.values():
        if edge.segment not in seen:
            seen.add(edge.segment)
            segments.append({"id": edge.segment, "a": roads.nodes[edge.u].tolist(),
                             "b": roads.nodes[edge.v].tolist()})
    points = [{"t": r["timestamp"], "true": [r["true_x"], r["true_y"]], "gps": [r["gps_x"], r["gps_y"]],
               "sel": [r["selected_x"], r["selected_y"]] if r["status"] == "matched" else None,
               "true_segment": r["true_segment"], "selected_segment": r["selected_segment"],
               "nearest_segment": r["nearest_segment"], "burst": r["burst"], "status": r["status"],
               "correct": r["correct"], "confidence": r["confidence"], "score": score,
               "entropy": r["entropy"], "candidates": r["candidate_count"],
               "accepted": score is not None and score >= threshold}
              for r, score in zip(rows, scores)]
    point = ev.point_metrics(rows)
    return {"config": result["config"], "seed": seed, "trajectory_id": result["trajectory_id"],
            "failure": result["failure"], "segments": segments, "points": points,
            "score_kind": "calibrated (Platt, mixture fit)" if calibrator else "raw posterior",
            "calibrator_available": load_calibrator(study_dir, model) is not None,
            "metrics": {"accuracy": point["accuracy"], "nearest_accuracy": point["nearest_accuracy"],
                        "matched_fraction": point["matched_fraction"],
                        "failure_rate": point["unmatched_rate"],
                        "candidate_recall": point["candidate_recall"],
                        "coverage": selective["coverage"], "accepted_risk": selective["accepted_risk"],
                        "accepted": selective["accepted"], "points": point["points"],
                        "gps_rmse": result["metrics"]["gps_rmse"]}}


class Handler(BaseHTTPRequestHandler):
    study_dir = DEFAULT_STUDY

    def _send(self, status, body, content_type):
        data = body.encode("utf8") if isinstance(body, str) else body
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        url = urlparse(self.path)
        if url.path in ("/", "/index.html"):
            self._send(200, (STATIC/"index.html").read_bytes(), "text/html; charset=utf-8")
        elif url.path == "/api/run":
            try:
                payload = run_demo(parse_qs(url.query), self.study_dir)
                self._send(200, json.dumps(payload, allow_nan=False), "application/json")
            except ValueError as error:
                self._send(400, json.dumps({"error": str(error)}), "application/json")
        else:
            self._send(404, "Not found", "text/plain")

    def log_message(self, *args):
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--study", type=Path, default=DEFAULT_STUDY,
                        help="calibration study directory providing calibrators_<model>.json")
    args = parser.parse_args()
    Handler.study_dir = args.study
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Offline synthetic demo at http://{args.host}:{args.port}  (Ctrl+C to stop)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
