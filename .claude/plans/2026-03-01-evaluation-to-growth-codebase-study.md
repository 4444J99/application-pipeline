# Evaluation-to-Growth: Application Pipeline Full Codebase Study

**Mode**: Autonomous | **Output**: Markdown Report
**Scope**: All scripts, algorithms, statistics, functions — exhaustive
**Date**: 2026-03-01

---

## Phase 1: Evaluation

### 1.1 Critique

#### Strengths

1. **Single source of truth for state machine** — `VALID_TRANSITIONS` in `pipeline_lib.py` is imported by both `validate.py` and `advance.py`. The transition graph is sound: no state-skipping without explicit guard (e.g., `qualified -> staged` is allowed but warns about skipping `drafting`).

2. **Scoring rubric-to-code fidelity** — All 8 dimension weights, both track-specific weight sets, all 12 signal functions, the credential matrix (4×8), affinity matrix (8×5), role-fit tiers (4 tiers), and qualification thresholds (5.0/5.5) match `strategy/scoring-rubric.md` exactly. Both weight sets sum to 1.0.

3. **Benefits-cliff-aware financial scoring** — The counterintuitive inversion (higher grant amounts score *lower*) is a genuinely sophisticated signal for the user's precarity-aware pipeline. SNAP ($20,352), Medicaid ($21,597), and Essential Plan ($39,125) thresholds are correctly coded.

4. **Three-layer content composition model** — blocks → profiles → legacy scripts with clear fallback chains in `compose.py` and `draft.py`. The `LENGTH_PREFERENCE` cascade (`short → [short, medium, long]`) is well-designed.

5. **Market intelligence integration** — `market-intelligence-2026.json` feeds runtime overrides into `score.py`, `standup.py`, `campaign.py`, and `followup.py` with hardcoded fallbacks when the JSON is missing. Zero-breaking-change design.

6. **Effort-aware urgency** — `campaign.py` loads per-effort urgency thresholds from market intel, so a `complex` (12-hour) entry gets flagged as urgent 14 days out instead of 7. This is the most sophisticated scheduling logic in the codebase.

7. **Format-preserving YAML mutation** — `update_yaml_field()` uses regex to modify individual fields while preserving comments, key order, and quoting. Post-mutation validation via `yaml.safe_load()` catches corruption.

8. **Comprehensive validation** — `validate.py` checks 19 dimensions: YAML parseability, ID-filename match, track/status/outcome/deadline-type/amount-type enums, fit score range, effort level, timeline consistency (via BFS reachability), portal-URL cross-check, block existence + frontmatter completeness, last_touched format, outreach/recommendations/portal_fields/deferral/withdrawal enums.

#### Weaknesses

1. **Three separate status progression definitions** that could diverge:
   - `pipeline_lib.py`: `VALID_TRANSITIONS` (authoritative graph)
   - `advance.py`: `_STATUS_ORDER` list (skip-detection only)
   - `standup.py`: `NEXT_STATUS` dict (triage mode — does NOT consult `VALID_TRANSITIONS`)

2. **The `check_entry()` tuple bug affects 2 scripts** — `preflight.check_entry()` returns `(errors, warnings)` but both `standup.py:section_readiness()` and `campaign.py:run_execute()` treat it as a flat list. A 2-element tuple is always truthy, so `if issues:` always fires and `len(issues)` always returns 2 regardless of actual error count.

3. **Massive code duplication across ATS submitters** — `resolve_cover_letter()` is copied in 6 files. `resolve_resume()` in 3. `load_config()` in 4. `auto_fill_answers()` in 3. `merge_answers()` in 3. The entire answer lifecycle (load/merge/validate/generate_template/init/check) is reimplemented identically in `greenhouse_submit.py`, `lever_submit.py`, and `ashby_submit.py`.

4. **Two inconsistent YAML mutation strategies** — Most scripts use `update_yaml_field()` (regex, format-preserving). But `standup.py:touch_entry()` uses `yaml.safe_load() + yaml.dump()` (destructive reformat), and `alchemize.py:update_pipeline_yaml()` does the same. These destroy comments and field ordering.

