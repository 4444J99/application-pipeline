# Wiring Tests Review — Issue Proposals

**Date:** 2026-03-31
**Source:** Evaluation-to-Growth analysis of 114 wiring tests
**Status:** Ready for issue creation

---

## Context

Created 4 wiring test files covering data flow, state machine, signal file integrity, and apply.py orchestration. All 114 tests pass. This review identifies gaps and improvements.

---

## Proposed Issues

### Issue 1: Add ID Map Consistency Test

**Priority:** Medium
**Type:** test
**Labels:** testing, wiring

PROFILE_ID_MAP and LEGACY_ID_MAP are tested indirectly — we check names are non-empty but not that the referenced files actually exist. Silent breakage when someone adds an entry without updating maps.

**Fix:** Assert `PROFILES_DIR / f"{profile_name}.json"` exists for each PROFILE_ID_MAP value. Same for LEGACY_ID_MAP → LEGACY_DIR.

**File:** `tests/test_wiring_data_flow.py`

---

### Issue 2: Add Negative Test Cases for Wiring Tests

**Priority:** High
**Type:** test
**Labels:** testing, wiring, coverage

Tests verify happy path only. Missing:
- `load_entry_by_id()` with unparseable YAML
- `load_profile()` when file referenced by map is deleted
- `can_advance()` with completely unknown statuses
- Signal file with corrupted YAML
- apply.py with missing `target` field

**Approach:** Add to existing wiring test files using isolated tests (monkeypatch, tmp_path).

**Estimated:** 5-8 new tests across all 4 files.

---

### Issue 3: Add Full Pipeline Integration Test

**Priority:** Medium
**Type:** test
**Labels:** testing, integration

Wiring tests cover individual components but don't test the full lifecycle: research → qualified → staged → submitted. A single integration test would verify the chain end-to-end.

**File:** New `tests/test_wiring_integration.py`

---

### Issue 4: Mark Network-Dependent Apply Tests

**Priority:** Low
**Type:** chore
**Labels:** testing, ci

Some apply.py tests could make real HTTP calls (Greenhouse API). Add `@pytest.mark.synthetic` to prevent flakiness in CI.

**File:** `tests/test_wiring_apply.py`

---

## Session Context

From S-wiring session ledger (2026-03-30):
- Portfolio code at a950ee0 (synced)
- 7 vacuums identified at close-out
- Next phase: IV-A stranger test
- IRF items: PRT-019 through PRT-023
