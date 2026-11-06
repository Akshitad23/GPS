# Confidence-Aware HMM Map Matching under Bursty GPS Errors
## A step-by-step learning guide and implementation plan

This is the complete learning path for our undergraduate probabilistic graphical models project. Start at Step 1; equations are introduced only after the idea they express. The numerical examples are illustrative, not experimental results.

**Goal:** infer a vehicle's road sequence from noisy GPS observations, then evaluate which assignments deserve confidence. The contribution is a controlled study and a modest confidence-calibration extension. We have not established global novelty.

## Contents

1. The problem
2. Probability basics
3. Roads and candidates
4. The HMM
5. Emissions
6. Transitions
7. Bursty errors
8. Viterbi decoding
9. Forward–backward inference
10. Defining confidence
11. Calibration
12. Rejection and risk–coverage
13. Experimental design
14. Exact coding plan
15. Verification, deliverables and viva
16. References and glossary

## Step 1 — Understand the problem

Imagine a main road with a service road beside it. A vehicle stays on the main road, but its phone sometimes reports positions closer to the service road.

| Quantity | Meaning |
|---|---|
| True position | Where the vehicle actually is |
| Observation | The imperfect coordinate recorded by GPS |
| Inferred position | The road position selected by our algorithm |

**Map matching** uses the road network and recorded coordinates to infer where the vehicle travelled.

The simplest baseline chooses the nearest road independently for each observation. It can jump between roads where no connecting turn exists. A sequence method considers both proximity and plausible movement.

Our project asks two questions:

1. Which road sequence best explains the measurements?
2. Which individual road assignments are reliable?

We begin with **offline** analysis: the complete journey is available. Later measurements can help resolve earlier ambiguity. We are not initially building live navigation.

We use synthetic roads and journeys first. This gives exact ground truth and avoids spending the semester cleaning GPS datasets. A real road graph with simulated journeys is an optional extension.

**Checkpoint:** a GPS point being closer to a road is evidence for that road, but connectivity and the rest of the journey also matter.

## Step 2 — Probability basics

Suppose the road is either main road M or service road S.

Before seeing the current GPS point:

\[
P(M)=0.8,\qquad P(S)=0.2.
\]

These are **priors**: beliefs before the new observation.

The **likelihood** asks how compatible an observation x is with each possible road:

\[
p(x\mid M),\qquad p(x\mid S).
\]

The **posterior** reverses the question: given x, which road is likely?

\[
P(M\mid x)=
\frac{p(x\mid M)P(M)}
{p(x\mid M)P(M)+p(x\mid S)P(S)}.
\]

The essential idea is:

\[
\text{posterior}\propto\text{likelihood}\times\text{prior}.
\]

### Worked example

Let the observation be twice as compatible with the service road. Use relative likelihood scores:

| Road | Prior | Likelihood score | Product |
|---|---:|---:|---:|
| Main | 0.8 | 1 | 0.8 |
| Service | 0.2 | 2 | 0.4 |

Normalise:

\[
P(M\mid x)=0.8/1.2\approx0.667,\quad
P(S\mid x)=0.4/1.2\approx0.333.
\]

The GPS point favours the service road, but earlier evidence keeps the main road more likely. Its probability decreases from 80% to about 67%.

For continuous coordinates, likelihoods are densities, not probabilities of one exact coordinate. Densities can exceed one. The illustrative scores 1 and 2 are relative likelihoods.

**Checkpoint:** likelihood is compatibility assuming a state; posterior is belief about the state after observing evidence.

## Step 3 — Represent roads and candidate positions

A road network is a graph:

\[
G=(V,E).
\]

Vertices are junctions/endpoints. Edges are road segments. Directed edges encode allowed travel direction. Store geometry, length and edge IDs.

Use a small map in metres containing parallel roads, connectors, junctions and alternative paths. Do not calculate metre distances directly from latitude/longitude degrees.

At each observation, project the coordinate onto nearby segments. A candidate contains:

- Directed edge ID.
- Projected coordinate.
- Distance along that edge.
- Distance from observation to projection.

A hidden state should include a **position on a segment**, rather than only a road name. Position is necessary for route-distance calculations.

Write the candidate set at observation t as:

\[
C_t=\{c_{t,1},\ldots,c_{t,K_t}\}.
\]

Candidate counts can vary. Initially use one projection per directed segment, with a search radius and optional maximum count.

