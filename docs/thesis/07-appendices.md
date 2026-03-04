# APPENDICES

---

## APPENDIX A: SYSTEM ARCHITECTURE DIAGRAMS

### A.1 High-Level System Architecture

```
                          ┌─────────────────────────────────┐
                          │     PRECISION PIPELINE v2       │
                          │   Career Application Decision   │
                          │          Support System         │
                          └──────────────┬──────────────────┘
                                         │
              ┌──────────────────────────┼──────────────────────────┐
              │                          │                          │
    ┌─────────▼─────────┐   ┌───────────▼───────────┐   ┌────────▼─────────┐
    │   DATA LAYER      │   │   SCORING ENGINE      │   │ COMPOSITION      │
    │                   │   │                       │   │ ENGINE           │
    │ ┌───────────────┐ │   │ ┌───────────────────┐ │   │ ┌──────────────┐ │
    │ │ Pipeline YAML │ │   │ │ WSM (9-dim)       │ │   │ │ Block Lib    │ │
    │ │ (1000+ files) │ │   │ │ Dual weights      │ │   │ │ (4 tiers)    │ │
    │ └───────────────┘ │   │ │ Bayesian learning │ │   │ └──────────────┘ │
    │ ┌───────────────┐ │   │ └───────────────────┘ │   │ ┌──────────────┐ │
    │ │ Market Intel  │ │   │ ┌───────────────────┐ │   │ │ Profiles     │ │
    │ │ (112 sources) │ │   │ │ Network Proximity │ │   │ │ (44 targets) │ │
    │ └───────────────┘ │   │ │ (6-signal, decay) │ │   │ └──────────────┘ │
    │ ┌───────────────┐ │   │ └───────────────────┘ │   │ ┌──────────────┐ │
    │ │ Scoring Rubric│ │   │ ┌───────────────────┐ │   │ │ Identity     │ │
    │ │ (YAML config) │ │   │ │ Reachability      │ │   │ │ Positions(5) │ │
    │ └───────────────┘ │   │ │ Analysis          │ │   │ └──────────────┘ │
    └───────────────────┘   │ └───────────────────┘ │   │ ┌──────────────┐ │
                            └───────────┬───────────┘   │ │ Storefront/  │ │
                                        │               │ │ Cathedral    │ │
              ┌─────────────────────────┤               │ └──────────────┘ │
              │                         │               └──────────────────┘
    ┌─────────▼─────────┐   ┌──────────▼────────────┐
    │   STATE MACHINE   │   │   ANALYTICS LAYER     │
    │                   │   │                       │
    │ 8 transient +     │   │ Conversion funnel     │
    │ 2 absorbing       │   │ Portfolio analysis    │
    │ states            │   │ Velocity tracking     │
    │                   │   │ Signal-action audit   │
    │ Absorbing Markov  │   │ Outcome learning      │
    │ chain model       │   │ Mode switching        │
    └───────────────────┘   └───────────────────────┘
```

### A.2 Pipeline State Machine (Finite State Automaton)

```
                                    ┌─────────┐
                         ┌─────────│research │──────────────────────┐
                         │         └────┬────┘                      │
                         │              │                           │
                    ┌────▼────┐    ┌────▼─────┐                    │
                    │withdrawn│    │qualified │◄────────────────┐   │
                    └─────────┘    └──┬─┬─┬──┘                 │   │
                         ▲            │ │ │                     │   │
                         │     ┌──────┘ │ └────────┐           │   │
                         │     │        │          │           │   │
                         │  ┌──▼────┐   │    ┌─────▼──┐       │   │
                         ├──│drafting│  │    │deferred│───────┤   │
                         │  └──┬────┘   │    └────────┘       │   │
                         │     │        │          ▲           │   │
                         │  ┌──▼───┐    │          │           │   │
                         ├──│staged│────┼──────────┘           │   │
                         │  └──┬───┘    │                      │   │
                         │     │        │                      │   │
                         │  ┌──▼──────┐ │                      │   │
                         ├──│submitted│ │                      │   │
                         │  └──┬──────┘ │                      │   │
                         │     │        │                      │   │
                         │  ┌──▼──────────┐                    │   │
                         ├──│acknowledged │                    │   │
                         │  └──┬──────────┘                    │   │
                         │     │                               │   │
                         │  ┌──▼──────┐                        │   │
                         ├──│interview│                        │   │
                         │  └──┬──────┘                        │   │
                         │     │                               │   │
                         │  ┌──▼────┐                          │   │
                         └──│outcome│  ◄───────────────────────┘   │
                            └───────┘                              │
                                                                   │
    Note: All states can transition to 'withdrawn' (arrows omitted
    for clarity). 'outcome' and 'withdrawn' are absorbing states.
```

**State Set:** Q = {research, qualified, drafting, staged, deferred, submitted, acknowledged, interview, outcome, withdrawn}

**Transient States (8):** T = {research, qualified, drafting, staged, deferred, submitted, acknowledged, interview}

**Absorbing States (2):** A = {outcome, withdrawn}

### A.3 Scoring Engine Data Flow

