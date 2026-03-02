# Evaluation-to-Growth: Codebase Study v2

**Date:** 2026-03-02
**Scope:** Full codebase post-Tier 0-3 implementation
**Method:** 7-agent parallel exhaustive audit across 30+ scripts, 41 test files

---

## Phase 1: Evaluation (Critique + Logic Check)

### Critical Bugs (Tier 0 — Fix Immediately)

| # | File:Line | Issue | Impact |
|---|-----------|-------|--------|
| C1 | `pipeline_lib.py:191-219` | `update_yaml_field()` injects `new_value` into `re.sub` replacement string unsanitized — backslash sequences (`\1`, `\g<1>`) interpreted as backreferences | Silent YAML corruption if any value contains backslashes |
| C2 | `alchemize.py:896-935` | `update_pipeline_yaml()` uses `yaml.dump()` for full-file rewrite — destroys all comments, blank lines, quoting, key order | Mangles every pipeline YAML it touches |
| C3 | `hygiene.py:171` | `live_ids` stores Greenhouse job IDs as `int` (from JSON), but `_extract_greenhouse_job_id` returns `str` — type mismatch means `job_id in live_ids` is always `False` | ATS posting verification for Greenhouse is completely broken |
| C4 | `score.py:1215` | `run_qualify()` calls `qualify(data)` without passing `all_entries` — every entry triggers a full `load_entries()` reload inside `compute_human_dimensions` | O(N^2) YAML parsing; unusable at scale |
| C5 | `tailor_resume.py:282+` | All `re.sub` replacement strings use f-string interpolation of AI-generated HTML — backslash sequences in content interpreted as backreferences | Resume HTML corruption |
| C6 | `answer_questions.py:287-302` | Same `re.sub` backreference injection as C1/C5 in answer integration | Answer file corruption |
| C7 | `enrich.py:155-158,201-207,298-303` | Regex replacement generates wrong indentation — list items at same level as parent key instead of nested under it | Enrichment silently fails for any nested YAML field (YAML validation catches it, but no enrichment happens) |
| C8 | `conversion_report.py:89` | `ttr <= 0` filter discards valid same-day responses (`ttr = 0`) | Response time statistics exclude same-day responses |
| C9 | `check_outcomes.py:268` | `outcome_note` appended at EOF with 2-space indentation instead of inside `conversion:` block | Creates malformed YAML structure |
| C10 | `score.py:1574,1605` | `old_score` from `fit.get("score")` not type-coerced — string YAML values cause `TypeError` on subtraction | Crash when YAML score is quoted string |

### High-Priority Bugs (Tier 0.5)

| # | File:Line | Issue | Impact |
|---|-----------|-------|--------|
| H1 | `pipeline_lib.py:83,86-110` | `"withdrawn"` appears in VALID_TRANSITIONS as target but absent from VALID_STATUSES and STATUS_ORDER | State machine inconsistency; validate.py rejects `status: withdrawn` entries |
| H2 | `alchemize.py:56` | Hardcodes `CURRENT_BATCH = "batch-03"` instead of importing from pipeline_lib | Will write to wrong batch when batch-04 is created |
| H3 | `campaign.py:506-508` | Rolling filter excludes `"hard"`, `"window"`, `"soft"` but omits `"fixed"` — entries with `dl_type == "fixed"` leak into rolling section | Fixed-deadline entries shown as rolling |
| H4 | `score.py:1130` | Regex `^(\s+)(score:\s+\S+)` for score line not anchored to `fit:` section — could match wrong YAML block if another section has `score:` | `original_score` inserted in wrong location |
| H5 | `draft.py:442-448` | Greedy regex for replacing `portal_fields:` can consume blank lines between YAML blocks | Joins two YAML blocks together |
| H6 | `draft.py:452-453` | `content.replace("\nconversion:", ...)` replaces ALL occurrences of `\nconversion:` | Corrupts file if "conversion:" appears more than once |
| H7 | `submit.py:321-322` | `filepath.rename()` does not work across filesystems | `OSError` if submitted/ is on different mount |
| H8 | `build_resumes.py:65-68` | Chrome return code never checked — stale PDF from previous run reported as success | False positive on resume build |
| H9 | `ingest_top_roles.py:219-221` | `--max-age` filter includes unknown-date postings despite docstring saying "skips" them | Inverted filter behavior |
| H10 | `standup.py:1097-1103` | `--section log` re-runs `section_health/stale/plan` with stdout output as side effect | User sees unwanted output |
| H11 | `pipeline_lib.py:42-46` | `_detect_current_batch()` uses lexicographic sort — breaks at batch-10+ | Wrong batch detected after batch-09 |
| H12 | `lever_submit.py:461-462` | API key passed as URL query parameter `?key=...` | Key visible in logs/proxy/redirects |

