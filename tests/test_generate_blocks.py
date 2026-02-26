"""Tests for scripts/generate_project_blocks.py — stats extraction and rendering."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from generate_project_blocks import (
    extract_readme_stats,
    extract_stats,
    render_stats_frontmatter,
    update_block_stats,
)


# ---------------------------------------------------------------------------
# extract_readme_stats — basic badge formats
# ---------------------------------------------------------------------------


def test_extract_readme_stats_simple_test_count():
    """Parses a simple tests-N- badge."""
    text = "![tests](https://img.shields.io/badge/tests-42-brightgreen)"
    stats = extract_readme_stats(text)
    assert stats["test_count"] == 42


def test_extract_readme_stats_comma_separated_test_count():
    """Parses tests with commas like tests-1,254-."""
    text = "![tests](https://img.shields.io/badge/tests-1,254-brightgreen)"
    stats = extract_readme_stats(text)
    assert stats["test_count"] == 1254


def test_extract_readme_stats_url_encoded_plus():
    """Parses tests-85%2B%20passing- (URL-encoded '+' and space)."""
    text = "![tests](https://img.shields.io/badge/tests-85%2B%20passing-brightgreen)"
    stats = extract_readme_stats(text)
    assert stats["test_count"] == 85


def test_extract_readme_stats_url_encoded_comma():
    """Parses tests-2%2C055%20passing- (URL-encoded comma and space)."""
    text = "![tests](https://img.shields.io/badge/tests-2%2C055%20passing-brightgreen)"
    stats = extract_readme_stats(text)
    assert stats["test_count"] == 2055


def test_extract_readme_stats_url_encoded_comma_lowercase():
    """Handles lowercase URL encoding (%2c instead of %2C)."""
    text = "![tests](https://img.shields.io/badge/tests-2%2c055%20passing-brightgreen)"
    stats = extract_readme_stats(text)
    assert stats["test_count"] == 2055


def test_extract_readme_stats_coverage():
    """Parses coverage-85.7%25 badge."""
    text = "![coverage](https://img.shields.io/badge/coverage-85.7%25-green)"
    stats = extract_readme_stats(text)
    assert stats["coverage"] == 85.7


def test_extract_readme_stats_whole_number_coverage():
    """Whole-number coverage stored as int, not float."""
    text = "![coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)"
    stats = extract_readme_stats(text)
    assert stats["coverage"] == 100
    assert isinstance(stats["coverage"], int)


def test_extract_readme_stats_languages():
    """Parses lang-X- badges."""
    text = (
        "![lang](https://img.shields.io/badge/lang-Python-blue) "
        "![lang](https://img.shields.io/badge/lang-TypeScript-blue)"
    )
    stats = extract_readme_stats(text)
    assert stats["languages"] == ["python", "typescript"]


def test_extract_readme_stats_no_badges():
    """Returns empty dict when no badges found."""
    text = "# My Project\n\nJust a plain README with no badges."
    stats = extract_readme_stats(text)
    assert stats == {}


def test_extract_readme_stats_combined_badges():
    """Parses multiple badge types in one README."""
    text = (
        "![lang](https://img.shields.io/badge/lang-python-blue)\n"
        "![tests](https://img.shields.io/badge/tests-1,312-brightgreen)\n"
        "![coverage](https://img.shields.io/badge/coverage-62.7%25-yellow)"
    )
    stats = extract_readme_stats(text)
    assert stats["languages"] == ["python"]
    assert stats["test_count"] == 1312
    assert stats["coverage"] == 62.7


# ---------------------------------------------------------------------------
# extract_stats — 3-layer merge
# ---------------------------------------------------------------------------


def test_extract_stats_registry_only():
    """Registry fields populate stats when no README or seed."""
    repo = {
        "ci_workflow": "python-ci.yml",
        "public": True,
        "promotion_status": "CANDIDATE",
        "portfolio_relevance": "HIGH - important project",
    }
    stats = extract_stats(repo, None, None)
    assert stats["ci"] is True
    assert stats["languages"] == ["python"]
    assert stats["public"] is True
    assert stats["promotion_status"] == "CANDIDATE"
    assert stats["relevance"] == "HIGH"


def test_extract_stats_seed_fallback_for_language():
    """Seed.yaml language used when registry CI doesn't indicate language."""
    repo = {
        "ci_workflow": "",
        "public": False,
        "promotion_status": "",
        "portfolio_relevance": "",
    }
    seed = {"metadata": {"language": "Rust"}}
    stats = extract_stats(repo, None, seed)
    assert stats["languages"] == ["rust"]