Do not insert the true road using simulator ground truth. Candidate generation may only use the map and noisy observations.

If no candidates are available, explicitly flag the point or expand the radius according to a documented rule. Do not silently drop failures.

**Candidate recall** is the fraction of observations whose true segment is represented. It measures segment inclusion, not exact recovery of continuous position.

Near junctions, define a consistent segment-label convention; otherwise a correct junction position may be penalised for an arbitrary edge-ID difference.

## Step 4 — The Hidden Markov Model

| Component | Project meaning |
|---|---|
| Hidden state Z_t | Road candidate at time t |
| Observation X_t | GPS coordinate |
| Initial distribution pi | Starting-state belief |
| Transition A_t(i,j) | Movement from previous candidate i to current j |
| Emission b_t(j) | Compatibility of the observation with candidate j |

A standard HMM factorises as:

\[
P(z_{1:T},x_{1:T})=
P(z_1)P(x_1\mid z_1)
\prod_{t=2}^{T}P(z_t\mid z_{t-1})P(x_t\mid z_t).
\]

Two assumptions make inference manageable:

**First-order Markov assumption**

\[
P(Z_t\mid Z_{1:t-1})=P(Z_t\mid Z_{t-1}).
\]

The previous state summarises the past for the next transition.

**Conditional emission independence**

\[
P(X_t\mid Z_{1:T},X_{1:t-1})=P(X_t\mid Z_t).
\]

Given the state, the current observation does not depend on other observations in the standard model.

These are modelling assumptions, not physical laws.

The conceptual generative HMM is useful for learning. Practical map matching constructs candidate positions and often transition scores from observations. We must document that approximation: a posterior from the resulting candidate lattice is model-relative, not an exact physical GPS probability.

## Step 5 — Emission likelihoods

Let q_tj be candidate j's projected coordinate. Assume isotropic Gaussian coordinate error:

\[
X_t=q_{t,j}+\epsilon_t,\qquad
\epsilon_t\sim\mathcal N(0,\sigma^2I).
\]

Then:

\[
b_t(j)=\frac{1}{2\pi\sigma^2}
\exp\left[-\frac{\|x_t-q_{t,j}\|^2}{2\sigma^2}\right].
\]

A smaller distance produces a larger likelihood. Larger sigma means more tolerance for displacement.

With the same sigma for all candidates, the shared constant can be omitted when computing relative path probabilities. Do not assume this cancellation if sigma varies across states.

Projection is a convenient approximation to an unknown continuous road position. This formula is our chosen model; it is not a claim that real GPS noise is always Gaussian, or that every published matcher uses this exact density.

The simulator's actual noise magnitude and the matcher's assumed sigma are separate quantities. Keeping them separate lets us study model mismatch.

## Step 6 — Transition scores and legal movement

For candidates i and j calculate:

- Road-network distance d_net(i,j).
- Straight-line distance d_obs between consecutive GPS observations.
- Elapsed time delta_t.

A paper-inspired compatibility score is:

\[
s_t(i,j)=
\exp\left[-\frac{|d_{\text{net}}(i,j)-d_{\text{obs}}|}{\beta}\right].
\]

Beta controls tolerance for distance mismatch. This beta is unrelated to the backward message introduced later.

Road distance includes partial distances on the starting/ending segments. Respect direction, same-edge ordering and connectivity. Shortest path between junctions alone is insufficient.

Set impossible transitions to zero, including disconnected movement or movement exceeding a documented speed limit over elapsed time.

For our first candidate-lattice implementation, row-normalise over feasible current candidates:

\[
A_t(i,j)=\frac{s_t(i,j)}{\sum_k s_t(i,k)}.
\]

This is a modelling choice. Row-normalising changes relative sequence probabilities compared with using unnormalised pairwise factors. We should not call this an exact reproduction of Newson–Krumm.

Observation-derived transitions also mean the resulting inference is best described as inference in our HMM-style candidate lattice. Its confidence needs empirical checking.

If a row is entirely impossible, leave it impossible and remove unreachable states during inference. If all complete paths disappear, return an explicit unmatched/broken-chain status. Never produce NaNs or secretly allow impossible travel.

Multiple physical routes may connect two candidates. Initially use shortest legal routing and state this limitation: uncertainty over alternative connecting routes is not fully represented.

