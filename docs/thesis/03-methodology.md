# CHAPTER 3 | METHODOLOGY

## 3.1 Research Design and Method

### 3.1.1 Design Science Research

This study employs a mixed-methods design science research (DSR) approach as formalized by Hevner, March, Park, and Ram (2004). Design science research contributes to the knowledge base through the construction and evaluation of artifacts --- systems, models, methods, or instantiations --- that address important organizational problems. Unlike behavioral science, which seeks to discover truth through the observation of existing phenomena, design science seeks to create value through the design of novel artifacts that extend the boundaries of human capability.

Hevner et al. (2004) establish seven guidelines for rigorous design science research:

1. **Design as an artifact:** The research must produce a viable artifact in the form of a construct, model, method, or instantiation. The precision pipeline satisfies this requirement as a production-deployed software system comprising 30+ Python scripts, 15,000+ lines of code, and 1,554 automated tests.

2. **Problem relevance:** The research must address an important and relevant problem. The application volume crisis documented in Chapter 2 --- with cold application conversion rates below 2%, 51,330 tech layoffs in Q1 2026, and no existing system combining MCDA with network analysis and portfolio optimization --- establishes problem relevance.

3. **Design evaluation:** The artifact must be rigorously evaluated. This study evaluates the pipeline through three methods: formal mathematical proof (Sections 3.4--3.8 and Chapter 4), systematic competitive analysis (Chapter 4, Section 4.3), and empirical pipeline data analysis (Chapter 4, Section 4.4).

4. **Research contributions:** The research must provide clear contributions. Four specific contributions are identified: integrated MCDA for applicant-side decisions, network-MCDA unification, Kelly criterion application to career strategy, and closed-loop outcome learning.

5. **Research rigor:** Rigorous methods must be applied in both construction and evaluation. Mathematical proofs use established theorems; competitive analysis follows a systematic 12-dimension taxonomy; empirical analysis uses era-separated cohort comparison.

6. **Design as a search process:** The design process is iterative. The v1-to-v2 evolution documents the iterative refinement cycle: v1 tested the volume hypothesis, which failed empirically (60 cold applications, 0 interviews), motivating the v2 precision redesign.

7. **Communication of research:** The research must be communicated to both technology-oriented and management-oriented audiences. This thesis serves both audiences through formal mathematical treatment (technology) and practical interpretation (management).

### 3.1.2 Mixed-Methods Integration

The study integrates three analytical methods:

**Method 1: Formal Mathematical Analysis.** Each major component of the pipeline is formalized using established mathematical frameworks and evaluated for optimality properties. The WSM scoring engine is analyzed under the Keeney-Raiffa additive value axioms. The Kelly criterion is applied to derive optimal effort allocation. The pipeline state machine is modeled as an absorbing Markov chain. Reachability analysis is formulated as sensitivity analysis on the network proximity dimension. Time decay is analyzed against exponential, step-function, and power-law models.

**Method 2: Systematic Competitive Evaluation.** A 12-dimension capability taxonomy, derived from the theoretical framework (Chapter 2, Section 2.12), is used to evaluate 60+ existing products, platforms, and academic prototypes. Each product is scored on a binary (0/1) or partial-credit (0/0.5/1) scale for each dimension. The methodology follows the structured literature review protocol of Kitchenham and Charters (2007), adapted for commercial product evaluation.

**Method 3: Empirical Pipeline Data Analysis.** The production pipeline's 1,000+ entries are analyzed using era-separated cohort comparison. Entries submitted before the precision pivot date (March 4, 2026) constitute the "volume era" cohort; entries submitted after constitute the "precision era" cohort. Metrics compared include composite score distributions, score component analysis, pipeline velocity (time in each state), and (where available) conversion outcomes.

### 3.1.3 Methodological Justification

The reliance on mathematical proof and competitive analysis rather than purely empirical outcome comparison is a deliberate methodological choice driven by two constraints:

First, the precision era began on March 4, 2026. At the time of writing, insufficient post-pivot outcome data has accumulated for statistically powered empirical comparison. Mathematical proof provides an alternative form of validation that is independent of sample size: if a theorem holds, it holds for all instances, not just the observed sample.

Second, ethical and practical constraints prevent a controlled experiment. The applicant cannot simultaneously pursue the same opportunity using both precision and volume strategies (the treatment and control conditions are mutually exclusive at the individual level). The pre-post design (volume era vs. precision era) is the strongest available quasi-experimental design given these constraints, but its statistical power depends on the number of post-pivot outcomes. Mathematical proof bridges this gap by establishing optimality properties that hold regardless of empirical sample size.

## 3.2 Population and Sample

### 3.2.1 Pipeline Population

The pipeline population consists of all entries created in the precision pipeline system from initial deployment (January 2026) through the data collection cutoff (March 31, 2026). This population encompasses:

- **Total entries:** 1,000+ across all directories (active/, submitted/, closed/, research_pool/)
- **Active entries:** Approximately 30 entries in active/ with actionable statuses (research, qualified, drafting, staged)
- **Research pool entries:** Approximately 948 entries in research_pool/ with research status (auto-sourced entries that have not yet been promoted to active)
- **Submitted entries:** Entries that have been submitted and are awaiting response
- **Closed entries:** Entries with terminal outcomes (accepted, rejected, withdrawn, expired)

### 3.2.2 Track Distribution

Entries span 9 application tracks:

| Track | Description | Expected Conversion | Weight Vector |
|-------|-------------|--------------------| --------------|
| job | Technology employment | 2--30% (channel-dependent) | WEIGHTS_JOB (network = 0.20) |
| grant | Creative/research funding | 2--15% (program-dependent) | WEIGHTS (network = 0.12) |
| residency | Artist/researcher residency | 3--10% | WEIGHTS |
| fellowship | Academic/professional fellowship | 5--20% | WEIGHTS |
| writing | Writing commissions/publications | 5--25% | WEIGHTS |
| prize | Awards and competitions | 2--8% | WEIGHTS |
| consulting | Freelance/consulting engagements | 10--40% | WEIGHTS |
| program | Academic programs/cohorts | 5--20% | WEIGHTS |
| emergency | Emergency financial support | 10--30% | WEIGHTS |

