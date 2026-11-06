"""Paired, reproducible model comparisons on synthetic trajectories.

This is a model comparison, not calibration training. Run development and
evaluation with disjoint seeds. Parameters are recorded before any results.
"""
import argparse
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import platform
import numpy as np
import scipy
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from .pipeline import Config, run_pipeline, summarise
from .__main__ import save

MODELS = ("baseline","motion","robust","bias")
SCENARIOS = {
    "independent": {"noise_kind":"independent"},
    "burst_positive": {"noise_kind":"burst","burst_offset":20.},
    "burst_negative": {"noise_kind":"burst","burst_offset":25.,"burst_angle_degrees":-90.},
    "burst_diagonal": {"noise_kind":"burst","burst_offset":28.,"burst_angle_degrees":45.},
    "burst_offgrid": {"noise_kind":"burst","burst_offset":12.,"burst_angle_degrees":90.},
    "burst_long": {"noise_kind":"burst","burst_offset":28.,"burst_points":18,"burst_start_fraction":.3},
    "burst_at_start": {"noise_kind":"burst","burst_offset":20.,"burst_start_fraction":0.},
    "matched_iid": {"noise_kind":"matched_iid","burst_offset":20.},
    "gap": {"noise_kind":"gap"},
}


def aggregate(results):
    rows = [row for result in results for row in result["rows"]]
    output = summarise(rows)
    good = [r for r in rows if r["status"]=="matched"]
    if good:
        p = np.clip([r["confidence"] for r in good],1e-12,1-1e-12)
        y = np.array([r["correct"] for r in good],dtype=float)
        output["log_loss_given_match"] = float(np.mean(-y*np.log(p)-(1-y)*np.log(1-p)))
    else:
        output["log_loss_given_match"] = None
    output["confident_wrong_count"] = sum(not r["correct"] and r["confidence"]>=.9 for r in good)
    output["confident_wrong_fraction_all"] = output["confident_wrong_count"]/len(rows)
    output["failed_trajectories"] = sum(r["failure"] is not None for r in results)
    output["mean_runtime_seconds"] = float(np.mean([r["metrics"]["runtime_seconds"] for r in results]))
    output["mean_trajectory_accuracy"] = float(np.mean([r["metrics"]["hmm_accuracy"] for r in results]))
    output["mean_gps_rmse"] = float(np.mean([r["metrics"]["gps_rmse"] for r in results]))
    return output


def paired_interval(baseline, other):
    # Resample complete trajectory differences, not correlated GPS points.
    delta = np.array([b["metrics"]["hmm_accuracy"]-a["metrics"]["hmm_accuracy"]
                      for a,b in zip(baseline,other)])
    rng = np.random.default_rng(20261027)
    draws = rng.choice(delta,(1000,len(delta)),replace=True).mean(axis=1)
    low,high = np.quantile(draws,[.025,.975])
    return {"mean_delta":float(delta.mean()),"ci95":[float(low),float(high)]}


def comparison_plot(summary, output):
    conditions = list(summary["scenarios"])
    fig, axes = plt.subplots(1,2,figsize=(16,6))
    x = np.arange(len(conditions))
    for i,model in enumerate(MODELS):
        accuracy = [summary["scenarios"][c][model]["hmm_accuracy"] for c in conditions]
        brier = [summary["scenarios"][c][model]["brier_given_match"] for c in conditions]
        axes[0].bar(x+(i-1.5)*.19,accuracy,width=.19,label=model)
        axes[1].bar(x+(i-1.5)*.19,brier,width=.19,label=model)
    for ax in axes:
        ax.set_xticks(x, [c.replace("burst_","") for c in conditions],rotation=45,ha="right")

        ax.grid(axis="y",alpha=.2)
    axes[0].set(ylabel="Road-segment accuracy",ylim=(0,1),title="All observations; unmatched counts as wrong")
    axes[1].set(ylabel="Binary correctness Brier score",title="Confidence quality (lower is better)")
    handles,labels=axes[0].get_legend_handles_labels()
    fig.legend(handles,labels,loc="upper center",ncol=4)
    fig.tight_layout(rect=(0,0,1,.93))
    fig.savefig(output,dpi=150)
    plt.close(fig)


def run_comparison(output, seeds=12, first_seed=10000, split="evaluation"):
    output = Path(output)
    if (output/"manifest.json").exists():
        raise FileExistsError("Use a fresh output directory; comparison manifests are not overwritten")
    if seeds<1:
        raise ValueError("seeds must be positive")
    output.mkdir(parents=True,exist_ok=True)
    base = Config()
    cases = []
    for scenario,overrides in SCENARIOS.items():
        for i in range(seeds):
            # Evaluation varies geometry as well as random noise; templates remain
            # the same six small route families, so this is not real-world validation.
            separation = (16.,24.,32.)[i%3] if split=="evaluation" else 20.
            config = replace(base,**overrides,route_variant=i%6,road_separation=separation)
            cases.append({"scenario":scenario,"seed":first_seed+i,"config":asdict(config)})
    manifest = {"split":split,"models":MODELS,"cases":cases,
                "versions":{"python":platform.python_version(),"numpy":np.__version__,"scipy":scipy.__version__},
                "note":"No model parameters fitted on evaluation. Same geometry/observations for all models per case."}
    (output/"manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf8")
    scenario_results = {}
    all_results = {m:[] for m in MODELS}
    for scenario in SCENARIOS:
        grouped = {m:[] for m in MODELS}
        for case in [c for c in cases if c["scenario"]==scenario]:
            config = Config(**case["config"])
            reference = None
            for model in MODELS:
                result = run_pipeline(replace(config,model=model),case["seed"])
                signature = [(r["timestamp"],r["true_segment"],r["gps_x"],r["gps_y"]) for r in result["rows"]]
                if reference is not None and signature != reference:
                    raise AssertionError("Unpaired data across model variants")
                reference = signature
                save(result,output/scenario/f'seed_{case["seed"]}'/model)
                grouped[model].append(result)
                all_results[model].append(result)
        scenario_results[scenario] = {m:aggregate(grouped[m]) for m in MODELS}
        scenario_results[scenario]["paired_accuracy_delta_vs_baseline"] = {
            m:paired_interval(grouped["baseline"],grouped[m]) for m in MODELS if m!="baseline"}
        print(f"Completed {scenario}: "+", ".join(f'{m}={scenario_results[scenario][m]["hmm_accuracy"]:.3f}' for m in MODELS),flush=True)
    summary = {"split":split,"seeds_per_scenario":seeds,
               "total_model_runs":len(cases)*len(MODELS),
               "manifest_sha256":hashlib.sha256((output/"manifest.json").read_bytes()).hexdigest(),
               "scenarios":scenario_results,
               "overall":{m:aggregate(all_results[m]) for m in MODELS}}
    (output/"comparison.json").write_text(json.dumps(summary,indent=2,allow_nan=False),encoding="utf8")
    comparison_plot(summary,output/"comparison.png")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",required=True,type=Path)
    parser.add_argument("--seeds",type=int,default=12)
    parser.add_argument("--first-seed",type=int,default=10000)
    parser.add_argument("--split",choices=["development","evaluation"],default="evaluation")
    args = parser.parse_args()
    result = run_comparison(args.output,args.seeds,args.first_seed,args.split)
    print(json.dumps(result["overall"],indent=2))


if __name__=="__main__":
    main()