## Step 7 — Independent noise versus burst errors

Independent noise:

\[
x_t=q_t+\epsilon_t.
\]

Each error is freshly sampled.

Bursty noise:

\[
x_t=q_t+b_t+\epsilon_t.
\]

During a burst, b_t is a persistent offset for several consecutive observations. For example, a 20-metre lateral offset can push a group of points towards a parallel road.

A slowly changing bias is an optional later variant:

\[
b_t=\rho b_{t-1}+\eta_t.
\]

Now observation errors remain related even when the true positions are known. The baseline's independent-emission assumption is misspecified.

The matcher may become confidently wrong, or road connectivity and observations outside the burst may rescue it. These are outcomes to measure.

Match or report error magnitude when comparing noise types. Otherwise greater error could explain a result attributed to temporal correlation.

Gaps are a separate intervention. Preserve actual timestamps after dropping observations; the transition must use the larger elapsed time.

## Step 8 — Viterbi: find one best sequence

Viterbi finds:

\[
\hat z_{1:T}=\arg\max_{z_{1:T}}P(z_{1:T},x_{1:T}).
\]

Let delta_t(j) be the score of the best partial sequence ending in j:

\[
\delta_1(j)=\pi(j)b_1(j),
\]

\[
\delta_t(j)=b_t(j)\max_i[\delta_{t-1}(i)A_t(i,j)].
\]

Save the maximising previous state as a backpointer. Choose the best final state and follow backpointers backwards.

### Worked two-observation example

Use pi(M)=pi(S)=0.5. Staying has transition probability 0.9; switching has probability 0.1.

| Observation | Main emission | Service emission |
|---|---:|---:|
| First | 0.9 | 0.1 |
| Second | 0.4 | 0.6 |

| Sequence | Product | Score |
|---|---|---:|
| M,M | 0.5 × 0.9 × 0.9 × 0.4 | 0.162 |
| M,S | 0.5 × 0.9 × 0.1 × 0.6 | 0.027 |
| S,M | 0.5 × 0.1 × 0.1 × 0.4 | 0.002 |
| S,S | 0.5 × 0.1 × 0.9 × 0.6 | 0.027 |

Viterbi chooses M,M despite the second point individually favouring S.

These illustrative transitions assume switching is feasible; a real map may prohibit it.

### Numerical stability

Long products underflow. Work in log space:

\[
\log\delta_t(j)=\log b_t(j)+
\max_i[\log\delta_{t-1}(i)+\log A_t(i,j)].
\]

Use negative infinity for impossible transitions. Never turn zero-probability travel into a small positive value without declaring a changed model.

With at most K candidates per observation, dense inference takes approximately O(T K²) time. Routing may dominate runtime.

## Step 9 — Forward–backward: account for competing sequences

Viterbi keeps a maximum. Posterior inference sums over alternatives.

Forward message:

\[
\alpha_1(j)=\pi(j)b_1(j),
\]

\[
\alpha_t(j)=b_t(j)\sum_i\alpha_{t-1}(i)A_t(i,j).
\]

Backward message:

\[
\beta_T(i)=1,
\]

\[
\beta_t(i)=\sum_j A_{t+1}(i,j)b_{t+1}(j)\beta_{t+1}(j).
\]

Combine:

\[
\gamma_t(j)=
\frac{\alpha_t(j)\beta_t(j)}
{\sum_k\alpha_t(k)\beta_t(k)}.
\]

For a standard HMM, gamma is P(Z_t=j | x_1:T). In our approximate candidate model, it is the corresponding model posterior.

In the example, all sequence scores sum to 0.218:

\[
P(Z_2=M\mid x_{1:2})=(0.162+0.002)/0.218\approx0.752.
\]

\[
P(Z_1=M\mid x_{1:2})=(0.162+0.027)/0.218\approx0.867.
\]

The selected road is the same at both points, but uncertainty differs.

The entire M,M path has posterior 0.162/0.218 ≈ 0.743. This differs from either pointwise confidence.

Implement forward/backward in log space using logsumexp. Candidate sets may vary, so A_t has shape K_(t-1) by K_t.

Choosing the largest marginal gamma at each point is not generally equivalent to Viterbi and may produce an infeasible sequence.

## Step 10 — Define confidence precisely

For the Viterbi-selected candidate:

\[
c_t=\gamma_t(\hat z_t).
\]

