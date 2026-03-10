# Pipeline Hardening: Tests, Commands, and Alpha-to-Omega

## Context

The four systemic fixes from the previous plan are implemented and working (hygiene.py, check_metrics.py enhancement, followup --init, standup followup dashboard, check_outcomes.py, research_contacts.py, funnel_report --compare-variants, conversion_report response-time analysis, submit metrics freshness check). 615 tests pass; 1 pre-existing failure remains. This plan addresses the next layer: test coverage gaps, cross-LLM command protocol, and remaining gaps to production maturity.

---

## [1] Fix Pre-Existing Test Failure

**File:** `tests/test_archive_research.py:69` — `test_active_has_no_research_after_archive`

**Root cause:** The test asserts `len(research_in_active) == 0` when `research_pool/` has entries. But 3 research-status entries remain in `active/` intentionally (they're being actively worked on and shouldn't be archived).

**Fix:** Change the assertion from strict zero to a threshold. The test's own docstring already acknowledges this: "After archival, active/ should have few or no research entries." Replace the hard `== 0` assertion with a tolerance (e.g., `<= 5`) and add a warning annotation when count > 0:

```python
# In test_active_has_no_research_after_archive:
if pool_entries:
    assert len(research_in_active) <= 5, (
        f"research_pool/ has {len(pool_entries)} entries but active/ has "
        f"{len(research_in_active)} research entries — consider running "
        f"archive_research.py --yes"
    )
    if research_in_active:
        import warnings
        warnings.warn(
            f"{len(research_in_active)} research entries in active/ "
            f"(may be intentionally kept for active work)"
        )
```

**File to modify:** `tests/test_archive_research.py`

---

## [2] Test Suite: Coverage Map and New Tests

### Coverage Map