5. **Silent failure as default error mode** — `enrich_materials()`, `enrich_variant()`, `enrich_blocks()`, `record_outcome()`'s field updates, `write_keywords_to_entry()`, and `advance_entry()`'s timeline update all silently swallow failures (return `False` or `pass` on `ValueError`).

6. **No retry logic anywhere** — All HTTP interactions (Greenhouse, Lever, Ashby APIs, web scraping) are single-attempt with no exponential backoff. Transient 429/5xx errors cause hard failures.

7. **Inconsistent funnel definitions across 3 scripts** — `funnel_report.py` measures by current-status ordinal comparison, `velocity.py` by timeline-timestamp presence, `conversion_report.py` by status-set membership. The same dataset produces different funnel numbers in each.

#### Priority Areas (Ranked)

| Priority | Issue | Impact | Scripts Affected |
|----------|-------|--------|-----------------|
| P0 | `check_entry()` tuple bug | Wrong output in 2 dashboard scripts | standup.py, campaign.py |
| P0 | Triage mode bypasses `VALID_TRANSITIONS` | State machine violations | standup.py |
| P1 | 6-file `resolve_cover_letter()` duplication | Maintenance burden, drift risk | 6 scripts |
| P1 | Score-4 gap in deadline feasibility | Non-uniform scoring scale | score.py |
| P1 | Silent failure on YAML mutations | Lost data with no feedback | 5+ scripts |
| P2 | Inconsistent funnel definitions | Conflicting analytics | 3 scripts |
| P2 | `touch_entry()` destructive YAML reformat | Comment/formatting destruction | standup.py |
| P2 | No weight validation | Could silently break scoring | score.py |
| P3 | No HTTP retry logic | Fragile API submissions | 4 scripts |
| P3 | Score threshold hardcoding in archive_research | Threshold drift | archive_research.py |

---

### 1.2 Logic Check

#### Contradictions Found

1. **`advance.py` blocks post-submission transitions but `VALID_TRANSITIONS` allows them.** Line 224 requires `current in ACTIONABLE_STATUSES or current == "deferred"`, filtering out `submitted → acknowledged`, `acknowledged → interview`, etc. — even though these are valid transitions. The transitions exist in `check_outcomes.py` instead, but this creates an undocumented split where different scripts own different parts of the state machine.

2. **`deferred → drafting` is impossible.** `VALID_TRANSITIONS["deferred"]` = `{staged, qualified, withdrawn}`. An entry deferred from `drafting` can only return to `qualified` or `staged`, never back to `drafting`. This is a semantic gap — the entry's actual state before deferral is lost.

3. **`_expire_entry()` bypasses `VALID_TRANSITIONS`.** `hygiene.py` directly sets `status: outcome` regardless of current state, including entries in `research` status (which can only reach `qualified` or `withdrawn` per the transition graph). Auto-expiration creates an implicit `research → outcome` edge that the state machine doesn't sanction.

4. **`browser_submit.py` records submission even when submit button not found.** `record_submission()` is called even when `submitted` is `False` (line ~340). The entry moves to `submitted/` despite never being actually submitted.

5. **`check_outcomes.py` accepts outcomes for any status.** You can `--record rejected` on a `research`-status entry. No guard checks that the entry was ever submitted.

#### Reasoning Gaps

1. **Cumulative funnel conflates "current status >= X" with "passed through X".** `funnel_report.py`'s `get_stage_index()` assigns ordinals, then counts entries where `stage_index >= i`. An entry that jumped from `research` directly to `staged` (skipping `qualified` and `drafting`) is counted as having passed through all intermediate stages.

2. **`run_auto_qualify` uses stale stored scores.** Line 1283 reads `entry.get("fit", {}).get("score", 0)` — the YAML-persisted score, not the freshly computed one from `qualify()`. If scores were recomputed but not yet written, the `min_score` filter operates on outdated data.

