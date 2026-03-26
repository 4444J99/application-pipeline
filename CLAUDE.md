# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Career application pipeline repo — personal infrastructure for managing grant, residency, fellowship, job, and writing applications as a structured conversion pipeline. Implements a **"Cathedral → Storefront"** philosophy: preserving deep, immersive systemic work (Cathedral) while providing high-signal, scannable entry points (Storefront) for reviewers.

**Owner:** @4444J99 (personal/liminal — not an organ repo)
**Parent:** `~/Workspace/4444J99/application-pipeline/`

## Three-Pillar Model

The pipeline serves three revenue pillars for the ORGANVM studio:

| Pillar | Purpose | Scoring Rubric | Track |
|--------|---------|---------------|-------|
| **1. Jobs** | Runway (temporary funding) | `weights_job` — network_proximity + deadline_feasibility + studio_alignment + remote_flexibility | `job` |
| **2. Grants & Funding** | Validation + non-dilutive capital | `weights_grant` — mission_alignment + narrative_fit + prestige_multiplier + cycle_urgency | `grant`, `residency`, `fellowship`, `prize`, `writing`, `emergency` |
| **3. Consulting** | Bridge to studio (recurring revenue, full autonomy) | `weights_consulting` — network_proximity + recurring_potential + studio_alignment + client_fit | `consulting` |

**North star:** ORGANVM is a studio — a Pixar, an ILM. Jobs buy time. Grants validate the art. Consulting builds the client base.

## Canonical Application Flow

**ALWAYS use `apply.py` to generate application packages.** Never create files manually.

```bash
python scripts/apply.py --target <entry-id>     # Single entry
python scripts/apply.py --batch                  # All staged entries
python scripts/apply.py --target <id> --dry-run  # Preview
```

The command runs this pipeline automatically:
1. **Clearance gate** — hard-blocks entries requiring active clearance, soft-passes eligibility-only
2. **Standards audit** (Level 1) — triad regulators with quorum
3. **Greenhouse API question fetch** — real portal fields, not invented
4. **Answer generation** — standard auto-fill + role-specific free-text
5. **Cover letter resolution** — from variants, unique from resume (WHY not WHAT)
6. **Protocol-validated outreach DM** — composed for org contacts, 7 articles checked
7. **Overlap check** — cover letter vs resume, <3 shared 4-word phrases
8. **PDF build** — Chrome headless, 1 page
9. **Application directory** — `applications/YYYY-MM-DD/<org>--<role>/`
10. **Continuity test** — all connections verified before declaring READY

**Outreach rule:** NEVER recycle already-contacted people. Research 3 FRESH contacts per submission.

## Pipeline Philosophy: Precision Over Volume

**Effective 2026-03-04.** The pipeline optimizes for finding perfect-fit roles and building relationships, not throughput.