The dual weight vector system (WEIGHTS and WEIGHTS_JOB) reflects the differential importance of network proximity across tracks. For the job track, where the referral multiplier is most extensively documented (8x, per ERIN, 2024), network proximity receives a weight of 0.20 (the highest single weight after mission_alignment at 0.25). For creative tracks, where network effects are less dominant (panel review processes introduce substantial randomness, per Pier et al., 2018), network proximity receives 0.12.

### 3.2.3 Era Separation

The precision pivot date (March 4, 2026) serves as the natural boundary for cohort separation:

**Volume era (pre-pivot):** Entries submitted before March 4, 2026, processed under v1 rules: lower qualification threshold, no explicit network analysis, no reachability analysis, daily standup emphasizing throughput and volume pressure, shorter stale thresholds (7 days).

**Precision era (post-pivot):** Entries submitted on or after March 4, 2026, processed under v2 rules: 9.0 qualification threshold, network proximity as a first-class scoring dimension, reachability analysis, mode-based governance, relaxed stale thresholds (14 days), daily workflow emphasizing research and relationship cultivation.

The `get_entry_era()` function in `pipeline_lib.py` operationalizes this separation by classifying entries based on their `timeline.submitted` date relative to the pivot date constant `PRECISION_PIVOT_DATE = "2026-03-04"`.

### 3.2.4 Sampling Considerations

This study analyzes a census rather than a sample: all pipeline entries are included in the analysis. No sampling was necessary because the entire population is available and computationally tractable. However, the population itself is a convenience sample of opportunities visible to and selected by a single applicant, and the findings are therefore subject to the limitations discussed in Section 3.15.

## 3.3 System Architecture: v1 versus v2

### 3.3.1 v1 Architecture (Volume-Optimized)

The v1 system, deployed from January through early March 2026, implemented a volume-optimized tracking architecture with the following characteristics:

- **Entry management:** YAML files organized in active/ and submitted/ directories with manual status tracking
- **Status progression:** Linear advancement through statuses with minimal qualification gates
- **Scoring:** 8-dimension scoring without network proximity; lower weights on relationship-dependent dimensions
- **Qualification threshold:** 5.0--5.5 (track-dependent), allowing most entries to advance
- **Standup messaging:** Emphasis on output quantity ("How many entries advanced today?"), daily urgency, 7-day stale threshold
- **Relationship tracking:** None; no network fields, no cultivation workflow, no follow-up protocol
- **Outcome learning:** None; no feedback loop between outcomes and scoring weights
- **Content strategy:** Block library without identity position framework; less structured composition workflow

### 3.3.2 v2 Architecture (Precision-Optimized)

The v2 system, deployed beginning March 4, 2026, implements a precision-optimized decision engine with the following architectural innovations:

**Table 3.1: v1 versus v2 Feature Comparison**

| Dimension | v1 (Volume) | v2 (Precision) |
|-----------|-------------|----------------|
| Scoring dimensions | 8 | 9 (+ network_proximity) |
| Weight vectors | 1 (uniform) | 2 (creative, job) |
| Network analysis | None | 6-signal time-decayed proximity |
| Qualification threshold | 5.0--5.5 | 9.0 (mode-adjustable) |
| Max active entries | Unlimited | 10 |
| Max weekly submissions | Unlimited | 1--2 |
| Stale threshold | 7 days | 14 days |
| Stagnant threshold | 14 days | 30 days |
| Outcome learning | None | Bayesian (70/30 blend) |
| Relationship cultivation | None | cultivate.py workflow |
| Reachability analysis | None | Per-entry gap analysis |
| Mode governance | None | Precision/Volume/Hybrid |
| Research pool | Flat directory | Separated (research_pool/) |
| Identity positions | None | 5 canonical positions |
| Content architecture | Flat blocks | Storefront/Cathedral tiers |
| Time decay | None | Step-function (30/90/180d) |
| Company cap | None | 1 per organization |
| Daily workflow | 5hr output-focused | 2hr research, 2hr relationships, 1hr application |

### 3.3.3 Architectural Rationale

The v2 architecture was not designed ab initio from theoretical principles; it evolved iteratively from v1 in response to empirical failure. The inciting event was the submission of 60 cold applications in four days under v1 rules, which produced zero interviews. This outcome, documented in the system's own conversion logs, triggered a systematic review of the theoretical literature (Chapter 2) and the redesign described in this chapter.

Each v2 feature can be traced to a specific theoretical justification:

| v2 Feature | Theoretical Basis |
|------------|-------------------|
| 9-dimension scoring | MCDA (Fishburn, 1967; Dawes, 1979) |
| Dual weight vectors | Domain-specific weight optimization |
| Network proximity scoring | Granovetter (1973), Lin (2001), Burt (1992) |
| 9.0 qualification threshold | McCall reservation wage (1970) |
| Max 10 active entries | Kelly criterion bet sizing (Kelly, 1956) |
| Bayesian outcome learning | Bayesian updating (Berger, 1985) |
| Time-decayed signals | Burt (2000), Ebbinghaus (1885) |
| Multi-track portfolio | Markowitz diversification (1952) |
| Storefront/Cathedral content | Shannon channel capacity (1948) |
| Relationship cultivation | Cialdini reciprocity (2006) |

## 3.4 The Weighted Sum Model Scoring Engine

### 3.4.1 Formal Specification

The pipeline's scoring engine implements the Weighted Sum Model as defined in Chapter 2, Section 2.4.2. For a pipeline entry a, the composite score V(a) is computed as:

V(a) = Sum_{i=1}^{9}(w_i * s_i(a))

where:
- s_i(a) is the score of entry a on dimension i, with s_i in {1, 2, ..., 10}
- w_i is the weight of dimension i, with Sum_{i=1}^{9}(w_i) = 1.0 and w_i > 0 for all i
- The composite V(a) is in [1.0, 10.0]

**Proof of boundedness.** Since each s_i is in [1, 10] and each w_i > 0 with Sum(w_i) = 1:

V_min = Sum(w_i * 1) = Sum(w_i) = 1.0
V_max = Sum(w_i * 10) = 10 * Sum(w_i) = 10.0

Therefore V(a) is in [1.0, 10.0] for all entries a and all weight configurations satisfying the constraints. This boundedness is preserved regardless of the specific weight values, providing a stable, interpretable score range.