3. **Campaign rolling-section filter is inverted.** `generate_campaign_markdown()` line 500: `not (get_deadline(e)[0] and get_deadline(e)[1] in ("hard", "window", "soft"))` includes entries with `type: fixed` in the "rolling" section. A fixed-deadline entry with a date would appear in rolling, which is semantically wrong.

4. **No temporal ordering validation in timelines.** `validate.py` checks that the current status is reachable from the highest-dated timeline stage, but does not verify that timeline dates are chronologically ordered. A `submitted` date before a `qualified` date passes validation.

#### Unsupported Claims

1. **`TYPICAL_LIMITS` in `preflight.py` is dead code.** Defined but never read — actual limits come from `field["word_limit"]` via `parse_submission_format()`.

2. **`build_form_data()` in `greenhouse_submit.py` is dead code.** The function constructs form fields but is never called by `submit_to_greenhouse()`.

3. **`writing_sample` in `PROFILE_FILLABLE` always returns None.** `get_profile_content()` explicitly returns `None` for this section, yet it's listed as "fillable," creating false gap reports.

4. **`--note` in `check_outcomes.py` is accepted but never written.** The CLI accepts `--note` but `record_outcome()` ignores it.

#### Coherence Recommendations

1. **Unify state transition ownership.** Either `advance.py` handles ALL transitions (including post-submission), or clearly document the split: `advance.py` owns pre-submission, `check_outcomes.py` owns post-submission, `hygiene.py` owns expiration.

2. **Add `deferred → drafting` to `VALID_TRANSITIONS`.** Store pre-deferral status in the `deferral` field so entries return to their exact origin.

3. **Make `standup.py` triage call `advance.py`'s `advance_entry()`** instead of using its own `NEXT_STATUS` dict. This ensures timeline fields get set.

4. **Gate `_expire_entry()` against post-submission statuses.** An entry that's been acknowledged or is in interview should not be auto-expired just because a deadline passed.

5. **Gate `record_outcome()` against pre-submission statuses.** Require `status in ("submitted", "acknowledged", "interview")`.

---

### 1.3 Logos Review (Rational/Factual Appeal)

#### Argument Clarity: Strong

The scoring algorithm is well-documented in `strategy/scoring-rubric.md` with a clear mathematical formulation. Every dimension has an explicit scale (1–10), named signals, and the composite formula is a standard weighted sum. The 8-dimension model covers distinct concerns without redundancy.

#### Evidence Quality: Mixed

**Strong evidence basis:**
- Benefits cliff thresholds sourced from actual program eligibility limits (SNAP, Medicaid, Essential Plan)
- Credential relevance matrix (4×8) maps real credentials to real tracks
- Portal friction scores reflect actual user experience with each ATS

**Weak evidence basis:**
- `HIGH_PRESTIGE` dict (37 organizations scored 5–10) is entirely subjective with no documented methodology
- `CONVERSION_TARGETS` in `funnel_report.py` (10% apply→phone, 33% phone→onsite) are industry averages but not cited
- `FRESHNESS_MODIFIERS` in `ingest_top_roles.py` (+1.5 for urgent to -3.0 for ghost) are arbitrary without calibration data

#### Persuasive Strength: Variable

The scoring system is persuasive for **prioritization** (which entry to work on next) but less persuasive for **absolute qualification** (should I apply at all?). The 5.0/5.5 thresholds are arbitrary and never calibrated against outcomes. With no closed-loop feedback from outcomes to scoring weights, the system cannot learn whether its recommendations are correct.

#### Enhancement Recommendations

1. **Calibrate thresholds against outcomes.** Once sufficient outcome data exists (>50 entries), compute the actual acceptance rate by score band and adjust `QUALIFICATION_THRESHOLD` empirically.
2. **Replace `HIGH_PRESTIGE` subjective scores** with a computed signal: e.g., company size, Glassdoor rating, or position in the user's network graph.
3. **Cite conversion rate benchmarks.** Add source URLs for the 10%/33%/33% targets in `funnel_report.py`.
4. **Weight validation assertion.** Add `assert abs(sum(WEIGHTS.values()) - 1.0) < 0.001` at module load time.

