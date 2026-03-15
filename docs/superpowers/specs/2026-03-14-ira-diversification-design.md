# IRA Diversification Design Spec

**Goal:** Replace the current single-model IRA panel (ICC = 0.086) with a multi-model, multi-persona architecture that produces genuine evaluative disagreement and meaningful ICC scores.

**Subsystem:** 2 of 5 in the strategic pivot sequence: (2) IRA Diversification -> (3) External Validation -> (1) Volume Engine -> (4) Academic Citations -> (5) Outreach Automation.

---

## Problem Statement

The current IRA (Inter-Rater Agreement) system produces near-zero ICC because:

1. **Same model bias**: All 3-5 subjective raters use Claude Opus, producing identical reasoning and +/-0.5 point variance.
2. **Deterministic contamination**: 5 objective dimensions (SD=0.0) flatten the ICC when mixed with 4 subjective dimensions in the ANOVA decomposition.
3. **Same evidence, same prompt**: All raters see identical context and converge on the same evaluation.

The ICC of 0.086 (or paradoxically 1.0 when only complete dimensions are included) does not reflect genuine inter-rater agreement -- it reflects a single model talking to itself.

## Design

### 1. Rater Panel Architecture

4 raters, each combining a distinct AI model with a distinct evaluation persona:

| Rater ID | Model | Provider | Persona | Evaluation Priority |
|---|---|---|---|---|
| `architect-opus` | `claude-opus-4-6` | Anthropic | Systems Architect | Clean abstractions, dependency flow, module boundaries, scalability |
| `qa-sonnet` | `claude-sonnet-4-6` | Anthropic | QA Lead | Testability, edge case coverage, failure modes, validation rigor |
| `pragmatist-haiku` | `claude-haiku-4-5-20251001` | Anthropic | Pragmatic Operator | Simplicity, onboarding speed, bus factor, operational toil |
| `auditor-gemini` | `gemini-2.0-flash` | Google | External Auditor | Evidence quality, claim sourcing, documentation completeness |

**Two axes of diversity:**
- **Model diversity** (3 Anthropic tiers + 1 Google) provides statistical independence through different training data and reasoning patterns.
- **Persona diversity** provides evaluative disagreement about what "good" means -- a QA lead and an architect genuinely *should* score architecture differently.

**Dimension classification** follows `diagnose.py`'s hardcoded split (not the rubric's `type` field, which uses `mixed` for some collector-measured dimensions):
- **Ground truth** (measured by automated collectors, deterministic): test_coverage, code_quality, data_integrity, operational_maturity, claim_provenance
- **Rated** (subjective judgment, goes through multi-model panel): architecture, documentation, analytics_intelligence, sustainability

Note: The rubric types `data_integrity` and `operational_maturity` as `mixed` and `analytics_intelligence` as `mixed`, but `diagnose.py` treats the first two as objective (they have automated collectors) and only `analytics_intelligence` has a subjective prompt generator. The partition function uses `diagnose.py`'s `OBJECTIVE_DIMENSIONS` and `SUBJECTIVE_DIMENSIONS` lists as the source of truth, not the rubric's `type` field.

### 2. Panel Configuration

Panel configuration lives in `strategy/system-grading-rubric.yaml`, extending the existing `ira` section:

```yaml
ira:
  min_raters: 3
  max_raters: 7
  panel:
    - rater_id: architect-opus
      model: claude-opus-4-6
      provider: anthropic
      persona: systems-architect
      temperature: 0.7
    - rater_id: qa-sonnet
      model: claude-sonnet-4-6
      provider: anthropic
      persona: qa-lead
      temperature: 0.7
    - rater_id: pragmatist-haiku
      model: claude-haiku-4-5-20251001
      provider: anthropic
      persona: pragmatic-operator
      temperature: 0.8
    - rater_id: auditor-gemini
      model: gemini-2.0-flash
      provider: google
      persona: external-auditor
      temperature: 0.7
  interpretation_bands:
    poor: [-1.0, 0.00]
    slight: [0.00, 0.20]
    fair: [0.21, 0.40]
    moderate: [0.41, 0.60]
    substantial: [0.61, 0.80]
    almost_perfect: [0.81, 1.00]
  consensus:
    method: median
    outlier_iqr_factor: 1.5
    re_rate_threshold: 0.61
```

