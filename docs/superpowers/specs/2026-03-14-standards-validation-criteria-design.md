# Standards & Validation of Criteria — Design Specification

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-STANDARDS-001 |
| **Version** | 1.3 |
| **Date** | 2026-03-14 |
| **Owner** | @4444J99 |
| **Status** | Draft |
| **Scope** | Meta-ORGANVM system-wide (application-pipeline is the reference implementation) |
| **Review** | v1.0: 3 critical, 4 important, 5 suggestions → fixed in v1.1. v1.1: 6 inaccurate validators, 2 consistency issues → fixed in v1.2. v1.2 → v1.3: scope expansion to meta-organvm + epistemological grounding |

---

## 1. Problem Statement

### 1.1 Immediate Problem (Application Pipeline)

The application-pipeline has accumulated validation infrastructure across ~6 files (`validate.py`, `validate_signals.py`, `verification_matrix.py`, `audit_system.py`, `diagnose.py`, `test_math_proofs.py`) but lacks:

1. A **unified standards document** — criteria are scattered, no single source of truth
2. A **validation framework** that catches cross-cutting gaps — individual validators don't cross-check each other
3. **Acceptance criteria for system health** — no definition of "passing" for the system as a whole
4. **External validity grounding** — internal consistency is verified, but nothing proves the criteria themselves reflect reality

The system needs two levels of standards validation:

- **Level A — Internal Grading Criteria**: The scoring rubric grades pipeline entries (jobs via `weights_job`, funding via `weights`). Standards here ensure the grader applies its own rules correctly.
- **Level B — External Review System ("Watchers of the Watchmen")**: The meta-system grades the grading system itself. Standards here ensure the grader is trustworthy — and that the evidence base underlying its criteria is grounded in external reality.

### 1.2 Systemic Scope (Meta-ORGANVM)

This standards framework is designed for **meta-organvm-wide application**, not just this pipeline. The application-pipeline serves as the **reference implementation** — the first organ to adopt the framework — but the architecture is organ-agnostic. Any ORGANVM organ with a grading rubric, diagnostic script, and outcome data can instantiate the same five-level hierarchy with its own domain-specific gates.

The five-level hierarchy maps onto the ORGANVM eight-organ model:
- Each organ defines its own Level 1-2 gates (entry scoring, schema enforcement) specific to its domain
- Level 3 (system quality) uses the shared diagnostic/IRA infrastructure already designed for cross-organ use (see `docs/sop--diagnostic-inter-rater-agreement.md` Appendix B)
- Levels 4-5 (outcome accreditation, source legitimacy) are inherently cross-organ — the evidence base is shared across the system

### 1.3 Epistemological Foundation

**Nothing built prior to this system is authoritative.** All thresholds, weights, multipliers, and benchmarks currently in the pipeline were constructed *before* any formal validation framework existed. They are provisional assumptions — useful starting points, but not validated truths.

This system is designed to become the **truth-source**: a cascade of logic checks that synthesizes external truths (derived from domain-specific evidence collection) with internal logic (derived from those sources). The five-level hierarchy operationalizes this epistemology:

- **Levels 1-3** verify internal consistency — "does the system do what it says it does?"
- **Level 4** verifies empirical grounding — "does what the system says actually correspond to outcomes?"
- **Level 5** verifies epistemic credibility — "are the sources underlying the system's claims legitimate?"

Every existing value in the system begins at `evidence_status: assumed`. The framework's purpose is to either **validate** those assumptions through cascading evidence checks, or **flag them for revision** when the evidence doesn't support them. This is not a one-time audit but a continuous epistemic engine.

---

## 2. Design Approach: Standards Registry

A centralized registry pattern:

- `strategy/system-standards.yaml` — machine-readable source of truth defining every system-wide criterion (Level 1 per-entry standards are documented but executed separately)
- `scripts/standards.py` — registry module mapping standards to validator functions
- `docs/system-standards.md` — human-readable companion reference
- Existing validators remain unchanged — the registry wraps and orchestrates them
- **New code required** for Level 4-5 gates that have no existing implementation (see Section 13)

### 2.1 Portability Across Organs

The architecture separates **framework** (organ-agnostic) from **implementation** (organ-specific):

| Layer | Portable? | What Changes Per Organ |
|-------|-----------|----------------------|
| `GateResult`, `LevelReport`, `BoardReport` data classes | Yes — shared | Nothing |
| `StandardsBoard` orchestrator | Yes — shared | Nothing |
| `_run_gate()`, `_run_subprocess_gate()` helpers | Yes — shared | Nothing |
| Five regulator class interfaces | Yes — shared | Nothing |
| Gate *implementations* inside regulators | **No** — organ-specific | Different validators, rubrics, schemas |
| `system-standards.yaml` criteria | **No** — organ-specific | Different standards per organ |

When another organ adopts the framework, it instantiates the same five classes but fills in its own gate logic. The quorum rule, hierarchical cascade, evidence lifecycle, and board report format are universal.

---

## 3. Conceptual Framework: Tiers vs. Levels

Two orthogonal classification systems govern this framework. They are **not interchangeable**.

### 3.1 Tiers (Enforcement Severity)

Tiers define **how strictly** a standard is enforced:

| Tier | Name | Gate Type | Consequence of Failure |
|------|------|-----------|----------------------|
| 1 | Operational Integrity | Hard | CI blocks merge |
| 2 | Systemic Quality | Soft | Diagnostic score drops, flagged in reports |
| 3 | Empirical Validity | Advisory | Flagged as unvalidated; upgrades to soft once `min_sample` met |

### 3.2 Levels (Jurisdictional Scope)

Levels define **who watches whom** — the hierarchical chain of oversight:

| Level | Name | Scope | Academic Analogue |
|-------|------|-------|-------------------|
| 1 | Course | Individual entry evaluation | Instructor |
| 2 | Department | Rubric compliance, schema | Chair / Dean |
| 3 | University | System quality, consistency | Board / Provost |
| 4 | National | Predictive validity | Accreditors |
| 5 | Federal | Source credibility | Dept. of Education |

