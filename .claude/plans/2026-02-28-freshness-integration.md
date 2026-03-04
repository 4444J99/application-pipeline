# 7-Day Rule: Posting-Age Freshness Integration

**Date:** 2026-02-28
**Mode:** Plan
**Scope:** `scripts/source_jobs.py`, `scripts/ingest_top_roles.py`, `pipeline/_schema.yaml`

---

## Context

Recruiters review applications in order of submission. Research shows:
- **48-hour peak**: applications in the first 48 hours have highest conversion rates
- **14-day black hole**: near-zero probability of response after 14 days
- **30-day ghost**: postings live after 30 days are effectively closed — short-list already selected

Currently, `ingest_top_roles.py` assigns `deadline_feasibility: 9` to all rolling-deadline jobs regardless of posting age. A 45-day-old posting scores identically to a same-day posting. This misprioritizes effort.

**Goal:** Capture posting dates from ATS APIs and apply a freshness scoring modifier so older postings are deprioritized automatically in the glove-fit engine.

---

## API Gap (confirmed by code review)

| Portal | Date field in raw API response | Captured today? |
|--------|-------------------------------|-----------------|
| Greenhouse | `updated_at` (ISO datetime string, e.g. "2026-02-10T14:30:00Z") | ❌ No |
| Lever | `createdAt` (Unix ms timestamp) | ❌ No |
| Ashby | `publishedDate` (ISO date — verify field name on first run) | ❌ No |

---

## Implementation Plan

### Step 1 — Capture posting dates in `scripts/source_jobs.py`

**`fetch_greenhouse_jobs()`** (around line 254): Extract `updated_at` and slice to `YYYY-MM-DD`:
```python
raw_date = job.get("updated_at", "")
posting_date = raw_date[:10] if raw_date else None
```
Add `"posting_date": posting_date` to the normalized dict.

**`fetch_lever_jobs()`** (around line 285): Convert `createdAt` Unix-ms to ISO date:
```python
created_ms = job.get("createdAt")
if created_ms:
    from datetime import datetime, timezone
    posting_date = datetime.fromtimestamp(created_ms / 1000, tz=timezone.utc).date().isoformat()
else:
    posting_date = None
```
Add `"posting_date": posting_date` to the normalized dict.

**`fetch_ashby_jobs()`** (around line 314): Extract `publishedDate` (graceful fallback):
```python
raw_date = job.get("publishedDate") or job.get("updatedAt", "")
posting_date = raw_date[:10] if raw_date else None
```
Add `"posting_date": posting_date` to the normalized dict.

**`create_pipeline_entry()`** (around line 430): Add to `timeline`:
```python
"timeline": {
    "researched": today,
    "posting_date": job.get("posting_date"),
},
```

### Step 2 — Add freshness scoring in `scripts/ingest_top_roles.py`

**Add constants and helper** after `IDENTITY_KEYWORDS`:
```python
FRESHNESS_MODIFIERS = {
    "urgent":   +1.5,   # 0–2 days: 48-hour peak
    "fresh":    +0.5,   # 3–7 days: still strong
    "standard":  0.0,   # 8–14 days: no modifier
    "aging":    -0.5,   # 15–21 days: declining
    "stale":    -1.5,   # 22–30 days: near-black-hole
    "ghost":    -3.0,   # 31+ days: effectively closed
    "unknown":   0.0,   # No date captured
}

def freshness_tier(posting_date: str | None) -> tuple[str, int | None]:
    if not posting_date:
        return "unknown", None
    try:
        from datetime import date as _date
        age = (_date.today() - _date.fromisoformat(posting_date)).days
    except (ValueError, TypeError):
        return "unknown", None
    if age <= 2:   return "urgent", age
    if age <= 7:   return "fresh", age
    if age <= 14:  return "standard", age
    if age <= 21:  return "aging", age
    if age <= 30:  return "stale", age
    return "ghost", age
```

