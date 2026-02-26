"""Tests for scripts/distill_keywords.py pure functions."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from distill_keywords import (
    normalize_text,
    extract_keywords,
    DOMAIN_STOPWORDS,
)


# --- normalize_text ---

class TestNormalizeText:
    def test_strips_html_tags(self):
        result = normalize_text("<p>Hello <b>world</b></p>")
        assert "<" not in result
        assert ">" not in result
        assert "hello" in result
        assert "world" in result

    def test_strips_html_entities(self):
        result = normalize_text("a &amp; b &lt; c")
        assert "&amp;" not in result
        assert "&lt;" not in result

    def test_lowercases(self):
        result = normalize_text("UPPERCASE Text")
        assert result == "uppercase text"

    def test_normalizes_whitespace(self):
        result = normalize_text("hello   world\n\ttab")
        assert "  " not in result
        assert "\n" not in result
        assert "\t" not in result

    def test_strips_punctuation(self):
        result = normalize_text("hello, world! test.")
        # Commas and periods become spaces, then normalized
        assert "," not in result
        assert "!" not in result

    def test_preserves_hyphens(self):
        result = normalize_text("full-stack developer")
        assert "full-stack" in result

    def test_empty_string(self):
        assert normalize_text("") == ""


# --- extract_keywords ---

class TestExtractKeywords:
    def test_basic_extraction(self):
        text = "python developer python engineer python programming"
        keywords = extract_keywords(text, top_n=5)
        # "python" should be the top keyword
        kw_names = [kw for kw, _ in keywords]
        assert "python" in kw_names

    def test_filters_stopwords(self):
        text = "the team is looking for a candidate with experience"
        keywords = extract_keywords(text, top_n=10)
        kw_names = [kw for kw, _ in keywords]
        for stop in ["the", "team", "looking", "candidate", "experience"]:
            assert stop not in kw_names

    def test_filters_short_words(self):
        text = "an a in on do it at go up to be"
        keywords = extract_keywords(text, top_n=10)
        assert len(keywords) == 0

    def test_filters_digits(self):
        text = "123 456 789 test"
        keywords = extract_keywords(text, top_n=10)
        kw_names = [kw for kw, _ in keywords]
        assert "123" not in kw_names

    def test_bigram_extraction(self):
        text = ("machine learning engineer machine learning "
                "engineer machine learning specialist")
        keywords = extract_keywords(text, top_n=5)
        kw_names = [kw for kw, _ in keywords]
        assert "machine-learning" in kw_names

    def test_top_n_limit(self):
        text = " ".join(f"word{i}" * (10 - i) for i in range(20))
        keywords = extract_keywords(text, top_n=5)
        assert len(keywords) <= 5

    def test_returns_counts(self):
        text = "python python python javascript javascript"
        keywords = extract_keywords(text, top_n=5)
        kw_dict = dict(keywords)
        assert kw_dict.get("python", 0) == 3
        assert kw_dict.get("javascript", 0) == 2

    def test_sorted_by_count(self):
        text = "python python python javascript javascript ruby"
        keywords = extract_keywords(text, top_n=5)
        counts = [count for _, count in keywords]
        assert counts == sorted(counts, reverse=True)

    def test_empty_text(self):
        keywords = extract_keywords("", top_n=5)
        assert keywords == []

    def test_html_in_text(self):
        text = "<div>Python developer</div> <span>Python engineer</span>"
        keywords = extract_keywords(text, top_n=5)
        kw_names = [kw for kw, _ in keywords]
        assert "python" in kw_names
        assert "div" not in kw_names
        assert "span" not in kw_names


# --- DOMAIN_STOPWORDS ---

class TestDomainStopwords:
    def test_common_application_words_filtered(self):
        assert "apply" in DOMAIN_STOPWORDS
        assert "candidate" in DOMAIN_STOPWORDS
        assert "experience" in DOMAIN_STOPWORDS
        assert "requirements" in DOMAIN_STOPWORDS

    def test_domain_terms_not_in_stopwords(self):
        # Technical terms should NOT be in stopwords
        assert "python" not in DOMAIN_STOPWORDS
        assert "engineering" not in DOMAIN_STOPWORDS
        assert "software" not in DOMAIN_STOPWORDS
        assert "design" not in DOMAIN_STOPWORDS