---

## Phase 2: Reinforcement (Logos + Pathos + Ethos)

### Logos (Statistical/Algorithmic Rigor)

| # | File:Line | Issue | Category |
|---|-----------|-------|----------|
| L1 | `funnel_report.py:139-146` | Stage-to-stage conversion conflates "current status index" with "stages actually traversed" — entry that went `submitted->outcome(rejected at resume_screen)` counted as having passed `interview` | LOGIC |
| L2 | `funnel_report.py:322-323` | `n_ack == 0` reports "OK" instead of "INSUFFICIENT DATA" | LOGIC |
| L3 | `velocity.py:100-117` | Funnel uses `timeline` fields, not status progression — entries with `status: submitted` but no `timeline.qualified` create leaky funnel | LOGIC |
| L4 | `score.py:722` | Unknown/missing grant amount treated as "$0 = no cliff risk = 10" — inflates scores for under-researched entries | LOGIC |
| L5 | `score.py:1653` | `recalibrate_weights` floors negative discriminative power to 0.01 — masks anti-predictive dimensions | LOGIC |
| L6 | `alchemize.py:493-499` | Tag matching is substring-based (`if tag in job_lower`) — "ai" matches "maintain", "domain", etc. | LOGIC |
| L7 | `distill_keywords.py:99` | Bigram overlap suppression checks `ug not in combined` against dict keys, not constituent words — suppression never fires | LOGIC |
| L8 | `pipeline_lib.py:838-842` | `recommend_blocks()` normalizes by keyword count — penalizes well-analyzed entries with many keywords | LOGIC |
| L9 | `conversion_report.py:92` | `int(ttr)` truncates float response times — biases statistics downward | LOGIC |
| L10 | `conversion_report.py:115` | `days_waiting` includes `acknowledged` entries that already received a response | LOGIC |

### Pathos (User Experience / Workflow)

| # | File:Line | Issue | Category |
|---|-----------|-------|----------|
| P1 | `run.py:58` | `enrich <id>` always passes `--yes`, bypassing confirmation | SAFETY |
| P2 | `run.py:135` | Extra CLI arguments after target ID silently dropped | UX |
| P3 | `followup.py:122-135` | Overdue actions accumulate forever — 90-day-old entries show 3 OVERDUE actions every run | NOISE |
| P4 | `standup.py:162-168` | Entry can appear in both "at_risk" and "stagnant" lists simultaneously | UX |
| P5 | `standup.py:1237` | Withdrawal reason hardcoded to `strategic_shift` regardless of user input | LOGIC |
| P6 | `validate.py:318` | Deferred without deferral field says "(recommended)" but treated as CI-failing error | UX |
| P7 | `standup.py:674` | Running `--log` twice daily silently replaces first session record | DATA LOSS |
| P8 | `followup.py:208-241` | `log_followup` only searches submitted/ but `show_all()` shows submitted/ + closed/ entries | INCONSISTENCY |

### Ethos (Safety / Security / Data Integrity)

| # | File:Line | Issue | Category |
|---|-----------|-------|----------|
| E1 | `pipeline_lib.py:528-535,578-585` | No path traversal protection on `load_block()`, `load_variant()` — `../../etc/passwd` resolves outside expected directory | SAFETY |
| E2 | `browser_submit.py:145-148` | Temp file for cover letter never cleaned up — sensitive content persists | SAFETY |
| E3 | All submitters | No duplicate submission prevention — running `--submit` twice sends duplicate application | SAFETY |
| E4 | All submitters | No status gate — entries in `research` or `drafting` can be submitted with `--submit` | SAFETY |
| E5 | `source_jobs.py:627-631` | `_yaml_quote` produces invalid YAML when text contains both single and double quotes | SAFETY |
| E6 | `browser_submit.py:460` | CSS selector `#{field_path}` crashes for field paths with dots/brackets | BUG |
| E7 | All scripts | Non-atomic file writes (`filepath.write_text()`) — crash mid-write truncates/corrupts file | SAFETY |