### 3.4.2 The Nine Dimensions

Each scoring dimension is computed from data fields in the pipeline YAML entry. The computation is deterministic: identical entry data always produces identical dimension scores.

**Dimension 1: mission_alignment (w_creative = 0.25, w_job = 0.25).** Quantifies the degree of alignment between the applicant's expertise and the target's stated requirements. Computed from keyword overlap between the entry's requirement fields and the applicant's canonical competency tags. Score range: 1 (no alignment) to 10 (complete alignment).

**Dimension 2: evidence_match (w_creative = 0.20, w_job = 0.20).** Quantifies the degree to which the applicant can provide direct evidence (work samples, portfolio items, case studies) addressing the target's requirements. Computed from the presence and quality of matched materials in the submission block library.

**Dimension 3: track_record_fit (w_creative = 0.15, w_job = 0.15).** Quantifies the relevance of the applicant's prior experience to the target role. Computed from a combination of signals including organization type match, industry alignment, seniority level fit, and skill overlap. The dimension is further decomposed into four sub-signals: relevance breadth, depth match, position seniority alignment, and differentiator presence.

**Dimension 4: network_proximity (w_creative = 0.12, w_job = 0.20).** Quantifies the strength and freshness of the applicant's relationship to the target organization. This dimension is described in full detail in Section 3.5.

**Dimension 5: strategic_value (w_creative = 0.10, w_job = 0.10).** Quantifies the long-term strategic value of the opportunity beyond immediate conversion. Considers factors including skill development, portfolio expansion, network expansion, and positioning for future opportunities.

**Dimension 6: financial_alignment (w_creative = 0.08, w_job = 0.05).** Quantifies the degree to which the opportunity's compensation aligns with the applicant's financial requirements. Includes benefits cliff awareness (SNAP limit at $20,352, Medicaid at $21,597, Essential Plan at $39,125) to flag opportunities whose compensation would trigger loss of public benefits.

**Dimension 7: effort_to_value (w_creative = 0.05, w_job = 0.03).** Quantifies the ratio of expected effort (application preparation, portal completion, follow-up) to expected value (conversion probability * outcome value). Higher scores indicate higher value per unit of effort.

**Dimension 8: deadline_feasibility (w_creative = 0.03, w_job = 0.01).** Quantifies the feasibility of meeting the application deadline given current workload and preparation status. Computed from the `deadline.date` field relative to the current date, with consideration of effort classification and current active entry count.

**Dimension 9: portal_friction (w_creative = 0.02, w_job = 0.01).** Quantifies the submission friction of the target's application portal. Portal friction scores are loaded from `strategy/market-intelligence-2026.json`, which assigns friction ratings to known portals (Greenhouse, Lever, Ashby, Workday, iCIMS, etc.) based on field count, required document types, and manual entry requirements. Lower friction portals receive higher scores (friction is a cost dimension, inverted).

### 3.4.3 Weight Configuration

The weight vectors are defined in `strategy/scoring-rubric.yaml`:

**Creative/Grant/Residency weights (WEIGHTS):**
```
mission_alignment:   0.25
evidence_match:      0.20
track_record_fit:    0.15
network_proximity:   0.12
strategic_value:     0.10
financial_alignment: 0.08
effort_to_value:     0.05
deadline_feasibility: 0.03
portal_friction:     0.02
Sum:                 1.00
```

**Job track weights (WEIGHTS_JOB):**
```
mission_alignment:   0.25
evidence_match:      0.20
network_proximity:   0.20
track_record_fit:    0.15
strategic_value:     0.10
financial_alignment: 0.05
effort_to_value:     0.03
deadline_feasibility: 0.01
portal_friction:     0.01
Sum:                 1.00
```

The key difference between weight vectors is the network_proximity weight: 0.12 for creative tracks versus 0.20 for the job track. This reflects the differential referral multiplier effect documented in Chapter 2 (Section 2.5): in the job market, referrals produce an 8x hiring rate advantage (ERIN, 2024), while in creative funding, panel review processes introduce substantial reviewer variance (Pier et al., 2018), diluting the network effect.

### 3.4.4 Axiom Verification for the Career Application Domain

The WSM is provably optimal when four axioms hold (Keeney & Raiffa, 1976). This section verifies each axiom for the career application domain:

**Axiom 1: Commensurability.** All dimensions must be measured on a common scale. The pipeline scores all dimensions on the same integer scale [1, 10]. This satisfies commensurability by construction --- no normalization is required because the measurement scale is uniform.

**Axiom 2: Mutual Preferential Independence (MPI).** The preference ordering over any subset of dimensions must be independent of the levels of the remaining dimensions. For the pipeline's 9 dimensions:
- Preference for higher mission_alignment does not depend on the level of portal_friction (one can assess mission fit without knowing how the portal works)
- Preference for higher network_proximity does not depend on the level of deadline_feasibility (having a better connection is always preferred regardless of the deadline)
- And so on for all dimension pairs

MPI is a reasonable assumption for the pipeline's dimensions because they measure genuinely distinct aspects of the application opportunity. The potential exception is the interaction between network_proximity and effort_to_value (higher network proximity may reduce effort through referral streamlining), but this interaction is captured within the effort_to_value dimension's computation rather than requiring a multiplicative interaction term.

**Axiom 3: Additivity.** The value function must be additive (no interaction effects). As argued above, the dimensions are designed to measure independent aspects of fit, and any interactions are captured within individual dimension computations rather than between dimensions.

**Axiom 4: Monotonicity.** Preference must be monotonic in each criterion. All 9 dimensions are "benefit" criteria: more mission_alignment, more evidence_match, more network_proximity, etc. are always preferred. Portal_friction is the most subtle: the raw construct (friction) is a cost, but the dimension score inverts the scale so that higher scores indicate *lower* friction, maintaining monotonicity.

### 3.4.5 The Qualification Threshold

The auto-qualify threshold of 9.0/10 functions as McCall's (1970) reservation wage in the scoring domain. The threshold defines the minimum composite score below which opportunities are not pursued, regardless of other factors.

