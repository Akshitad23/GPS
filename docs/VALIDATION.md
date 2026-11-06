# Part 1 development validation

Date: 25 October 2026.

## Scope
Implemented synthetic straight-segment maps, legal truth journeys, independent and persistent-offset GPS errors, missing observations, candidate projection, directed graph routing with partial edges, nearest-segment baseline, log-space Viterbi and forward–backward, segment-level confidence and entropy, export and static plotting.

## Validation
18 unittest checks pass. Tests include exhaustive variable-width lattice enumeration, the learning-guide example, a 1,000-observation numerical stability case, impossible paths, one-way partial-edge routing, bidirectional jitter, projection, six noiseless routes under a sharp assumed emission model, deterministic seeds, gap timestamps, matched RMSE, candidate exclusion, confidence bounds, invalid inputs, configuration-specific IDs and projection-slack regression.

Run: python -m unittest discover -s tests -v

## Current development benchmark
Command: python -m gpsmatch benchmark --seeds 30 --output results/benchmark_with_slack

30 trajectories per condition. Six route templates cycle across seeds 42–71. Road separation 20 m; baseline noise per-axis sigma 8 m; burst adds +20 m in y for 10 points. Assumed emission sigma 8 m. See each saved summary.json for exact config and versions.

| Condition | Points | Nearest accuracy | HMM accuracy | Brier (assignment correctness) | Failed trajectories |
|---|---:|---:|---:|---:|---:|
| Independent | 1156 | 81.57% | 89.71% | 0.06371 | 0/30 |
| Burst | 1156 | 73.70% | 82.27% | 0.10596 | 0/30 |
| RMSE-matched independent | 1156 | 74.91% | 84.95% | 0.07680 | 0/30 |
| Gaps | 976 | 80.94% | 88.11% | 0.07477 | 0/30 |

Candidate recall was 100% for these conditions. Deliberate exclusion is tested separately and produces explicit failure.

Burst and matched-independent conditions have the same empirical coordinate RMSE per seed: mean 15.1076 m. This isolates magnitude only partially; direction, tails and relation to geometry still differ. The fixed +y burst is not always directed toward an alternative road on all route templates.

Burst rows include 205 wrong segment assignments, 36 with raw confidence at least 0.9. This motivates further study; it does not establish novelty or provide a full calibration analysis.

## Development fixes
1. Initially, directed-candidate heading assumptions treated projected GPS jitter as illegal reverse movement. Replaced states with one physical-position candidate per segment. Routing uses available legal entry and exit directions; no heading persistence is inferred.
2. A strict speed screen caused failures on noisy projected positions. Added the explicit heuristic allowance projection_slack_sigma * sqrt(2) * assumed_sigma, default multiplier 3. This is not a formal confidence bound.
3. Retained strict-screen development outputs in results/benchmark. Current outputs are results/benchmark_with_slack.
4. Appended a configuration hash to trajectory IDs to distinguish parameter variants.

## Interpretation limits
The same development seeds informed debugging. These are development checks, not held-out estimates of research performance. Person 2 should freeze the core parameters, make trajectory-grouped splits and evaluate calibration/rejection on new seeds and, preferably, held-out route geometries.

The map is small and synthetic. Candidate posterior probabilities are model-relative and uncalibrated. Matching is offline. Whole-chain failures are reported explicitly. The static figure is not an interactive demo.

## Next work
Person 2 owns calibration, reliability plots, risk–coverage, grouped uncertainty summaries, held-out experiments and interactive demo. See PERSON2_HANDOFF.md.
