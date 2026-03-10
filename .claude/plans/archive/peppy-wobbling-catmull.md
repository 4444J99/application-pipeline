# Evaluation-to-Growth: Application Pipeline Project Review

## Context

Full-system review of `~/Workspace/4444J99/application-pipeline/` using the Evaluation-to-Growth lens-protocol. The pipeline manages 43 active entries + 1 submitted across grants, residencies, jobs, and writing tracks. It has 18 Python scripts, 9 test files (191 tests), modular narrative blocks, 44 target profiles, and a signals/conversion tracking system. This review evaluates content quality, structural integrity, strategic effectiveness, and growth opportunities.

---

## PHASE 1: CRITIQUE

### 1.1 Critique — Core Content Quality

**Narrative Blocks (blocks/)**
- **Strengths:** Tiered depth system (60s → 2min → 5min → cathedral) is well-designed. The 60s pitch is tight and metric-forward. Cathedral block provides genuine philosophical depth.
- **Weakness: Metrics Inconsistency (CRITICAL).** The single most damaging content problem. Three numbers are used interchangeably for the same claim:
  - `blocks/identity/60s.md`: "101 repositories"
  - `blocks/evidence/metrics-snapshot.md`: "103" (table), synced 2026-02-18
  - `strategy/storefront-playbook.md`: "101 repos" (line 7), "103 repositories" (line 15), "101 repos" (line 52) — *three different numbers in one file*
  - `strategy/identity-positions.md`: "101" (systems-artist, creative-technologist), "103" (systems-artist evidence line)
  - `blocks/evidence/work-samples.md`: "0 essays" (line 9) while everywhere else says "42 essays"
  - `blocks/evidence/metrics-snapshot.md`: "Published essays | 0" (line 11) — contradicts all other files
  - Profiles (44 JSON files): all say "101 repositories"
  - Cover letters: mixed (101, 103)
  - Legacy submissions: "100 repositories" (watermill)
- **Impact:** A reviewer who cross-references the portfolio site with the cover letter could find conflicting numbers — immediate credibility damage. The "0 essays" in metrics-snapshot.md and work-samples.md is a data corruption bug that could propagate through alchemize.py's automated mapping.

**Cover Letters (variants/cover-letters/)**
- 8 cover letters for 43 active entries = 19% coverage
- Quality is strong where they exist (anthropic-fde, together-ai, cohere are well-crafted)
- The grant-art-template is reusable but generic

**Strategy Documents**
- `storefront-playbook.md`: Excellent conceptual framework (cathedral/storefront metaphor). Rules are actionable. The 60-second test is practical.
- `identity-positions.md`: 4 canonical positions are well-differentiated. Rules section is strong ("never say software engineer").
- `qualification-assessment.md`: Honest gap analysis — rare and valuable.

### 1.2 Logic Check — Structural Coherence

**Pipeline Architecture**
- Schema (`_schema.yaml`) → entries → blocks → variants → profiles → submission flow is logically sound
- Status progression: researched → qualified → drafting → staged → submitted → acknowledged is clear

**Script Ecosystem — Duplication Problem**
- `load_block()` is defined identically in 3 files: `compose.py:25`, `submit.py:36`, `draft.py:272`. Should live in `pipeline_lib.py`.
- `load_entries()` is duplicated in `score.py:82` vs `pipeline_lib.py:81`. The `score.py` version filters differently but could use the shared one with a filter param.
- This duplication creates maintenance drift risk.

**Test Coverage Gap**
- 9/18 scripts have tests (50% coverage):
  - WITH tests: advance, campaign, compose, draft, enrich, pipeline_lib, preflight, submit, validate
  - WITHOUT tests: alchemize, check_metrics, conversion_report, daily_batch, greenhouse_submit, pipeline_status, score, standup, velocity
- The untested scripts include critical path components: `score.py` (drives prioritization), `greenhouse_submit.py` (handles actual API submission), `alchemize.py` (new orchestrator)

