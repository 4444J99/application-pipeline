# Wiring Tests — Implementation Record

**Created:** 2026-03-30
**Author:** Claude (AI Assistant)
**Purpose:** Document the wiring test suite for the application-pipeline

---

## Overview

Created 4 new test files to verify the "wiring" (logical and data-flow connections) between components in the application-pipeline. These tests follow the "Christmas Light" hierarchy metaphor — verifying each connection in the chain is intact.

---

## Test Files Created

### 1. tests/test_wiring_data_flow.py (31 tests)

Tests data loading interfaces between pipeline_lib and downstream scripts:

- `load_entries()` — Pipeline YAML loading with metadata (_dir, _file)
- `load_entry_by_id()` — Single entry lookup
- `load_profile()` — Target profile loading with PROFILE_ID_MAP fallback
- `load_block()` — Block content loading from blocks/ directory
- `load_variant()` — Variant content loading
- `load_legacy_script()` — Legacy submission scripts with LEGACY_ID_MAP
- End-to-end data flow wiring between loaders
- Directory existence checks

### 2. tests/test_wiring_state.py (29 tests)

Tests state machine transitions:

- `VALID_TRANSITIONS` completeness and consistency
- `is_actionable()` function behavior
- `is_deferred()` function behavior  
- `can_advance()` function behavior
- Entry status consistency with valid transitions
- State machine invariants (forward progress, no orphaned statuses)

### 3. tests/test_wiring_signals.py (33 tests)

Tests signal file integrity:

- Signal file existence (contacts.yaml, outreach-log.yaml, network.yaml, conversion-log.yaml, hypotheses.yaml)
- contacts.yaml structure and integrity
- network.yaml structure
- contacts.yaml ↔ network.yaml consistency
- outreach-log.yaml → contacts.yaml references
- conversion-log.yaml state transitions
- hypotheses.yaml → entry references
- Entry → Signal file wiring
- Date consistency across signal files

### 4. tests/test_wiring_apply.py (21 tests)

Tests apply.py orchestration flow:

- apply.py import structure
- Entry loading for apply
- Standard answers wiring
- Greenhouse question extraction
- Answer generation wiring
- Contact loading for apply
- Cover letter resolution wiring
- Application directory creation
- DM composition wiring
- Integration tests for full apply flow
- Error handling

---

## Test Results

```
============================= test session starts ==============================
tests/test_wiring_data_flow.py ........... 31 passed
tests/test_wiring_state.py ................ 29 passed  
tests/test_wiring_signals.py .............. 33 passed
tests/test_wiring_apply.py ................ 21 passed

Total: 114 passed in 10.68s
```

---

## Running the Tests

```bash
# Run all wiring tests
python -m pytest tests/test_wiring_data_flow.py tests/test_wiring_state.py tests/test_wiring_signals.py tests/test_wiring_apply.py -v

# Run individual test files
python -m pytest tests/test_wiring_data_flow.py -v
python -m pytest tests/test_wiring_state.py -v
python -m pytest tests/test_wiring_signals.py -v
python -m pytest tests/test_wiring_apply.py -v
```

---

## Design Philosophy

These tests verify the "wiring" between components — the logical and data-flow connections that make the pipeline work. They follow two patterns:

1. **Live-data tests** — Validate against actual YAML files in the repo
2. **Isolated tests** — Use monkeypatch and tmp_path for unit testing

The tests are designed to catch regressions when:
- ID maps are updated but references break
- Status transitions change but validation doesn't
- Signal files are modified without updating references
- apply.py sub-modules are refactored

---

## Related Documentation

- CLAUDE.md — Project context and architecture
- tests/conftest.py — Test configuration and fixtures
- scripts/pipeline_lib.py — Central hub with single sources of truth
- scripts/pipeline_entry_state.py — Entry state machine
- scripts/apply.py — Canonical application command
