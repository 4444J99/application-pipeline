# application-pipeline

Career application infrastructure treating job/grant search as a conversion pipeline.

## Philosophy

The existing system was built as a **cathedral**: deep, immersive, comprehensive. The market operates as a **triage system** — 60 seconds to earn attention. This repo redesigns around the storefront insight while preserving cathedral depth as a second layer.

**Core model:** Diagnose variables, A/B test material variants, optimize signals, narrow targets, track conversion rates.

## Structure

```
pipeline/     → YAML per application (structured state machine)
blocks/       → Modular narrative building blocks (tiered depth)
variants/     → A/B tracked material versions
materials/    → Consolidated raw materials (resumes, CVs, samples)
targets/      → Target research and intelligence
signals/      → Conversion analytics
strategy/     → Strategic documents
scripts/      → Python CLI tooling
docs/         → Architecture and workflow documentation
```

## Quick Start

```bash
# View current pipeline state + upcoming deadlines
python scripts/pipeline_status.py

# Validate all pipeline YAML entries
python scripts/validate.py

# Assemble blocks into target-specific submission
python scripts/compose.py --target creative-capital-2027

# Conversion analysis
python scripts/conversion_report.py
```

## Key Concepts

- **Blocks as atoms, submissions as molecules** — compose from tested blocks instead of writing fresh
- **Tiered depth** — blocks have depth tiers appropriate to type (see `blocks/README.md`)
- **Pipeline state machine** — `research → qualified → drafting → staged → submitted → acknowledged → interview → outcome`
- **Variant tracking** — every submission records which block versions were used
- **Benefits cliff awareness** — built into the schema for every target

## Source

Migrated from three locations:
1. `portfolio/intake/` — raw materials
2. `organvm-corpvs-testamentvm/applications/` — per-target narrative docs
3. `organvm-corpvs-testamentvm/docs/applications/` — tracker, covenant-ark, strategy, profiles, cover letters, submission scripts