**Framing Block Sprawl**
- `strategy/identity-positions.md` defines 4 canonical positions: systems-artist, educator, creative-technologist, community-practitioner
- `blocks/framings/` has 8 files: the 4 canonical + `ai-orchestrator.md`, `emergency-precarity.md`, `starts-prize-european-dimension.md`, `starts-prize-art-tech-collaboration.md`
- The extra 4 aren't referenced in identity-positions.md. This creates ambiguity about which framings are "official."

### 1.3 Logos — Argument Structure

**Core Thesis:** "The process of creation IS the product" — governance as artistic medium.
- This is a genuinely novel position in the intersection of systems art and institutional critique
- It's well-argued across the cathedral block and 60s pitch
- The storefront playbook correctly identifies that this thesis needs translation for different audiences

**Logical Weakness:** The pipeline treats all 43 entries as equally viable, but conversion data (1 submission, 0 outcomes) means the scoring system (`score.py`) is optimizing on theory, not empirical feedback. The 8-dimension scoring model has no calibration data.

### 1.4 Pathos — Emotional Resonance

**Strongest:** Community-practitioner framing — "building creative infrastructure from lived experience of precarity." This grounds the abstract systems work in human stakes.
**Weakest:** Creative-technologist framing — reads like a technical resume rather than a compelling narrative. "Production-grade AI orchestration systems" doesn't generate emotional investment from a reviewer.
**Missing:** The qualification-assessment.md is admirably honest about gaps (no external validation, no published book, no gallery exhibitions), but none of the cover letters address these gaps preemptively. Reviewers will notice them.

### 1.5 Ethos — Credibility Signals

**Strong credibility:**
- MFA Creative Writing — legitimizes the writing-as-art claim
- 11 years teaching, 2,000+ students, 8+ institutions — demonstrates professional track record
- 2,349+ tests, 94+ CI/CD — demonstrates technical rigor
- Open-source everything — demonstrates transparency commitment

**Credibility risks:**
- "0 essays" in two evidence files undermines the "42 essays" claim everywhere else
- No external validation (awards, exhibitions, publications, peer citations) — the system is self-referential
- The sheer scale claim (103 repos, 8 orgs, ~810K words) by one person may trigger skepticism without external anchoring

---

## PHASE 2: SYNTHESIS

### Key Insight

The pipeline has excellent *infrastructure* but thin *conversion data* and *inconsistent content*. It's a well-engineered system for producing applications, but the applications themselves have metric contradictions that could undermine the very precision the system claims to embody. The irony is sharp: a project built on "governance as artwork" has ungoverned data inconsistencies.

### Priority Matrix

| Issue | Severity | Effort | Impact |
|-------|----------|--------|--------|
| Metrics inconsistency (101/103/0 essays) | CRITICAL | Low | Fix prevents credibility damage in every submission |
| `load_block()` duplication | Medium | Low | Consolidate to pipeline_lib.py |
| Test coverage for critical scripts | High | Medium | score.py, greenhouse_submit.py, alchemize.py need tests |
| Framing block sprawl | Low | Low | Document or consolidate the 4 extra framings |
| Conversion data bootstrapping | High | Medium | Need a feedback loop before scoring has meaning |
| Preemptive gap-addressing in cover letters | Medium | Medium | Storefront playbook Rule 4 doesn't address known weaknesses |

---

## PHASE 3: RISK ANALYSIS

### 3.1 Blind Spots

1. **No A/B signal loop.** The pipeline tracks *which* blocks were used per submission but has no mechanism to compare outcomes across framings. With 1 submission recorded and 0 outcomes, the scoring model, block selection, and identity-position choices are all untested hypotheses.

2. **Profile JSON staleness.** 44 profile JSONs all contain "101 repositories" and "~410K+ words" — numbers that are already outdated per metrics-snapshot.md (103 repos, ~810K+ words). No script validates profile freshness against the source-of-truth metrics.

