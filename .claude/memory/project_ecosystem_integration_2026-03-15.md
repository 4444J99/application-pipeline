---
name: Ecosystem Integration State 2026-03-15
description: Meta-organ snapshot, 9 identity positions, auto-classify, engagement findings, stakeholder portal live
type: project
---

## Ecosystem State (as of 2026-03-15)

### system-snapshot.json
- Location: `~/Workspace/meta-organvm/organvm-corpvs-testamentvm/system-snapshot.json`
- Contents: 8 organs with per-organ repo counts, system density (0.578), 1,833 entities, 28 edges, AMMOI text, omega scorecard, promotion pipeline counts, 31 system variables
- Updated: daily by CI + every organvm refresh

### config/metrics.yaml
- Auto-generated — NEVER edit manually
- Refresh: `python scripts/refresh_from_ecosystem.py` or `make refresh-ecosystem`
- Includes `organism:` section with density, entities, edges, AMMOI

### Identity Positions Expanded: 5 → 9
New positions: documentation-engineer, governance-architect, platform-orchestrator, founder-operator

Each has full integration:
- `strategy/identity-positions.md` entry
- `materials/resumes/base/{position}-resume.html`
- `blocks/framings/{position}.md`
- `generate_job_profile.py` EVIDENCE_BY_POSITION
- `interview_prep.py` STAR questions
- `material_builder.py` BLOCK_SLOTS
- `discover_jobs.py` VALID_POSITIONS

### Auto-Classification
`source_jobs.py` now calls `classify_position.py` — entries get best-fit position from title/description regex, not defaulting to independent-engineer.

### Engagement Findings (first intelligence run)
- **Strongest read predictors**: deadline_feasibility (+2.55), network_proximity (+1.89)
- **Negative correlation**: financial_alignment (-2.29), track_record_fit (-1.94)
- **5 effective job-track blocks** (82% read rate): framings/independent-engineer, methodology/ai-conductor, pitches/credentials-creative-tech, evidence/differentiators, evidence/work-samples
- **6 "invisible" blocks** are ALL grant-track (3-6 month response cycles = silence by design, not toxic). Use `--track job` to filter.
- **181 GitHub interactors** identified with proximity scores

### Stakeholder Portal
- LIVE at https://stakeholder-portal-ten.vercel.app/
- Auto-deploys on push to main
- Neon database: pulse_snapshots + metric_observations tables
- Pulse daemon writes every 15 min
- /api/metrics endpoint, dashboard pulse, organ detail metrics

### Known Data Gap
`total_words_numeric` not auto-computed — word-counting needs workspace access. Zero in CI. Manual section of system-metrics.json carries the value.

### Makefile Targets
- `make refresh-all` — ecosystem + prestige + positions
- `make refresh-intelligence` — full cycle including engagement + blocks + proximity

**How to apply:** Run `make refresh-all` before daily pipeline operations to ensure metrics, positions, and prestige are current. The corpus fingerprint will automatically pick up new blocks from the expanded positions.
