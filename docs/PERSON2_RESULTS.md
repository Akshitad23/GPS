# Person 2: evaluation, calibration and demo results

All numbers below come from `results/calibration_study/results.md` (auto-generated from `results.json`; manifest SHA-256 recorded there). They describe a small synthetic study, not real GPS data.

## What was built

| File | Role |
|---|---|
| `gpsmatch/evaluation.py` | Metrics that only read evaluation rows: accuracy, unmatched rate, candidate recall, Brier, log loss, ECE, reliability tables with counts, tie-aware risk–coverage, risk at matched coverage, threshold selection/transfer, journey-group bootstrap, explicit CSV boolean parsing and schema checks |
| `gpsmatch/calibration.py` | Platt map `sigmoid(a·logit p + b)` (2 parameters) and isotonic (PAV) map |
| `gpsmatch/study.py` | Frozen protocol, runner (manifest written before inference, never overwritten), analysis, figures, Markdown tables |
| `gpsmatch/demo_server.py`, `gpsmatch/demo_static/index.html` | Local offline demo; every request calls `run_pipeline` |
| `tests/test_evaluation.py` | 11 tests: metric definitions, ties, failure denominators, CSV round-trip agreement with pipeline metrics, calibrator monotonicity/order preservation, demo uses pipeline predictions |

Reproduce:

```powershell
python -m unittest discover -s tests -v                              # 40 tests
python -m gpsmatch.study all --output results/calibration_study_new  # fresh directory
python -m gpsmatch.demo_server                                       # http://127.0.0.1:8765
```

## Protocol (frozen in code and in `manifest.json`)

- **Journey group = one seed.** All noise scenarios of a seed share the same simulated truth (route, start phase). The run asserts this. Groups never cross splits, and bootstrap intervals resample whole groups (1000 draws), not points.
- **Splits:** development seeds 40000–40011 (12 groups), calibration 50000–50035 (36), test 60000–60035 (36). These are disjoint from every earlier result folder. Route variant = index mod 6, so each split covers all six routes equally. Road separation is 20 m.
- **Scenarios per group:** `independent`, `burst` (20 m, 10 points), `burst_diagonal` (28 m at 45°), `burst_negative` (25 m at −90°), `burst_long` (28 m, 18 points, starting at 30%), `matched_iid` (RMSE matched to `burst`), `gap`.
- **Models:** baseline (the project default) and robust (recommended by the improvements study). Predictions are consumed unchanged.
- **Calibration fits use calibration journeys only:**
  - *independent:* the 36 independent-noise journeys.
  - *mixture:* 36 journeys of equal size. Group i uses `[independent, independent, burst, burst_diagonal][i mod 4]`.
  - Both used 1,390 matched rows; 0 unmatched rows were excluded.
  - `burst_negative` and `burst_long` appear in neither fit, so they are unseen burst types at test time.
- **Development split** is used only for the screening-slack sensitivity check and sanity checks. Nothing was tuned on test.

### Labelling conventions

- Correctness and confidence both refer to the **physical segment**. The direction suffix is ignored: `m0+` and `m0-` are both segment `m0`.
- Confidence is the posterior mass summed over all candidates of that segment.
- Junction points are labelled by the simulator's truth edge at that time. The start phase is random, so points rarely lie exactly on a node.
- `selected_directed_edge` is never scored as heading.

### Failures

- Unmatched rows stay in every accuracy and coverage denominator, are never accepted, and are excluded from probability metrics. Their count is reported alongside.
- In the main study, **0 of 1,176 trajectory runs failed**, and candidate recall was 100% everywhere. Failures appear only in the slack sensitivity check below.

## Noise magnitude (test)

| Scenario | Mean radial RMSE (m) | RMSE inside burst (m) |
|---|---:|---:|
| independent | 11.29 | – |
| burst | 15.42 | 23.45 |
| matched_iid | 15.42 | – |
| burst_negative | 16.79 | 26.77 |
| burst_diagonal | 18.44 | 30.69 |
| burst_long | 22.33 | 30.34 |
| gap | 11.33 | – |

## Results

### 1. Bursts hurt more than their error energy explains

Values are test accuracy over all observations, with 95% journey-bootstrap CIs.

| Scenario | Baseline | Robust | Nearest road |
|---|---|---|---:|
| independent | 89.7% [88.3, 91.1] | 93.9% [92.7, 95.0] | 82.5% |
| burst | 80.3% [74.2, 85.7] | 89.2% [85.4, 92.5] | 73.7% |
| matched_iid (same RMSE as burst) | 85.0% [82.9, 87.0] | 92.5% [90.9, 94.0] | 74.4% |
| burst_negative | 73.6% [66.0, 80.7] | 78.5% [71.0, 85.4] | 72.8% |
| burst_long | **61.3%** [51.6, 71.0] | **64.0%** [53.0, 74.4] | **65.3%** |
| gap | 87.8% [86.1, 89.5] | 92.7% [91.4, 94.0] | 81.2% |