### 3. Persona Prompt Design

Persona prompts stored in `strategy/rater-personas.yaml`. Each persona has a `role` (identity framing) and `scoring_bias` (variance driver):

```yaml
systems-architect:
  role: >-
    You are a systems architect evaluating software quality.
    You prioritize clean abstractions, dependency flow clarity,
    module boundary discipline, and scalability potential.
    You are skeptical of convenience shortcuts that create coupling.
    You weigh architectural purity highly, even at the cost of
    operational simplicity.
  scoring_bias: >-
    When in doubt, penalize tight coupling and reward separation
    of concerns. A system that's hard to reason about modularly
    scores lower even if it "works."

qa-lead:
  role: >-
    You are a QA lead evaluating software quality.
    You prioritize testability, edge case coverage, failure mode
    documentation, validation rigor, and regression safety.
    You are skeptical of code that's hard to test in isolation.
    You weigh defensive programming highly.
  scoring_bias: >-
    When in doubt, penalize untestable designs and reward explicit
    error handling. Systems that rely on happy-path assumptions
    score lower.

pragmatic-operator:
  role: >-
    You are a pragmatic operator who will run this system daily.
    You prioritize onboarding speed, cognitive load reduction,
    command discoverability, and low maintenance burden.
    You are skeptical of over-engineering and complexity that
    doesn't reduce daily toil.
  scoring_bias: >-
    When in doubt, penalize complexity and reward simplicity.
    A system that requires reading 400 lines of CLAUDE.md to
    operate has a documentation problem, not a documentation
    strength.

external-auditor:
  role: >-
    You are an external auditor reviewing this system for the
    first time. You prioritize evidence quality, claim sourcing,
    documentation completeness, and whether stated capabilities
    match observable artifacts.
    You are skeptical of self-reported metrics.
  scoring_bias: >-
    When in doubt, penalize unverifiable claims and reward
    transparent evidence chains. High scores require proof,
    not assertion.
```

The `scoring_bias` field is the primary variance driver. For example, the pragmatic-operator *should* score documentation lower than the architect (too much documentation = complexity overhead), while the external-auditor *should* score it higher (more docs = more evidence). This creates genuine evaluative disagreement, not random noise.

### 4. Rating Generation Pipeline

New script: `scripts/generate_ratings.py`

**Flow:**

1. Load rubric + panel config from `system-grading-rubric.yaml`
2. Load persona prompts from `strategy/rater-personas.yaml`
3. Run objective collectors once (reuse `diagnose.py` collectors)
4. For each rater in panel:
   a. Build system prompt = persona role + scoring bias + rubric context
   b. Generate subjective prompts (reuse `diagnose.py` prompt generators)
   c. Call model API with temperature from config
   d. Parse structured JSON response into rating scores
   e. Merge objective ground truth + subjective scores
   f. Save to `ratings/<rater-id>.json`
5. Archive existing rating files to `ratings/archive/` before writing new ones
6. Optionally run `diagnose_ira.py --consensus` at the end

**Migration:** Before writing new rating files, `generate_ratings.py` moves any existing `ratings/*.json` (except `consensus-*.json`) to `ratings/archive/YYYY-MM-DD/`. This prevents old-format rater IDs (e.g., `senior-engineer`, `qa-lead`) from mixing with new-format IDs (e.g., `architect-opus`, `qa-sonnet`) in IRA computation. The `--compute-ira` flag operates only on files generated in the current session.

**API integration:**

Two provider functions:
- `_call_anthropic(model, system_prompt, user_prompt, temperature)` -- uses `anthropic` SDK
- `_call_google(model, system_prompt, user_prompt, temperature)` -- uses `google-genai` SDK (already installed)

Calls are sequential (not parallel) to respect rate limits and the 16GB RAM constraint.

**Response format:**

Models are instructed to return JSON matching the existing rating schema:

```json
{
  "architecture": {"score": 8.0, "confidence": "medium", "evidence": "...", "strengths": [...], "weaknesses": [...]},
  "documentation": {"score": 7.5, "confidence": "high", "evidence": "..."},
  "analytics_intelligence": {"score": 8.5, "confidence": "medium", "evidence": "..."},
  "sustainability": {"score": 7.0, "confidence": "medium", "evidence": "..."}
}
```

