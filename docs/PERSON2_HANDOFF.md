# Update: optional models implemented

The original baseline interface below remains supported. `Config.model` now selects baseline/motion/robust/bias. See IMPROVEMENTS.md for additional parameters and comparisons. Rows additionally export state_count, selected_x, selected_y, bias_x and bias_y. candidate_count counts unique physical segments; state_count includes offset hypotheses. Raw nearest-road matching always uses uncorrected observations. Use selected_x/y to plot inferred positions in bias mode; reprojecting raw GPS would plot the wrong hypothesis. These are model-estimated offsets, not known simulator errors. Calibration remains Person 2 work.

# Person 2 handoff: evaluation, calibration and demo

This document defines the second person's ownership, the inspected Part 1 interface and the checks required before the complete research project is finished. The commands and output schema below refer to the implemented code.

## Ownership boundary

Person 1 owns synthetic roads and journeys, observation corruption, candidate generation, routing, HMM score construction, Viterbi and forward-backward inference. Person 2 owns the experiment runner, confidence evaluation, calibration comparison, results analysis and local demo. Both should understand the complete pipeline for the viva.

Person 2 must consume the core outputs rather than duplicate the HMM or change predictions inside evaluation. If a core bug is found, report it, fix it explicitly and regenerate affected results.

## Work in order

1. Reproduce the supplied example and run the core correctness checks.
2. Validate the output schema, units and segment-label convention.
3. Group complete trajectories into development, calibration and test sets. Keep related variants of a route together when evaluating route generalisation.
4. Implement metrics independently of the matcher: assignment accuracy, unmatched rate, candidate recall, correctness Brier score, log loss and reliability diagrams.
5. Build risk-coverage curves for raw posterior and entropy scores. Compare methods at matched coverage.
6. Fit one small calibration mapping using calibration journeys only. Compare fitting on independent noise with fitting on a mixture of error types.
7. Evaluate both mappings on untouched test journeys, including burst errors. Preserve unsuccessful conditions and negative results.
8. Summarise multiple seeds. Resample whole trajectories for uncertainty intervals because observations within one journey are correlated.
9. Add a local demo that calls the existing pipeline and displays its actual predictions.
10. Write results, limitations and discussion; assemble reproducible figures and tables for the report.

## Evaluation rules that must stay consistent

- Segment accuracy is not full reconstructed-route accuracy.
- Confidence must refer to the same segment label used to score correctness. Aggregate candidate probabilities if multiple candidates represent one evaluated segment.
- Candidate recall means the true segment was available; it does not mean the exact true continuous position was available.
- Missing candidates and broken chains must remain visible. An algorithm cannot gain apparent quality by silently dropping failures.
- Coverage uses all attempted observations as its denominator. Risk is undefined when no observations are accepted.
- Keep overall accuracy, accepted risk and coverage together.
- State how junction points and opposite directions are labelled.
- Ground truth is available to evaluation but never to candidate generation or inference.
- Hyperparameters, calibration and thresholds must not be fitted on final test journeys.

## Calibration is not automatically improved rejection

A monotonic mapping of confidence can improve Brier score and probability interpretation while preserving the ranking. Therefore it generally leaves the risk-coverage curve unchanged, apart from tie effects. Do not claim better rejection merely because numerical confidence changes.

If improved ranking is investigated, treat an extra correctness predictor using residuals, entropy or candidate count as a separate supervised method with separate validation. This is optional, not required for the first completed project.

## Minimum demo

Show roads, simulated ground truth, GPS observations, predicted segments and rejected observations. Controls should cover noise scale, burst length and confidence threshold. Display accuracy, coverage, accepted risk, candidate recall and failure rate. Mark the system as offline and synthetic. Include a reproducible seed and explain that future observations contribute to forward-backward confidence.

## Completion checklist

- [ ] Reproduced a Part 1 run and tests.
- [ ] Frozen and documented trajectory splits and seeds.
- [ ] All failures counted explicitly.
- [ ] Raw and calibrated probability metrics reported separately from rejection ranking.
- [ ] Noise magnitude reported when comparing independent and burst errors.
- [ ] Results include several trajectories and seeds.
- [ ] Demo uses the same inference code as experiments.
- [ ] Report makes no unsupported novelty or performance claims.

## Implemented Part 1 interface

The implementation uses four compact modules rather than every proposed file in the original guide:

| Module | Implemented responsibility |
|---|---|
| gpsmatch/roads.py | Straight-segment directed map, projection, shortest paths and partial-edge distances |
| gpsmatch/simulation.py | Six route variants, timestamped ground truth and observation corruption |
| gpsmatch/inference.py | Variable-width, log-space Viterbi and forward-backward |
| gpsmatch/pipeline.py | Config, matcher, evaluation rows and summary metrics |

The callable API is:

```python
from gpsmatch.pipeline import Config, run_pipeline

result = run_pipeline(Config(noise_kind="burst", burst_points=10), seed=42)
rows = result["rows"]
metrics = result["metrics"]
```

The lower-level matcher is `match(roads, times, observations, config)`. It receives only the road map, timestamps and observed coordinates. Ground truth is introduced afterwards when building evaluation rows.

### Configuration fields

| Field | Meaning | Default |
|---|---|---:|
| noise_kind | independent, burst, matched_iid or gap | independent |
| noise_sigma | Per-axis independent Gaussian noise scale, metres | 8 |
| assumed_sigma | Matcher's emission scale, metres | 8 |
| transition_beta | Route/observed distance mismatch scale, metres | 15 |
| candidate_radius | Projection search radius, metres | 60 |
| max_speed | Base transition travel-speed limit, metres/second | 35 |
| projection_slack_sigma | Nonnegative multiplier for projection-noise distance slack | 3 |
| road_separation | Distance between parallel roads, metres | 20 |
| sample_interval | Time between generated samples, seconds | 1 |
| speed | Simulated constant travel speed, metres/second | 8 |
| burst_offset | Vertical offset during the central burst, metres | 20 |
| burst_points | Requested central burst length in observations | 10 |
| gap_points | Requested central dropped-observation count | 6 |
| route_variant | Route index; six routes cycle modulo six | 0 |

For a fair burst-versus-independent comparison, use `matched_iid` with the same seed and remaining configuration as `burst`. Its random errors are rescaled to exactly match that burst trajectory's empirical radial RMSE. Rescaling fixes overall energy, so this is a controlled magnitude-matched reference rather than a claim of perfectly independent samples after normalisation. It does not reproduce the burst's directional distribution or tails.

### Top-level return fields

| Field | Type and meaning |
|---|---|
| config | Dictionary of configuration values |
| seed | Seed used for independent truth/noise random streams |
| trajectory_id | Identifier includes noise kind, route variant, seed and a ten-character SHA-256 configuration hash; retain it when combining experiment variants |
| rows | One evaluation dictionary per retained observation |
| metrics | Summary values described below |
| failure | Failure explanation, or null on a successful complete trajectory |
| roads | In-memory RoadMap object; not directly JSON serialisable |

### Pointwise row schema

| Fields | Meaning |
|---|---|
| trajectory_id, timestamp | Identity and retained observation time in seconds |
| true_x, true_y | True coordinates, metres |
| gps_x, gps_y | Observed coordinates, metres |
| true_segment | Physical segment label, without travel direction |
| true_directed_edge | Ground-truth direction-specific edge ID |
| burst | Whether this retained observation belongs to the simulated burst |
| candidate_count | Number of physical-segment projections; opposite directed edges are deduplicated |
| true_segment_present | Whether any candidate represents the true physical segment |
| nearest_segment, nearest_correct | Closest available segment and its correctness |
| selected_segment, selected_directed_edge | Viterbi-selected physical segment and its canonical edge representation; the latter is not inferred heading |
| confidence | Posterior mass aggregated over the selected physical segment |
| entropy | Physical-segment posterior entropy divided by log(number of distinct candidate segments), or zero for one segment |
| correct | Selected physical segment equals true_segment |
| status | matched or unmatched |

Candidate generation deduplicates opposite directed edges to one projection per physical segment. Each candidate stores a canonical edge and offset for geometry; selected_directed_edge is that representation ID, not an inferred travel direction. Routing permits departure and arrival through either legal direction of a bidirectional segment. It respects one-way connectivity when no reverse edge exists, but does not enforce heading continuity, turning restrictions or no-U-turn rules. Candidate count, confidence, entropy, candidate recall and main correctness are all physical-segment quantities. true_directed_edge remains simulator truth and must not be compared with selected_directed_edge as a direction-accuracy metric.

On failure, selected labels are empty strings, confidence and entropy are null, and correct is false. The current pipeline marks the entire trajectory unmatched if even one observation has no candidate or no complete feasible path exists. It does not yet recover separate chain fragments. Nearest-road predictions can still be available on individual observations in such a failed trajectory.

