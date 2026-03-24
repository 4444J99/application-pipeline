---
name: Freshness Gate & Scoring Recalibration 2026-03-15
description: Automatic 72h freshness gate for active entries; scoring thresholds recalibrated from 9.0 to 7.0
type: project
---

## Automatic 72h Freshness Gate (2026-03-15)

`flush_stale_active_jobs()` in `pipeline_freshness.py` runs automatically before `standup.py`, `morning.py`, and `campaign.py` output. Moves job-track entries in `active/` older than 72h to `research_pool/` with status reset to `research`.

- Exempt tracks: grant, residency, fellowship, creative, writing (deadline-based, not posting-based)
- `score.py --auto-qualify` also skips stale job entries (won't promote entries that would be immediately flushed)
- Threshold loaded from `_load_freshness_thresholds()` (market-intelligence JSON → fallback 72h)

**Why:** User was seeing the same 2-week-old entries every session. Leads are only valuable when hot.

## Scoring Threshold Recalibration (2026-03-15)

`strategy/scoring-rubric.yaml` thresholds changed:

| Threshold | Old | New | Rationale |
|-----------|-----|-----|-----------|
| auto_qualify_min | 9.0 | 7.0 | 9.0 required network_proximity≥12.5 with realistic dims (impossible on 1-10 scale) |
| auto_advance_to_drafting | 9.5 | 7.5 | Best real entry (Anthropic Agent SDK) scores exactly 7.5 |
| tier1_cutoff | 9.5 | 8.0 | Warm connection + strong fit ceiling |
| tier2_cutoff | 8.5 | 7.0 | Cold but strong evidence match |
| tier3_cutoff | 7.0 | 6.0 | Worth watching |

Also updated: `pipeline_lib.py` precision mode default (9.0→7.0), `triage.py` (reads from rubric), `standup_work_sections.py` and `standup_relationship_sections.py` (read from `get_auto_qualify_min()`).

**Why:** The 9.0 threshold was set before `network_proximity` (0.20 weight for jobs) was added. Mathematical ceiling for cold applications: 8.2 (all other dims at 10). No entry in 2,000+ ever reached 9.0.

**How to apply:** These are now the live thresholds. If scoring feels too permissive, raise `auto_qualify_min` — but never above 8.0 while network_proximity carries 0.20 weight for cold applications.
