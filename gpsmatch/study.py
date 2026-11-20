"""Person 2 calibration study: frozen splits, calibration fitting and evaluation.

Usage (from the GPS directory):

    python -m gpsmatch.study run     --output results/calibration_study
    python -m gpsmatch.study analyse --output results/calibration_study

``run`` writes a manifest BEFORE inference and refuses to reuse a directory.
It only calls the existing ``run_pipeline``; predictions are never altered.
``analyse`` reads the saved prediction CSVs back (explicit boolean parsing),
fits calibration maps on calibration journeys only, and evaluates them on the
untouched test journeys. It can be re-run; it overwrites only analysis outputs.

Protocol (frozen here and copied into the manifest):

* A "journey group" is one seed. All noise scenarios of that seed share the
  same simulated truth journey (route variant and start phase), so a group's
  variants always stay in the same split and bootstrap intervals resample
  whole groups.
* Development, calibration and test use disjoint seed blocks. Development is
  used only for the screening-slack sensitivity check and sanity checks.
* Calibration maps are fitted on (a) independent-noise calibration journeys
  and (b) a mixture of independent and burst calibration journeys with the
  same number of trajectories. Both are evaluated on the same test journeys.
* Test also includes burst types that neither fit population contains
  (burst_long, burst_negative) and a magnitude-matched independent control.
"""
import argparse
import csv
import hashlib
import json
import math
import platform
from dataclasses import asdict, replace
from pathlib import Path
import numpy as np
import scipy
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from .pipeline import Config, run_pipeline
from . import evaluation as ev
from .calibration import CALIBRATORS

SPLITS = {
    "development": list(range(40000, 40012)),
    "calibration": list(range(50000, 50036)),
    "test": list(range(60000, 60036)),
}
SCENARIOS = {
    "independent": {"noise_kind": "independent"},
    "burst": {"noise_kind": "burst", "burst_offset": 20.},
    "burst_diagonal": {"noise_kind": "burst", "burst_offset": 28., "burst_angle_degrees": 45.},
    "burst_negative": {"noise_kind": "burst", "burst_offset": 25., "burst_angle_degrees": -90.},
    "burst_long": {"noise_kind": "burst", "burst_offset": 28., "burst_points": 18,
                   "burst_start_fraction": .3},
    "matched_iid": {"noise_kind": "matched_iid", "burst_offset": 20.},
    "gap": {"noise_kind": "gap"},
}
SEEN_IN_MIXTURE = ("independent", "burst", "burst_diagonal")
DEFAULT_MODELS = ("baseline", "robust")
SLACK_VALUES = (0., 1., 2., 3., 5.)
SLACK_SCENARIOS = ("independent", "burst", "burst_long", "gap")
TARGET_RISK = .05
COVERAGES = (.5, .6, .7, .8, .9)
ROUTE_FIT, ROUTE_TEST = (0, 1, 2), (3, 4, 5)
EXTRA_FIELDS = ("split", "scenario", "seed", "group", "route_variant", "model")


def mixture_scenario(index):
    """Equal-size mixture: half independent, a quarter each of two burst types."""
    return ("independent", "independent", "burst", "burst_diagonal")[index % 4]


def case_config(model, scenario, index, **overrides):
    return replace(Config(), model=model, route_variant=index % 6,
                   **SCENARIOS[scenario], **overrides)


# ======================================================================= run

