# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Career application pipeline repo — personal infrastructure for managing grant, residency, fellowship, job, and writing applications as a structured conversion pipeline.

**Owner:** @4444J99 (personal/liminal — not an organ repo)
**Parent:** `~/Workspace/4444J99/application-pipeline/`

## Architecture

- `pipeline/` — One YAML file per application, organized into `active/`, `submitted/`, `closed/` subdirectories (schema in `_schema.yaml`)
- `blocks/` — Modular narrative building blocks with tiered depth (60s / 2min / 5min / cathedral)
- `variants/` — A/B tracked material versions with outcome attribution (e.g. `cover-letters/`, `project-descriptions/`)
- `materials/` — Raw materials (resumes, CVs, work samples, headshots)
- `targets/profiles/` — 44 target-specific profile JSONs with pre-written artist statements, bios, work samples
- `signals/` — Conversion analytics (conversion-log.yaml, patterns.md, outreach-log.yaml, standup-log.yaml)
- `strategy/` — Strategic documents (funding strategy, scoring rubric, identity positions, campaign reports)
- `scripts/` — Python CLI tooling (all scripts import from `pipeline_lib.py`)
- `docs/` — Architecture rationale and workflow guide

## Pipeline State Machine

Entries progress through these statuses in order:

```
research → qualified → drafting → staged → submitted → acknowledged → interview → outcome
                  ↘        ↘         ↘
                   → → → deferred → staged / qualified (re-activate)
```

- **Actionable statuses** (what scripts operate on): `research`, `qualified`, `drafting`, `staged`
- **Deferred**: Ready to submit but blocked by external factors (portal paused, cycle not open). Not actionable — excluded from standup/campaign/advance but visible in standup's deferred section. Entries have a `deferral` field with `reason`, optional `resume_date`, and `note`.
- **Terminal outcomes**: `accepted`, `rejected`, `withdrawn`, `expired`
- `advance.py` enforces forward-only progression with validation
- `standup.py` flags entries untouched for >7 days as stale

## Content Composition Model

Three content layers feed into submissions:

1. **Blocks** (`blocks/`) — Reusable narrative modules authored manually. Referenced by path in pipeline YAML `submission.blocks_used` (e.g. `identity/2min`, `projects/organvm-system`). See `blocks/README.md` for the tier system.
2. **Profiles** (`targets/profiles/*.json`) — Target-specific pre-written content: artist statements at 3 lengths, bios, work samples.
3. **Legacy scripts** (`scripts/legacy-submission/`) — 32 pre-pipeline paste-ready submissions, parsed via `pipeline_lib.load_legacy_script()`.

**Fallback pattern**: `draft.py` and `compose.py --profile` check blocks first, then fall back to profile content, then legacy scripts. Entries don't need `blocks_used` fully populated.

## Script Dependency Graph

Scripts are independent CLIs but some import functions from each other:

- **`pipeline_lib.py`** — Shared foundation: `load_entries()`, `load_profile()`, `load_block()`, `load_variant()`, `load_legacy_script()`, path constants, ID maps, text utils. Every script imports from here.
- **`campaign.py`** imports from `enrich.py` — the `--execute` mode runs enrichment + advance + preflight as a pipeline.
- **`alchemize.py`** imports from `greenhouse_submit.py` — the Greenhouse-specific end-to-end orchestrator (research → identity mapping → synthesis prompt → integration → submission).
- **`followup.py`** — Follow-up tracker: generates daily outreach lists, logs follow-up actions to entries and outreach-log.yaml.
- **`funnel_report.py`** — Conversion funnel analytics: stage distribution, conversion rates by variable (channel, portal, position, track), weekly velocity, target vs actual comparison.
- All other scripts are standalone CLIs that read/write pipeline YAML files.

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

# Scoring (8-dimension weighted rubric, see strategy/scoring-rubric.md)
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

# Batch enrichment: wire materials, blocks, variants, portal_fields
python scripts/enrich.py --report                    # Show enrichment gaps
python scripts/enrich.py --all --dry-run             # Preview all enrichments
python scripts/enrich.py --all --yes                 # Execute all enrichments
python scripts/enrich.py --materials --yes            # Wire resume only
python scripts/enrich.py --blocks --dry-run           # Preview job block wiring
python scripts/enrich.py --blocks --yes               # Wire identity-matched blocks to jobs
python scripts/enrich.py --variants --yes             # Wire cover letters only
python scripts/enrich.py --portal --yes               # Populate portal_fields only
python scripts/enrich.py --variants --grant-template  # Also wire grant template to grants
python scripts/enrich.py --all --effort quick --yes   # Quick entries only