3. **Greenhouse-only automation.** `greenhouse_submit.py` and `alchemize.py` only handle Greenhouse portals. Of 43 active entries, how many are Greenhouse? The remaining entries (grants via Submittable, SlideRoom, direct email, Google Forms) have no automation path. This creates a two-tier system where Greenhouse jobs get full orchestration while grants/residencies — which may have higher strategic value — stay manual.

4. **No portfolio freshness check.** Cover letters link to `https://4444j99.github.io/portfolio/` but the pipeline has no mechanism to verify the portfolio is deployed, current, and consistent with the claims being made.

5. **Emergency framing without guardrails.** `blocks/framings/emergency-precarity.md` exists but isn't one of the 4 canonical positions. Emergency fund applications (fca-emergency, rauschenberg, wff-housing) need careful tone calibration — the pipeline doesn't distinguish between "applying from strength" and "applying from need."

### 3.2 Shatter Points

1. **Single-source-of-truth violation.** CLAUDE.md says "update covenant-ark first, then propagate to blocks here." But there's no automation for propagation. Every manual sync is a chance for the 101/103 drift to recur. `check_metrics.py` exists but isn't wired into CI or pre-commit.

2. **alchemize.py imports private functions.** `alchemize.py` imports `_get_custom_questions` and `_field_type_label` from `greenhouse_submit.py` — these are underscore-prefixed (private convention). If `greenhouse_submit.py` refactors internally, alchemize breaks silently.

3. **Scoring without calibration = false confidence.** The composite score formula in `score.py` produces numbers like 4.2 that *look* authoritative but are purely heuristic. No calibration against actual outcomes means the scores could systematically misdirect effort toward low-conversion targets.

4. **Cover letter variant naming.** Variants use inconsistent naming: `anthropic-fde-custom-agents.md` (target-specific), `grant-art-template.md` (generic), `openai-se-applied-evals.md` (target-specific). The `-alchemized` suffix from alchemize.py adds a third convention. This makes it hard to audit which entries have which coverage.

---

## PHASE 4: GROWTH

### 4.1 Bloom — Immediate Improvements

**B1. Fix metrics inconsistency (all files)**
- Establish canonical numbers from `metrics-snapshot.md` (the designated source-of-truth): 103 repos, 42 essays
- Fix `metrics-snapshot.md` line 11: "Published essays | 0" → "Published essays | 42"
- Fix `work-samples.md` line 9: "0 essays" → "42 essays"
- Grep-and-replace "101 repo" → "103 repo" across blocks/, strategy/, variants/
- Update all 44 profile JSONs: "101 repositories" → "103 repositories", "~410K+" → "~810K+"
- Wire `check_metrics.py` into `validate.py` or create a pre-commit hook
- Files: `blocks/evidence/metrics-snapshot.md`, `blocks/evidence/work-samples.md`, `blocks/identity/60s.md`, `strategy/storefront-playbook.md`, `strategy/identity-positions.md`, all `targets/profiles/*.json`, all `variants/cover-letters/*.md`

**B2. Consolidate `load_block()` into pipeline_lib.py**
- Move the function from `compose.py:25` to `pipeline_lib.py`
- Update imports in `compose.py`, `submit.py`, `draft.py`
- Add to `pipeline_lib.py` exports
- Files: `scripts/pipeline_lib.py`, `scripts/compose.py`, `scripts/submit.py`, `scripts/draft.py`

**B3. Make alchemize.py private imports explicit**
- Rename `_get_custom_questions` → `get_custom_questions` and `_field_type_label` → `field_type_label` in `greenhouse_submit.py`, or add a public facade
- Files: `scripts/greenhouse_submit.py`, `scripts/alchemize.py`

**B4. Document non-canonical framings**
- Add a "## Extended Framings" section to `strategy/identity-positions.md` acknowledging ai-orchestrator, emergency-precarity, and starts-prize-* blocks as target-specific extensions of the 4 canonical positions
- File: `strategy/identity-positions.md`

### 4.2 Evolve — Strategic Growth