- At equal empirical RMSE, the persistent burst lowers baseline accuracy by about 5 points compared with `matched_iid`.
- The two conditions also differ in directional structure, not only in correlation over time, so this is not a pure correlation effect.
- **Negative result:** on long bursts, both HMMs fall to roughly nearest-road accuracy. The baseline is slightly below nearest road, although the CIs overlap. The temporal model follows the shifted trace onto the parallel road and stays there.

### 2. Raw confidence is reasonably calibrated under independent noise but confidently wrong in long bursts

Baseline, test, matched rows only. The matched fraction is 100% in every condition.

| Scenario | Brier | Log loss | ECE |
|---|---:|---:|---:|
| independent | 0.061 | 0.19 | 0.041 |
| burst | 0.112 | 0.39 | 0.039 |
| burst_negative | 0.184 | 0.87 | 0.125 |
| burst_long | 0.292 | 2.18 | 0.244 |

In `burst_long`, the bin with confidence ≥ 0.9 holds most of the points but only about 68% are correct (`figures/reliability_baseline.png`).

### 3. Calibration helps only when the fit population matches the test errors

The table shows the change in test Brier score compared with raw confidence, with a paired journey-bootstrap 95% CI. A negative change is an improvement.

| Test scenario | Platt fit on independent | Platt fit on mixture | Isotonic fit on mixture |
|---|---|---|---|
| **Baseline:** independent | −0.003 [−0.005, −0.001] | +0.015 [+0.013, +0.017] | +0.006 [+0.005, +0.008] |
| **Baseline:** burst_long (unseen) | +0.010 [+0.006, +0.015] | −0.021 [−0.036, −0.006] | −0.019 [−0.030, −0.008] |
| **Baseline:** all test | +0.003 [+0.001, +0.005] | +0.003 [+0.000, +0.007] | −0.002 [−0.004, +0.001] |
| **Robust:** independent | −0.011 [−0.015, −0.006] | −0.001 [−0.005, +0.002] | −0.006 [−0.008, −0.003] |
| **Robust:** burst_long (unseen) | +0.029 [+0.012, +0.047] | −0.012 [−0.018, −0.005] | −0.006 [−0.011, −0.001] |
| **Robust:** all test | +0.002 [−0.002, +0.007] | −0.003 [−0.006, +0.000] | −0.003 [−0.006, −0.001] |

**Fit on independent noise:**

- For the baseline, the fitted Platt slope is a = 1.55 > 1, so the map makes confidence *sharper*.
- This improves independent and gap journeys.
- It worsens every burst scenario, because it makes already-overconfident burst errors more extreme.

**Fit on the mixture:**

- For the baseline, the slope is a = 0.30, which flattens confidence.
- This helps the unseen long and negative bursts.
- It costs calibration on clean journeys.

**Pooled over all test journeys:**

- No map gives a clear Brier gain for the baseline.
- Isotonic-mixture halves ECE (0.066 → 0.033).
- Platt-mixture cuts log loss from 0.64 to 0.43.
- For robust, isotonic-mixture gives a small significant Brier improvement (−0.003).

**Conclusion:** one global post-hoc map cannot be right for both the clean and the burst regimes. The best map depends on which error regime it was fitted on.

### 4. Calibration does not improve rejection

| Test risk at 80% coverage (baseline) | raw | 1 − entropy | Platt-mixture | Isotonic-mixture |
|---|---:|---:|---:|---:|
| independent | 0.014 | 0.023 | 0.014 | 0.017 |
| burst | 0.100 | 0.115 | 0.100 | 0.117 |
| burst_long | 0.331 | 0.348 | 0.331 | 0.331 |
| all test | 0.112 | 0.125 | 0.112 | 0.112 |

**Platt maps:**

- Platt maps are strictly increasing (a > 0), so risk at every matched coverage is identical to raw confidence.
- AURC differs only slightly, for example 0.0862 vs 0.0883 pooled. This is a tie effect: confidences within 1e-6 of 1 are clipped together before the logit.

**Isotonic maps:**

- Isotonic maps merge scores into steps, which creates ties.
- This makes some operating points *worse*. For example, baseline independent risk at 60% coverage rises from 0.001 to 0.013.

**Entropy:**

- 1 − entropy is never clearly better than the raw posterior.
- Its AURC is slightly worse in every scenario.

None of these scores fixes `burst_long`: its accepted risk stays at about 32% even at 50% coverage.

### 5. Rejection thresholds do not transfer from clean to bursty journeys

