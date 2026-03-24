---
name: Colossal Triage Executed 2026-03-13
description: Major pipeline triage reduced 59 actionable to 10, health 5.2→7.2, scoring threshold 9.0 unattainable
type: project
---

Pipeline underwent major triage on 2026-03-13.

**Key actions:**
- 3 expired entries closed (Prix Ars x2, S+T+ARTS)
- 54 staged entries demoted to qualified (all below 9.0)
- 32 entries deferred for org-cap violations
- 19 low-scoring entries returned to research_pool
- 9 mid-range entries deferred
- 2 deadline entries deferred (PEN America 6.5, Google Creative Fellowship 5.1)
- Net: 59 actionable → 10 actionable (COMPLIANT)
- Health: 5.2/10 → 7.2/10
- Compliance: 0/2 → 2/2

**Critical finding: 9.0 threshold unattainable**
- Scoring model recalibrated ~0.9 points lower than original scores
- 0 of 2,037 entries (including 15,348 fresh postings) reach 9.0
- Top entries: Anthropic Agent SDK (8.5), Cursor DevEx (8.4), then cluster at 8.3
- `strategy/scoring-rubric.yaml` threshold needs adjustment — suggested range: 8.0-8.3

**Why:** Pipeline was over-built and under-actuated. 15-day submission drought, 0% acceptance rate from 25 submissions, 0 outreach actions logged.

**How to apply:** Focus on submitting the top 2 (Anthropic, Cursor) and doing follow-up outreach on all 11 pending entries. Run `python scripts/run.py recalibrate` to address threshold issue.
