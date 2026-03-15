# Corpus-Driven Scoring Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace title-pattern scoring with corpus-driven scoring that matches job description content against the user's actual body of work (blocks, resume, projects).

**Architecture:** At sourcing time, fetch the full job description from ATS APIs (Greenhouse content field, Lever description, Ashby body). Store as `description` field in the pipeline YAML entry. At scoring time, tokenize the description and compute TF-IDF cosine similarity against the user's corpus content (blocks, resume sections, profile). Use similarity scores to drive `mission_alignment`, `evidence_match`, and `track_record_fit` dimensions instead of title-pattern lookup.

**Tech Stack:** Python stdlib (no new dependencies). Extends existing `text_match.py` TF-IDF engine and `score_human_dimensions.py`.

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `scripts/source_jobs.py` | Modify | Add description fetching to Greenhouse/Lever/Ashby sourcing |
| `scripts/score_human_dimensions.py` | Modify | Replace title-pattern fallback with corpus-driven scoring for auto-sourced entries |
| `scripts/score_text_match.py` | Modify | Add `corpus_match_from_description()` that works with inline description text (not research.md files) |
| `scripts/score_constants.py` | Modify | Add `CORPUS_SKILLS` — canonical skill keywords extracted from blocks/resume for fast matching |
| `tests/test_score_human_dimensions.py` | Modify | Add tests for corpus-driven scoring path |
| `tests/test_source_jobs.py` | Modify | Add tests for description fetching |

---

## Chunk 1: Fetch Job Descriptions at Sourcing Time

### Task 1: Add description fetching to Greenhouse sourcing

**Files:**
- Modify: `scripts/source_jobs.py` — `fetch_greenhouse_jobs()` function (~line 315)
- Test: `tests/test_source_jobs.py`

The Greenhouse list endpoint (`/v1/boards/{token}/jobs`) doesn't include description. The single-job endpoint (`/v1/boards/{token}/jobs/{id}`) returns a `content` field with full HTML description (~30K chars). Fetching per-job is expensive, so we only fetch for entries that pass the title filter.

- [ ] **Step 1: Write failing test for description fetching**

```python
def test_greenhouse_job_includes_description(monkeypatch):
    """Greenhouse jobs should include description text when available."""
    import source_jobs

    fake_list = json.dumps({"jobs": [
        {"id": 123, "title": "Software Engineer, Developer Experience",
         "updated_at": "2026-03-15", "absolute_url": "https://example.com/jobs/123",
         "location": {"name": "Remote"}}
    ]})
    fake_detail = json.dumps({
        "content": "<p>We are looking for a developer experience engineer...</p>",
        "title": "Software Engineer, Developer Experience",
    })

    call_count = {"n": 0}
    def fake_http_get(url):
        call_count["n"] += 1
        if "/jobs/" in url and url.endswith("/123"):
            return fake_detail.encode()
        return fake_list.encode()

    monkeypatch.setattr(source_jobs, "_http_get", fake_http_get)
    jobs = source_jobs.fetch_greenhouse_jobs("test-board")
    assert len(jobs) == 1
    assert "developer experience" in jobs[0].get("description", "").lower()
```

- [ ] **Step 2: Run test, verify it fails**

Run: `pytest tests/test_source_jobs.py::test_greenhouse_job_includes_description -v`
Expected: FAIL — `description` key missing from job dict

- [ ] **Step 3: Implement description fetching in `fetch_greenhouse_jobs()`**

After the list fetch, for each job that passes the existing title filter, make a second GET to `/v1/boards/{token}/jobs/{id}` to get the `content` field. Strip HTML to plain text and store as `description` in the normalized job dict.

Key implementation details:
- Only fetch description for jobs that pass `_passes_title_filter()` (already exists)
- Use existing `normalize_text()` from `text_match.py` to strip HTML
- Rate limit: add 100ms sleep between detail fetches to avoid hammering API
- If detail fetch fails, continue with empty description (non-blocking)
- Cap description at 5000 chars to avoid bloating YAML files

- [ ] **Step 4: Run test, verify it passes**

- [ ] **Step 5: Add description to pipeline YAML entry template**

In `_create_entry()` (~line 724), add `description` field under `target`:

```python
"target": {
    ...existing fields...
    "description": job.get("description", ""),
},
```

- [ ] **Step 6: Commit**

```bash
git add scripts/source_jobs.py tests/test_source_jobs.py
git commit -m "feat: fetch job descriptions from Greenhouse API at sourcing time"
```

### Task 2: Add description fetching to Lever and Ashby

**Files:**
- Modify: `scripts/source_jobs.py` — `fetch_lever_jobs()` and `fetch_ashby_jobs()`

Lever list endpoint already returns `descriptionPlain` or `description` per job. Ashby returns `descriptionHtml` in the posting response. These don't need a second API call.

- [ ] **Step 1: Write tests for Lever and Ashby description extraction**

- [ ] **Step 2: Extract description from Lever response** (`descriptionPlain` field)

- [ ] **Step 3: Extract description from Ashby response** (`descriptionHtml` field, strip HTML)

- [ ] **Step 4: Run tests, verify pass**

