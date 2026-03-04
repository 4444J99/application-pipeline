# Precision-Over-Volume Pipeline Pivot

**Date:** 2026-03-04
**Status:** Implemented

## Context

60 cold applications in 4 days → 0 interviews, 5 resume-screen rejections. Pipeline optimized for volume (3-5/day) when it should optimize for finding perfect-fit roles.

## Changes Implemented

### Phase 1: Scoring Rubric Overhaul
- Added `network_proximity` as 9th dimension (12% creative, 20% job weight)
- Raised all thresholds: auto_qualify 7.0→9.0, auto_advance 8.0→9.5, tier1 8.5→9.5
- Implemented `score_network_proximity()` in score.py (~60 lines)
- Added `network` field to pipeline schema

### Phase 2: Volume Benchmarks Eliminated
- Daily target: 3→0, weekly max: 20→2, sweet spot: 21-80→5-15
- Stale thresholds relaxed: 7→14 days, stagnant 14→30, response_overdue 21→30
- Added `precision_strategy` section to market-intelligence-2026.json

### Phase 3: Pipeline Constants
- EFFORT_MINUTES doubled (quick 30→60, standard 90→180, deep 270→480)
- COMPANY_CAP 3→1 (max 1 per org)
- REPLENISH_THRESHOLD 5→3, EXECUTION_STALE_STAGED_DAYS 3→7
- Agent rules: advance thresholds 7.0→9.0, 8.0→9.5
- Ingest: MIN_SCORE 8.5→9.0, TOP_N 10→5
- Standup messaging replaced volume pressure with relationship investment guidance

### Phase 5: Strategy Docs
- job-prioritization.md: replaced "3-5 apps/day" with precision weekly workflow
- CLAUDE.md: added "Pipeline Philosophy: Precision Over Volume" section

### Phase 6: Tests
- Created tests/test_network_proximity.py (26 tests)
- Updated 8 test files: dimension count 8→9, threshold assertions, company cap, staleness

## Files Modified (13 + 1 new)
1. strategy/scoring-rubric.yaml
2. strategy/market-intelligence-2026.json
3. strategy/agent-rules.yaml
4. scripts/pipeline_lib.py
5. scripts/score.py
6. pipeline/_schema.yaml
7. scripts/standup.py
8. scripts/ingest_top_roles.py
9. strategy/job-prioritization.md
10. CLAUDE.md
11. tests/test_score.py
12. tests/test_standup.py
13. tests/test_validate.py
14. tests/test_pipeline_lib.py
15. tests/test_company_cap.py
16. tests/test_check_outcomes.py
17. tests/test_hygiene.py
18. tests/test_network_proximity.py (new)

## Verification
- ruff check: clean
- pytest: 1462 passed, 1 skipped (2 pre-existing failures in test_funding_scorer excluded)
- validate.py: 1052 entries valid
