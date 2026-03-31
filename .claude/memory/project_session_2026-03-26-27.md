---
name: Session arc 2026-03-26/27
description: Materials Protocol formalized (12 articles), repo reorg Phase 2, Gemini collaboration tested (net negative), batch 1 submitted, batch 2 achieves 12/12 compliance, 10 applications total.
type: project
---

## Sessions S36-S37 — 2026-03-26 through 2026-03-27

**Commits:** 30+ across application-pipeline and meta-organvm/corpvs

### Materials Protocol (the big build)
- Third formal system in ORGANVM rhetorical triad (Testament → Outreach Protocol → Materials Protocol)
- 12 articles: Page-Fill, Structural Integrity, Identity Sovereignty, Metric Canonicality, Content Complementarity, Visual Identity Parity, Storefront Gate, Project Rotation, Triple Layer, Voice Compliance, Inhabitant Gate, Word Count
- Imports from: Testament (Art. I-III, XII, XIII), Outreach Protocol (P-I, P-V), Voice Constitution (19 rules), Attention Mechanics (ATT-A0-A5), Praxis Perpetua (Constitutional Laws), Storefront Playbook
- Three-persona hardening: 9 revisions integrated
- `materials_validator.py` — automated enforcement, 12 PASS/FAIL checks
- All 5 batch-2 packages achieved 12/12 compliance
- Spec: `docs/superpowers/specs/2026-03-27-materials-protocol-formalization-design.md`

### Repo Reorganization Phase 2
- Root reduced from 35 → 14 items (Minimal Root philosophy)
- `variants/` → `materials/variants/`, `targets/` → `materials/targets/`, `config/` → `.config/`, `launchd/` → `.config/launchd/`, `ratings/` → `signals/ratings/`
- Pipeline path constants updated in `pipeline_lib.py`, `diagnose.py`, `generate_ratings.py`
- 5 backup tarballs removed from git tracking
- `blocks/framings/independent-engineer.md` → `software-engineer-at-organvm.md` (275 YAML references updated)

### Batch 1 (submitted 2026-03-26)
- dbt Labs (8.5), Anduril (8.4), Grafana Labs (8.3), Twilio (8.3), Databricks (7.4)
- All remote. Fresh contacts researched for each. Outreach logged.

### Batch 2 (ready 2026-03-27, 12/12 Materials Protocol)
- Temporal AI SDK (8.6), Anthropic DevProd (8.4), Cursor Reliability (8.4), Datadog Curriculum (8.4), Wikimedia FundTech (8.5)
- Cover letters: 573-626 words, zero resume overlap, triple layer enforced
- Resumes: domain-relevant projects from 89-project registry, 4+ entries, vertical layout
- Portal answers: API-sourced from Greenhouse

### Gemini CLI Collaboration (tested and evaluated)
- Used for logging batch 1 submissions and generating batch 2 materials
- Correctly logged outreach, updated entry statuses, researched contacts
- BROKE: cover letter formatting (metadata headers), inflated metrics (127 repos instead of 113), columnar resume layouts, 51 uncommitted files, didn't use venv
- ROOT CAUSE: no access to Claude's persistent memory (feedback rules, Protocol, identity reframe)
- VERDICT: net negative for this repo. Use for isolated stateless tasks only. Never for materials production.

### New Connections (2026-03-26)
- Paul Pham (Senior Quality Engineer, dbt Labs) — accepted, profile viewed, DM pending
- Alexander Desroches (Field Engineering Leader, Databricks FinServ) — accepted, DM pending

### GitHub Followers
- 27 total. 4 AdenHQ cluster (Adel Burieva, Bryan, Timothy Zhang, RichardTang). 23 organic.

### Key Fixes
- Clearance gate wired into apply.py (hard block vs soft eligibility)
- Cover letter template matching resume visual identity (saved as base template)
- `tailor_resume.py` prompt: HARD RULES section + domain-relevant project menu from registry
- Validation: 37 errors → 0 (framing rename propagation + status_meta backfills + duplicate removal)