---

### 1.4 Pathos Review (Emotional Resonance)

#### Current Emotional Tone

The pipeline is functionally cold — it treats applications as manufacturing units moving through a production line. This is appropriate for efficiency but creates two emotional gaps:

1. **No positive reinforcement loop.** The system flags staleness, overdue follow-ups, at-risk deadlines, and expired entries — all negative signals. There is no celebration of milestones (first interview, 10th submission, portfolio completion).

2. **"Ghosted" language.** `check_outcomes.py` uses "LIKELY GHOSTED" (all-caps) for entries past the response window. This framing can be demoralizing at scale. An alternative framing: "Response window exceeded — archive or follow up?"

#### Audience Connection

The pipeline is a single-user system where the user IS the audience. The emotional design should optimize for sustained motivation across long application cycles.

#### Engagement Recommendations

1. Add a `section_wins(entries)` to `standup.py` that highlights positive signals: entries that moved forward, interviews scheduled, follow-ups that got responses.
2. Replace "LIKELY GHOSTED" with "Response window exceeded" and pair with an actionable suggestion.
3. Add running totals to campaign view: "Applications this month: 12 (target: 15)" as a progress bar.

---

### 1.5 Ethos Review (Credibility/Authority)

#### Perceived Expertise: High

The codebase demonstrates genuine domain expertise:
- Benefits-cliff awareness is rarely seen in application tracking tools
- The 12-signal scoring model with track-specific weights is well beyond typical Trello-board tracking
- Market intelligence integration with configurable urgency thresholds shows operational maturity

#### Trustworthiness Signals

**Present:**
- Strategy docs match code 1:1 (scoring rubric fully implemented)
- Comprehensive validation (19 dimensions in `validate.py`)
- 30+ test files covering core logic

**Missing:**
- No outcome-to-scoring feedback loop (scores are never validated against reality)
- No confidence intervals on any statistic
- No audit trail for state transitions (who changed what, when, why)

#### Credibility Recommendations

1. **Add a calibration report.** Periodically compare predicted scores against actual outcomes to measure scoring accuracy.
2. **Log all state transitions** with timestamp, source script, and reason to `signals/transition-log.yaml`.
3. **Add sample sizes** to every displayed rate: "33% (3/9)" not just "33%".

---

## Phase 2: Reinforcement (Synthesis)

### Contradictions to Resolve

| # | Contradiction | Resolution |
|---|--------------|------------|
| 1 | Triage mode bypasses `VALID_TRANSITIONS` | Make triage import and call `advance_entry()` from `advance.py` |
| 2 | `_expire_entry()` bypasses state machine | Add status guard: skip if `status in ("submitted", "acknowledged", "interview")` |
| 3 | `browser_submit.py` records unsubmitted entries | Gate `record_submission()` behind `submitted == True` check |
| 4 | `check_outcomes.py` accepts outcomes for any status | Add guard: `status in ("submitted", "acknowledged", "interview")` |
| 5 | `deferred → drafting` impossible | Add to `VALID_TRANSITIONS`; store `pre_deferral_status` |

### Reasoning Gaps to Fill

| # | Gap | Fix |
|---|-----|-----|
| 1 | Cumulative funnel conflation | Track stage transitions historically via timeline dates, not current status |
| 2 | `run_auto_qualify` uses stale scores | Recompute score via `compute_composite()` before filtering against `min_score` |
| 3 | Campaign rolling filter inverted | Check `type in ("rolling", "tba")` directly |
| 4 | No timeline chronological validation | Add check in `validate.py`: timeline dates must be non-decreasing |

### Unsupported Claims to Remove/Support

| # | Claim | Action |
|---|-------|--------|
| 1 | `TYPICAL_LIMITS` in preflight.py | Remove dead code |
| 2 | `build_form_data()` in greenhouse_submit.py | Remove dead code |
| 3 | `writing_sample` in `PROFILE_FILLABLE` | Remove from set |
| 4 | `--note` in check_outcomes.py | Implement writing to YAML or remove flag |

