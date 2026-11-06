# Part 1 implementation: step-by-step record

This is the implementation record for the simulator and HMM core. See GPS_PROJECT_GUIDE.md for the concepts, VALIDATION.md for measured results and PERSON2_HANDOFF.md for the remaining work.

## 1. Establish the local Python core

The implementation uses NumPy, SciPy and Matplotlib. Road routing is implemented directly. The core needs no GPU, neural-network training or external API.

## 2. Represent roads and candidates

`gpsmatch/roads.py` defines the road map, physical segments and projected candidates. The synthetic map has parallel roads, connectors and coordinates measured in metres. Candidate generation uses only the observed coordinates and map, never truth. Physical-segment candidates are deduplicated. A selected_directed_edge label gives canonical geometry orientation; it must not be interpreted as inferred vehicle heading.

## 3. Generate ground truth

`gpsmatch/simulation.py` generates valid contiguous route templates at timestamped positions. It records coordinates and segment IDs before adding errors. Truth and noise use reproducible random streams. Truth is retained for evaluation but is excluded from the matcher inputs.

## 4. Corrupt the observations

The simulator supports independent Gaussian noise, persistent-offset bursts, magnitude-matched independent controls and missing-observation gaps. Gaps preserve original timestamps. The matched control matches empirical displacement RMSE rather than the full error distribution. Burst offsets have a fixed global direction, so their effect depends on the true route.

## 5. Compute movement compatibility

Routing includes partial distances on the starting and ending segments, legal network travel and same-segment movement. An early strict-orientation implementation interpreted small projected GPS jitter as a heading reversal. The corrected position-based routing permits legal entry/exit orientations when reverse edges exist. This is a physical-position matcher, not a heading estimator.

## 6. Construct HMM-style scores

`gpsmatch/pipeline.py` validates configuration and builds observation-dependent candidate sets. Emissions penalise squared GPS residual. Transitions penalise disagreement between network and observed movement and are row-normalised. Impossible transitions remain impossible. The speed cap includes the documented projection-slack allowance; this prevents reasonable projected jitter from making complete chains infeasible.

These choices form a paper-inspired candidate lattice, not an exact continuous generative GPS sensor model or an exact reproduction of Newson–Krumm. Uniform initial candidate priors and shortest-route transitions are explicit simplifications.

## 7. Infer the route and posterior

`gpsmatch/inference.py` implements log-space Viterbi with backpointers and forward–backward using logsumexp. It supports changing candidate counts and detects impossible complete paths. Forward–backward uses future observations, so the system is offline.

## 8. Define confidence consistently

Accuracy is evaluated on physical segments. Confidence is posterior mass for the segment selected by Viterbi. Entropy measures spread across physical-segment probabilities. Candidate recall means that the true segment was considered; it does not guarantee exact continuous-position recovery. Low entropy is not proof of correctness when the correct segment is missing.

## 9. Expose and run the pipeline

The public entry point is `run_pipeline(Config(...), seed=42)` in `gpsmatch.pipeline`. It returns configuration, seed, trajectory identity, pointwise rows, metrics, failure status and road geometry. The command-line runner is `gpsmatch/__main__.py`; use the commands in README.md for demonstrations and benchmarks. Configuration hashes distinguish trajectory variants.

## 10. Retain failures and validate

A missing candidate set or impossible complete chain currently marks the whole trajectory unmatched. Rows remain visible; the pipeline does not silently discard failures. Overall accuracy and conditional-on-match metrics are distinguished. Eighteen correctness tests pass; the exact commands, fixes and final development-run measurements are in VALIDATION.md.

## 11. Interpret the development findings

The latest benchmark contains 30 trajectories per condition and includes independent noise, bursts, RMSE-matched independent controls and gaps. All current benchmark trajectories matched, but earlier strict-policy failures are retained for inspection. These runs helped fix the model and are development evidence, not a held-out research evaluation. See VALIDATION.md for exact numbers and the observed confidently wrong burst assignments.

## 12. Hand off to Person 2

Person 2 should freeze grouped trajectory splits, run held-out confidence evaluation, fit calibration on separate journeys, compare risk at matched coverage and build the local demo. They should consume the existing pipeline rather than rewrite inference. Calibration and research conclusions remain future work. The main limitations are a small synthetic map, fixed route templates, simple motion/noise models, approximate candidate scoring and whole-chain failure rather than recovery.
