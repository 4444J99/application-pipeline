# Product Extraction: Application Pipeline → ORGAN-III Flagship

**Date:** 2026-03-30
**Authority:** User directive — "application pipeline should be a product and should be an organ"
**Pattern:** Same as Cvrsvs Honorvm (NLnet/aerarium) — extract reusable engine from working system

## The Insight

The application pipeline is not personal tooling. It's a general-purpose multi-track application management engine that happens to run one production instance. 161 scripts, 3,266 tests, 127 CLI commands. The same extraction pattern as Cvrsvs Honorvm: built for one, portable for many.

## The Triptych

Three instances of one engine, not three separate systems:

| Instance | Track Config | Data Location | Identity |
|----------|-------------|---------------|----------|
| Jobs (personal) | weights_job, ATS integrations | 4444J99/application-pipeline | Platform Orchestrator |
| Grants (institutional) | weights_grant, forced revision SOP | meta-organvm/aerarium--res-publica | Systems Artist / Infra Builder |
| Consulting (commercial) | weights_consulting, client lifecycle | organvm-iii-ergon/commerce--meta | Founder-Operator |

## Extraction Boundary

### ENGINE (154 scripts, reusable)
- **State machine:** pipeline_entry_state.py — status transitions, validation, actionable checks
- **Scoring:** score.py, score_network.py, text_match.py — configurable multi-dimension rubric
- **ATS clients:** greenhouse_submit.py, lever_submit.py, ashby_submit.py — portal integrations
- **Outreach:** dm_composer.py, protocol_validator.py, protocol_types.py, network_graph.py, followup.py
- **Quality gates:** tailor_resume.py (sentence completeness validator), apply.py (URL liveness, portal validation), recruiter_filter.py
- **CRM:** crm.py, research_contacts.py, log_dm.py, reconcile_outreach.py
- **Analytics:** funnel_report.py, snapshot.py, org_intelligence.py, skills_gap.py, block_outcomes.py
- **Diagnostics:** diagnose.py, diagnose_ira.py, generate_ratings.py, standards.py
- **CLI:** run.py (127 commands), cli.py (Typer)
- **Library:** pipeline_lib.py + 6 extracted modules

### INSTANCE (personal data, stays in 4444J99)
- pipeline/ — 72 YAML entries
- applications/ — submission bundles
- materials/ — resumes, cover letters, profiles
- signals/ — contacts, outreach log, conversion data
- blocks/ — 126 narrative modules (content is personal; structure is engine)
- intake/ — ingestion staging

### 7 SCRIPTS WITH INSTANCE COUPLING
These reference personal data and need configurable identity injection:
- check_email.py, check_email_constants.py — email config
- generate_project_blocks.py — ORGANVM-specific project list
- materials_validator.py — personal metrics
- prepare_submission.py — personal info
- refresh_from_ecosystem.py — ORGANVM system snapshot
- standards.py — ORGANVM-specific validators

## Extraction Phases

### Phase 1: Declare (DONE)
- [x] Update seed.yaml — organ: III, tier: flagship, extraction boundary documented
- [x] Declare produces/consumes edges
- [x] Document in memory

### Phase 2: Decouple
- [ ] Create `config/identity.yaml` — personal data (name, email, phone, links, metrics)
- [ ] Replace hardcoded personal references in 7 coupled scripts with identity config loads
- [ ] Extract `STANDARD_ANSWERS` from apply.py into config
- [ ] Extract `CANONICAL` metrics from recruiter_filter.py into config
- [ ] Extract `CREDENTIALS`/`TITLE_LINES` from apply.py and build_cover_letters.py into config

### Phase 3: Package
- [ ] Define `pyproject.toml` entry points for the engine CLI
- [ ] Separate `src/` (engine) from data directories
- [ ] `pip install application-pipeline-engine` provides the CLI + library
- [ ] Instance repo provides data directories + identity config

### Phase 4: Second Instance
- [ ] Aerarium adopts the engine for grant track
- [ ] Commerce--meta adopts the engine for consulting track
- [ ] Prove the extraction works by running a non-personal instance

## Relationship to Cvrsvs Honorvm

| | Cvrsvs Honorvm | Application Pipeline Engine |
|---|---|---|
| Source | organvm-engine (314 files, 73K lines) | application-pipeline (161 scripts, 3,266 tests) |
| Extract | Governance primitives (state machine, DAG validator, seed contracts) | Application primitives (state machine, scoring, ATS, outreach, quality gates) |
| Funder | NLnet NGI0 Commons (EUR 37,080) | TBD — could be NLnet, could be self-funded product |
| License | Apache 2.0 | TBD (open-core: engine Apache 2.0, premium features LLC) |
| First external user | Minimal 3-repo example project | Aerarium grant track |
