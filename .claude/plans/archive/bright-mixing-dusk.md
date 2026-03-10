# Evaluation-to-Growth: Application Pipeline Project Review

## Context

Full-system review of the `application-pipeline` project — a personal career application infrastructure managing grant, residency, fellowship, job, and writing applications as a structured conversion pipeline. The system comprises 19 Python scripts, 42 active entries, 44 target profiles, 36 narrative blocks, and a comprehensive strategy layer. This review applies the Evaluation-to-Growth lens-protocol across all four phases: Critique, Reinforcement, Risk Analysis, and Growth.

---

## Phase 1: CRITIQUE

### 1A. Strengths

**Architecture:** The storefront/cathedral two-layer model is genuinely well-conceived. The separation into blocks (content atoms), pipeline (state machine), profiles (intelligence), and signals (analytics) is clean and each layer is independently useful. The `_schema.yaml` at 232 lines documents every field with enums — rare discipline for a personal project.

**State machine rigor:** The pipeline state machine (`research → qualified → drafting → staged → submitted → acknowledged → interview → outcome`) is enforced by `advance.py` with valid transition tables, and validated by `validate.py` which checks status-timeline consistency, block paths, dimension ranges, and outreach records. This is genuinely robust.

**Scoring system:** The 8-dimension weighted rubric (`score.py`) is well-calibrated — auto-deriving 5 dimensions from data (deadline, financial, portal, effort, strategic) while preserving human-judgment dimensions (mission, evidence, track record). The benefits cliff awareness (SNAP/Medicaid/Essential Plan thresholds) is a real-world concern that most systems wouldn't model.

**Content composition model:** The 3-layer fallback (`blocks → profiles → legacy scripts`) in `pipeline_lib.py` ensures no entry is ever "empty" while allowing incremental improvement. The legacy script parser (`_parse_legacy_markdown`) handles 32 pre-existing submissions without requiring migration.

**Testing:** 305 tests across 12 files, running against real data. Tests validate actual pipeline YAML, block files, and profile JSONs — not mocked abstractions.

### 1B. Weaknesses

**YAML mutation via regex:** Multiple scripts (`advance.py`, `enrich.py`, `score.py`, `standup.py`) modify YAML files using regex substitution rather than parse-modify-dump. This is fragile:
- `advance.py:63-69` — `re.sub(r'^(status:\s+).*$', ...)` breaks if `status:` appears in a comment or multi-line string
- `enrich.py:113-119` — `re.sub(r'^(\s*materials_attached:\s*)\[\]', ...)` assumes exact formatting of empty arrays
- `score.py:369-375` — `re.sub(r"^(\s+score:\s+)[\d.]+", ...)` assumes score is numeric only (fails on `null` or quoted strings)

**Signals layer is hollow:** The entire signals/analytics infrastructure exists structurally but has near-zero data:
- `conversion-log.yaml` — 2 entries, 0 outcomes
- `patterns.md` — "No data yet" with 5 untested hypotheses
- `outreach-log.yaml` — 0 entries
- `standup-log.yaml` — 1 session
- `conversion_report.py` has sophisticated analysis code (outcome rates by track, identity position, score bracket) that cannot produce meaningful output

**Profile-pipeline ID mismatch at scale:** `PROFILE_ID_MAP` in `pipeline_lib.py` has 14 manual mappings. With 42 entries and 44 profiles, ~30 entries lack explicit mappings. Adding new entries requires remembering to update the map — there's no validation that warns about unmapped entries.

**Cross-script import coupling is inconsistent:** `campaign.py` imports from `enrich.py` and `score.py`. `alchemize.py` imports from `greenhouse_submit.py` and `enrich.py`. `preflight.py` lazily imports from `draft.py` and `submit.py` inside functions. This creates a fragile import web without a clear dependency direction. `sys.path.insert(0, ...)` in tests compounds this.

**No automated opportunity intake:** The first step of the pipeline (discovering opportunities) is entirely manual. Every entry in `pipeline/active/` was hand-created. The `research` status exists but no tooling populates it.

**Duplicate constants across scripts:** `VALID_TRANSITIONS` is defined identically in both `validate.py:39-48` and `advance.py:26-35`. `VALID_TRACKS`, `VALID_STATUSES`, etc. appear in both `validate.py` and `pipeline_lib.py`.

### 1C. Logic Consistency Check