**Update `pre_score()`**: apply freshness modifier to the final score (clamped 0–10):
```python
tier, _ = freshness_tier(job.get("posting_date"))
freshness_mod = FRESHNESS_MODIFIERS[tier]
score = sum(dims[dim] * weight for dim, weight in WEIGHTS_JOB.items())
return round(max(0.0, min(10.0, score + freshness_mod)), 2)
```

**Update Top 10 display** in `run()`: add freshness column showing tier + age:
```
  #  Score  Age      Tier               Company              Role
  1   9.3   Day 1    devex-tier         Anthropic            Software Engineer ✓
  2   8.8   Day 42   [ghost]            OpenAI               DX Engineer ✓
```

**Add `--max-age DAYS` flag** to `main()` and `run()`: filter out postings older than N days before scoring. Default: `None` (no filter).

### Step 3 — Update `pipeline/_schema.yaml`

Add one comment line in the `timeline` section (after `researched`):
```yaml
#   posting_date: ISO date the job was posted (from ATS API; null if unavailable)
```

---

## Files to Modify

| File | Lines | Change |
|------|-------|--------|
| `scripts/source_jobs.py` | ~254, ~285, ~314, ~430 | Add `posting_date` capture in all 3 fetch functions; add to `create_pipeline_entry()` timeline |
| `scripts/ingest_top_roles.py` | after line 57, `pre_score()`, `run()`, `main()` | Add `FRESHNESS_MODIFIERS`, `freshness_tier()`, update scoring, display, and `--max-age` flag |
| `pipeline/_schema.yaml` | timeline section (~line 88) | Document `posting_date` |

---

## Verification

```bash
# 1. Run glove-fit with freshness active — freshness column should appear
python scripts/ingest_top_roles.py --top 20

# 2. Test age filter
python scripts/ingest_top_roles.py --max-age 14

# 3. Inspect a promoted entry for posting_date in timeline
python scripts/ingest_top_roles.py --promote --dry-run

# 4. Run tests
pytest tests/ -v
```

**Note on Ashby field verification**: If `posting_date` is `None` for all Ashby entries on first run, inspect the raw API JSON to confirm the correct field name (`publishedDate`, `createdAt`, or `updatedAt`).

---

---

# [ARCHIVED] Evaluation-to-Growth: Application Pipeline — Project-Wide Review

**Date:** 2026-02-28
**Mode:** Autonomous
**Output:** Markdown Report + Implementation Plan
**Scope:** Full pipeline — strategy, architecture, content, conversion, risk

---

## Context

The application pipeline is 4 days into its first submission burst: 48 applications submitted Feb 24–28 across job, grant, writing, emergency, and prize tracks. The infrastructure (37 scripts, 701 tests, state machine, scoring rubric, block library, ATS integrations) is mature. Zero positive outcomes exist yet — too early for data — but the system's design assumptions and execution patterns are now visible and auditable.

---

## Phase 1 — Evaluation

### 1.1 Critique

**Strengths:**
1. **Infrastructure is genuinely exceptional.** 37 scripts, 701 passing tests, YAML state machine, 8-dimension scoring rubric with dual weight sets — this is enterprise-grade tooling built by one person for one person's application pipeline. The engineering is proportionate to the ambition.
2. **Identity position system is well-differentiated and documented.** Five framings of the same body of work with clear rules for when to use each, tailored opening line templates, and explicit "what to emphasize / what to acknowledge" guidance.
3. **Storefront Playbook is excellent strategic theory.** The Cathedral → Storefront translation framework, the 60-second test, preemptive gap framing — these are sophisticated practices that most applicants never formalize.
4. **Content composition model is principled.** blocks → profiles → variants is the right architecture: modular, reusable, auditable.
5. **Scoring rubric is defensible.** Two separate weight sets (creative vs. job), 8 auto-derived dimensions, signal-based computation with no gut-feel input — well-reasoned.
6. **The 60s block delivers.** "103 repositories across 8 organizations, built and documented by one person" is the right hook. Immediate, concrete, unusual.