**Threshold calibration.** The 9.0 threshold is set at the 89th percentile of the feasible scoring range [1.0, 10.0]. This reflects the precision strategy's emphasis on pursuing only the highest-fit opportunities. The threshold is mode-adjustable:

| Mode | auto_qualify_min | max_active | max_weekly_submissions |
|------|-----------------|------------|----------------------|
| Precision | 9.0 | 10 | 2 |
| Volume | 7.0 | 30 | 10 |
| Hybrid | 8.0 | 15 | 5 |

The mode system operationalizes the McCall comparative statics: when financial pressure requires faster conversion, the threshold is lowered (volume mode); when runway permits selectivity, the threshold is raised (precision mode).

**Cold application impossibility.** Under the job track weight configuration, a cold-network entry (network_proximity = 1) cannot reach 9.0 even with perfect scores on all other dimensions:

V_max_cold = 0.25(10) + 0.20(10) + 0.20(1) + 0.15(10) + 0.10(10) + 0.05(10) + 0.03(10) + 0.01(10) + 0.01(10) = 2.5 + 2.0 + 0.2 + 1.5 + 1.0 + 0.5 + 0.3 + 0.1 + 0.1 = 8.2

Since 8.2 < 9.0, it is **mathematically impossible** for a cold-network job-track entry to reach the qualification threshold. This is not a bug; it is a designed structural enforcement: the weight configuration requires network cultivation as a prerequisite for job-track qualification.

For creative tracks (network_proximity weight = 0.12):

V_max_cold_creative = 0.25(10) + 0.20(10) + 0.15(10) + 0.12(1) + 0.10(10) + 0.08(10) + 0.05(10) + 0.03(10) + 0.02(10) = 2.5 + 2.0 + 1.5 + 0.12 + 1.0 + 0.8 + 0.5 + 0.3 + 0.2 = 8.92

At 8.92, cold-network creative entries *barely* fall below the 9.0 threshold even with perfect scores on all other dimensions. This creates a softer constraint for creative tracks, where panel-based review introduces enough randomness to justify occasional cold submissions for exceptionally well-matched opportunities.

## 3.5 Network Proximity Scoring with Time Decay

### 3.5.1 The Network Proximity Dimension

Network proximity is the fourth scoring dimension and the most architecturally significant innovation of the v2 system. It quantifies the strength and freshness of the applicant's relationship to the target organization, operationalizing the social capital theories of Granovetter (1973), Lin (2001), and Burt (1992) into a numerical scoring dimension.

### 3.5.2 Ordinal Scale

Network proximity is measured on a 5-level ordinal scale mapped to integer scores:

| Level | Score | Description | Empirical Basis |
|-------|-------|-------------|-----------------|
| Cold | 1 | No relationship to anyone at the organization | Baseline: 2% conversion (Indeed, 2025) |
| Acquaintance | 4 | Shared community, event, or platform connection | Weak tie: ~5% conversion (Granovetter, 1973) |
| Warm | 7 | Active communication, mutual connection with introduction | Moderate weak tie: ~15% conversion (Rajkumar et al., 2022) |
| Strong | 9 | Direct referral from current employee or champion | Referral: 28--30% hire rate (ERIN, 2024) |
| Internal | 10 | Direct relationship with hiring manager | Internal: 40--60% conversion (SHRM, 2024) |

The non-linear spacing (1, 4, 7, 9, 10) reflects the non-linear relationship between tie strength and conversion probability. The gap between cold (1) and acquaintance (4) is larger than the gap between strong (9) and internal (10), consistent with Rajkumar et al.'s (2022) finding of an inverted U-shaped relationship between tie strength and job transmission probability: the largest marginal gains come from moving from cold to weak-tie connections, with diminishing returns at higher tie strengths.

### 3.5.3 Six-Signal Aggregation

The network proximity score is computed as the maximum across six independent signals, each of which can independently establish a minimum score:

**Signal 1: Explicit relationship_strength.** The entry's `network.relationship_strength` field provides the base score via the ordinal map above. This is the primary signal, set through manual assessment or automated hydration (`enrich.py --network`).

**Signal 2: Referral channel.** If `conversion.channel == "referral"`, the minimum score is 8, reflecting a known referral pathway regardless of the explicit relationship_strength setting.

**Signal 3: Follow-up responses (time-decayed).** If any `follow_up[]` entry has `response in ("replied", "referred")`, the minimum score depends on the freshness of the response:

| Response Age | Minimum Score | Tier |
|-------------|---------------|------|
| <= 30 days | 7 | Fresh |
| <= 90 days | 5 | Aging |
| <= 180 days | 3 | Stale |
| > 180 days | 0 (no boost) | Expired |
| No date | 7 (benefit of doubt) | Legacy |

This time decay reflects Burt's (2000) observation that professional network value decays substantially within 3--6 months of last contact. The "benefit of doubt" rule for entries without dates preserves backward compatibility with legacy data created before the time decay system was implemented.

**Signal 4: Mutual connections.** If `network.mutual_connections >= 5`, the minimum score is 5. This reflects Lin's (2001) social capital theory: a concentration of mutual connections at a single organization indicates embedded social resources.

**Signal 5: Outreach actions (time-decayed).** Completed outreach actions (`outreach[].status == "done"`) contribute to the score if they are recent (within 60 days):
- 2+ recent completed outreach actions: minimum score 5
- 1 recent completed outreach action: minimum score 4
- Outreach older than 60 days: no boost

**Signal 6: Organizational density.** The number of other pipeline entries at the same organization provides an indirect measure of familiarity:
- 3+ other entries at the same org: minimum score 4
- 1--2 other entries at the same org: minimum score 3

The **max operator** aggregation means that the highest signal wins. This is a deliberate design choice: a single strong signal (e.g., a referral channel) should not be diluted by the absence of other signals. An entry with a direct referral (Signal 2: min 8) but no mutual connections (Signal 4: no boost) receives a score of 8, not an average of 8 and 1.

### 3.5.4 Time Decay Model

The time decay model uses a step function with four tiers:

```
_NETWORK_DECAY = {
    "response_fresh": 30,    # days - full boost
    "response_aging": 90,    # reduced boost
    "response_stale": 180,   # minimal boost
    "outreach_stale": 60,    # done outreach older than this gives no boost
}
```

