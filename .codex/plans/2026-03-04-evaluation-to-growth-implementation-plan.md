# Evaluation-to-Growth Implementation Plan

Date: 2026-03-04
Project: application-pipeline
Scope: Project-wide reliability, API parity, and deterministic verification

## Objective
Align public command surfaces (`run.py`, `cli.py`, MCP) with real behavior, remove environment-dependent test instability, and preserve current delivery velocity.

## Phase 1 — Stabilize Critical Regressions (P0)
1. Fix `cli validate` crash.
   - Add `error: str | None` to `ValidationResult` or update CLI to read only `errors/message`.
   - Add direct test for `cli validate` with no target.
2. Fix `cli score --all` behavior.
   - Support true batch mode in API and CLI (`all_entries` bool) or route through `score.py --all` until API extraction completes.
   - Add test that `score --all --dry-run` exits 0 and reports batch summary.
3. Make full tests deterministic across machines.
   - Introduce explicit metrics source mode (e.g., env var `PIPELINE_METRICS_SOURCE=fallback|canonical`).
   - Default tests to fallback mode; add one optional integration test for canonical mode.

## Phase 2 — Restore Contract Integrity (P1)
1. Replace placeholder implementations in `pipeline_api.py` for:
   - `score_entry`, `advance_entry`, `draft_entry`, `compose_entry`, `validate_entry`.
2. Ensure behavior parity against legacy scripts:
   - Golden tests comparing API result fields to legacy script outcomes for representative fixtures.
3. Tighten API tests:
   - Remove permissive assertions allowing `SUCCESS|DRY_RUN|ERROR` for the same path.
   - Assert specific state transitions and side effects in dry-run and write modes.

## Phase 3 — Verification Hardening (P1)
1. Make `verify_all.py` tool resolution deterministic.
   - Prefer `sys.executable -m ruff` with fallback to `ruff` binary.
2. Add CI job for full `pytest tests/ -q` weekly (or nightly) in addition to quick gates.
3. Add matrix coverage requirement for MCP tool paths (`scripts/mcp_server.py`) not just core scripts.

## Phase 4 — Structural Risk Reduction (P2)
1. Break monoliths over 900 lines (`score.py`, `standup.py`, `pipeline_lib.py`, `funding_scorer.py`) into domain modules.
2. Consolidate duplicated `sys.path.insert(...)` bootstrap logic into a single bootstrap utility.
3. Convert broad `except Exception` blocks in critical paths to explicit exception classes with actionable logging.

## Acceptance Criteria
- `PATH="$PWD/.venv/bin:$PATH" .venv/bin/python scripts/verify_all.py --quick` passes.
- `PATH="$PWD/.venv/bin:$PATH" .venv/bin/python -m pytest -q tests/` passes in local and CI.
- `scripts/cli.py` commands produce outputs consistent with `scripts/run.py` for overlapping commands.
- API and MCP paths expose real pipeline operations rather than placeholders.

## Rollout Strategy
1. Land P0 in a single PR (hotfix + tests).
2. Land Phase 2 in incremental PRs per API function to reduce blast radius.
3. Land Phase 3 and 4 behind feature branches with benchmark snapshots before/after refactors.

## Continuation Update (2026-03-04, pass 2)
- Replaced `sys.path.insert(...)` bootstrapping in `cli.py`, `pipeline_api.py`, and `mcp_server.py` with package-first imports and script-mode fallback imports.
- Added explicit API exception envelope (`API_OPERATION_ERRORS`) in `pipeline_api.py` to avoid blanket `except Exception` in critical command/API paths.
- Extracted job/freshness/opportunity reporting logic from `standup.py` into `standup_pipeline_sections.py`.
- Added direct tests for newly added section module:
  - `tests/test_standup_pipeline_sections.py`
- Verification:
  - `ruff check scripts/ tests/` passed.
  - Targeted regressions (CLI/API/MCP/standup/matrix) passed.
  - `scripts/verify_all.py --quick` passed.
  - Full suite passed: `1627 passed, 1 skipped`.

## Continuation Update (2026-03-04, pass 3)
- Extracted pipeline freshness/era logic into `scripts/pipeline_freshness.py`:
  - `get_entry_era`, `get_posting_age_hours`, `get_freshness_tier`, `compute_freshness_score`
  - constants: `PRECISION_PIVOT_DATE`, `JOB_FRESH_HOURS`, `JOB_WARM_HOURS`, `JOB_STALE_HOURS`
- Updated `pipeline_lib.py` to re-export the above symbols for backward compatibility and removed duplicate inline implementations.
- Extracted score TF-IDF signal helpers into `scripts/score_text_match.py`:
  - mission/evidence/track text signal helpers and text-match cache loader