Our main correctness target is the road segment, rather than exact continuous position. If several candidates correspond to the same evaluated segment, sum their probabilities:

\[
c_t^{\text{road}}=
\sum_{j:\operatorname{edge}(j)=\operatorname{edge}(\hat z_t)}
\gamma_t(j).
\]

Decide whether opposite directions count as different labels and apply that definition consistently.

Entropy measures spread:

\[
H_t=-\sum_j\gamma_t(j)\log\gamma_t(j).
\]

For K_t>1, normalised entropy is H_t/log(K_t). Define it as zero when K_t=1. If evaluating road uncertainty, aggregate to road probabilities before calculating entropy.

A single candidate or low entropy does not prove correctness. The true road may be absent. Candidate-set confidence is conditional on available explanations.

Forward–backward uses future observations. Label the system offline. Real-time filtering would instead estimate P(Z_t | x_1:t).

## Step 11 — Calibration: does confidence match correctness?

Define:

\[
y_t=\mathbf1[\text{selected segment equals true segment}].
\]

A calibrated correctness score near 0.8 should correspond to about 80% correct assignments across comparable cases.

Use a reliability diagram: group predictions by score and compare average score with observed correctness. Report bin counts; sparse bins are unstable.

Binary Brier score for assignment correctness:

\[
\operatorname{BS}=\frac1N\sum_t(c_t-y_t)^2.
\]

Binary log loss:

\[
-\frac1N\sum_t[y_t\log c_t+(1-y_t)\log(1-c_t)].
\]

Clip only for numerical evaluation and report the clipping rule. This binary correctness loss differs from multiclass log loss for the true road distribution.

### Our focused extension

Fit a small mapping g(c) on labelled calibration trajectories. Compare raw c against g(c). A monotonic isotonic mapping is one option; logistic calibration on the logit score is another.

Compare calibration trained on:

1. Independent-noise trajectories only.
2. A mixture of independent and burst-noise trajectories.

Keep test trajectories untouched. Calibration uses labelled correctness and therefore requires labelled development data; synthetic ground truth supplies it here.

Calibration does not change the decoded road sequence. A monotonic mapping usually preserves ranking, so it should not be expected to improve a risk–coverage curve except through ties. Its primary value is better probability interpretation and threshold transfer.

A later ranking method could use entropy, candidate distance and other diagnostics, but that is a distinct supervised extension and must be evaluated separately.

## Step 12 — Rejection and risk–coverage

Accept an assignment if its score is at least threshold tau.