### 3.3 Tier × Level Cross-Reference

Each standard belongs to exactly one level (jurisdiction) and one tier (severity). The mapping:

| Level | Default Tier | Rationale |
|-------|-------------|-----------|
| 1 — Course | Tier 1 (hard) | Scoring errors directly harm entries; runtime enforcement |
| 2 — Department | Tier 1 (hard) | Schema/rubric violations are objective bugs; CI gate |
| 3 — University | Tier 2 (soft) | Quality is measured on a continuum, not binary |
| 4 — National | Tier 3 → 2 (advisory → soft) | Advisory until outcome data reaches `min_sample`, then soft |
| 5 — Federal | Tier 3 (advisory) | Source quality assessment is informational; no auto-enforcement |

Individual standards within a level may override the default tier (e.g., a Level 3 standard like `math_proofs_pass` could be Tier 1/hard because it's binary).

---

## 4. Standards YAML Schema

`strategy/system-standards.yaml` — the single source of truth.

```yaml
version: "1.0"

tiers:
  1:
    name: Operational Integrity
    description: Does the system work as specified?
    gate: hard
  2:
    name: Systemic Quality
    description: Is the system well-built?
    gate: soft
  3:
    name: Empirical Validity
    description: Are the criteria grounded in reality?
    gate: advisory

standards:
  # ── Level 2 / Tier 1: Department (Schema Enforcement) ─────
  weight_sum_general:
    level: 2
    tier: 1
    category: scoring
    track: [job, funding]
    description: General scoring weights sum to 1.0
    check: abs(sum - 1.0) < 0.001
    validator: validate.validate_scoring_rubric
    source: strategy/scoring-rubric.yaml

  weight_sum_job:
    level: 2
    tier: 1
    category: scoring
    track: [job]
    description: Job scoring weights sum to 1.0
    check: abs(sum - 1.0) < 0.001
    validator: validate.validate_scoring_rubric
    source: strategy/scoring-rubric.yaml

  weight_sum_system_grading:
    level: 2
    tier: 1
    category: scoring
    description: System grading rubric weights sum to 1.0
    check: abs(sum - 1.0) < 0.001
    validator: audit_system.audit_logic
    source: strategy/system-grading-rubric.yaml

  state_machine_valid:
    level: 2
    tier: 1
    category: pipeline
    description: All entry status transitions follow VALID_TRANSITIONS
    validator: validate.validate_entry

  dimensions_consistent:
    level: 2
    tier: 1
    category: wiring
    description: DIMENSION_ORDER == rubric keys == VALID_DIMENSIONS
    validator: audit_system.audit_wiring

  threshold_ordering:
    level: 2
    tier: 1
    category: scoring
    description: tier1_cutoff > tier2_cutoff > tier3_cutoff
    validator: audit_system.audit_logic

  high_prestige_ranges:
    level: 2
    tier: 1
    category: constants
    description: All HIGH_PRESTIGE org scores in 1-10
    validator: audit_system.audit_wiring

  role_fit_tier_ranges:
    level: 2
    tier: 1
    category: constants
    description: All ROLE_FIT_TIERS dimension scores in 1-10
    validator: audit_system.audit_wiring

  rubric_weights_match_code:
    level: 2
    tier: 1
    category: wiring
    description: scoring-rubric.yaml weights == score.py _DEFAULT_WEIGHTS
    validator: audit_system.audit_wiring

  system_rubric_matches_diagnose:
    level: 2
    tier: 1
    category: wiring
    description: system-grading-rubric.yaml dims == diagnose.py collectors+generators
    validator: audit_system.audit_wiring

  lint_clean:
    level: 2
    tier: 1
    category: code_quality
    description: Zero ruff lint errors in scripts/ and tests/
    validator: subprocess  # Runs: python -m ruff check scripts/ tests/
    command: [python, -m, ruff, check, scripts/, tests/]

  tests_pass:
    level: 2
    tier: 1
    category: code_quality
    description: Full pytest suite passes
    validator: subprocess  # Runs: python -m pytest tests/ -q
    command: [python, -m, pytest, tests/, -q]

  verification_matrix_complete:
    level: 2
    tier: 1
    category: code_quality
    description: All modules have corresponding test coverage
    validator: subprocess  # Runs: python scripts/verification_matrix.py --strict
    command: [python, scripts/verification_matrix.py, --strict]

  signal_integrity:
    level: 2
    tier: 1
    category: data
    description: All signal YAML files pass schema and referential integrity
    validator: validate_signals.validate_all_signals

  # ── Level 3 / Tier 2: University (System Quality) ─────────
  icc_agreement:
    level: 3
    tier: 2
    category: ira
    description: Inter-rater agreement on system quality
    threshold: 0.61     # Landis & Koch "substantial"
    target: 0.81        # "almost perfect"
    validator: diagnose_ira.compute_icc

  claim_provenance_ratio:
    level: 3
    tier: 2
    category: integrity
    description: Proportion of statistical claims with sources
    threshold: 0.80     # 80% sourced or cited
    target: 1.0
    validator: audit_system.audit_claims

  diagnostic_composite:
    level: 3
    tier: 2
    category: quality
    description: System diagnostic composite score
    threshold: 6.0
    target: 8.0
    validator: diagnose.compute_composite

  wiring_integrity:
    level: 3
    tier: 2
    category: integrity
    description: All wiring checks pass
    threshold: 1.0      # 100% pass rate
    validator: audit_system.audit_wiring

  logical_consistency:
    level: 3
    tier: 2
    category: integrity
    description: All logic checks pass
    threshold: 1.0
    validator: audit_system.audit_logic

  math_proofs_pass:
    level: 3
    tier: 1            # Override: binary check, hard gate
    category: integrity
    description: All mathematical certifications pass
    validator: subprocess  # Runs: python -m pytest tests/test_math_proofs.py -q
    command: [python, -m, pytest, tests/test_math_proofs.py, -q]

  # ── Level 4 / Tier 3: National (Outcome Accreditation) ────
  weight_outcome_correlation:
    level: 4
    tier: 3
    category: calibration
    description: Dimension weights predict actual outcomes
    min_sample: 30
    threshold: 0.3      # Minimum correlation coefficient
    validator: standards.compute_dimension_correlation  # NEW — see Section 13.1
    evidence_status: assumed

  weight_drift:
    level: 4
    tier: 3
    category: calibration
    description: Current weights within acceptable drift of empirical optimum
    min_sample: 30
    threshold: 0.15     # Max average weight delta
    validator: standards.compute_weight_drift  # NEW wrapper — calls outcome_learner.compute_weight_drift(), see Section 13.6
    evidence_status: assumed

  hypothesis_accuracy:
    level: 4
    tier: 3
    category: calibration
    description: Pre-recorded predictions match actual outcomes
    min_sample: 10
    threshold: 0.5      # >50% prediction accuracy
    validator: standards.compute_hypothesis_accuracy  # NEW — wraps outcome_learner, see Section 13.2
    evidence_status: assumed

  # ── Level 5 / Tier 3: Federal (Source Legitimacy) ──────────
  source_quality:
    level: 5
    tier: 3
    category: provenance
    description: Statistical claims backed by credible sources
    quality_tiers:
      peer_reviewed: 4
      industry_report: 3
      content_marketing: 2
      opinion: 1
      unsourced: 0
    threshold: 2.5
    validator: standards.check_source_quality  # NEW — see Section 13.3

  benchmark_alignment:
    level: 5
    tier: 3
    category: provenance
    description: Pipeline metrics align with external industry baselines
    threshold: 0.7      # >=70% of benchmarks within expected range
    validator: standards.check_benchmark_alignment  # NEW — see Section 13.4

  source_freshness:
    level: 5
    tier: 3
    category: provenance
    description: Cited sources are current (not stale)
    threshold: 0.8      # >=80% of sources published within 2 years
    max_age_years: 2
    validator: standards.check_source_freshness  # NEW — see Section 13.5
```

### Standard Properties

| Property | Type | Description |
|----------|------|-------------|
| `level` | int (1-5) | Jurisdictional level (who watches whom) |
| `tier` | int (1-3) | Enforcement severity (hard/soft/advisory) |
| `category` | string | Grouping: scoring, pipeline, wiring, constants, ira, integrity, quality, calibration, provenance, code_quality, data |
| `track` | list, optional | Scopes to job/funding/both |
| `description` | string | What this standard requires |
| `check` | string, optional | Human-readable formula |
| `threshold` | float, optional | Minimum acceptable value |
| `target` | float, optional | Aspirational value |
| `validator` | string | `module.function` reference, or `subprocess` for command-line checks |
| `command` | list, optional | Shell command (when `validator: subprocess`) |
| `source` | string, optional | File path where the standard is defined |
| `min_sample` | int, optional | (Tier 3) Minimum data points before standard is enforceable |
| `evidence_status` | string, optional | (Tier 3) `assumed` until `min_sample` met, then `validated` |
| `quality_tiers` | object, optional | (Tier 3) Source credibility tier definitions |
| `max_age_years` | int, optional | (Tier 3) Maximum age for cited sources |

**Note:** The YAML above shows the comprehensive initial registry. Additional standards may be added over time following the same schema.

---

## 5. Five-Level Hierarchical Oversight Architecture

Modeled on the academic oversight hierarchy (Instructor → Chair → Board → Accreditors → Dept. of Education). The critical property: **no level watches itself.** Each level is overseen by an independent authority above it.

### 5.1 Level Mapping

| Level | Academic Analogue | Pipeline Level | Pipeline Watchman | Jurisdiction | Question |
|-------|-------------------|----------------|-------------------|--------------|----------|
| **1 — Course** | Instructor | Entry Scoring | `score.py` | Individual entry evaluation | "Was this entry scored correctly?" |
| **2 — Department** | Chair / Dean | Schema Enforcement | `validate.py` | Rubric compliance, schema, enums | "Does the scorer follow the syllabus?" |
| **3 — University** | Board / Provost | System Quality | `diagnose.py` + `audit_system.py` + IRA | Institutional consistency & quality | "Is the institution well-run?" |
| **4 — National** | Accreditors (peer review) | Outcome Accreditation | `outcome_learner.py` + `recalibrate.py` | Predictive validity of criteria | "Do the criteria actually work?" |
| **5 — Federal** | Dept. of Education | Source & Benchmark Grounding | Source quality + market benchmarks | Credibility of the evidence base | "Are the validators' sources legitimate?" |

### 5.2 Enforcement Classification

| Level | Gate Type | Failure Consequence |
|-------|-----------|---------------------|
| 1 | Runtime | Entry gets wrong score → rescore |
| 2 | CI hard gate | Merge blocked until schema/rubric fixed |
| 3 | Soft standard | Diagnostic score drops, IRA flags divergence |
| 4 | Advisory → soft | Weight marked `assumed` until outcome data validates it |
| 5 | Advisory | Source downgraded, claim flagged as ungrounded |

### 5.3 Hierarchy Enforcement

```
Level 5: Source Legitimacy
  ↑ watches
Level 4: Outcome Accreditation
  ↑ watches
Level 3: System Quality
  ↑ watches
Level 2: Schema Enforcement
  ↑ watches
Level 1: Entry Scoring
```

Each level only has jurisdiction over the one directly below — Level 4 doesn't check schema compliance, Level 2 doesn't assess source quality. Clean separation of concerns.

Each level's output feeds into the level above:
- Level 2 failures block CI → Level 3 measurements are meaningless if Level 2 fails
- Level 3 scores feed into Level 4 → can't assess empirical validity if the system isn't internally consistent
- Level 4-5 findings feed back down → recalibration adjusts Level 2 weights when empirical evidence shows they're wrong

---

## 6. The Pipeline Triad

Mirroring the education "Triad" — three independent external mechanisms, not one monolithic checker:

### 6.1 Outcome Accreditation (≈ accrediting agencies)
- `outcome_learner.py` performs "peer review" of dimension weights
- If a weight is not predictive of outcomes after N=30 samples, it loses accreditation — marked `assumed`, not `validated`
- Analogous to losing accreditation: an unvalidated weight still functions but carries a warning

### 6.2 Market Alignment (≈ state authorization)
- Market intelligence benchmarks (`strategy/market-intelligence-2026.json`) provide external reference points
- Pipeline conversion rates, response times, and channel effectiveness are compared against industry baselines
- If the pipeline's reality diverges significantly from market benchmarks, the benchmarks need re-sourcing or the pipeline's model needs adjustment

### 6.3 Source Legitimacy (≈ Dept. of Education watching the accreditors)
- Every statistical claim gets a **source quality tier**:
  - **4 — Peer-reviewed**: Academic study, government data (BLS, Census)
  - **3 — Industry report**: LinkedIn Economic Graph, Glassdoor data
  - **2 — Content marketing**: ResumeGenius, Resume Now (useful but promotional)
  - **1 — Opinion/anecdotal**: Blog posts, single-person experience
  - **0 — Unsourced**: No attribution at all
- This watches the *watchers' evidence* — not just "does a citation exist?" but "is the citation credible?"

---

## 7. Five Levels × Three Regulators (Triad Per Level)

Each level is **one regulatory body** containing **three logic gates** within its domain. The body is the unit of execution; the gates are its internal assessment dimensions.

### 7.1 Level 1 — Course (Entry Scoring)

| Regulator | Role | What It Checks | Delegates To |
|-----------|------|----------------|--------------|
| **Rubric Scorer** | Gate 1A | Applies weighted dimensions to produce entry score | `score.py:compute_dimensions()` + `score.py:compute_composite()` (exist) |
| **Evidence Validator** | Gate 1B | Independent TF-IDF signal — does content match opportunity? | `text_match.py:analyze_entry()` → `cosine_similarity()` (exist) |
| **Historical Comparator** | Gate 1C | Is score consistent with outcomes of similarly-scored entries? | `outcome_learner.py:analyze_dimension_accuracy()` (exists) |

**Check:** If the rubric scorer gives 9.2 but evidence match is weak and historical comparators at that score have 0% acceptance, the triad flags a disagreement.

**Scope:** Level 1 operates **per-entry**, not system-wide. It is invoked by `score.py` at scoring time, not by `StandardsBoard.full_audit()`. See Section 9.3.

### 7.2 Level 2 — Department (Schema Enforcement)

| Regulator | Role | What It Checks | Delegates To |
|-----------|------|----------------|--------------|
| **Schema Validator** | Gate 2A | Entry structure: required fields, valid enums, state machine transitions | `validate.py:validate_entry()` (exists) |
| **Rubric Validator** | Gate 2B | Rubric integrity: weights sum, dimensions defined, thresholds ordered | `validate.py:validate_scoring_rubric()` (exists) |
| **Wiring Validator** | Gate 2C | Cross-references: YAML ↔ code ↔ constants all agree | `audit_system.py:audit_wiring()` (exists) |

**Check:** Schema can be valid (good YAML) while wiring is broken (code uses different weights than YAML). All three must pass independently.

### 7.3 Level 3 — University (System Quality)

| Regulator | Role | What It Checks | Delegates To |
|-----------|------|----------------|--------------|
| **Diagnostic Scorer** | Gate 3A | Objective measurements: test coverage, code quality, data integrity, ops maturity, claim provenance | `diagnose.py:measure_*()` functions (exist) |
| **Integrity Auditor** | Gate 3B | Claims provenance, wiring consistency, logical soundness | `audit_system.py:run_full_audit()` (exists) |
| **Agreement Assessor** | Gate 3C | Independent raters converge: ICC, kappa, consensus formation | `diagnose_ira.py:compute_icc()` (exists) |

**Check:** Diagnostic score could be high (lots of tests) while integrity audit flags unsourced claims and IRA shows raters disagree. Each catches what the others miss.

**Note:** Gate 3C requires rating JSON files in `ratings/`. If no ratings exist, the gate returns `passed=False, evidence="no rating files found"`. This is a valid failure — the system hasn't been rated yet.

### 7.4 Level 4 — National (Outcome Accreditation)

| Regulator | Role | What It Checks | Delegates To |
|-----------|------|----------------|--------------|
| **Outcome Correlator** | Gate 4A | Do dimension weights predict acceptance/rejection? | `standards.py:compute_dimension_correlation()` (**NEW** — wraps `outcome_learner.py:analyze_dimension_accuracy()`, see Section 13.1) |
| **Recalibration Engine** | Gate 4B | Are weights drifting from empirical optimum? Proposes adjustments | `recalibrate.py:compute_weight_recommendations()` (exists) |
| **Hypothesis Auditor** | Gate 4C | Do pre-recorded predictions match actual outcomes? | `standards.py:compute_hypothesis_accuracy()` (**NEW** — wraps `outcome_learner.py:validate_hypotheses_with_weights()`, see Section 13.2) |

**Check:** Outcome correlator might show mission_alignment is predictive, but hypothesis auditor reveals we consistently overpredict acceptance for high-mission entries. Recalibration engine proposes the fix.

**Independence caveat:** Gates 4A and 4B share upstream outcome data — they are correlated, not fully independent. Gate 4C depends on manually-entered hypotheses (currently zero logged). The quorum rule at this level provides weaker guarantees than at Levels 1-3. See Section 8.2.

### 7.5 Level 5 — Federal (Source Legitimacy)

| Regulator | Role | What It Checks | Delegates To |
|-----------|------|----------------|--------------|
| **Source Quality Assessor** | Gate 5A | Credibility tier of each claim's source (peer-reviewed → unsourced) | `standards.py:check_source_quality()` (**NEW** — extends `audit_system.py:audit_claims()` with credibility scoring, see Section 13.3) |
| **Benchmark Aligner** | Gate 5B | Do pipeline metrics match external industry baselines? | `standards.py:check_benchmark_alignment()` (**NEW** — compares `market-intelligence-2026.json` benchmarks against pipeline actuals, see Section 13.4) |
| **Temporal Validator** | Gate 5C | Are cited sources current? (2024 data in a 2026 system = stale) | `standards.py:check_source_freshness()` (**NEW** — scans source dates in `market-research-corpus.md`, see Section 13.5) |

**Check:** A claim could be "sourced" (Level 3 passes) but the source is a 2023 blog post (temporal fail) from a content marketing site (quality tier 2) that contradicts current BLS data (benchmark misalign). Three independent red flags.

**Independence caveat:** All three gates assess the same source material from different angles (credibility, alignment, currency). They are not independent data sources but provide independent evaluation dimensions. A single bad source can fail all three gates simultaneously.

### 7.6 Triad Agreement Rule

Within each level, a standard passes only when **at least 2 of 3 regulators agree**. This prevents:
- A single validator being wrong from causing false failures
- A single validator being fooled from causing false passes

```
Level N passes when: ≥ 2 of 3 regulators pass
Level N+1 only runs when: Level N passes
```

---

## 8. Quorum Independence Analysis

### 8.1 Strong Independence (Levels 1-3)

At Levels 1-3, the three gates draw from genuinely different data sources and methodologies:

| Level | Gate A Source | Gate B Source | Gate C Source | Independence |
|-------|-------------|-------------|-------------|--------------|
| 1 | Rubric weights | TF-IDF corpus | Historical outcomes | **Strong** — three separate algorithms |
| 2 | YAML schema | Arithmetic on rubric | AST/import analysis | **Strong** — three separate domains |
| 3 | Subprocess measurements | File scanning + regex | Multi-rater statistics | **Strong** — three separate methodologies |

The 2-of-3 quorum provides genuine redundancy at these levels.

### 8.2 Weak Independence (Levels 4-5)

At Levels 4-5, gates share upstream dependencies:

| Level | Shared Dependency | Impact |
|-------|------------------|--------|
| 4 | Gates 4A and 4B both operate on `conversion-log.yaml` outcome data | If outcome data is corrupted, both fail together |
| 4 | Gate 4C requires manually-entered hypotheses (currently 0 logged) | Gate 4C is permanently failing until hypotheses are recorded |
| 5 | All three gates assess `market-research-corpus.md` and `market-intelligence-2026.json` | A single fabricated source could fool all three |

**Mitigation:** At Levels 4-5, the quorum rule is **necessary but not sufficient**. These levels are advisory precisely because their independence guarantees are weaker. As outcome data accumulates and hypotheses are logged, the independence strengthens.

---

## 9. Regulatory Body Architecture

Each level is **one regulatory body** (one module/class) containing **three logic gates** within its domain. The body is the unit of execution; the gates are its internal assessment dimensions.

### 9.1 Class Structure

```python
# One body per level, three gates inside
class CourseRegulator:          # Level 1 — per-entry
    def gate_rubric(self, entry: dict) -> GateResult: ...
    def gate_evidence(self, entry: dict) -> GateResult: ...
    def gate_historical(self, entry: dict) -> GateResult: ...
    def evaluate(self, entry: dict) -> LevelReport: ...

class DepartmentRegulator:      # Level 2 — system-wide
    def gate_schema(self) -> GateResult: ...
    def gate_rubric(self) -> GateResult: ...
    def gate_wiring(self) -> GateResult: ...
    def evaluate(self) -> LevelReport: ...

class UniversityRegulator:      # Level 3 — system-wide
    def gate_diagnostic(self) -> GateResult: ...
    def gate_integrity(self) -> GateResult: ...
    def gate_agreement(self) -> GateResult: ...
    def evaluate(self) -> LevelReport: ...

class NationalRegulator:        # Level 4 — system-wide
    def gate_outcome(self) -> GateResult: ...
    def gate_recalibration(self) -> GateResult: ...
    def gate_hypothesis(self) -> GateResult: ...
    def evaluate(self) -> LevelReport: ...

class FederalRegulator:         # Level 5 — system-wide
    def gate_source_quality(self) -> GateResult: ...
    def gate_benchmark(self) -> GateResult: ...
    def gate_temporal(self) -> GateResult: ...
    def evaluate(self) -> LevelReport: ...
```

### 9.2 Design Properties

**Encapsulation** — Each body owns its domain. The Department Regulator doesn't know about outcome correlation. The Federal Regulator doesn't check schema validity. Clean jurisdiction.

**Delegation** — Bodies wrap existing validators rather than reimplementing. `DepartmentRegulator.gate_schema()` calls `validate.validate_entry()` underneath. `UniversityRegulator.gate_integrity()` calls `audit_system.audit_wiring()`. New code is the orchestration, not the checks. Level 4-5 gates require new wrapper functions (see Section 13).

**Uniform interface** — Every body produces the same structure:

```python
@dataclass
class GateResult:
    gate: str           # "rubric", "evidence", "historical"
    passed: bool
    score: float | None # 0.0-1.0 for soft standards, None for binary
    evidence: str       # why it passed or failed

@dataclass
class LevelReport:
    level: int          # 1-5
    name: str           # "Course", "Department", ...
    gates: list[GateResult]  # always 3
    passed: bool        # ≥2/3 gates pass
    quorum: str         # "3/3", "2/3", "1/3"
```

### 9.3 Execution Model

Level 1 (Course) operates **per-entry** and is invoked at scoring time. Levels 2-5 operate **system-wide** and run via `StandardsBoard`.

```python
class StandardsBoard:
    """Runs system-wide regulatory bodies (Levels 2-5) in hierarchical order."""

    def full_audit(self) -> BoardReport:
        """Run Levels 2-5 hierarchically. Level 1 is per-entry, not included."""
        reports = []
        for regulator in [self.department, self.university, self.national, self.federal]:
            report = regulator.evaluate()
            reports.append(report)
            if not report.passed:
                # Higher levels not meaningful if lower level fails
                break
        return BoardReport(level_reports=reports)

    def check_level(self, level: int) -> LevelReport:
        """Run a single level's regulatory body."""
        return self._regulators[level].evaluate()

    def check_entry(self, entry: dict) -> LevelReport:
        """Run Level 1 (Course) for a specific entry."""
        return self.course.evaluate(entry)
```

**CI integration:** `verify_all.py` calls `StandardsBoard().check_level(2)` — only Level 2 (Department) is a CI hard gate.

**Diagnostic integration:** `diagnose.py` calls `StandardsBoard().check_level(3)` — Level 3 (University) feeds into the diagnostic scorecard.

**Full audit:** `python scripts/run.py standards` calls `StandardsBoard().full_audit()` — runs Levels 2-5 hierarchically.

---

## 10. Error Handling

### 10.1 Validator Exceptions

When a validator function raises an exception (crash, timeout, import error), the gate wraps it into a failing `GateResult`:

```python
def _run_gate(self, gate_name: str, validator_fn, *args) -> GateResult:
    try:
        return validator_fn(*args)
    except Exception as exc:
        return GateResult(
            gate=gate_name,
            passed=False,
            score=None,
            evidence=f"validator error: {type(exc).__name__}: {exc}",
        )
```

Exceptions never propagate past the regulatory body — they are treated as gate failures.

### 10.2 Missing Data

| Scenario | Behavior |
|----------|----------|
| No rating files for Level 3 Gate 3C | Gate fails: `"no rating files in ratings/"` |
| No outcome data for Level 4 | All gates fail: `"insufficient data (0 outcomes, need 30)"` |
| No `market-intelligence-2026.json` | Level 5 Gate 5B fails: `"market intelligence file not found"` |
| `market-research-corpus.md` missing | Level 5 Gate 5C fails: `"corpus file not found"` |

### 10.3 Timeout Handling

Validators that shell out (e.g., `diagnose.py` runs `pytest --co`) inherit the existing 120-second timeout from `_run_cmd()`. No additional timeout is added at the standards layer.

---

## 11. Visual Hierarchy

```
                    ┌─────────────────────────────┐
                    │       STANDARDS BOARD        │
                    │   (Full Hierarchical Audit)  │
                    │     Levels 2-5 system-wide   │
                    └──────────────┬───────────────┘
                                   │
          ┌────────────────────────┼────────────────────────┐
          │                        │                        │
          ▼                        ▼                        ▼
    Pipeline State         Tier Classification        Board Report
    (system-wide)        (hard/soft/advisory)       (output verdict)

══════════════════════════════════════════════════════════════════════
 LEVEL 5 ─ FEDERAL: Source Legitimacy                    [advisory]
 "Are the validators' sources legitimate?"
══════════════════════════════════════════════════════════════════════
          │
          ├──── Gate 5A: Source Quality Assessor         [NEW code]
          │     └── Credibility tier per claim (peer-reviewed → unsourced)
          │
          ├──── Gate 5B: Benchmark Aligner               [NEW code]
          │     └── Pipeline metrics vs. external industry baselines
          │
          └──── Gate 5C: Temporal Validator               [NEW code]
                └── Source currency (stale data detection)

              ≥2/3 pass? ──▶ Level 5 PASSES
          ▲ watches
══════════════════════════════════════════════════════════════════════
 LEVEL 4 ─ NATIONAL: Outcome Accreditation            [advisory→soft]
 "Do the criteria actually work?"
══════════════════════════════════════════════════════════════════════
          │
          ├──── Gate 4A: Outcome Correlator              [NEW wrapper]
          │     └── outcome_learner.py: dimension weights vs. outcomes
          │
          ├──── Gate 4B: Recalibration Engine             [delegates]
          │     └── recalibrate.py: weight drift from empirical optimum
          │
          └──── Gate 4C: Hypothesis Auditor              [NEW wrapper]
                └── outcome_learner.py: prediction vs. actual accuracy

              ≥2/3 pass? ──▶ Level 4 PASSES
          ▲ watches
══════════════════════════════════════════════════════════════════════
 LEVEL 3 ─ UNIVERSITY: System Quality                       [soft]
 "Is the institution well-run?"
══════════════════════════════════════════════════════════════════════
          │
          ├──── Gate 3A: Diagnostic Scorer               [delegates]
          │     └── diagnose.py: test coverage, code quality,
          │         data integrity, ops maturity, claim provenance
          │
          ├──── Gate 3B: Integrity Auditor               [delegates]
          │     └── audit_system.py: wiring checks, logic checks,
          │         claim scanning
          │
          └──── Gate 3C: Agreement Assessor              [delegates]
                └── diagnose_ira.py: ICC(2,1), kappa, consensus

              ≥2/3 pass? ──▶ Level 3 PASSES
          ▲ watches
══════════════════════════════════════════════════════════════════════
 LEVEL 2 ─ DEPARTMENT: Schema Enforcement                   [hard]
 "Does the scorer follow the syllabus?"
══════════════════════════════════════════════════════════════════════
          │
          ├──── Gate 2A: Schema Validator                [delegates]
          │     └── validate.py: required fields, valid enums,
          │         state machine transitions
          │
          ├──── Gate 2B: Rubric Validator                 [delegates]
          │     └── validate_scoring_rubric(): weights sum,
          │         dimensions defined, thresholds ordered
          │
          └──── Gate 2C: Wiring Validator                 [delegates]
                └── audit_system.audit_wiring(): YAML ↔ code ↔
                    constants cross-references

              ≥2/3 pass? ──▶ Level 2 PASSES
          ▲ watches
══════════════════════════════════════════════════════════════════════
 LEVEL 1 ─ COURSE: Entry Scoring              [runtime, per-entry]
 "Was this entry scored correctly?"
 (invoked at scoring time, not in full_audit)
══════════════════════════════════════════════════════════════════════
          │
          ├──── Gate 1A: Rubric Scorer                   [delegates]
          │     └── score.py: weighted dimension scoring
          │         (job weights vs. funding weights)
          │
          ├──── Gate 1B: Evidence Validator               [delegates]
          │     └── text_match.py: TF-IDF content match
          │         (independent objective signal)
          │
          └──── Gate 1C: Historical Comparator           [delegates]
                └── outcome_learner.py score audit: consistency
                    with similarly-scored entry outcomes

              ≥2/3 pass? ──▶ Level 1 PASSES


  CROSS-SECTION: Single Level Internals

         ┌─────────────────────┐
         │   Regulatory Body   │
         │    (one per level)  │
         └──────────┬──────────┘
                    │
        ┌───────────┼───────────┐
        │           │           │
   ┌────▼────┐ ┌───▼────┐ ┌───▼─────┐
   │ Gate A  │ │ Gate B │ │ Gate C  │
   │         │ │        │ │         │
   │ passes? │ │passes? │ │ passes? │
   └────┬────┘ └───┬────┘ └───┬─────┘
        │          │           │
        └──────────┼───────────┘
                   │
            ┌──────▼──────┐
            │  ≥2/3 pass? │
            │   QUORUM    │
            └──────┬──────┘
                   │
              ┌────▼────┐
              │  Level   │
              │  Report  │
              └─────────┘
```

### Legend

| Symbol | Meaning |
|--------|---------|
| `[hard]` | CI blocks merge on failure |
| `[soft]` | Diagnostic reports, no CI block |
| `[advisory]` | Informational, insufficient data expected |
| `[runtime]` | Per-entry evaluation, flags disagreement |
| `[delegates]` | Wraps existing validator function |
| `[NEW code]` | Requires new implementation (see Section 13) |
| `[NEW wrapper]` | New function wrapping existing code (see Section 13) |
| `≥2/3` | Quorum rule: majority of gates must pass |
| `↑ watches` | Higher level oversees lower level |

---

## 12. File Structure

```
scripts/
  standards.py          # StandardsBoard + 5 regulator classes + data classes
                        # + 5 new functions for Level 4-5 gates (Section 13)
strategy/
  system-standards.yaml # Criteria definitions, thresholds, source of truth
docs/
  system-standards.md   # Human-readable reference
```

One new module (`standards.py`), one new YAML (`system-standards.yaml`), one new doc (`system-standards.md`).

- Levels 1-3: pure delegation to existing validators
- Levels 4-5: new wrapper functions in `standards.py` that compose existing logic with new assessment criteria

---

## 13. New Code Required (Levels 4-5)

### 13.1 `standards.compute_dimension_correlation()`

**Purpose:** Gate 4A — compute correlation between dimension scores and outcomes.

**Wraps:** `outcome_learner.py:analyze_dimension_accuracy()` (exists, returns per-dimension accuracy stats).

```python
def compute_dimension_correlation(min_sample: int = 30) -> GateResult:
    """Compute average Pearson correlation between dimension scores and binary outcomes."""
    # 1. Load conversion-log.yaml for outcome data
    # 2. Load scored entries with dimension breakdowns
    # 3. For each dimension, compute point-biserial correlation with accept/reject
    # 4. Return average correlation as score, pass if >= threshold
    # Returns GateResult(gate="outcome", passed=bool, score=float, evidence=str)
```

**New logic:** The existing `analyze_dimension_accuracy()` computes accuracy bins, not correlation coefficients. This function adds the correlation computation.

### 13.2 `standards.compute_hypothesis_accuracy()`

**Purpose:** Gate 4C — compute prediction accuracy from recorded hypotheses.

**Wraps:** `outcome_learner.py:validate_hypotheses_with_weights()` (exists, compares hypotheses against outcomes).

```python
def compute_hypothesis_accuracy(min_sample: int = 10) -> GateResult:
    """Compute fraction of pre-recorded hypotheses that matched actual outcomes."""
    # 1. Load signals/hypotheses.yaml
    # 2. Cross-reference with conversion-log.yaml outcomes
    # 3. Count correct/incorrect predictions
    # 4. Return accuracy as score, pass if >= threshold
    # Returns GateResult(gate="hypothesis", passed=bool, score=float, evidence=str)
```

### 13.3 `standards.check_source_quality()`

**Purpose:** Gate 5A — assess credibility tier of each statistical claim's source.

**Extends:** `audit_system.py:audit_claims()` (exists, returns sourced/cited/unsourced classification).

```python
SOURCE_QUALITY_TIERS = {
    "peer_reviewed": 4,   # BLS, Census, academic journals
    "industry_report": 3, # LinkedIn Economic Graph, Glassdoor
    "content_marketing": 2, # ResumeGenius, Resume Now
    "opinion": 1,         # Blog posts, single anecdotes
    "unsourced": 0,       # No attribution
}

# Keyword heuristics for tier classification
TIER_KEYWORDS = {
    "peer_reviewed": ["bls.gov", "census.gov", "doi.org", "arxiv.org", "nber.org"],
    "industry_report": ["linkedin.com", "glassdoor.com", "indeed.com", "burning-glass"],
    "content_marketing": ["resumegenius", "resume-now", "zety.com", "novoresume"],
}

def check_source_quality(threshold: float = 2.5) -> GateResult:
    """Compute average source quality tier across all statistical claims."""
    # 1. Run audit_claims() to get all claims with sources
    # 2. For each sourced/cited claim, classify into quality tier via URL/keyword matching
    # 3. Compute average quality score
    # 4. Return average as score, pass if >= threshold
```

**Data source:** Source URLs from `market-research-corpus.md` and inline citations in `strategy/` files.

### 13.4 `standards.check_benchmark_alignment()`

**Purpose:** Gate 5B — compare pipeline metrics against external benchmarks.

```python
def check_benchmark_alignment(threshold: float = 0.7) -> GateResult:
    """Check what fraction of market benchmarks are within expected range of pipeline actuals."""
    # 1. Load market-intelligence-2026.json benchmarks (conversion rates, response times, etc.)
    # 2. Load pipeline actuals from conversion-log.yaml
    # 3. For each benchmark with a pipeline counterpart, check if within 2x tolerance
    # 4. Return fraction aligned as score, pass if >= threshold
```

**Cold-start:** Initially most benchmarks will lack pipeline counterparts (insufficient outcome data). The gate returns `passed=False, evidence="2/15 benchmarks have pipeline data"` — honest about coverage.

### 13.5 `standards.check_source_freshness()`

**Purpose:** Gate 5C — verify cited sources are not stale.

```python
def check_source_freshness(max_age_years: int = 2) -> GateResult:
    """Check what fraction of cited sources were published within max_age_years."""
    # 1. Parse market-research-corpus.md for source entries with dates
    # 2. Compare each source date against current date
    # 3. Flag sources older than max_age_years
    # 4. Return fraction fresh as score, pass if >= threshold
```

**Data source:** `market-research-corpus.md` contains 126 annotated sources, many with publication year in the citation.

### 13.6 `standards.compute_weight_drift()`

**Purpose:** Gate 4B — check if current weights have drifted from empirical optimum.

**Wraps:** `outcome_learner.py:compute_weight_drift()` (exists, computes per-dimension delta between base and calibrated weights).

```python
def compute_weight_drift(min_sample: int = 30) -> GateResult:
    """Check if scoring weights have drifted beyond threshold from empirical optimum."""
    # 1. Load current weights from scoring-rubric.yaml
    # 2. Compute calibrated weights via outcome_learner.compute_weight_recommendations()
    # 3. Call outcome_learner.compute_weight_drift(base, calibrated)
    # 4. Return average drift as score, pass if <= threshold
    # Returns GateResult(gate="recalibration", passed=bool, score=float, evidence=str)
```

### 13.7 Subprocess Gate Execution

Standards with `validator: subprocess` run shell commands and interpret exit codes:

```python
def _run_subprocess_gate(self, gate_name: str, command: list[str]) -> GateResult:
    """Run a subprocess command and convert exit code to GateResult."""
    try:
        result = subprocess.run(command, cwd=REPO_ROOT, capture_output=True, text=True, timeout=120)
        return GateResult(
            gate=gate_name,
            passed=(result.returncode == 0),
            score=1.0 if result.returncode == 0 else 0.0,
            evidence=result.stdout[:500] if result.returncode == 0 else result.stderr[:500],
        )
    except subprocess.TimeoutExpired:
        return GateResult(gate=gate_name, passed=False, score=0.0, evidence="timeout after 120s")
```

This handles `lint_clean`, `tests_pass`, `verification_matrix_complete`, and `math_proofs_pass`.

---

## 14. Integration Points

| Integration | How |
|-------------|-----|
| `verify_all.py` | Calls `StandardsBoard().check_level(2)` (Department) as CI hard gate |
| `diagnose.py` | Calls `StandardsBoard().check_level(3)` (University) for diagnostic reporting |
| `score.py` | Calls `CourseRegulator().evaluate(entry)` at scoring time (Level 1) |
| `run.py` | New command `standards` runs full hierarchical audit |
| `cli.py` | New `standards` command with `--level`, `--json`, `--gate` flags |
| `mcp_server.py` | New `pipeline_standards` tool returning JSON board report |

### 14.1 Migration Path

**Backward compatibility:** `verify_all.py` gains one additional check (Level 2 via `StandardsBoard`) but all existing checks remain. If `standards.py` fails to import (e.g., missing dependency), the existing checks still run — the new check is additive.

**Rollback:** Removing the `StandardsBoard` call from `verify_all.py` restores the previous behavior. No existing validator outputs change format.

**Incremental adoption:** Level 2 can be wired into CI first. Levels 3-5 are added to `diagnose.py` and `run.py standards` without affecting CI. Level 1 entry-scoring integration can be added last.

---

## 15. Testing Strategy

### 15.1 Orchestration Tests

```python
class TestStandardsBoard:
    def test_full_audit_stops_on_level_failure(self): ...
    def test_full_audit_runs_all_levels_on_success(self): ...
    def test_check_level_returns_correct_level(self): ...
    def test_check_entry_invokes_course_regulator(self): ...

class TestQuorumRule:
    def test_3_of_3_passes(self): ...
    def test_2_of_3_passes(self): ...
    def test_1_of_3_fails(self): ...
    def test_0_of_3_fails(self): ...
```

### 15.2 Regulator Tests (one class per level)

Each regulator is tested with mocked gate functions to verify:
- Gate delegation calls the correct underlying validator
- GateResult is correctly constructed from validator output
- Exception wrapping works (validator crash → failed GateResult)
- Quorum is correctly computed

### 15.3 Integration Tests

Live tests against the actual codebase (similar to existing `test_audit_system.py` pattern):
- Level 2 full evaluation against live rubric/schema
- Level 3 full evaluation against live diagnostic data
- Cross-validation: `StandardsBoard` results consistent with existing `verify_all.py` results

### 15.4 Coverage

New tests in `tests/test_standards.py`. Existing test files unchanged.

---

## 16. Success Criteria

### 16.1 Functional

1. All existing validation continues to work (no regressions)
2. `strategy/system-standards.yaml` is the single source of truth for all thresholds
3. `python scripts/run.py standards` produces a hierarchical 5-level report
4. CI runs Level 2 (Department) as a hard gate via `verify_all.py`
5. `diagnose.py` reports Level 3 (University) soft standards
6. Level 4-5 standards are advisory until outcome data reaches `min_sample`
7. Every standard has a validator function that produces `GateResult`
8. Triad quorum (≥2/3) is enforced at every level
9. Level 1 is invocable per-entry at scoring time
10. Validator exceptions are caught and wrapped into failing `GateResult`s
11. New functions for Level 4-5 gates are implemented (Section 13)

### 16.2 Portability

12. Framework data classes (`GateResult`, `LevelReport`, `BoardReport`, `StandardsBoard`) contain no application-pipeline-specific logic
13. Gate implementations are cleanly separated from orchestration — another organ can subclass or replace gate functions without modifying the board
14. `system-standards.yaml` schema is documented well enough that another organ can author its own without reading application-pipeline code

### 16.3 Epistemological

15. Every pre-existing threshold, weight, and multiplier in the system can be traced to either `evidence_status: assumed` or `evidence_status: validated` via the standards registry
16. The framework produces an honest report — systems with insufficient outcome data show advisory failures, not false passes
17. Level 5 (Source Legitimacy) can flag a claim that passes Levels 1-4 — external credibility is not overridden by internal consistency