Both Anthropic and Google support JSON output mode. A validation step checks that returned scores are within 1.0-10.0 range and all 4 subjective dimensions are present.

**Error handling:**

- If a model API call fails, skip that rater and log a warning
- IRA computation works with 3+ raters (min_raters config)
- Malformed JSON responses trigger one retry; if still malformed, skip rater
- Missing API key for a configured provider produces a clear error with env var name

**API key management:**

Environment variables: `ANTHROPIC_API_KEY` and `GOOGLE_API_KEY`. Script exits with clear error if keys are missing for configured raters.

**CLI:**

```bash
python scripts/generate_ratings.py                        # Full session: all panel raters
python scripts/generate_ratings.py --rater architect-opus  # Single rater only
python scripts/generate_ratings.py --dry-run               # Show prompts, don't call APIs
python scripts/generate_ratings.py --compute-ira           # Run IRA after generation
```

### 5. ICC Computation Fix

Changes to `scripts/diagnose_ira.py`:

**Automatic dimension partitioning:**

New function `partition_dimensions(ratings, rubric)` splits dimensions into:
- **Ground truth** (objective/deterministic): reported as single measurement, no ICC
- **Rated** (subjective): ICC computed on these only

Classification uses `diagnose.py`'s `OBJECTIVE_DIMENSIONS` and `SUBJECTIVE_DIMENSIONS` constants as the authoritative source. Falls back to rubric `type` field only if these constants are not importable. This avoids the `mixed` type ambiguity in the rubric.

**Report output changes:**

```
=================================================================
  INTER-RATER AGREEMENT (IRA) REPORT
=================================================================

  Raters (4): architect-opus, qa-sonnet, pragmatist-haiku, auditor-gemini

  GROUND TRUTH (objective -- deterministic, not rated):
  Dimension                  Score
  -------------------------------------------
  test_coverage              10.0
  code_quality                9.4
  data_integrity             10.0
  operational_maturity        9.5
  claim_provenance            5.6

  SUBJECTIVE AGREEMENT:
  Overall ICC(2,1): 0.72 (substantial)
  Fleiss' kappa (binned): 0.65 (substantial)

  Dimension                 Scores                    Range    SD
  ----------------------------------------------------------------------
  architecture              8.5, 7.0, 6.5, 8.0        2.0   0.74
  documentation             8.0, 7.5, 7.0, 9.0        2.0   0.73
  analytics_intelligence    9.0, 7.5, 8.0, 8.5        1.5   0.56
  sustainability            7.0, 6.0, 8.0, 6.5        2.0   0.74
```

**JSON output changes:**

```json
{
  "n_raters": 4,
  "rater_ids": ["architect-opus", "qa-sonnet", "pragmatist-haiku", "auditor-gemini"],
  "ground_truth": {
    "test_coverage": {"score": 10.0, "evidence": "..."},
    "code_quality": {"score": 9.4, "evidence": "..."}
  },
  "subjective_icc": 0.72,
  "subjective_interpretation": "substantial",
  "dimensions": { ... }
}
```

**Backward compatibility:** If no rubric is found, all dimensions go through ICC as before (existing behavior preserved).

### 6. Integration Wiring

| Layer | Change |
|---|---|
| `scripts/run.py` | Add `"rateall"` quick command -> `generate_ratings.py` |
| `scripts/cli.py` | Add `rate` command with `--rater`, `--dry-run`, `--compute-ira` flags |
| `scripts/mcp_server.py` | Add `pipeline_rate` tool returning JSON |
| `pyproject.toml` | Add `anthropic` to runtime dependencies |

### 7. Testing Strategy

**New file: `tests/test_generate_ratings.py`** (9 tests):

| Test | What |
|---|---|
| `test_panel_config_loads` | Panel config from rubric YAML has required fields (rater_id, model, provider, persona, temperature) |
| `test_persona_prompts_load` | All personas referenced in panel config exist in rater-personas.yaml |
| `test_call_anthropic_formats_request` | Anthropic API call builds correct message structure (mocked) |
| `test_call_google_formats_request` | Google API call builds correct message structure (mocked) |
| `test_response_parsing_valid_json` | Valid model response parsed into rating schema correctly |
| `test_response_parsing_malformed` | Graceful fallback when model returns non-JSON or incomplete JSON |
| `test_objective_scores_shared` | Objective ground truth scores injected into all rater output files identically |
| `test_dry_run_no_api_calls` | `--dry-run` mode prints prompts without making any API calls |
| `test_missing_api_key_error` | Clear error message when env var missing for configured provider |