**Theoretical justification for step-function over exponential.** As discussed in Chapter 2 (Section 2.5.5), the exponential decay model f(t) = f_0 * e^{-lambda*t} is the most theoretically principled time decay model. However, the step function is more appropriate for the pipeline's context for three reasons:

1. **Date resolution.** Pipeline entries record dates at day-level granularity, not hour or minute level. The precision of the date data is insufficient to support continuous decay; a step function matches the data resolution.

2. **Behavioral meaningfulness.** The tiers correspond to behaviorally meaningful distinctions: "contacted last week" (fresh) is categorically different from "contacted three months ago" (aging), which is categorically different from "contacted six months ago" (stale). The step function captures these categorical distinctions directly.

3. **Implementational transparency.** The step function is immediately interpretable by the user: "your contact with this person was 45 days ago, which puts it in the 'aging' tier." Exponential decay would produce a continuous value (e.g., 0.71) that requires additional explanation.

The error introduced by using a step function rather than continuous exponential decay is bounded by the tier width. Within each tier, the maximum error is the difference between the step function value and the exponential value at the tier boundary. For practical purposes, this error is dominated by the much larger uncertainty in the relationship between contact freshness and actual conversion probability.

## 3.6 Pipeline State Machine as Absorbing Markov Chain

### 3.6.1 State Machine Definition

The pipeline's status progression is defined as a finite state machine (FSM) with 10 states and defined transitions. Formally:

**Definition.** Let M = (S, T, s_0, F) where:
- S = {research, qualified, drafting, staged, submitted, acknowledged, interview, outcome, withdrawn, deferred} is the set of 10 states
- T: S x S -> {0, 1} is the transition relation (1 if the transition is valid, 0 otherwise)
- s_0 = research is the initial state
- F = {outcome, withdrawn} is the set of terminal (absorbing) states

The valid transitions, as defined in `pipeline_lib.py`:

```
VALID_TRANSITIONS = {
    "research":     {"qualified", "withdrawn"},
    "qualified":    {"drafting", "staged", "deferred", "withdrawn"},
    "drafting":     {"staged", "qualified", "deferred", "withdrawn"},
    "staged":       {"submitted", "drafting", "deferred", "withdrawn"},
    "deferred":     {"staged", "qualified", "drafting", "withdrawn"},
    "submitted":    {"acknowledged", "interview", "outcome", "withdrawn"},
    "acknowledged": {"interview", "outcome", "withdrawn"},
    "interview":    {"outcome", "withdrawn"},
    "outcome":      {},
    "withdrawn":    {},
}
```

The state machine enforces forward-only progression through the primary pipeline path (research -> qualified -> drafting -> staged -> submitted -> acknowledged -> interview -> outcome) with lateral transitions to deferred (hold) and backward transitions from drafting/staged/deferred back to qualified (re-evaluation). The terminal states outcome and withdrawn have no valid outgoing transitions.

### 3.6.2 Absorbing Markov Chain Formulation

The pipeline state machine can be modeled as an absorbing Markov chain --- a stochastic process where some states are absorbing (once entered, never left) and from every non-absorbing (transient) state, it is possible to reach at least one absorbing state.

**Definition.** An absorbing Markov chain is characterized by a transition probability matrix P that can be written in canonical form:

P = | Q  R |
    | 0  I |

where:
- Q is a t x t matrix giving transition probabilities between transient states (t = |S| - |F| = 8)
- R is a t x r matrix giving transition probabilities from transient to absorbing states (r = |F| = 2)
- 0 is an r x t zero matrix (absorbing states never transition to transient states)
- I is an r x r identity matrix (absorbing states stay absorbed)

**Transient states (t = 8):** research, qualified, drafting, staged, submitted, acknowledged, interview, deferred

**Absorbing states (r = 2):** outcome, withdrawn

### 3.6.3 The Fundamental Matrix

**Theorem (Kemeny & Snell, 1960).** The fundamental matrix N = (I - Q)^{-1} exists and has the following interpretations:

- N_{ij} is the expected number of times the chain visits transient state j, given that it starts in transient state i, before absorption.
- The sum of the i-th row of N gives the expected number of steps before absorption when starting in state i.

**Theorem.** The absorption probability matrix B = NR gives:
- B_{ij} is the probability that the chain is absorbed in absorbing state j, given that it starts in transient state i.

These results provide computable answers to practically relevant questions:
- "Starting from research, how many times does a typical entry visit the drafting state before reaching outcome?" (Read from N)
- "What is the expected number of pipeline steps from staged to absorption?" (Row sum of N)
- "Given that an entry is currently in submitted status, what is the probability it reaches outcome versus withdrawn?" (Read from B)

### 3.6.4 Estimation of Transition Probabilities

The transition probabilities in Q and R are estimated from the observed transition frequencies in the pipeline's data. For each pair of states (s_i, s_j) where T(s_i, s_j) = 1:

p_{ij} = (number of observed transitions from s_i to s_j) / (total transitions from s_i)

At the current stage of the pipeline, some transitions have sparse observations (particularly in the post-pivot precision era). The fundamental matrix analysis is therefore presented as a methodological capability rather than a fully calibrated empirical model. As the pipeline accumulates more transition data, the Q and R matrices will be refined, and the fundamental matrix predictions can be validated against observed absorption patterns.

### 3.6.5 Practical Applications of the Markov Chain Model

The Markov chain formulation enables several practical analyses:

**Expected pipeline length.** The row sums of N predict how many state transitions a typical entry undergoes before reaching a terminal state. This informs workload planning: entries that are expected to traverse many states (high row sum) require more sustained attention.

**Bottleneck identification.** High values in specific columns of N indicate states where entries "pile up" --- they are visited many times before progressing. If N_{drafting} is high, it suggests that the drafting -> staged transition is a bottleneck requiring intervention.

**Withdrawal versus outcome probability.** The B matrix decomposition reveals whether entries from a given starting state are more likely to reach outcome (success or rejection) or withdrawal (applicant-initiated exit). High withdrawal probability from a specific state may indicate that the state's requirements are too demanding or that the information available at that state frequently reveals deal-breaking issues.

## 3.7 Reachability Analysis as Sensitivity Analysis

### 3.7.1 Motivation

