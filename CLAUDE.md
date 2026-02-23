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
# Daily standup (start here every session)
python scripts/standup.py
python scripts/standup.py --hours 5          # Adjust time budget
python scripts/standup.py --section stale    # Single section
python scripts/standup.py --touch <entry-id> # Mark entry as reviewed
python scripts/standup.py --log              # Log session metrics
python scripts/standup.py --triage           # Interactive triage of stagnant entries

# Pipeline overview
python scripts/pipeline_status.py

# Validate pipeline YAML
python scripts/validate.py

# Scoring
python scripts/score.py --target <target-id>  # Score single entry
python scripts/score.py --all --dry-run        # Preview all scores

# Conversion analysis
python scripts/conversion_report.py

# Compose submission from blocks
python scripts/compose.py --target <target-id>
python scripts/compose.py --target <target-id> --snapshot  # Save to submissions/
python scripts/compose.py --target <target-id> --counts    # Word/char counts
python scripts/compose.py --target <target-id> --profile   # Fall back to profile content

# Draft portal-ready submissions from profiles
python scripts/draft.py --target <target-id>               # Generate draft from profile
python scripts/draft.py --target <target-id> --length short # Use short variants
python scripts/draft.py --target <target-id> --populate    # Write portal_fields to YAML
python scripts/draft.py --batch --effort quick             # Draft all quick-effort entries
python scripts/draft.py --batch --status qualified         # Draft all qualified entries

# Batch-advance pipeline entries
python scripts/advance.py --report                         # Show advancement opportunities
python scripts/advance.py --dry-run --to drafting --effort quick  # Preview batch advance
python scripts/advance.py --to drafting --effort quick --yes      # Execute batch advance
python scripts/advance.py --to staged --id <entry-id>            # Advance specific entry

# Submit: generate portal-ready checklists and record submissions
python scripts/submit.py --target <target-id>          # Generate paste-ready checklist
python scripts/submit.py --target <target-id> --open   # Also open portal URL in browser
python scripts/submit.py --check <target-id>           # Pre-submit validation only
python scripts/submit.py --target <target-id> --record # After submitting: update YAML + log

# Preflight: batch submission readiness checker
python scripts/preflight.py                       # Check all staged entries
python scripts/preflight.py --target <target-id>  # Check one entry
python scripts/preflight.py --status qualified    # Check entries with different status

# Submission velocity tracking
python scripts/velocity.py                    # Display velocity stats
python scripts/velocity.py --update-signals   # Write to signals/patterns.md

# Tests
pytest tests/ -v
```

## Key Files

- `scripts/pipeline_lib.py` — Shared utilities (load_entries, load_profile, legacy loading, ID maps, text utils)
- `scripts/draft.py` — Profile→portal bridge: assembles portal-ready drafts from profile content
- `scripts/submit.py` — Portal-ready checklist generator + `--record` for post-submission tracking
- `scripts/preflight.py` — Batch submission readiness validator for staged entries
- `scripts/advance.py` — Batch pipeline progression with validation and dry-run
- `scripts/velocity.py` — Submission velocity metrics and throughput tracking
- `pipeline/_schema.yaml` — Canonical schema for pipeline YAML entries
- `pipeline/submissions/` — Snapshots of composed submissions (via `compose.py --snapshot`)
- `pipeline/drafts/` — Working drafts from `draft.py` (intermediate, not finalized)
- `targets/profiles/` — 44 target profile JSONs with artist statements, bios, work samples
- `blocks/identity/60s.md` — 100-word elevator pitch (storefront layer)
- `blocks/identity/cathedral.md` — Full immersive statement (cathedral layer)
- `strategy/storefront-playbook.md` — Cathedral → storefront translation guide
- `strategy/identity-positions.md` — Four canonical identity framings
- `scripts/legacy-submission/` — 32 pre-pipeline paste-ready submission scripts (integrated via `load_legacy_script`)
- `signals/conversion-log.yaml` — Per-submission outcome data (updated via `submit.py --record`)
- `signals/patterns.md` — Pipeline velocity report (updated via `velocity.py --update-signals`)

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
