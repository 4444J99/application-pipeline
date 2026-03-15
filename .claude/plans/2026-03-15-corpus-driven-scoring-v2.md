# Corpus-Driven Scoring Implementation Plan (v2)

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace title-pattern scoring with living-corpus scoring. The blocks directory, resume content, and project descriptions ARE the skill fingerprint — dynamically read, never hardcoded. Job descriptions are fetched at sourcing time and scored against this living corpus via TF-IDF cosine similarity.

**Architecture:** Two new capabilities: (1) `source_jobs.py` fetches full job descriptions from ATS APIs and stores them in entry YAML. (2) A corpus fingerprint builder reads ALL blocks, resumes, and project content to create a TF-IDF vector representing "everything this person does." Job descriptions are scored against this fingerprint. As the corpus grows (new blocks, essays, projects), the fingerprint automatically reflects the full scope of work — no manual curation.

**Tech Stack:** Python stdlib. Extends existing `text_match.py` TF-IDF engine. No new dependencies.

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `scripts/source_jobs.py` | Modify | Add description fetching to Greenhouse/Lever/Ashby sourcing |
| `scripts/corpus_fingerprint.py` | Create | Build and cache TF-IDF vector from ALL blocks, resumes, project docs |
| `scripts/score_human_dimensions.py` | Modify | Replace title-pattern fallback with corpus similarity for auto-sourced entries |
| `scripts/score_text_match.py` | Modify | Add `score_description_against_corpus()` using corpus fingerprint |
| `tests/test_corpus_fingerprint.py` | Create | Tests for fingerprint building and caching |
| `tests/test_score_human_dimensions.py` | Modify | Tests for corpus-driven scoring path |
| `tests/test_source_jobs.py` | Modify | Tests for description fetching |

**Not modified:** `scripts/score_constants.py` — no hardcoded skills. The corpus IS the skills.

---

## Chunk 1: Fetch Job Descriptions at Sourcing Time

### Task 1: Add description fetching to Greenhouse sourcing

**Files:**
- Modify: `scripts/source_jobs.py` — `fetch_greenhouse_jobs()` (~line 315)
- Test: `tests/test_source_jobs.py`

The Greenhouse list endpoint (`/v1/boards/{token}/jobs`) returns title/location/URL but no description. The single-job endpoint (`/v1/boards/{token}/jobs/{id}`) returns a `content` field with full HTML description (~30K chars). Only fetch for jobs that pass the title filter.

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
        "content": "<p>Build developer tools in Python and TypeScript.</p>",
        "title": "Software Engineer, Developer Experience",
    })

    def fake_http_get(url):
        if url.endswith("/123"):
            return fake_detail.encode()
        return fake_list.encode()

    monkeypatch.setattr(source_jobs, "_http_get", fake_http_get)
    jobs = source_jobs.fetch_greenhouse_jobs("test-board")
    assert len(jobs) == 1
    assert "developer tools" in jobs[0].get("description", "").lower()
```

- [ ] **Step 2: Run test, verify it fails**

Run: `pytest tests/test_source_jobs.py::test_greenhouse_job_includes_description -v`

- [ ] **Step 3: Implement description fetching**

After the list fetch, for each job: GET `/v1/boards/{token}/jobs/{id}` to get `content`. Strip HTML via `text_match.normalize_text()`. Cap at 5000 chars. Store as `description` in the job dict.

Key constraints:
- Only fetch for jobs passing `_passes_title_filter()` (already exists)
- 100ms sleep between detail fetches (rate limit)
- If detail fetch fails, continue with empty description (non-blocking)
- Store plain text, not HTML

- [ ] **Step 4: Run test, verify pass**

- [ ] **Step 5: Add description to pipeline YAML entry template**

In `_create_entry()` (~line 724), add under `target`:
```python
"description": job.get("description", ""),
```

- [ ] **Step 6: Commit**

### Task 2: Add description fetching to Lever and Ashby

**Files:**
- Modify: `scripts/source_jobs.py` — `fetch_lever_jobs()`, `fetch_ashby_jobs()`

Lever returns `descriptionPlain` per job in the list response. Ashby returns `descriptionHtml`. These don't need extra API calls.

- [ ] **Step 1: Write tests**
- [ ] **Step 2: Extract from Lever** (`descriptionPlain` field, or `description` stripped of HTML)
- [ ] **Step 3: Extract from Ashby** (`descriptionHtml`, strip HTML)
- [ ] **Step 4: Run tests, verify pass**
- [ ] **Step 5: Commit**

---

## Chunk 2: Living Corpus Fingerprint

### Task 3: Build the corpus fingerprint module

**Files:**
- Create: `scripts/corpus_fingerprint.py`
- Test: `tests/test_corpus_fingerprint.py`

The fingerprint is a TF-IDF vector built from the ENTIRE blocks directory, all resume base files, and project README content. It represents "everything this person has done and can do." It's rebuilt when stale (>24h) or on demand, and cached to `signals/corpus-fingerprint.yaml`.

- [ ] **Step 1: Write failing test**

```python
def test_build_fingerprint_reads_all_blocks(tmp_path):
    """Fingerprint should include terms from all block files."""
    blocks = tmp_path / "blocks"
    blocks.mkdir()
    (blocks / "devtools.md").write_text("---\ntitle: devtools\n---\nPython CLI tooling pytest GitHub Actions")
    (blocks / "teaching.md").write_text("---\ntitle: teaching\n---\nComposition pedagogy curriculum 2000 students")

    fp = build_corpus_fingerprint(blocks_dir=blocks)
    assert "python" in fp.terms
    assert "pedagogy" in fp.terms
    assert "pytest" in fp.terms
    assert fp.term_count > 5