def _write_rows(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run_study(output, models=DEFAULT_MODELS):
    output = Path(output)
    if (output/"manifest.json").exists():
        raise FileExistsError("Use a fresh output directory; the study manifest is not overwritten")
    output.mkdir(parents=True, exist_ok=True)
    manifest = {
        "protocol": __doc__,
        "splits": SPLITS, "scenarios": SCENARIOS, "models": list(models),
        "mixture_rule": "calibration group i uses " + str([mixture_scenario(i) for i in range(4)]) + "[i % 4]",
        "route_rule": "route_variant = index within split % 6",
        "slack_sensitivity": {"split": "development", "model": "baseline",
                              "values": SLACK_VALUES, "scenarios": SLACK_SCENARIOS},
        "target_risk": TARGET_RISK, "coverages": COVERAGES,
        "route_holdout": {"fit_routes": ROUTE_FIT, "test_routes": ROUTE_TEST},
        "base_config": asdict(Config()),
        "versions": {"python": platform.python_version(), "numpy": np.__version__,
                     "scipy": scipy.__version__, "matplotlib": matplotlib.__version__},
    }
    (output/"manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf8")
    trajectories = []
    for model in models:
        for split, seeds in SPLITS.items():
            rows = []
            for index, seed in enumerate(seeds):
                reference = None
                for scenario in SCENARIOS:
                    result = run_pipeline(case_config(model, scenario, index), seed)
                    truth = [(r["true_segment"], r["true_x"], r["true_y"]) for r in result["rows"]]
                    if scenario == "independent":
                        reference = truth
                    elif scenario != "gap":  # gaps drop observations; others keep all
                        assert truth == reference, "noise variants of a group must share truth"
                    extra = {"split": split, "scenario": scenario, "seed": seed, "group": f"{split}_{seed}",
                             "route_variant": index % 6, "model": model}
                    rows.extend({**r, **extra} for r in result["rows"])
                    burst_err = [math.hypot(r["gps_x"]-r["true_x"], r["gps_y"]-r["true_y"])
                                 for r in result["rows"] if r["burst"]]
                    trajectories.append({**extra, "trajectory_id": result["trajectory_id"],
                                         "points": result["metrics"]["points"],
                                         "failure": result["failure"] or "",
                                         "gps_rmse": result["metrics"]["gps_rmse"],
                                         "burst_rmse": float(np.sqrt(np.mean(np.square(burst_err)))) if burst_err else "",
                                         "runtime_seconds": result["metrics"]["runtime_seconds"]})
            _write_rows(output/"predictions"/f"{split}_{model}.csv", rows)
            print(f"{model}/{split}: {len(seeds)} groups, {len(rows)} observations", flush=True)
    # Screening-slack sensitivity: development journeys only.
    slack_rows = []
    for slack in SLACK_VALUES:
        for index, seed in enumerate(SPLITS["development"]):
            for scenario in SLACK_SCENARIOS:
                result = run_pipeline(case_config("baseline", scenario, index,
                                                  projection_slack_sigma=slack), seed)
                slack_rows.extend({**r, "split": "development", "scenario": scenario, "seed": seed,
                                   "group": f"development_{seed}", "route_variant": index % 6,
                                   "model": "baseline", "slack": slack} for r in result["rows"])
    _write_rows(output/"predictions"/"development_slack_sensitivity.csv", slack_rows)
    _write_rows(output/"trajectories.csv", trajectories)
    print("Run complete", flush=True)


# ======================================================================= analyse

def _load(output, split, model):
    rows = ev.load_rows(output/"predictions"/f"{split}_{model}.csv")
    for r in rows:
        r["seed"] = int(r["seed"])
        r["route_variant"] = int(r["route_variant"])
    ev.check_rows(rows)
    return rows


def _groups(rows):
    grouped = {}
    for r in rows:
        grouped.setdefault(r["group"], []).append(r)
    return [grouped[k] for k in sorted(grouped)]


def _fit_population(cal_rows, population, routes=None):
    seeds = SPLITS["calibration"]
    chosen = set()
    for index, seed in enumerate(seeds):
        if routes is not None and index % 6 not in routes:
            continue
        scenario = "independent" if population == "independent" else mixture_scenario(index)
        chosen.add((seed, scenario))
    rows = [r for r in cal_rows if (r["seed"], r["scenario"]) in chosen]
    return rows


def _fit(rows, kind):
    p, y = ev.matched_arrays(rows)
    return CALIBRATORS[kind]().fit(p, y)


def _prob_block(rows, calibrator, draws, raw_reference=None):
    p, y = ev.matched_arrays(rows, "confidence", calibrator)
    block = ev.probability_metrics(p, y)
    # Bootstrap over whole journey groups. Each group contributes its matched
    # rows; groups are resampled with replacement, never individual points.
    arrays = []
    for g in _groups(rows):
        pc, yc = ev.matched_arrays(g, "confidence", calibrator)
        pr, _ = ev.matched_arrays(g, "confidence", None)
        arrays.append((pc, pr, yc))
    rng = np.random.default_rng(20261110)
    samples = {"brier": [], "log_loss": [], "ece": [], "delta": []}
    for _ in range(draws if arrays else 0):
        pick = rng.integers(0, len(arrays), len(arrays))
        pc = np.concatenate([arrays[i][0] for i in pick])
        if len(pc) == 0:
            continue  # undefined draw (no matched rows); skipped explicitly
        pr = np.concatenate([arrays[i][1] for i in pick])
        yc = np.concatenate([arrays[i][2] for i in pick])
        m = ev.probability_metrics(pc, yc)
        for name in ("brier", "log_loss", "ece"):
            samples[name].append(m[name])
        samples["delta"].append(m["brier"]-float(np.mean((pr-yc)**2)))

    def ci(values):
        return [float(v) for v in np.quantile(values, [.025, .975])] if values else None
    for name in ("brier", "log_loss", "ece"):
        block[f"{name}_ci95"] = ci(samples[name])
    if calibrator is not None:
        block["brier_delta_vs_raw"] = (block["brier"]-raw_reference["brier"]
                                       if block["brier"] is not None else None)
        block["brier_delta_vs_raw_ci95"] = ci(samples["delta"])
    block["reliability"] = ev.reliability_table(p, y)
    return block


def analyse(output, draws=1000):
    output = Path(output)
    manifest = json.loads((output/"manifest.json").read_text(encoding="utf8"))
    models = manifest["models"]
    trajectories = list(csv.DictReader((output/"trajectories.csv").open(encoding="utf8")))
    results = {"manifest_sha256": hashlib.sha256((output/"manifest.json").read_bytes()).hexdigest(),
               "bootstrap_draws": draws, "models": {}}
    figures = output/"figures"
    figures.mkdir(exist_ok=True)

    # ---------- noise magnitude per scenario (test split, model-independent)
    magnitude = {}
    for scenario in SCENARIOS:
        t = [x for x in trajectories if x["split"] == "test" and x["scenario"] == scenario
             and x["model"] == models[0]]
        burst = [float(x["burst_rmse"]) for x in t if x["burst_rmse"] != ""]
        magnitude[scenario] = {"trajectories": len(t),
                               "mean_gps_rmse_m": float(np.mean([float(x["gps_rmse"]) for x in t])),
                               "mean_burst_segment_rmse_m": float(np.mean(burst)) if burst else None}
    results["noise_magnitude_test"] = magnitude
    results["failures"] = {f'{x["model"]}/{x["split"]}/{x["scenario"]}/seed{x["seed"]}': x["failure"]
                           for x in trajectories if x["failure"]}

    for model in models:
        cal_rows = _load(output, "calibration", model)
        test_rows = _load(output, "test", model)
        dev_rows = _load(output, "development", model)
        mres = {"development_overview": {s: ev.point_metrics([r for r in dev_rows if r["scenario"] == s])
                                         for s in SCENARIOS}}
        # ---------- fit calibrators (calibration split only)
        fitted, fit_info = {}, {}
        for population in ("independent", "mixture"):
            pop_rows = _fit_population(cal_rows, population)
            matched = sum(r["status"] == "matched" for r in pop_rows)
            for kind in CALIBRATORS:
                name = f"{kind}_{population}"
                fitted[name] = _fit(pop_rows, kind)
                fit_info[name] = {**fitted[name].to_dict(), "population": population,
                                  "trajectories": len({r["trajectory_id"] for r in pop_rows}),
                                  "observations": len(pop_rows), "matched_used": matched,
                                  "unmatched_excluded": len(pop_rows)-matched}
        mres["calibrators"] = fit_info
        (output/f"calibrators_{model}.json").write_text(json.dumps(fit_info, indent=2), encoding="utf8")

        # ---------- test evaluation, per scenario and pooled
        mres["test"] = {}
        for scenario in list(SCENARIOS)+["ALL"]:
            rows = test_rows if scenario == "ALL" else [r for r in test_rows if r["scenario"] == scenario]
            entry = {"point": ev.point_metrics(rows)}
            groups = _groups(rows)
            entry["point"]["accuracy_ci95"] = ev.bootstrap_groups(
                groups, lambda pooled: ev.point_metrics(pooled)["accuracy"], draws)
            raw = _prob_block(rows, None, draws)
            entry["probability"] = {"raw": raw}
            for name, cal in fitted.items():
                entry["probability"][name] = _prob_block(rows, cal, draws, raw)
            entry["selective"] = {
                "raw_confidence": ev.selective_summary(rows, "confidence", None, COVERAGES),
                "entropy": ev.selective_summary(rows, "entropy", None, COVERAGES),
                **{name: ev.selective_summary(rows, "confidence", cal, COVERAGES)
                   for name, cal in fitted.items()}}
            mres["test"][scenario] = entry

        # ---------- threshold transfer: choose on calibration, apply to test
        transfer = {}
        for population in ("independent", "mixture"):
            pop_rows = _fit_population(cal_rows, population)
            for score in ("confidence", "entropy"):
                s, c = ev.matched_arrays(pop_rows, score)
                threshold = ev.threshold_for_risk(s, c, len(pop_rows), TARGET_RISK)
                key = f"{score}_from_{population}"
                transfer[key] = {"threshold": threshold,
                                 "calibration": ev.apply_threshold(s, c, len(pop_rows), threshold),
                                 "test": {}}
                for scenario in SCENARIOS:
                    rows = [r for r in test_rows if r["scenario"] == scenario]
                    st, ct = ev.matched_arrays(rows, score)
                    transfer[key]["test"][scenario] = ev.apply_threshold(st, ct, len(rows), threshold)
        mres["threshold_transfer"] = {"target_risk": TARGET_RISK, **transfer}

        # ---------- route generalisation: fit on routes 0-2, test on routes 3-5
        route = {}
        held_test = [r for r in test_rows if r["route_variant"] in ROUTE_TEST]
        maps = {"raw": None,
                "platt_independent_all_routes": fitted["platt_independent"],
                "platt_independent_routes_0_2": _fit(_fit_population(cal_rows, "independent", ROUTE_FIT), "platt"),
                "platt_mixture_all_routes": fitted["platt_mixture"],
                "platt_mixture_routes_0_2": _fit(_fit_population(cal_rows, "mixture", ROUTE_FIT), "platt")}
        for scenario in ("independent", "burst", "burst_long"):
            rows = [r for r in held_test if r["scenario"] == scenario]
            route[scenario] = {}
            for name, cal in maps.items():
                p, y = ev.matched_arrays(rows, "confidence", cal)
                route[scenario][name] = {k: v for k, v in ev.probability_metrics(p, y).items()}
        mres["route_holdout"] = {"fit_routes": ROUTE_FIT, "test_routes": ROUTE_TEST, "results": route}
        results["models"][model] = mres
        _plots(model, test_rows, fitted, mres, figures)

    # ---------- screening-slack sensitivity (development only)
    slack_rows = ev.load_rows(output/"predictions"/"development_slack_sensitivity.csv")
    slack = {}
    for value in SLACK_VALUES:
        for scenario in SLACK_SCENARIOS:
            rows = [r for r in slack_rows if float(r["slack"]) == value and r["scenario"] == scenario]
            slack[f"{value:g}/{scenario}"] = ev.point_metrics(rows)
    results["slack_sensitivity_development"] = slack
    (output/"results.json").write_text(json.dumps(results, indent=2, allow_nan=False, default=_json),
                                       encoding="utf8")
    (output/"results.md").write_text(render_markdown(results), encoding="utf8")
    print(f"Analysis written to {output/'results.json'} and {output/'results.md'}")
    return results


def _json(value):
    if isinstance(value, float) and math.isinf(value):
        return "inf"
    raise TypeError(type(value))


# ======================================================================= figures

PLOT_SCENARIOS = ("independent", "burst", "burst_long", "matched_iid")
METHOD_STYLE = {"raw": ("raw posterior", "black"),
                "platt_independent": ("Platt fit: independent", "tab:blue"),
                "platt_mixture": ("Platt fit: mixture", "tab:orange"),
                "isotonic_mixture": ("Isotonic fit: mixture", "tab:green")}


def _plots(model, test_rows, fitted, mres, figures):
    # Reliability diagrams with bin counts.
    fig, axes = plt.subplots(2, len(PLOT_SCENARIOS), figsize=(4.2*len(PLOT_SCENARIOS), 7.5),
                             gridspec_kw={"height_ratios": [3, 1]}, sharex=True)
    for col, scenario in enumerate(PLOT_SCENARIOS):
        rows = [r for r in test_rows if r["scenario"] == scenario]
        ax, hist = axes[0, col], axes[1, col]
        ax.plot([0, 1], [0, 1], color=".7", linestyle="--", linewidth=1)
        for name, (label, color) in METHOD_STYLE.items():
            p, y = ev.matched_arrays(rows, "confidence", fitted.get(name))
            table = [b for b in ev.reliability_table(p, y) if b["count"]]
            ax.plot([b["mean_confidence"] for b in table], [b["accuracy"] for b in table],
                    marker="o", color=color, label=label, linewidth=1.4, markersize=4)
        p, _ = ev.matched_arrays(rows)
        hist.hist(p, bins=np.linspace(0, 1, 11), color=".5")
        hist.set_yscale("log")
        b = mres["test"][scenario]["probability"]
        ax.set_title(f"{scenario}\nBrier raw {b['raw']['brier']:.3f} / mix {b['platt_mixture']['brier']:.3f}",
                     fontsize=10)
        ax.set(xlim=(0, 1), ylim=(0, 1))
        hist.set_xlabel("confidence (raw)")
        if col == 0:
            ax.set_ylabel("observed segment accuracy")
            hist.set_ylabel("count (log)")
    axes[0, 0].legend(fontsize=8, loc="upper left")
    fig.suptitle(f"Reliability on untouched test journeys ({model}); 10 equal-width bins", fontsize=11)
    fig.tight_layout()
    fig.savefig(figures/f"reliability_{model}.png", dpi=150)
    plt.close(fig)

    # Risk-coverage curves.
    fig, axes = plt.subplots(1, len(PLOT_SCENARIOS), figsize=(4.2*len(PLOT_SCENARIOS), 3.8), sharey=True)
    for ax, scenario in zip(axes, PLOT_SCENARIOS):
        rows = [r for r in test_rows if r["scenario"] == scenario]
        for score, cal, label, color, style in [
                ("confidence", None, "raw posterior", "black", "-"),
                ("entropy", None, "1 - entropy", "tab:red", "-"),
                ("confidence", fitted["platt_mixture"], "Platt (mixture)", "tab:orange", ":"),
                ("confidence", fitted["isotonic_mixture"], "isotonic (mixture)", "tab:green", "--")]:
            s, c = ev.matched_arrays(rows, score, cal)
            _, cov, risk = ev.risk_coverage(s, c, len(rows))
            ax.step(cov, risk, where="post", color=color, linestyle=style, label=label, linewidth=1.4)
        ax.set(title=scenario, xlabel="coverage (all attempted points)", xlim=(0, 1))
        ax.grid(alpha=.2)
    axes[0].set_ylabel("accepted risk")
    axes[0].legend(fontsize=8)
    fig.suptitle(f"Risk-coverage on test journeys ({model}); Platt overlays raw by construction", fontsize=11)
    fig.tight_layout()
    fig.savefig(figures/f"risk_coverage_{model}.png", dpi=150)
    plt.close(fig)

    # Threshold transfer.
    fig, ax = plt.subplots(figsize=(10, 4))
    scenarios = list(SCENARIOS)
    x = np.arange(len(scenarios))
    for i, (key, color) in enumerate([("confidence_from_independent", "tab:blue"),
                                      ("confidence_from_mixture", "tab:orange")]):
        info = mres["threshold_transfer"][key]
        risks = [info["test"][s]["accepted_risk"] or 0. for s in scenarios]
        covs = [info["test"][s]["coverage"] for s in scenarios]
        bars = ax.bar(x+(i-.5)*.38, risks, width=.38, color=color,
                      label=f"{key.replace('confidence_from_', 'threshold fit on ')} (t={info['threshold']:.3f})")
        for bar, cov in zip(bars, covs):
            ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+.003, f"cov {cov:.0%}",
                    ha="center", fontsize=7, rotation=90)
    ax.axhline(TARGET_RISK, color="red", linestyle="--", linewidth=1, label=f"target risk {TARGET_RISK:.0%}")
    ax.set_ylim(0, ax.get_ylim()[1]*1.25)
    ax.set_xticks(x, scenarios, rotation=30, ha="right")
    ax.set_ylabel("realised accepted risk on test")
    ax.legend(fontsize=8)
    ax.set_title(f"Rejection-threshold transfer ({model}): chosen on calibration journeys, applied to test")
    fig.tight_layout()
    fig.savefig(figures/f"threshold_transfer_{model}.png", dpi=150)
    plt.close(fig)

    # Fitted maps.
    fig, ax = plt.subplots(figsize=(5, 5))
    grid = np.linspace(0, 1, 501)
    ax.plot([0, 1], [0, 1], color=".7", linestyle="--")
    for name, cal in fitted.items():
        ax.plot(grid, cal.predict(grid), label=name, linewidth=1.3)
    ax.set(xlabel="raw confidence", ylabel="calibrated probability", title=f"Fitted maps ({model})")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(figures/f"calibration_maps_{model}.png", dpi=150)
    plt.close(fig)


