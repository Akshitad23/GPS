# Improved motion, robust emissions and bias-aware map matching

This note documents the implemented alternatives in `gpsmatch/models.py`. They extend the baseline candidate lattice; they do not establish globally novel methods. Evaluation claims must come from saved comparisons, not from the equations alone.

## 1. Four model settings

| Config.model | Motion score | Emission | Extra hidden variable |
|---|---|---|---|
| baseline | Consecutive observed displacement | Gaussian | None |
| motion | Multi-lag GPS motion estimate | Gaussian | None |
| robust | Same improved motion | Student-t | None |
| bias | Same improved motion | Gaussian after bias correction | Discrete persistent 2D offset |

The baseline remains available for comparison. `match` validates Config and dispatches non-baseline settings to `alternative_match`. All variants use observed coordinates, timestamps and the map; they do not read true path, simulated speed or burst labels.

## 2. Improved motion from GPS only

`motion_estimates` collects observed velocity vectors from differences spanning 3, 4 and 5 observations around each time. It takes a coordinate-wise median. Short trajectories fall back to adjacent differences. Each difference is divided by actual elapsed time, so sampling gaps retain their timestamps.

For adjacent times, expected travel distance is:

    target = 0.5 * (estimated_speed_previous + estimated_speed_current) * elapsed_time

The motion log compatibility is:

    -abs(network_distance - target) / (motion_scale + speed_uncertainty * elapsed_time)

The speed bound is:

    network_distance <= max_speed * elapsed_time + projection_slack_sigma * sqrt(2) * assumed_sigma

The allowance recognises that projected observed positions can move more than the physical vehicle because of measurement noise. It is an explicit approximation, not a physical guarantee.

A soft direction penalty uses the cosine between candidate displacement and averaged GPS velocity. It activates only above 2 metres/second and is tapered for displacement below 5 metres. It discourages movement opposite to the estimated direction but cannot distinguish parallel roads travelled in the same direction.

Longer differences reduce independent jitter, but burst boundaries, stops, sharp turns and long gaps can still distort motion estimates. These estimates use future observations; this remains an offline method.

## 3. Heavy-tailed Student-t observation score

For residual distance r, scale sigma and degrees of freedom nu, `emission_scores` uses:

    log_score = -0.5 * (nu + 2) * log(1 + (r / sigma)^2 / nu)

This is the two-dimensional isotropic Student-t kernel. Constants shared by all candidates under fixed sigma and nu cancel in relative sequence scores.

The Student-t tail penalises large residuals less strongly than the Gaussian. This can reduce domination by isolated outliers, but it does not explicitly model temporal error correlation and may also weaken useful location evidence. `robust` includes the same improved motion score as `motion`, so the comparison between those two isolates the emission change.

## 4. Add bias to the hidden state

The bias model expands the state to:

    hidden_state = (road_position_candidate, bias_vector)

The default one-dimensional bias levels are -30, -15, 0, 15 and 30 metres. Their Cartesian product gives 25 two-dimensional offsets.

For every observation and bias hypothesis b:

1. Correct the coordinate: corrected_observation = observed_coordinate - b.
2. Project that corrected coordinate onto nearby road segments.
3. Calculate residual and emission against the corrected coordinate.
4. Retain the associated bias index with every road candidate.

Correcting BEFORE projection is essential. Merely subtracting a bias from an emission residual after projecting the original coordinate would not move the candidate position consistently.

Road-distance and direction calculations use the corrected candidate positions. The GPS-only motion estimates themselves are calculated from the original observations.

## 5. Persistent bias transitions

A Gaussian-shaped discrete jump prior favours smaller bias magnitudes:

    prior(b) proportional to exp(-||b||^2 / (2 * bias_prior_sigma^2))

The probability of a bias redraw over elapsed time dt is:

    jump(dt) = 1 - (1 - bias_jump_probability)^dt

The bias transition combines persistence with a redraw:

    P(b_new | b_old) = (1 - jump) * indicator(b_new == b_old) + jump * prior(b_new)

Thus most adjacent states retain their bias, while occasional jumps allow a burst to begin or end. The formula interprets the configured jump probability as a per-second redraw rate on this time scale. A redraw may choose the same bias.

Initial bias uses a separate, narrower Gaussian-shaped prior controlled by `initial_bias_sigma`. This favours a near-unbiased beginning, which is a substantive modelling assumption and can be wrong when a journey starts during persistent error.

## 6. Avoid candidate-count rewards

For each previous state, road transition scores are normalised separately within each destination bias group. The resulting conditional road probabilities are multiplied by the bias transition probability. The joint row is then reconditioned on feasible outgoing destinations.

Initial bias mass is similarly divided among candidates belonging to that bias. This avoids rewarding a bias merely because it produces more candidate hypotheses. Reconditioning on feasible destinations remains part of the candidate-lattice approximation.

`distance_matrix` vectorises exact legal candidate-to-candidate distances and respects available reverse road edges. Impossible movement remains negative infinity.

## 7. Configuration and outputs

