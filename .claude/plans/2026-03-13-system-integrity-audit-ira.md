# System Integrity Audit, Diagnostic Grading Tool & IRA Grade-Norming SOP

## Context

The application-pipeline has grown to 118 modules, 2,253 tests, a 9-dimension scoring rubric, an 8-dimension system-grading rubric, and 112+ sourced market benchmarks. The system grades **applicant entries** against a scoring rubric and grades **itself** against a system-grading rubric. Both rubrics contain statistical claims, hardcoded thresholds, and cross-references.

**Problem:** No systematic audit has verified that:
1. Statistical claims in the system are sourced, non-invented, and logically sound
2. All cross-references (rubric → code → constants → market data) are consistently wired
3. The system-grading rubric measures what it claims to measure
4. The IRA (inter-rater agreement) process is formalized as a repeatable SOP

**What this plan produces:**
- A diagnostic audit script (`scripts/audit_system.py`) that checks claim provenance, wiring integrity, and logical consistency
- Enhancements to `diagnose.py` for source-verification awareness
- A formal IRA grade-norming SOP document for meta-organvm
- CLI/MCP integration for the audit tool

---

## Current State Inventory

### What Exists

| Component | File | State |
|-----------|------|-------|
| Entry scoring rubric | `strategy/scoring-rubric.yaml` | 9 dimensions, 2 weight sets (general + job), thresholds |
| System grading rubric | `strategy/system-grading-rubric.yaml` | 8 dimensions, IRA config, scoring guides |
| Score implementation | `scripts/score.py` + 6 sub-modules | Loads rubric, has hardcoded fallbacks |
| Score constants | `scripts/score_constants.py` | HIGH_PRESTIGE (97 orgs), ROLE_FIT_TIERS (4 tiers) |
| Diagnostic tool | `scripts/diagnose.py` | 4 objective collectors, 4 subjective prompt generators |
| IRA computation | `scripts/diagnose_ira.py` | ICC(2,1), Cohen's kappa, Fleiss' kappa, consensus |
| Market intelligence | `strategy/market-intelligence-2026.json` | 112 sources, channel multipliers, benchmarks |
| Market research corpus | `strategy/market-research-corpus.md` | 126 annotated sources |
| Scoring rubric docs | `strategy/scoring-rubric.md` | Dimension descriptions, evidence tables |
| Rating files | `ratings/rater1.json`, `ratings/rater2.json` | Stub/test data only (2 dims each) |
| Tests | `tests/test_diagnose.py` (27), `tests/test_diagnose_ira.py` (34) | 61 tests total |

### Identified Risks

#### A. Unverifiable Claims
Statistical claims are repeated across 15+ files but sourcing is inconsistent:
- **"8x referral multiplier"** — cited as "LinkedIn Economic Graph" but no direct URL to the dataset
- **"53% callback lift"** — cited as "ResumeGenius 2026" but it's a content marketing report, not peer-reviewed
- **"62% reject generic AI content"** — cited as "Resume Now AI Applicant Report"
- **"68% more offers"** — cited as "ResumeGenius 2026"
- **Benefits cliffs** ($20,352 SNAP, $21,597 Medicaid) — no source noted; should be verified against 2026 FPL

These claims may be **directionally correct** but the specific percentages could be fabricated by AI summarization. The audit must flag claims that lack verifiable primary sources.

#### B. Wiring Gaps (Potential)
- `score.py` loads `scoring-rubric.yaml` with hardcoded fallback — but do the fallback values STILL match the YAML?
- `diagnose.py` maps 4 objective dimensions to collectors and 4 subjective to prompt generators — does this match `system-grading-rubric.yaml`'s 8 dimensions exactly?
- `score_constants.py` HIGH_PRESTIGE org scores are opinion-based (what makes Anthropic an 8 vs Google an 8?)
- `ROLE_FIT_TIERS` dimension scores (mission_alignment=9 for "developer experience") — are these calibrated against actual outcomes?
- `validate.py` VALID_DIMENSIONS must match `pipeline_lib.py` DIMENSION_ORDER

