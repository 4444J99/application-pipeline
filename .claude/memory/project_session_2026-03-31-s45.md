---
name: Session S45 — Freshness Fix + All-Front Advance (2026-03-31)
description: Critical freshness data integrity fix (99% false positive rate in job sourcing), pipeline triage 99→12 active, 3 applications built, health 7.0→9.0
type: project
---

## The Freshness Fix (Critical)

**Greenhouse `updated_at` was being used instead of `first_published`.** A Coinbase job posted January 23 but edited March 29 passed as "1 day old." Ashby used wrong field name (`publishedDate` instead of `publishedAt`), silently falling back to `updatedAt`.

- 712 of 719 matched jobs were stale but appeared fresh (99% false positive rate)
- The 72-hour freshness filter was operational but meaningless
- All 19 active qualified jobs were verified against live APIs — only 5 were within 7 days
- Airtable Backend: 422 days old. Samsara Platform: 147 days old. Instacart: 210 days old.

**Fix:** `first_published` for Greenhouse, `publishedAt` for Ashby, null-date jobs rejected, `date_source` field added to all entries. 7 new tests, 36/36 passing.

## Pipeline Triage

- 72 over-cap org entries → research_pool (Coinbase 36, Toast 18, Samsara 14, etc.)
- 13 stale entries (verified via live API) → research_pool
- 2 expired grants → closed (Google Creative Fellowship, Headlands Center)
- ZKM Rauschenberg reactivated to drafting (Apr 12 deadline)
- Health: 7.0 → 9.0. Compliance: VIOLATED → COMPLIANT. Active: 99 → 12.

## 3 Applications Built

| Entry | Score | Posted | Portal |
|-------|-------|--------|--------|
| Ramp Fraud & Identity | 8.3 | Mar 27 (4d) | Ashby |
| Deepgram Solutions Engineer | 8.3 | Mar 26 (5d) | Ashby |
| LiveKit Staff Dev Advocate | 8.0 | Mar 28 (3d) | Ashby |

Each has: resume PDF, cover letter PDF + MD, outreach DM (protocol-validated), portal answers, entry YAML. Directories: `applications/2026-03-31/`.

Outreach contacts: Will Koh (Ramp), Shadi Baqleh (Deepgram), David Zhao (LiveKit).

## Bug Fix: followup.py

`_append_outreach_log()` crashed when `outreach-log.yaml` was a flat list (the actual format) vs the expected dict with `entries` key. Fixed to handle both formats.

## Memory

- Created: `feedback_memory_reconciliation.md` (memory is hypothesis, verify before presenting)
- Created: `project_freshness_gate_2026-03-15.md` (was orphan index entry — file never existed)
- Corrected: MEMORY.md deadline claims (Creative Capital closed, NLnet archived, Sovereign Tech phantom)
- Corrected: contact count 210→113
- Synced to chezmoi: feedback_memory_parity.md, feedback_memory_reconciliation.md

## Sovereign Tech Fellowship — Phantom Purged

Memory referenced "Sovereign Tech Fellowship Apr 6 P1" across multiple sessions. No pipeline entry ever existed. No YAML, no draft, no research pool entry. Pure memory-only phantom. Purged.

## IRF Items

**Completed:** IRF-APP-026 partially (Google Creative Fellowship + Headlands = closed/expired; Google AMI still deferred)

**New items to add:**
- IRF-APP-041: Greenhouse `first_published` fix deployed — posting_date data integrity restored. All future source_jobs.py runs use true posting dates. 7 new tests.
- IRF-APP-042: followup.py format compatibility fix — handles flat list and dict YAML formats
- IRF-APP-043: Resume base templates produce 2-page PDFs — all 9 base templates need CSS tightening for 1-page constraint
- IRF-APP-044: update_irf.py still in repo root — should be in scripts/ for consistency
- IRF-APP-045: LinkedIn content engine: post-002-testament-revision (7/8 READY) and post-004 (6/8 READY) are publish-ready. 1 published post in 14 days = PUBLISH loop underinvestment confirmed.
