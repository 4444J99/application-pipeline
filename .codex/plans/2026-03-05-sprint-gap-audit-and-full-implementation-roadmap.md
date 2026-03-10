# Sprint Gap Audit + Full Implementation Roadmap

Date: 2026-03-05
Scope: application-pipeline diagnostics, data integrity remediation, rubric automation hardening

## 1) Verified Baseline (Current State)

Validated directly from repo and local command output:

- `python scripts/diagnose.py --objective-only` currently reports:
  - Test Coverage: **10.0** (`2197 tests; matrix strict pass`)
  - Code Quality: **9.4** (`0 lint errors; 967/1213 functions type-hinted; 0 shadow scripts`)
  - Operational Maturity: **9.5** (`7/7 agents loaded; backup <7d; notifications configured`)
  - Data Integrity: **1.0** (`669 validation errors; 0 signal errors`)
- `python scripts/validate.py --check-id-maps --check-rubric` confirms:
  - `VALIDATION FAILED — 669 file(s) with errors`
  - all 669 are `Fit score out of range: 0`
- `pipeline/research_pool` has `1362` files total; `669` have `fit.score: 0`.
- All 669 zero-score files are `status: research`, `track: job`, `tags` include `auto-sourced`, source is `source_jobs.py`.

## 2) Audit Findings (Errors/Gaps in Prior Plan)

### P0-1: Root cause is known and deterministic, not yet targeted directly

- `scripts/source_jobs.py` writes `fit.score: 0` for every new auto-sourced entry.
- `scripts/validate.py` enforces score range `1..10`, so every such file fails validation.
- Prior plan proposed broad triage/reprocessing first, but the write-time defect should be fixed before backfill.

### P0-2: Dispatcher regression introduced during command expansion

- `scripts/run.py` defines `"resumes"` twice in `COMMANDS`; first mapping is overridden silently by Python dict semantics.
- Result: `build_resumes.py` command path is currently unreachable via `run.py`.

### P1-1: Operational maturity metric is incomplete vs rubric intent

- `measure_operational_maturity()` does not run `monitor_pipeline.py --strict`; it only checks agent status, backup age, and `notifications.yaml` existence.
- This can overstate maturity by missing strict monitor failures.

### P1-2: Data-integrity metric saturates and loses decision value

- `measure_data_integrity()` counts files-with-errors, not severity by error class.
- Score curve bottoms out at `1.0` for large counts, so incremental remediation is not visible once above saturation.

### P2-1: Rubric synchronization is partial

- `diagnose_ira.py` agreement interpretation bands can load from rubric.
- But score binning (`critical/below_average/...`) remains hardcoded in code.
- Prior claim that all categorical agreement logic is rubric-driven is overstated.

### P2-2: Quality-tooling expansion plan needs dependency/runtime prep

- Proposed `coverage.py`, `mypy`, `pylint` are not in current dev dependencies.
- CI and `verify_all.py` currently gate on matrix + ruff + validate + pytest; no coverage/type gates yet.

## 3) Improved Implementation Plan (Phased, Concrete)

## Phase A (P0): Correct Contract Mismatch + Fast Structural Fixes

Goal: stop generating new invalid data, remove high-impact regression.

1. Fix write-time source of `fit.score: 0`
- Update `source_jobs.py` entry creation to assign a valid initial fit score (recommended: `pre_score` integration) instead of `0`.
- Keep score semantics explicit: "initial estimate" until full `score.py --all` recompute.
- Ensure discover flow stays consistent (discover already computes `_score`; align persisted value logic).

2. Fix run dispatcher key collision
- Resolve duplicate `resumes` command key by splitting into distinct command names, e.g.:
  - `resumes-build` -> `build_resumes.py`
  - `resumes-check` -> `upgrade_resumes.py`
- Preserve backward compatibility with one alias if needed, but avoid silent override.

3. Tests for both fixes
- Add/extend tests to assert:
  - auto-sourced entries created by source_jobs have score in valid range.
  - `run.py` command table has no duplicate keys for standalone commands.

Exit criteria:
- New source-ingested entries no longer fail validation for score=0.
- Dispatcher exposes both resume operations unambiguously.

## Phase B (P0): One-Time Data Remediation for Existing 669 Entries

Goal: clear current backlog and restore Data Integrity to operationally useful range.

1. Pre-remediation safety
- Generate backup artifact before bulk edits.

2. Backfill strategy (use existing scoring engine)
- Re-score `research_pool` entries with existing scoring logic instead of ad-hoc patching.
- Prefer deterministic batch path that writes valid dimensions and composite scores.
- Record before/after counts for:
  - zero-score files
  - validate errors