**Scoring-to-qualification gap:** `score.py` computes a composite but `QUALIFICATION_THRESHOLD = 5.0` is essentially the midpoint. With weights heavily favoring mission_alignment (25%) and evidence_match (20%), an entry with strong fit but poor logistics (expired deadline, bad portal) still qualifies easily. The threshold may be too permissive to be useful as a gate.

**Campaign window doesn't account for effort:** `campaign.py:65-115` filters by deadline window but doesn't consider effort level. A "complex" (1-2 day) entry with 3 days left is surfaced alongside a "quick" (30 min) entry with 3 days left, both as "critical." The system knows effort levels but doesn't use them in feasibility calculations.

**Alchemize resume selection is read-only:** `alchemize.py` phase_map includes resume selection text in the mapping output, but never actually wires the selected resume into the pipeline YAML. That's still done separately by `enrich.py`. There's a potential inconsistency if the identity position changes between mapping and enrichment.

**Deadline scoring uses `datetime.now()` vs `date.today()`:** `score.py:114-118` uses `datetime.strptime` and `datetime.now()` for deadline calculation, while `pipeline_lib.py:186-188` uses `date.today()`. These can disagree by up to 1 day depending on time-of-day, and the test suite (`test_score.py:105-109`) documents this discrepancy in comments rather than fixing it.

### 1D. Logos Review (Logical Structure)

The system's logical flow is: **Discover → Research → Score → Qualify → Draft → Stage → Submit → Track**. But:
- Steps 1-2 (Discover/Research) lack tooling for most portal types (only Greenhouse automated)
- Steps 3-4 (Score/Qualify) exist but the threshold is purely advisory
- Steps 5-7 (Draft/Stage/Submit) have tooling but submission is still manual (copy-paste from checklists)
- Step 8 (Track) infrastructure exists but has no data flow

The system excels at the middle of the funnel (organizing, scoring, enriching) but has weak edges — no automated intake and no closed-loop outcome tracking.

### 1E. Pathos Review (Emotional/Motivational Integrity)

The system handles a genuinely stressful domain (applications under benefits cliff constraints) with unusual care:
- Benefits cliff analysis is woven into scoring, not bolted on
- `qualification-assessment.md` explicitly maps honest claims vs non-claims — a healthy self-audit
- The storefront/cathedral metaphor acknowledges the emotional reality that "nobody has time to enter the cathedral"
- The 5 identity positions allow authentic self-presentation rather than forcing a single persona

**Risk:** The system's sophistication could become a procrastination vector. With 42 active entries and 19 scripts, maintaining the system can displace doing the work. The standup system's 7-section structure (health → stale → plan → outreach → practices → replenish → log) may be overdesigned for a solo operator.

### 1F. Ethos Review (Credibility Architecture)

The identity-position system (systems-artist, creative-technologist, educator, community-practitioner, independent-engineer) is genuinely thoughtful. Each position has a clear framing in `strategy/identity-positions.md` with extended prompts and template structures.

**Concern:** The evidence layer (blocks/evidence/) relies heavily on self-reported metrics. `check_metrics.py` validates consistency between blocks and profiles, but the canonical source (`metrics-snapshot.md`) is self-authored. The system validates internal consistency but not external verifiability.

---

## Phase 2: REINFORCEMENT (Synthesis)

### Core Synthesis

The application pipeline is a **well-architected but under-utilized system**. Its structural rigor (schema validation, state machine enforcement, 8-dimension scoring, benefits cliff awareness) is genuinely impressive for personal infrastructure. But the system has outgrown its usage:

1. **Built for scale, operating at trickle:** 42 active entries, 2 submissions, 0 outcomes. The analytics infrastructure (conversion reports, velocity tracking, pattern detection) exists for a throughput that hasn't materialized.

2. **Middle-funnel excellence, edge-funnel gaps:** The system excels at organizing, scoring, and enriching but has no automated intake (discovery) and no closed-loop outcome tracking.

3. **Technical debt in the plumbing:** Regex-based YAML mutation across 4+ scripts is the single largest fragility. One malformed YAML file or unexpected formatting could corrupt data silently.

4. **Strategy layer is aspirational:** Strategy documents describe what *should* happen (conversion analysis, pattern detection, outreach cadence) but the data to support those strategies doesn't exist yet.

### What's Working (Preserve These)

- 8-dimension scoring rubric with benefits cliff awareness
- Block/profile/legacy 3-tier content composition
- Schema validation with transition checking
- Identity-position system with resume variants
- Storefront/cathedral content architecture