The threshold was chosen on calibration journeys to give 5% accepted risk, then applied to test.

**Baseline, threshold fitted on independent journeys (t = 0.542):**

| Test scenario | Coverage | Accepted risk |
|---|---:|---:|
| independent | 86% | 3.2% |
| matched_iid | 85% | 7.0% |
| burst | 84% | 12.5% |
| burst_negative | 84% | 20.0% |
| burst_long | 85% | 33.9% |

**Baseline, threshold fitted on the mixture (t = 0.979):**

| Test scenario | Coverage | Accepted risk |
|---|---:|---:|
| independent | 57% | 0.0% |
| burst | 49% | 3.2% |
| burst_long | 55% | 32.2% |

The robust model shows the same pattern. See `figures/threshold_transfer_*.png`.

- **Fitting on the mixture:** the threshold becomes conservative on known error types and gives up about 30 points of clean coverage.
- **Unseen long bursts:** the risk is still several times the target.
- **Coverage stays stable even when risk explodes,** so a confidence threshold cannot detect the regime change by itself.

### 6. Route hold-out (secondary)

Calibrators were fitted on routes 0–2 and tested on routes 3–5. The reversed and crossing routes behaved like calibrators fitted on all routes. For example, baseline Platt-independent on independent test journeys scored Brier 0.0595 in both cases. Route families here are few and similar, so this is weak evidence only.

### 7. Screening-slack sensitivity (development, baseline)

**Slack multiplier 0 (strict screening):**

- 3 of 12 journeys fail entirely in each non-gap scenario, and 2 of 12 in gap.
- Failures lower end-to-end accuracy, for example 68.1% vs 90.3% on independent.
- Accuracy among matched journeys is unchanged.

**Slack multiplier 1–5:**

- 0 failures in every scenario.
- Independent accuracy is stable at 90.3–90.5%.
- Burst accuracy varies between 83.4% and 87.3% without a trend. With only 12 development journeys, this is noise.

The default multiplier of 3 is therefore not critical. Some slack is necessary.

## Limitations

- Synthetic straight-segment map with two parallel roads, six route families and one road spacing (20 m). There is no real GPS data, no unseen topology, and no turning or heading constraints.
- Burst types are a hand-picked set of constant offsets. "Unseen" burst types still come from the same simulator.
- Confidence is offline forward–backward smoothing that uses future observations, so it is not usable for real-time rejection.
- The calibration population is small: 1,390 matched rows, with very few low-confidence points (see the histograms). Bins below 0.3 contain fewer than 10 points.
- Calibrators were not re-fitted per seed block. Uncertainty comes from journey bootstrap over one frozen test set.
- Gaps remove observations. Coverage is over retained GPS points, not over the whole journey.

## Claims the report should and should not make

**Supported:**

- Persistent bursts degrade segment accuracy more than RMSE-matched independent noise.
- Raw HMM confidence becomes confidently wrong in long bursts.
- Monotonic calibration changes probability quality but not rejection ranking.
- Which fit population is best depends on the error regime.
- Thresholds tuned on clean journeys do not transfer to bursty ones.

**Not supported:**

- Any improvement in rejection from calibration.
- Any real-world accuracy figure.
- Any novelty claim beyond this controlled synthetic comparison.

## Demo

`python -m gpsmatch.demo_server` serves a local page labelled OFFLINE · SYNTHETIC.

**Display:**

- Roads, simulated truth, GPS points (bursts ringed) and the selected segment positions.
- Accepted points are coloured as correct or wrong; rejected and unmatched points have their own colour.
- A confidence-over-time strip shows the threshold line.

**Controls:**

- Model, noise kind, route, seed (with a Next button).
- Noise σ, burst length, burst offset and burst direction.
- Raw or calibrated score, and the acceptance threshold.

**Tiles:** accuracy (plus nearest-road accuracy), coverage, accepted risk (shown as "undefined" when nothing is accepted), candidate recall, failure rate and GPS RMSE.

The calibrated option loads `results/calibration_study/calibrators_<model>.json` (the Platt mixture fit). It changes only the score, never the selected segment.

A good live example is seed 42, burst, 20-point burst, threshold 0.9. About 62% of points are accepted with about 65% accepted risk, which shows confident errors directly.

## Output files

`results/calibration_study/`:

- `manifest.json`
- `predictions/{split}_{model}.csv`, which includes the extra columns `split`, `scenario`, `seed`, `group`, `route_variant` and `model`
- `predictions/development_slack_sensitivity.csv`
- `trajectories.csv` (per-run failure text, RMSE and runtime)
- `calibrators_{model}.json`
- `results.json`, `results.md`
- `figures/`: `reliability_*`, `risk_coverage_*`, `threshold_transfer_*` and `calibration_maps_*`, each as a PNG per model
