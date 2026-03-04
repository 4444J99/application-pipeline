# Evaluation-to-Growth: Application Pipeline — Project-Wide Review

*Plan date: 2026-03-01 — Post-test-suite audit focusing on logic, stats, algorithms, and functions*

---

## Context

The pipeline has 903 passing tests, 0 linting issues, and a complete 8-dimension scoring engine backed by market-intelligence-2026.json. This review applies the evaluation-to-growth lens to every script: identify logic errors, statistical weaknesses, algorithm gaps, and systemic blind spots — then plan targeted fixes in priority order.

---

## Phase 1: CRITIQUE — What's Broken or Fragile

### C1 · `followup.py:log_followup()` — YAML structure destruction (lines 206-216)
`yaml.dump(data, ...)` re-serializes the entire file alphabetically, destroying all hand-crafted key ordering, comments, and indentation. Every call to `--log` permanently mangles the entry file structure. **This is a data-integrity bug.**

*Fix:* Replace `yaml.dump` with targeted `update_yaml_field` + raw-text append for the `follow_up` list item.

### C2 · `followup.py:_append_outreach_log()` — Unchecked file open (line 230)
`with open(OUTREACH_LOG)` raises `FileNotFoundError` if `signals/outreach-log.yaml` doesn't exist. No guard, no initialization.

*Fix:* Add `if not OUTREACH_LOG.exists(): OUTREACH_LOG.write_text("entries: []\n")` before open.

### C3 · `velocity.py:deadline_pressure` — Cumulative buckets (lines 134-147)
Buckets `this_week / next_2_weeks / next_month` are NOT exclusive — a 5-day deadline appears in all 3. Inflates every bucket except `this_week`.

*Fix:* Make buckets exclusive: `[0-7]`, `[8-14]`, `[15-30]`.

### C4 · `velocity.py:compute_velocity()` — `"window"` deadlines excluded (line 139)
`dl_type in ("hard", "fixed")` misses `"window"` type. Window deadlines are also time-critical.

*Fix:* `dl_type in ("hard", "fixed", "window")`.

### C5 · `funnel_report.py:compare_variants()` — Interview count logic error (lines 383-385)
`status in ("interview", "outcome") and outcome not in (rejected, expired, withdrawn)` excludes entries that were status=outcome/rejected after a real interview. The interview count should use `timeline.interview` not final outcome.

*Fix:* Count `interviewed` as `bool(entry.get("timeline", {}).get("interview"))`.

### C6 · `funnel_report.py:get_stage_index()` — Deferred treated as "submitted" equivalent (line 72)
`FUNNEL_STAGES` puts "deferred" at index 4, same level as "submitted". A deferred entry at `stage_index=4` is counted in `reached_submitted` calculations, inflating the qualified→submitted conversion rate.

*Fix:* Remove "deferred" from FUNNEL_STAGES entirely (or give it index -0.5 by handling separately).

### C7 · `preflight.py:readiness_score()` — Deadline "safe" threshold too low (line 172)
`d > 3` means 4-day deadlines are "safe". CLAUDE.md sets 7-day urgency. Inconsistency.

*Fix:* `d > 7` to match CLAUDE.md urgency protocol.

### C8 · `validate.py:score range check` — No type guard (line 118)
`if score is not None and not (1 <= score <= 10)` — if score is a YAML string ("7.3"), this throws `TypeError`. `yaml.safe_load` can return strings for unquoted values in some edge cases.

*Fix:* `isinstance(score, (int, float)) and not (1 <= score <= 10)`.

### C9 · `followup.py:show_schedule()` — Exact-day matching only (line 453)
`if low == days_since` only shows a follow-up action on day 7 (the start of window), not on days 8-10. An entry at day 9 would appear "not scheduled" in the 21-day view.

*Fix:* Change to `if low <= days_since <= high`.

### C10 · `enrich.py:CURRENT_BATCH` hardcoded (line 46)
`CURRENT_BATCH = "batch-03"` is hardcoded. When batch-04 is created, this silently continues pointing to batch-03.

*Fix:* Move to `pipeline_lib.py` and auto-detect: `max((MATERIALS_DIR / "resumes").glob("batch-*"), key=lambda p: p.name)`.