---

## Phase 3: Risk Analysis

### 3.1 Blind Spots

#### Hidden Assumptions

1. **Python dict ordering = YAML field ordering.** The composition model (`compose.py`, `draft.py`) iterates `blocks_used` in dict insertion order. If a user edits YAML in a tool that reorders keys, the output section order silently changes.

2. **All resumes are 1 page.** `build_resumes.py` validates this, but the page-count regex (`/Type\s*/Page(?!s)`) on raw PDF bytes is fragile. Chrome-generated PDFs are simple enough for this, but a manually-edited PDF could fool the count.

3. **Market intelligence JSON is always well-formed.** `validate_intel_schema()` checks top-level keys but not nested structure. Malformed `track_benchmarks` values (e.g., strings instead of dicts) would crash scripts at runtime.

4. **The profile JSON is authoritative.** Content resolution falls back to profiles, but profiles are never validated against a schema. A profile missing `artist_statement.medium` would silently produce a gap.

5. **`COMPANY_DISPLAY_NAMES` in `source_jobs.py` has a mapping error.** `"coreweave": "Weights & Biases"` — CoreWeave and Weights & Biases are different companies. This would mislabel sourced jobs.

#### Overlooked Perspectives

1. **No applicant-side analytics.** The pipeline tracks what the user does (submit, follow up) but not what the market does (response patterns by day-of-week, time-of-year, etc.). Temporal patterns in hiring cycles could inform submission timing.

2. **No A/B testing infrastructure for content.** `compare_variants()` in `funnel_report.py` categorizes submissions by composition type (alchemized, block+variant, etc.) but does not randomize assignment. Observed differences may be confounded by self-selection (harder entries get more effort).

3. **No geographic bias detection.** `source_jobs.py` penalizes international entries (-3 points) but does not track whether this penalty correlates with actual outcomes.

4. **No portfolio impact signal.** `portfolio_url` is checked for presence but not for quality, recency, or relevance to the specific application.

#### Potential Biases

1. **Title-pattern matching in `ROLE_FIT_TIERS` favors DevEx/DevRel.** Tier-1 contains 12+ DevEx/DevRel patterns but only 2 infrastructure patterns. This biases auto-sourcing toward a specific career track.

2. **`HIGH_PRESTIGE` list is fixed and US-centric.** 37 organizations, almost all US tech companies. European institutions and non-tech organizations are underrepresented.

3. **Benefits cliff scoring penalizes the most valuable opportunities.** By design — but this means the system actively deprioritizes high-paying grants, which may not align with long-term financial goals.

#### Mitigation Strategies

1. **Schema-validate profiles** — add a `validate_profile()` function that checks required keys/types.
2. **Fix the CoreWeave mapping** — immediate data correction.
3. **Add outcome-conditioned analytics** — track acceptance rates by geography, timing, and content composition to validate or refute scoring assumptions.
4. **Consider time-decaying prestige scores** — load from a config file instead of hardcoding, with annual review.

---

### 3.2 Shatter Points

#### Critical Vulnerabilities (Severity: High → Critical)

