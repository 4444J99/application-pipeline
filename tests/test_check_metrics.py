"""Tests for scripts/check_metrics.py"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from check_metrics import (
    _FALLBACK_METRICS,
    METRIC_PATTERNS,
    ORGAN_PATTERNS,
    SOURCE_METRICS,
    apply_fix,
    check_file,
    check_profile_json,
    load_source_metrics,
)

# --- _FALLBACK_METRICS ---


def test_fallback_metrics_keys():
    """_FALLBACK_METRICS has all required keys."""
    required = {
        "total_repos", "active_repos", "archived_repos",
        "github_orgs", "published_essays", "total_words_k",
        "named_sprints", "automated_tests", "organ_repo_counts",
    }
    assert required.issubset(set(_FALLBACK_METRICS.keys()))


def test_fallback_metrics_repo_count():
    """total_repos matches sum of organ counts."""
    organ_sum = sum(_FALLBACK_METRICS["organ_repo_counts"].values())
    assert _FALLBACK_METRICS["total_repos"] == organ_sum


# --- ORGAN_PATTERNS ---


def test_organ_patterns_all_organs():
    """ORGAN_PATTERNS covers organs I-VII."""
    organ_values = set(ORGAN_PATTERNS.values())
    for organ in ("I", "II", "III", "IV", "V", "VI", "VII"):
        assert organ in organ_values, f"Organ {organ} missing from ORGAN_PATTERNS"


# --- METRIC_PATTERNS ---


def test_metric_patterns_structure():
    """Each METRIC_PATTERNS entry has name, patterns, metric_key, transform."""
    for mp in METRIC_PATTERNS:
        assert "name" in mp
        assert "patterns" in mp
        assert "metric_key" in mp
        assert "transform" in mp
        assert isinstance(mp["patterns"], list)
        assert len(mp["patterns"]) > 0


# --- check_file ---


def test_check_file_clean():
    """check_file on a file with correct metrics returns []."""
    total = SOURCE_METRICS["total_repos"]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(f"This system has {total} repositories across 8 orgs.\n")
        f.flush()
        errors = check_file(Path(f.name), source_root=Path(f.name).parent)
    assert errors == []


def test_check_file_stale_repo_count():
    """check_file detects wrong 'N repositories'."""
    wrong = SOURCE_METRICS["total_repos"] + 10
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(f"This system has {wrong} repositories spanning everything.\n")
        f.flush()
        errors = check_file(Path(f.name), source_root=Path(f.name).parent)
    assert len(errors) > 0
    assert errors[0]["metric"] == "total_repos"
    assert errors[0]["found"] == wrong


def test_check_file_stale_word_count():
    """check_file detects wrong 'NK words of'."""
    wrong_k = SOURCE_METRICS["total_words_k"] + 50
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(f"Over ~{wrong_k}K words of documentation and essays.\n")
        f.flush()
        errors = check_file(Path(f.name), source_root=Path(f.name).parent)
    word_errors = [e for e in errors if e["metric"] == "word_count_k"]
    assert len(word_errors) > 0
    assert word_errors[0]["found"] == wrong_k


def test_check_file_skips_organ_lines():
    """Organ-specific lines not flagged as total_repos mismatch."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("ORGAN-III has 27 repos for commercial products.\n")
        f.flush()
        errors = check_file(Path(f.name), source_root=Path(f.name).parent)
    repo_errors = [e for e in errors if e["metric"] == "total_repos"]
    assert len(repo_errors) == 0


# --- check_profile_json ---


def test_check_profile_json_valid():
    """Valid profile with correct metrics returns no errors."""
    import json
    total = SOURCE_METRICS["total_repos"]
    profile = {
        "name": "Test",
        "artist_statement": {
            "short": f"A system of {total} repositories.",
        },
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(profile, f)
        f.flush()
        errors = check_profile_json(Path(f.name))
    assert errors == []


# --- apply_fix ---


def test_apply_fix_replaces_number():
    """apply_fix correctly substitutes a number in a line."""
    wrong = SOURCE_METRICS["total_repos"] + 5
    expected = SOURCE_METRICS["total_repos"]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(f"System has {wrong} repositories total.\n")
        f.flush()
        filepath = Path(f.name)
    error = {"file": filepath.name, "line": 1, "metric": "total_repos",
             "found": wrong, "expected": expected, "line_text": ""}
    result = apply_fix(filepath, error)
    assert result is True
    assert str(expected) in filepath.read_text()


def test_apply_fix_comma_formatted():
    """apply_fix handles '2,349' style numbers."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("We have 2,000 automated tests across the system.\n")
        f.flush()
        filepath = Path(f.name)
    expected = SOURCE_METRICS["automated_tests"]
    error = {"file": filepath.name, "line": 1, "metric": "test_count",
             "found": 2000, "expected": expected, "line_text": ""}
    result = apply_fix(filepath, error)
    assert result is True
    content = filepath.read_text()
    assert f"{expected:,}" in content or str(expected) in content


# --- load_source_metrics ---


def test_source_metrics_fallback():
    """load_source_metrics with nonexistent path returns _FALLBACK_METRICS."""
    result = load_source_metrics(Path("/nonexistent/path/metrics.json"))
    assert result == _FALLBACK_METRICS
