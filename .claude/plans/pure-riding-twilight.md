# Diagnostic Tool, Grading Rubric & Inter-Rater Agreement SOP

## Context

The application pipeline has reached 9.9/10 on E2G review after 4 passes of improvements (2,135 tests, 121/121 modules, 0 lint errors). The user wants to formalize system quality measurement via:

1. **A diagnostic tool** — comprehensive system self-assessment producing a graded scorecard
2. **A grading rubric** — formal criteria for evaluating each dimension with anchored scoring guides
3. **An IRA (inter-rater agreement) SOP** — process for running diagnostics across multiple AI models and computing agreement metrics to converge on ground truth

This enables "grade norming with other AI eyes" — different LLMs independently score the same codebase, then agreement metrics (ICC, kappa) reveal where subjective assessments converge or diverge.

---

## Deliverables

### 1. `strategy/system-grading-rubric.yaml` — 8-Dimension Rubric

Eight dimensions with weights summing to 1.0. Each has type (objective/subjective/mixed), weight, anchored scoring guide (1-3-5-7-10), and evidence sources.

| Dimension | Type | Weight | What It Measures |
|-----------|------|--------|-----------------|
| test_coverage | objective | 0.15 | Test count, module coverage ratio, edge case depth |
| architecture | subjective | 0.15 | Module decomposition, separation of concerns, dependency flow |
| data_integrity | mixed | 0.15 | Schema validation, state machine enforcement, YAML consistency |
| operational_maturity | mixed | 0.15 | Automation (launchd), backup, monitoring, alerting |
| code_quality | objective | 0.10 | Lint errors, type hints, consistent patterns |
| analytics_intelligence | mixed | 0.10 | Funnel/conversion analytics, scoring model, trend detection |
| documentation | subjective | 0.10 | CLAUDE.md completeness, inline docs, handoff readiness |
| sustainability | subjective | 0.10 | Single-operator resilience, bus factor mitigation, onboarding ease |

Each dimension includes:
- `scoring_guide`: Anchored descriptors at 1 (critical gaps), 3 (below average), 5 (adequate), 7 (strong), 10 (exemplary)
- `evidence_sources`: Which files/commands to inspect
- `ira_config`: Agreement method (ICC for continuous, kappa for categorical), consensus method (median), outlier threshold (1.5 × IQR)

### 2. `scripts/diagnose.py` — Diagnostic Tool

**Objective collectors** (automated measurement):
- `measure_test_coverage()` — runs pytest count, verification matrix ratio
- `measure_code_quality()` — runs ruff, counts type-hinted functions
- `measure_data_integrity()` — runs validate.py + validate_signals.py, counts errors
- `measure_operational_maturity()` — checks launchd status, backup recency, monitor output

**Subjective prompt generators** (for AI raters):
- `generate_architecture_prompt()` — presents module dependency graph + file structure for rating
- `generate_documentation_prompt()` — presents CLAUDE.md + docs/ for rating
- `generate_analytics_prompt()` — presents scoring model + funnel logic for rating
- `generate_sustainability_prompt()` — presents handoff doc + automation for rating

**Core functions:**
- `compute_diagnostic_score(objective_scores, subjective_scores)` — weighted composite
- `--json` flag outputs structured JSON for IRA consumption
- `--subjective-only` generates prompts for external raters without running objective collectors
- `--objective-only` runs only automated measurements
- Human report: table with dimension, score, weight, weighted contribution, evidence summary

**JSON output schema** (consumed by `diagnose_ira.py`):
```yaml
{
  "rater_id": "claude-opus-4-6",
  "timestamp": "2026-03-05T...",
  "rubric_version": "1.0",
  "dimensions": {
    "test_coverage": {"score": 9.2, "evidence": "...", "confidence": "high"},
    ...
  },
  "composite": 8.7
}
```

### 3. `scripts/diagnose_ira.py` — Inter-Rater Agreement Computation

Pure-stdlib implementation (no scipy/numpy dependency).

**Agreement metrics:**
- `compute_icc(ratings_matrix)` — ICC(2,1) two-way random, absolute agreement. Uses sum-of-squares decomposition (SSR, SSC, SSE from two-way ANOVA without interaction).
- `compute_cohens_kappa(rater1, rater2)` — for pairwise categorical agreement (used when scores are binned to bands)
- `compute_fleiss_kappa(ratings_matrix)` — for 3+ raters on categorical data
- `compute_consensus(scores_per_dimension)` — median as consensus value, IQR-based outlier flagging (>1.5 × IQR from Q1/Q3)

**Interpretation bands** (Landis & Koch 1977):
- <0.00: poor, 0.00-0.20: slight, 0.21-0.40: fair, 0.41-0.60: moderate, 0.61-0.80: substantial, 0.81-1.00: almost perfect