**E1. Add tests for critical untested scripts**
- Priority order: `score.py` (drives prioritization), `greenhouse_submit.py` (API submission), `alchemize.py` (new orchestrator)
- Score.py tests should verify weight normalization, dimension clamping, composite calculation
- Greenhouse tests should mock API calls and verify payload construction
- Alchemize tests should verify phase outputs against known entries
- Files: `tests/test_score.py` (create), `tests/test_greenhouse_submit.py` (create), `tests/test_alchemize.py` (create)

**E2. Add storefront playbook Rule 6: Address Known Gaps**
- New rule: "Preemptively address the gap the reviewer will notice. Frame it as trajectory, not absence."
- Example: "No external awards yet — but the 103-repo system was built in 18 months, and the evaluation framework this pipeline implements is itself evidence of the methodology."
- File: `strategy/storefront-playbook.md`

**E3. Profile freshness automation**
- Add a `--check-freshness` flag to `validate.py` that compares profile JSON metric values against `metrics-snapshot.md` source of truth
- Alert on any profile with stale numbers
- File: `scripts/validate.py`

**E4. Conversion feedback loop**
- After 5+ submissions are recorded in `signals/conversion-log.yaml`, build a simple analysis in `conversion_report.py` that correlates identity_position, blocks_used, and effort_level with outcomes
- Use this to calibrate `score.py` weights empirically
- Files: `scripts/conversion_report.py`, `scripts/score.py`

---

## Implementation Order

1. **B1** — Metrics fix (highest impact, lowest risk, prevents credibility damage)
2. **B2** — load_block consolidation (quick cleanup)
3. **B3** — Public API for greenhouse_submit imports (prevents future breakage)
4. **B4** — Document extended framings (documentation-only)
5. **E1** — Test coverage for score.py, greenhouse_submit.py, alchemize.py
6. **E2** — Storefront playbook Rule 6
7. **E3** — Profile freshness validation
8. **E4** — Conversion feedback loop (deferred until data accumulates)

## Verification

1. `python scripts/validate.py` passes after all changes
2. `pytest tests/ -v` passes with new + existing tests
3. `grep -r "101 repo" blocks/ strategy/ variants/` returns 0 matches after B1
4. `grep -r "0 essays" blocks/` returns 0 matches after B1
5. `grep "def load_block" scripts/` returns exactly 1 match (in pipeline_lib.py) after B2
6. `grep "def load_entries" scripts/` returns exactly 1 match (in pipeline_lib.py) after B2 (score.py refactored)
7. No underscore-prefixed imports from greenhouse_submit.py after B3

## Critical Files

| File | Action | Step |
|------|--------|------|
| `blocks/evidence/metrics-snapshot.md` | Fix "0 essays" → "42 essays" | B1 |
| `blocks/evidence/work-samples.md` | Fix "0 essays" → "42 essays" | B1 |
| `blocks/identity/60s.md` | "101" → "103" | B1 |
| `strategy/storefront-playbook.md` | Standardize all to "103" | B1 |
| `strategy/identity-positions.md` | Standardize + add extended framings section | B1, B4 |
| `targets/profiles/*.json` (44 files) | "101" → "103", "~410K+" → "~810K+" | B1 |
| `variants/cover-letters/*.md` (8 files) | Standardize repo count | B1 |
| `scripts/pipeline_lib.py` | Add `load_block()` | B2 |
| `scripts/compose.py` | Import from pipeline_lib | B2 |
| `scripts/submit.py` | Import from pipeline_lib | B2 |
| `scripts/draft.py` | Import from pipeline_lib | B2 |
| `scripts/score.py` | Use pipeline_lib.load_entries() | B2 |
| `scripts/greenhouse_submit.py` | Publicize imported functions | B3 |
| `scripts/alchemize.py` | Update import names | B3 |
| `tests/test_score.py` | Create | E1 |
| `tests/test_greenhouse_submit.py` | Create | E1 |
| `tests/test_alchemize.py` | Create | E1 |
| `strategy/storefront-playbook.md` | Add Rule 6 | E2 |
| `scripts/validate.py` | Add --check-freshness | E3 |