---

## Phase 2: LOGIC CHECK — Algorithm Correctness

### L1 · `score.py:score_effort_to_value()` — Coverage denominator hardcoded
`coverage_bonus = min(blocks_count / 6 * 2, 2)` — denominator 6 is arbitrary. `JOB_BLOCKS_BY_IDENTITY["independent-engineer"]` has 5 blocks, so max coverage_bonus for a fully-enriched job entry is `5/6*2 = 1.67`, never reaching 2. The denominator should be the expected block count for the position.

*Fix:* `expected = len(JOB_BLOCKS_BY_IDENTITY.get(position, {})) or 6; coverage_bonus = min(blocks_count / expected * 2, 2)`.

### L2 · `score.py:score_effort_to_value()` — International penalty overapplied
`int_adj = -3 if location_class in ("international", "remote-global") else 0` — remote-global requires no relocation, yet gets same -3 penalty as international (requires visa/travel). These are different risk levels.

*Fix:* `int_adj = -3 if location_class == "international" else (-1 if location_class == "remote-global" else 0)`.

### L3 · `score.py:compute_human_dimensions()` — Hot skills signal checks job title not job requirements
`sum(1 for sk in hot_skills if any(kw in sk for kw in keywords))` — `keywords` comes from the job title, `hot_skills` comes from market intel. The signal fires if a hot skill string appears as a substring of a title keyword. "kubernetes" never appears in any title keyword — the signal almost never fires.

*Fix:* Cross-match hot_skills against `submission.blocks_used` keys OR distilled keywords from `distill_keywords.py` output stored in entry YAML, not title keywords.

### L4 · `score.py:score_strategic_value()` — HIGH_PRESTIGE is binary (one tier only)
All prestige entries get base 8 regardless of actual acceptance rate. Creative Capital (~3% acceptance) and Prix Ars (~5%) and Whiting (~1%) should have differentiated values.

*Fix:* Add `PRESTIGE_TIERS = {"tier1": [..., "whiting", ...], "tier2": [..., "creative-capital", ...], "tier3": [..., "prix-ars", ...]}` with base values 10/9/8.

### L5 · `score.py:score_deadline_feasibility()` — No materials-readiness adjustment
`d ≤ 7 → 5`, `d ≤ 14 → 6` regardless of whether materials are ready. A fully-enriched entry with 14 days should score higher than an empty entry with 14 days.

*Fix:* After computing base feasibility, check `submission.materials_attached` — if populated, add +1 bonus (capped at 9).

### L6 · `pipeline_lib.py:update_yaml_field(nested=True)` — First-match ambiguity
`count=1` updates the first occurrence of an indented `field:` key. If two blocks both have a `date:` nested key (e.g., `deadline.date` and `timeline.date`), calling with `field="date", nested=True` updates whichever appears first in the file.

*Fix:* Add `parent_key` parameter: scope the regex to within the parent block content only.

### L7 · `advance.py:run_report()` — Drafting entries not blocked on missing profile
`blockers.append("no profile")` only fires for `status == "qualified"`. A `drafting` entry without a profile also can't proceed to staged but is shown as "READY".

*Fix:* Add `elif status == "drafting" and not has_profile: blockers.append("no profile")`.

### L8 · `validate.py:check_profile_freshness()` — Only checks repo count
Profiles also contain test counts, word counts, essay counts. A profile with stale `test_count=1095` (vs canonical 2349) passes freshness validation.

*Fix:* Extend to also extract and compare `test_count`, `essay_count`, and `word_count` from metrics-snapshot.md.

---

## Phase 3: LOGOS — Statistical Validity

### S1 · `funnel_report.py:TARGETS` — Stage-index off-by-one
`submitted = sum(1 for e if get_stage_index(status) >= 4)` — Stage 4 is "deferred" (index 4 in FUNNEL_STAGES), not "submitted" (index 5). Submitted count is inflated by all deferred entries.

*Fix:* Resolved by C6 (remove deferred from FUNNEL_STAGES); re-verify all stage indices after fix.

### S2 · `velocity.py:conversion_funnel` — Denominator uses sparse `timeline.researched`
Most entries in research_pool/ don't have `timeline.researched` set. Denominator `max(funnel.get("researched", 0), 1)` defaults to 1 when no researched dates exist, making percentages meaningless.