**Weaknesses:**
1. **48 submissions in 4 days with identical block sets.** Batch-02 and -03 job submissions all wire the same 5 blocks (`framings/independent-engineer`, `evidence/differentiators`, `evidence/work-samples`, `pitches/credentials-creative-tech`, `methodology/ai-conductor`). The block library's modularity is being negated by templating. This is the exact failure mode the system was designed to prevent.
2. **The non-job pipeline is stalled.** Creative Capital ($50K, April 2), Google AMI ($9K+, rolling 9.0 score), Prix Ars (€10K–20K, deadline March 4 — possibly already missed), LACMA, Whiting — the highest-value entries are staged but unsubmitted while 30+ jobs were sent.
3. **"Acknowledged" is conflated with human progression.** The `patterns.md` calls it a conversion metric; it's an autoresponder. No human has advanced any application yet — the pipeline is 4 days old.
4. **940 research_pool entries** is not a queue, it's a dump. Auto-sourcing has created a volume problem disguised as precision. The `ingest_top_roles.py` just built addresses inflow; the pool itself needs a triage protocol.
5. **The independent-engineer position contains a structural credibility gap it must explicitly bridge.** Identity-positions.md acknowledges it ("no team PRs, no production users"), but the gap is real: ATS systems pattern-match "solo practitioner with no employers" as a risk signal. The position's strength (solo-at-institutional-scale) requires human readers to override that pattern.

---

### 1.2 Logic Check

**Contradictions:**
- The storefront playbook says "One Sentence, One Claim" — the `blocks/identity/60s.md` violates this with three nested claims in one paragraph. The 60s block is the *most-used* piece of content; this is consequential.
- The conversion-log records `blocks_used: null` for batch-01 submissions. The scoring rubric's `evidence_match` dimension uses `blocks_used` count as a signal. Batch-01 entries are therefore being systematically under-scored by the rubric — even if their actual submissions were stronger.
- `fit.original_score` is documented as "frozen historical baseline — not used in computation." But it appears in active YAML entries alongside `fit.score`. The dual-score field is a maintenance burden and coherence risk if anyone reads the raw YAML.

**Reasoning Gaps:**
- No mechanism exists to propagate covenant-ark metric updates to blocks. When the repo count, test count, or CI pipeline count changes, every block that references these numbers must be manually updated. The `check_metrics.py` script validates consistency but doesn't repair it.
- The scoring model has no calibration baseline. All scores are computed forward from data signals but there are no positive outcomes to validate the model against. A score of 8.5 may or may not predict interview success.

---

### 1.3 Logos (Rational Appeal)

- The argument for a systematic pipeline is correct. Tailored materials + structured state machine + campaign orchestration is better than ad hoc applications.
- The dual-rubric design (creative vs. job weights) is well-reasoned and documented.
- **Weakness:** The scoring model produces no differentiation within the job track when blocks_used is identical across entries. All batch-02/03 jobs share the same 5 blocks → same evidence_match signal → same score band. The rubric is calibrated for block diversity that doesn't exist in current submissions.
- **Weakness:** The `pre_score` function in `ingest_top_roles.py` hard-codes `financial_alignment=8` and `effort_to_value=7` regardless of company or role. These defaults are reasonable but documented nowhere — silent assumptions that could produce wrong rankings if the assumptions are ever violated.

---

### 1.4 Pathos (Emotional Resonance)

- The community-practitioner opening ("queer, housing-precarious artist building creative infrastructure from lived experience of precarity") is the most emotionally authentic — it's specific, it positions the work inside a real material condition, and it creates genuine resonance with the funders it targets.
- The independent-engineer position is the least emotionally resonant — "Sole architect of a 103-repository system" is compelling *about* the scale but doesn't communicate *why it matters to the reader*. The storefront leads with the number but not the claim that makes the number interesting.
- The 60s block's current text: "The process of creation is the product: governance structures, dependency graphs, and promotion pipelines are generative constraints, not bureaucracy." — this is an excellent conceptual claim, but "generative constraints" is inside vocabulary. A first-pass reviewer may not follow.

---

### 1.5 Ethos (Credibility)