def test_fingerprint_similarity_high_for_matching_description(tmp_path):
    """Description matching corpus content should score high."""
    blocks = tmp_path / "blocks"
    blocks.mkdir()
    (blocks / "eng.md").write_text("---\ntitle: eng\n---\nPython TypeScript React CI/CD GitHub Actions pytest Docker CLI developer tools")

    fp = build_corpus_fingerprint(blocks_dir=blocks)
    score = fp.score_description("Looking for Python and TypeScript developer with CI/CD and testing experience")
    assert score > 0.15  # meaningful similarity

def test_fingerprint_similarity_low_for_unrelated_description(tmp_path):
    """Description with no corpus overlap should score low."""
    blocks = tmp_path / "blocks"
    blocks.mkdir()
    (blocks / "eng.md").write_text("---\ntitle: eng\n---\nPython TypeScript React CI/CD GitHub Actions pytest Docker CLI developer tools")

    fp = build_corpus_fingerprint(blocks_dir=blocks)
    score = fp.score_description("iOS Swift UIKit CoreData Xcode App Store mobile native development")
    assert score < 0.05  # near zero similarity
```

- [ ] **Step 2: Run tests, verify failure**

- [ ] **Step 3: Implement `corpus_fingerprint.py`**

```python
"""Living corpus fingerprint — TF-IDF vector built from all blocks, resumes, and project content.

The blocks directory IS the corpus. As blocks are added, modified, or removed,
the fingerprint automatically reflects the full scope of work on next rebuild.

Usage:
    from corpus_fingerprint import get_fingerprint
    fp = get_fingerprint()
    similarity = fp.score_description("job description text here")
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from pipeline_lib import BLOCKS_DIR, REPO_ROOT, SIGNALS_DIR

# Cache staleness threshold (seconds)
CACHE_MAX_AGE = 86400  # 24 hours

CACHE_PATH = SIGNALS_DIR / "corpus-fingerprint-cache.yaml"

# Content sources
RESUME_BASE_DIR = REPO_ROOT / "materials" / "resumes" / "base"
BLOCKS_ROOT = BLOCKS_DIR


@dataclass
class CorpusFingerprint:
    """TF-IDF vector representing the user's full body of work."""
    tfidf_vector: dict[str, float]
    terms: set[str]
    term_count: int
    source_file_count: int
    built_at: float

    def score_description(self, description: str) -> float:
        """Compute cosine similarity between this fingerprint and a job description."""
        from text_match import cosine_similarity, tfidf_vector, tokenize, compute_idf

        desc_tokens = tokenize(description)
        if not desc_tokens:
            return 0.0

        # Build a minimal IDF from just these two documents
        # (the corpus text and the description)
        corpus_tokens = list(self.terms)
        idf = compute_idf([corpus_tokens, desc_tokens])

        desc_vec = tfidf_vector(desc_tokens, idf)
        corpus_vec = tfidf_vector(corpus_tokens, idf)

        return cosine_similarity(corpus_vec, desc_vec)


