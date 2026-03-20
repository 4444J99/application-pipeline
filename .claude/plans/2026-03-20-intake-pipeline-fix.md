# Plan: Universal Intake Pipeline Fix

**Date:** 2026-03-20
**Problem:** 994 research_pool entries ingested by `source_jobs.py` but never scored. 902 score ≥ 7.0. 584 are warm-path leads at orgs with contacts. Zero were evaluated.
**Root cause:** `agent.py` calls `load_entries()` which defaults to `ALL_PIPELINE_DIRS` (active/submitted/closed), excluding `PIPELINE_DIR_RESEARCH_POOL`.

---

## The Universal Fix: Three Layers

### Layer 1: agent.py — Include Research Pool in Scan

**File:** `scripts/agent.py` line 476
**Current:** `entries = load_entries()`
**Fix:** `entries = load_entries(dirs=ALL_PIPELINE_DIRS_WITH_POOL)`

This single change makes Rules 1 and 2 operate on research_pool entries:
- Rule 1: Score unscored research entries → assigns scores to 0.0 entries
- Rule 2: Research + score ≥ threshold → auto-advance to active/qualified

**Safety:** Rule 2 already enforces org-cap and allocation limits. The promotion state machine prevents invalid transitions. No new logic needed — just broader input.

**Import fix:** Add `ALL_PIPELINE_DIRS_WITH_POOL` to the import from `pipeline_lib`.

### Layer 2: source_jobs.py — Stamp created_at on Intake

**File:** `scripts/source_jobs.py`
**Fix:** When writing new YAML entries, add `created_at: YYYY-MM-DD` field.

Currently entries have no creation date, making age-based analysis impossible. The `created_at` field enables:
- Freshness monitoring (are postings still live?)
- Intake velocity tracking (how many new roles per week?)
- Staleness detection without HTTP requests

### Layer 3: Governance — No Entry Without Evaluation

**Principle:** An unscored entry is an entry in an invalid state. The system that enforces forward-only transitions on entries must enforce that evaluation happens on intake.

**Implementation:** Add a `daily-intake-triage` LaunchAgent that runs after `source_jobs.py`:

```
source_jobs.py → score.py --all --include-pool → auto-qualify
```

Schedule: Daily at 6:15 AM (after source_jobs runs, before standup at 6:30 AM).

**LaunchAgent plist:**
```xml
<key>Label</key>
<string>com.4jp.pipeline.daily-intake-triage</string>
<key>ProgramArguments</key>
<array>
    <string>/opt/anaconda3/bin/python</string>
    <string>/Users/4jp/Workspace/4444J99/application-pipeline/scripts/score.py</string>
    <string>--all</string>
    <string>--include-pool</string>
</array>
<key>StartCalendarInterval</key>
<dict>
    <key>Hour</key><integer>6</integer>
    <key>Minute</key><integer>15</integer>
</dict>
```

---

## Validation

After implementing:
1. `agent.py --plan` should show research_pool entries in its scan
2. No entry in research_pool should have score 0.0 after the daily triage runs
3. `standup.py` should report research_pool entries that scored ≥ 7.0 as "pending triage"
4. `validate.py` could add a gate: entries with `status: research` and `created_at > 7 days` and `score == 0` → warning

---

## What This Does NOT Change

- Research_pool entries are never deleted — they are observation data
- The org-cap (max 1 per org in active/) still enforces precision
- The scoring rubric is unchanged — scores are deterministic
- Manual review is still required before submission — auto-qualify promotes to `qualified`, not `staged`

---

## Implementation Steps

1. [ ] Fix `agent.py` line 476: use `ALL_PIPELINE_DIRS_WITH_POOL`
2. [ ] Fix `source_jobs.py`: stamp `created_at` on new entries
3. [ ] Create LaunchAgent plist for daily intake triage
4. [ ] Add `intake-triage` command to `run.py` (runs score --all --include-pool)
5. [ ] Add validation gate: warn on unscored entries older than 7 days
6. [ ] Run initial backfill: `score.py --all --include-pool --yes` to score all 994
7. [ ] Update CLAUDE.md with the new automation schedule
8. [ ] Write tests for the agent.py change