```
    Pipeline Entry (YAML)
           │
           ▼
    ┌──────────────────┐
    │ compute_dimensions│──── Reads 9 fields from entry YAML
    │ (score.py:1164)  │     Returns dict[str, float]
    └────────┬─────────┘
             │
             ├──────────────────────────────────────┐
             │                                      │
    ┌────────▼──────────┐               ┌──────────▼──────────┐
    │score_network_prox │               │ get_weights()       │
    │(score.py:1054)    │               │ (score.py:1205)     │
    │                   │               │                     │
    │ 6 signals:        │               │ Track-specific:     │
    │ 1. relationship   │               │  creative→WEIGHTS   │
    │ 2. mutual_conn    │               │  job→WEIGHTS_JOB    │
    │ 3. follow_up resp │               │                     │
    │ 4. referral chan   │               │ Bayesian blend:     │
    │ 5. outreach done  │               │  w = 0.70*prior     │
    │ 6. org density    │               │    + 0.30*evidence  │
    │                   │               │  (if outcomes >= 10)│
    │ Time decay:       │               │                     │
    │  <30d: full boost │               │ Normalize: Σw = 1.0 │
    │  30-90d: reduced  │               └──────────┬──────────┘
    │  90-180d: minimal │                          │
    │  >180d: expired   │                          │
    │                   │                          │
    │ Aggregation: max()│                          │
    └────────┬──────────┘                          │
             │                                     │
             ▼                                     ▼
    ┌────────────────────────────────────────────────┐
    │ compute_composite(dimensions, weights)         │
    │ (score.py:1187)                               │
    │                                                │
    │ V(a) = Σ w_i × s_i                            │
    │                                                │
    │ Properties:                                    │
    │  • Bounded: V(a) ∈ [1.0, 10.0]               │
    │  • Normalized: Σ w_i = 1.0                    │
    │  • MPI-optimal: unique value function          │
    └────────────────────┬───────────────────────────┘
                         │
                         ▼
    ┌─────────────────────────────────┐
    │ Threshold Decision              │
    │                                 │
    │ V(a) ≥ 9.0 → auto-qualify     │
    │ V(a) ≥ 9.5 → auto-advance     │
    │ V(a) < 9.0 → hold / cultivate  │
    └─────────────────────────────────┘
```

### A.4 Bayesian Outcome Learning Feedback Loop

```
    ┌───────────────────────────────────────┐
    │ 1. COLLECT OUTCOME DATA               │
    │    closed/ + submitted/ entries        │
    │    with outcome ∈ {accepted, rejected} │
    │    AND all 9 dimension scores          │
    └──────────────────┬────────────────────┘
                       │
                       ▼
    ┌───────────────────────────────────────┐
    │ 2. ANALYZE DIMENSION ACCURACY         │
    │                                       │
    │ For each dimension i:                 │
    │   δ_i = mean(s_i | accepted)          │
    │       - mean(s_i | rejected)          │
    │                                       │
    │ High δ_i → dimension discriminates    │
    │ Low δ_i → dimension does not          │
    └──────────────────┬────────────────────┘
                       │
                       ▼
    ┌───────────────────────────────────────┐
    │ 3. COMPUTE WEIGHT RECOMMENDATIONS     │
    │                                       │
    │ Redistribute 0.02 weight units:       │
    │   Increase weight of top-δ dimensions │
    │   Decrease weight of bottom-δ dims    │
    │                                       │
    │ Normalize: Σ w_evidence = 1.0         │
    └──────────────────┬────────────────────┘
                       │
                       ▼
    ┌───────────────────────────────────────┐
    │ 4. BLEND WITH PRIOR                   │
    │                                       │
    │ w_posterior = 0.70 × w_prior          │
    │            + 0.30 × w_evidence        │
    │                                       │
    │ Normalize: Σ w_posterior = 1.0        │
    │                                       │
    │ Guard: MIN_OUTCOMES = 10              │
    │ Guard: max weight change ≤ 0.02/cycle │
    └──────────────────┬────────────────────┘
                       │
                       ▼
    ┌───────────────────────────────────────┐
    │ 5. WRITE CALIBRATION FILE             │
    │    strategy/outcome-calibration.yaml  │
    │                                       │
    │ Loaded by score.py get_weights()      │
    │ at next scoring cycle                 │
    └───────────────────────────────────────┘
```

---

## APPENDIX B: COMPLETE SCORING RUBRIC CONFIGURATION

### B.1 Scoring Rubric (strategy/scoring-rubric.yaml)

```yaml
version: "2.0"
description: >
  9-dimension weighted scoring rubric for pipeline entries.
  Source of truth for score.py weights and auto-qualify thresholds.
  Precision-over-volume: network_proximity added, throughput dimensions reduced.

# Precision weights for creative/grant/residency tracks (must sum to 1.0)
weights:
  mission_alignment: 0.25
  evidence_match: 0.20
  track_record_fit: 0.15
  network_proximity: 0.12
  strategic_value: 0.10
  financial_alignment: 0.08
  effort_to_value: 0.05
  deadline_feasibility: 0.03
  portal_friction: 0.02

# Precision weights for job track — network_proximity highest (referral = 8x)
weights_job:
  mission_alignment: 0.25
  evidence_match: 0.20
  network_proximity: 0.20
  track_record_fit: 0.15
  strategic_value: 0.10
  financial_alignment: 0.05
  effort_to_value: 0.03
  deadline_feasibility: 0.01
  portal_friction: 0.01

thresholds:
  auto_qualify_min: 9.0
  auto_advance_to_drafting: 9.5
  tier1_cutoff: 9.5
  tier2_cutoff: 8.5
  tier3_cutoff: 7.0
  score_range_min: 1
  score_range_max: 10

# Benefits cliff thresholds (annual USD)
benefits_cliffs:
  snap_limit: 20352
  medicaid_limit: 21597
  essential_plan_limit: 39125
```