def _read_all_blocks(blocks_dir: Path | None = None) -> str:
    """Read and concatenate all block markdown files, stripping frontmatter."""
    root = blocks_dir or BLOCKS_ROOT
    parts = []
    for md in sorted(root.rglob("*.md")):
        if md.name.startswith("_") or md.name == "README.md":
            continue
        text = md.read_text(encoding="utf-8", errors="replace")
        # Strip YAML frontmatter
        if text.startswith("---"):
            end = text.find("---", 3)
            if end != -1:
                text = text[end + 3:]
        parts.append(text)
    return " ".join(parts)


def _read_all_resumes(resume_dir: Path | None = None) -> str:
    """Read base resume HTML files and extract text."""
    root = resume_dir or RESUME_BASE_DIR
    if not root.exists():
        return ""
    from text_match import normalize_text
    parts = []
    for html_file in sorted(root.glob("*.html")):
        parts.append(normalize_text(html_file.read_text(encoding="utf-8", errors="replace")))
    return " ".join(parts)


def build_corpus_fingerprint(
    blocks_dir: Path | None = None,
    resume_dir: Path | None = None,
) -> CorpusFingerprint:
    """Build a TF-IDF fingerprint from all blocks and resumes."""
    from text_match import compute_idf, compute_tf, tokenize

    all_text = _read_all_blocks(blocks_dir) + " " + _read_all_resumes(resume_dir)
    tokens = tokenize(all_text)

    # For IDF, treat each block file as a separate document
    root = blocks_dir or BLOCKS_ROOT
    per_doc_tokens = []
    for md in sorted(root.rglob("*.md")):
        if md.name.startswith("_") or md.name == "README.md":
            continue
        text = md.read_text(encoding="utf-8", errors="replace")
        doc_tokens = tokenize(text)
        if doc_tokens:
            per_doc_tokens.append(doc_tokens)

    idf = compute_idf(per_doc_tokens) if per_doc_tokens else {}
    tf = compute_tf(tokens)
    tfidf = {term: tf.get(term, 0) * idf.get(term, 1.0) for term in set(tf) | set(idf) if term in tf}

    terms = set(tokens)
    source_count = len(per_doc_tokens)

    return CorpusFingerprint(
        tfidf_vector=tfidf,
        terms=terms,
        term_count=len(terms),
        source_file_count=source_count,
        built_at=time.time(),
    )


# Module-level cache
_cached_fingerprint: CorpusFingerprint | None = None


def get_fingerprint() -> CorpusFingerprint:
    """Get the corpus fingerprint, rebuilding if stale or missing."""
    global _cached_fingerprint
    now = time.time()
    if _cached_fingerprint and (now - _cached_fingerprint.built_at) < CACHE_MAX_AGE:
        return _cached_fingerprint

    _cached_fingerprint = build_corpus_fingerprint()
    return _cached_fingerprint
```

- [ ] **Step 4: Run tests, verify pass**

- [ ] **Step 5: Commit**

```bash
git add scripts/corpus_fingerprint.py tests/test_corpus_fingerprint.py
git commit -m "feat: living corpus fingerprint from blocks and resume content"
```

---

## Chunk 3: Wire Corpus Scoring Into Dimensions

### Task 4: Add `score_description_against_corpus()` to score_text_match

**Files:**
- Modify: `scripts/score_text_match.py`

- [ ] **Step 1: Write failing test**

```python
def test_score_description_against_corpus_returns_dimensions(monkeypatch, tmp_path):
    """Should return mission_alignment, evidence_match, track_record_fit from corpus similarity."""
    import corpus_fingerprint

    blocks = tmp_path / "blocks"
    blocks.mkdir()
    (blocks / "skills.md").write_text("---\ntitle: t\n---\nPython TypeScript React pytest CI/CD Docker GitHub Actions CLI developer tools documentation")

    monkeypatch.setattr(corpus_fingerprint, "BLOCKS_ROOT", blocks)
    monkeypatch.setattr(corpus_fingerprint, "_cached_fingerprint", None)

    from score_text_match import score_description_against_corpus
    result = score_description_against_corpus("Python TypeScript developer with CI/CD and testing experience")
    assert "mission_alignment" in result
    assert "evidence_match" in result
    assert "track_record_fit" in result
    assert result["mission_alignment"] >= 6