*Fix:* Use `total_entries = len(entries)` as denominator (all entries loaded, not just those with researched dates).

### S3 · `followup.py:TIER_PRIORITY` — Creative entries all tier 5 (no differentiation)
All creative entries get priority 5 regardless of strategic value (Creative Capital score 9 vs emergency score 7). High-value opportunities aren't prioritized in follow-up ordering.

*Fix:* Use `fit.score` as tiebreaker: `actions.sort(key=lambda x: (x["tier"], -x.get("score", 5.0), -x["day"]))`.

### S4 · `velocity.py:weekly_velocity` — Old submissions silently discarded
`all_weeks[-8:]` silently drops data older than 8 weeks. Slow periods and campaign gaps are invisible.

*Fix:* Show all weeks with non-zero activity; for gaps > 2 weeks, emit a `--- [N weeks inactive] ---` marker.

---

## Phase 4: PATHOS — Usability / Human Experience

### P1 · `preflight.py` — `sys.exit(1)` on any issue blocks CI
`"no portfolio_url set"` is chronic for most entries and causes every preflight run to report failure, desensitizing to real issues.

*Fix:* Distinguish `ERROR` (file not found, expired deadline, missing application_url) from `WARN` (no portfolio_url, using base resume). Only `exit(1)` on errors.

### P2 · `advance.py` — No warning when skipping stages
`qualified → staged` silently skips drafting. User advancing without compose/draft has no signal.

*Fix:* Print `[WARN] Skipping drafting stage — run compose.py before submitting` when advancing more than one step forward.

### P3 · `standup.py` — Follow-up overdue count not in default output
Overdue outreach is only visible with `--section followup`. Critical daily action hidden behind flag.

*Fix:* Include condensed follow-up summary (overdue count + due today) in the default standup header section.

---

## Phase 5: ETHOS — Consistency and Trustworthiness

### E1 · Three incompatible YAML mutation strategies
- `pipeline_lib.update_yaml_field()` — regex surgery preserving format
- `followup.log_followup()` — `yaml.dump()` full re-serialize (destroys format)
- `enrich.py` — direct `re.sub` regex substitution

*Fix:* After C1 fix, standardize all pipeline YAML mutations to use `update_yaml_field` + raw-text append. Audit all scripts for `yaml.dump(data, f, ...)` writes to pipeline files.

### E2 · `CURRENT_BATCH` defined in 2 script files
`enrich.py:46` and `tailor_resume.py` both hardcode `"batch-03"`. They can drift.

*Fix:* Single definition in `pipeline_lib.py` with auto-detection (resolved by C10).

### E3 · `pipeline_lib.load_entries()` silently skips invalid YAML
Bad YAML files are dropped with no log. Corrupted entries disappear silently.

*Fix:* `print(f"[WARN] Skipping unparseable entry: {filepath}", file=sys.stderr)`.

### E4 · Block validation doesn't check frontmatter
`validate.py` confirms block paths exist but not that they have valid frontmatter (required: title, category, tags, identity_positions, tracks, tier). Missing `tier` produces wrong compose behavior silently.

*Fix:* Add `validate_block_frontmatter(block_path)` call for each `blocks_used` path in `validate_entry()`.

---

## Phase 6: BLIND SPOTS — What's Not Being Tracked

### B1 · No framing-level A/B tracking
`--compare-variants` classifies by composition method, not by *which specific framing block* was used. Can't determine if `framings/independent-engineer` converts better than `framings/creative-technologist`.

*Opportunity:* Add `conversion.framing_used` field populated in `submit.py --record`. New `--by framing` dimension in `funnel_report.py`.

### B2 · No salary extraction from job postings
`source_jobs.py` ingests job postings without extracting salary ranges. All unknown-salary jobs default to `financial_alignment = 5`.

*Opportunity:* Add regex salary extraction in `source_jobs.py` → `amount.value` + `amount.max_value`.

### B3 · No time-to-response tracking
`timeline.submitted` and `timeline.acknowledged` are both tracked but `response_time_days` is never computed. Response time patterns reveal channel quality.

