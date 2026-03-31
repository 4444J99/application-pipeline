---
name: Outreach data persistence gap — RESOLVED 2026-03-25
description: LinkedIn DM activity was not persisting to signal files. RESOLVED with log_dm.py (single-command) and reconcile_outreach.py (batch backfill). Both operational.
type: project
---

**STATUS: RESOLVED 2026-03-25**

LinkedIn outreach actions were happening but not being logged consistently across the three signal files (outreach-log.yaml, contacts.yaml, network.yaml).

**Root cause:** Each DM required updating 3 files separately.

**Fix (two tools):**
1. `log_dm.py` — single-command DM logging. `run.py logdm "Contact" --note "..."` updates all three files in one shot. For daily use.
2. `reconcile_outreach.py` — batch reconciliation. Parses pasted LinkedIn DM history (anchors on "Open the options list" line for contact attribution), diffs against logged data, backfills gaps. For periodic catch-up.

Both committed and operational as of 2026-03-25.
