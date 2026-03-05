# Application Pipeline: Five-Phase Infrastructure Enhancement

## Context

The pipeline has 797 entries but is operationally congested: 59 actionable entries vs max 10 allowed, 54 staged entries all stale and below the 9.0 threshold, org-cap violations everywhere. The system has ~65 scripts generating signals that aren't connected — no cross-file validation, no machine-readable output for dashboards, no notification layer, no trend tracking. This plan closes those gaps across 5 phases (~3,400 new lines, 8 new scripts, 7 new test files).

---

## Phase 1: Referential Integrity & Pipeline Triage Gate

**Why:** Signal files reference pipeline entries that may not exist. Org-cap violations are advisory only. 54 staged entries below threshold clog the pipeline.

### 1a. Cross-file referential integrity — `scripts/validate_signals.py` MODIFIED (+55 lines)
- Add `_collect_all_entry_ids() -> set[str]` scanning all pipeline dirs
- Add `validate_referential_integrity(errors)` checking:
  - conversion-log `id` → pipeline entry exists
  - hypotheses `entry_id`/`id` → pipeline entry exists
- Wire into `validate_all_signals()` after existing 4 checks

### 1b. Deduplication & org-cap validation — `scripts/validate.py` MODIFIED (+65 lines)
- Add `validate_no_duplicate_urls(entries, errors)` — detect same `target.application_url`
- Add `validate_org_cap_warnings(entries, warnings)` — flag >1 active+submitted per org
- Add `--check-org-cap` CLI flag

### 1c. Triage automation — `scripts/triage.py` NEW (~180 lines)
- `triage_staged_backlog(entries, min_score=9.0, dry_run=True)` — demote sub-threshold staged → qualified
- `triage_org_cap(entries, cap=1, dry_run=True)` — keep highest-scored per org, defer rest
- `--report` (default), `--execute --yes`, `--org-cap`, `--min-score`

### 1d. Wire into CI — `scripts/verify_all.py` MODIFIED (+3 lines)
- Add `--check-org-cap` to pipeline-validation command

### 1e. Tests
- `tests/test_validate_signals.py` MODIFIED (+60 lines) — referential integrity valid/dangling
- `tests/test_validate.py` MODIFIED (+45 lines) — duplicate URL, org-cap warnings
- `tests/test_triage.py` NEW (~140 lines) — staged demotion, org-cap resolution, dry-run

### 1f. `scripts/run.py` MODIFIED — add `triage` command

---

## Phase 2: Machine-Readable Pipeline (--json everywhere)

**Why:** Foundation for dashboards, notifications, and trend tracking. Currently all reports are text-only.

### 2a. `scripts/standup.py` MODIFIED (+45 lines)
- Add `--json` flag
- Add `collect_standup_data(hours, section) -> dict` gathering all section dicts
- JSON mode prints `json.dumps(payload)` instead of formatted text

### 2b. `scripts/conversion_dashboard.py` MODIFIED (+35 lines)
- Add `--json` flag
- Add `generate_dashboard_data() -> dict` with portals/positions/tracks/response_times/blocks/calibration

### 2c. `scripts/campaign.py` MODIFIED (+55 lines)
- Add `--json` flag
- Add `generate_campaign_data(entries, days) -> dict` with tiers/deadlines/execution_order

### 2d. `scripts/crm.py` MODIFIED (+40 lines)
- Add `--json` flag
- Add `generate_crm_data(contacts) -> dict` with stats/by_org/overdue/uncovered

### 2e. Daily snapshots — `scripts/snapshot.py` NEW (~220 lines)
- `capture_snapshot() -> dict` — entry counts, scores, org-cap violations, stale count
- `load_snapshot(date_str)`, `compute_deltas(current, previous)`
- Saves to `signals/daily-snapshots/YYYY-MM-DD.json`
- `--report`, `--save`, `--trends` (7d/30d/90d deltas), `--json`

### 2f. Tests
- `tests/test_standup.py` MODIFIED (+30 lines) — JSON output valid
- `tests/test_conversion_dashboard.py` MODIFIED (+25 lines) — dashboard data structure
- `tests/test_campaign.py` MODIFIED (+25 lines) — campaign data structure
- `tests/test_crm.py` MODIFIED (+25 lines) — CRM data structure
- `tests/test_snapshot.py` NEW (~100 lines) — capture/deltas/trends/save/load