**Modified: `tests/test_diagnose_ira.py`** (4 new tests):

| Test | What |
|---|---|
| `test_partition_dimensions_by_type` | Objective/subjective split matches rubric type field |
| `test_icc_subjective_only` | ICC computation excludes objective (SD=0) dimensions |
| `test_ground_truth_in_json_output` | JSON report contains `ground_truth` key with objective scores |
| `test_backward_compat_no_rubric` | All dimensions go through ICC when no rubric file is found |

## File Inventory

| File | Action |
|---|---|
| `scripts/generate_ratings.py` | **CREATE** -- Multi-model rating session orchestrator |
| `strategy/rater-personas.yaml` | **CREATE** -- Persona prompts for each rater role |
| `strategy/system-grading-rubric.yaml` | **MODIFY** -- Expand `ira` section with `panel` config |
| `scripts/diagnose_ira.py` | **MODIFY** -- Add dimension partitioning, ground truth reporting |
| `scripts/run.py` | **MODIFY** -- Add `rateall` command |
| `scripts/cli.py` | **MODIFY** -- Add `rate` command |
| `scripts/mcp_server.py` | **MODIFY** -- Add `pipeline_rate` tool |
| `pyproject.toml` | **MODIFY** -- Add `anthropic` dependency |
| `tests/test_generate_ratings.py` | **CREATE** -- 9 tests for rating generation |
| `tests/test_diagnose_ira.py` | **MODIFY** -- 4 new dimension partitioning tests |
| `CLAUDE.md` | **MODIFY** -- Add generate_ratings.py to script dependency graph, rateall to quick commands, rate to CLI commands |

## Dependencies

- `anthropic` Python SDK (new runtime dependency)
- `google-genai` (already installed)
- Environment variables: `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`

## Cost and Rate Limits

**Estimated per-session cost** (4 raters, 4 subjective dimensions each):

Each subjective prompt includes ~100 lines of CLAUDE.md excerpt + ~40 lines of file excerpts + scoring guide (~300 tokens). With system prompt (~200 tokens) and response (~500 tokens), each call is ~1,500-2,000 tokens.

| Rater | Calls | Est. Input | Est. Output | Est. Cost |
|---|---|---|---|---|
| architect-opus | 4 | ~6K tokens | ~2K tokens | ~$0.30 |
| qa-sonnet | 4 | ~6K tokens | ~2K tokens | ~$0.05 |
| pragmatist-haiku | 4 | ~6K tokens | ~2K tokens | ~$0.01 |
| auditor-gemini | 4 | ~6K tokens | ~2K tokens | Free tier |
| **Total** | 16 | ~24K | ~8K | **~$0.36** |

Rate limits: Anthropic allows 1,000 req/min on most tiers. Google Gemini free tier allows 15 req/min. Sequential calls with no delay will stay well within limits. If Google rate-limits, a 5-second backoff is sufficient.

**Model ID note:** Model IDs in the panel config (e.g., `claude-opus-4-6`) should be verified against the Anthropic API at implementation time. The panel config in `system-grading-rubric.yaml` is the single source of truth, making model ID updates a YAML change with no code changes required.

## Verification

```bash
# After implementation:
python scripts/generate_ratings.py --dry-run          # Verify prompts without API calls
python scripts/generate_ratings.py --compute-ira      # Full session + IRA
python scripts/diagnose_ira.py ratings/*.json --consensus  # Verify ICC on subjective only

# Tests:
pytest tests/test_generate_ratings.py tests/test_diagnose_ira.py -v
python scripts/verification_matrix.py --strict
ruff check scripts/ tests/
```

## Success Criteria

1. ICC on subjective dimensions >= 0.40 (moderate agreement) -- indicating genuine but not artificial agreement
2. Per-dimension SD >= 0.5 for at least 3 of 4 subjective dimensions -- confirming real variance
3. No single rater's mean score across all subjective dimensions deviates from the panel mean by more than 1.5 points (leniency bias check)
4. All 13 new + 4 modified tests pass
5. Existing test suite remains green
