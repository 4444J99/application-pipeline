# Text Analysis Engine: TF-IDF Cosine Similarity for Objective Scoring

## Context

The pipeline's three "human" dimensions (mission_alignment, evidence_match, track_record_fit) currently use **metadata-only signals** — checking field presence, tag matches, enum lookups. None read actual text content. This means a posting about Kubernetes infrastructure scores the same as one about frontend design if the metadata fields match identically.

The fix: compute **TF-IDF cosine similarity** between job posting text and candidate content (blocks, resumes, profiles). Pure stdlib Python — no sklearn, no numpy. Portable to TypeScript for `life-my--midst--in` integration.

**What this replaces:** `distill_keywords.py` does frequency analysis (top-20 unigrams/bigrams) but no similarity scoring, no corpus IDF, no gap analysis, no score integration.

---

## Architecture

```
BUILD: 85+ research.md files → tokenize → compute_idf → cache to signals/text-match-corpus.yaml
MATCH: posting TF-IDF vector × content TF-IDF vector → cosine similarity → 0-2 signal score
INTEGRATE: 3 new signal functions in score.py (5th signal per human dimension, additive 0-2)
```

Three content slices per entry:
- **"mission"**: identity + framing blocks + artist statements → `_ma_text_alignment`
- **"evidence"**: evidence + methodology + project blocks → `_em_text_coverage`
- **"fit"**: resume HTML→text + profile highlights → `_tr_text_fit`

---

## Files

| File | Change |
|------|--------|
| `scripts/text_match.py` | **NEW** — Core TF-IDF engine + CLI |
| `scripts/score.py` | Add 3 signal functions + wire into `compute_human_dimensions()` at line ~976 |
| `scripts/run.py` | Add `textmatch` and `gaps` quick commands |
| `signals/text-match-corpus.yaml` | **NEW** — Cached IDF table (auto-generated) |
| `tests/test_text_match.py` | **NEW** — 30+ tests with synthetic data |

---

## Implementation Details

### 1. `scripts/text_match.py` — Core Module

**Imports:** `argparse`, `html`, `json`, `math`, `re`, `string`, `collections.Counter`, `dataclasses`, `pathlib`, `yaml` + `pipeline_lib` functions (`load_entries`, `load_block`, `load_block_index`, `load_profile`, `load_entry_by_id`, constants).

**Constants:**
- `STOPWORDS`: ~80 English + 54 domain stopwords (copied from `distill_keywords.py`, not imported)
- `MIN_DF = 2` (terms in only 1 doc are noise)
- `MAX_DF_RATIO = 0.80` (terms in >80% of docs are too generic)
- `CORPUS_CACHE_PATH = SIGNALS_DIR / "text-match-corpus.yaml"`

**Dataclasses:**
- `GapTerm(term, posting_tfidf, candidate_tfidf, gap_magnitude, suggested_blocks)`
- `TextMatchResult(entry_id, overall_similarity, mission_score, evidence_score, fit_score, gap_terms, per_block_similarity, posting_word_count, candidate_word_count, corpus_size)`

**Core functions (pure math, no side effects):**
- `normalize_text(text)` — strip HTML/markdown, lowercase, preserve hyphens
- `tokenize(text)` — unigrams only (bigrams explode vector space without sparse matrix support), filter stopwords + short tokens + digits
- `compute_tf(tokens)` → `dict[str, float]` — count/total
- `compute_idf(corpus_tokens)` → `dict[str, float]` — `log(N/df)`, filtered by MIN_DF/MAX_DF_RATIO
- `tfidf_vector(tokens, idf)` → `dict[str, float]` — sparse TF×IDF
- `cosine_similarity(vec_a, vec_b)` → `float` — dot/(mag_a×mag_b)

**Corpus builder:**
- `load_research_text(entry_id)` — reads `.alchemize-work/<id>/research.md`, strips `## Custom Questions` section
- `build_corpus()` → `(idf, doc_tokens, corpus_size)` — iterates all research dirs
- `save_corpus_cache()` / `load_corpus_cache()` — YAML cache with 7-day staleness
- `get_idf(force_rebuild=False)` — primary entry point, uses cache if fresh

**Content assembly:**
- `assemble_candidate_content(entry, content_type)` — builds text from blocks (via `load_block()`), profiles (via `load_profile()`), and resumes (HTML→text strip)
- `_strip_frontmatter(text)` — remove YAML frontmatter from blocks
- `_html_to_text(html)` — strip `<style>`, `<script>`, tags, entities