Reachability analysis addresses a specific operational question: "For a given pipeline entry, what is the minimum relationship level needed to push the composite score above the qualification threshold?" This question is fundamental to the relationship cultivation workflow, as it determines which entries are worth investing cultivation effort in and how much improvement is needed.

### 3.7.2 Formal Definition

**Definition.** For an entry a with current dimension scores s = (s_1, ..., s_9), weight vector w = (w_1, ..., w_9), and qualification threshold theta, the entry is **reachable** if there exists a network proximity level l in {cold, acquaintance, warm, strong, internal} such that:

V(a | s_4 = l_score) = Sum_{i != 4}(w_i * s_i) + w_4 * l_score >= theta

where l_score is the integer score corresponding to level l (cold=1, acquaintance=4, warm=7, strong=9, internal=10) and dimension 4 is network_proximity.

**Computation.** The minimum required network proximity score is:

s_4_required = (theta - Sum_{i != 4}(w_i * s_i)) / w_4

The entry is reachable if s_4_required <= 10 (the maximum network proximity score). The **reachable_with** level is the minimum ordinal level whose score exceeds s_4_required.

### 3.7.3 Reachability Scenarios

**Table 3.7: Reachability by Network Level and Track**

| Starting Score (all other dims = 8) | Network Required (Job Track, w=0.20) | Network Required (Creative, w=0.12) |
|------|------|------|
| 7.0 | (9.0 - 6.4) / 0.20 = 13.0 -> UNREACHABLE | (9.0 - 7.04) / 0.12 = 16.3 -> UNREACHABLE |
| 7.5 | (9.0 - 6.8) / 0.20 = 11.0 -> UNREACHABLE | (9.0 - 7.44) / 0.12 = 13.0 -> UNREACHABLE |
| 8.0 | (9.0 - 7.2) / 0.20 = 9.0 -> STRONG (9) | (9.0 - 7.84) / 0.12 = 9.7 -> INTERNAL (10) |
| 8.5 | (9.0 - 7.6) / 0.20 = 7.0 -> WARM (7) | (9.0 - 8.24) / 0.12 = 6.3 -> WARM (7) |
| 9.0 | Already above threshold | (9.0 - 8.64) / 0.12 = 3.0 -> ACQUAINTANCE (4) |

This analysis reveals the practical implication of the weight structure: for job-track entries with moderate scores on other dimensions (8/10), a warm relationship (score = 7) is sufficient to reach the threshold, but a cold application (score = 1) leaves the entry far below qualification. The reachability analysis thus provides specific, actionable guidance for cultivation effort: "Build a warm connection at this organization, and the entry qualifies."

### 3.7.4 Reachability as Sensitivity Analysis

Reachability analysis is formally a single-variable sensitivity analysis on the network proximity dimension. It answers the question: "Holding all other dimensions constant, how sensitive is the qualification decision to changes in network proximity?"

The sensitivity of the composite score to network proximity changes is:

dV/ds_4 = w_4

This is constant (the WSM is linear in each dimension), so the sensitivity is directly proportional to the network proximity weight: 0.20 for job track, 0.12 for creative tracks. A one-unit increase in network proximity score changes the composite by 0.20 (job) or 0.12 (creative).

## 3.8 Bayesian Outcome Learning

### 3.8.1 Motivation and Architecture

The Bayesian outcome learning system closes the feedback loop between submission outcomes and scoring weights. Without outcome learning, the scoring system operates on expert-assigned weights that may not optimally predict conversion outcomes. With outcome learning, the system converges toward empirically optimal weights as outcome data accumulates.

### 3.8.2 Implementation

The outcome learning system (`outcome_learner.py`) operates in four stages:

**Stage 1: Data Collection.** The `collect_outcome_data()` function scans closed/ and submitted/ entries for those with outcome fields and pre-outcome dimension scores. Each qualifying entry yields a record containing: entry_id, outcome (accepted/rejected/withdrawn/expired), composite_score, dimension_scores (dict), track, and identity_position.

**Stage 2: Dimension Accuracy Analysis.** The `analyze_dimension_accuracy()` function compares average dimension scores for accepted versus rejected entries. For each dimension i:

delta_i = mean(s_i | outcome = accepted) - mean(s_i | outcome = rejected)

The signal is categorized as:
- **Overweighted:** delta_i < -0.5 (rejected entries scored *higher* on this dimension, suggesting the weight is misallocated)
- **Underweighted:** delta_i > 1.5 (accepted entries scored much higher, suggesting the dimension is more important than its current weight reflects)
- **Neutral:** -0.5 <= delta_i <= 1.5

**Stage 3: Weight Recommendation.** The `compute_weight_recommendations()` function adjusts weights by redistributing 0.02 weight units from overweighted to underweighted dimensions. The adjustment is conservative (0.02 per cycle) to prevent oscillation. After adjustment, weights are renormalized to sum to 1.0.

**Stage 4: Bayesian Blending.** The `get_weights()` function in `score.py` blends calibrated weights with base weights:

w_posterior = 0.70 * w_prior + 0.30 * w_calibrated

This 70/30 blend ratio reflects a conservative Bayesian prior: the expert-assigned weights (informed by the literature review) are given 70% influence, while the empirical calibration receives 30%. This ratio ensures that:

1. The system does not overfit to small samples (when n < 10, calibration is suppressed entirely)
2. Expert knowledge from the theoretical framework is preserved
3. The system converges gradually rather than jumping to empirically-derived weights that may reflect noise

After blending, weights are renormalized: w_final = w_posterior / Sum(w_posterior), ensuring they continue to sum to 1.0.

### 3.8.3 Convergence Properties

**Theorem.** Under the assumption that the calibrated weights w_calibrated converge to a fixed point w* (the empirically optimal weights) as the sample size increases, the blended weights w_posterior converge to:

w_converged = 0.70 * w_prior + 0.30 * w*

This is not the empirically optimal w* but a blend that incorporates expert judgment. The rationale for not converging to pure w* is that expert-assigned weights encode theoretical knowledge (e.g., the importance of network proximity based on the Granovetter/Rajkumar literature) that may not be fully captured in the pipeline's own outcome data, which is limited to a single user's experience.