| Setting | Default | Role |
|---|---:|---|
| motion_scale | 10 | Base distance-compatibility scale, metres |
| speed_uncertainty | 2 | Additional distance tolerance per elapsed second |
| heading_weight | 0.5 | Soft direction penalty strength |
| student_df | 4 | Student-t tail parameter |
| bias_levels | (-30,-15,0,15,30) | Grid on each coordinate axis, metres |
| bias_prior_sigma | 20 | Bias redraw prior scale, metres |
| initial_bias_sigma | 5 | Initial bias prior scale, metres |
| bias_jump_probability | 0.04 | Per-second bias redraw probability |

`alternative_match` returns the ordinary path, posteriors, candidate sets and transition matrices, plus `state_biases` aligned with the candidates. Physical-road confidence must marginalise all candidate states representing that road, including different bias values. It must not be confused with confidence in one exact bias.

Example API:

    from gpsmatch.pipeline import Config, run_pipeline
    result = run_pipeline(Config(model="bias", noise_kind="burst"), seed=42)

## 8. Limits and interpretation

- Bias is restricted to a finite grid; offsets between levels are approximated and offsets outside the grid are poorly represented.
- Parallel-road identity and lateral GPS bias can be genuinely unidentifiable. A plausible offset is not proof that the inferred road is correct.
- The initial near-zero bias prior may help clean starts but disadvantage traces starting inside a burst.
- The method has more states, transition work and tuning choices than the baseline.
- Row-normalised, observation-derived candidate scoring is an HMM-style approximation, not an exact continuous sensor model.
- Student-t robustness and persistent-bias modelling solve different failure mechanisms; neither is guaranteed to improve every condition.
- Hyperparameters must be fixed before final held-out testing. Development comparisons are not final evidence of generalisation.
- A calibrated confidence study, risk-coverage evaluation and broader real-data validation remain distinct tasks.

## 9. Reproduce the paired model comparison

`gpsmatch/compare.py` runs all four models on identical observations for each case and asserts that the timestamp, truth-segment and GPS signatures agree. It writes its manifest before starting model runs and refuses to overwrite an existing manifest.

Example development command, using a new output directory:

    python -m gpsmatch.compare --output results/comparison_dev_new --seeds 6 --first-seed 1000 --split development

Example evaluation command, after development choices are frozen:

    python -m gpsmatch.compare --output results/comparison_eval_new --seeds 12 --first-seed 10000 --split evaluation

Development uses 20-metre road separation. Evaluation cycles through 16, 24 and 32 metres, but reuses the six small route families; it is not a real-world or fully unseen-topology validation.

Nine scenarios are implemented: independent noise; positive, negative, diagonal, off-grid, long and start-of-trace bursts; matched independent noise; and missing-observation gaps. The burst angle and start fraction are configurable in the simulator. Every model receives exactly the same observations per paired case.

Each model/case directory saves predictions.csv and summary.json. The root saves manifest.json, comparison.json and comparison.png. The aggregate includes segment accuracy, conditional Brier and log loss, candidate recall, unmatched trajectories, confident-wrong counts at confidence at least 0.9, runtime and GPS RMSE.

Paired accuracy differences are calculated per whole trajectory. A fixed-seed bootstrap resamples those trajectory differences 1,000 times to report percentile intervals. These are descriptive synthetic-benchmark intervals, not proof of universal improvement. The runner labels a split but does not itself enforce disjoint seed ranges across separately launched commands; use nonoverlapping ranges and preserve manifests.

This comparison does not train a confidence calibrator. Raw-score probability quality, route accuracy and future calibrated rejection experiments are separate analyses. Inspect the saved outputs for measured findings; no result values are assumed in this note.

## 10. Recorded development outcome

The completed development-v2 comparison used six seeds per scenario (54 trajectories and 216 model runs). Overall pooled segment accuracy was approximately 0.80910 for baseline, 0.85756 for motion, 0.88057 for robust and 0.78610 for bias. These are development observations supplied by the implementation run, not untouched final evaluation results.

The bias model helped in the long-burst development scenario (approximately 0.853 versus baseline 0.636) but performed worse in other conditions. It remains an experimental alternative, not the recommended universal replacement. Parallel-road/bias ambiguity and the narrow initial bias prior are important explanations to investigate, not verified causes of every error.

The preserved development run is reproducible from its manifest at results/improvements_development_v2. Its invocation was:

    python -m gpsmatch.compare --split development --first-seed 1000 --seeds 6 --output results/improvements_development_v2

To rerun, choose a fresh output directory because existing manifests are protected. The separate evaluation was launched with first seed 10000 and 12 seeds per scenario; its results must be inspected after completion before making held-out claims.

The demonstration CLI also accepts a model selector, for example:

    python -m gpsmatch demo --model robust --seed 42 --output results/robust_demo_new

## 11. Completed evaluation

The evaluation has finished. See [IMPROVEMENT_RESULTS.md](IMPROVEMENT_RESULTS.md) for measured values, limitations and remaining Person 2 work. Baseline remains default; robust is the recommended general-purpose option among the tested alternatives.
