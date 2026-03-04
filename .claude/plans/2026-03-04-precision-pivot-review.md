# Evaluation-to-Growth: Precision-Over-Volume Pivot Review

**Date:** 2026-03-04
**Status:** Implemented

## Summary

Applied Evaluation-to-Growth framework to the precision-over-volume pivot (`fb79f51`).
Identified 8 weaknesses, 3 contradictions, and implemented 6 fixes.

## Fixes Implemented

1. **Wire AUTO_QUALIFY_MIN** — `score.py` `run_auto_qualify()` and argparse now use rubric-loaded `AUTO_QUALIFY_MIN` (9.0) instead of hardcoded 7.0
2. **Stale references** — Fixed 4 locations: CLAUDE.md (7.0→9.0, 8.5→9.0), run.py (8.5→9.0), ingest_top_roles.py docstring (8.5→9.0)
3. **Agent Rule 4 score gate** — Added `min_score: 9.0` to prevent sub-threshold entries from advancing drafting→staged
4. **mutual_connections signal** — `score_network_proximity()` now scores `network.mutual_connections >= 5` → min 5
5. **MEMORY.md** — Replaced volume benchmarks with precision-era values
6. **Tests** — Added `test_run_auto_qualify_default_uses_rubric_threshold`, 7 mutual_connections tests, invalid enum edge case

## Files Modified

| File | Change |
|------|--------|
| `scripts/score.py` | Wired AUTO_QUALIFY_MIN into defaults; added mutual_connections signal |
| `CLAUDE.md` | Fixed 7.0→9.0 and 8.5→9.0 references |
| `scripts/run.py` | Fixed topjobs label 8.5→9.0 |
| `scripts/ingest_top_roles.py` | Fixed docstring 8.5→9.0 |
| `strategy/agent-rules.yaml` | Added min_score: 9.0 to Rule 4 |
| `tests/test_score.py` | Added AUTO_QUALIFY_MIN wiring test |
| `tests/test_network_proximity.py` | Added 7 mutual_connections tests + invalid enum test |
| `MEMORY.md` | Replaced volume benchmarks |

## Acknowledged Risks (not addressed — by design)

- No rollback mechanism for precision mode
- 25 submitted entries retain volume-era scores
- 948 research_pool entries not rescored (9.0 will reject most — intended)
- No time decay on network signals (deferred to future iteration)
- Case-sensitive org matching in density signal (low severity)