\[
\operatorname{coverage}(\tau)=
\frac{\#\text{accepted observations}}{\#\text{all observations}}.
\]

\[
\operatorname{risk}(\tau)=
\frac{\#\text{incorrect accepted observations}}
{\#\text{accepted observations}}.
\]

Risk is undefined when nothing is accepted. Do not report zero error for zero accepted points.

Sweep thresholds to draw risk against coverage. Compare methods at matched coverage, such as 50%, 80% and 95%, where available.

Nearest-road distance, raw posterior and entropy can provide different rejection rankings. Their scores need not share the same numerical scale.

Selecting only easy points can reduce accepted error without improving the underlying decoded route. Report overall accuracy, coverage and accepted risk together.

Unmatched observations count against end-to-end coverage. Report failure rate and conditional accuracy separately so dropping difficult points cannot hide failures.

## Step 13 — Design a reproducible experiment

### Main research question

How do temporally correlated GPS errors affect road-assignment confidence, and can a simple calibration procedure improve the reliability of stated probabilities?

### Baselines

| Method | Purpose |
|---|---|
| Nearest segment | No temporal reasoning |
| HMM Viterbi | Sequence-based road assignments |
| HMM + raw posterior rejection | Model confidence |
| HMM + entropy rejection | Alternative ambiguity ranking |
| HMM + calibrated confidence | Probability calibration extension |

An existing map matcher is an optional external reference, not a prerequisite for the core experiment.

### Data generation

Generate legal routes, sample positions at recorded timestamps and save true edge IDs. Add noise only after truth is stored. Use different route shapes and start positions, not just many noisy copies of one journey.

Start with a modest sweep:

| Factor | Initial example settings |
|---|---|
| Independent noise sigma | 3, 8, 15 metres |
| Burst offset | 10, 20, 30 metres |
| Burst duration | 3, 8, 15 observations |
| Sampling interval | 1, 3, 5 seconds |
| Gap duration | 0, 10, 20 seconds |
| Road separation | 10, 20, 40 metres |

These are proposed experimental settings, not published recommended values. Use a small subset first; do not launch the full Cartesian product.

For isotropic noise with per-axis variance sigma², expected squared radial displacement is 2 sigma². A constant burst bias adds ||b||² during its active fraction. Use this relationship and empirical RMSE checks to create approximately magnitude-matched independent controls. Correlation and tails can still differ; report those differences.

### Splits and uncertainty

Split by complete trajectory, with independent random seeds. Related variants of a ground-truth route should stay in one split when testing route generalisation. Reserve separate development, calibration and test groups.

Tune sigma, beta, candidate radius and thresholds only on development/calibration data. The matcher never sees true test road IDs.

Report results separately by noise type and burst interval, as well as overall. Use multiple trajectory seeds. Confidence intervals should resample whole trajectories because nearby points are correlated.

### Metrics

- Segment-assignment accuracy.
- Candidate recall.
- Unmatched/broken-chain rate.
- Binary Brier score and log loss for correctness.
- Reliability diagrams and bin counts.
- Risk–coverage curves and risk at matched coverage.
- Runtime.
- Actual GPS displacement RMSE.

Optional: route-distance error and uncertainty in reconstructed connecting paths. Do not label pointwise segment accuracy as complete route accuracy.

A negative result is useful: for example, independent-noise calibration may fail on bursts. Report it rather than adjusting the test set.

## Step 14 — Exactly what to code

Build a local Python research pipeline first. No neural-network training, GPU, paid API or mobile application is needed for the core scope.

### Proposed modules

| File | Responsibility | Main output |
|---|---|---|
| src/gpsmatch/roads.py | Synthetic directed graph and geometry | Road network |
| src/gpsmatch/simulation.py | Legal routes and timestamped true positions | Ground-truth trajectories |
| src/gpsmatch/noise.py | Independent errors, bursts and gaps | Noisy observations |
| src/gpsmatch/candidates.py | Projection and nearby-segment search | Candidate lists |
| src/gpsmatch/routing.py | Directed distances including partial edges | Pairwise network distances |
| src/gpsmatch/model.py | Initial, emission and transition scores | Log-score lattice |
| src/gpsmatch/inference.py | Viterbi and forward–backward | Selected states and marginals |
| src/gpsmatch/confidence.py | Edge aggregation, entropy and calibration | Correctness scores |
| src/gpsmatch/evaluation.py | Metrics and trajectory-level summaries | Tables and curves |
| experiments/run_benchmark.py | Seeded experiment configuration | Reproducible results |
| app.py | Local interactive demo | Map and uncertainty display |
| tests/ | Small correctness checks | Verified inference and routing |

These files are a plan; this guide does not claim the application has been implemented.

### Data contracts

A truth row contains trajectory_id, timestamp, true_x, true_y and true_edge_id.

An observation row contains trajectory_id, timestamp, gps_x and gps_y. Store simulator error labels separately for evaluation, never as matcher inputs.

A prediction row contains trajectory_id, timestamp, selected_edge_id, raw_confidence, calibrated_confidence, entropy and status.

Save pointwise results plus trajectory summaries. Save the seed, configuration and dependency versions with each benchmark.

### Suggested tools

Use NumPy for arrays, SciPy for logsumexp, NetworkX for graph operations, and Matplotlib for initial plots. Geometry can start with straightforward line-segment projection; Shapely becomes useful for richer geometry.

Use scikit-learn for the small calibration model, and Streamlit plus Plotly for an optional local demo. Verify compatibility when creating the environment; no version combination has been tested in this document.

A general-purpose HMM library is optional. Custom recurrences make variable candidate counts and confidence calculations easier to inspect.

### Build order and acceptance criteria

1. **Toy arithmetic:** implement Viterbi and forward–backward on the two-state example. Match the numbers above.
2. **Map and truth:** draw a synthetic network and legal noiseless journeys.
3. **Noise:** show independent scatter and a persistent-offset burst.
4. **Candidates and routing:** test projections, partial-edge distances and illegal travel.
5. **Matcher:** compare nearest-road and Viterbi on the same observations.
6. **Confidence:** compute marginals, edge confidence and entropy.
7. **Experiments:** produce per-condition accuracy and candidate-recall tables.
8. **Calibration:** fit only on held-out calibration journeys and evaluate untouched test journeys.
9. **Demo:** visualise the existing pipeline without embedding evaluation truth in inference.
10. **Optional realism:** repeat with a small real road graph and simulated journeys.

The first concrete coding milestone should be one reproducible plot showing the true route, noisy observations, nearest-road assignments and HMM assignments. Calibration comes after that works.

## Step 15 — Verification and deliverables

### Necessary correctness checks

- Enumerate all paths on a tiny lattice; compare Viterbi maximum and forward/backward sums.
- Check every posterior row sums to one within numerical tolerance.
- Verify impossible transitions remain impossible.
- Verify long trajectories do not underflow.
- Test changing candidate counts and missing candidates.
- Test same-edge forward movement, illegal reverse movement, disconnected edges and partial-edge distances.
- Verify timestamps survive observation gaps.
- Verify calibration and test trajectory IDs do not overlap.

Do not assume every noiseless journey has a unique answer: exact geometric overlaps can remain ambiguous.

### Demo behaviour

Display the road graph, true simulated journey, GPS observations, inferred segment sequence and rejected points. Let the reader vary noise, burst duration and confidence threshold.

Show overall accuracy, accepted coverage, accepted risk and candidate recall beside the map. Clearly mark truth as simulation ground truth and the analysis as offline.

Use fixed seeds to reproduce cases. Include an easy case, an ambiguous case and a confidently wrong case if experiments actually find one.

### What the contribution is

A defensible semester submission is:

> A reproducible benchmark of HMM road-assignment confidence under independent and correlated GPS errors, with a held-out calibration comparison and selective-prediction evaluation.

It does not claim that HMM map matching, burst errors, entropy, rejection or calibration are individually new. Further related-work review is required before claiming a novel combination.

### Syllabus mapping

| Syllabus area | Project connection |
|---|---|
| Unit 1: probabilistic AI and inference | Priors, likelihoods, posteriors and latent states |
| Unit 2: HMMs and independence | Sequence model, Viterbi, forward–backward and assumption mismatch |
| Unit 3: MRFs | Optional explanation of the chain's factorisation; not required for the core contribution |

### Final submission

- Report with problem, model choices, experiments, results and limitations.
- Reproducible code and configurations.
- Figures and result tables.
- Local demo.
- Viva slides explaining one example end to end.

No performance improvements are promised before experiments.

## Step 16 — References and glossary

### Verified starting references

1. Newson and Krumm, *Hidden Markov Map Matching Through Noise and Sparseness*, ACM SIGSPATIAL 2009. Foundation for the map-matching direction; it already investigates noise and sparse sampling. Our candidate-lattice choices must be distinguished from an exact reproduction.
   https://www.microsoft.com/en-us/research/wp-content/uploads/2016/12/map-matching-ACM-GIS-camera-ready.pdf

2. LeuvenMapMatching repository. Useful Python implementation reference; not asserted to be identical to our proposed matcher.
   https://github.com/wannesm/LeuvenMapMatching

3. SciPy logsumexp documentation. Stable computation needed for log-space forward/backward sums.
   https://docs.scipy.org/doc/scipy/reference/generated/scipy.special.logsumexp.html

The links above were opened while preparing this guide. We have not installed the repository or verified our proposed contribution as globally new.

### Glossary

| Term | Meaning |
|---|---|
| Map matching | Infer positions on roads from noisy measurements |
| Hidden state | Unobserved road candidate |
| Prior | Belief before incorporating new evidence |
| Likelihood | Compatibility of evidence with a proposed state |
| Posterior | Belief after incorporating evidence |
| Emission | Observation likelihood for a state |
| Transition | Movement compatibility/probability between states |
| Viterbi | Highest-scoring complete state sequence |
| Forward–backward | Marginal posterior inference using the whole sequence |
| Calibration | Agreement between stated confidence and observed correctness |
| Abstention | Leave an assignment unresolved when confidence is insufficient |
| Coverage | Fraction of all observations accepted |
| Selective risk | Error rate among accepted observations |
| Candidate recall | Fraction whose true segment was considered |
| Model mismatch | Actual data violate assumptions of the model |

**Reading order:** Steps 1–7 explain the model; Steps 8–12 explain inference and confidence; Steps 13–15 turn it into a research project.