---

## Phase 3: Risk Analysis (Blind Spots + Shatter Points)

### Blind Spots

1. **No "withdrawn" in VALID_STATUSES** — The state machine documents `withdrawn` as a terminal outcome but the code treats it as an `outcome` sub-type. VALID_TRANSITIONS allows transitioning TO "withdrawn" from every status, creating a phantom state.

2. **Datetime vs Date handling** — `parse_date()` silently returns `None` for PyYAML `datetime` objects (from timestamps like `2026-03-01T14:30:00`). Multiple scripts rely on this function for deadline/timeline parsing.

3. **YAML mutation fragility** — The entire codebase uses regex-based YAML field updates to preserve formatting. This is fundamentally fragile: fails on inline values, comments on same line, empty values, different indentation levels. The alternative (`yaml.dump`) destroys formatting. This is the core architectural tension.

4. **Cross-script "submitted" detection** — 5 different scripts use 5 different methods to determine if an entry is "submitted", leading to metric inconsistencies.

5. **`http_request_with_retry()` defined but never used** — Added in Tier 3 but never integrated into any HTTP-calling script.

6. **Test coverage black holes** — `load_block()`, `load_variant()`, `execute_campaign()`, `_record_submission()`, `check_urls()`, `check_postings()`, `auto_expire()` have zero test coverage.

### Shatter Points

1. **`update_yaml_field` regex injection (C1)** — Any caller passing a value with `\1` or `\g<1>` silently corrupts the file. Currently safe because callers pass simple strings, but one new feature could break everything.

2. **`alchemize.py` `yaml.dump` (C2)** — Every call destroys file formatting. Anyone running `alchemize.py --integrate` mangles their pipeline YAML.

3. **Enrichment indentation (C7)** — The enrichment pipeline is silently non-functional for nested YAML fields. The YAML validation guard prevents corruption but means `enrich.py --materials`, `--variants`, `--blocks` all silently fail when the target field is nested under `submission:`.

4. **O(N^2) auto-qualify (C4)** — With 1000+ research_pool entries, `score.py --auto-qualify` would parse YAML files ~1,000,000 times.

---

## Phase 4: Growth (Bloom + Evolve)

### Tier 0: Critical Bug Fixes (13 items)

**C1**: Use lambda replacement in `update_yaml_field`:
```python
re.sub(pattern, lambda m: m.group(1) + new_value, content, count=1, flags=re.MULTILINE)
```

**C2**: Replace `yaml.dump` in `alchemize.py:update_pipeline_yaml` with targeted `update_yaml_field` calls for each modified field.

**C3**: Convert `_extract_greenhouse_job_id` return to `int`:
```python
return int(m.group(1)) if m else None
```

**C4**: Pass `all_entries` through `run_qualify` -> `qualify` -> `compute_dimensions`:
```python
all_raw = _load_entries_raw()
for filepath, data in entries:
    should_apply, reason = qualify(data, all_entries=all_raw)
```

**C5/C6**: Replace f-string interpolation in `re.sub` replacements with lambda functions in `tailor_resume.py` and `answer_questions.py`.

**C7**: Fix `enrich.py` regex replacements to capture parent indentation and compute child indentation dynamically:
```python
match = re.search(r'^(\s*)materials_attached:\s*\[\]', content, re.MULTILINE)
if match:
    indent = match.group(1)
    child_indent = indent + "  "
    replacement = f"{indent}materials_attached:\n{child_indent}- {resume}"
```

**C8**: Change `ttr <= 0` to `ttr < 0` in `conversion_report.py:89`.

**C9**: Fix `check_outcomes.py:268` to insert `outcome_note` inside `conversion:` block using regex anchor.