**Analysis:**
- `analyze_entry(entry_id, entry, idf, corpus_size)` → `TextMatchResult | None` — runs all 4 content types, per-block similarity, gap analysis
- `_similarity_to_score(similarity)` → `int` — maps cosine [0,1] to signal [0,2]: `<0.05→0`, `0.05-0.15→1`, `≥0.15→2`
- `_compute_gaps(posting_vec, content_vec, idf, top_n=15)` → `list[GapTerm]` — terms with high posting weight but low/zero candidate weight (gap > 50% of posting weight)
- `_find_blocks_for_term(term, tag_index)` — tag_index lookup first (fast), then block filename scan (fallback, capped at 3)

**CLI flags:** `--build-corpus`, `--target <id>`, `--all`, `--gaps`, `--blocks`, `--json`, `--top N`

### 2. `scripts/score.py` — Integration

Add at module level:
```python
_TEXT_MATCH_IDF: tuple[dict[str, float], int] | None = None

def _get_text_match_idf(): ...  # lazy-load via text_match.get_idf()
def _text_match_result(entry): ...  # graceful fallback to None
```

Three new signal functions (each returns `tuple[int, str]`):
- `_ma_text_alignment(entry)` → `(0-2, reason)` — uses `result.mission_score`
- `_em_text_coverage(entry)` → `(0-2, reason)` — uses `result.evidence_score`
- `_tr_text_fit(entry)` → `(0-2, reason)` — uses `result.fit_score`

Wire into `compute_human_dimensions()` (~line 976):
```python
# Before: mission = max(1, min(10, ma1 + ma2 + ma3 + ma4))
# After:  mission = max(1, min(10, ma1 + ma2 + ma3 + ma4 + ma5))
```
Same pattern for evidence_match (em5) and track_record_fit (tr5). Add 5th line to explain output.

**Graceful degradation:** If text_match.py import fails or no corpus exists, all 3 signals return `(0, "no research text available")` — no score regression.

### 3. `scripts/run.py` — Quick Commands

```python
"textmatch": ("text_match", []),
"gaps": ("text_match", ["--all", "--gaps"]),
```

### 4. `tests/test_text_match.py`

~30 tests using synthetic data (no real research files needed):
- `TestNormalizeText` (6): HTML stripping, markdown stripping, hyphen preservation, empty string
- `TestTokenize` (3): stopword filtering, short token filtering, technical term preservation
- `TestComputeTf` (3): basic frequency, empty tokens, single token
- `TestComputeIdf` (3): MIN_DF/MAX_DF_RATIO filtering, empty corpus
- `TestTfidfVector` (2): basic vector, IDF exclusion
- `TestCosineSimilarity` (6): identical, orthogonal, partial overlap, empty, symmetry, range
- `TestSimilarityToScore` (6): boundary values at 0, 0.05, 0.15
- `TestStripFrontmatter` (2): with/without frontmatter
- `TestComputeGaps` (3): missing terms, covered terms, sort order
- `TestAssembleCandidateContent` (3): mission includes framing, fit excludes blocks, full includes all

---

## Key Design Decisions

1. **Additive 0-2 signals, not replacement.** Text match nudges existing metadata signals — doesn't dominate. Coarse 3-tier mapping because TF-IDF without semantics is imprecise.

2. **Unigrams only.** Bigrams would explode vector dimensionality without scipy sparse matrices. Sufficient for cosine similarity; gap analysis shows adjacent gap terms for compound detection.

3. **Three content slices, not one vector.** Different blocks serve different dimensions. Identity blocks shouldn't boost evidence_match; resume shouldn't boost mission_alignment.

4. **Tag_index for gap suggestions.** `blocks/_index.yaml` inverted index is already built — use it for O(1) lookup instead of scanning 121 block files.

5. **TypeScript portability.** The 4 core math functions (`compute_tf`, `compute_idf`, `tfidf_vector`, `cosine_similarity`) are pure `dict[str, float]` → directly portable to `Map<string, number>` for `life-my--midst--in`.

---

## Verification

1. `ruff check scripts/text_match.py tests/test_text_match.py` — lint clean
2. `pytest tests/test_text_match.py -v` — all synthetic tests pass
3. `python scripts/text_match.py --build-corpus` — builds IDF from ~85 research files
4. `python scripts/text_match.py --target <known-id> --gaps` — shows similarity + gap analysis
5. `python scripts/text_match.py --all` — batch analysis
6. `python scripts/score.py --target <known-id>` — shows 5th signal line per human dimension
7. `python scripts/score.py --all --dry-run` — no score regression (text signals add 0-2, not subtract)
8. `pytest tests/ -v` — all existing tests still pass