- **Strongest signals:** 3.6K tests, 94 CI/CD pipelines, 43 validated dependency edges, 0 violations — these are verifiable, metric-backed, and unusual for a solo practitioner.
- **Weakest signals:** The `original_score` field implies the scores were once gut-feel, which undermines the rubric's authority. The "42 essays" claim is referenced everywhere but the essays themselves are external — a reviewer following links needs to actually find them.
- **The "5 years building production-grade infrastructure" framing** (identity-positions.md) is accurate but will pattern-match ATS as "non-standard background" without context. The current profile says "Sole architect" which is better, but the 5-year framing needs to survive the 30-second resume screen.
- **The pipeline codebase itself is a credibility asset that isn't being used.** The resume lists "Application Pipeline — CLI Tooling Suite" as a project. This system — 14 scripts, state machine, scoring rubric — is demonstrably production-grade Python. A GitHub link to this repo with a visible test count would materially strengthen the IE position.

---

## Phase 2 — Reinforcement

### 2.1 Synthesis

**Core tension to resolve:** The pipeline's infrastructure sophistication serves the job track (high volume, mechanical optimization) but the highest-value opportunities are in the grant/prize track (low volume, bespoke deep work). The same tooling that generates 30 job submissions in 3 days cannot be applied to Creative Capital — but the pipeline currently treats all tracks with similar velocity assumptions.

**Coherence improvements needed:**
1. **The 60s block** should be rewritten to satisfy the One Sentence, One Claim rule: three discrete sentences, not one paragraph with subordinate clauses.
2. **blocks_used = null entries** in conversion-log should be flagged and retroactively filled (even if approximated) so scoring remains consistent.
3. **original_score field** should be considered for deprecation or explicit archival once calibration data exists.

---

## Phase 3 — Risk Analysis

### 3.1 Blind Spots

1. **ATS velocity detection.** 10 Anthropic applications filed within 4 days (Feb 24–28) to the same company via Greenhouse. Some ATS systems rate-limit or flag applicants who submit to multiple roles simultaneously. This is not documented anywhere in the pipeline's risk model.
2. **The grant pipeline is the strategic moat — and it's being neglected.** Jobs at AI labs are competitive and bidirectional (many strong candidates applying for many roles). Art grants and prizes are evaluative — reviewers are looking for a *specific kind of practitioner*, and the ORGANVM system is a better answer to their question than to a job spec. The pipeline's volume focus inverts the value gradient.
3. **No feedback integration protocol.** When the first batch of rejections arrive (likely mid-March), there's no workflow to systematically capture the signal. The `check_outcomes.py` script records outcomes, but there's no mechanism to analyze patterns and update strategy.
4. **Calibration void.** All scoring is forward-computed from data signals with no positive outcomes to validate against. The rubric may be systematically miscalibrated in ways that won't become visible until outcomes exist.
5. **Metric staleness.** The blocks and identity-positions.md reference "103 repositories," "3.6K tests," "94 CI/CD pipelines," "42 essays" — but these numbers change as the ORGANVM system grows. No automated sync exists. A reviewer who runs their own count and gets a different number is a credibility risk.

### 3.2 Shatter Points

1. **Prix Ars Electronica March 4 deadline.** The Feb 25 campaign view shows three entries at "staged" with 7 days. As of Feb 28, 4 days remain (Mar 4). If these complex submissions haven't been worked, €40,000 in opportunity is about to expire despite being tracked in the pipeline.
   *Severity: HIGH. Immediate action required.*

2. **The 60s block is the most-used content piece and it violates its own rules.** Every job submission using blocks wires `identity/60s` or `framings/independent-engineer`. If the core identity content doesn't pass the 60-second test, the whole block-based submission model is compromised.
   *Severity: MEDIUM. Affects all future job submissions.*

3. **blocks_used field in conversion-log is null for all batch-01 submissions (16 entries).** When A/B analysis runs on "does blocks_used composition affect outcomes?", batch-01 will be excluded or produce misleading signals because the data wasn't captured.
   *Severity: MEDIUM. Data loss for future analysis.*