*Opportunity:* Compute `metrics.response_time_days` in `check_outcomes.py`.

### B4 · No resume version at submission time
`materials_attached` records path but not version/hash. Historical "which resume was used" is lost when files are updated.

*Opportunity:* Store SHA256 hash of resume file at `submit --record` time in `conversion.resume_hash`.

### B5 · Cover letter gap detection depends on hardcoded map
`COVER_LETTER_MAP` has 4 entries. Variants in `variants/cover-letters/` that aren't in the map are undetected.

*Opportunity:* Add `enrich.py --scan-variants` to auto-populate COVER_LETTER_MAP from filesystem scan.

### B6 · Keyword-to-block gap not surfaced in preflight
`distill_keywords.py --match-tags` shows which requirements have matching blocks, but this output isn't integrated into preflight check. Gaps are invisible at submission time.

*Opportunity:* Run keyword→block gap analysis in `check_entry()` if keywords extracted.

---

## Phase 7: SHATTER POINTS — Single Points of Failure

### SP1 · `blocks/_index.yaml` — Silent degradation if missing
`load_block_index()` returns `{}` without any error or warning. Multiple scripts that depend on it silently degrade.

*Fix:* Emit `[WARN] blocks/_index.yaml not found — run build_block_index.py` to stderr.

### SP2 · `market-intelligence-2026.json` — Partial corruption propagates silently
All market-derived scores have `try/except` fallbacks to hardcoded defaults. Partial corruption (loads but wrong schema) bypasses the fallback, propagating wrong values silently.

*Fix:* Add schema validation in `market_intel.py` (verify required keys and types).

### SP3 · `update_yaml_field()` regex surgery can corrupt valid files
Regex could match comment lines or string values containing a field name. Post-update `yaml.safe_load` is the only safeguard; semantically wrong (but valid YAML) passes.

*Fix:* Add smoke-test assertions in the test suite verifying key fields survive round-trips through each mutation function.

### SP4 · No backup before batch operations
`advance --yes`, `enrich --yes`, `score --all` modify potentially hundreds of files with no backup.

*Fix:* Add `--backup` flag that snapshots modified files to `pipeline/.backup/{timestamp}/` before writing.

---

## Phase 8: BLOOM — Growth Opportunities

### G1 · Score confidence interval
Signal-based scores are deterministic but not calibrated. Scores of 7.3 vs 7.2 are treated as meaningfully different. Adding `fit.score_confidence` ("low" / "medium" / "high" based on data completeness: blocks wired, profile exists, portal_fields populated) prevents over-reliance on micro-differences.

### G2 · Automated follow-up template generation
`followup.py` tells *what* to do but not *what to say*. `--generate <entry_id>` could produce a template DM from the entry's profile + position context.

### G3 · `funnel_report.py --by score_tier` breakdown
Tiers: `[<5.0, 5.0-6.5, 6.5-7.5, 7.5-9.0, 9.0+]`. This validates the scoring rubric — if high-scoring entries convert at materially higher rates, the rubric is predictive. If not, it needs recalibration.

### G4 · Predictive deadline clustering
`campaign.py --predict` could cluster entries by "natural submission date" based on effort level + available time budget, projecting a realistic weekly schedule with workload balancing.

---

## Implementation Sprints

### Sprint A — Critical Bugs (1-2 hours)

| Fix | File | Description |
|-----|------|-------------|
| C2 | `followup.py` | Guard `_append_outreach_log()` against missing file |
| C3 | `velocity.py` | Make deadline buckets exclusive |
| C4 | `velocity.py` | Add `"window"` to deadline pressure types |
| C8 | `validate.py` | Add `isinstance` guard on score range check |
| C9 | `followup.py` | Fix `show_schedule()` to use window range |
| E3 | `pipeline_lib.py` | Log skipped unparseable YAML files |

### Sprint B — Logic Fixes (2-3 hours)

| Fix | File | Description |
|-----|------|-------------|
| C1 | `followup.py` | Replace `yaml.dump` with targeted text mutation |
| C5 | `funnel_report.py` | Fix `interviewed` count to use `timeline.interview` |
| C6 | `funnel_report.py` | Remove "deferred" from FUNNEL_STAGES |
| C7 | `preflight.py` | Fix readiness_score deadline threshold to 7d |
| L2 | `score.py` | Split international vs remote-global penalty |
| L7 | `advance.py` | Add missing profile blocker for drafting entries |
| P1 | `preflight.py` | Split ERROR vs WARN; only exit(1) on errors |