### 2g. `scripts/run.py` MODIFIED — add `snapshot` command

---

## Phase 3: Notification Layer + MCP Expansion

**Why:** Makes the system self-reporting. Weekly briefs and agent actions currently vanish into stdout.

### 3a. Notification dispatcher — `scripts/notify.py` NEW (~180 lines)
- `dispatch_webhook(payload, url) -> (bool, str)` — POST JSON via stdlib urllib
- `dispatch_email(subject, body, recipients) -> (bool, str)` — extract SMTP logic from `daily_pipeline_health.py` lines 64-103
- `dispatch_event(event_type, payload) -> list` — route to configured channels
- Config: `strategy/notifications.yaml` with webhook URLs and email recipients per event type
- Events: `weekly_brief`, `agent_action`, `deadline_alert`, `outcome_received`, `triage_report`
- `--test-webhook`, `--test-email`, `--config`

### 3b. `strategy/notifications.yaml` NEW (~15 lines)
- Webhook + email config with event subscriptions

### 3c. `scripts/weekly_brief.py` MODIFIED (+15 lines)
- After `--save`, dispatch `weekly_brief` event via `notify.dispatch_event()`
- Add `--notify` flag

### 3d. `scripts/agent.py` MODIFIED (+10 lines)
- After `--execute`, dispatch `agent_action` event with actions taken

### 3e. MCP expansion — `scripts/mcp_server.py` MODIFIED (+80 lines)
- Add tools: `pipeline_funnel()`, `pipeline_snapshot()`, `pipeline_triage()`, `pipeline_crm_dashboard()`, `pipeline_campaign()`
- Each imports from the corresponding script's data-generation function

### 3f. Weekly briefing automation — `launchd/com.4jp.pipeline.weekly-briefing.plist` NEW (~30 lines)
- Sunday 7PM schedule, invokes `weekly_brief.py --save`

### 3g. Tests
- `tests/test_notify.py` NEW (~120 lines) — config loading, webhook/email dispatch (mocked), event routing
- `tests/test_mcp_server.py` MODIFIED (+45 lines) — new tool coverage

### 3h. `scripts/run.py` MODIFIED — add `notify` command

---

## Phase 4: Intelligence Feedback Loops

**Why:** Close the learning cycle — org intelligence, skills gaps, block-outcome correlation, trend detection.

### 4a. Org intelligence — `scripts/org_intelligence.py` NEW (~250 lines)
- `aggregate_org(org, entries, contacts) -> dict` — entries, contacts, outcomes, avg_score, response_times, network_density
- `rank_orgs(entries, contacts) -> list` — sorted by composite opportunity score
- `--all`, `--org <name>`, `--json`

### 4b. Skills gap analysis — `scripts/skills_gap.py` NEW (~200 lines)
- Reuse `text_match.py` TF-IDF tokenizer
- `extract_required_skills(entry) -> list[str]` from research.md
- `compute_coverage(required, content) -> dict` with coverage_pct, matched, missing, suggested_blocks
- `--target <id>`, `--all`, `--json`

### 4c. Block-outcome correlation — `scripts/block_outcomes.py` NEW (~200 lines)
- `compute_block_cross_tabs(entries) -> dict` — block usage × position × portal × outcome
- `classify_blocks(cross_tabs) -> dict` with golden/neutral/toxic categories
- `--toxic`, `--golden`, `--json`

### 4d. Trend analysis — `scripts/snapshot.py` MODIFIED (+60 lines)
- `compute_slope(values) -> float` — linear regression for trend direction
- `detect_inflections(snapshots, key) -> list[str]` — flag metric reversals

### 4e. Tests
- `tests/test_org_intelligence.py` NEW (~100 lines)
- `tests/test_skills_gap.py` NEW (~90 lines)
- `tests/test_block_outcomes.py` NEW (~100 lines)
- `tests/test_snapshot.py` MODIFIED for trend tests