**Safeguards.** Three safeguards prevent degenerate weight configurations:
1. **Minimum outcomes:** Calibration is suppressed when n < MIN_OUTCOMES_FOR_CALIBRATION (10)
2. **Minimum weight:** No dimension weight can fall below 0.01 (ensuring all dimensions contribute)
3. **Normalization:** Weights are always renormalized to sum to 1.0 after any adjustment

## 3.9 The Relationship Cultivation Subsystem

### 3.9.1 Architecture

The relationship cultivation subsystem (`cultivate.py`) bridges the gap between scoring and action by translating reachability analysis results into concrete relationship-building tasks. The subsystem imports `analyze_reachability()` from `score.py` and `identify_referral_candidates()` from `warm_intro_audit.py`.

### 3.9.2 Candidate Selection

The `get_cultivation_candidates()` function identifies entries where network improvement could push the composite score above the qualification threshold. The selection criteria are:

1. Entry has an actionable status (research, qualified, drafting, staged)
2. Entry's current composite score is below the threshold (9.0 in precision mode)
3. Entry is reachable (there exists a network proximity level that would push it above the threshold)
4. Entry is not deferred or withdrawn

Candidates are sorted by the "gap" --- the difference between the current composite and the threshold --- with the smallest gaps (closest to qualifying) prioritized, as these require the least cultivation effort to unlock.

### 3.9.3 Action Suggestion

The `suggest_actions()` function generates concrete, score-aware cultivation recommendations. For a given candidate, it:

1. Identifies the current network proximity level
2. Computes the target level needed to reach the threshold
3. Translates the target level into specific actions (e.g., "LinkedIn connect would move network 1->4, adding +0.6 pts for creative track, +0.8 pts for job track")
4. Estimates the score impact of each action

### 3.9.4 Theoretical Grounding

The cultivation workflow operationalizes three theoretical principles:

**Cialdini's reciprocity principle:** The workflow emphasizes providing value before requesting referrals. Cultivation actions are structured in a sequence: (1) research the contact and their work, (2) provide value (share relevant content, make introductions, comment substantively on their work), (3) establish rapport through non-transactional interaction, (4) make the referral request only after reciprocity debt is established.

**Granovetter's weak ties theory:** The workflow targets acquaintance-level connections that can serve as bridges to target organizations, consistent with the finding that moderately weak ties are the most effective for job transmission (Rajkumar et al., 2022).

**Burt's structural holes:** The workflow prioritizes building connections that span structural holes between the applicant's current professional network and target organizations, maximizing the non-redundant information access that Burt (1992, 2004) identifies as the primary benefit of structural hole-spanning connections.

## 3.10 Mode Switching and Adaptive Governance

### 3.10.1 Three Operational Modes

The pipeline operates in one of three modes, each defined by a set of threshold parameters:

| Parameter | Precision | Volume | Hybrid |
|-----------|-----------|--------|--------|
| auto_qualify_min | 9.0 | 7.0 | 8.0 |
| max_active | 10 | 30 | 15 |
| max_weekly_submissions | 2 | 10 | 5 |
| stale_days | 14 | 7 | 10 |
| stagnant_days | 30 | 14 | 21 |

### 3.10.2 Theoretical Justification

The mode system operationalizes the McCall (1970) comparative statics (Chapter 2, Section 2.6.2):

- **Precision mode** corresponds to the high-reservation-wage regime: the applicant has sufficient runway and patience to wait for optimal opportunities. This is the default mode in the current market environment.
- **Volume mode** corresponds to the low-reservation-wage regime: financial pressure requires faster conversion, justifying lower thresholds and higher throughput.
- **Hybrid mode** represents the intermediate regime, appropriate when the applicant has moderate runway or when market conditions are mixed.

Mode selection is governed by market conditions and applicant circumstances. The `get_pipeline_mode()` function loads the current mode from `strategy/market-intelligence-2026.json`, which includes a `pivot_date`, `review_date`, and `revert_trigger` specifying the conditions under which mode should be reassessed.

### 3.10.3 Mode as Constraint, Not Override

A critical design principle is that mode can only *raise* thresholds, not lower them below the mode's floor. The `_mode_adjusted_threshold()` function in `agent.py` ensures that autonomous pipeline actions never violate mode constraints:

```python
def _mode_adjusted_threshold(base_threshold, mode_thresholds):
    """Mode can only raise, not lower."""
    mode_min = mode_thresholds.get("auto_qualify_min", base_threshold)
    return max(base_threshold, mode_min)
```

This prevents the agent from lowering standards below what the current mode permits, even if other conditions might suggest relaxation.

## 3.11 Data Collection Methods and Instruments

### 3.11.1 Pipeline YAML as Data Instrument

Each pipeline entry is stored as a YAML file containing structured fields that serve as the primary data collection instrument. The schema (`pipeline/_schema.yaml`) defines required and optional fields across several categories:

**Identification fields:** id, title, track, status, tags
**Target fields:** organization, role_title, application_url, portal, location
**Fit assessment:** score, dimensions, identity_position, notes
**Network fields:** relationship_strength, mutual_connections, contact_name, contact_role
**Timeline fields:** discovered, qualified, submitted, deadline
**Submission fields:** materials_attached, blocks_used, cover_letter, portal_fields
**Follow-up fields:** follow_up[] (date, method, contact, response, notes)
**Outreach fields:** outreach[] (type, status, date, channel, contact, note)
**Conversion fields:** channel, outcome, outcome_date, stage_reached

### 3.11.2 Market Intelligence Database

The market intelligence database (`strategy/market-intelligence-2026.json`) provides time-varying strategic parameters including:

- Portal friction scores for known ATS platforms
- Salary benchmarks by role and market
- Grant calendar with upcoming deadlines
- Hot skills data from LinkedIn and Indeed
- Conversion benchmarks from industry reports

This database is updated manually from 112 sources reviewed quarterly, with a freshness warning system (`--staleness` flag) that identifies data older than 6 months.

### 3.11.3 Signal Collection

Conversion and signal data are collected in three structured YAML files:

- `signals/conversion-log.yaml`: Records each status transition, submission event, and outcome event with timestamps
- `signals/outreach-log.yaml`: Records each outreach action (LinkedIn connect, DM, email) with dates and response status
- `signals/signal-actions.yaml`: Records each decision triggered by a pipeline signal (score change, threshold crossing, agent action)