| # | Vulnerability | Severity | Impact |
|---|--------------|----------|--------|
| 1 | **`check_entry()` tuple bug** — `standup.py` and `campaign.py` always report "2 issues" regardless of actual errors | HIGH | Misleading readiness signals; user may submit unready entries or delay ready ones |
| 2 | **`touch_entry()` full YAML rewrite** — destroys comments and field ordering | HIGH | Data loss on every `--touch` operation; accumulated formatting destruction over time |
| 3 | **No file locking on concurrent YAML mutation** — `advance.py`, `enrich.py`, `followup.py`, `check_outcomes.py` all read-modify-write without locks | HIGH | Race conditions if scripts run in parallel (e.g., campaign `--execute` while manually editing) |
| 4 | **`record_submission()` uses `filepath.rename()`** — silently overwrites if destination exists | MEDIUM | Entry data loss if duplicate IDs or re-submission attempts |
| 5 | **`_expire_entry()` non-atomic move** — writes to dest, then deletes source. Crash between = duplicate | MEDIUM | Entry exists in both `active/` and `closed/` after crash |
| 6 | **Lever API key in URL query parameter** — visible in server logs, proxies, browser history | MEDIUM | Credential exposure |
| 7 | **`browser_submit.py` records even when submit fails** — moves entry to submitted/ regardless | MEDIUM | False submission records; entry appears submitted but was never actually received |
| 8 | **Median calculation is wrong** — `conversion_report.py` uses `sorted_times[len//2]` (wrong for even-length lists) | LOW | Slightly incorrect response time statistics |
| 9 | **`_em_slot_name_alignment` double-counting** — block key "bio" matches fields "bio", "short_bio", "bio_text" | LOW | Inflated evidence_match scores |
| 10 | **Deadline score-4 gap** — mapping jumps 3→5, score 4 is unreachable | LOW | Non-uniform scoring scale; cosmetic |

#### Potential Attack Vectors (How Critics Might Respond)

1. **"The scoring has never been validated."** No closed-loop feedback from outcomes to weights. A critic could argue the entire 8-dimension model is theoretically elegant but empirically uncalibrated.

2. **"Sample sizes are too small for statistical claims."** With <100 total entries and <20 outcomes, every conversion rate, response time median, and breakdown-by-dimension could be noise. No script reports confidence intervals.

3. **"The system optimizes for volume, not quality."** The velocity metrics, weekly submission counts, and "sweet spot: 21-80 applications" framing emphasize throughput. A critic could argue fewer, higher-quality applications would be more effective.

#### Preventive Measures

1. **Fix the tuple bug immediately** — unpack `(errors, warnings) = check_entry(e)` in both scripts.
2. **Replace `touch_entry()` YAML rewrite** with `update_last_touched()` from `pipeline_lib.py`.
3. **Add file-level advisory locks** using `fcntl.flock()` for write operations.
4. **Gate `record_submission()` on actual submit success** in `browser_submit.py`.
5. **Use `statistics.median()`** from stdlib.
6. **Add Wilson score intervals** to all rate displays.

#### Contingency Preparations

1. **Backup before batch operations** — `advance.py`'s `_backup_files()` pattern should be adopted by all mutating scripts.
2. **YAML validation after every write** — already done in `update_yaml_field()` but not in `touch_entry()`, `_expire_entry()`, or `populate_portal_fields()`.
3. **Transaction log** — append every mutation to `signals/mutation-log.yaml` for forensic recovery.

---

## Phase 4: Growth

### 4.1 Bloom (Emergent Insights)

#### Emergent Themes

1. **The codebase has outgrown its "scripts in a directory" architecture.** 30+ scripts with cross-imports, duplicated functions, and inconsistent patterns suggest the need for a proper Python package structure with shared modules.

2. **Three analytics scripts (funnel_report, conversion_report, velocity) compute overlapping but inconsistent metrics.** This reveals a need for a unified analytics layer with a single funnel definition, shared statistical functions, and consistent output formatting.

3. **The scoring system is the most sophisticated component but has no feedback loop.** Every other pipeline component (enrichment, follow-up, hygiene) reacts to external signals. Scoring alone is static — set once, never updated by outcomes.

4. **Regex-based YAML mutation is the single largest source of bugs.** At least 5 distinct failure modes stem from regex patterns that don't match unusual YAML formatting. This is a systemic architectural issue, not a per-script bug.

#### Expansion Opportunities

1. **Outcome-conditioned scoring recalibration.** With sufficient outcome data, compute `P(accepted | score_band)` and adjust dimension weights to maximize predictive accuracy. Even a simple logistic regression on 8 dimensions would outperform the current fixed weights.