3. Validate + verify
- Run validation with id-map/rubric checks.
- Run targeted tests for modified ingestion/scoring/diagnostics.

Exit criteria:
- `fit.score: 0` count reduced from 669 to 0 (or explicit documented exceptions).
- Validation error count attributable to this class is 0.

## Phase C (P1): Close Operational Maturity Automation Gap

Goal: make `9.5 -> 10.0` achievable via fully automated checks, not file-presence proxies.

1. Add notification config validator
- Implement strict config validation (required keys, channel/event validity, basic shape checks).
- Reuse in `notify.py --config` and in diagnostics.

2. Strengthen `measure_operational_maturity()`
- Execute `monitor_pipeline.py --strict` and include result in score.
- Replace simple `notifications.yaml exists` with validator pass/fail.

3. Tests
- Add diagnose tests for strict-monitor failure and invalid notification schema cases.

Exit criteria:
- Operational maturity score reflects strict monitoring + config validity.
- Manual `notifications.yaml` check no longer required.

## Phase D (P1): Make Quality Metrics Objective and Reproducible

Goal: implement the previous proposal safely with minimal CI disruption.

1. Add tooling incrementally
- Add `coverage` and `mypy` to dev dependencies.
- Keep `pylint` optional until signal-to-noise is proven.

2. Coverage baseline first, gating second
- Produce coverage report artifact in CI and local verify path.
- Do not fail builds initially; set baseline and ratchet policy later.

3. Type checking scope control
- Start with `scripts/` subset (or selected modules), exclude legacy/deprecated paths initially.
- Add gradual strictness rollout plan.

4. Rubric integration
- Update rubric and diagnose evidence text to distinguish:
  - test count/matrix coverage
  - line/branch coverage
  - type-check health

Exit criteria:
- CI emits coverage + type-check signals.
- Diagnose report references objective outputs, not qualitative placeholders.

## Phase E (P2): Finish Rubric-Driven Diagnostic Semantics

Goal: remove residual hardcoded agreement/scoring bands.

1. Move IRA bin thresholds to rubric config
- Add explicit bin definitions to `system-grading-rubric.yaml`.
- Make `diagnose_ira.bin_score()` read bins from rubric with fallback.

2. Add regression tests
- Tests that rubric-edited bins change categorization behavior deterministically.

3. Data integrity metric decomposition
- In diagnose details, report counts by error class (e.g., fit-range, portal mismatch, timeline ordering).
- Optionally score against percent-invalid and severity weighting.

Exit criteria:
- Agreement interpretation + binning both configurable via rubric.
- Data-integrity progress visible during partial remediation.

## 4) Execution Order and Timeboxing

Recommended order:
1. Phase A (same day)
2. Phase B (same day immediately after A)
3. Phase C (next day)
4. Phase D (next 1-2 days)
5. Phase E (after D baseline stabilizes)

Rationale:
- A and B directly remove the dominant failure mode (669 errors) and prevent recurrence.
- C closes known automation gap in maturity scoring.
- D/E improve metric fidelity without blocking immediate system health restoration.

## 5) Validation Checklist per Phase

Phase A:
- `python scripts/source_jobs.py --fetch --yes --limit 1` (or fixture-based test path)
- `python scripts/validate.py --check-id-maps --check-rubric`
- `pytest tests/test_source_jobs.py tests/test_run.py -q`

Phase B:
- backup created and timestamped
- `python scripts/score.py --all` (or controlled batch variant)
- `python scripts/validate.py --check-id-maps --check-rubric`
- before/after remediation summary recorded

Phase C:
- `python scripts/monitor_pipeline.py --strict`
- `python scripts/notify.py --config`
- `pytest tests/test_diagnose.py tests/test_notify.py -q` (add tests as needed)

Phase D/E:
- coverage and mypy reports generated in CI artifacts
- updated rubric parsed by diagnose + diagnose_ira without fallback errors
- targeted tests pass

## 6) Risk Controls

- Always backup before bulk YAML rewrites.
- Keep remediation idempotent and dry-run capable when possible.
- Land metric-model changes (Phase D/E) separately from data backfill (Phase B) to preserve blame clarity.
- Avoid introducing hard gates on new tools until baseline noise is characterized.

## 7) Definition of Done for "Next Sprint Complete"

- New auto-sourced entries no longer introduce `fit.score: 0` validation failures.
- Existing 669 invalid entries remediated (or exceptions documented and excluded by explicit policy).
- `run.py` dispatcher collision fixed and test-covered.
- Operational maturity metric includes strict monitor + notification config validation.
- Coverage/type metrics are integrated as objective signals (at least non-blocking baseline).
- IRA binning/config fully rubric-driven (or explicitly tracked as remaining delta).