#### C. Logical Consistency
- Rubric weights must sum to 1.0 (asserted at import time — good)
- Benefits cliff thresholds should be >= current FPL values
- AUTO_QUALIFY_MIN in rubric (9.0) vs scoring-rubric.md documentation — must agree
- ROLE_FIT_TIERS tier ordering (tier-1-strong, tier-4-poor, tier-3-weak, tier-2-moderate) — unusual ordering, is this intentional?

---

## Plan

### Phase 1: Audit Script (`scripts/audit_system.py`)

A new diagnostic script that performs three classes of checks:

#### 1.1 Claim Provenance Audit
Scan for statistical claims and verify source traceability.

```
For each claim found in scripts/ and strategy/:
  - Extract the number + context (regex patterns: \d+%|[0-9]+x|\$[0-9,]+)
  - Check if a "source" field or inline citation exists nearby
  - Flag: SOURCED (has URL/report name), CITED (has report name, no URL), UNSOURCED (claim with no attribution)
  - For market-intelligence-2026.json: verify every top-level object has a "source" or "note" field
```

**Output:** Table of claims with provenance status and risk level.

#### 1.2 Wiring Integrity Audit
Verify all cross-references are connected and consistent.

| Check | What | How |
|-------|------|-----|
| Rubric↔Code weights | `scoring-rubric.yaml` weights == `score.py` `_DEFAULT_WEIGHTS` | Load both, dict compare |
| Rubric↔Code thresholds | `scoring-rubric.yaml` thresholds == `score.py` `AUTO_QUALIFY_MIN`, etc. | Load both, compare |
| Dimensions consistent | `DIMENSION_ORDER` in pipeline_lib == `scoring-rubric.yaml` weight keys == `validate.py` `VALID_DIMENSIONS` | Set comparison |
| System rubric↔diagnose | `system-grading-rubric.yaml` dimension keys == `diagnose.py` `OBJECTIVE_DIMENSIONS` ∪ `SUBJECTIVE_DIMENSIONS` | Set comparison |
| System rubric weights sum | `system-grading-rubric.yaml` dimension weights sum to 1.0 | Arithmetic check |
| HIGH_PRESTIGE ranges | All values in `score_constants.py` HIGH_PRESTIGE are 1-10 | Range check |
| ROLE_FIT_TIERS ranges | All dimension scores in ROLE_FIT_TIERS are 1-10 | Range check |
| Benefits cliffs positive | All cliff values > 0 and reasonable (< $100k) | Range check |
| IRA config consistent | `system-grading-rubric.yaml` ira.min_raters >= 2 | Value check |
| Market JSON completeness | Every section in market-intelligence-2026.json has "source" or "note" | Key check |

#### 1.3 Logical Consistency Audit
Check for impossible, improbable, or illogical values.

| Check | What | Flag if |
|-------|------|---------|
| Weight sums | Both weight dicts | abs(sum - 1.0) > 0.001 |
| Threshold ordering | tier1 > tier2 > tier3 | Misordered |
| Score ranges | All hardcoded scores | Outside 1-10 |
| Conversion rates | Market intelligence rates | > 1.0 or < 0 |
| Multiplier sanity | Channel multipliers | > 20x or < 0 |
| Follow-up windows | Protocol day ranges | start > end |
| Salary ranges | min > max, or max > $1M | Sanity check |
| Org prestige ordering | Tier labels vs scores | Tier-1 scored lower than Tier-4 |
| ROLE_FIT_TIERS ordering | tier names vs dimension values | tier-1-strong has lower scores than tier-4-poor |

**CLI interface:**
```bash
python scripts/audit_system.py                    # Full audit report
python scripts/audit_system.py --claims           # Claims provenance only
python scripts/audit_system.py --wiring           # Wiring integrity only
python scripts/audit_system.py --logic            # Logical consistency only
python scripts/audit_system.py --json             # Machine-readable output
```

### Phase 2: Enhance `diagnose.py` Source Awareness

Add a new objective collector `measure_claim_provenance()` that calls the audit script's claim-checking logic and produces a score:
- 10: All claims have verifiable primary sources (URLs)
- 7: All claims cited (report name), most with URLs
- 5: Most claims cited, some unsourced
- 3: Many unsourced claims
- 1: Pervasive unsourced claims