- [ ] **Step 5: Commit**

```bash
git commit -m "feat: extract job descriptions from Lever and Ashby API responses"
```

---

## Chunk 2: Corpus-Driven Scoring

### Task 3: Build canonical corpus skills list

**Files:**
- Modify: `scripts/score_constants.py`

Extract the key skills, technologies, and capabilities from the user's blocks and resume into a structured keyword set. This is the "what I can do" reference that job descriptions get matched against.

- [ ] **Step 1: Define `CORPUS_SKILLS` in `score_constants.py`**

Organized by category, derived from blocks/framings/independent-engineer.md and resume:

```python
CORPUS_SKILLS = {
    "languages": {"python", "typescript", "javascript", "html", "css", "yaml", "json", "markdown", "bash", "zsh"},
    "frameworks": {"react", "node", "express", "astro", "vite", "typer", "fastapi", "pydantic"},
    "testing": {"pytest", "vitest", "playwright", "ruff", "ci-cd", "github-actions", "tdd", "test-infrastructure"},
    "ai_agent": {"claude", "anthropic", "agent-sdk", "mcp", "model-context-protocol", "agentic", "ai-agent", "llm", "orchestration", "multi-agent"},
    "devtools": {"cli", "developer-tools", "developer-experience", "devex", "dx", "sdk", "api", "documentation", "technical-writing"},
    "infrastructure": {"docker", "terraform", "gcp", "nginx", "redis", "websocket", "ci-cd", "github-actions", "monorepo"},
    "data": {"yaml", "json-schema", "validation", "pipeline", "etl", "data-pipeline"},
    "frontend": {"react", "astro", "p5js", "d3js", "css", "responsive", "accessibility"},
    "methodology": {"ai-conductor", "governance", "automation", "quality-gates", "promotion-state-machine"},
    "teaching": {"curriculum", "pedagogy", "instructor", "course-design", "writing", "composition", "communication"},
}

# Flattened for fast lookup
CORPUS_SKILLS_FLAT = set()
for category_skills in CORPUS_SKILLS.values():
    CORPUS_SKILLS_FLAT.update(category_skills)
```

- [ ] **Step 2: Commit**

### Task 4: Add corpus-match scoring function

**Files:**
- Modify: `scripts/score_text_match.py`
- Test: `tests/test_score_text_match.py` (or `tests/test_text_match.py`)

- [ ] **Step 1: Write failing test**

```python
def test_corpus_match_from_description_high_match():
    """Job description with many corpus skills should score high."""
    description = "Looking for a senior developer experience engineer with Python, TypeScript, CI/CD, and documentation skills. Must have experience with CLI tools, testing frameworks like pytest, and developer tools."
    result = corpus_match_from_description(description)
    assert result["mission_alignment"] >= 8
    assert result["evidence_match"] >= 8

def test_corpus_match_from_description_low_match():
    """Job description with no corpus overlap should score low."""
    description = "Looking for a senior iOS engineer with Swift, Objective-C, and UIKit experience. Must have App Store deployment experience."
    result = corpus_match_from_description(description)
    assert result["mission_alignment"] <= 4
    assert result["evidence_match"] <= 4

def test_corpus_match_from_description_empty():
    """Empty description should return neutral defaults."""
    result = corpus_match_from_description("")
    assert result["mission_alignment"] == 5
```

- [ ] **Step 2: Run tests, verify failure**

- [ ] **Step 3: Implement `corpus_match_from_description()`**

```python
def corpus_match_from_description(description: str) -> dict[str, int]:
    """Score a job description against the user's corpus of skills and work.

    Tokenizes the description, counts overlapping terms with CORPUS_SKILLS,
    and maps coverage percentage to dimension scores.

    Returns dict with mission_alignment, evidence_match, track_record_fit.
    """
    if not description or len(description.strip()) < 50:
        return {"mission_alignment": 5, "evidence_match": 4, "track_record_fit": 4}

    from text_match import tokenize
    tokens = set(tokenize(description))
    if not tokens:
        return {"mission_alignment": 5, "evidence_match": 4, "track_record_fit": 4}

    # Count hits per category
    category_hits = {}
    total_hits = 0
    for category, skills in CORPUS_SKILLS.items():
        hits = len(tokens & skills)
        # Also check bigrams: "developer experience" → "developer-experience"
        for skill in skills:
            if "-" in skill:
                parts = skill.split("-")
                if all(p in tokens for p in parts):
                    hits += 1
        category_hits[category] = hits
        total_hits += hits

    # Coverage: what fraction of our skills appear in the description
    coverage = total_hits / max(len(CORPUS_SKILLS_FLAT), 1)

    # Category-weighted scoring
    # High-signal categories for mission_alignment
    ma_categories = {"ai_agent", "devtools", "methodology", "teaching"}
    ma_hits = sum(category_hits.get(c, 0) for c in ma_categories)
    ma_possible = sum(len(CORPUS_SKILLS[c]) for c in ma_categories)
    ma_ratio = ma_hits / max(ma_possible, 1)

    # High-signal categories for evidence_match
    em_categories = {"languages", "frameworks", "testing", "infrastructure"}
    em_hits = sum(category_hits.get(c, 0) for c in em_categories)
    em_possible = sum(len(CORPUS_SKILLS[c]) for c in em_categories)
    em_ratio = em_hits / max(em_possible, 1)

    # Map ratios to 1-10 scores
    # 0% → 3, 10% → 5, 20% → 7, 30%+ → 9
    def ratio_to_score(r):
        if r >= 0.30: return 9
        if r >= 0.20: return 8
        if r >= 0.15: return 7
        if r >= 0.10: return 6
        if r >= 0.05: return 5
        if r >= 0.02: return 4
        return 3

    mission = ratio_to_score(ma_ratio)
    evidence = ratio_to_score(em_ratio)
    track_record = max(3, min(mission, evidence) - 1)  # slightly below the lower of the two

    return {
        "mission_alignment": mission,
        "evidence_match": evidence,
        "track_record_fit": track_record,
    }
```

