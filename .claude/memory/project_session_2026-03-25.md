---
name: Session arc 2026-03-25
description: Massive session — rubric refactor, 118 entries scored, 3 diseases cured (3.5→8.3), repo reorg Phase 1, apply.py built, 5 application packages with API-sourced questions, Maddie roadmap, Scott update, Protocol + standards audit wiring logged as next priorities.
type: project
---

## Session S35 — 2026-03-25

**Commits:** 20+ across application-pipeline and meta-organvm/corpvs
**Diagnostic:** 3.5 → 4.8 → 8.3

### What Was Built
- Three-pillar scoring rubric v3.0 (jobs/grants/consulting separate weights + 7 new dimensions)
- 118 active entries scored (50 at 8.0+)
- `apply.py` — single-command application pipeline (API questions → answers → cover letter → PDF → directory)
- `log_dm.py` — single-command DM logging across 3 signal files
- Reconcile parser rewrite (anchor on "Open the options list")
- IRA ratings via 3-model panel (Opus/Sonnet/Sonnet)
- Maddie Sovereign Systems roadmap (3-domain hub-and-spoke)
- 5 complete application packages with API-sourced Greenhouse questions

### Three Diseases Cured
1. Signal schema drift: 22→0 errors (10 organic action types added)
2. Validation errors: 1,509→0 (4 identity positions + 7 dimensions + 44 status_meta backfills)
3. Unrated dimensions: 4→0 (IRA consensus: arch=7, docs=9, analytics=9, sustainability=7.5)

### Repo Reorganization Phase 1
- Merged blocks/cover-letters → variants/cover-letters
- Merged templates/ → blocks/ and targets/ (templates deleted)
- Archived pipeline/drafts → pipeline/archive/drafts
- Deleted pipeline/deferred (orphan moved to active)
- Consolidated outreach plans to applications/<date>/
- Deleted broken 2026-03-25 packages and regenerated via apply.py

### Key Decisions
- apply.py is the ONLY way to generate application packages going forward
- Portal questions fetched from Greenhouse API, never invented
- Cover letters are WHY (narrative), resumes are WHAT (evidence), portal answers are HOW (direct)
- Zero verbatim metric overlap between cover letter and resume

### Open IRF Items (from this session)
- IRF-APP-034: Wire Protocol into apply.py
- IRF-APP-035: Wire standards.py audit into submission validation
- IRF-APP-036: Repo reorg Phase 2
- IRF-APP-037: 5 more applications tomorrow
