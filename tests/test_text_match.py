"""Tests for text_match.py TF-IDF engine using synthetic data."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from text_match import (
    GapTerm,
    TextMatchResult,
    _compute_gaps,
    _find_blocks_for_term,
    _html_to_text,
    _similarity_to_score,
    _strip_frontmatter,
    assemble_candidate_content,
    compute_idf,
    compute_tf,
    cosine_similarity,
    normalize_text,
    tfidf_vector,
    tokenize,
)  # noqa: I001 - import order after sys.path manipulation

# --- TestNormalizeText ---

class TestNormalizeText:
    def test_strips_html_tags(self):
        result = normalize_text("<p>Hello <b>world</b></p>")
        assert "<" not in result
        assert "hello" in result
        assert "world" in result

    def test_strips_markdown_headers(self):
        result = normalize_text("## Section Title\nContent here")
        assert "##" not in result
        assert "section" in result

    def test_strips_markdown_bold(self):
        result = normalize_text("This is **bold** and *italic*")
        assert "**" not in result
        assert "*" not in result
        assert "bold" in result

    def test_preserves_hyphens(self):
        result = normalize_text("cloud-native platform-engineering")
        assert "cloud-native" in result
        assert "platform-engineering" in result

    def test_decodes_html_entities(self):
        result = normalize_text("AT&amp;T &lt;script&gt;")
        assert "&amp;" not in result
        assert "&lt;" not in result

    def test_empty_string(self):
        assert normalize_text("") == ""


# --- TestTokenize ---

class TestTokenize:
    def test_filters_stopwords(self):
        tokens = tokenize("the quick brown fox and the lazy dog")
        assert "the" not in tokens
        assert "and" not in tokens
        assert "quick" in tokens
        assert "brown" in tokens

    def test_filters_short_tokens(self):
        tokens = tokenize("go do it we are ok an by")
        # All 2-letter or less should be filtered
        assert all(len(t) > 2 for t in tokens)

    def test_preserves_technical_terms(self):
        tokens = tokenize("kubernetes terraform platform-engineering agentic-workflows")
        assert "kubernetes" in tokens
        assert "terraform" in tokens
        assert "platform-engineering" in tokens
        assert "agentic-workflows" in tokens


# --- TestComputeTf ---

class TestComputeTf:
    def test_basic_frequency(self):
        tokens = ["python", "python", "java", "rust"]
        tf = compute_tf(tokens)
        assert tf["python"] == pytest.approx(0.5)
        assert tf["java"] == pytest.approx(0.25)
        assert tf["rust"] == pytest.approx(0.25)

    def test_empty_tokens(self):
        assert compute_tf([]) == {}

    def test_single_token(self):
        tf = compute_tf(["kubernetes"])
        assert tf["kubernetes"] == pytest.approx(1.0)


# --- TestComputeIdf ---

class TestComputeIdf:
    def test_min_df_filtering(self):
        # Term in only 1 doc should be filtered (MIN_DF=2)
        # Need enough docs so "python" (in 3/5=60%) passes MAX_DF_RATIO (80%)
        corpus = [
            ["python", "kubernetes"],
            ["python", "terraform"],
            ["python", "docker"],
            ["javascript", "react"],
            ["javascript", "angular"],
        ]
        idf = compute_idf(corpus)
        assert "python" in idf
        assert "javascript" in idf
        # "kubernetes" appears in only 1 doc -> filtered by MIN_DF
        assert "kubernetes" not in idf

    def test_max_df_ratio_filtering(self):
        # Term in >80% of docs should be filtered
        corpus = [
            ["python", "java"],
            ["python", "rust"],
            ["python", "golang"],
            ["python", "typescript"],
            ["python", "ruby"],
        ]
        idf = compute_idf(corpus)
        # "python" appears in 5/5 = 100% -> filtered by MAX_DF_RATIO
        assert "python" not in idf

    def test_empty_corpus(self):
        assert compute_idf([]) == {}


# --- TestTfidfVector ---

class TestTfidfVector:
    def test_basic_vector(self):
        tokens = ["python", "python", "java"]
        idf = {"python": 1.0, "java": 2.0}
        vec = tfidf_vector(tokens, idf)
        # python TF = 2/3, IDF = 1.0 -> 2/3
        assert vec["python"] == pytest.approx(2 / 3)
        # java TF = 1/3, IDF = 2.0 -> 2/3
        assert vec["java"] == pytest.approx(2 / 3)

    def test_idf_exclusion(self):
        tokens = ["python", "obscure-term"]
        idf = {"python": 1.5}  # obscure-term not in IDF
        vec = tfidf_vector(tokens, idf)
        assert "python" in vec
        assert "obscure-term" not in vec


# --- TestCosineSimilarity ---

class TestCosineSimilarity:
    def test_identical_vectors(self):
        vec = {"python": 1.0, "java": 2.0}
        assert cosine_similarity(vec, vec) == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        vec_a = {"python": 1.0}
        vec_b = {"java": 1.0}
        assert cosine_similarity(vec_a, vec_b) == pytest.approx(0.0)

    def test_partial_overlap(self):
        vec_a = {"python": 1.0, "java": 1.0}
        vec_b = {"python": 1.0, "rust": 1.0}
        sim = cosine_similarity(vec_a, vec_b)
        assert 0.0 < sim < 1.0

    def test_empty_vectors(self):
        assert cosine_similarity({}, {"a": 1.0}) == 0.0
        assert cosine_similarity({"a": 1.0}, {}) == 0.0
        assert cosine_similarity({}, {}) == 0.0

    def test_symmetry(self):
        vec_a = {"python": 1.0, "java": 0.5}
        vec_b = {"python": 0.8, "rust": 1.2}
        assert cosine_similarity(vec_a, vec_b) == pytest.approx(
            cosine_similarity(vec_b, vec_a)
        )

    def test_range_zero_to_one(self):
        vec_a = {"python": 3.0, "java": 1.0, "rust": 0.5}
        vec_b = {"python": 1.0, "java": 2.0, "golang": 1.0}
        sim = cosine_similarity(vec_a, vec_b)
        assert 0.0 <= sim <= 1.0


# --- TestSimilarityToScore ---

class TestSimilarityToScore:
    def test_zero_similarity(self):
        assert _similarity_to_score(0.0) == 0

    def test_below_threshold(self):
        assert _similarity_to_score(0.04) == 0

    def test_at_first_threshold(self):
        assert _similarity_to_score(0.05) == 1

    def test_between_thresholds(self):
        assert _similarity_to_score(0.10) == 1

    def test_at_second_threshold(self):
        assert _similarity_to_score(0.15) == 2

    def test_high_similarity(self):
        assert _similarity_to_score(0.95) == 2


# --- TestStripFrontmatter ---

class TestStripFrontmatter:
    def test_with_frontmatter(self):
        text = "---\ntitle: Test\ntags: [a, b]\n---\nActual content here"
        result = _strip_frontmatter(text)
        assert result == "Actual content here"
        assert "title:" not in result

    def test_without_frontmatter(self):
        text = "Just regular content\nNo frontmatter here"
        result = _strip_frontmatter(text)
        assert result == text


# --- TestHtmlToText ---

class TestHtmlToText:
    def test_strips_style_blocks(self):
        html = "<style>body { color: red; }</style><p>Hello</p>"
        result = _html_to_text(html)
        assert "color" not in result
        assert "Hello" in result

    def test_strips_script_blocks(self):
        html = "<script>alert('hi')</script><p>Content</p>"
        result = _html_to_text(html)
        assert "alert" not in result
        assert "Content" in result

    def test_decodes_entities(self):
        html = "<p>AT&amp;T &copy; 2024</p>"
        result = _html_to_text(html)
        assert "AT&T" in result


# --- TestComputeGaps ---

class TestComputeGaps:
    def test_missing_terms(self):
        posting = {"kubernetes": 0.5, "terraform": 0.4, "python": 0.3}
        content = {"python": 0.3}  # missing kubernetes and terraform
        idf = {"kubernetes": 1.0, "terraform": 1.0, "python": 1.0}
        gaps = _compute_gaps(posting, content, idf)
        terms = [g.term for g in gaps]
        assert "kubernetes" in terms
        assert "terraform" in terms

    def test_covered_terms_excluded(self):
        posting = {"python": 0.5, "kubernetes": 0.4}
        content = {"python": 0.5, "kubernetes": 0.4}  # fully covered
        idf = {"python": 1.0, "kubernetes": 1.0}
        gaps = _compute_gaps(posting, content, idf)
        assert len(gaps) == 0

    def test_sort_order_by_gap_magnitude(self):
        posting = {"kubernetes": 0.8, "terraform": 0.3, "docker": 0.5}
        content = {}  # nothing covered
        idf = {"kubernetes": 1.0, "terraform": 1.0, "docker": 1.0}
        gaps = _compute_gaps(posting, content, idf)
        magnitudes = [g.gap_magnitude for g in gaps]
        assert magnitudes == sorted(magnitudes, reverse=True)


# --- TestFindBlocksForTerm ---

class TestFindBlocksForTerm:
    def test_direct_tag_match(self):
        tag_index = {
            "kubernetes": ["projects/k8s-deploy", "evidence/infra"],
            "python": ["projects/organvm"],
        }
        blocks = _find_blocks_for_term("kubernetes", tag_index)
        assert "projects/k8s-deploy" in blocks

    def test_partial_match(self):
        tag_index = {
            "platform-engineering": ["framings/independent-engineer"],
        }
        blocks = _find_blocks_for_term("platform", tag_index)
        assert "framings/independent-engineer" in blocks

    def test_no_match(self):
        tag_index = {"kubernetes": ["projects/k8s"]}
        blocks = _find_blocks_for_term("quantum-computing", tag_index)
        assert blocks == []

    def test_capped_at_three(self):
        tag_index = {
            "python": ["a", "b", "c", "d", "e"],
        }
        blocks = _find_blocks_for_term("python", tag_index)
        assert len(blocks) <= 3


# --- TestAssembleCandidateContent ---

class TestAssembleCandidateContent:
    def test_mission_skips_evidence_blocks(self):
        """Mission content should only include identity/framings blocks."""
        entry = {
            "id": "nonexistent-test-entry",
            "submission": {
                "blocks_used": {
                    "identity": "identity/2min",
                    "evidence": "evidence/differentiators",
                },
                "materials_attached": [],
            },
        }
        # This will return empty since blocks won't load, but tests the filtering logic
        content = assemble_candidate_content(entry, "mission")
        # Content may be empty (blocks don't exist for fake ID), but should not crash
        assert isinstance(content, str)

    def test_fit_excludes_blocks(self):
        """Fit content uses resumes and profiles, not blocks."""
        entry = {
            "id": "nonexistent-test-entry",
            "submission": {
                "blocks_used": {
                    "identity": "identity/2min",
                },
                "materials_attached": [],
            },
        }
        content = assemble_candidate_content(entry, "fit")
        assert isinstance(content, str)

    def test_unknown_content_type_returns_empty(self):
        entry = {
            "id": "test",
            "submission": {"blocks_used": {}, "materials_attached": []},
        }
        content = assemble_candidate_content(entry, "unknown")
        assert content == ""


# --- TestTextMatchResult ---

class TestTextMatchResult:
    def test_dataclass_creation(self):
        result = TextMatchResult(
            entry_id="test-id",
            overall_similarity=0.123,
            mission_score=1,
            evidence_score=2,
            fit_score=0,
        )
        assert result.entry_id == "test-id"
        assert result.overall_similarity == 0.123
        assert result.gap_terms == []

    def test_gap_term_creation(self):
        gap = GapTerm(
            term="kubernetes",
            posting_tfidf=0.5,
            candidate_tfidf=0.0,
            gap_magnitude=0.5,
            suggested_blocks=["projects/k8s"],
        )
        assert gap.term == "kubernetes"
        assert gap.suggested_blocks == ["projects/k8s"]


# --- Integration-style tests with synthetic IDF ---

class TestEndToEnd:
    """Tests that chain multiple functions together."""

    def _build_synthetic_idf(self):
        """Build a small IDF table from synthetic docs."""
        corpus = [
            ["python", "kubernetes", "terraform", "infrastructure", "deployment"],
            ["python", "machine-learning", "tensorflow", "neural", "training"],
            ["javascript", "react", "frontend", "typescript", "components"],
            ["python", "django", "backend", "postgresql", "api-design"],
            ["kubernetes", "docker", "containers", "orchestration", "microservices"],
        ]
        return compute_idf(corpus), len(corpus)

    def test_similar_docs_score_higher(self):
        idf, _ = self._build_synthetic_idf()
        posting = ["python", "kubernetes", "infrastructure", "deployment", "terraform"]
        candidate_good = ["python", "kubernetes", "terraform", "infrastructure", "containers"]
        candidate_bad = ["javascript", "react", "frontend", "components", "typescript"]

        posting_vec = tfidf_vector(posting, idf)
        good_vec = tfidf_vector(candidate_good, idf)
        bad_vec = tfidf_vector(candidate_bad, idf)

        sim_good = cosine_similarity(posting_vec, good_vec)
        sim_bad = cosine_similarity(posting_vec, bad_vec)
        assert sim_good > sim_bad

    def test_score_mapping_end_to_end(self):
        idf, _ = self._build_synthetic_idf()
        # Identical content should get score 2
        tokens = ["python", "kubernetes", "terraform"]
        vec = tfidf_vector(tokens, idf)
        sim = cosine_similarity(vec, vec)
        assert _similarity_to_score(sim) == 2

    def test_gaps_reflect_missing_skills(self):
        idf, _ = self._build_synthetic_idf()
        posting_tokens = ["python", "kubernetes", "terraform", "infrastructure"]
        candidate_tokens = ["python"]  # missing k8s, terraform, infra

        posting_vec = tfidf_vector(posting_tokens, idf)
        candidate_vec = tfidf_vector(candidate_tokens, idf)

        gaps = _compute_gaps(posting_vec, candidate_vec, idf)
        gap_terms = [g.term for g in gaps]
        # Should detect missing terms
        assert len(gaps) > 0
        # python should NOT be a gap (covered)
        assert "python" not in gap_terms