### What Needs Change (Prioritized)

1. **Replace regex YAML mutation with safe parse-modify-dump** — affects `advance.py`, `enrich.py`, `score.py`, `standup.py`
2. **Add a submission tracking feedback loop** — currently `conversion-log.yaml` is manually maintained; `submit.py --record` should auto-populate it
3. **Consolidate duplicate constants** — `VALID_TRANSITIONS`, `VALID_TRACKS`, etc. should live in `pipeline_lib.py` only
4. **Make deadline scoring consistent** — use `date.today()` everywhere, not mixed `datetime.now()` / `date.today()`
5. **Add effort-feasibility check to campaign urgency** — don't show "critical" for entries that need 2 days of work with 1 day left

---

## Phase 3: RISK ANALYSIS

### 3A. Blind Spots

1. **No rollback mechanism:** `advance.py`, `enrich.py`, and `score.py` all write directly to YAML files. There's no undo, no backup-before-write, no diff tracking. A bad batch operation could corrupt multiple entries. Git is the only safety net but it requires the user to notice and revert.

2. **Profile freshness is checked for one metric only:** `validate.py:276-332` checks repo count freshness but not other metrics (published words, project count, etc.). Stale profiles with outdated statistics could produce inaccurate submissions.

3. **No test for the full pipeline chain:** Tests validate individual functions but there's no integration test that runs `research → score → qualify → map → synthesize` end-to-end. The scripts interact through file I/O (YAML files on disk) which is never tested as a chain.

4. **Network-dependent code is untested:** `alchemize.py` functions that fetch web pages (`fetch_page_text`, `fetch_greenhouse_data`) and `greenhouse_submit.py` POST endpoints have no mock tests. Any API change breaks silently.

5. **No concurrency safety:** Multiple scripts can modify the same YAML file simultaneously. Running `enrich.py --all --yes` and `score.py --all` at the same time would produce race conditions and data corruption.

### 3B. Shatter Points

1. **Regex YAML mutation (Critical):** If any YAML file uses unexpected formatting (quoted strings, multi-line values, YAML anchors), the regex substitutions in `advance.py`, `enrich.py`, `score.py`, and `standup.py` will either fail silently or corrupt the file. This is the most likely source of data loss.

2. **`sys.path.insert(0, ...)` in tests:** All test files manually insert the `scripts/` directory into `sys.path`. If any script filename collides with a stdlib or third-party module name, imports will break unpredictably.

3. **Greenhouse API dependency without fallback:** `alchemize.py` and `greenhouse_submit.py` depend on the Greenhouse Job Board API. If Greenhouse changes their API or the job posting expires, the pipeline breaks for all job-track entries. There's no cached/offline mode.

4. **44 profiles, 14 manual ID mappings:** `PROFILE_ID_MAP` maps entry IDs to profile filenames, but 30+ entries rely on ID-filename matching. Adding entries with non-matching names will silently return `None` from `load_profile()`, and many scripts treat `None` as "no profile" rather than erroring.

---

## Phase 4: GROWTH

### 4A. Bloom (Emergent Insights)

The pipeline's greatest unrealized value is its **variant tracking + outcome attribution** design. The schema already records which blocks, identity position, and framing were used per submission. Once 10+ outcomes exist, `conversion_report.py` can answer: "Which identity position wins grants? Which block combinations get interviews? Which framing language correlates with success?"

This is a genuine learning system — but it requires submissions and outcomes to learn from. The system is optimized for a throughput it hasn't achieved.

### 4B. Evolve (Implementation Plan)

#### Priority 1: Fix YAML Mutation (Prevents Data Loss)

**Problem:** 4 scripts use regex to modify YAML files, risking corruption.

**Solution:** Add a `safe_update_yaml()` function to `pipeline_lib.py` that:
1. Reads the file with `yaml.safe_load()`
2. Applies changes to the parsed dict
3. Writes back with `yaml.dump()` using a custom Dumper that preserves key order and formatting preferences
4. Alternatively: read raw text, parse, modify the dict, then use a targeted write strategy that only replaces the specific field values (preserving comments and formatting) via a proper YAML round-trip library

**Files:** `scripts/pipeline_lib.py` (new function), `scripts/advance.py`, `scripts/enrich.py`, `scripts/score.py`, `scripts/standup.py` (refactor to use it)