Add this as a 9th dimension to `system-grading-rubric.yaml`:
```yaml
claim_provenance:
  label: Claim Provenance
  type: objective
  weight: 0.05  # Reduce other weights proportionally
  description: >-
    Source traceability for statistical claims. Every benchmark,
    multiplier, and percentage should trace to a named report or URL.
```

Rebalance existing weights to accommodate (subtract 0.005-0.01 from the four 0.15-weight dimensions).

### Phase 3: IRA Grade-Norming SOP (Generic Cross-Organ)

Create `docs/sop--ira-grade-norming.md` following the meta-organvm SOP template format.
**Scope:** Written generically so any ORGANVM organ can use it. The application-pipeline is the reference implementation.

**Content:**

1. **Purpose**: Establish reliable system quality scores through multi-rater agreement for any ORGANVM organ or project
2. **Scope**: Any project with a `system-grading-rubric.yaml` (or equivalent) defining weighted dimensions with scoring guides
3. **Prerequisites**: A grading rubric YAML, a diagnostic script that produces objective + subjective rating JSON, 3+ raters (AI or human)
4. **Procedure:**
   - **Step 1 — Define rubric**: Create `strategy/system-grading-rubric.yaml` with dimensions, weights, scoring guides, and IRA config
   - **Step 2 — Generate objective baseline**: Run diagnostic tool with `--json --rater-id objective` → save to `ratings/objective.json`
   - **Step 3 — Generate subjective prompts**: Run diagnostic tool with `--subjective-only` → distribute prompts to 3+ raters
   - **Step 4 — Collect ratings**: Each rater produces JSON per the schema; save to `ratings/<rater-id>.json`
   - **Step 5 — Compute IRA**: Run IRA tool on `ratings/*.json --consensus`
   - **Step 6 — Evaluate agreement**: ICC ≥ 0.61 = acceptable; < 0.61 triggers rubric refinement discussion
   - **Step 7 — Apply consensus**: Median scores become the official system grade
   - **Step 8 — Archive**: Move rating files to `ratings/archive/YYYY-QN/`
5. **Quality checks**: ICC interpretation bands (Landis & Koch), outlier flagging via IQR, divergent dimension identification
6. **Review frequency**: Quarterly (aligned with recalibration cycles)
7. **Appendix A**: Reference implementation paths for application-pipeline
8. **Appendix B**: Rating JSON schema specification

Also copy to `meta-organvm/organvm-corpvs-testamentvm/docs/operations/sop--ira-grade-norming.md` for cross-organ reference.

### Phase 3.5: Execute Live IRA Session

Run the full IRA grade-norming session within this implementation:

1. **Generate objective baseline**: `python scripts/diagnose.py --json --rater-id objective > ratings/objective.json`
2. **Generate subjective ratings from multiple AI perspectives**:
   - Use `diagnose.py --subjective-only` to extract prompts
   - Rate from 3 distinct AI perspectives (e.g., "senior-engineer", "systems-architect", "qa-lead") by evaluating the evidence and scoring each subjective dimension
   - Save each as `ratings/<perspective>.json`
3. **Compute IRA**: `python scripts/diagnose_ira.py ratings/*.json --consensus`
4. **Analyze results**: Flag divergent dimensions, identify rubric refinement candidates
5. **Record consensus scores** in a dated results file

### Phase 4: Wire Into CLI/MCP/run.py

| Layer | Addition |
|-------|----------|
| `run.py` | `"audit": ("audit_system.py", [], "System integrity audit: claims, wiring, logic")` |
| `cli.py` | `audit` command with `--claims`, `--wiring`, `--logic`, `--json` flags |
| `mcp_server.py` | `pipeline_audit` tool returning JSON audit results |

### Phase 5: Tests

New file: `tests/test_audit_system.py`

