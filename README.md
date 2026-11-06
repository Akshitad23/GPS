# Confidence-Aware HMM-Based Map Matching Under Bursty GPS Errors

Person 1 implementation: synthetic directed roads, reproducible journeys, independent/burst GPS errors and gaps, nearest-segment baseline, HMM-style candidate-lattice inference, and road-level confidence.

## Run

Python 3.12 was used for development. From this directory:

```powershell
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m gpsmatch demo --output results/demo
python -m gpsmatch benchmark --seeds 30 --output results/benchmark_with_slack
```

The demo writes a static comparison figure and CSV/JSON outputs. It is not yet an interactive application.

## API

```python
from gpsmatch import Config, run_pipeline
result = run_pipeline(Config(noise_kind="burst"), seed=42)
print(result["metrics"])
```

Read [the implementation notes](docs/PART1_IMPLEMENTATION.md), [Person 2 handoff](docs/PERSON2_HANDOFF.md), and [learning guide](docs/GPS_PROJECT_GUIDE.md).

See [the current project status](docs/PROJECT_STATUS.md) for the verified implementation, saved results and remaining work.

## Scope and limitations

This is a small synthetic research baseline, not a production navigation system or an exact reproduction of Newson–Krumm. Roads are straight segments. Candidate transitions are observation-derived distance scores, row-normalised over legal destinations. Posteriors are relative to this approximate candidate lattice and are not guaranteed calibrated.

Directed connectivity is used for routing, while hidden states and confidence use physical segment positions without heading continuity. selected_directed_edge records canonical geometry orientation, not inferred heading. Speed screening includes an explicit projection-uncertainty allowance of projection_slack_sigma × sqrt(2) × assumed_sigma (default multiplier 3). If no full path exists, the trajectory is explicitly unmatched; it is not silently repaired. Both end-to-end and matched-only metrics are reported. Calibrated confidence, risk–coverage analysis, a larger experiment suite and interactive demo are Person 2 work.

Research foundation: [Newson and Krumm (2009)](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/12/map-matching-ACM-GIS-camera-ready.pdf).

## Development validation

29 unit tests pass, verified on 5 November 2026. The baseline development benchmark contains 120 trajectories over independent noise, burst noise, RMSE-matched independent noise and gaps. See results/benchmark_with_slack/aggregate.json. The earlier results/benchmark folder records strict-screening development failures; it is not the current default run. These runs informed debugging and are not a held-out research evaluation.

## Optional improved models

The baseline remains the default for reproducibility. Select `--model motion`, `--model robust` or `--model bias`. Robust includes the GPS-only motion model plus Student-t emissions; bias includes motion plus persistent offset hypotheses and Gaussian emissions. Bias is experimental and may reduce accuracy on ambiguous parallel roads. See [IMPROVEMENTS.md](docs/IMPROVEMENTS.md).

```powershell
python -m gpsmatch demo --model robust --output results/robust_demo_new
python -m gpsmatch.compare --split evaluation --first-seed 20000 --seeds 12 --output results/comparison_new
```

Comparison runs require a fresh output directory and save a pre-run manifest. Existing model comparisons: `results/improvements_development_v2` (seeds 1000–1005) and `results/improvements_evaluation` (seeds 10000–10011). The failed `results/improvements_development` run has a metric dtype bug and no complete aggregate; use v2. Changed road spacing is tested, but the same six synthetic route families remain. No real GPS validation is claimed.
