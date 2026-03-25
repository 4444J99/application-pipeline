---
name: Outreach data persistence gap
description: LinkedIn DM activity is not persisting back to pipeline signal files — outreach-log, contacts, network all lag behind actual activity. 30 DMs sent but only 19 logged. Root cause is no single ingestion point.
type: project
---

LinkedIn outreach actions are happening but not being logged consistently across the three signal files (outreach-log.yaml, contacts.yaml, network.yaml).

**Why:** Each DM requires updating 3 files separately. `followup.py --log` only updates outreach-log and the entry YAML, not contacts or network. No batch reconciliation tool exists.

**Impact:** Warm-path analysis showed 3/23 when the real number was 10/23. Standup/followup dashboards show stale data. Protocol validator can't find connect notes. Network graph underreports.

**How to apply:** Build a reconciliation tool (`reconcile.py` or `log-dm` command) that:
1. Accepts pasted LinkedIn DM history
2. Parses contact names, dates, message text
3. Diffs against existing logged data
4. Backfills outreach-log.yaml, contacts.yaml, network.yaml in one pass

Also consider: `log-dm` single command for real-time logging of individual DMs across all three files.

Identified 2026-03-24. User expressed frustration ("very annoying"). Priority fix for next session.