**CLI interface:**
```bash
python scripts/diagnose_ira.py ratings/*.json              # Compute IRA from rating files
python scripts/diagnose_ira.py ratings/*.json --consensus   # Also output consensus scores
python scripts/diagnose_ira.py ratings/*.json --json        # Machine-readable output
```

**Report output:**
- Per-dimension ICC + interpretation band
- Overall ICC across all dimensions
- Outlier flags (which rater diverged most on which dimension)
- Consensus scores (median per dimension)
- Dimensions with lowest agreement → candidates for rubric refinement

### 4. IRA SOP for meta-organvm

Location: `docs/sop--diagnostic-inter-rater-agreement.md` (kept in this repo since it's pipeline-specific; cross-referenced from meta-organvm governance docs).

**8-section SOP format** (matching meta-organvm conventions):

1. **Header**: SOP ID, version, effective date, owner, review cycle
2. **Purpose & Scope**: Grade norming across AI raters for pipeline quality
3. **Prerequisites**: Python 3.11+, rubric YAML, N≥3 rater sessions
4. **Phase 1 — Rubric Familiarization**: Each rater reads rubric + evidence sources
5. **Phase 2 — Independent Rating**: Each rater runs `diagnose.py --json`, saves to `ratings/`
6. **Phase 3 — Agreement Computation**: Run `diagnose_ira.py ratings/*.json --consensus`
7. **Phase 4 — Consensus Formation**: Review outliers, discuss divergent dimensions, re-rate if ICC < 0.61
8. **Phase 5 — Archival & Trend Tracking**: Save consensus to `signals/diagnostic-history/`, track drift over time

**Recommended rater panel**: 3-5 AI models (e.g., Claude Opus, Sonnet, GPT-4, Gemini) + 1 human anchor rater.

### 5. Test Files

- `tests/test_diagnose.py` (~15 tests): objective collectors with monkeypatched subprocess, subjective prompt generation, composite scoring, JSON output format
- `tests/test_diagnose_ira.py` (~12 tests): ICC computation (perfect agreement=1.0, zero agreement~0, known values), kappa (perfect=1.0, chance=0), Fleiss kappa, consensus median, outlier detection, interpretation bands

### 6. Integration

- Add `diagnose` and `ira` commands to `scripts/run.py`
- Add `diagnose.py` and `diagnose_ira.py` to CLAUDE.md commands section
- Add to verification matrix (module → test mapping)

---

## Files to Create/Modify

| File | Action |
|------|--------|
| `strategy/system-grading-rubric.yaml` | CREATE — 8-dimension rubric |
| `scripts/diagnose.py` | CREATE — diagnostic tool |
| `scripts/diagnose_ira.py` | CREATE — IRA computation |
| `tests/test_diagnose.py` | CREATE — diagnostic tests |
| `tests/test_diagnose_ira.py` | CREATE — IRA tests |
| `docs/sop--diagnostic-inter-rater-agreement.md` | CREATE — IRA SOP |
| `scripts/run.py` | MODIFY — add `diagnose`, `ira` commands |
| `CLAUDE.md` | MODIFY — add new commands to tables |
| `strategy/module-verification-overrides.yaml` | MODIFY — if needed for new modules |

**Reuse from existing codebase:**
- `pipeline_lib.py`: `REPO_ROOT`, `load_entries()`, `parse_date()` — for evidence gathering
- `score.py`: `scoring_confidence_band()` — reuse for diagnostic confidence
- `launchd_manager.py`: `get_agent_status()` — for operational maturity measurement
- `validate.py` / `validate_signals.py`: invoke as subprocess for data integrity scoring
- `verification_matrix.py`: invoke for module coverage ratio
- `standup.py` health score pattern: 5-dimension × 2.0 pattern as reference (but diagnostic uses weighted continuous scores)

---

## Verification

1. `ruff check scripts/diagnose.py scripts/diagnose_ira.py tests/test_diagnose.py tests/test_diagnose_ira.py` — 0 errors
2. `pytest tests/test_diagnose.py tests/test_diagnose_ira.py -v` — all pass
3. `python scripts/diagnose.py` — produces human-readable scorecard
4. `python scripts/diagnose.py --json > ratings/claude-opus.json` — valid JSON
5. `python scripts/diagnose_ira.py ratings/*.json` — IRA report (needs ≥2 rating files)
6. `python scripts/run.py diagnose` and `python scripts/run.py ira` — work via quick commands
7. `python scripts/verification_matrix.py --strict` — new modules covered
8. Full suite: `pytest tests/ -v` — no regressions
