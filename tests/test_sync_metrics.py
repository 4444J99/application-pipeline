"""Tests for scripts/sync_metrics.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from sync_metrics import (
    CANONICAL_METRICS,
    _normalize_number,
    check_file,
    collect_scan_files,
    parse_canonical_metrics,
)

# --- TestNormalizeNumber ---


def test_normalize_plain_integer():
    assert _normalize_number("103") == 103


def test_normalize_comma_formatted():
    assert _normalize_number("2,349") == 2349


def test_normalize_plus_suffix():
    assert _normalize_number("94+") == 94


def test_normalize_comma_and_plus():
    assert _normalize_number("1,000+") == 1000


def test_normalize_invalid_returns_minus_one():
    assert _normalize_number("N/A") == -1


def test_normalize_empty_string():
    assert _normalize_number("") == -1


def test_normalize_alpha_string():
    assert _normalize_number("twenty") == -1


def test_normalize_large_number():
    assert _normalize_number("21,160") == 21160


# --- TestCheckFile ---


def test_check_file_matching_canonical(tmp_path):
    """Exact canonical match → no discrepancy returned (empty list without verbose)."""
    filepath = tmp_path / "test.md"
    filepath.write_text("We have 103 repositories in the system.\n")
    metrics = {
        "repositories": {
            "canonical": "103",
            "pattern": r"\b(1\d{2})\s*(?:repositories|repos)\b",
            "description": "Total repositories",
        }
    }
    results = check_file(filepath, metrics, verbose=False)
    stale = [r for r in results if r["status"] == "stale"]
    assert stale == []


def test_check_file_stale_number(tmp_path, monkeypatch):
    """Different number → discrepancy record returned."""
    import sync_metrics as sm
    monkeypatch.setattr(sm, "REPO_ROOT", tmp_path)
    filepath = tmp_path / "test.md"
    filepath.write_text("We have 150 repositories in the system.\n")
    metrics = {
        "repositories": {
            "canonical": "103",
            "pattern": r"\b(1\d{2})\s*(?:repositories|repos)\b",
            "description": "Total repositories",
        }
    }
    results = check_file(filepath, metrics, verbose=False)
    stale = [r for r in results if r["status"] == "stale"]
    assert len(stale) == 1
    assert stale[0]["found"] == "150"
    assert stale[0]["canonical"] == "103"


def test_check_file_allow_higher_no_discrepancy(tmp_path, monkeypatch):
    """allow_higher=True, found value higher than canonical → no discrepancy."""
    import sync_metrics as sm
    monkeypatch.setattr(sm, "REPO_ROOT", tmp_path)
    filepath = tmp_path / "test.md"
    filepath.write_text("2,500 automated tests in the suite.\n")
    metrics = {
        "automated_tests": {
            "canonical": "2,349",
            "pattern": r"\b(2,\d{3})\+?\s*(?:automated\s+)?tests?\b",
            "description": "Automated tests",
            "allow_higher": True,
        }
    }
    results = check_file(filepath, metrics, verbose=False)
    stale = [r for r in results if r["status"] == "stale"]
    assert stale == []


def test_check_file_allow_higher_lower_value_is_discrepancy(tmp_path, monkeypatch):
    """allow_higher=True but found lower than canonical → discrepancy."""
    import sync_metrics as sm
    monkeypatch.setattr(sm, "REPO_ROOT", tmp_path)
    filepath = tmp_path / "test.md"
    filepath.write_text("2,100 automated tests in the suite.\n")
    metrics = {
        "automated_tests": {
            "canonical": "2,349",
            "pattern": r"\b(2,\d{3})\+?\s*(?:automated\s+)?tests?\b",
            "description": "Automated tests",
            "allow_higher": True,
        }
    }
    results = check_file(filepath, metrics, verbose=False)
    stale = [r for r in results if r["status"] == "stale"]
    assert len(stale) == 1


def test_check_file_no_pattern_match(tmp_path, monkeypatch):
    """No occurrences of pattern → empty list returned."""
    import sync_metrics as sm
    monkeypatch.setattr(sm, "REPO_ROOT", tmp_path)
    filepath = tmp_path / "test.md"
    filepath.write_text("No relevant numbers here.\n")
    metrics = {
        "repositories": {
            "canonical": "103",
            "pattern": r"\b(1\d{2})\s*(?:repositories|repos)\b",
            "description": "Total repositories",
        }
    }
    results = check_file(filepath, metrics, verbose=False)
    assert results == []


def test_check_file_multiple_matches(tmp_path, monkeypatch):
    """Multiple occurrences of stale numbers all reported."""
    import sync_metrics as sm
    monkeypatch.setattr(sm, "REPO_ROOT", tmp_path)
    filepath = tmp_path / "test.md"
    filepath.write_text(
        "We have 150 repositories total.\n"
        "With 120 repositories in production.\n"
    )
    metrics = {
        "repositories": {
            "canonical": "103",
            "pattern": r"\b(1\d{2})\s*(?:repositories|repos)\b",
            "description": "Total repositories",
        }
    }
    results = check_file(filepath, metrics, verbose=False)
    stale = [r for r in results if r["status"] == "stale"]
    assert len(stale) == 2


def test_check_file_verbose_includes_ok(tmp_path, monkeypatch):
    """verbose=True returns ok records for matching values."""
    import sync_metrics as sm
    monkeypatch.setattr(sm, "REPO_ROOT", tmp_path)
    filepath = tmp_path / "test.md"
    filepath.write_text("We have 103 repositories in the system.\n")
    metrics = {
        "repositories": {
            "canonical": "103",
            "pattern": r"\b(1\d{2})\s*(?:repositories|repos)\b",
            "description": "Total repositories",
        }
    }
    results = check_file(filepath, metrics, verbose=True)
    ok = [r for r in results if r["status"] == "ok"]
    assert len(ok) == 1


# --- TestParseCanonicalMetrics ---


def test_parse_canonical_metrics_missing_file():
    """Non-existent path returns empty dict."""
    result = parse_canonical_metrics(Path("/nonexistent/path/covenant-ark.md"))
    assert result == {}


def test_parse_canonical_metrics_extracts_table_rows(tmp_path):
    """Parses table rows after 'Ground Truth Metrics' heading."""
    ark = tmp_path / "covenant-ark.md"
    ark.write_text(
        "# Some heading\n\n"
        "## Ground Truth Metrics\n\n"
        "| Metric | Value |\n"
        "|--------|-------|\n"
        "| repositories | 103 |\n"
        "| automated_tests | 2,349 |\n"
        "\n"
        "## Next Section\n"
    )
    result = parse_canonical_metrics(ark)
    assert "repositories" in result
    assert result["repositories"] == "103"
    assert "automated_tests" in result


def test_parse_canonical_metrics_skips_header_row(tmp_path):
    """Header row 'Metric | Value' is not included in results."""
    ark = tmp_path / "covenant-ark.md"
    ark.write_text(
        "## Ground Truth Metrics\n\n"
        "| Metric | Value |\n"
        "|--------|-------|\n"
        "| repos | 103 |\n"
    )
    result = parse_canonical_metrics(ark)
    assert "Metric" not in result
    assert "metric" not in result


# --- TestCollectScanFiles ---


def test_collect_scan_files_returns_paths():
    """collect_scan_files returns a list of Path objects."""
    files = collect_scan_files()
    assert isinstance(files, list)
    # All items should be Path objects
    for f in files:
        assert isinstance(f, Path)


def test_canonical_metrics_has_required_keys():
    """CANONICAL_METRICS has the expected metric keys."""
    for key in ("repositories", "automated_tests", "ci_cd_workflows"):
        assert key in CANONICAL_METRICS


def test_canonical_metrics_have_required_fields():
    """Each metric entry has canonical, pattern, and description."""
    for key, config in CANONICAL_METRICS.items():
        assert "canonical" in config, f"{key} missing 'canonical'"
        assert "pattern" in config, f"{key} missing 'pattern'"
        assert "description" in config, f"{key} missing 'description'"
