# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Career application pipeline repo — personal infrastructure for managing grant, residency, fellowship, job, and writing applications as a structured conversion pipeline. Implements a **"Cathedral → Storefront"** philosophy: preserving deep, immersive systemic work (Cathedral) while providing high-signal, scannable entry points (Storefront) for reviewers.

**Owner:** @4444J99 (personal/liminal — not an organ repo)
**Parent:** `~/Workspace/4444J99/application-pipeline/`

## Pipeline Philosophy: Precision Over Volume

**Effective 2026-03-04.** The pipeline optimizes for finding perfect-fit roles and building relationships, not throughput.

- **Max 1-2 applications per week**, each deeply researched
- **Minimum score 9.0** to apply; network_proximity >= 5 preferred
- **9 scoring dimensions** including `network_proximity` (referral = 8x hire rate)
- **Max 10 actionable entries** (qualified+drafting+staged) at any time; max 1 per organization. Note: the `active/` directory may contain more files including recently-promoted research entries awaiting triage.
- **Daily split:** 2hr research, 2hr relationships, 1hr application work
- **Stale thresholds relaxed:** 14 days (was 7), stagnant 30 days (was 14). _Source: loaded dynamically from `strategy/market-intelligence-2026.json`; these are the fallback defaults when JSON is absent._
- **No volume pressure** in standup messaging; no "ship something this week"
- **Minimum outreach before submission:** At least 1 outreach action (LinkedIn connect, email, referral ask) required before advancing to submitted. Use `followup.py --log` to record.
- **Rationale:** 60 cold applications in 4 days → 0 interviews. Precision targeting + warm paths is the only viable strategy. Note: referral multiplier (8x) and cover letter callback (+53%) are *market benchmarks* (not yet validated by this pipeline's own data).

## Architecture

- `pipeline/` — One YAML file per application, organized into `active/`, `submitted/`, `closed/`, and `research_pool/` subdirectories (schema in `_schema.yaml`)
  - `research_pool/` holds auto-sourced research-status entries, separated from actionable entries to keep `active/` lean (~30 files vs ~1000)
- `blocks/` — Modular narrative building blocks with tiered depth (60s / 2min / 5min / cathedral). Each block has frontmatter: `title`, `category`, `tags`, `identity_positions`, `tracks`, `tier`. Regenerate the tag index with `python scripts/build_block_index.py`.
- `variants/` — A/B tracked material versions with outcome attribution (e.g. `cover-letters/`, `project-descriptions/`)
- `materials/` — Raw materials (resumes, CVs, work samples, headshots). Resumes organized into `base/` (5 identity-position templates) and `batch-NN/` (target-tailored versions, current: `batch-03/`).
- `targets/profiles/` — 44 target-specific profile JSONs with pre-written artist statements, bios, work samples
- `signals/` — Conversion analytics (conversion-log.yaml, patterns.md, outreach-log.yaml, standup-log.yaml)
- `strategy/` — Strategic documents (funding strategy, scoring rubric, identity positions, campaign reports)
- `scripts/` — Python CLI tooling (all scripts import from `pipeline_lib.py`). Includes ATS-specific submitters for Greenhouse, Lever, and Ashby portals.
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
- `advance.py` enforces forward-only progression with validation; requires at least 1 outreach action before advancing to `submitted` (bypass with `--force`)
- `standup.py` flags entries untouched for >14 days as stale (threshold loaded from market-intelligence JSON)

## Identity Positions

Every application must align with one of five canonical positions defined in `strategy/identity-positions.md`. These determine framing, block selection, and resume variant:

1. **Independent Engineer** — AI lab roles (Anthropic, OpenAI, Stripe). Focus: large-scale infra, testing discipline, "AI-conductor" methodology.
2. **Systems Artist** — Art grants/residencies. Focus: governance as artwork, systemic scale.
3. **Educator** — Academic roles/fellowships. Focus: teaching complex systems at scale.
4. **Creative Technologist** — Tech grants/consulting. Focus: AI orchestration, production-grade creative instruments.
5. **Community Practitioner** — Identity-specific funding. Focus: precarity-informed systemic practice.

## Content Composition Model

Three content layers feed into submissions:

1. **Blocks** (`blocks/`) — Reusable narrative modules authored manually. Referenced by path in pipeline YAML `submission.blocks_used` (e.g. `identity/2min`, `projects/organvm-system`). See `blocks/README.md` for the tier system.
2. **Profiles** (`targets/profiles/*.json`) — Target-specific pre-written content: artist statements at 3 lengths, bios, work samples.
3. **Legacy scripts** (`scripts/legacy-submission/`) — 32 pre-pipeline paste-ready submissions, parsed via `pipeline_lib.load_legacy_script()`.

**Fallback pattern**: `draft.py` and `compose.py --profile` check blocks first, then fall back to profile content, then legacy scripts. Entries don't need `blocks_used` fully populated.

**Storefront content rules**: Lead with numbers ("103 repositories," "2,349 tests"). One sentence, one claim — maintain scannability for 60-second reviews. Preemptively frame gaps (e.g., lack of awards) as deliberate trajectory.

## Script Dependency Graph

Scripts are independent CLIs but some import functions from each other:

- **`pipeline_lib.py`** — Shared foundation: `load_entries()`, `load_profile()`, `load_block()`, `load_variant()`, `load_legacy_script()`, path constants, ID maps, text utils. Every script imports from here.
- **`campaign.py`** imports from `enrich.py` — the `--execute` mode runs enrichment + advance + preflight as a pipeline.
- **`alchemize.py`** imports from `greenhouse_submit.py` — the Greenhouse-specific end-to-end orchestrator (research → identity mapping → synthesis prompt → integration → submission).
- **`followup.py`** — Follow-up tracker: generates daily outreach lists, logs follow-up actions to entries and outreach-log.yaml. `--init` populates follow_up fields on submitted entries.
- **`funnel_report.py`** — Conversion funnel analytics: stage distribution, conversion rates by variable (channel, portal, position, track), weekly velocity, target vs actual comparison, variant composition comparison.
- **`hygiene.py`** imports from `source_jobs.py` — URL liveness, ATS posting verification, auto-expire, track-specific gates. Also: `--prune-research` archives stale research entries, `--rotate-signals` archives old signal-actions entries.
- **`check_outcomes.py`** — Outcome recording and stale response alerts. Updates conversion-log and moves terminal entries to closed/.
- **`research_contacts.py`** — Recruiter identification and follow-up protocol date generation.
- **`submit.py`** imports from `check_metrics.py` — `--check` mode now validates block metrics freshness.
- **`text_match.py`** — TF-IDF text matching engine; provides objective scoring signals by comparing job posting keywords against block/profile content. Used by `score.py` for evidence_match dimension.
- **`feedback_capture.py`** — standalone; writes hypothesis entries to `signals/hypotheses.yaml`. Use to record predicted outcome reasons before results arrive. Run `run.py hypotheses` to list, `run.py analysis` to see patterns, `run.py hypothesis <id>` to capture for a specific entry.
- **`check_email.py`** — standalone; scans for submission confirmations and responses. Requires `.email-config.yaml` with IMAP credentials (not committed). Run `run.py email` daily.
- **`triage.py`** — Triage automation: demotes sub-threshold staged entries, resolves org-cap violations. `--execute --yes` to apply, `--json` for machine output.
- **`snapshot.py`** — Daily pipeline snapshots with trend analysis (7d/30d/90d deltas, linear regression slopes, inflection detection). Saves to `signals/daily-snapshots/`.
- **`notify.py`** — Notification dispatcher: routes pipeline events (weekly_brief, agent_action, deadline_alert, etc.) to webhooks and email per `strategy/notifications.yaml`.
- **`org_intelligence.py`** — Organization intelligence: aggregates entries, contacts, outcomes, network density per org. Composite opportunity scoring.
- **`skills_gap.py`** — Skills gap analysis: extracts required skills from entries, computes coverage against block content.
- **`block_outcomes.py`** — Block-outcome correlation: classifies blocks as golden (>50% accept), toxic (>75% reject), or neutral.
- **`calendar_export.py`** — iCal export: generates VCALENDAR/VEVENT/VALARM from pipeline deadlines. Pure stdlib.
- **`interview_prep.py`** imports from `org_intelligence.py`, `skills_gap.py` — Interview prep document generator combining org intelligence, skills gaps, STAR questions, and block talking points.
- **`recalibrate.py`** imports from `score.py` — Quarterly rubric recalibration: proposes scoring weight adjustments based on outcome patterns. Requires `--apply --yes` to modify `scoring-rubric.yaml`.
- **`diagnose.py`** imports from `launchd_manager.py` — uses `get_agent_status()` for operational maturity measurement. Loads rubric from `strategy/system-grading-rubric.yaml`.
- **`diagnose_ira.py`** — standalone; computes ICC, kappa, and consensus from rating JSON files in `ratings/`. Includes `partition_dimensions()` for separating objective ground truth from subjective rated dimensions.
- **`generate_ratings.py`** imports from `diagnose.py` — uses COLLECTORS, PROMPT_GENERATORS, OBJECTIVE_DIMENSIONS, SUBJECTIVE_DIMENSIONS for multi-model IRA rating. Calls Anthropic and Google APIs.
- All other scripts are standalone CLIs that read/write pipeline YAML files.

## Module Architecture

`pipeline_lib.py` was decomposed into focused modules to keep the main file manageable:

| Module | Extracted From | Purpose |
|--------|---------------|---------|
| `pipeline_entry_state.py` | `pipeline_lib.py` | Entry state machine: status transitions, validation, actionable checks |
| `pipeline_freshness.py` | `pipeline_lib.py` | Staleness thresholds, age categorization, freshness scoring |
| `pipeline_market.py` | `pipeline_lib.py` | Market intelligence loader, portal friction scores, strategic base values, HTTP retry |
| `standup_constants.py` | `standup.py` | Standup section names, colors, budget defaults |
| `standup_work_sections.py` | `standup.py` | Work-focused standup sections: stale, plan, outreach, practices, replenish, deferred, precision compliance |
| `standup_relationship_sections.py` | `standup.py` | Relationship standup sections: follow-up dashboard, CRM summary |

Scripts import from these modules directly (e.g. `from pipeline_market import build_market_intelligence_loader`). The main `pipeline_lib.py` re-exports commonly used functions for backward compatibility.

## Resume Workflow

**NEVER use base resumes (`materials/resumes/base/`) for final submissions.** Every target must have a tailored resume in the current batch directory (`materials/resumes/batch-03/`).

```bash
# Tailor a resume for a target (generates HTML in batch-03/<entry-id>/)
python scripts/tailor_resume.py --target <entry-id>

# Wire the tailored resume into the pipeline YAML
python scripts/tailor_resume.py --target <entry-id> --wire

# Build PDFs from HTML resumes (headless Chrome)
python scripts/build_resumes.py                          # All unbuilt resumes
python scripts/build_resumes.py --target <entry-id>      # Single target
```

All resumes must be exactly 1 page.

## Completion Summaries

When finishing an application batch or role, always provide:
1. The original job posting / application URL
2. Direct links to the tailored resume (PDF), cover letter, and answers files

## Commands

Most scripts are accessible via `python scripts/run.py <command>` (see Quick Commands below). For full flag documentation, run any script with `--help`.

```bash
# Daily workflow
python scripts/standup.py                              # Daily dashboard (start here)
python scripts/standup.py --section followup           # Follow-up dashboard only
python scripts/standup.py --triage                     # Interactive triage of stagnant entries
python scripts/campaign.py                             # Deadline-aware campaign (14-day window)
python scripts/campaign.py --execute --yes             # Execute pipeline for urgent entries
python scripts/followup.py                             # Today's follow-up actions
python scripts/check_outcomes.py                       # Entries awaiting response

# Pipeline operations
python scripts/score.py --target <id>                  # Score single entry (9-dimension rubric)
python scripts/score.py --auto-qualify --yes            # Promote research_pool entries ≥ 9.0
python scripts/advance.py --report                     # Show advancement opportunities
python scripts/advance.py --to staged --id <id>        # Advance specific entry
python scripts/enrich.py --all --yes                   # Wire materials, blocks, variants
python scripts/submit.py --target <id>                 # Generate paste-ready checklist
python scripts/submit.py --target <id> --record        # Record submission + update YAML

# Composition & drafting
python scripts/compose.py --target <id>                # Compose from blocks
python scripts/draft.py --target <id>                  # Draft from profile
python scripts/alchemize.py --target <id>              # Greenhouse end-to-end orchestrator

# ATS submissions
python scripts/greenhouse_submit.py --target <id>      # Greenhouse (dry-run)
python scripts/lever_submit.py --target <id>           # Lever portal
python scripts/ashby_submit.py --target <id>           # Ashby portal

# Analytics & reporting
python scripts/funnel_report.py                        # Conversion funnel
python scripts/quarterly_report.py                     # Quarterly analytics
python scripts/rejection_learner.py                    # Rejection dimension analysis
python scripts/portfolio_analysis.py                   # Block/position/channel analysis
python scripts/velocity_report.py                      # Monthly velocity
python scripts/snapshot.py --report                    # Pipeline snapshot with counts and trends
python scripts/snapshot.py --save                      # Save daily snapshot to signals/daily-snapshots/
python scripts/org_intelligence.py --all               # Org intelligence rankings
python scripts/skills_gap.py --all                     # Skills gap analysis across entries
python scripts/block_outcomes.py                       # Block-outcome correlation (golden/toxic)

# Triage & notifications
python scripts/triage.py                               # Triage gate report (dry-run)
python scripts/triage.py --execute --yes               # Execute triage demotions/deferrals
python scripts/notify.py --config                      # Show notification config
python scripts/notify.py --test-webhook                # Test webhook dispatch

# Calendar & interview prep
python scripts/calendar_export.py                      # Print iCal to stdout
python scripts/calendar_export.py --output ~/Calendar/pipeline.ics  # Export .ics file
python scripts/calendar_export.py --follow-ups         # Include follow-up dates
python scripts/interview_prep.py --target <id>         # Generate interview prep document
python scripts/interview_prep.py --auto                # Prep all interview-status entries

# Relationship management
python scripts/crm.py                                  # CRM dashboard
python scripts/crm.py --add "Name" --org "Company"     # Add contact
python scripts/followup.py --log <id> --channel linkedin --contact "Name" --note "DM sent"
python scripts/research_contacts.py --target <id>      # Recruiter identification

# Validation & hygiene
python scripts/validate.py --check-id-maps --check-rubric  # Full CI-parity validation
python scripts/validate_signals.py --strict            # Signal YAML validation (CI gate)
python scripts/hygiene.py                              # URL liveness, staleness, gates
python scripts/check_metrics.py                        # Block metric consistency
python scripts/freshness_monitor.py                    # Entry age categorization

# Diagnostics & grade norming
python scripts/diagnose.py                             # System diagnostic scorecard
python scripts/diagnose.py --json --rater-id opus > ratings/opus.json  # JSON for IRA
python scripts/diagnose.py --subjective-only           # Generate prompts for AI raters
python scripts/diagnose.py --objective-only            # Only automated measurements
python scripts/diagnose_ira.py ratings/*.json          # IRA report from rating files
python scripts/diagnose_ira.py ratings/*.json --consensus  # With consensus scores
python scripts/generate_ratings.py                        # Full multi-model rating session
python scripts/generate_ratings.py --rater architect-opus  # Single rater only
python scripts/generate_ratings.py --dry-run               # Show prompts without API calls
python scripts/generate_ratings.py --compute-ira           # Run IRA after rating

# Infrastructure
python scripts/agent.py --plan                         # Autonomous agent preview
python scripts/monitor_pipeline.py --strict            # Backup + signal freshness
python scripts/backup_pipeline.py create               # Create dated tar.gz
python scripts/launchd_manager.py --status             # LaunchAgent status
ruff check scripts/ tests/                             # Lint (run via .venv)

# Tests
pytest tests/ -v
pytest tests/test_compose.py -v                        # Single test file
pytest tests/test_compose.py::test_name -v             # Single test
```

## Quick Commands

Single-word command protocol via `python scripts/run.py <command>`. 59 standalone + 20 parameterized = 79 commands (consolidated from 112).

| Command | What It Does |
|---------|-------------|
| `standup` | Daily dashboard: stale entries, deadlines, priorities, follow-ups |
| `campaign` | Deadline-aware campaign view with urgency tiers |
| `followup` | Today's follow-up actions and overdue items |
| `outcomes` | Entries awaiting response + stale submissions |
| `morning` | Morning digest: health + stale + followups + campaign |
| `deferred` | Deferred entries: overdue and upcoming re-activations |
| `scoreall` | Preview all scores |
| `qualify` | Preview auto-qualification |
| `enrichall` | Preview all enrichments |
| `preflight` | Batch submission readiness |
| `triagegate` | Triage gate: demote sub-threshold staged, resolve org-cap |
| `funnel` | Conversion funnel analytics |
| `conversion` | Conversion rate report by track/position/score |
| `quarterly` | Quarterly analytics report |
| `rejections` | Rejection learning: dimension weakness, timing, block correlation |
| `blockoutcomes` | Block-outcome correlation: golden/toxic blocks |
| `blockroi` | Block acceptance rate ROI analysis |
| `portfolio` | Portfolio analysis: blocks, positions, channels, variants |
| `snapshot` | Pipeline snapshot: counts, scores, trends |
| `textmatch` | TF-IDF text match analysis |
| `orgs` | Org intelligence: aggregated org rankings |
| `skillsgap` | Skills gap analysis across entries |
| `crm` | Relationship CRM: contacts, interactions, coverage gaps |
| `cultivate` | Relationship cultivation candidates |
| `warmintro` | Warm intro audit: referral paths and org density |
| `validate` | Pipeline YAML schema validation |
| `metrics` | Metric consistency check |
| `hygiene` | Entry data quality: URLs, staleness, gates, signal rotation |
| `signals` | Validate signal YAML schema integrity |
| `verifyall` | Run full verification gates (matrix + lint + validate + tests) |
| `monitor` | Monitor backup + conversion-log freshness |
| `freshness` | Entry freshness report (posting age analysis) |
| `learner` | Outcome learning engine: calibration report |
| `hypotheses` | List all recorded outcome hypotheses |
| `hypotheses-v` | Validate outcome hypotheses vs actuals |
| `recalibrate` | Quarterly rubric recalibration proposal |
| `market` | Market conditions, benchmarks, and grant calendar |
| `funding` | Non-dilutive funding opportunities by viability |
| `sourcejobs` | Preview new job postings from ATS APIs |
| `topjobs` | Daily glove-fit fetch: top roles ≥ 9.0 score |
| `discover` | Skill-based job discovery across free APIs |
| `calendar` | Export pipeline deadlines to iCal |
| `interviewprep` | Interview prep for all interview-status entries |
| `agent` | Preview autonomous agent planned actions |
| `automation` | Launchd automation status |
| `backup` | List pipeline backups |
| `notify` | Notification dispatcher config check |
| `weeklybrief` | Weekly executive brief |
| `diagnose` | System diagnostic scorecard (objective dimensions) |
| `ira` | Inter-rater agreement report (needs ratings/*.json) |
| `rateall` | Multi-model IRA rating session with diverse AI panel |

**With target ID:** `score <id>`, `enrich <id>`, `advance <id>`, `compose <id>`, `draft <id>`, `submit <id>`, `check <id>`, `record <id>`, `gate <id>`, `contacts <id>`, `hypothesis <id>`, `alchemize <id>`, `answers <id>`, `tailor <id>`, `review <id>`, `cultivate <id>`, `textmatch <id>`, `skillsgap <id>`, `orgdetail <org>`, `interviewprep <id>`

**Session sequences:**
- Morning: `morning` (or: `standup` → `followup` → `outcomes` → `campaign`)
- Submit: `campaign` → `check <id>` → `submit <id>` → `record <id>`
- Research: `hygiene` → `scoreall` → `qualify` → `enrichall`
- Analyze: `funnel` → `conversion` → `quarterly` → `blockroi` → `rejections`
- Strategy: `funding` → `market` → `recalibrate`
- Agent: `agent` → `deferred` → `signals` → `hypotheses-v`
- Health: `monitor` → `freshness` → `verifyall` → `backup`
- Triage: `triagegate` → `snapshot` → `orgs` → `blockoutcomes`
- Interview: `interviewprep <id>` → `skillsgap <id>` → `orgdetail <org>`
- Diagnostic: `diagnose` → `rateall` → `ira`

## Configuration Files

| File | Purpose |
|------|---------|
| `strategy/scoring-rubric.yaml` | Scoring dimensions, weights, thresholds (loaded by `score.py`) |
| `strategy/agent-rules.yaml` | Agent decision rules and thresholds (loaded by `agent.py`) |
| `strategy/market-intelligence-2026.json` | Market data, portal friction, benchmarks (loaded by many scripts) |
| `signals/signal-actions.yaml` | Signal-to-action audit trail (written by `advance.py`, `log_signal_action.py`) |
| `signals/agent-actions.yaml` | Agent plan/execute run history (written by `agent.py`) |
| `signals/contacts.yaml` | Relationship CRM contacts and interactions (written by `crm.py`) |
| `strategy/notifications.yaml` | Notification event routing: webhook URLs, email recipients (loaded by `notify.py`) |
| `strategy/system-grading-rubric.yaml` | 9-dimension quality rubric for diagnostic grade norming (loaded by `diagnose.py`) |
| `strategy/rater-personas.yaml` | Persona prompts for multi-model IRA raters (loaded by `generate_ratings.py`) |

## Automation (LaunchAgent)

LaunchAgent plist files in `launchd/` for macOS scheduled tasks:

| Agent | Schedule | Script |
|-------|----------|--------|
| `daily-deferred` | Daily 6:00 AM | `check_deferred.py --alert` |
| `daily-monitor` | Daily 6:30 AM | `monitor_pipeline.py --strict` |
| `weekly-backup` | Sunday 2:00 AM | `backup_pipeline.py create` |
| `agent-biweekly` | Mon/Thu 7:00 AM | `agent.py --execute --yes` |
| `weekly-briefing` | Sunday 7:00 PM | `weekly_brief.py --save` |
| `calendar-refresh` | Daily 6:45 AM | `calendar_export.py --output ~/Calendar/pipeline-deadlines.ics --follow-ups` |

Install: `python scripts/launchd_manager.py --install --kickstart`
Status: `python scripts/launchd_manager.py --status`

## CLI vs Raw Scripts

The Typer CLI (`pipeline` command) and `run.py` coexist. Use either:

| Method | Example | When to Use |
|--------|---------|-------------|
| `run.py` | `python scripts/run.py standup` | Quick single-word commands, backward compat |
| CLI | `pipeline score <id>` | Clean API, structured output, programmatic use |
| MCP | `mcp_server.py` | AI-assisted autonomous execution |

## Testing Patterns

- Tests live in `tests/` (~1,977 tests) and use pytest
- Scripts use `sys.path.insert(0, ...)` to add `scripts/` to the import path (no package installation needed)
- **Two test styles**: (1) live-data tests validate against actual YAML files, block directories, and profiles; (2) isolated tests use `tmp_path`, `monkeypatch`, and `capsys` for unit testing script logic
- `pytest-mock` available; `monkeypatch.setattr` used extensively for isolating filesystem, `sys.argv`, and module globals
- ATS synthetic tests (`test_ats_synthetic.py`) require internet and are marked `@pytest.mark.synthetic`
- Run `ruff` via `.venv/bin/activate` — it's not in the global PATH

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

- **Deadline Prioritization**:
  - Remind user when a deadline is within **14 days** (2 weeks).
  - Heavily prioritize and flag as urgent when a deadline is within **7 days** (1 week).
- Pipeline YAML filenames use kebab-case matching the `id` field
- Block filenames are descriptive and match reference paths in pipeline YAML
- Variant filenames follow `{target-type}-v{n}.md` or `{target-specific-name}.md` pattern
- All narrative text uses covenant-ark metrics (update there first, propagate here)
- Prefer `pathlib.Path` for filesystem logic; explicit YAML field validation over implicit assumptions
- `daily_batch.py` and `daily_pipeline.py` are deprecated (moved to `scripts/deprecated/`). Use `standup.py --section plan` and `campaign.py --execute` instead
- Never commit secrets or local submission data (`.submit-config.yaml`, `.greenhouse-answers/`, `.env`)

## Relationship to Corpus

Canonical identity statements, metrics, and evidence live in `organvm-corpvs-testamentvm/docs/applications/00-covenant-ark.md`. This repo consumes those as source of truth and composes them into submission-ready materials. When metrics change, update covenant-ark first, then propagate to blocks here. Run `python scripts/check_metrics.py` to verify consistency.

## CI & Linting

- CI runs via `.github/workflows/quality.yml`: verification matrix, ruff lint, signal validation, YAML validation, pytest (Ubuntu, Python 3.12)
- **Verification matrix gate**: `python scripts/verification_matrix.py --strict` runs first in CI — enforces module-to-test coverage (117/117 modules). Override exceptions in `strategy/module-verification-overrides.yaml`.
- **Signal validation gate**: `python scripts/validate_signals.py --strict` validates all signal YAML files (signal-actions, conversion-log, hypotheses, agent-actions) plus referential integrity and contacts schema
- Linter: `ruff check scripts/ tests/` — config in `pyproject.toml` (line-length 120, E/F/I/UP rules, E501 ignored)
- No formal coverage threshold; prioritize regression coverage for pipeline state and YAML schema changes
- Full local CI-parity check: `python scripts/verify_all.py`

## Dependencies

- Python 3.11+ (venv at `.venv/` uses Python 3.14)
- Runtime: PyYAML, Typer (CLI), google-genai (AI answer generation), mcp (MCP server)
- Dev: pytest, pytest-mock, ruff (`pip install -e ".[dev]"`)
- ATS submitters use stdlib `urllib` for HTTP (no requests dependency)
- Editable install metadata in `application_pipeline.egg-info/` (from `pip install -e .`)
