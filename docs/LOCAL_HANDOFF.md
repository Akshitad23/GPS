# Local Codex continuation handoff

## Project directory
C:\Amrita\Sem 5\MIS5\GPS

## User's goal
Undergraduate mathematics/PGM project: confidence-aware offline HMM map matching under bursty GPS errors. Two-person split: Person 1 builds simulator/inference; Person 2 owns calibration, broader evaluation and interactive demo.

## Current status
Person 1 and optional model improvements are implemented locally. Nothing needs to be extracted from a ZIP.

Files:
- gpsmatch/roads.py: synthetic physical segments, projections and legal road distances.
- gpsmatch/simulation.py: truth journeys; independent noise, arbitrary-angle burst offsets, start fraction and gaps.
- gpsmatch/inference.py: log-space Viterbi and forward–backward.
- gpsmatch/pipeline.py: Config and public run_pipeline API; default model remains baseline.
- gpsmatch/models.py: motion, robust and bias alternatives.
- gpsmatch/compare.py: paired comparisons, pre-run manifest and exports.
- gpsmatch/__main__.py: CLI with --model baseline/motion/robust/bias.
- tests/: 29 passing tests.

Read docs/IMPROVEMENTS.md and docs/IMPROVEMENT_RESULTS.md first; docs/PERSON2_HANDOFF.md specifies the remaining work. README.md contains commands. All evaluation runs have completed.

## Results
Evaluation uses 108 synthetic trajectories and 432 model runs over nine scenarios, with seeds 10000–10011 and changed road spacing.
Overall accuracies: baseline82.54%, motion87.85%, robust88.74%, bias83.33%.
Robust is recommended among tested options, but baseline remains default for reproducibility.
Bias-aware is experimental, helps long bursts but can harm other cases.
Detailed probability-quality metrics, limits and saved outputs are in the results document.
No real-data or unseen-topology performance claim is justified. No confidence calibrator has been trained.

## Next steps
Continue based on the user's next instruction. Do not rewrite the working baseline or silently overwrite experiment manifests. No deployment or email sending is involved. User wants local project files and a local Codex task rather than this cloud Work conversation.

## Chat transition issue
The cloud conversation had local filesystem execution, but that did not make it a local Codex chat. The assistant could not convert it in place. Two attempts to list saved Codex projects returned an app connection error, so no replacement local task was created automatically.

To continue manually, create a local Codex task attached to this GPS folder and ask:
"Read docs/LOCAL_HANDOFF.md and continue the GPS project from its current local state."
