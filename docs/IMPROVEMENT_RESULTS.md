# Improvements: measured results and reproduction

## Implemented
- baseline: original Gaussian/observed-distance candidate lattice, preserved as default.
- motion: GPS-only multi-lag median motion estimates, time-aware movement compatibility and displacement-direction penalty.
- robust: motion model plus an isotropic two-dimensional Student-t emission kernel (df=4).
- bias: motion model plus a persistent discrete two-dimensional offset state. GPS is corrected under each hypothesis before projection. Marginals are summed across offsets for road confidence.

See IMPROVEMENTS.md for equations and assumptions. No neural training or extra packages are required.

## Verification
29 unit tests pass. New checks cover exact enumeration of an augmented lattice, vectorised-versus-scalar directed routing, zero-bias-grid equivalence to motion, bias-aware candidate generation, paired observations across models, robust tails, baseline regression and boolean correctness metrics. Compilation passed. The bias demo and model comparison plots were generated and inspected.

## Experimental protocol
Development: six seeds (1000–1005), nine scenarios, 54 trajectories, 216 model runs, road separation 20 metres.
Evaluation: twelve different seeds (10000–10011), nine scenarios, 108 trajectories, 432 model runs. Road separation cycles through 16, 24 and 32 metres. Model settings were frozen before evaluation.

The same 4,140 observed positions are evaluated for each model in evaluation, or 16,560 model-point predictions total. Every case asserts identical GPS coordinates, timestamps and truth across models. All evaluation trajectories matched, with 100% candidate recall.

Nine scenarios: independent noise; positive, negative, diagonal, off-grid, long and start-of-trace bursts; RMSE-matched independent noise; missing observations. Routes still use six small synthetic families. This is held-out noise/spacing evaluation, NOT unseen-topology or real-world validation.

The runner writes a manifest before inference and refuses to overwrite it. Seeds are grouped by trajectory. Scenario-level bootstrap intervals resample paired whole-trajectory accuracy differences. Reusing seed ranges is not automatically forbidden by the CLI, so inspect manifests.

## Evaluation results

| Model | Segment accuracy | Brier score ↓ | Binary log loss ↓ | Wrong assignments with confidence ≥0.9 | Mean runtime/trajectory |
|---|---:|---:|---:|---:|---:|
| Baseline | 82.54% | 0.11313 | 0.56156 | 143 | 0.034 s |
| Motion | 87.85% | 0.10016 | 0.58482 | 152 | 0.034 s |
| Robust | 88.74% | 0.09544 | 0.41355 | 120 | 0.033 s |
| Bias-aware | 83.33% | 0.11484 | 0.36119 | 61 | 0.420 s |

These are pooled pointwise metrics. The report does not assert a universal or statistically significant improvement from the pooled values alone. Scenario-specific paired intervals are saved in comparison.json.

Motion improves road accuracy but its log loss and confident-wrong count worsen overall. This is why accuracy alone is insufficient.

Robust improved both overall accuracy and the two probability-error metrics on this evaluation. It is the recommended general-purpose option from these tested variants. It did not win every individual scenario.

Bias-aware is experimental: on long bursts it reached 81.6% versus 64.5% for baseline, but worsened several other scenarios and was about 13 times slower than robust. The initial near-zero bias prior can disadvantage traces beginning inside a burst. Road identity and bias can be intrinsically ambiguous. Better log loss does not mean every calibration measure improves: its Brier score was slightly worse than baseline.

These numbers should not be directly compared with the earlier 120-trajectory benchmark's 89.7% baseline figure: this evaluation contains harder scenarios and different geometry/seeds.

## Files
- results/improvements_development_v2: complete development results.
- results/improvements_evaluation/manifest.json: pre-evaluation settings and case identities.
- results/improvements_evaluation/comparison.json: aggregates and scenario-level paired intervals.
- results/improvements_evaluation/comparison.png: accuracy/Brier plots.
- Scenario/seed/model subdirectories: predictions.csv and summary.json.
- results/improvements_development: interrupted earlier run after an aggregate-metric dtype error; not a complete result set. The fixed metric is regression-tested.

## Reproduce
From the GPS project directory:

    python -m unittest discover -s tests -v
    python -m gpsmatch demo --model robust --output results/robust_demo_new
    python -m gpsmatch.compare --split evaluation --first-seed 20000 --seeds 12 --output results/comparison_new

Use a fresh output directory. For exact replay, use the stored manifest's seeds and configuration with another fresh output folder.

## What remains for Person 2
Fit calibration on separate labelled trajectories, plot reliability and risk–coverage, evaluate threshold transfer, expand map/route diversity, and build the interactive demo. Raw model confidence is not guaranteed calibrated. Keep the baseline and all alternatives, including negative results.
