---
name: Data hygiene — dynamic vs observation
description: Never delete system observations. Distinguish recomputable cache from learning artifacts. Clean aggressively but preserve the diary.
type: feedback
---

Two categories of pipeline data — treat them differently:

**Dynamic (compute on demand, never store in git):**
- Scores, research_pool entries, PDFs, TF-IDF cache, telemetry
- These are gitignored and regenerated each session

**Observation (accumulates, never regenerated, never deleted):**
- Conversion log, contacts, hypotheses, outreach log
- Daily health snapshots, weekly briefs, diagnostic history
- Engagement findings, agent action logs, follow-up reports
- These live in signals/ (active) and signals/archive/ (historical)

**Why:** The system's observations about itself over time can't be regenerated because the conditions that produced them no longer exist. A daily health snapshot from March 13 records what was true on March 13. Deleting it destroys information.

**How to apply:** Before deleting any data file, ask: "Can I regenerate this by running a command?" If yes → delete/gitignore. If no → it's an observation, archive it.
