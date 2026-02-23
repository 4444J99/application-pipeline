"""Tests for scripts/compose.py"""

import sys
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from compose import compose, find_entry, count_words


def test_compose_with_blocks():
    """Compose should produce output when blocks_used has valid paths."""
    entry = {
        "id": "creative-capital-2027",
        "name": "Creative Capital 2027 Open Call",
        "track": "grant",
        "status": "qualified",
        "target": {"organization": "Creative Capital"},
        "deadline": {"date": "2026-04-02", "time": "15:00 ET"},
        "submission": {
            "blocks_used": {
                "artist_statement": "identity/2min",
                "project_description": "projects/organvm-system",
            },
            "variant_ids": {},
            "materials_attached": [],
            "portfolio_url": "https://4444j99.github.io/portfolio/",
        },
    }
    result = compose(entry)
    assert "# Submission: Creative Capital 2027 Open Call" in result
    assert "## Artist Statement" in result
    assert "## Project Description" in result
    assert "**Portfolio:** https://4444j99.github.io/portfolio/" in result


def test_compose_missing_blocks():
    """Compose should handle missing blocks gracefully."""
    entry = {
        "id": "test",
        "name": "Test",
        "track": "grant",
        "status": "qualified",
        "target": {"organization": "Test Org"},
        "submission": {
            "blocks_used": {
                "nonexistent": "does-not/exist",
            },
            "variant_ids": {},
            "materials_attached": [],
        },
    }
    result = compose(entry)
    assert "*Block not found: does-not/exist*" in result


def test_compose_no_submission():
    """Compose should handle entries without submission config."""
    entry = {
        "id": "test",
        "name": "Test",
        "track": "grant",
        "status": "research",
        "target": {"organization": "Test Org"},
        "submission": "not-a-dict",
    }
    result = compose(entry)
    assert "*No submission blocks configured.*" in result


def test_compose_missing_submission_key():
    """Compose should handle entries with no submission key at all."""
    entry = {
        "id": "test",
        "name": "Test",
        "track": "grant",
        "status": "research",
        "target": {"organization": "Test Org"},
    }
    result = compose(entry)
    assert "# Submission: Test" in result


def test_compose_empty_blocks():
    """Compose should handle empty blocks_used dict."""
    entry = {
        "id": "test",
        "name": "Test",
        "track": "grant",
        "status": "qualified",
        "target": {"organization": "Test Org"},
        "submission": {
            "blocks_used": {},
            "variant_ids": {},
            "materials_attached": [],
        },
    }
    result = compose(entry)
    assert "# Submission: Test" in result


def test_count_words():
    """count_words should return accurate word counts."""
    assert count_words("one two three") == 3
    assert count_words("") == 0
    assert count_words("single") == 1


def test_find_entry_returns_dict():
    """find_entry should return a dict for a known entry."""
    entry = find_entry("creative-capital-2027")
    assert entry is not None
    assert isinstance(entry, dict)
    assert entry["id"] == "creative-capital-2027"


def test_find_entry_returns_none_for_unknown():
    """find_entry should return None for an unknown entry."""
    entry = find_entry("definitely-does-not-exist-12345")
    assert entry is None


def test_compose_includes_materials():
    """Compose should list attached materials."""
    entry = {
        "id": "test",
        "name": "Test",
        "track": "grant",
        "status": "qualified",
        "target": {"organization": "Test Org"},
        "submission": {
            "blocks_used": {},
            "variant_ids": {},
            "materials_attached": ["resumes/cv.pdf", "samples/portfolio.pdf"],
        },
    }
    result = compose(entry)
    assert "## Attached Materials" in result
    assert "- resumes/cv.pdf" in result
    assert "- samples/portfolio.pdf" in result