def test_extract_stats_readme_overrides_registry_language():
    """README badge languages override registry CI-inferred language."""
    repo = {
        "ci_workflow": "python-ci.yml",
        "public": True,
        "promotion_status": "",
        "portfolio_relevance": "",
    }
    readme = "![lang](https://img.shields.io/badge/lang-typescript-blue)"
    stats = extract_stats(repo, readme, None)
    # README wins over registry
    assert stats["languages"] == ["typescript"]


def test_extract_stats_readme_adds_test_count():
    """README badge test_count is captured."""
    repo = {
        "ci_workflow": "python-ci.yml",
        "public": True,
        "promotion_status": "",
        "portfolio_relevance": "",
    }
    readme = "![tests](https://img.shields.io/badge/tests-500-green)"
    stats = extract_stats(repo, readme, None)
    assert stats["test_count"] == 500


def test_extract_stats_empty_when_no_data():
    """Returns minimal stats when repo has no useful fields."""
    repo = {
        "ci_workflow": "",
        "public": None,
        "promotion_status": "",
        "portfolio_relevance": "",
    }
    stats = extract_stats(repo, None, None)
    assert "languages" not in stats
    assert "test_count" not in stats
    assert "ci" not in stats


# ---------------------------------------------------------------------------
# render_stats_frontmatter
# ---------------------------------------------------------------------------


def test_render_stats_frontmatter_full():
    """Renders all fields when all present."""
    stats = {
        "languages": ["python", "typescript"],
        "test_count": 1254,
        "coverage": 85,
        "ci": True,
        "public": True,
        "promotion_status": "PUBLIC_PROCESS",
        "relevance": "CRITICAL",
    }
    lines = render_stats_frontmatter(stats)
    assert lines[0] == "stats:"
    assert "  languages: [python, typescript]" in lines
    assert "  test_count: 1254" in lines
    assert "  coverage: 85" in lines
    assert "  ci: true" in lines
    assert "  public: true" in lines
    assert "  promotion_status: PUBLIC_PROCESS" in lines
    assert "  relevance: CRITICAL" in lines


def test_render_stats_frontmatter_partial():
    """Only renders fields that have data."""
    stats = {"languages": ["python"], "ci": True}
    lines = render_stats_frontmatter(stats)
    assert len(lines) == 3  # stats: + languages + ci
    assert "  test_count" not in "\n".join(lines)
    assert "  coverage" not in "\n".join(lines)


# ---------------------------------------------------------------------------
# update_block_stats — field preservation (Fix 7)
# ---------------------------------------------------------------------------


def test_update_block_stats_preserves_custom_fields(tmp_path):
    """Custom frontmatter keys are preserved after stats update."""
    block = tmp_path / "test-block.md"
    block.write_text(
        "---\n"
        'title: "Test Block"\n'
        "category: projects\n"
        "tags: [python]\n"
        "audience: grant-reviewers\n"
        "tier: short\n"
        "review_status: hand-authored\n"
        "---\n"
        "\n# Content\nSome text.\n"
    )
    stats = {"languages": ["python"], "test_count": 42}
    changed = update_block_stats(block, stats)
    assert changed is True

    result = block.read_text()
    # Custom field must survive
    assert "audience: grant-reviewers" in result or "audience:" in result
    # Stats must be present
    assert "test_count: 42" in result
    assert "languages: [python]" in result
    # Content preserved
    assert "# Content" in result
    assert "Some text." in result


def test_update_block_stats_no_change_returns_false(tmp_path):
    """Returns False when new stats match existing stats."""
    block = tmp_path / "test-block.md"
    block.write_text(
        "---\n"
        'title: "Test"\n'
        "stats:\n"
        "  languages: [python]\n"
        "  test_count: 42\n"
        "---\n"
        "\nContent\n"
    )
    stats = {"languages": ["python"], "test_count": 42}
    changed = update_block_stats(block, stats)
    assert changed is False


def test_update_block_stats_updates_existing_stats(tmp_path):
    """Replaces old stats block with new one."""
    block = tmp_path / "test-block.md"
    block.write_text(
        "---\n"
        'title: "Test"\n'
        "tier: short\n"
        "stats:\n"
        "  languages: [python]\n"
        "  test_count: 10\n"
        "---\n"
        "\nContent\n"
    )
    stats = {"languages": ["python", "typescript"], "test_count": 500, "ci": True}
    changed = update_block_stats(block, stats)
    assert changed is True

    result = block.read_text()
    assert "test_count: 500" in result
    assert "test_count: 10" not in result
    assert "ci: true" in result
    assert "tier: short" in result