| Test | What |
|------|------|
| `test_claim_scan_finds_percentages` | Regex extraction works on sample text |
| `test_wiring_rubric_weights_match_code` | Live check: rubric YAML weights == score.py defaults |
| `test_wiring_dimensions_consistent` | Live check: DIMENSION_ORDER == rubric keys == VALID_DIMENSIONS |
| `test_wiring_system_rubric_matches_diagnose` | Live check: 8 dimensions in rubric == diagnose collectors+generators |
| `test_logical_weight_sums` | Both weight dicts sum to 1.0 |
| `test_logical_threshold_ordering` | tier1 > tier2 > tier3 |
| `test_logical_score_ranges` | All HIGH_PRESTIGE values in 1-10 |
| `test_logical_role_tier_ordering` | tier-1-strong has highest scores |
| `test_market_json_has_sources` | Every section has "source" or "note" |
| `test_audit_cli_runs` | Basic smoke test of `main()` |
| `test_audit_json_output_structure` | JSON output has expected keys |

Add to `test_diagnose.py`:
| Test | What |
|------|------|
| `test_measure_claim_provenance_returns_score` | New collector produces valid score |

---

## Critical Files

| File | Action |
|------|--------|
| `scripts/audit_system.py` | **CREATE** — Main audit script |
| `scripts/diagnose.py` | **MODIFY** — Add `measure_claim_provenance()` collector, update dimension lists |
| `strategy/system-grading-rubric.yaml` | **MODIFY** — Add `claim_provenance` dimension, rebalance weights |
| `scripts/run.py` | **MODIFY** — Add `"audit"` command |
| `scripts/cli.py` | **MODIFY** — Add `audit` CLI command |
| `scripts/mcp_server.py` | **MODIFY** — Add `pipeline_audit` tool |
| `docs/sop--ira-grade-norming.md` | **CREATE** — IRA SOP document |
| `tests/test_audit_system.py` | **CREATE** — Audit tests |
| `tests/test_diagnose.py` | **MODIFY** — Add claim provenance test |

## Reuse Inventory

| Existing | Reuse For |
|----------|-----------|
| `diagnose.py:load_rubric()` | Loading system-grading-rubric.yaml |
| `diagnose.py:_run_cmd()` | Running subprocess checks |
| `diagnose.py:compute_composite()` | Weighted score computation |
| `diagnose.py:format_json_output()` | JSON output pattern |
| `diagnose_ira.py:compute_icc()` | IRA computation in SOP |
| `diagnose_ira.py:interpret_agreement()` | Agreement band interpretation |
| `pipeline_lib.DIMENSION_ORDER` | Canonical dimension list |
| `pipeline_lib.VALID_DIMENSIONS` | Validation set |
| `score.py:_load_rubric()` | Rubric loading pattern |
| `score.py:_DEFAULT_WEIGHTS` | Fallback comparison target |
| `score_constants.HIGH_PRESTIGE` | Prestige audit target |
| `score_constants.ROLE_FIT_TIERS` | Tier audit target |
| SOP template from meta-organvm | `sop_template.md` format |

---

## Verification

```bash
# After Phase 1 (audit script):
python scripts/audit_system.py
python scripts/audit_system.py --json | python -m json.tool

# After Phase 2 (diagnose enhancement):
python scripts/diagnose.py --objective-only
python scripts/diagnose.py --json --rater-id test

# After Phase 4 (CLI/MCP):
python scripts/run.py audit
python scripts/cli.py audit --json

# Tests:
.venv/bin/python -m pytest tests/test_audit_system.py tests/test_diagnose.py -v
.venv/bin/python scripts/verification_matrix.py --strict
.venv/bin/ruff check scripts/ tests/
```

---

## Execution Order

| Step | Phase | Priority |
|------|-------|----------|
| 1 | Create `audit_system.py` with 3 audit classes | HIGH |
| 2 | Wire into `run.py` | HIGH |
| 3 | Create `tests/test_audit_system.py` | HIGH |
| 4 | Run audit, analyze and fix findings | HIGH |
| 5 | Enhance `diagnose.py` with claim provenance | MEDIUM |
| 6 | Update `system-grading-rubric.yaml` (9th dimension, rebalance) | MEDIUM |
| 7 | Wire into `cli.py` and `mcp_server.py` | MEDIUM |
| 8 | Create IRA grade-norming SOP (generic cross-organ) | MEDIUM |
| 9 | Copy SOP to meta-organvm | MEDIUM |
| 10 | Execute live IRA session (3+ AI perspectives) | HIGH |
| 11 | Compute IRA, record consensus scores | HIGH |
| 12 | Run full test suite + verification matrix + lint | HIGH |