- **Max 1-2 applications per week**, each deeply researched
- **Minimum score 7.0** to apply (recalibrated 2026-03-15 from 9.0); network_proximity >= 5 preferred
- **9 scoring dimensions** including `network_proximity` (referral = 8x hire rate)
- **Max 10 actionable entries** (qualified+drafting+staged) at any time; max 1 per organization. Note: the `active/` directory may contain more files including recently-promoted research entries awaiting triage.
- **Daily split:** 2hr research, 2hr relationships, 1hr application work
- **Stale thresholds relaxed:** 14 days (was 7), stagnant 30 days (was 14). _Source: loaded dynamically from `strategy/market-intelligence-2026.json`; these are the fallback defaults when JSON is absent._
- **No volume pressure** in standup messaging; no "ship something this week"
- **Minimum outreach before submission:** At least 1 outreach action (LinkedIn connect, email, referral ask) required before advancing to submitted. Use `followup.py --log` to record.
- **Rationale:** 60 cold applications in 4 days → 0 interviews. Precision targeting + warm paths is the only viable strategy. Note: referral multiplier (8x) and cover letter callback (+53%) are *market benchmarks* (not yet validated by this pipeline's own data).

## Architecture

**Root follows Minimal Root philosophy — only architectural pillars at top level.**

- `pipeline/` — One YAML file per application, organized into `active/`, `submitted/`, `closed/`, `research_pool/`, and `archive/` subdirectories (schema in `_schema.yaml`)
  - `research_pool/` holds auto-sourced research-status entries, separated from actionable entries to keep `active/` lean (~30 files vs ~1000)
  - `archive/drafts/` — old markdown checklists (historical, not active)
- `blocks/` — Modular narrative building blocks with tiered depth (60s / 2min / 5min / cathedral). Each block has frontmatter: `title`, `category`, `tags`, `identity_positions`, `tracks`, `tier`. Regenerate the tag index with `python scripts/build_block_index.py`.
- `materials/` — All submission materials consolidated:
  - `resumes/` — `base/` (9 identity-position templates) and `batch-NN/` (target-tailored, current: `batch-03/`)
  - `variants/` — A/B tracked material versions (cover-letters, project-descriptions, statements)
  - `targets/profiles/` — 1,030+ target-specific profile JSONs with pre-written artist statements, bios, work samples
  - `targets/grants/`, `targets/jobs/`, `targets/residencies/` — track-specific research
  - `cvs/`, `headshots/`, `work-samples/`
- `applications/` — Dated submission bundles (`applications/YYYY-MM-DD/<org>--<role>/`). Each contains: entry.yaml, portal-answers.md, cover-letter.md/.pdf, resume.pdf, outreach-dm.md. Generated by `apply.py`.
- `signals/` — Conversion analytics and observability data:
  - `contacts.yaml`, `outreach-log.yaml`, `network.yaml` — relationship CRM
  - `conversion-log.yaml`, `hypotheses.yaml`, `signal-actions.yaml` — pipeline signals
  - `daily-health/`, `daily-snapshots/`, `weekly-brief/` — automated reports
  - `ratings/` — IRA inter-rater agreement session results
- `strategy/` — Strategic documents (scoring rubric, identity positions, market intelligence, agent rules)
- `scripts/` — 160+ Python CLI tools (all import from `pipeline_lib.py`)
- `docs/` — Architecture rationale, thesis chapters, venture roadmaps, specs
  - `docs/superpowers/specs/` — design specifications
  - `docs/ventures/` — client project roadmaps (Pillar 3)
  - `docs/reports/` — evaluation reports and checklists
- `.config/` — Tooling configs (`metrics.yaml`) and `launchd/` plist files
- `.claude/memory/` — Session memory backup (synced from `~/.claude/projects/.../memory/`). Must be committed and pushed on every session close. 33 files.
- `intake/` — Ingestion staging area (CSV exports, LinkedIn data). Not part of active pipeline.

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

Every application must align with one of nine canonical positions defined in `strategy/identity-positions.md`. These determine framing, block selection, and resume variant:

1. **Systems Artist** — Art grants/residencies. Focus: governance as artwork, systemic scale.
2. **Educator / Learning Architect** — Academic roles, EdTech, L&D. Focus: curriculum design, systems pedagogy.
3. **Creative Technologist** — Tech grants/consulting. Focus: AI orchestration, production-grade creative instruments.
4. **Community Practitioner** — Identity-specific funding. Focus: precarity-informed systemic practice.
5. **Independent Engineer** — AI lab roles (Anthropic, OpenAI). Focus: testing discipline, CI/CD, systems architecture.
6. **Documentation Engineer** — Docs-as-code roles (Stripe, Vercel). Focus: 810K+ words, content architecture, auto-generation.
7. **Governance / Compliance Architect** — AI safety, EU AI Act. Focus: human-oversight architecture, promotion state machine.
8. **Platform Orchestrator** — Platform engineering, DevEx. Focus: 8-org orchestration, registry, pulse daemon.
9. **Founder / Operator** — Fractional CTO, advisory, accelerators. Focus: solo institutional-scale operation.

## Content Composition Model

Three content layers feed into submissions:

1. **Blocks** (`blocks/`) — Reusable narrative modules authored manually. Referenced by path in pipeline YAML `submission.blocks_used` (e.g. `identity/2min`, `projects/organvm-system`). See `blocks/README.md` for the tier system.
2. **Profiles** (`materials/targets/profiles/*.json`) — Target-specific pre-written content: artist statements at 3 lengths, bios, work samples.
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
- **`diagnose_ira.py`** — standalone; computes ICC (intraclass correlation coefficient), Cohen's kappa, Fleiss kappa, and consensus from rating JSON files in `ratings/`. Includes `partition_dimensions()` for separating objective ground truth from subjective rated dimensions. The core IRA diagnostic tool.
- **`generate_ratings.py`** imports from `diagnose.py` — uses COLLECTORS, PROMPT_GENERATORS, OBJECTIVE_DIMENSIONS, SUBJECTIVE_DIMENSIONS for multi-model IRA rating. Calls Anthropic and Google APIs. Produces rating JSON files consumed by `diagnose_ira.py`.
- **`standards.py`** imports from `diagnose.py`, `diagnose_ira.py`, `audit_system.py`, and other validators — hierarchical standards validation framework with a five-level oversight architecture (triad regulators: 3 gates per level, ≥2/3 quorum). Wraps existing validators and adds Level 4-5 assessment gates. Designed for meta-ORGANVM portability — data classes and orchestration are organ-agnostic. Loads rubric from `strategy/system-standards.yaml`.
- **`external_validator.py`** imports from `pipeline_market.py` — fetches salary data from BLS OES API, skill demand from Remotive API, org signals from GitHub API. Stores to `strategy/external-validation-cache.json`. Used by `audit_system.py` for external validation audit.
- **`network_graph.py`** — Network graph with BFS/DFS path-finding, hop-decay scoring (Granovetter weak-ties theory), tie-strength tracking. Ingests from `contacts.yaml` and `outreach-log.yaml`. Stores to `signals/network.yaml`. Reverse-syncs to `contacts.yaml` via `--sync-contacts`.
- **`score_network.py`** imports from `network_graph.py` — `_score_from_graph()` queries the network graph for org proximity, combined with entry-level signals via `max(entry_score, graph_score)`.
- **`recruiter_filter.py`** — Pre-submission gate: validates materials against canonical metrics (single source of truth), detects red flags (passive language, "Independent"), checks cover letter existence/quality, auto-fixes stale metrics in base resumes. Run `run.py recruiter` before any submission.
- **`protocol_types.py`** — Domain types for the Outreach Protocol: Message, Agent, Claim, Tension, Question, and 7 validation result dataclasses. Imported by protocol_validator.py and dm_composer.py.
- **`protocol_validator.py`** — Outreach Protocol enforcement: validates messages against 7 formal articles (P-I Hook Planting, P-II Continuity, P-III Ratio Decay, P-IV Terminal Question, P-V Inhabitation, P-VI Bare Resource, P-VII Thread Parity). `validate_full_sequence()` runs all articles.
- **`dm_composer.py`** — Acceptance DM composition using Protocol constraints. Recovers connect notes from outreach plan markdown files, generates Protocol-compliant DMs, validates output. `--contact`, `--all-pending`, `--target` modes. Run `run.py dm <contact>` or `run.py compose-dm`.
- **`reconcile_outreach.py`** — LinkedIn DM history ingestion and backfill. Parses pasted message history (anchors on "Open the options list" line for contact attribution), diffs against outreach-log.yaml, backfills all three signal files.
- **`apply.py`** — **THE canonical application command.** Single command that runs the full pipeline: clearance gate → standards audit (Level 1) → Greenhouse API question fetch → auto-fill answers → cover letter resolution → Protocol-validated DM composition → overlap check → PDF build → application directory creation → continuity test. `run.py apply <id>` or `--batch` for all staged. **Use this for all future applications — never bypass it with manual file creation.**
- **`log_dm.py`** — Single-command DM logging across all 3 signal files (contacts.yaml, outreach-log.yaml, network.yaml). `run.py logdm <contact> --note "..."`. Solves the 3-file-per-DM friction.
- **`standards.py`** — Hierarchical standards validation: 5-level oversight (Course → Department → University → National → Federal) with triad regulators (3 gates per level, ≥2/3 quorum). Wired into apply.py as Level 1 pre-submission gate.
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
python scripts/diagnose_ira.py ratings/*.json          # IRA report from rating files (ICC, Cohen's kappa, Fleiss kappa)
python scripts/diagnose_ira.py ratings/*.json --consensus  # With consensus scores
python scripts/generate_ratings.py                        # Full multi-model rating session
python scripts/generate_ratings.py --rater architect-opus  # Single rater only
python scripts/generate_ratings.py --dry-run               # Show prompts without API calls
python scripts/generate_ratings.py --compute-ira           # Run IRA after rating
python scripts/standards.py                               # Full hierarchical standards audit (5-level, triad regulators)
python scripts/standards.py --level 2                     # Single level only
python scripts/standards.py --json                        # Machine-readable output
python scripts/standards.py --run-all                     # All levels (no cascade stop on failure)
python scripts/external_validator.py                       # Fetch + compare + report
python scripts/external_validator.py --fetch-only          # Refresh validation cache only
python scripts/external_validator.py --compare-only        # Compare using existing cache
python scripts/external_validator.py --json                # Machine-readable output

# Network graph
python scripts/network_graph.py                          # Dashboard: nodes, edges, tie strength
python scripts/network_graph.py --map                    # Full network tree from you
python scripts/network_graph.py --orgs                   # Org reachability scores
python scripts/network_graph.py --path "Cloudflare"      # Find paths to org
python scripts/network_graph.py --path "Cloudflare" --all # All paths (max 3 hops)
python scripts/network_graph.py --score <entry-id>       # Network score for entry
python scripts/network_graph.py --ingest                 # Ingest contacts + outreach into graph
python scripts/network_graph.py --sync-contacts          # Sync graph → contacts.yaml
python scripts/network_graph.py --add-edge --from "A" --to "B" --strength 7  # Add edge

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

Single-word command protocol via `python scripts/run.py <command>`. 102 standalone + 25 parameterized = 127 commands.

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
| `network` | Network graph: nodes, edges, tie strength distribution |
| `netmap` | Network map: full tree from you |
| `netorgs` | Org reachability: scores, hops, paths per org |
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
| `ira` | Inter-rater agreement report (ICC, Cohen's kappa, Fleiss kappa — needs ratings/*.json) |
| `rateall` | Multi-model IRA rating session with diverse AI panel |
| `validate-external` | Refresh external validation cache and compare against scoring inputs |
| `standards` | Hierarchical standards audit (5-level oversight, triad regulators, ≥2/3 quorum) |

**With target ID:** `score <id>`, `enrich <id>`, `advance <id>`, `compose <id>`, `draft <id>`, `submit <id>`, `check <id>`, `record <id>`, `gate <id>`, `contacts <id>`, `hypothesis <id>`, `alchemize <id>`, `answers <id>`, `tailor <id>`, `review <id>`, `cultivate <id>`, `textmatch <id>`, `skillsgap <id>`, `orgdetail <org>`, `interviewprep <id>`, `netpath <org>`, `netscore <id>`

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
- Network: `network` → `netmap` → `netorgs` → `netpath <org>` → `netscore <id>`
- Diagnostic: `diagnose` → `rateall` → `ira` → `validate-external`

## Configuration Files

| File | Purpose |
|------|---------|
| `strategy/scoring-rubric.yaml` | Three-pillar scoring rubric v3.0: `weights_job` (11 dims incl. studio_alignment, remote_flexibility), `weights_grant` (10 dims incl. narrative_fit, prestige_multiplier, cycle_urgency), `weights_consulting` (9 dims incl. recurring_potential, client_fit). `score.py` dispatches by track. |
| `strategy/agent-rules.yaml` | Agent decision rules and thresholds (loaded by `agent.py`) |
| `strategy/market-intelligence-2026.json` | Market data, portal friction, benchmarks (loaded by many scripts) |
| `signals/signal-actions.yaml` | Signal-to-action audit trail (written by `advance.py`, `log_signal_action.py`) |
| `signals/agent-actions.yaml` | Agent plan/execute run history (written by `agent.py`) |
| `signals/contacts.yaml` | Relationship CRM contacts and interactions (written by `crm.py`, synced by `network_graph.py`) |
| `signals/network.yaml` | Network graph: nodes, edges, tie strengths (written by `network_graph.py`, read by `score_network.py`) |
| `signals/outreach-log.yaml` | Outreach action log: connection requests, DMs, seeds (written by `followup.py`, `network_graph.py`) |
| `strategy/notifications.yaml` | Notification event routing: webhook URLs, email recipients (loaded by `notify.py`) |
| `strategy/system-grading-rubric.yaml` | 9-dimension quality rubric for diagnostic grade norming (loaded by `diagnose.py`) |
| `strategy/rater-personas.yaml` | Persona prompts for multi-model IRA raters (loaded by `generate_ratings.py`) |
| `strategy/external-validation-cache.json` | Cached external data from BLS/GitHub/job APIs (written by `external_validator.py`) |

## Automation (LaunchAgent)

LaunchAgent plist files in `launchd/` for macOS scheduled tasks:

| Agent | Schedule | Script |
|-------|----------|--------|
| `daily-deferred` | Daily 6:00 AM | `check_deferred.py --alert` |
| `daily-monitor` | Daily 6:30 AM | `monitor_pipeline.py --strict` |
| `weekly-backup` | Sunday 2:00 AM | `backup_pipeline.py create` |
| `daily-intake-triage` | Daily 6:15 AM | `score.py --all --include-pool` |
| `agent-daily` | Daily 7:00 AM | `agent.py --execute --yes` |
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

## Makefile

Convenience targets wrapping common commands:

```bash
make test            # Full pytest suite (python -m pytest tests/ -q)
make test-fast       # Quick smoke subset (pipeline_lib, validate, run, cli tests only)
make lint            # ruff check scripts/ tests/
make validate        # Schema + ID map + rubric validation
make verify          # Full verify_all.py (CI-parity)
make verify-quick    # Fast verification gates (verify_all.py --quick)
```

## Testing Patterns

- Tests live in `tests/` (~1,977 tests) and use pytest
- Scripts use `sys.path.insert(0, ...)` to add `scripts/` to the import path (no package installation needed)
- **Two test styles**: (1) live-data tests validate against actual YAML files, block directories, and profiles; (2) isolated tests use `tmp_path`, `monkeypatch`, and `capsys` for unit testing script logic
- `pytest-mock` available; `monkeypatch.setattr` used extensively for isolating filesystem, `sys.argv`, and module globals
- ATS synthetic tests (`test_ats_synthetic.py`) require internet and are marked `@pytest.mark.synthetic`
- **Test isolation via `conftest.py`**: sets `PIPELINE_METRICS_SOURCE=fallback` (deterministic metrics) and redirects `PIPELINE_SIGNAL_ACTIONS_PATH` to a temp directory (prevents tests from mutating repo signal logs)
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
- **Test count distinction:** 23,470 tests = system-wide across all ORGANVM repos; 3,266 = this pipeline specifically. Use "23,470 tests" in outward-facing materials (resumes, cover letters, LinkedIn); use "3,266 tests" for pipeline-specific claims.
- **Canonical metrics** are defined in `scripts/recruiter_filter.py` CANONICAL dict. Update there first when metrics change; run `python scripts/run.py recruiter --fix` to propagate to base resumes.
- All narrative text uses covenant-ark metrics (update there first, propagate here)
- Prefer `pathlib.Path` for filesystem logic; explicit YAML field validation over implicit assumptions
- `daily_batch.py` and `daily_pipeline.py` are deprecated (moved to `scripts/deprecated/`). Use `standup.py --section plan` and `campaign.py --execute` instead
- Never commit secrets or local submission data (`.submit-config.yaml`, `.greenhouse-answers/`, `.env`)

## Academic & Institutional Context

This pipeline is the first case study for two cross-cutting ORGANVM systems:

### The Self-Governing Evaluative Authority
A multi-model IRA (inter-rater agreement) facility that evaluates this pipeline's quality across 9 dimensions using 4 AI raters with distinct personas. Implements Beer's Viable System Model System 3* (independent audit). The authority is domain-agnostic — the pipeline is its first client, not its reason for existing.

- Authority dissertation: `meta-organvm/praxis-perpetua/research/dissertation-institutional-authority/`
- Supporting docs: `meta-organvm/praxis-perpetua/research/2026-03-15-institutional-immune-system.md`, `2026-03-15-self-governing-institution-of-checks.md`
- Journal paper (Doc A): `organvm-v-logos/public-process/research/2026-03-15-ai-as-psychometrician.md`

### The Studium Generale ORGANVM (SGO)
ORGANVM's internal university, research engine, and publication house. **Home: `meta-organvm/praxis-perpetua/`** (governance YAMLs, defense rubrics, research corpus, dissertations). This pipeline's thesis (Ch 1-10 in `docs/thesis/`) is SGO-2026-D-001. The evaluative authority's dissertation is SGO-2026-D-002.

- SGO home: `meta-organvm/praxis-perpetua/` (governance/, strategy/, research/, commissions/)
- SGO design spec: `docs/superpowers/specs/2026-03-17-studium-generale-organvm-design.md`
- Research corpus index: `meta-organvm/praxis-perpetua/research/README.md`

### Thesis Chapters
| Chapter | File | Content |
|---------|------|---------|
| Ch 1-7 | `docs/thesis/01-07` | MCDA framework, proofs, competitive analysis |
| Ch 8 | `docs/thesis/08-evaluative-capacity.md` | IRA facility as pipeline self-regulation |
| Ch 9 | `docs/thesis/09-conductor-methodology.md` | Production + evaluation as co-constitutive |
| Ch 10 | `docs/thesis/10-generalization.md` | Generalization to other domains |

## Relationship to Corpus

Canonical identity statements, metrics, and evidence live in `organvm-corpvs-testamentvm/docs/applications/00-covenant-ark.md`. This repo consumes those as source of truth and composes them into submission-ready materials. When metrics change, update covenant-ark first, then propagate to blocks here. Run `python scripts/check_metrics.py` to verify consistency.

## CI & Linting

- CI runs via `.github/workflows/quality.yml` on push/PR to main + weekly Monday 6am schedule
- **Push/PR job**: runs `verify_all.py` (bundles verification matrix, lint, validation, pytest) + advisory `preflight.py --status staged`
- **Weekly regression job**: adds `outcome_learner.py --drift-check` on top of the push/PR checks
- **Verification matrix gate**: `python scripts/verification_matrix.py --strict` — enforces module-to-test coverage (117/117 modules). Override exceptions in `strategy/module-verification-overrides.yaml`.
- **Signal validation gate**: `python scripts/validate_signals.py --strict` validates all signal YAML files (signal-actions, conversion-log, hypotheses, agent-actions) plus referential integrity and contacts schema
- Linter: `ruff check scripts/ tests/` — config in `pyproject.toml` (line-length 120, E/F/I/UP rules, E501 ignored)
- No formal coverage threshold; prioritize regression coverage for pipeline state and YAML schema changes
- Full local CI-parity check: `python scripts/verify_all.py` (or `make verify`)

## Dependencies

- Python 3.11+ (venv at `.venv/` uses Python 3.14)
- Runtime: PyYAML, ruamel.yaml, Typer (CLI), anthropic, google-genai (AI answer generation), mcp (MCP server)
- Dev: pytest, pytest-mock, ruff (`pip install -e ".[dev]"`)
- Optional: `pip install -e ".[jobspy]"` for python-jobspy job sourcing integration
- ATS submitters use stdlib `urllib` for HTTP (no requests dependency)
- Editable install metadata in `application_pipeline.egg-info/` (from `pip install -e .`)