- [ ] **Step 4: Run tests, verify pass**

- [ ] **Step 5: Commit**

### Task 5: Wire corpus scoring into `compute_human_dimensions`

**Files:**
- Modify: `scripts/score_human_dimensions.py` — `compute_human_dimensions()` auto-sourced branch (~line 386)
- Test: `tests/test_score_human_dimensions.py`

- [ ] **Step 1: Write failing test**

```python
def test_auto_sourced_with_description_uses_corpus_scoring(monkeypatch):
    """Auto-sourced entry with description should use corpus match, not title patterns."""
    entry = {
        "name": "Software Engineer",  # Generic title → tier-2 (7/6/5) in old system
        "tags": ["auto-sourced"],
        "track": "job",
        "target": {
            "description": "Build developer tools and CLI infrastructure in Python and TypeScript. Work with CI/CD pipelines, GitHub Actions, and testing frameworks.",
        },
        "fit": {"identity_position": "independent-engineer"},
        "submission": {"blocks_used": {}},
    }
    result = compute_human_dimensions(entry)
    # With corpus matching, this should score much higher than tier-2 (7/6/5)
    # because the description matches devtools + languages + testing categories
    assert result["mission_alignment"] >= 7
    assert result["evidence_match"] >= 7
```

- [ ] **Step 2: Run test, verify failure** (current code returns 7/6/5 from tier-2 title match)

- [ ] **Step 3: Modify `compute_human_dimensions` auto-sourced branch**

Replace the current logic (lines 386-431) with:

```python
if "auto-sourced" in tags:
    # Prefer corpus-driven scoring from job description
    description = (entry.get("target", {}).get("description", "") or "")
    if len(description.strip()) >= 50:
        from score_text_match import corpus_match_from_description
        base = corpus_match_from_description(description)
    else:
        # Fallback to title-pattern matching when no description available
        base = estimate_role_fit_from_title(entry)

    # Existing: boost for blocks and hot skills
    ...rest of existing code unchanged...
```

- [ ] **Step 4: Run tests, verify pass**

- [ ] **Step 5: Run full score test suite**

Run: `pytest tests/test_score.py tests/test_score_human_dimensions.py tests/test_pipeline_freshness.py -q`

- [ ] **Step 6: Commit**

```bash
git commit -m "feat: corpus-driven scoring replaces title-pattern matching for auto-sourced entries"
```

---

## Chunk 3: Integration and Verification

### Task 6: End-to-end verification

- [ ] **Step 1: Source fresh jobs with descriptions**

```bash
python scripts/source_jobs.py --fetch --fresh-only --yes
```

Verify new entries have `target.description` populated.

- [ ] **Step 2: Re-score and check results**

```bash
python scripts/score.py --auto-qualify --dry-run
```

Verify: roles matching corpus skills (DevEx, CLI, testing, Python/TS) score higher than generic roles.

- [ ] **Step 3: Run full test suite**

```bash
make test
```

- [ ] **Step 4: Commit all changes**

### Task 7: Update CLAUDE.md with new scoring model

- [ ] **Step 1: Add note about corpus-driven scoring to CLAUDE.md**

Document that auto-sourced entries now use job description content matching against the user's skill corpus, with title-pattern matching as fallback only when no description is available.

- [ ] **Step 2: Commit**

---

## Key Design Decisions

1. **Description fetching is per-filtered-job, not per-all-jobs.** The Greenhouse list endpoint returns ~500-2000 jobs per board. Title filtering reduces this to ~50-100. Description fetching only happens for filtered jobs, with 100ms rate limiting (~5-10 seconds total per board).

2. **Corpus skills are hardcoded, not dynamically extracted.** Dynamically parsing all blocks at scoring time is expensive and fragile. The `CORPUS_SKILLS` dict is a curated, stable representation of the user's capabilities. Update it when the portfolio changes significantly.

3. **Description stored in YAML, not as separate files.** Capped at 5000 chars to keep YAML files manageable. This avoids the `.alchemize-work/research.md` dependency that made the existing text-match system unusable for auto-sourced entries.

4. **Title-pattern matching remains as fallback.** Some ATS APIs may not return descriptions, or descriptions may be too short. The tier system still works for those cases — it's just no longer the primary scoring path.