# ======================================================================= markdown

def _f(value, digits=4, pct=False):
    if value is None:
        return "n/a"
    if isinstance(value, str):
        return value
    if math.isinf(value):
        return "inf"
    return f"{value:.{max(digits-2, 1)}%}" if pct else f"{value:.{digits}f}"


def _ci(ci, digits=4):
    return f"[{ci[0]:.{digits}f}, {ci[1]:.{digits}f}]" if ci else "n/a"


def render_markdown(results):
    out = ["# Calibration study results (auto-generated)\n",
           f"Manifest SHA-256: `{results['manifest_sha256']}`. Bootstrap: {results['bootstrap_draws']} "
           "draws resampling whole journey groups (seeds).\n",
           "## Noise magnitude on test journeys\n",
           "| Scenario | Trajectories | Mean radial GPS RMSE (m) | Mean RMSE inside burst (m) |",
           "|---|---:|---:|---:|"]
    for s, m in results["noise_magnitude_test"].items():
        out.append(f"| {s} | {m['trajectories']} | {m['mean_gps_rmse_m']:.2f} | {_f(m['mean_burst_segment_rmse_m'], 2)} |")
    out.append(f"\nFailed trajectories across all runs: {len(results['failures'])}.")
    for key, why in results["failures"].items():
        out.append(f"- {key}: {why}")
    for model, m in results["models"].items():
        out += [f"\n## Model: {model}\n", "### Calibrators (fitted on calibration journeys only)\n",
                "| Map | Trajectories | Matched rows used | Unmatched excluded | Parameters |", "|---|---:|---:|---:|---|"]
        for name, c in m["calibrators"].items():
            params = f"a={c['a']:.3f}, b={c['b']:.3f}" if c["kind"] == "platt" else f"{c['blocks']} steps"
            out.append(f"| {name} | {c['trajectories']} | {c['matched_used']} | {c['unmatched_excluded']} | {params} |")
        out += ["\n### End-to-end assignment quality on test\n",
                "| Scenario | Obs | Matched | Accuracy (95% CI) | Nearest | Candidate recall | Failed traj. |",
                "|---|---:|---:|---|---:|---:|---:|"]
        for s, e in m["test"].items():
            p = e["point"]
            out.append(f"| {s} | {p['points']} | {_f(p['matched_fraction'], pct=True)} | "
                       f"{_f(p['accuracy'], pct=True)} {_ci(p['accuracy_ci95'], 3)} | {_f(p['nearest_accuracy'], pct=True)} | "
                       f"{_f(p['candidate_recall'], pct=True)} | {p['failed_trajectories']} |")
        out += ["\n### Probability quality on test (matched rows only; see matched fraction above)\n",
                "| Scenario | Method | Brier (95% CI) | Δ Brier vs raw (95% CI) | Log loss | ECE |",
                "|---|---|---|---|---:|---:|"]
        for s, e in m["test"].items():
            for name, b in e["probability"].items():
                delta = (f"{b['brier_delta_vs_raw']:+.4f} {_ci(b.get('brier_delta_vs_raw_ci95'))}"
                         if "brier_delta_vs_raw" in b else "—")
                out.append(f"| {s} | {name} | {_f(b['brier'])} {_ci(b['brier_ci95'])} | {delta} | "
                           f"{_f(b['log_loss'])} | {_f(b['ece'])} |")
        out += ["\n### Selective prediction on test: accepted risk at matched coverage\n",
                "| Scenario | Score | AURC | " + " | ".join(f"risk@{c:.0%}" for c in COVERAGES) + " |",
                "|---|---|---:|" + "---:|"*len(COVERAGES)]
        for s, e in m["test"].items():
            for name, sel in e["selective"].items():
                if name.startswith("platt_independent") or name.startswith("isotonic_independent"):
                    continue
                out.append(f"| {s} | {name} | {_f(sel['aurc'])} | " +
                           " | ".join(_f(sel[f'risk@{c:.2f}']) for c in COVERAGES) + " |")
        tt = m["threshold_transfer"]
        out += [f"\n### Threshold transfer (target accepted risk {tt['target_risk']:.0%} on calibration)\n",
                "| Rule | Threshold | Cal. coverage | Cal. risk | " +
                " | ".join(f"{s} cov / risk" for s in SCENARIOS) + " |",
                "|---|---:|---:|---:|" + "---|"*len(SCENARIOS)]
        for key, info in tt.items():
            if key == "target_risk":
                continue
            cal = info["calibration"]
            out.append(f"| {key} | {_f(info['threshold'])} | {_f(cal['coverage'], pct=True)} | "
                       f"{_f(cal['accepted_risk'], pct=True)} | " +
                       " | ".join(f"{_f(v['coverage'], pct=True)} / {_f(v['accepted_risk'], pct=True)}"
                                  for v in info["test"].values()) + " |")
        rh = m["route_holdout"]
        out += [f"\n### Route hold-out: calibrators fitted on routes {rh['fit_routes']}, tested on routes {rh['test_routes']}\n",
                "| Test scenario | Map | Brier | Log loss | ECE | Matched rows |", "|---|---|---:|---:|---:|---:|"]
        for s, maps in rh["results"].items():
            for name, b in maps.items():
                out.append(f"| {s} | {name} | {_f(b['brier'])} | {_f(b['log_loss'])} | {_f(b['ece'])} | {b['population']} |")
    out += ["\n## Screening-slack sensitivity (development journeys, baseline)\n",
            "| Slack multiplier / scenario | Matched | Accuracy | Accuracy given match | Failed traj. |",
            "|---|---:|---:|---:|---:|"]
    for key, p in results["slack_sensitivity_development"].items():
        out.append(f"| {key} | {_f(p['matched_fraction'], pct=True)} | {_f(p['accuracy'], pct=True)} | "
                   f"{_f(p['accuracy_given_match'], pct=True)} | {p['failed_trajectories']}/{p['trajectories']} |")
    return "\n".join(out)+"\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["run", "analyse", "all"])
    parser.add_argument("--output", type=Path, default=Path("results/calibration_study"))
    parser.add_argument("--models", nargs="+", default=list(DEFAULT_MODELS),
                        choices=["baseline", "motion", "robust", "bias"])
    parser.add_argument("--draws", type=int, default=1000)
    args = parser.parse_args()
    if args.command in ("run", "all"):
        run_study(args.output, args.models)
    if args.command in ("analyse", "all"):
        analyse(args.output, args.draws)


if __name__ == "__main__":
    main()