### 4f. `scripts/run.py` MODIFIED — add `orgs`, `skillsgap`, `blockoutcomes` commands

---

## Phase 5: Calendar + CRM Integration

**Why:** Ambient deadline awareness + relationship intelligence + interview readiness.

### 5a. Calendar export — `scripts/calendar_export.py` NEW (~180 lines)
- Pure stdlib iCal generation (VCALENDAR/VEVENT/VALARM text format)
- `generate_vevent(uid, summary, dtstart, description, alarms=[7,1]) -> str`
- `generate_calendar(entries, include_followups=False) -> str`
- Events: deadlines with 7d/1d alarms, follow-up dates, agent schedule
- `--output <path>`, `--follow-ups`, `--json`

### 5b. CRM-pipeline deepening — `scripts/crm.py` MODIFIED (+50 lines)
- `suggest_all_proximity(contacts, entries) -> list[dict]` — compute network_proximity from contact depth
- `--wire-proximity` flag to update entry YAML `fit.dimensions.network_proximity`

### 5c. CRM schema validation — `scripts/validate_signals.py` MODIFIED (+40 lines)
- `validate_contacts(errors) -> int` — required fields, valid channels, date formats
- Wire into `validate_all_signals()`

### 5d. Interview prep — `scripts/interview_prep.py` NEW (~230 lines)
- `generate_prep(entry_id) -> str` combining:
  - Role overview (pipeline YAML + research.md)
  - Org intelligence (from org_intelligence.py)
  - Skills gap (from skills_gap.py)
  - STAR question bank (per identity position, hardcoded)
  - Talking points (from blocks used in submission)
- `--target <id>`, `--auto` (all interview-status entries)
- Output: `submissions/<entry-id>-interview-prep.md`

### 5e. Calendar launchd agent — `launchd/com.4jp.pipeline.calendar-refresh.plist` NEW (~30 lines)
- Daily 6:45 AM, refreshes `~/Calendar/pipeline-deadlines.ics`

### 5f. Tests
- `tests/test_calendar_export.py` NEW (~100 lines)
- `tests/test_crm.py` MODIFIED (+30 lines) — proximity suggestion/wiring
- `tests/test_interview_prep.py` NEW (~80 lines)

### 5g. `scripts/run.py` MODIFIED — add `calendar`, `interviewprep` commands

---

## Inventory

| Phase | New Scripts | Modified Scripts | New Tests | Modified Tests | Config/Other | Est. Lines |
|-------|-------------|-----------------|-----------|---------------|-------------|-----------|
| 1 | triage.py | validate_signals, validate, verify_all, run | test_triage | test_validate_signals, test_validate | — | ~550 |
| 2 | snapshot.py | standup, conversion_dashboard, campaign, crm, run | test_snapshot | test_standup, test_conv_dash, test_campaign, test_crm | — | ~600 |
| 3 | notify.py | weekly_brief, agent, mcp_server, run | test_notify | test_mcp_server | notifications.yaml, weekly-briefing.plist | ~500 |
| 4 | org_intelligence, skills_gap, block_outcomes | snapshot, run | test_org_intel, test_skills_gap, test_block_outcomes | test_snapshot | — | ~1000 |
| 5 | calendar_export, interview_prep | crm, validate_signals, run | test_calendar_export, test_interview_prep | test_crm | calendar-refresh.plist | ~750 |
| **Total** | **8** | **14** | **7** | **8** | **3** | **~3,400** |

## Dependency Order

```
Phase 1 (integrity/triage)
  └─► Phase 2 (JSON output)
        ├─► Phase 3 (notifications + MCP)  ← can parallel with Phase 4
        └─► Phase 4 (intelligence loops)
              └─► Phase 5 (calendar + CRM + interview)
```

## Verification

After each phase:
1. `source .venv/bin/activate && python scripts/verify_all.py` — full CI gate
2. `pytest tests/ -v` — all tests pass
3. `ruff check scripts/ tests/` — no lint errors
4. Smoke test new commands via `python scripts/run.py <command>`

After all phases:
5. Update CLAUDE.md: Commands, Quick Commands table, Configuration Files, Automation table
6. Commit and push