### Summary metrics

| Metric | Definition |
|---|---|
| points | Number of retained observations after any simulated gap |
| matched_fraction | Matched observations divided by retained observations |
| hmm_accuracy | Correct matched assignments divided by all retained observations; failures contribute zero correct |
| hmm_accuracy_given_match | Correctness among matched observations only; null if none |
| nearest_accuracy | Correct nearest-road assignments divided by all retained observations |
| candidate_recall | True physical segment present divided by all retained observations |
| brier_given_match | Binary correctness Brier score on matched observations only |
| gps_rmse | Radial coordinate error RMSE in metres |
| runtime_seconds | End-to-end generation, matching and summary runtime |

A simulated gap removes observations from the evaluation rows; it does not create unmatched rows at missing timestamps. Coverage therefore concerns retained GPS observations, not all latent positions along a journey. Preserve the larger timestamp difference over a gap.

For end-to-end reporting, do not present brier_given_match alone: accompany it with matched_fraction and hmm_accuracy. Calibration fitting must exclude null scores explicitly and explain its population.


## Setup and reproducible commands

Run from the project root in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m gpsmatch demo --seed 42 --output results/demo
.\.venv\Scripts\python.exe -m gpsmatch benchmark --seed 42 --seeds 30 --output results/benchmark_with_slack
```

The same commands can use `python` when an environment with the requirements is already selected. The core requirements are NumPy, SciPy and Matplotlib. Calibration and a web demo are not yet implemented or included as dependencies.

The demo command writes independent, burst and gap examples. Each condition directory contains `predictions.csv` and `summary.json`; the parent directory contains `comparison.png`. Summary JSON includes the configuration, seed, trajectory ID, metrics, failure explanation and Python/library versions.

The benchmark command writes independent, burst, matched_iid and gap runs. Each condition has a `seed_<number>` directory containing its own predictions and summary. Root `aggregate.json` contains pooled point metrics, trajectory count, failed-trajectory count, average trajectory accuracy, mean radial GPS RMSE and mean runtime. It cycles through six route variants as seeds increase.

Use a fresh output directory for a new experiment configuration; existing filenames are overwritten. The initial benchmark is a core sanity study, not a final held-out research evaluation. It does not yet perform train/calibration/test splits, probability calibration, reliability diagrams, risk-coverage curves or trajectory-bootstrap intervals. These are Person 2's work.

CSV booleans are textual True/False, and null confidence fields are blank. Parse them explicitly when loading CSV; do not treat the nonempty text False as a truthy boolean. JSON booleans and nulls retain their native types. A row's timestamp is numeric seconds, not a wall-clock date.

`comparison.png` shows candidate assignments as point markers. It does not reconstruct and display every shortest-path connector between observation candidates; do not describe it as complete route reconstruction.



## Current screening rule and checked benchmark

Projected candidates contain positional error, so a strict distance <= max_speed * elapsed_time screen can reject otherwise useful trajectories. The current default permits:

```text
network_distance <= max_speed * elapsed_time
                    + projection_slack_sigma * sqrt(2) * assumed_sigma
```

The default slack multiplier is 3. Setting it to zero restores strict screening. This is a heuristic tolerance for projection uncertainty, not a guarantee that inferred motion is physically exact or a probabilistic confidence bound. It does not change disconnected paths into connected paths. Person 2 should include a sensitivity check for this choice before making final research claims.

The current default benchmark is `results/benchmark_with_slack/aggregate.json`, using seeds 42 through 71: 30 trajectories per condition, 120 total. Every trajectory matched and candidate recall was 100% in these runs. The existing `results/benchmark` folder records an earlier strict-screening development run with failures; do not mix it into the current-default results.

| Condition | HMM segment accuracy | Nearest accuracy | Correctness Brier | Mean GPS RMSE, m |
|---|---:|---:|---:|---:|
| Independent | 89.71% | 81.57% | 0.0637 | 11.29 |
| Burst | 82.27% | 73.70% | 0.1060 | 15.11 |
| Magnitude-matched independent | 84.95% | 74.91% | 0.0768 | 15.11 |
| Gap | 88.11% | 80.94% | 0.0748 | 11.19 |

These figures are taken from that saved aggregate, not a claim of held-out research performance. They demonstrate a functioning pipeline and motivate the calibration study. The burst and magnitude-matched control have equal empirical mean RMSE but differ in more than correlation, including directional structure. The parent implementation run reports 18 passing core tests; rerun the test command in your own environment before extending it.