## 3.12 Data Analysis Methods

### 3.12.1 Score Distribution Analysis

Composite scores are analyzed by era (volume vs. precision), track, and identity position. The analysis computes:
- Mean, median, standard deviation, and interquartile range for each cohort
- Score component analysis: contribution of each dimension to the composite, weighted by the dimension weight
- Network proximity impact: maximum achievable score by network level and track

### 3.12.2 Conversion Funnel Analysis

The conversion funnel is analyzed at each pipeline stage:
- Stage distribution: count of entries in each status
- Stage-to-stage conversion rates: proportion of entries that advance versus withdraw or stall
- Velocity metrics: mean and median time in each status
- Channel-specific conversion: rates broken down by referral versus cold versus other channels

### 3.12.3 Competitive Analysis Methodology

Each competitive product is evaluated against the 12-dimension capability taxonomy using a structured assessment protocol:
1. Product documentation review (website, help center, API documentation)
2. Free trial or demo evaluation (where available)
3. Published customer reviews and case studies
4. Academic publications describing the system's methodology (for academic prototypes)

Scoring uses a three-level scale: 0 (capability absent), 0.5 (partial implementation), 1.0 (full implementation matching the taxonomy definition). Two independent raters assess each product, with disagreements resolved through discussion.

## 3.13 Validity and Reliability

### 3.13.1 Internal Validity

Internal validity --- the degree to which observed effects can be attributed to the intervention rather than confounding variables --- is addressed through multiple strategies:

**Mathematical proof** eliminates confounding by establishing results that hold under all conditions satisfying the axioms, not just the observed data. If the WSM boundedness proof holds, it holds for all possible entries, not just those in the current pipeline.

**Era-separated cohort comparison** controls for temporal confounding to the extent that the volume era and precision era differ primarily in the pipeline strategy applied, not in the external market conditions. However, the pivot date (March 4, 2026) also coincides with evolving market conditions, creating a potential confound that cannot be fully controlled.

**Automated scoring** eliminates scorer bias: identical entry data always produces identical scores, regardless of when or by whom the scoring is triggered. This addresses the consistency advantage that Dawes (1979) identifies as the primary benefit of linear models.

### 3.13.2 External Validity

External validity --- the degree to which findings generalize beyond the study context --- is limited by the single-user deployment (L1), the specific labor market context (L5), and the specific track mix. The mathematical proofs are user-independent (they hold for any applicant facing the same structural problem), providing a form of generalizability that does not depend on the empirical sample. The competitive analysis results are generalizable to the extent that the 12-dimension taxonomy captures the relevant capabilities for career decision support.

### 3.13.3 Reliability

Reliability --- the degree to which results are reproducible --- is ensured by:
- **Deterministic scoring:** The scoring engine is a pure function: identical inputs produce identical outputs. The 1,554 automated tests verify this property.
- **Version-controlled configuration:** All scoring weights, thresholds, and mode parameters are version-controlled in YAML configuration files, enabling exact reproduction of any historical scoring run.
- **Documented methodology:** The mathematical formalizations in this chapter specify every computation in sufficient detail for independent reimplementation.

## 3.14 Ethical Considerations

### 3.14.1 Data Privacy

All pipeline data is generated through the author's own career activities. No third-party personal data is collected, stored, or analyzed. Contact names appearing in pipeline entries are stored locally and are not transmitted to any external service.

### 3.14.2 Informed Consent

No human subjects were studied; the pipeline analyzes the author's own decision-making process and its outcomes. IRB review is not required for self-study research that does not involve other human participants.

### 3.14.3 Algorithmic Fairness Considerations

The scoring system is used for self-selection (the applicant deciding which opportunities to pursue), not for evaluating other people. As discussed in Chapter 2 (Section 2.4.6, algorithmic fairness), this substantially changes the fairness calculus: there is no disparate impact concern in the traditional sense because the system scores opportunities, not individuals.

However, structural bias can enter the system through dimensions that reflect existing social capital inequality. The network_proximity dimension inherently advantages applicants with larger or better-positioned professional networks. The system's design mitigates this concern in two ways: (1) the relationship cultivation workflow provides a mechanism for building network capital rather than merely measuring it, and (2) the mode system allows threshold adjustment when existing network capital is insufficient.

### 3.14.4 AI-Assisted Research Ethics

Large language models were used as research assistants for literature discovery, citation verification, mathematical exposition, and draft generation. All substantive claims, proofs, and interpretations are the author's own. The methodology follows the "AI-conductor" model: human direction, AI-assisted generation, human review and editorial control. This approach is documented transparently in the acknowledgments and is consistent with emerging academic standards for AI-assisted research (Nature, 2023; Science, 2023).

## 3.15 Limitations

### 3.15.1 Methodological Limitations

**L1: Single-user deployment.** The pipeline serves one applicant. All empirical results derive from a single user's career activities. Multi-user validation would strengthen generalizability claims.

**L2: Early precision era.** Limited post-pivot outcome data constrains empirical validation. The methodological choice to emphasize mathematical proof addresses this limitation.

**L3: Absence of controlled experiment.** The pre-post quasi-experimental design cannot rule out temporal confounds (market conditions changing simultaneously with the strategy pivot).

**L4: Expert-assigned weights.** Weights are assigned through expert judgment informed by market research, not derived through formal AHP pairwise comparison. The Bayesian outcome learning system provides a convergence mechanism.

### 3.15.2 Technical Limitations

**L5: Static dimension set.** The 9 dimensions are fixed by design. No mechanism exists for automatically discovering new relevant dimensions from data.

**L6: Maximum operator for network signals.** The max-aggregation of 6 network signals discards information about signal concordance. A weighted combination might better capture the joint effect of multiple weak signals.

**L7: Step-function time decay.** The step function introduces discontinuities at tier boundaries. Entries one day apart at a tier boundary receive different scores despite having essentially identical freshness.

These limitations are acknowledged not as fatal flaws but as design choices with known trade-offs. Each represents a simplification that prioritizes implementational clarity and interpretability over theoretical purity --- a trade-off that Dawes (1979) suggests is the correct one for practical decision support systems.