### Sprint C — Statistical Accuracy (3-4 hours)

| Fix | File | Description |
|-----|------|-------------|
| L1 | `score.py` | Dynamic coverage denominator by position's expected blocks |
| L3 | `score.py` | Fix hot-skills signal to use blocks/keywords not title |
| L4 | `score.py` | Tier HIGH_PRESTIGE dict with differentiated bases |
| L5 | `score.py` | Materials-readiness +1 bonus to deadline_feasibility |
| S2 | `velocity.py` | Use total entry count as funnel denominator |
| S3 | `followup.py` | Use `fit.score` as follow-up tier tiebreaker |
| S4 | `velocity.py` | Show all weeks with gap markers |

### Sprint D — Architecture Hygiene (1-2 hours)

| Fix | File | Description |
|-----|------|-------------|
| C10/E2 | `pipeline_lib.py` | Add auto-detecting `CURRENT_BATCH` constant |
| L6 | `pipeline_lib.py` | Add `parent_key` scope to `update_yaml_field` |
| L8 | `validate.py` | Extend freshness check to test/essay/word counts |
| E4 | `validate.py` | Add block frontmatter validation |
| SP1 | `pipeline_lib.py` | Warn if `blocks/_index.yaml` missing |
| SP2 | `market_intel.py` | Schema validation on JSON load |

### Sprint E — Growth Features (4-6 hours, optional)

| Fix | File | Description |
|-----|------|-------------|
| B1 | `submit.py` + `funnel_report.py` | `conversion.framing_used` + `--by framing` |
| B2 | `source_jobs.py` | Regex salary extraction → `amount.value` |
| B3 | `check_outcomes.py` | Compute `metrics.response_time_days` |
| B5 | `enrich.py` | Add `--scan-variants` filesystem auto-population |
| G3 | `funnel_report.py` | Add `--by score_tier` breakdown |
| P2 | `advance.py` | Warn when skipping stages |
| SP4 | `advance.py`, `enrich.py`, `score.py` | Add `--backup` flag |

---

## Critical Files

- `scripts/score.py` — L1, L2, L3, L4, L5 fixes
- `scripts/followup.py` — C1, C2, C9, S3 fixes
- `scripts/velocity.py` — C3, C4, S2, S4 fixes
- `scripts/funnel_report.py` — C5, C6, S1 fixes
- `scripts/preflight.py` — C7, P1 fixes
- `scripts/validate.py` — C8, L8, E4 fixes
- `scripts/pipeline_lib.py` — L6, E2, E3, C10, SP1 fixes
- `scripts/enrich.py` — C10 (moved constant) + B5
- `scripts/advance.py` — L7, P2 fixes
- `scripts/market_intel.py` — SP2 validation

---

## Verification

After each sprint:

```bash
# Schema + block validation
python scripts/validate.py --check-freshness

# Metric consistency
python scripts/check_metrics.py

# Full test suite (903 baseline)
pytest tests/ -v

# Scoring sanity (one entry per track type)
python scripts/score.py --explain --target prix-ars-electronica
python scripts/score.py --explain --target cohere-applied-ai-engineer-agentic-workflows-korea
python scripts/score.py --explain --target creative-capital-2027

# Follow-up YAML integrity (verify no structure destruction after log)
python scripts/validate.py

# Funnel accuracy check
python scripts/funnel_report.py
python scripts/funnel_report.py --targets
python scripts/velocity.py

# Confirm deadline buckets don't double-count
python scripts/velocity.py | grep -A4 "Deadline"
```

**Acceptance criteria:**
- All 903 tests still passing
- `validate.py` reports 0 errors
- `check_metrics.py` reports 0 inconsistencies
- `followup.py --log` produces valid formatted YAML (no key reordering)
- `velocity.py` deadline buckets sum correctly (no double-counting)
- `funnel_report.py` deferred entries not counted as "submitted"
- `preflight.py` exits 0 for entries with only WARN-level issues
