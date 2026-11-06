# Project status

Reviewed on 5 November 2026.

Project title: Confidence-Aware HMM-Based Map Matching Under Bursty GPS Errors.

## Research question

How do persistent GPS error bursts affect road-segment assignments and their confidence? Can a calibration mapping fitted on separate labelled journeys improve the interpretation of confidence and the transfer of rejection thresholds?

The project is an undergraduate probabilistic graphical models study. Its core is an offline HMM-style candidate lattice on a small synthetic road network. Forward-backward confidence uses the complete journey, including future observations.

## Implemented code

| File | Responsibility |
|---|---|
| gpsmatch/roads.py | Road geometry, segment projections and legal shortest distances including partial edges |
| gpsmatch/simulation.py | Six legal route families, independent noise, persistent-offset bursts, magnitude-matched controls and timestamp-preserving gaps |
| gpsmatch/inference.py | Log-space Viterbi and forward-backward on variable-width lattices |
| gpsmatch/pipeline.py | Configuration, public API, physical-segment confidence, entropy and evaluation rows |
| gpsmatch/models.py | GPS-derived motion, Student-t emissions and persistent discrete bias alternatives |
| gpsmatch/compare.py | Paired comparisons, saved manifests, aggregate metrics and trajectory bootstrap intervals |
| gpsmatch/__main__.py | Demo and benchmark commands, CSV/JSON export and static plots |

`run_pipeline(Config(...), seed=...)` is the public API. `match` receives the map, observed coordinates and timestamps. Evaluation adds ground truth afterwards. Physical segments are the correctness labels; the selected canonical edge does not estimate travel heading. Bias-mode confidence sums posterior mass across offset hypotheses for the selected segment.

The four models are baseline, motion, robust and bias. Baseline remains the default. Robust combines GPS-derived motion with Student-t emissions. Bias adds a persistent two-dimensional offset hypothesis and corrects coordinates before projection.

## Verified results

`python -m unittest discover -s tests -v` passed all 29 tests during this review. Checks cover exact small-lattice inference, numerical stability, routing, reproducibility, failure reporting and model variants.

The completed evaluation in `results/improvements_evaluation` contains 108 trajectories per model across nine scenarios, or 432 model runs. Each model has 4,140 evaluated observations. Seeds are 10000 through 10011, and road spacing varies across 16, 24 and 32 metres. The six route families are reused.

During this review, accuracy, binary correctness Brier score and binary log loss were recomputed from all evaluation prediction CSVs with explicit boolean parsing. They agree with `comparison.json` within an absolute tolerance of 1e-12.

| Model | Segment accuracy | Brier score | Binary log loss | Wrong with confidence at least 0.9 |
|---|---:|---:|---:|---:|
| Baseline | 82.54% | 0.11313 | 0.56156 | 143 |
| Motion | 87.85% | 0.10016 | 0.58482 | 152 |
| Robust | 88.74% | 0.09544 | 0.41355 | 120 |
| Bias | 83.33% | 0.11484 | 0.36119 | 61 |

All saved evaluation runs matched, with 100% segment candidate recall. These values describe this synthetic evaluation. They do not establish performance on real GPS data or unseen road topology. Robust has the highest pooled accuracy among these variants, but its high-confidence errors still require study.

`results/improvements_development_v2` is the completed model-development comparison. `results/improvements_development` is an interrupted older run. `results/benchmark` preserves earlier strict-screening failures; `results/benchmark_with_slack` is the later baseline development benchmark. Keep these result sets distinct and preserve existing manifests.

## Remaining work

1. Freeze a calibration-study protocol with separate development, calibration and test trajectory groups. Keep related noise variants together. Existing inspected evaluation results can inform development, but new final claims need fresh test data after the protocol is fixed.
2. Evaluate raw posterior confidence and entropy with reliability diagrams, bin counts, risk-coverage curves and uncertainty intervals that resample whole journey groups.
3. Fit a small calibration mapping on independent-noise journeys and another on a mixture of independent and burst-noise journeys. Evaluate both on the same untouched test groups.
4. Report probability quality separately from ranking. A monotonic calibration mapping generally preserves ranking and does not by itself improve rejection at matched coverage.
5. Build a local interactive demo that calls the existing pipeline and displays truth, GPS, assignments and rejected points. Include seed, noise, burst and threshold controls, plus accuracy, coverage, accepted risk, candidate recall and failure rate.
6. Assemble the report, figures and viva material from the resulting measurements. Broader maps and real-data validation are extensions.

Failures must remain in coverage denominators. Risk is undefined when nothing is accepted. Probability metrics exclude unmatched rows with null scores and must be accompanied by match rates. Gaps remove observations, so coverage concerns retained GPS points. The current matcher marks a whole journey unmatched if no complete path exists.

## Context sources

The review covered README.md, all Python source and test files, the learning guide, implementation and validation notes, Person 2 handoff, local continuation handoff, model-improvement notes and saved evaluation outputs.

The supplied shared-chat URL returned a preview page without conversation messages through the available retrieval methods. Its conversation content has not been read. `docs/LOCAL_HANDOFF.md` supplies the local continuation context; `docs/PERSON2_HANDOFF.md` specifies the unfinished calibration and demo work.