# Campaign orchestrator: deadline-aware pipeline execution
python scripts/campaign.py                           # This week's campaign (14-day window)
python scripts/campaign.py --days 7                  # Next 7 days only
python scripts/campaign.py --days 30                 # Full month view
python scripts/campaign.py --days 90                 # Full quarter view
python scripts/campaign.py --days 90 --save          # Save markdown report to strategy/
python scripts/campaign.py --execute --dry-run       # Preview pipeline execution
python scripts/campaign.py --execute --yes           # Execute for all urgent entries
python scripts/campaign.py --execute --id <entry-id> --yes  # Single entry

# Greenhouse-specific orchestrator (4-phase: intake → research → map → synthesize)
python scripts/alchemize.py --target <target-id>                    # Full pipeline → prompt.md
python scripts/alchemize.py --target <target-id> --phase research   # Stop after research
python scripts/alchemize.py --target <target-id> --integrate        # Integrate output.md back
python scripts/alchemize.py --target <target-id> --submit           # Submit via greenhouse_submit.py

# Greenhouse API submission
python scripts/greenhouse_submit.py --target <target-id>          # Dry-run preview
python scripts/greenhouse_submit.py --target <target-id> --submit # POST to Greenhouse
python scripts/greenhouse_submit.py --init-answers --target <target-id>  # Generate answer template
python scripts/greenhouse_submit.py --check-answers --batch              # Validate all answers

# Follow-up tracker and daily outreach list
python scripts/followup.py                     # Show today's follow-up actions
python scripts/followup.py --all               # All entries with follow-up status
python scripts/followup.py --schedule           # Upcoming follow-up schedule (21 days)
python scripts/followup.py --overdue            # Overdue follow-ups only
python scripts/followup.py --log <entry-id> --channel linkedin --contact "Name" --note "DM sent"

# Conversion funnel analytics
python scripts/funnel_report.py                # Full funnel summary
python scripts/funnel_report.py --by channel   # Breakdown by channel
python scripts/funnel_report.py --by position  # Breakdown by identity position
python scripts/funnel_report.py --by portal    # Breakdown by portal type
python scripts/funnel_report.py --by track     # Breakdown by track
python scripts/funnel_report.py --weekly       # Weekly submission velocity
python scripts/funnel_report.py --targets      # Conversion targets vs actual

# Metric consistency check (compares blocks against canonical system-metrics.json)
python scripts/check_metrics.py

# Submission velocity tracking
python scripts/velocity.py                    # Display velocity stats
python scripts/velocity.py --update-signals   # Write to signals/patterns.md

# Tests
pytest tests/ -v
pytest tests/test_compose.py -v              # Single test file
pytest tests/test_compose.py::test_name -v   # Single test
```

## Testing Patterns

- Tests live in `tests/` and use pytest
- Scripts use `sys.path.insert(0, ...)` to add `scripts/` to the import path (no package installation needed)
- Tests operate on real pipeline data — they validate against actual YAML files, block directories, and profiles
- No mocking framework; tests verify constants, data integrity, and script output against live data

## Key ID Mapping

Pipeline entry IDs don't always match profile filenames or legacy script names. `pipeline_lib.py` maintains two maps:

- `PROFILE_ID_MAP` — entry ID → profile JSON filename (e.g. `"creative-capital-2027"` → `"creative-capital"`)
- `LEGACY_ID_MAP` — legacy script filename → entry ID (e.g. `"cc-creative-capital"` → `"creative-capital-2027"`)

When adding new entries, check if these maps need updating.

## Greenhouse Integration

For entries with `target.portal: greenhouse`:

- `greenhouse_submit.py` uses the public Greenhouse Job Board API for form submission
- Personal info (name, email, phone) loaded from `scripts/.submit-config.yaml`
- Custom question answers stored in `scripts/.greenhouse-answers/<entry-id>.yaml`
- `alchemize.py` orchestrates the full flow: scrapes job posting, maps identity blocks to requirements, generates a synthesis prompt, then integrates AI-generated output back into pipeline YAML

## Conventions

- Pipeline YAML filenames use kebab-case matching the `id` field
- Block filenames are descriptive and match reference paths in pipeline YAML
- Variant filenames follow `{target-type}-v{n}.md` or `{target-specific-name}.md` pattern
- All narrative text uses covenant-ark metrics (update there first, propagate here)
- `daily_batch.py` is deprecated — use `standup.py --section plan` instead

## Relationship to Corpus

Canonical identity statements, metrics, and evidence live in `organvm-corpvs-testamentvm/docs/applications/00-covenant-ark.md`. This repo consumes those as source of truth and composes them into submission-ready materials. When metrics change, update covenant-ark first, then propagate to blocks here. Run `python scripts/check_metrics.py` to verify consistency.

## Dependencies

- Python 3.11+ (venv at `.venv/` uses Python 3.14)
- PyYAML (`pip install pyyaml`)
- No other external dependencies — `alchemize.py` and `greenhouse_submit.py` use stdlib `urllib` for HTTP