- Updated `score.py` to consume extracted text-signal helpers via imports.
- Added direct tests for new modules:
  - `tests/test_pipeline_freshness.py`
  - `tests/test_score_text_match.py`
- Structural impact:
  - `pipeline_lib.py` reduced to 1007 lines (from 1196 in prior pass).
  - `score.py` reduced to 1904 lines (from 1960 in prior pass).
- Verification:
  - `ruff check scripts/ tests/` passed.
  - Targeted regressions passed (`262 passed`).
  - `scripts/verify_all.py --quick` passed.
  - Full suite passed: `1635 passed, 1 skipped`.

## Continuation Update (2026-03-04, pass 4)
- Extracted entry/date/state utilities from `pipeline_lib.py` into `scripts/pipeline_entry_state.py`:
  - `parse_date`, `parse_datetime`, `format_amount`
  - `get_effort`, `get_score`, `get_deadline`, `days_until`
  - `is_actionable`, `is_deferred`, `can_advance`
- Updated `pipeline_lib.py` to re-export these functions for backward compatibility and removed duplicated inline implementations.
- Extracted standup work sections into `scripts/standup_work_sections.py` and converted `standup.py` sections to wrappers:
  - `section_health`, `section_stale`, `section_execution_gap`, `section_plan`,
    `section_outreach`, `section_practices`, `section_replenish`, `section_deferred`
  - preserved monkeypatch behavior for `standup._load_recent_agent_runs` via wrapper injection.
- Extracted follow-up/relationship sections into `scripts/standup_relationship_sections.py`:
  - `section_followup`, `section_relationships`
  - wired wrappers in `standup.py`.
- Added direct tests for new modules:
  - `tests/test_pipeline_entry_state.py`
  - `tests/test_standup_work_sections.py`
  - `tests/test_standup_relationship_sections.py`
- Structural impact:
  - `pipeline_lib.py` now 869 lines (below 900 target).
  - `standup.py` now 896 lines (below 900 target).
- Verification:
  - `ruff check scripts/ tests/` passed.
  - Targeted regressions passed (`150 passed`).
  - `scripts/verify_all.py --quick` passed.
  - Full suite passed: `1644 passed, 1 skipped`.

## Continuation Update (2026-03-04, pass 5)
- Extracted score human-signal system into `scripts/score_human_dimensions.py`:
  - constants: `TRACK_POSITION_AFFINITY`, `POSITION_EXPECTED_ORGANS`, `CREDENTIALS`
  - signals: `_ma_*`, `_em_*`, `_tr_*`
  - orchestrator: `estimate_role_fit_from_title`, `compute_human_dimensions`
- Extracted auto-derived score dimensions into `scripts/score_auto_dimensions.py`:
  - `score_deadline_feasibility`, `score_financial_alignment`, `score_portal_friction`
  - `_get_effort_base_from_market`, `score_effort_to_value`
  - `_get_differentiation_boost`, `score_strategic_value`
- Extracted network proximity scoring into `scripts/score_network.py`:
  - `_NETWORK_DECAY`, `_days_since`, `score_network_proximity`, `_log_network_change`
- Extracted explain/review rendering into `scripts/score_explain.py`:
  - `RUBRIC_DESCRIPTIONS`, `_rubric_desc`, `explain_entry`, `review_compressed`
- Extracted reachability/triage workflows into `scripts/score_reachability.py`:
  - `_NETWORK_LEVELS`, `analyze_reachability`, `run_reachable`, `run_triage_staged`
- Converted `scripts/score.py` to compatibility wrappers/re-exports for all legacy symbols used by tests and other modules.
- Preserved backward-compatibility import surface by re-exporting `load_market_intelligence` from `score.py` for dependent modules (`funding_scorer`, `preflight`, `campaign`, `standup`).
- Added direct tests for each new module:
  - `tests/test_score_human_dimensions.py`
  - `tests/test_score_auto_dimensions.py`
  - `tests/test_score_network.py`
  - `tests/test_score_explain.py`
  - `tests/test_score_reachability.py`
- Structural impact:
  - `score.py` reduced to 896 lines (from 1904; below 900 target).
  - score domain is now split into 5 focused modules.
- Verification:
  - `ruff check scripts/ tests/` passed.
  - Targeted regressions passed (`183 passed`).
  - `scripts/verify_all.py --quick` passed.
  - Full suite passed via interpreter-coupled pytest:
    - `.venv/bin/python -m pytest -q tests/` -> `1661 passed, 1 skipped`.