```

- [ ] **Step 2: Implement**

```python
def score_description_against_corpus(description: str) -> dict[str, int]:
    """Score a job description against the living corpus fingerprint.

    Returns dimension scores derived from cosine similarity between
    the job description and the full corpus of blocks/resume/projects.
    """
    if not description or len(description.strip()) < 50:
        return {"mission_alignment": 5, "evidence_match": 4, "track_record_fit": 4}

    from corpus_fingerprint import get_fingerprint
    fp = get_fingerprint()
    similarity = fp.score_description(description)

    # Map similarity to scores
    # Calibrated from manual inspection:
    # 0.00-0.03 = no overlap (3), 0.03-0.08 = weak (5), 0.08-0.15 = moderate (7), 0.15+ = strong (9)
    def sim_to_score(s: float) -> int:
        if s >= 0.20: return 10
        if s >= 0.15: return 9
        if s >= 0.12: return 8
        if s >= 0.08: return 7
        if s >= 0.05: return 6
        if s >= 0.03: return 5
        if s >= 0.01: return 4
        return 3

    score = sim_to_score(similarity)
    return {
        "mission_alignment": score,
        "evidence_match": score,
        "track_record_fit": max(3, score - 1),
    }
```

- [ ] **Step 3: Run tests, verify pass**
- [ ] **Step 4: Commit**

### Task 5: Wire into compute_human_dimensions

**Files:**
- Modify: `scripts/score_human_dimensions.py` — auto-sourced branch (~line 386)

- [ ] **Step 1: Write failing test**

```python
def test_auto_sourced_with_description_uses_corpus(monkeypatch):
    """Auto-sourced entry with description should use corpus scoring, not title patterns."""
    entry = {
        "name": "Software Engineer",  # Generic title → tier-2 (7/6/5) in title system
        "tags": ["auto-sourced"],
        "track": "job",
        "target": {"description": "Build developer tools and CLI infrastructure in Python and TypeScript. Testing with pytest, CI/CD with GitHub Actions."},
        "fit": {"identity_position": "independent-engineer"},
        "submission": {"blocks_used": {}},
    }
    # Should score higher than tier-2 because description matches corpus
    result = compute_human_dimensions(entry)
    assert result["evidence_match"] >= 7
```

- [ ] **Step 2: Modify auto-sourced branch**

```python
if "auto-sourced" in tags:
    description = (entry.get("target", {}).get("description", "") or "")
    if len(description.strip()) >= 50:
        from score_text_match import score_description_against_corpus
        base = score_description_against_corpus(description)
    else:
        base = estimate_role_fit_from_title(entry)
    # ...rest of existing hot-skills boost logic unchanged...
```

- [ ] **Step 3: Run tests, verify pass**
- [ ] **Step 4: Run full test suite**: `pytest tests/test_score.py tests/test_score_human_dimensions.py -q`
- [ ] **Step 5: Commit**

---

## Chunk 4: Integration and Verification

### Task 6: End-to-end test

- [ ] **Step 1: Source fresh jobs with descriptions**
```bash
python scripts/source_jobs.py --fetch --fresh-only --yes
```
Verify entries have `target.description` populated.

- [ ] **Step 2: Check corpus fingerprint**
```bash
python -c "from corpus_fingerprint import get_fingerprint; fp = get_fingerprint(); print(f'Corpus: {fp.term_count} terms from {fp.source_file_count} files')"
```

- [ ] **Step 3: Re-score and check**
```bash
python scripts/score.py --auto-qualify --dry-run
```
Verify: roles whose descriptions match the corpus score higher than unrelated roles.

- [ ] **Step 4: Full test suite**
```bash
make test
```

- [ ] **Step 5: Final commit**

---

## Key Design Decisions

1. **No hardcoded skills.** The blocks directory IS the corpus. Add a block about Kubernetes → the system starts recognizing Kubernetes roles. Write an essay about governance-as-artwork → governance terms enter the fingerprint. The corpus is amorphous and grows with the work.

2. **Fingerprint cached for 24h.** Building the fingerprint reads ~50 block files and ~5 resume files — fast enough (~100ms) but unnecessary to repeat every scoring call. Cache invalidates daily, ensuring new blocks are picked up within a day.

3. **Similarity thresholds calibrated empirically.** The `sim_to_score()` mapping needs tuning against real data. After the first batch of scored entries, run `python scripts/score.py --all --explain` to inspect similarity values and adjust thresholds.

4. **Title matching remains as fallback.** When no job description is available (API limitation), the tier system still provides a reasonable estimate. But it's no longer the primary path — most entries will have descriptions.

5. **Description stored in YAML entry, not separate files.** Capped at 5000 chars. Avoids the `.alchemize-work/research.md` dependency that made text-match unusable for bulk entries.