2. **Keyword-to-block recommendation engine.** `distill_keywords.py` extracts keywords and `match_tags_report()` cross-references against block tags. The missing link is a `recommend_blocks(entry_id)` function that combines keyword overlap, identity-position, and track to suggest optimal block selection.

3. **Content quality scoring.** A `score_content_alignment(entry, target_keywords)` function that measures how well a composed submission matches the target's extracted keywords, beyond simple word counts.

4. **Time-series analytics.** Track scoring drift, submission velocity trends, and response rate changes over time. Currently, each analytics run is a snapshot with no historical comparison.

#### Novel Angles

1. **Rejection analysis.** When outcomes arrive, analyze whether rejected entries share common scoring patterns (low in specific dimensions) to identify systematic blind spots.

2. **Effort-to-outcome efficiency.** Measure `effort_minutes / outcome_quality` to identify whether deep-effort entries actually convert better than quick ones, or if the ROI curve flattens.

3. **Portal-specific content optimization.** Different ATS portals have different rendering engines. Content that displays well in Greenhouse may truncate in Lever. A portal-aware content formatter could optimize output per platform.

#### Cross-Domain Connections

1. **The scoring model is essentially a multi-criteria decision analysis (MCDA) framework.** Connecting to MCDA literature (AHP, TOPSIS, PROMETHEE) could reveal mathematically superior aggregation methods beyond weighted sum.

2. **The follow-up protocol is a simple state machine over time.** Connecting to customer success / CRM literature could reveal more sophisticated outreach cadence models (e.g., variable timing based on response signals).

3. **The pipeline's "Cathedral → Storefront" philosophy** could be formalized as a content compression algorithm: given N blocks at depth D, generate the minimum-loss summary at target word count W.

---

### 4.2 Evolve (Concrete Implementation Priorities)

#### Tier 0: Fix Bugs (< 1 hour each)

| # | Fix | File | Change |
|---|-----|------|--------|
| 1 | Unpack `check_entry()` tuple | `standup.py:752`, `campaign.py:416` | `errors, warnings = check_entry(e)` |
| 2 | Fix `touch_entry()` to use `update_last_touched()` | `standup.py:touch_entry()` | Replace `yaml.dump` with regex mutation |
| 3 | Fix median calculation | `conversion_report.py` | `from statistics import median` |
| 4 | Fix `CoreWeave` display name | `source_jobs.py` | `"coreweave": "CoreWeave"` |
| 5 | Remove dead `TYPICAL_LIMITS` | `preflight.py` | Delete unused constant |
| 6 | Remove dead `build_form_data()` | `greenhouse_submit.py` | Delete unused function |
| 7 | Remove `writing_sample` from `PROFILE_FILLABLE` | `draft.py` | Remove from set |
| 8 | Implement `--note` in `record_outcome` or remove flag | `check_outcomes.py` | Write note to YAML or remove CLI arg |
| 9 | Fill deadline score-4 gap | `score.py` | `<=5 → 4, <=7 → 5` |
| 10 | Gate `record_submission()` on submit success | `browser_submit.py` | `if submitted: record_submission(...)` |

#### Tier 1: Consolidate Shared Code (1–2 hours each)

| # | Consolidation | From | To |
|---|--------------|------|-----|
| 1 | `resolve_cover_letter()` | 6 scripts | `pipeline_lib.py` |
| 2 | `resolve_resume()` | 3 scripts | `pipeline_lib.py` |
| 3 | `load_config()` | 4 scripts | `pipeline_lib.py` |
| 4 | `_format_block_stats()` + `_NOISE_LANGS` | compose.py, draft.py | `pipeline_lib.py` |
| 5 | `TIER_PRIORITY` + `get_tier()` | followup.py, research_contacts.py | `pipeline_lib.py` |
| 6 | `PROTOCOL_STEPS` / follow-up protocol | followup.py, research_contacts.py, standup.py | `pipeline_lib.py` (load from market intel) |
| 7 | Score tier boundaries | funnel_report.py, conversion_report.py | `pipeline_lib.py` constant |
| 8 | `FUNNEL_STAGES` | funnel_report.py, velocity.py | `pipeline_lib.py` constant |
| 9 | Auto-fill regex patterns | greenhouse, lever, ashby submitters | `ats_common.py` module |
| 10 | Multipart form assembly | greenhouse, lever, ashby submitters | `ats_common.py` module |