**Verification:** `pytest tests/ -v` — all 305 existing tests pass; add new tests for edge cases (quoted strings, multi-line values, YAML anchors)

#### Priority 2: Consolidate Duplicate Constants

**Problem:** `VALID_TRANSITIONS` defined in both `validate.py:39-48` and `advance.py:26-35`. `VALID_TRACKS` in both `validate.py:12` and `pipeline_lib.py:64`.

**Solution:** Move all shared constants to `pipeline_lib.py`. Import from there in `validate.py` and `advance.py`. Remove duplicate definitions.

**Files:** `scripts/pipeline_lib.py`, `scripts/validate.py`, `scripts/advance.py`

**Verification:** `pytest tests/ -v` — no regressions; grep for duplicate definitions confirms single source

#### Priority 3: Fix Datetime Inconsistency

**Problem:** `score.py` uses `datetime.now()` for deadline calculation while `pipeline_lib.py` uses `date.today()`. Results can differ by 1 day.

**Solution:** Change `score.py:114` from `datetime.strptime(...) → datetime.now()` comparison to `date` comparison using `pipeline_lib.parse_date()` and `pipeline_lib.days_until()`. Simplify test comments that document the discrepancy.

**Files:** `scripts/score.py`, `tests/test_score.py`

**Verification:** `pytest tests/test_score.py -v` — deadline tests should pass without time-of-day workaround comments

#### Priority 4: Add Effort-Aware Campaign Feasibility

**Problem:** `campaign.py` classifies urgency by deadline alone. A "complex" entry (1-2 days work) due in 3 days is shown as "critical" but is actually infeasible.

**Solution:** Add feasibility flag to `classify_urgency()` that compares `EFFORT_MINUTES[effort_level]` against available time. Show `[INFEASIBLE]` tag alongside entries where effort exceeds remaining time.

**Files:** `scripts/campaign.py`, `tests/test_campaign.py` (new tests)

**Verification:** `python scripts/campaign.py` — complex entries with 1-3 day deadlines show `[INFEASIBLE]`

#### Priority 5: Auto-Populate Conversion Log on Submit

**Problem:** `conversion-log.yaml` is manually maintained. `submit.py --record` updates the YAML status but doesn't add to conversion log.

**Solution:** In `submit.py`'s `--record` path, append to `signals/conversion-log.yaml` with entry ID, submission date, track, identity position, blocks used, and variant ID. This ensures every submission is tracked without manual intervention.

**Files:** `scripts/submit.py`, `scripts/pipeline_lib.py` (add `append_conversion_log()` helper)

**Verification:** `python scripts/submit.py --target <id> --record` then check `signals/conversion-log.yaml` has a new entry

#### Priority 6: Add Pipeline Integration Test

**Problem:** No test exercises the cross-script pipeline chain. Individual functions are tested but file I/O interactions between scripts are not.

**Solution:** Add `tests/test_integration.py` with a test that creates a temporary YAML entry, runs `score → enrich → advance → preflight` in sequence, and verifies the entry progresses correctly through the state machine with all fields populated.

**Files:** `tests/test_integration.py` (new)

**Verification:** `pytest tests/test_integration.py -v`

### Files to Modify (Summary)

| Priority | File(s) | Change |
|----------|---------|--------|
| P1 | `pipeline_lib.py`, `advance.py`, `enrich.py`, `score.py`, `standup.py` | Safe YAML mutation |
| P2 | `pipeline_lib.py`, `validate.py`, `advance.py` | Consolidate duplicate constants |
| P3 | `score.py`, `tests/test_score.py` | Fix datetime inconsistency |
| P4 | `campaign.py`, `tests/test_campaign.py` | Effort-aware feasibility |
| P5 | `submit.py`, `pipeline_lib.py` | Auto-populate conversion log |
| P6 | `tests/test_integration.py` | Cross-script integration test |

### Verification (End-to-End)

1. `pytest tests/ -v` — All existing + new tests pass
2. `python scripts/validate.py` — All pipeline entries valid
3. `python scripts/score.py --all --dry-run` — Scoring produces consistent results
4. `python scripts/campaign.py` — Shows [INFEASIBLE] tags where appropriate
5. `python scripts/campaign.py --days 90` — Full quarter view with no [LOW] entries showing as recommended
6. Manual: create a test entry, advance it through the full pipeline, verify conversion log auto-populated
