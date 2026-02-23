# CLAUDE.md

## What This Is

Career application pipeline repo — personal infrastructure for managing grant, residency, fellowship, job, and writing applications as a structured conversion pipeline.

**Owner:** @4444J99 (personal/liminal — not an organ repo)
**Parent:** `~/Workspace/4444J99/application-pipeline/`

## Architecture

- `pipeline/` — One YAML file per application tracking full lifecycle (schema in `_schema.yaml`)
- `blocks/` — Modular narrative building blocks with tiered depth (60s → 2min → 5min → cathedral)
- `variants/` — A/B tracked material versions with outcome attribution
- `materials/` — Raw materials (resumes, CVs, work samples, headshots)
- `targets/` — Target research organized by track (grants, residencies, jobs, writing, emergency)
- `signals/` — Conversion analytics (log, patterns, signal map)
- `strategy/` — Strategic documents (funding strategy, qualification assessment, playbook)
- `scripts/` — Python CLI tooling
- `docs/` — Architecture rationale and workflow guide

## Commands

```bash
# Pipeline overview
python scripts/pipeline_status.py

# Validate pipeline YAML
python scripts/validate.py

# Conversion analysis
python scripts/conversion_report.py

# Compose submission from blocks
python scripts/compose.py --target <target-id>
```

## Key Files

- `pipeline/_schema.yaml` — Canonical schema for pipeline YAML entries
- `blocks/identity/60s.md` — 100-word elevator pitch (storefront layer)
- `blocks/identity/cathedral.md` — Full immersive statement (cathedral layer)
- `strategy/storefront-playbook.md` — Cathedral → storefront translation guide
- `strategy/identity-positions.md` — Four canonical identity framings
- `signals/conversion-log.yaml` — Per-submission outcome data

## Conventions

- Pipeline YAML filenames use kebab-case matching the `id` field
- Block filenames are descriptive and match reference paths in pipeline YAML
- Variant filenames follow `{target-type}-v{n}.md` pattern
- All narrative text uses covenant-ark metrics (update there first, propagate here)

## Relationship to Corpus

Canonical identity statements, metrics, and evidence live in `organvm-corpvs-testamentvm/docs/applications/00-covenant-ark.md`. This repo consumes those as source of truth and composes them into submission-ready materials. When metrics change, update covenant-ark first, then propagate to blocks here.

## Dependencies

- Python 3.11+
- PyYAML (`pip install pyyaml`)
- No other external dependencies