**C10**: Type-coerce `old_score` in `score.py`:
```python
old_score = float(fit.get("score", 0)) if fit.get("score") is not None else None
```

### Tier 1: High-Priority Fixes (12 items)

**H1**: Add `"withdrawn"` to `VALID_STATUSES` and `STATUS_ORDER` (or remove from VALID_TRANSITIONS targets and document as outcome sub-type).

**H2**: Replace `alchemize.py:56` with `from pipeline_lib import CURRENT_BATCH`.

**H3**: Add `"fixed"` to campaign.py rolling filter exclusion list.

**H4**: Anchor score regex to `fit:` section context in `score.py:1130`.

**H5/H6**: Use `re.sub` with `count=1` for portal_fields and conversion replacements in `draft.py`.

**H7**: Replace `filepath.rename()` with `shutil.move()` in `submit.py:321`.

**H8**: Delete target PDF before Chrome run in `build_resumes.py`, check return code.

**H9**: Fix `--max-age` filter logic in `ingest_top_roles.py`.

**H10**: Separate data collection from printing in standup stats functions.

**H11**: Sort batches by numeric suffix in `_detect_current_batch()`.

**H12**: Move Lever API key from URL query param to Authorization header.

### Tier 2: Logic & Consistency (10 items)

- **L1**: Track actual stage transitions (not just current status) for funnel conversion.
- **L4**: Default unknown grant amounts to score 7 instead of 10.
- **L6**: Use word-boundary matching for tag-to-job matching in alchemize.py.
- **L7**: Fix bigram overlap suppression to check constituent words.
- **L9**: Keep float precision for response time statistics.
- **L10**: Exclude `acknowledged` from "awaiting response" list.
- **P1**: Remove `--yes` from `run.py` enrich command template; require explicit confirmation.
- **P3**: Add follow-up action expiry (e.g., stop showing after 30 days).
- **P4**: Add `continue` after at_risk append in standup.py to prevent double-listing.
- **P6**: Demote deferred-without-deferral from error to warning in validate.py.

### Tier 3: Safety & Architecture (8 items)

- **E1**: Add path traversal guard to `load_block()` and `load_variant()`.
- **E3**: Add duplicate submission check (verify status != submitted) in all ATS submitters.
- **E4**: Add status gate (require status == staged) before submission.
- **E5**: Fix `_yaml_quote` to handle text with both single and double quotes.
- **E7**: Implement write-to-temp-then-rename pattern for critical YAML mutations (advance, score, check_outcomes).
- `parse_date()`: Handle `datetime` objects from PyYAML explicitly.
- Consolidate `VALID_DIMENSIONS`/`DIMENSION_ORDER` into a single constant in pipeline_lib.
- Wire `http_request_with_retry()` into hygiene.py URL checks.

### Tier 4: Test Coverage Expansion (Priority Gaps)

| Priority | Missing Coverage | Script |
|----------|-----------------|--------|
| HIGH | `load_block()`, `load_variant()` | pipeline_lib.py |
| HIGH | `_record_submission()`, `_append_conversion_log()` (real function call) | submit.py |
| HIGH | `check_urls()`, `auto_expire()` | hygiene.py |
| HIGH | `execute_campaign()` | campaign.py |
| MEDIUM | `enrich_portal_fields()` | enrich.py |
| MEDIUM | `--wire` mode | tailor_resume.py |
| MEDIUM | `integrate_answers()` | answer_questions.py |
| LOW | Convert silent `return` skips to `pytest.skip()` | test_enrich.py |
| LOW | Add `tests/fixtures/` for stable synthetic data | systemic |

---

## Implementation Summary

| Tier | Items | Estimated Effort | Risk if Deferred |
|------|-------|-----------------|------------------|
| 0 | 13 critical bugs | ~2 hours | Active data corruption, silent failures |
| 1 | 12 high-priority | ~1.5 hours | Incorrect behavior, stale references |
| 2 | 10 logic fixes | ~1.5 hours | Metric inaccuracy, UX annoyances |
| 3 | 8 safety items | ~2 hours | Path traversal, duplicate submissions |
| 4 | 9 test gaps | ~2 hours | Regression risk |

**Total: 52 items across 5 tiers**