#### Tier 2: Architectural Improvements (2–4 hours each)

| # | Improvement | Rationale |
|---|-------------|-----------|
| 1 | Add `assert abs(sum(w) - 1.0) < 0.001` for both weight sets | Catches silent weight drift |
| 2 | Make triage mode call `advance_entry()` | Ensures timeline fields + transition validation |
| 3 | Add `deferred → drafting` transition | Fixes stuck-state for deferred drafting entries |
| 4 | Add timeline chronological ordering check to `validate.py` | Catches date-swap errors |
| 5 | Add duplicate ID detection across directories to `validate.py` | Catches ID collisions |
| 6 | Add status guard to `record_outcome()` | Prevents outcomes on pre-submission entries |
| 7 | Add status guard to `_expire_entry()` | Prevents expiring post-submission entries |
| 8 | Fix campaign rolling filter logic | Check `type in ("rolling", "tba")` directly |
| 9 | Fresh-compute scores in `run_auto_qualify` | Use `compute_composite()` not YAML-persisted score |
| 10 | Add Wilson score intervals to all rate displays | Statistical rigor for small samples |

#### Tier 3: New Capabilities (4–8 hours each)

| # | Capability | Value |
|---|-----------|-------|
| 1 | Unified analytics module with single funnel definition | Consistent metrics across scripts |
| 2 | Outcome-conditioned scoring recalibration | Empirically validated weights |
| 3 | `ats_common.py` shared ATS submission base | Eliminates 6-file duplication |
| 4 | Keyword-to-block recommendation engine | Automated block selection |
| 5 | Transaction/mutation log | Forensic recovery, audit trail |
| 6 | `ruamel.yaml` adoption for round-trip YAML editing | Eliminates regex YAML mutation bugs |
| 7 | HTTP retry with exponential backoff | Resilient API submissions |
| 8 | Profile schema validation | Catches missing profile fields |
| 9 | `section_wins()` in standup for positive reinforcement | Sustained motivation |
| 10 | Time-series analytics with historical comparison | Trend detection |

---

## Summary

### Key Findings

| Category | Count | Most Critical |
|----------|-------|--------------|
| Bugs | 10 | `check_entry()` tuple unpacking (P0) |
| Logic contradictions | 5 | Triage bypasses VALID_TRANSITIONS |
| Dead code | 4 | `build_form_data()`, `TYPICAL_LIMITS`, `writing_sample`, `--note` |
| Code duplication | 10 clusters | `resolve_cover_letter()` in 6 files |
| Missing validation | 15+ | No timeline chronology, no outcome status guard |
| Statistical gaps | 6 | No confidence intervals, wrong median, no sample sizes |
| Hardcoded constants needing extraction | 20+ | Score tiers, funnel stages, protocol steps |

### Architecture Assessment

The pipeline is a **mature prototype** — the domain model (identity positions, scoring rubric, state machine) is sophisticated and well-documented, but the implementation has accumulated technical debt from organic growth. The transition from "30 scripts in a directory" to a proper Python package with shared modules would eliminate the largest class of bugs (duplication, inconsistency) and enable the most valuable new capabilities (unified analytics, scoring recalibration, automated block recommendation).

### Recommended Next Steps

1. **Immediate (today):** Fix the `check_entry()` tuple bug and `touch_entry()` YAML destruction — these affect daily workflow.
2. **This week:** Consolidate the 6 `resolve_cover_letter()` copies and 3 `resolve_resume()` copies into `pipeline_lib.py`.
3. **This month:** Create `ats_common.py` to deduplicate the three ATS submitters, add weight validation, and fix the 5 state machine contradictions.
4. **Next month:** Build the unified analytics module and outcome-conditioned scoring recalibration.