4. **The independent-engineer position mismatches hiring manager pattern recognition.** "Sole architect... solo practitioner... independent practice" are signals that fire "contractor" or "consultant" in a hiring manager's mental model before the scale of the work registers. The framing needs to proactively interrupt this pattern earlier.
   *Severity: MEDIUM. Ongoing risk for all job submissions.*

5. **The application_pipeline codebase is public.** If a reviewer finds it (linked from the resume project description), they may read the scoring rubric, identity positions, storefront rules, and the company-focus analysis which names specific companies and their perceived weaknesses. This is an information exposure risk for the independent-engineer strategy.
   *Severity: LOW (until confirmed as public repo). Verify repo visibility.*

---

## Phase 4 — Growth

### 4.1 Bloom (Emergent Insights)

1. **The pipeline codebase IS the strongest evidence for the independent-engineer position.** This system — 37 scripts, 701 tests, 8-dimension scoring rubric, ATS integrations, state machine — is more sophisticated than many production internal tools at engineering orgs. It should be featured as the *primary* work sample, not just an item in the project list.

2. **The grant pipeline is the moat, not the job pipeline.** For art grants and prizes, the ORGANVM system answers the evaluator's actual question: "Is this practitioner doing something genuinely unusual at genuine scale?" For AI lab job openings, the question is "Does this person have the right mix of prior team experience and technical skills?" The grant track is where the work's distinctiveness is actually a competitive advantage.

3. **A "feedback hypothesis" workflow would transform the pipeline's learning rate.** When an outcome is recorded, the system could auto-prompt: "What's your hypothesis about why this outcome occurred?" Structured hypotheses over 10–15 outcomes would produce a calibrated scoring model that no amount of upfront rubric design can achieve.

4. **The block library's six categories (evidence, identity, methodology, projects, framings, pitches) are the right taxonomy but the `pitches/` category has low coverage.** Every target should have a bespoke pitch block. The current system relies on profile content for target-specific material — but profiles are JSON files, not narrative blocks, and they don't feed into block-based composition cleanly.

### 4.2 Evolve (Recommended Implementation Plan)

**Priority order: immediate → short-term → medium-term**

---

#### IMMEDIATE (This Week, Before More Submissions)

**A. Prix Ars & S+T+ARTS Deadline Crisis**
- **Action:** Drop all other pipeline activity. Work the three staged prize entries (Prix Ars Digital Humanity, Prix Ars Interactive Art+, S+T+ARTS Prize). March 4 deadline = 4 days. These are complex submissions (€10–20K each).
- **Files:** `pipeline/active/prix-ars-electronica.yaml`, `pipeline/active/starts-prize.yaml`

**B. Rewrite the 60s Block — One Sentence, One Claim**
- **Problem:** The block is the most-used piece of content and violates its own rules.
- **Action:** Rewrite `blocks/identity/60s.md` as three discrete sentences:
  - Sentence 1: The hook with the number
  - Sentence 2: The methodology (what makes it unusual)
  - Sentence 3: The medium (AI as compositional instrument)
- **File:** `blocks/identity/60s.md`

**C. Pause Job Submission Burst**
- **Action:** The 48 submissions already in flight are sufficient for signal gathering. No new job submissions until mid-March when first batch of outcomes appears.
- **Rationale:** ATS concentration risk at Anthropic (10 roles); feedback-free additional submissions yield diminishing returns; grant pipeline is more time-sensitive and value-dense.

---

#### SHORT-TERM (2–3 Weeks, Before Feedback Arrives)

**D. Feedback Integration Protocol**
- **Create:** `scripts/feedback_capture.py` — when an outcome is recorded via `check_outcomes.py --record`, auto-prompt for a structured hypothesis: What category (resume_screen, cover_letter, credential_gap, timing, auto-rejection)? What's the hypothesis? Store in `signals/hypotheses.yaml`.
- **Purpose:** By the time 10+ rejections arrive, hypotheses will be structured enough to run pattern analysis.

**E. Retroactive blocks_used Capture for Batch-01**
- **Action:** For the 16 batch-01 entries in conversion-log with `blocks_used: null`, manually add approximate block references. Even imprecise ("cover-letter-only") is better than null for future A/B analysis.
- **Files:** `signals/conversion-log.yaml` (16 entries)