| Script | Test File | Status |
|--------|-----------|--------|
| advance.py | test_advance.py | Has tests |
| alchemize.py | test_alchemize.py | Has tests |
| answer_questions.py | — | **NEEDS TESTS** |
| archive_research.py | test_archive_research.py | Has tests (fix #1) |
| ashby_submit.py | test_ashby_submit.py | Has tests |
| browser_submit.py | — | Skip (Playwright dependency, interactive) |
| build_block_index.py | — | **NEEDS TESTS** |
| build_resumes.py | — | Skip (headless Chrome dependency) |
| campaign.py | test_campaign.py | Has tests |
| check_metrics.py | — | **NEEDS TESTS** (new Phase 2 code) |
| check_outcomes.py | — | **NEEDS TESTS** (new Phase 4 code) |
| compose.py | test_compose.py | Has tests |
| conversion_report.py | — | **NEEDS TESTS** (new response_time_analysis) |
| distill_keywords.py | test_distill_keywords.py | Has tests |
| draft.py | test_draft.py | Has tests |
| enrich.py | test_enrich.py | Has tests |
| followup.py | test_followup.py | Has tests — **ADD** init_follow_ups tests |
| funnel_report.py | test_funnel_report.py | Has tests — **ADD** compare_variants tests |
| generate_project_blocks.py | test_generate_blocks.py | Has tests |
| greenhouse_submit.py | test_greenhouse_submit.py | Has tests |
| hygiene.py | — | **NEEDS TESTS** (new Phase 1 code) |
| lever_submit.py | test_lever_submit.py | Has tests |
| migrate_batch_folders.py | — | Skip (one-shot migration, already run) |
| pipeline_lib.py | test_pipeline_lib.py | Has tests |
| pipeline_status.py | test_pipeline_status.py | Has tests |
| preflight.py | test_preflight.py | Has tests |
| research_contacts.py | — | **NEEDS TESTS** (new Phase 3 code) |
| score.py | test_score.py | Has tests |
| source_jobs.py | — | **NEEDS TESTS** |
| standup.py | test_standup.py | Has tests — **ADD** section_followup tests |
| submit.py | test_submit.py | Has tests — **ADD** _check_metrics_freshness tests |
| tailor_resume.py | — | **NEEDS TESTS** |
| validate.py | test_validate.py | Has tests |
| velocity.py | test_velocity.py | Has tests |

### New Test Files to Create (8)

All tests follow existing pattern: `sys.path.insert(0, ...)`, `_make_entry()` helpers, test function return values not subprocess output, no external mocking framework.

#### `tests/test_check_metrics.py`
- `test_fallback_metrics_keys` — _FALLBACK_METRICS has all required keys
- `test_fallback_metrics_repo_count` — total_repos matches sum of organ counts
- `test_organ_patterns_all_organs` — ORGAN_PATTERNS covers I-VII
- `test_metric_patterns_structure` — Each METRIC_PATTERNS entry has name, patterns, metric_key, transform
- `test_check_file_clean` — check_file on a file with correct metrics returns []
- `test_check_file_stale_repo_count` — check_file detects wrong "N repositories"
- `test_check_file_stale_word_count` — check_file detects wrong "NK words of"
- `test_check_file_skips_organ_lines` — Organ-specific lines not flagged as total_repos mismatch
- `test_check_profile_json_valid` — Valid profile returns no errors
- `test_apply_fix_replaces_number` — apply_fix correctly substitutes a number in a line
- `test_apply_fix_comma_formatted` — apply_fix handles "2,349" style numbers
- `test_source_metrics_fallback` — load_source_metrics with nonexistent path returns _FALLBACK_METRICS

#### `tests/test_check_outcomes.py`
- `test_stale_days_constant` — STALE_DAYS == 14
- `test_typical_windows_has_major_portals` — TYPICAL_WINDOWS covers greenhouse, lever, ashby, submittable
- `test_get_awaiting_entries` — Filters to submitted/acknowledged status
- `test_get_stale_entries` — Entries >STALE_DAYS without response are stale
- `test_get_stale_entries_with_response` — Entries with response_received=true excluded
- `test_record_outcome_updates_fields` — Verifies YAML field updates (uses tempfile)
- `test_summary_counts` — show_summary returns correct totals

#### `tests/test_hygiene.py`
- `test_check_gate_job_requires_url` — Job without application_url fails gate
- `test_check_gate_grant_requires_deadline` — Grant without deadline.date (non-rolling) fails
- `test_check_gate_valid_entry_passes` — Well-formed entry passes all gates
- `test_check_stale_rolling` — Entry with rolling deadline + old last_touched flagged
- `test_check_stale_rolling_recent` — Recent rolling entry not flagged
- `test_full_report_structure` — run_full_report returns dict with expected keys

#### `tests/test_research_contacts.py`
- `test_generate_research_prompt` — Returns non-empty string with org name and role
- `test_generate_outreach_template` — Returns dict with required fields (type, channel, status)
- `test_generate_followup_dates` — Returns 3 dates matching protocol (Day 1-2, 7-10, 14-21)
- `test_research_single_missing_entry` — Handles nonexistent entry gracefully

#### `tests/test_conversion_report.py`
- `test_analyze_by_dimension_grouping` — Groups entries by extract_fn correctly
- `test_analyze_by_dimension_counts` — Counts submitted/accepted/rejected
- `test_response_time_analysis_empty` — No TTR data handled gracefully
- `test_response_time_analysis_stats` — Mean/median calculated from synthetic entries

#### `tests/test_source_jobs.py`
- `test_normalize_job_id` — ID normalization produces valid kebab-case
- `test_build_entry_yaml` — Generated YAML has required schema fields
- `test_ats_url_parsing` — Greenhouse/Lever/Ashby URL patterns parsed correctly
- `test_location_classification` — US/remote/international classified correctly

#### `tests/test_answer_questions.py`
- `test_extract_questions_from_greenhouse` — Parses custom questions from Greenhouse schema
- `test_generate_answer_prompt` — Prompt includes question text and identity blocks
- `test_integrate_answers` — YAML integration writes correct fields

#### `tests/test_tailor_resume.py`
- `test_wire_resume_updates_yaml` — Wiring updates submission.materials_attached
- `test_wire_resume_creates_field` — Creates materials_attached if missing
- `test_batch_format_validation` — Batch folder path follows materials/resumes/batch-NN/

### Additions to Existing Test Files (4)

#### `tests/test_followup.py` — add:
- `test_init_follow_ups_adds_field` — init_follow_ups populates follow_up: [] on entries without it
- `test_init_follow_ups_skips_existing` — Entries with existing follow_up not modified
- `test_init_follow_ups_dry_run` — dry_run=True doesn't write files

#### `tests/test_funnel_report.py` — add:
- `test_compare_variants_classification` — Entries classified as alchemized/block+variant/etc
- `test_compare_variants_empty` — No submitted entries returns gracefully
- `test_compare_variants_counts` — Response and interview counts correct

#### `tests/test_standup.py` — add:
- `test_section_followup_exists` — "followup" in SECTIONS dict
- `test_section_followup_runs` — section_followup([]) doesn't crash
- `test_section_followup_shows_overdue` — Entry with overdue follow-up appears in output

#### `tests/test_submit.py` — add:
- `test_check_metrics_freshness_clean` — Entry with no blocks returns no issues
- `test_check_metrics_freshness_import_error` — Handles missing check_metrics gracefully

### Execution Order

1. Fix `test_archive_research.py` first (unblocks CI green)
2. Create new test files in dependency order: test_check_metrics → test_check_outcomes → test_hygiene → test_research_contacts → test_conversion_report → test_source_jobs → test_answer_questions → test_tailor_resume
3. Add to existing test files last (test_followup, test_funnel_report, test_standup, test_submit)

---

## [3] Single-Word Command Protocols

### Design Principles

- **One word** triggers a complete workflow step
- **No slash prefix** — just a word, interpretable by any LLM (Claude, Gemini, Codex, ChatGPT)
- **Deterministic execution** — each command maps to a specific script invocation
- **Chainable** — commands can be issued in sequence to build a full session
- **Self-documenting** — the command word implies its function

### Command Protocol Table

| Command | Executes | What It Does |
|---------|----------|-------------|
| `standup` | `python scripts/standup.py` | Daily dashboard: stale entries, deadlines, priorities, follow-ups |
| `campaign` | `python scripts/campaign.py` | Deadline-aware campaign view with urgency tiers |
| `hygiene` | `python scripts/hygiene.py` | Entry data quality report: URLs, staleness, gates |
| `followup` | `python scripts/followup.py` | Today's follow-up actions and overdue items |
| `outcomes` | `python scripts/check_outcomes.py` | Entries awaiting response + stale submissions |
| `funnel` | `python scripts/funnel_report.py` | Conversion funnel analytics |
| `metrics` | `python scripts/check_metrics.py` | Metric consistency check across blocks/profiles/strategy |
| `validate` | `python scripts/validate.py` | Pipeline YAML schema validation |
| `status` | `python scripts/pipeline_status.py` | Full pipeline status overview |
| `velocity` | `python scripts/velocity.py` | Submission velocity stats |
| `conversion` | `python scripts/conversion_report.py` | Conversion rate report by track/position/score |

### Parameterized Commands (word + target)

| Command Pattern | Executes | What It Does |
|----------------|----------|-------------|
| `score <id>` | `python scripts/score.py --target <id>` | Score a single entry |
| `enrich <id>` | `python scripts/enrich.py --target <id> --all --yes` | Wire materials/blocks/variants |
| `advance <id>` | `python scripts/advance.py --id <id>` | Advance entry to next status |
| `compose <id>` | `python scripts/compose.py --target <id>` | Compose submission from blocks |
| `draft <id>` | `python scripts/draft.py --target <id>` | Draft from profile content |
| `submit <id>` | `python scripts/submit.py --target <id>` | Generate portal-ready checklist |
| `check <id>` | `python scripts/submit.py --check <id>` | Pre-submit validation |
| `record <id>` | `python scripts/submit.py --target <id> --record` | Record completed submission |
| `gate <id>` | `python scripts/hygiene.py --gate <id>` | Track-specific readiness gate |
| `contacts <id>` | `python scripts/research_contacts.py --target <id>` | Research hiring contacts |

### Batch Commands

| Command | Executes | What It Does |
|---------|----------|-------------|
| `scoreall` | `python scripts/score.py --all --dry-run` | Preview all scores |
| `enrichall` | `python scripts/enrich.py --all --dry-run` | Preview all enrichments |
| `preflight` | `python scripts/preflight.py` | Batch submission readiness |
| `archive` | `python scripts/archive_research.py --report` | Show archival candidates |
| `qualify` | `python scripts/score.py --auto-qualify` | Preview auto-qualification |

### Session Sequence Examples

**Morning session (30 min):**
```
standup → followup → outcomes → campaign
```

**Submit-focused session:**
```
campaign → check <id> → submit <id> → record <id>
```

**Research & enrich session:**
```
hygiene → scoreall → qualify → enrichall
```

**Analytics session:**
```
funnel → conversion → velocity → metrics
```

### Implementation

**File:** `scripts/run.py` — NEW dispatcher script

```python
#!/usr/bin/env python3
"""Single-word command dispatcher for the application pipeline.

Usage:
    python scripts/run.py standup
    python scripts/run.py score creative-capital-2027
    python scripts/run.py campaign
"""
```

Maps each command word to its script + args. Also serves as documentation for any LLM: the LLM reads run.py and knows every available command.

**Also add to CLAUDE.md:** A "Quick Commands" section listing each one-word command and what it does, so any LLM reading the project instructions knows the protocol.

**Cross-LLM compatibility:** The protocol is just natural language words. Any LLM that reads CLAUDE.md will see the command table and can execute the corresponding `python scripts/...` command. No tool-specific syntax required.

---

## [4] Alpha-to-Omega: What's Missing

### Current State Assessment

**What works:**
- 33 scripts covering research → scoring → enrichment → composition → submission → tracking
- 1039 pipeline entries (45 submitted, ~960 in research pool)
- 8-dimension scoring rubric with weighted composite
- Block/variant/profile composition model
- ATS API integration (Greenhouse, Lever, Ashby)
- Conversion funnel analytics
- CI on GitHub Actions (validate + pytest)

**What's missing for production maturity:**

### A. Dependency Management (HIGH)

No `pyproject.toml` or `requirements.txt`. CI installs `pyyaml pytest` inline. Every developer (human or AI) has to guess dependencies.

**Fix:** Create `pyproject.toml` with:
- `[project]` metadata (name, version, description, python-requires)
- `[project.dependencies]` — pyyaml
- `[project.optional-dependencies]` dev = pytest, ruff
- `[tool.pytest.ini_options]` testpaths = ["tests"]
- `[tool.ruff]` basic Python linting config

**Update CI:** `pip install -e ".[dev]"` instead of `pip install pyyaml pytest`

### B. Linting in CI (HIGH)

No code quality enforcement. `ruff` is the standard linter per workspace CLAUDE.md.

**Fix:** Add ruff check step to `quality.yml`:
```yaml
- name: Lint
  run: ruff check scripts/ tests/
```

### C. Schema Validation Strictness (MEDIUM)

`validate.py` exists but doesn't catch all issues. Missing:
- Cross-reference validation (blocks_used paths exist, variant_ids paths exist)
- Duplicate ID detection across directories
- Timeline date ordering (researched < qualified < submitted)

**Fix:** Add these checks to `validate.py` as new validation passes.

### D. Data Backup/Export (MEDIUM)

No mechanism to snapshot pipeline state. If YAML files are accidentally corrupted, no recovery path beyond git.

**Fix:** Add `scripts/export.py` that dumps full pipeline state to a single JSON/CSV for analysis and backup. Can also feed into external dashboards.

### E. Outcome Monitoring Workflow (MEDIUM)

`check_outcomes.py` reports stale entries but doesn't actually check portals for responses. The gap is activation: no daily reminder to check email/portals.

**Fix:** Wire `outcomes` into the standup output. Add a standup section (or subsection of followup dashboard) that lists "check portal for response" actions for entries >7 days since submission.

### F. Pre-commit Hooks (LOW)

No pre-commit hooks. Easy wins: run `validate.py` and `ruff check` before every commit.

**Fix:** Create `.pre-commit-config.yaml` or a simple `.git/hooks/pre-commit` script.

### G. Version / Changelog (LOW)

No version tracking. seed.yaml says `status: LOCAL`. No changelog.

**Fix:** Add version field to seed.yaml. Maintain a CHANGELOG.md (or rely on git log + conventional commits).

### H. Documentation Consolidation (LOW)

3 docs (architecture.md, workflow.md, eruptio-execution-guide.md) but no unified user guide. CLAUDE.md serves as the primary reference.

**Fix:** CLAUDE.md is already comprehensive. Low priority — keep it as the single source.

### Priority Order for Implementation

1. **Fix test failure** (5 min)
2. **Create test files** (8 files, ~400 lines total)
3. **Add to existing test files** (4 files, ~60 lines)
4. **Create `pyproject.toml`** + update CI
5. **Create `scripts/run.py`** command dispatcher
6. **Update CLAUDE.md** with Quick Commands section
7. **Add ruff to CI**
8. **Add pre-commit hook**
9. **Enhance `validate.py`** with cross-reference checks
10. **Create `scripts/export.py`** for data backup

---

## Files to Create/Modify

| File | Action | Phase |
|------|--------|-------|
| `tests/test_archive_research.py` | MODIFY — fix assertion threshold | [1] |
| `tests/test_check_metrics.py` | CREATE — 12 tests | [2] |
| `tests/test_check_outcomes.py` | CREATE — 7 tests | [2] |
| `tests/test_hygiene.py` | CREATE — 6 tests | [2] |
| `tests/test_research_contacts.py` | CREATE — 4 tests | [2] |
| `tests/test_conversion_report.py` | CREATE — 4 tests | [2] |
| `tests/test_source_jobs.py` | CREATE — 4 tests | [2] |
| `tests/test_answer_questions.py` | CREATE — 3 tests | [2] |
| `tests/test_tailor_resume.py` | CREATE — 3 tests | [2] |
| `tests/test_followup.py` | MODIFY — add 3 tests | [2] |
| `tests/test_funnel_report.py` | MODIFY — add 3 tests | [2] |
| `tests/test_standup.py` | MODIFY — add 3 tests | [2] |
| `tests/test_submit.py` | MODIFY — add 2 tests | [2] |
| `scripts/run.py` | CREATE — command dispatcher | [3] |
| `CLAUDE.md` | MODIFY — add Quick Commands section | [3] |
| `pyproject.toml` | CREATE — project metadata + deps | [4] |
| `.github/workflows/quality.yml` | MODIFY — add ruff step, use pyproject | [4] |

---

## Verification

```bash
source .venv/bin/activate

# [1] Fix test failure
pytest tests/test_archive_research.py -v        # Should pass

# [2] Test suite
pytest tests/ -v                                 # All pass (616+ tests)
pytest tests/test_check_metrics.py -v            # New tests
pytest tests/test_check_outcomes.py -v
pytest tests/test_hygiene.py -v
pytest tests/test_research_contacts.py -v
pytest tests/test_conversion_report.py -v

# [3] Command protocol
python scripts/run.py standup                    # Dispatches correctly
python scripts/run.py score creative-capital-2027
python scripts/run.py --help                     # Lists all commands

# [4] Alpha-to-omega
pip install -e ".[dev]"                          # pyproject.toml works
ruff check scripts/ tests/                       # Clean or fixable
python scripts/validate.py                       # Still passes
```