### B.2 Dimension Definitions

| # | Dimension | Weight (Creative) | Weight (Job) | Description | Scale |
|---|-----------|-------------------|-------------|-------------|-------|
| 1 | `mission_alignment` | 0.25 | 0.25 | Degree to which the opportunity's mission, values, and organizational culture align with the applicant's identity, career goals, and values | 1 (no alignment) to 10 (perfect alignment) |
| 2 | `evidence_match` | 0.20 | 0.20 | Degree to which the applicant's portfolio, work samples, and documented evidence directly address the opportunity's stated requirements | 1 (no match) to 10 (complete match) |
| 3 | `track_record_fit` | 0.15 | 0.15 | Degree to which the applicant's career trajectory, skills, and experience match the opportunity's explicit and implicit requirements | 1 (no fit) to 10 (perfect fit) |
| 4 | `network_proximity` | 0.12 | 0.20 | Strength of the applicant's relationship to the target organization, measured via 6-signal aggregation with time decay | 1 (cold/unknown) to 10 (internal/embedded) |
| 5 | `strategic_value` | 0.10 | 0.10 | Long-term strategic benefit of the opportunity beyond immediate compensation, including career positioning, portfolio enhancement, and future optionality | 1 (no strategic value) to 10 (transformative) |
| 6 | `financial_alignment` | 0.08 | 0.05 | Degree to which the opportunity's compensation structure aligns with the applicant's financial needs, considering benefits cliff thresholds and market benchmarks | 1 (below survival) to 10 (optimal alignment) |
| 7 | `effort_to_value` | 0.05 | 0.03 | Ratio of expected effort (application preparation time, portal complexity, materials required) to expected value (probability-weighted compensation) | 1 (extremely poor) to 10 (minimal effort, high value) |
| 8 | `deadline_feasibility` | 0.03 | 0.01 | Feasibility of preparing a high-quality submission within the available time before the application deadline, accounting for other pipeline commitments | 1 (impossible) to 10 (ample time) |
| 9 | `portal_friction` | 0.02 | 0.01 | Inverse measure of the application portal's friction: account creation requirements, form complexity, attachment limitations, and submission workflow friction | 1 (maximum friction) to 10 (frictionless) |

### B.3 Weight Verification

**Creative Track Weights:**

Sum = 0.25 + 0.20 + 0.15 + 0.12 + 0.10 + 0.08 + 0.05 + 0.03 + 0.02 = **1.00** ✓

**Job Track Weights:**

Sum = 0.25 + 0.20 + 0.20 + 0.15 + 0.10 + 0.05 + 0.03 + 0.01 + 0.01 = **1.00** ✓

### B.4 Network Proximity Ordinal Scale

| Level | Score | Label | Description | Empirical Conversion Rate |
|-------|-------|-------|-------------|---------------------------|
| 0 | 1 | Cold | No connection to target organization | 2--5% (cold online) |
| 1 | 4 | Acquaintance | Aware of each other; LinkedIn connection, brief meeting, shared event | 5--8% (warm lead) |
| 2 | 7 | Warm | Active professional relationship; have had substantive conversations, mutual context | 15--25% (employee referral) |
| 3 | 9 | Strong | Close professional relationship; can request direct referral or advocacy; referrer has influence | 25--40% (strong referral) |
| 4 | 10 | Internal | Inside the organization (internal transfer, contractor-to-FTE, board member) | 40--60% (internal) |

### B.5 Six Network Proximity Signals

| Signal | Source Field | Score Contribution | Aggregation |
|--------|------------|-------------------|-------------|
| 1. Relationship strength | `network.relationship_strength` | Direct ordinal mapping to 1/4/7/9/10 | max |
| 2. Mutual connections | `network.mutual_connections` | 0 = 1, 1--2 = 4, 3--5 = 7, 6+ = 9 | max |
| 3. Follow-up response | `follow_up[].response` where response ∈ {replied, referred} | replied = 7, referred = 9, with time decay | max |
| 4. Referral channel | `conversion.channel` == "referral" | 9 | max |
| 5. Outreach completed | `outreach[].status` == "done" (recent, ≤60 days) | count 1 = 4, count 2+ = 7 | max |
| 6. Organizational density | Count of other entries at same org | 1 = 1, 2 = 4, 3+ = 7 | max |

### B.6 Time Decay Tiers for Network Signals

| Tier | Days Since Interaction | Label | Signal 3 (Follow-up) Minimum | Signal 5 (Outreach) |
|------|-----------------------|-------|-----------------------------|---------------------|
| Fresh | 0--30 | Full boost | min 7 (replied), min 9 (referred) | Full credit |
| Aging | 31--90 | Reduced boost | min 5 (replied), min 7 (referred) | Full credit |
| Stale | 91--180 | Minimal boost | min 3 (replied), min 5 (referred) | No credit |
| Expired | >180 | No boost | No contribution | No credit |
| Legacy | No date recorded | Benefit of doubt | min 7 (replied), min 9 (referred) | Full credit |