**F. Research Pool Triage Protocol**
- **Problem:** 940 entries is unmanageable for manual review.
- **Action:** Run `python scripts/score.py --auto-qualify --yes --min-score 8.0` to promote only the genuinely high-fit entries. Archive everything below 6.0 via `archive_research.py --yes`. Target: ≤100 entries in research_pool that are worth reviewing manually.

**G. Grant Pipeline Execution**
- **Entries to work (staged, rolling deadlines):** Google AMI (9.0 score, deep), Whiting (8.0, standard), LACMA (7.9, deep), Creative Capital (8.0, deep, April 2).
- **These are the moat opportunities.** Each requires bespoke narrative — blocks exist but need composition.

---

#### MEDIUM-TERM (1–2 Months, Once Feedback Arrives)

**H. Scoring Calibration Loop**
- When 10+ outcomes exist (mix of rejections and at least 1 interview), run `funnel_report.py --by position --by score` and compare predicted scores against actual outcomes.
- Adjust `ROLE_FIT_TIERS` in `score.py` and position weights in `strategy/scoring-rubric.md` based on findings.

**I. Metric Auto-Sync**
- **Create:** `scripts/sync_metrics.py` — reads canonical metrics from `organvm-corpvs-testamentvm/docs/applications/00-covenant-ark.md` and flags blocks/identity-positions.md where numbers differ.
- **Purpose:** Prevents the credibility risk of citing stale numbers.

**J. Independent-Engineer Position Framing Adjustment**
- **Issue:** "Sole architect... solo practitioner" pattern-matches as "contractor" before the scale registers.
- **Action:** Update `strategy/identity-positions.md` and `blocks/framings/independent-engineer.md` to interrupt the contractor pattern earlier: lead with the output scale, then clarify the production context ("without institutional support, without a team").
- **Principle:** Name the objection before the reader forms it.

**K. Pipeline Codebase as Primary Work Sample**
- **Action:** Add `application-pipeline` as a named project block in `blocks/projects/`. Include: test count, script count, scoring rubric, state machine description, ATS integration.
- **Purpose:** Demonstrated engineering discipline applied to a real operational problem = stronger evidence than the abstract ORGANVM system for an IE position reviewer.

---

## Verification

Each recommendation is verifiable:

| Item | Verification |
|------|-------------|
| A. Prix Ars | Check `pipeline/submitted/` for prix-ars-*.yaml by March 4 |
| B. 60s block rewrite | Read new `blocks/identity/60s.md`; confirm 3 distinct sentences |
| C. Job pause | Check that `pipeline/active/` adds no new job YAMLs until March 15 |
| D. Feedback capture | Run `python scripts/check_outcomes.py --record cohere-applied-ai --outcome rejected`; verify it prompts for hypothesis |
| E. Batch-01 backfill | grep blocks_used null in conversion-log; count should drop to 0 |
| F. Pool triage | `find pipeline/research_pool -name "*.yaml" | wc -l` should drop to ≤100 |
| G. Grant pipeline | Three grant entries should reach `submitted` status by March 15 |

---

## Summary Table

| Phase | Finding | Severity | Action |
|-------|---------|---------|--------|
| Critique | 48 jobs submitted; identical blocks | High | Pause; diversify block usage going forward |
| Critique | Grant pipeline stalled | High | Reprioritize to grants immediately |
| Logic | 60s block violates own rules | Medium | Rewrite (Item B) |
| Logic | blocks_used null in batch-01 | Medium | Retroactive capture (Item E) |
| Risk | Prix Ars March 4 deadline | URGENT | Submit this week (Item A) |
| Risk | No feedback integration | High | Build feedback_capture.py (Item D) |
| Risk | ATS concentration at Anthropic | Medium | Monitor; no additional applications |
| Risk | Metric staleness | Low | Build sync_metrics.py (Item I) |
| Growth | Pipeline codebase as work sample | High | Add as project block (Item K) |
| Growth | Grant track is the moat | High | Reframe strategic priority (Items G, J) |
