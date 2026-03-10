# Application Pipeline Script Inventory Task

## Objective
Create a complete inventory of all executable Python scripts in `/Users/4jp/Workspace/4444J99/application-pipeline/scripts/`, including:
- Script names and CLI flags/arguments
- One-line descriptions
- Workflow categorization
- Comparison with CLAUDE.md documentation

## Task Status

### Phase 1: Initial Reconnaissance ✓ COMPLETED
- Identified 34 Python scripts in scripts/ directory
- Files listed: advance.py, alchemize.py, answer_questions.py, archive_research.py, ashby_submit.py, browser_submit.py, build_block_index.py, build_resumes.py, campaign.py, check_metrics.py, check_outcomes.py, compose.py, conversion_report.py, distill_keywords.py, draft.py, enrich.py, followup.py, funnel_report.py, generate_project_blocks.py, greenhouse_submit.py, hygiene.py, lever_submit.py, migrate_batch_folders.py, pipeline_lib.py, pipeline_status.py, preflight.py, research_contacts.py, score.py, source_jobs.py, standup.py, submit.py, tailor_resume.py, validate.py, velocity.py

### Phase 2: Detailed Analysis (PENDING)
For each script, extract:
1. Script name
2. Full argparse configuration (all flags, arguments, help text)
3. One-line description
4. Workflow category assignment:
   - **Daily Workflow**: standup, campaign, followup
   - **Batch Operations**: enrich, advance, score, archive_research
   - **Analysis**: funnel_report, conversion_report, velocity, check_outcomes
   - **Submission**: submit, compose, draft, alchemize, greenhouse_submit, ashby_submit, lever_submit, browser_submit
   - **Maintenance**: validate, hygiene, check_metrics, source_jobs, pipeline_status, tailor_resume, build_resumes, build_block_index, generate_project_blocks, distill_keywords, answer_questions, research_contacts, migrate_batch_folders

### Phase 3: Documentation Comparison (PENDING)
- Compare documented commands in CLAUDE.md against actual script implementations
- Identify discrepancies between documentation and code

### Phase 4: Compilation (PENDING)
- Return structured inventory organized by workflow type
- Include exact CLI signatures for each script

## Workflow Categories

### Daily Workflow
Scripts run at start of session to assess status and plan day.
- `standup.py` - Daily standup with time budget and triage
- `campaign.py` - Deadline-aware pipeline execution
- `followup.py` - Follow-up tracker and outreach list

### Batch Operations
Scripts that operate on multiple pipeline entries at once.
- `enrich.py` - Wire materials, blocks, variants, portal_fields
- `advance.py` - Move entries through pipeline states
- `score.py` - Scoring with 8-dimension rubric
- `archive_research.py` - Move research entries to archive

### Analysis & Reporting
Scripts that generate analytics and insights.
- `funnel_report.py` - Conversion funnel analytics
- `conversion_report.py` - Basic conversion analysis
- `velocity.py` - Submission velocity tracking
- `check_outcomes.py` - TBD

### Submission
Scripts that generate portal-ready submissions or integrate with ATS platforms.
- `submit.py` - Generate paste-ready checklists
- `compose.py` - Compose from blocks
- `draft.py` - Draft from profiles
- `alchemize.py` - Greenhouse orchestrator
- `greenhouse_submit.py` - Greenhouse API submission
- `ashby_submit.py` - Ashby API submission
- `lever_submit.py` - Lever API submission
- `browser_submit.py` - Playwright browser automation
- `answer_questions.py` - AI-assisted answer generation
- `distill_keywords.py` - Keyword extraction

### Maintenance & Support
Scripts for pipeline hygiene, validation, and infrastructure.
- `validate.py` - Validate pipeline YAML
- `hygiene.py` - Pipeline data integrity checks
- `check_metrics.py` - Verify metrics consistency
- `source_jobs.py` - Fetch jobs from ATS APIs
- `pipeline_status.py` - Pipeline overview
- `tailor_resume.py` - Wire resumes to YAML
- `build_resumes.py` - PDF build via headless Chrome
- `build_block_index.py` - Build searchable block index
- `generate_project_blocks.py` - Auto-generate project blocks
- `research_contacts.py` - Research contact management
- `migrate_batch_folders.py` - Resume batch folder migration
- `pipeline_lib.py` - Shared library (not a CLI script)

## Deliverable Format

```
# Application Pipeline Script Inventory

## Daily Workflow (3 scripts)
### standup.py
**CLI Signature**: `python scripts/standup.py [--hours HOURS] [--section SECTION] [--touch ENTRY_ID] [--log] [--triage]`
**Description**: Daily standup with time budget assessment and entry triage
**Flags**: --hours, --section, --touch, --log, --triage

### campaign.py
**CLI Signature**: `python scripts/campaign.py [--days DAYS] [--save] [--execute] [--id ENTRY_ID] [--yes]`
**Description**: Deadline-aware pipeline execution with 14-day window

### followup.py
**CLI Signature**: `python scripts/followup.py [--all] [--schedule] [--overdue] [--log ENTRY_ID] [--channel CHANNEL] [--contact CONTACT] [--note NOTE]`
**Description**: Follow-up tracker and daily outreach list

## ... (other categories)
```

## Progress Tracking

- [ ] Read argparse from standup.py
- [ ] Read argparse from campaign.py
- [ ] Read argparse from followup.py
- [ ] Read argparse from enrich.py
- [ ] Read argparse from advance.py
- [ ] Read argparse from score.py
- [ ] Read argparse from archive_research.py
- [ ] Read argparse from funnel_report.py
- [ ] Read argparse from conversion_report.py
- [ ] Read argparse from velocity.py
- [ ] Read argparse from check_outcomes.py
- [ ] Read argparse from submit.py
- [ ] Read argparse from compose.py
- [ ] Read argparse from draft.py
- [ ] Read argparse from alchemize.py
- [ ] Read argparse from greenhouse_submit.py
- [ ] Read argparse from ashby_submit.py
- [ ] Read argparse from lever_submit.py
- [ ] Read argparse from browser_submit.py
- [ ] Read argparse from answer_questions.py
- [ ] Read argparse from distill_keywords.py
- [ ] Read argparse from validate.py
- [ ] Read argparse from hygiene.py
- [ ] Read argparse from check_metrics.py
- [ ] Read argparse from source_jobs.py
- [ ] Read argparse from pipeline_status.py
- [ ] Read argparse from tailor_resume.py
- [ ] Read argparse from build_resumes.py
- [ ] Read argparse from build_block_index.py
- [ ] Read argparse from generate_project_blocks.py
- [ ] Read argparse from research_contacts.py
- [ ] Read argparse from migrate_batch_folders.py
- [ ] Compare against CLAUDE.md documentation
- [ ] Compile final inventory