---

## APPENDIX C: MATHEMATICAL NOTATION REFERENCE

### C.1 Sets and Indices

| Symbol | Definition |
|--------|-----------|
| A | Set of all pipeline entries (alternatives) |
| a, a' | Individual pipeline entries |
| D = {d_1, ..., d_9} | Set of 9 scoring dimensions |
| Q = {q_1, ..., q_10} | State set of the pipeline FSM |
| T ⊂ Q | Set of transient states (|T| = 8) |
| A_s ⊂ Q | Set of absorbing states (|A_s| = 2) |
| i | Dimension index (i = 1, ..., 9) |
| j | State index (j = 1, ..., 10) |

### C.2 Scoring Functions

| Symbol | Definition | Domain |
|--------|-----------|--------|
| s_i(a) | Score of entry a on dimension i | {1, 2, ..., 10} |
| w_i | Weight for dimension i | (0, 1) |
| V(a) | Composite score for entry a: V(a) = Σ w_i × s_i(a) | [1.0, 10.0] |
| w* | Reservation score (qualification threshold) | Currently 9.0 |
| W | Weight vector (w_1, ..., w_9) | Σ w_i = 1.0 |
| W_c | Creative track weight vector (WEIGHTS) | Σ w_i = 1.0 |
| W_j | Job track weight vector (WEIGHTS_JOB) | Σ w_i = 1.0 |

### C.3 Network Proximity

| Symbol | Definition |
|--------|-----------|
| NP(a) | Network proximity score for entry a |
| sig_k(a) | k-th network signal for entry a (k = 1, ..., 6) |
| NP(a) = max_k{sig_k(a)} | Aggregation via max operator |
| τ(t) | Time decay function: τ(t) = tier based on days t since interaction |
| t_fresh | Fresh threshold = 30 days |
| t_aging | Aging threshold = 90 days |
| t_stale | Stale threshold = 180 days |

### C.4 Kelly Criterion

| Symbol | Definition |
|--------|-----------|
| f* | Optimal Kelly fraction: f* = (pb - q) / b |
| p | Probability of success (conversion rate) |
| q | Probability of failure: q = 1 - p |
| b | Net odds (payoff ratio: value gained / effort risked) |

### C.5 McCall Reservation Wage Model

