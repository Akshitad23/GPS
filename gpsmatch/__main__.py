"""CLI for reproducible demonstrations and small benchmarks."""
import argparse
import csv
import json
import platform
from pathlib import Path
from dataclasses import replace
import numpy as np
import scipy
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from .pipeline import Config, run_pipeline, summarise


def save(result, directory):
    directory.mkdir(parents=True, exist_ok=True)
    with (directory/"predictions.csv").open("w", newline="", encoding="utf8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(result["rows"][0]))
        writer.writeheader()
        writer.writerows(result["rows"])
    metadata = {k:v for k,v in result.items() if k not in ("rows", "roads")}
    metadata["versions"] = {"python": platform.python_version(), "numpy": np.__version__,
                            "scipy": scipy.__version__, "matplotlib": matplotlib.__version__}
    (directory/"summary.json").write_text(json.dumps(metadata, indent=2, allow_nan=False), encoding="utf8")


def plot(results, destination):
    fig, axes = plt.subplots(len(results), 1, figsize=(12, 3.7*len(results)), squeeze=False)
    for ax, result in zip(axes[:,0], results):
        roads, rows = result["roads"], result["rows"]
        seen = set()
        for edge in roads.edges.values():
            if edge.segment in seen:
                continue
            seen.add(edge.segment)
            points = np.array([roads.nodes[edge.u], roads.nodes[edge.v]])
            ax.plot(points[:,0], points[:,1], color=".8", linewidth=5, zorder=0)
        ax.plot([r["true_x"] for r in rows], [r["true_y"] for r in rows],
                color="green", label="True journey", linewidth=2)
        ax.scatter([r["gps_x"] for r in rows], [r["gps_y"] for r in rows],
                   s=12, color="black", alpha=.4, label="GPS")
        for key, marker, color, label in [("nearest_segment","x","orange","Nearest"),
                                          ("selected_directed_edge","o","royalblue","HMM")]:
            points = []
            for r in rows:
                candidates = roads.candidates(np.array([r["gps_x"],r["gps_y"]]), result["config"]["candidate_radius"])
                if not r[key] or not candidates:
                    continue
                if key == "nearest_segment":
                    candidate = min(candidates, key=lambda c:c.residual)
                else:
                    from .roads import Candidate
                    candidate = Candidate(roads.edges[r[key]],0.,np.array([r["selected_x"],r["selected_y"]]),0.)
                points.append(candidate.point)
            if points:
                points = np.array(points)
                ax.scatter(points[:,0], points[:,1], marker=marker, color=color, s=18, label=label)
        metrics = result["metrics"]
        ax.set_title(f'{result["config"]["noise_kind"]}: HMM {metrics["hmm_accuracy"]:.1%}, '
                     f'nearest {metrics["nearest_accuracy"]:.1%}, candidate recall {metrics["candidate_recall"]:.1%}')
        ax.set(xlabel="x (metres)", ylabel="y (metres)")
        ax.set_aspect("equal", adjustable="datalim")
        ax.legend(loc="upper right", ncol=4, fontsize=8)
    fig.tight_layout()
    fig.savefig(destination, dpi=160)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["demo", "benchmark"])
    parser.add_argument("--output", type=Path, default=Path("results/demo"))
    parser.add_argument("--seeds", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--model",choices=["baseline","motion","robust","bias"],default="baseline")
    args = parser.parse_args()
    if args.seeds <= 0:
        parser.error("--seeds must be positive")
    args.output.mkdir(parents=True, exist_ok=True)
    base = Config(model=args.model)
    if args.command == "demo":
        results = [run_pipeline(replace(base, noise_kind=kind), args.seed)
                   for kind in ("independent","burst","gap")]
        for result in results:
            save(result, args.output/result["config"]["noise_kind"])
        plot(results, args.output/"comparison.png")
        print(json.dumps({r["config"]["noise_kind"]:r["metrics"] for r in results}, indent=2))
    else:
        summary = {}
        for kind in ("independent","burst","matched_iid","gap"):
            rows, rmses, runtimes, failures, trajectory_metrics = [], [], [], [], []
            for i in range(args.seeds):
                config = replace(base, noise_kind=kind, route_variant=i%6)
                result = run_pipeline(config, args.seed+i)
                save(result, args.output/kind/f"seed_{args.seed+i}")
                rows.extend(result["rows"])
                rmses.append(result["metrics"]["gps_rmse"])
                runtimes.append(result["metrics"]["runtime_seconds"])
                failures.append(result["failure"] is not None)
                trajectory_metrics.append(result["metrics"])
            pooled = summarise(rows)
            summary[kind] = {**pooled, "trajectories":args.seeds,
                             "failed_trajectories":sum(failures),
                             "mean_gps_rmse":float(np.mean(rmses)),
                             "mean_runtime_seconds":float(np.mean(runtimes)),
                             "mean_trajectory_accuracy":float(np.mean([m["hmm_accuracy"] for m in trajectory_metrics]))}
        (args.output/"aggregate.json").write_text(json.dumps(summary, indent=2, allow_nan=False),encoding="utf8")
        print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