| Symbol | Definition |
|--------|-----------|
| w̄ | Reservation wage (mapped to reservation score) |
| β | Discount factor (patience/runway parameter) |
| c | Per-period search cost |
| F(w) | CDF of offer distribution |
| V*(w) | Optimal value function: V*(w) = max{w/(1-β), c + β × E[V*(w')]} |

### C.6 Markov Chain

| Symbol | Definition |
|--------|-----------|
| P | Transition matrix (10 × 10) |
| Q | Sub-matrix of transition probabilities among transient states (8 × 8) |
| R | Sub-matrix of transition probabilities from transient to absorbing states (8 × 2) |
| N | Fundamental matrix: N = (I - Q)^{-1} |
| B | Absorption probability matrix: B = N × R |
| I | Identity matrix (8 × 8) |
| N_{ij} | Expected number of visits to state j before absorption, starting from state i |

### C.7 Information Theory

| Symbol | Definition |
|--------|-----------|
| H(X) | Shannon entropy of random variable X: H(X) = -Σ p(x) log₂ p(x) |
| I(X;Y) | Mutual information: I(X;Y) = H(X) - H(X\|Y) |
| C | Channel capacity: C = max_{p(x)} I(X;Y) |
| SNR | Signal-to-noise ratio |

### C.8 Portfolio Theory

| Symbol | Definition |
|--------|-----------|
| r_i | Expected return (conversion rate) for track i |
| σ_i | Standard deviation of returns for track i |
| σ_{ij} | Covariance between tracks i and j |
| ρ_{ij} | Correlation between tracks i and j |
| α_i | Portfolio allocation to track i (Σ α_i = 1) |

### C.9 Bayesian Outcome Learning

| Symbol | Definition |
|--------|-----------|
| w_prior | Prior weight vector (from scoring-rubric.yaml or previous calibration) |
| w_evidence | Evidence weight vector (from outcome analysis) |
| w_posterior | Posterior weight vector: w_posterior = 0.70 × w_prior + 0.30 × w_evidence |
| δ_i | Dimension accuracy: δ_i = mean(s_i \| accepted) - mean(s_i \| rejected) |
| n_min | Minimum outcomes for calibration activation = 10 |

---

## APPENDIX D: CODEBASE FUNCTION INDEX

### D.1 Core Libraries

| File | Function | Purpose | Lines |
|------|----------|---------|-------|
| `pipeline_lib.py` | `load_entries()` | Load all pipeline YAML entries from active/, submitted/, closed/ | ~50 |
| `pipeline_lib.py` | `load_profile()` | Load target profile JSON by entry ID | ~20 |
| `pipeline_lib.py` | `load_block()` | Load narrative block by category/name path | ~25 |
| `pipeline_lib.py` | `load_variant()` | Load A/B variant file by target and version | ~20 |
| `pipeline_lib.py` | `load_legacy_script()` | Load legacy submission content by ID mapping | ~30 |
| `pipeline_lib.py` | `update_yaml_field()` | Safe regex-based YAML field mutation with validation | ~60 |
| `pipeline_lib.py` | `get_strategic_base()` | Load strategic parameters from market intelligence JSON | ~20 |
| `pipeline_lib.py` | `get_portal_scores()` | Load portal friction scores from market intelligence | ~15 |
| `pipeline_lib.py` | `get_pipeline_mode()` | Determine current operational mode (precision/volume/hybrid) | ~20 |
| `pipeline_lib.py` | `get_mode_thresholds()` | Load mode-specific threshold parameters | ~15 |
| `pipeline_lib.py` | `get_entry_era()` | Classify entry as volume-era or precision-era by submission date | ~15 |

### D.2 Scoring Engine

| File | Function | Purpose | Lines |
|------|----------|---------|-------|
| `score.py` | `compute_dimensions()` | Extract and compute all 9 dimension scores from entry | ~40 |
| `score.py` | `compute_composite()` | WSM: V(a) = Σ w_i × s_i | ~15 |
| `score.py` | `get_weights()` | Track-specific + Bayesian-calibrated weight selection | ~30 |
| `score.py` | `score_network_proximity()` | 6-signal max-aggregated network scoring with time decay | ~120 |
| `score.py` | `analyze_reachability()` | Per-entry gap analysis: minimum network level for threshold | ~40 |
| `score.py` | `run_reachable()` | Display reachability for all actionable entries | ~30 |
| `score.py` | `run_triage_staged()` | Categorize staged entries into submit/hold/demote | ~50 |
| `score.py` | `run_auto_qualify()` | Promote research_pool entries above threshold to active/qualified | ~40 |
| `outcome_learner.py` | `collect_outcome_data()` | Scan closed/submitted entries for outcome-score pairs | ~40 |
| `outcome_learner.py` | `analyze_dimension_accuracy()` | Compute δ_i for each dimension | ~30 |
| `outcome_learner.py` | `compute_weight_recommendations()` | Generate evidence-based weight adjustments | ~40 |
| `outcome_learner.py` | `load_calibration()` | Load calibrated weights for score.py integration | ~20 |

### D.3 Pipeline Operations

| File | Function | Purpose |
|------|----------|---------|
| `advance.py` | `advance_entry()` | Transition entry between pipeline states with validation |
| `standup.py` | `run_standup()` | Generate daily dashboard with stale, deadline, priority sections |
| `campaign.py` | `run_campaign()` | Deadline-aware pipeline execution with urgency tiers |
| `agent.py` | `plan_actions()` | Autonomous pipeline state transition planning |
| `agent.py` | `execute_actions()` | Execute planned transitions with safety checks |
| `validate.py` | `validate_entry()` | Validate pipeline YAML against schema |
| `cultivate.py` | `get_cultivation_candidates()` | Identify entries where network cultivation unlocks threshold |
| `cultivate.py` | `suggest_actions()` | Generate concrete cultivation action recommendations |
| `cultivate.py` | `log_cultivation_action()` | Record cultivation actions in entry outreach[] |
| `enrich.py` | `enrich_entry()` | Wire materials, blocks, variants, portal_fields to entry |
| `enrich.py` | `enrich_network()` | Batch-populate network fields from existing signals |

### D.4 Composition Engine

| File | Function | Purpose |
|------|----------|---------|
| `compose.py` | `compose_submission()` | Assemble submission from blocks by target |
| `draft.py` | `draft_from_profile()` | Generate portal-ready drafts from profile JSON |
| `tailor_resume.py` | `tailor_resume()` | Generate HTML resume tailored to specific target |
| `build_resumes.py` | `build_pdf()` | Convert HTML resume to PDF via headless Chrome |
| `build_block_index.py` | `build_index()` | Regenerate block tag index from frontmatter |

### D.5 Analytics

| File | Function | Purpose |
|------|----------|---------|
| `funnel_report.py` | `run_funnel()` | Conversion funnel analytics with breakdowns |
| `conversion_report.py` | `run_conversion()` | Conversion rate report by track/position/score |
| `velocity_report.py` | `run_velocity()` | Submission velocity and pipeline throughput |
| `portfolio_analysis.py` | `run_portfolio()` | Multi-query portfolio analysis engine |
| `block_roi_analysis.py` | `run_block_roi()` | Block acceptance rate ROI analysis |
| `validate_hypotheses.py` | `run_validation()` | Hypothesis prediction accuracy assessment |
| `log_signal_action.py` | `log_signal()` | Signal-to-action audit trail recording |

### D.6 External Integrations

| File | Function | Purpose |
|------|----------|---------|
| `source_jobs.py` | `fetch_jobs()` | Auto-source job postings from ATS APIs |
| `greenhouse_submit.py` | `submit_application()` | POST application to Greenhouse Job Board API |
| `lever_submit.py` | `submit_application()` | Submit to Lever portal |
| `ashby_submit.py` | `submit_application()` | Submit to Ashby portal |
| `browser_submit.py` | `browser_submit()` | Playwright-based browser submission automation |
| `check_email.py` | `check_inbox()` | IMAP-based submission confirmation scanning |
| `market_intel.py` | `run_market_intel()` | Market intelligence CLI with track/calendar/salary views |

---

## APPENDIX E: PIPELINE ENTRY SCHEMA

### E.1 Required Fields

```yaml
# Minimal pipeline entry
id: "example-entry-2026"                    # Unique identifier (kebab-case)
status: "research"                          # Pipeline state
track: "job"                                # Application track
target:
  organization: "Example Corp"             # Target organization name
  role: "Senior Software Engineer"         # Position or program title
  application_url: "https://..."           # Portal URL
```

### E.2 Complete Schema

```yaml
# Complete pipeline entry (all fields)
id: "example-entry-2026"
status: "qualified"                          # research|qualified|drafting|staged|
                                             # submitted|acknowledged|interview|
                                             # outcome|deferred|withdrawn
track: "job"                                 # job|grant|residency|fellowship|
                                             # writing|prize|consulting|program|emergency

target:
  organization: "Example Corp"
  role: "Senior Software Engineer"
  application_url: "https://example.com/apply"
  portal: "greenhouse"                       # greenhouse|lever|ashby|custom|none
  department: "Engineering"
  location: "Remote"

# Identity mapping
identity_position: "independent-engineer"    # independent-engineer|systems-artist|
                                             # educator|creative-technologist|
                                             # community-practitioner

# Scoring (populated by score.py)
scoring:
  mission_alignment: 9
  evidence_match: 8
  track_record_fit: 9
  network_proximity: 7
  strategic_value: 8
  financial_alignment: 7
  effort_to_value: 8
  deadline_feasibility: 9
  portal_friction: 8
  composite: 8.47                            # WSM output
  scored_at: "2026-03-04"
  weight_config: "weights_job"               # Which weight vector was used

# Network relationship data
network:
  relationship_strength: "warm"              # cold|acquaintance|warm|strong|internal
  mutual_connections: 3
  referral_source: "Jane Doe"
  hydrated_from: "follow_up.response"        # Traceability for auto-hydration
  hydrated_at: "2026-03-04"

# Timeline
timeline:
  discovered: "2026-02-15"
  qualified: "2026-02-20"
  drafting_started: "2026-02-25"
  staged: "2026-03-01"
  submitted: "2026-03-04"
  last_touched: "2026-03-04"

deadline:
  date: "2026-03-15"
  type: "hard"                               # hard|soft|rolling

# Submission metadata
submission:
  effort: "standard"                         # quick|standard|deep|complex
  blocks_used:
    - "identity/2min"
    - "projects/organvm-system"
    - "framings/independent-engineer"
  materials_attached:
    - "resumes/batch-03/example-entry-2026/resume.pdf"
    - "materials/cover-letters/example-entry-2026.md"
  portal_fields:
    first_name: "Anthony"
    last_name: "Padavano"
    email: "..."
    phone: "..."
    linkedin: "..."

# Conversion tracking
conversion:
  channel: "referral"                        # cold|warm|referral|internal
  stage_reached: "interview"                 # highest stage reached
  outcome: "pending"                         # pending|accepted|rejected|
                                             # withdrawn|expired

# Follow-up protocol
follow_up:
  - date: "2026-03-05"
    channel: "linkedin"
    action: "connect"
    status: "done"
    contact: "Jane Doe"
    response: "replied"
    response_date: "2026-03-06"
  - date: "2026-03-12"
    channel: "linkedin"
    action: "dm"
    status: "planned"

# Outreach history (pre-submission cultivation)
outreach:
  - date: "2026-02-20"
    type: "pre_submission"
    channel: "linkedin"
    action: "connect"
    contact: "Jane Doe"
    status: "done"
    note: "Shared article on distributed systems"

# Deferral tracking (when status = deferred)
deferral:
  reason: "Application portal not yet open"
  resume_date: "2026-04-01"
  note: "Cycle opens Q2 2026"

# Research data (populated by source_jobs.py, distill_keywords.py)
research:
  source: "greenhouse_api"
  sourced_at: "2026-02-15"
  keywords:
    - "distributed systems"
    - "kubernetes"
    - "go"
  salary_range: "$180,000 - $220,000"
  company_size: "500-1000"
```

---

## APPENDIX F: COMPETITIVE PRODUCT DETAILED ASSESSMENTS

### F.1 Assessment Methodology

Each product was evaluated against the 12-dimension capability taxonomy defined in Section 4.3. Scoring uses a 3-level scale:

- **Full (1.0):** Complete implementation of the capability with configurability and integration
- **Partial (0.5):** Some implementation exists but lacks depth, configurability, or integration
- **None (0.0):** No implementation of the capability

Products were grouped into five categories: Applicant Tracking Systems (employer-side), Job Search Aggregators, Resume Optimization Tools, AI Application Assistants, and Career Strategy Platforms. Additionally, academic decision support systems documented in the literature were evaluated.

### F.2 Detailed Assessments

#### F.2.1 Category: Job Search Aggregators and Trackers

**Teal (teal.hq)** --- Score: 3.0/12

| Dimension | Score | Notes |
|-----------|-------|-------|
| Multi-criteria scoring | 0.5 | Basic job match scoring without configurable weights |
| Network proximity | 0.0 | No relationship tracking |
| Time-decayed network | 0.0 | N/A |
| Portfolio diversification | 0.0 | Job-only; no multi-track support |
| Reachability analysis | 0.0 | No gap analysis |
| Bayesian outcome learning | 0.0 | No adaptive calibration |
| Markov chain modeling | 0.5 | Basic pipeline stage tracking |
| Mode switching | 0.0 | No market-adaptive governance |
| Block-based composition | 0.5 | Template library with basic customization |
| Identity position framework | 0.0 | No audience-specific framing |
| Cultivation workflow | 0.0 | No relationship building features |
| Market intelligence | 0.5 | Basic salary data and company profiles |

**Huntr (huntr.co)** --- Score: 2.0/12

| Dimension | Score | Notes |
|-----------|-------|-------|
| Multi-criteria scoring | 0.0 | No scoring system |
| Network proximity | 0.0 | No relationship tracking |
| Time-decayed network | 0.0 | N/A |
| Portfolio diversification | 0.5 | Multiple boards (but all job-track) |
| Reachability analysis | 0.0 | No gap analysis |
| Bayesian outcome learning | 0.0 | No adaptive calibration |
| Markov chain modeling | 0.5 | Kanban-style pipeline stages |
| Mode switching | 0.0 | No market-adaptive governance |
| Block-based composition | 0.0 | No content composition |
| Identity position framework | 0.0 | No audience-specific framing |
| Cultivation workflow | 0.5 | Basic contact management |
| Market intelligence | 0.0 | No market data integration |

**LinkedIn Job Search** --- Score: 2.5/12

| Dimension | Score | Notes |
|-----------|-------|-------|
| Multi-criteria scoring | 0.5 | "Match" percentage (opaque algorithm) |
| Network proximity | 0.5 | Shows mutual connections at target org |
| Time-decayed network | 0.0 | No temporal dimension |
| Portfolio diversification | 0.0 | Jobs only |
| Reachability analysis | 0.0 | No gap analysis |
| Bayesian outcome learning | 0.0 | No learner |
| Markov chain modeling | 0.0 | No pipeline tracking |
| Mode switching | 0.0 | No governance modes |
| Block-based composition | 0.0 | No composition system |
| Identity position framework | 0.0 | Single profile for all targets |
| Cultivation workflow | 0.5 | InMail and connection features |
| Market intelligence | 0.5 | Salary insights, company pages |

#### F.2.2 Category: Resume Optimization Tools

**Jobscan** --- Score: 1.5/12

| Dimension | Score | Notes |
|-----------|-------|-------|
| Multi-criteria scoring | 0.5 | ATS keyword match score (single-dimension) |
| Network proximity | 0.0 | No relationship features |
| Time-decayed network | 0.0 | N/A |
| Portfolio diversification | 0.0 | Resume-only focus |
| Reachability analysis | 0.0 | No gap analysis |
| Bayesian outcome learning | 0.0 | No adaptive features |
| Markov chain modeling | 0.0 | No pipeline tracking |
| Mode switching | 0.0 | No governance |
| Block-based composition | 0.5 | Resume template customization |
| Identity position framework | 0.0 | No audience targeting |
| Cultivation workflow | 0.0 | No relationship features |
| Market intelligence | 0.0 | No market data |

**Rezi** --- Score: 1.0/12

| Dimension | Score | Notes |
|-----------|-------|-------|
| Multi-criteria scoring | 0.0 | No scoring |
| Network proximity | 0.0 | No relationship features |
| Time-decayed network | 0.0 | N/A |
| Portfolio diversification | 0.0 | Resume-only |
| Reachability analysis | 0.0 | No gap analysis |
| Bayesian outcome learning | 0.0 | No learning |
| Markov chain modeling | 0.0 | No tracking |
| Mode switching | 0.0 | No governance |
| Block-based composition | 0.5 | AI resume builder with templates |
| Identity position framework | 0.0 | No audience targeting |
| Cultivation workflow | 0.0 | No relationship features |
| Market intelligence | 0.5 | Basic job market data |

#### F.2.3 Category: AI Application Assistants

**LazyApply / EasyApply bots** --- Score: 0.5/12

| Dimension | Score | Notes |
|-----------|-------|-------|
| All dimensions | 0.0 or 0.5 | Extreme volume-optimization tools. Auto-submit hundreds of applications with zero quality control. Represent the antithesis of the precision pipeline philosophy. Score 0.5 on portal_friction automation only. |

#### F.2.4 Category: Career Strategy Platforms

**PathRise / Exponent / Interview Kickstart** --- Score: 1.5/12

| Dimension | Score | Notes |
|-----------|-------|-------|
| Multi-criteria scoring | 0.0 | Coaching-based, no algorithmic scoring |
| Network proximity | 0.5 | Mentorship matching and networking advice |
| Time-decayed network | 0.0 | N/A |
| Portfolio diversification | 0.0 | Role-specific coaching only |
| Reachability analysis | 0.0 | No gap analysis |
| Bayesian outcome learning | 0.0 | No data-driven learning |
| Markov chain modeling | 0.0 | No pipeline modeling |
| Mode switching | 0.0 | No governance |
| Block-based composition | 0.5 | Template-based preparation materials |
| Identity position framework | 0.0 | No structured positioning |
| Cultivation workflow | 0.0 | General networking advice but no workflow |
| Market intelligence | 0.0 | Anecdotal, not systematic |

### F.3 Summary Table

| Product/Category | Score | Closest Dimensions |
|-----------------|-------|-------------------|
| **Precision Pipeline** | **12.0/12** | All |
| Teal | 3.0/12 | Basic scoring, templates, salary |
| LinkedIn | 2.5/12 | Mutual connections, salary, InMail |
| Huntr | 2.0/12 | Boards, pipeline, contacts |
| Jobscan | 1.5/12 | ATS matching, templates |
| PathRise et al. | 1.5/12 | Networking, templates |
| Rezi | 1.0/12 | Templates, market data |
| Auto-apply bots | 0.5/12 | Portal automation only |

---

## APPENDIX G: RESEARCH AGENT METHODOLOGY

### G.1 AI-Assisted Research Protocol

This appendix documents the methodology for the AI-assisted research process used in the preparation of this thesis. The protocol follows the "AI-conductor" model described in Section 5.8.3: human direction, AI-assisted generation, human review and editorial control.

### G.2 Research Phases

**Phase 1: Literature Discovery.** Three research agents were deployed in parallel, each focused on a distinct domain:

1. **Hiring Curve Research Agent:** Tasked with gathering empirical data on application conversion rates, recruiter behavior, ATS usage statistics, referral multipliers, cover letter effectiveness, and timing/seasonality effects.

2. **Mathematical Theory Research Agent:** Tasked with gathering formal definitions, axiomatic foundations, and comparative analyses of MCDA methods (WSM, AHP, TOPSIS, ELECTRE, PROMETHEE), portfolio optimization theory, Kelly criterion derivation, McCall job search model, network centrality measures, decay functions, and signal detection theory.

3. **Pipeline Optimization Research Agent:** Tasked with gathering empirical evidence on social network effects in hiring (Granovetter, Rajkumar, Lin, Burt), persuasion science (Cialdini, Green & Brock, Petty & Cacioppo), information asymmetry (Spence, Akerlof, Rothschild & Stiglitz), grant peer review reliability, and the Matthew effect in funding.

**Phase 2: Source Verification.** All citations produced by research agents were verified against the original publications where accessible. Citations that could not be verified were either replaced with verified alternatives or qualified with appropriate hedging language. Industry reports and surveys were cross-referenced against multiple sources where possible.

**Phase 3: Theoretical Synthesis.** The integration of findings from six theoretical traditions (MCDA, social network theory, portfolio optimization, optimal stopping, information theory, persuasion science) into a unified framework was performed by the author with AI assistance for exposition but human control over the intellectual argument.

**Phase 4: Mathematical Proofs.** All formal proofs (Theorems 1--6) were constructed by the author using standard techniques from the cited theoretical frameworks. AI assistance was used for notation verification and proof exposition but not for the proof constructions themselves.

### G.3 Source Categories

| Category | Count | Primary Sources |
|----------|-------|-----------------|
| Academic journals | 35+ | *Quarterly Journal of Economics*, *Science*, *PNAS*, *American Journal of Sociology*, *Management Science*, *Operations Research*, *Bell System Technical Journal*, *Journal of Finance*, *Journal of Applied Psychology*, *Annual Review of Psychology* |
| Industry reports | 25+ | Indeed Hiring Lab, Greenhouse Software, LinkedIn Talent Solutions, ERIN, Ashby, JobVite, ZipRecruiter, CareerBuilder |
| Books/monographs | 15+ | Markowitz (1959), Keeney & Raiffa (1976), Cialdini (2006), Granovetter (1995), Kemeny & Snell (1960), Belton & Stewart (2002), Triantaphyllou (2000) |
| Conference proceedings | 5+ | ACM CIKM, ISPOR MCDA Task Force |
| Government/foundation data | 8+ | BLS, NEA, NSF, Creative Capital, Guggenheim Foundation |
| Technology platforms | 10+ | Layoffs.fyi, Jobscan, Teal, LinkedIn, Glassdoor |

### G.4 Limitations of the AI-Assisted Research Process

1. **Citation currency.** AI language models have knowledge cutoffs; some citations may not reflect the most recent editions or updates of cited works. All substantive claims were verified against available sources as of March 2026.

2. **Access limitations.** Not all cited works were available in full text for verification. Where only abstracts or secondary references were available, this is noted in the citation context.

3. **Potential for hallucinated statistics.** Industry statistics (e.g., specific conversion rates, survey percentages) cited from AI-generated research summaries carry a risk of fabrication. These statistics were cross-referenced against multiple sources where possible and should be treated as indicative rather than definitive where source verification was incomplete.

4. **Theoretical interpretation.** While the mathematical frameworks cited (WSM, Kelly, McCall, Markov chains) are well-established, their application to the career management domain is novel. The interpretations and mappings presented in this thesis are the author's original contribution and have not been independently validated by domain experts in each theoretical tradition.

### G.5 Reproducibility

The pipeline system described in this thesis is maintained as a production codebase consisting of:

- **30+ Python scripts** in `scripts/` directory
- **15,000+ lines of code** (excluding tests)
- **1,554 automated tests** (all passing at time of writing)
- **1,000+ pipeline YAML entries** across `pipeline/active/`, `pipeline/submitted/`, `pipeline/closed/`, and `pipeline/research_pool/`
- **Runtime dependency:** PyYAML only
- **Development dependencies:** pytest, ruff
- **Python version:** 3.11+ (tested on 3.14)

The scoring engine (`scripts/score.py`), outcome learner (`scripts/outcome_learner.py`), and pipeline state machine (`scripts/pipeline_lib.py`) are the core components whose mathematical properties are analyzed in this thesis. Interested researchers may examine the implementation to verify the formal properties claimed in Chapter 4.
