"""Tests for scripts/validate_hypotheses.py."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import validate_hypotheses as vh_mod
from validate_hypotheses import accuracy_stats, build_outcome_map, validate


def test_build_outcome_map_supports_entry_id_and_id_fields():
    log = [
        {"entry_id": "entry-1", "outcome": "accepted"},
        {"id": "entry-2", "outcome": "rejected"},
    ]
    assert build_outcome_map(log) == {"entry-1": "accepted", "entry-2": "rejected"}


def test_validate_marks_correct_incorrect_and_unresolved():
    hypotheses = [
        {"hypothesis_id": "h1", "entry_id": "entry-1", "hypothesis": "good fit", "predicted_outcome": "accepted"},
        {"hypothesis_id": "h2", "entry_id": "entry-2", "hypothesis": "weak fit", "predicted_outcome": "accepted"},
        {"hypothesis_id": "h3", "entry_id": "entry-3", "hypothesis": "unknown", "predicted_outcome": "rejected"},
    ]
    outcomes = {"entry-1": "accepted", "entry-2": "rejected"}
    results = validate(hypotheses, outcomes)
    by_id = {row["hypothesis_id"]: row for row in results}
    assert by_id["h1"]["validated"] is True
    assert by_id["h2"]["validated"] is False
    assert by_id["h3"]["validated"] is None


def test_accuracy_stats_computes_percentage_from_resolved_items():
    results = [
        {"validated": True},
        {"validated": False},
        {"validated": None},
    ]
    stats = accuracy_stats(results)
    assert stats == {
        "total": 3,
        "resolved": 2,
        "correct": 1,
        "incorrect": 1,
        "accuracy": 50.0,
        "unresolved": 1,
    }


def test_load_hypotheses_supports_dict_shape(tmp_path, monkeypatch):
    signals = tmp_path / "signals"
    signals.mkdir()
    (signals / "hypotheses.yaml").write_text("hypotheses:\n  - hypothesis: test\n")
    monkeypatch.setattr(vh_mod, "SIGNALS_DIR", signals)
    data = vh_mod.load_hypotheses()
    assert isinstance(data, list)
    assert data[0]["hypothesis"] == "test"


def test_load_conversion_log_supports_dict_shape(tmp_path, monkeypatch):
    signals = tmp_path / "signals"
    signals.mkdir()
    (signals / "conversion-log.yaml").write_text("entries:\n  - id: e1\n    outcome: accepted\n")
    monkeypatch.setattr(vh_mod, "SIGNALS_DIR", signals)
    data = vh_mod.load_conversion_log()
    assert isinstance(data, list)
    assert data[0]["id"] == "e1"


# --- accuracy_by_category ---


def _make_result(hypothesis_id, entry_id, category, validated, predicted=None, actual=None):
    """Build a minimal validation result dict for testing."""
    return {
        "hypothesis_id": hypothesis_id,
        "entry_id": entry_id,
        "category": category,
        "hypothesis": f"hypothesis for {entry_id}",
        "predicted": predicted,
        "actual": actual,
        "validated": validated,
    }


def test_accuracy_by_category_validated_pattern():
    """Category with >50% accuracy is classified as validated_pattern."""
    results = [
        _make_result("h1", "e1", "timing", True, actual="rejected"),
        _make_result("h2", "e2", "timing", True, actual="expired"),
        _make_result("h3", "e3", "timing", False, actual="interview"),
    ]
    cat_stats = vh_mod.accuracy_by_category(results)
    assert "timing" in cat_stats
    timing = cat_stats["timing"]
    assert timing["total"] == 3
    assert timing["resolved"] == 3
    assert timing["correct"] == 2
    assert timing["incorrect"] == 1
    assert timing["accuracy"] == round(2 / 3 * 100, 1)
    assert timing["pattern"] == "validated_pattern"


def test_accuracy_by_category_invalid_assumption():
    """Category with <30% accuracy is classified as invalid_assumption."""
    results = [
        _make_result("h1", "e1", "resume_screen", False, actual="interview"),
        _make_result("h2", "e2", "resume_screen", False, actual="accepted"),
        _make_result("h3", "e3", "resume_screen", False, actual="interview"),
        _make_result("h4", "e4", "resume_screen", False, actual="accepted"),
    ]
    cat_stats = vh_mod.accuracy_by_category(results)
    assert cat_stats["resume_screen"]["accuracy"] == 0.0
    assert cat_stats["resume_screen"]["pattern"] == "invalid_assumption"


def test_accuracy_by_category_no_data():
    """Category with 0 resolved items is classified as no_data."""
    results = [
        _make_result("h1", "e1", "compensation", None),
        _make_result("h2", "e2", "compensation", None),
    ]
    cat_stats = vh_mod.accuracy_by_category(results)
    assert cat_stats["compensation"]["resolved"] == 0
    assert cat_stats["compensation"]["pattern"] == "no_data"


def test_accuracy_by_category_inconclusive():
    """Category with 30-50% accuracy is classified as inconclusive."""
    # 1 correct out of 3 resolved = 33.3%, which is between 30 and 50
    results = [
        _make_result("h1", "e1", "role_fit", True, actual="rejected"),
        _make_result("h2", "e2", "role_fit", False, actual="interview"),
        _make_result("h3", "e3", "role_fit", False, actual="accepted"),
    ]
    cat_stats = vh_mod.accuracy_by_category(results)
    assert cat_stats["role_fit"]["pattern"] == "inconclusive"
    assert cat_stats["role_fit"]["accuracy"] == round(1 / 3 * 100, 1)


def test_accuracy_by_category_multiple_categories():
    """Multiple categories are each computed independently."""
    results = [
        _make_result("h1", "e1", "timing", True, actual="rejected"),
        _make_result("h2", "e2", "timing", True, actual="expired"),
        _make_result("h3", "e3", "credential_gap", False, actual="interview"),
        _make_result("h4", "e4", "credential_gap", False, actual="accepted"),
        _make_result("h5", "e5", "other", None),
    ]
    cat_stats = vh_mod.accuracy_by_category(results)
    assert cat_stats["timing"]["pattern"] == "validated_pattern"
    assert cat_stats["credential_gap"]["pattern"] == "invalid_assumption"
    assert cat_stats["other"]["pattern"] == "no_data"


# --- classify_patterns ---


def test_classify_patterns_sorts_into_buckets():
    """Categories are sorted into validated, invalid, inconclusive, no_data."""
    category_stats = {
        "timing": {"pattern": "validated_pattern"},
        "resume_screen": {"pattern": "invalid_assumption"},
        "role_fit": {"pattern": "inconclusive"},
        "compensation": {"pattern": "no_data"},
    }
    classified = vh_mod.classify_patterns(category_stats)
    assert classified["validated"] == ["timing"]
    assert classified["invalid"] == ["resume_screen"]
    assert classified["inconclusive"] == ["role_fit"]
    assert classified["no_data"] == ["compensation"]


def test_classify_patterns_empty_input():
    """Empty category_stats yields empty lists."""
    classified = vh_mod.classify_patterns({})
    assert classified == {"validated": [], "invalid": [], "inconclusive": [], "no_data": []}


def test_classify_patterns_all_validated():
    """All categories as validated_pattern land in validated list."""
    category_stats = {
        "timing": {"pattern": "validated_pattern"},
        "resume_screen": {"pattern": "validated_pattern"},
    }
    classified = vh_mod.classify_patterns(category_stats)
    assert len(classified["validated"]) == 2
    assert classified["invalid"] == []
    assert classified["inconclusive"] == []
    assert classified["no_data"] == []


def test_classify_patterns_alphabetical_order():
    """Categories within each bucket are sorted alphabetically."""
    category_stats = {
        "z_cat": {"pattern": "validated_pattern"},
        "a_cat": {"pattern": "validated_pattern"},
        "m_cat": {"pattern": "validated_pattern"},
    }
    classified = vh_mod.classify_patterns(category_stats)
    assert classified["validated"] == ["a_cat", "m_cat", "z_cat"]


# --- generate_full_report ---


def test_generate_full_report_structure():
    """Report contains all expected top-level keys."""
    results = [
        _make_result("h1", "e1", "timing", True, actual="rejected"),
        _make_result("h2", "e2", "timing", False, actual="interview"),
        _make_result("h3", "e3", "compensation", None),
    ]
    report = vh_mod.generate_full_report(results)
    assert set(report.keys()) == {"summary", "category_accuracy", "patterns", "resolved", "unresolved"}


def test_generate_full_report_summary_matches_accuracy_stats():
    """Summary section matches accuracy_stats output."""
    results = [
        _make_result("h1", "e1", "timing", True, actual="rejected"),
        _make_result("h2", "e2", "timing", False, actual="interview"),
        _make_result("h3", "e3", "role_fit", None),
    ]
    report = vh_mod.generate_full_report(results)
    expected_stats = vh_mod.accuracy_stats(results)
    assert report["summary"] == expected_stats


def test_generate_full_report_resolved_and_unresolved_separation():
    """Resolved and unresolved entries are correctly separated."""
    results = [
        _make_result("h1", "e1", "timing", True, predicted="rejected", actual="rejected"),
        _make_result("h2", "e2", "timing", False, predicted="rejected", actual="interview"),
        _make_result("h3", "e3", "role_fit", None),
        _make_result("h4", "e4", "other", None, actual="acknowledged"),
    ]
    report = vh_mod.generate_full_report(results)
    assert len(report["resolved"]) == 2
    assert len(report["unresolved"]) == 2
    # Resolved items have "correct" field
    assert report["resolved"][0]["correct"] is True
    assert report["resolved"][1]["correct"] is False
    # Unresolved items have entry_id, category, hypothesis, actual
    unresolved_ids = {item["entry_id"] for item in report["unresolved"]}
    assert unresolved_ids == {"e3", "e4"}


def test_generate_full_report_patterns_match_classify():
    """Patterns section matches classify_patterns output."""
    results = [
        _make_result("h1", "e1", "timing", True, actual="rejected"),
        _make_result("h2", "e2", "timing", True, actual="expired"),
        _make_result("h3", "e3", "credential_gap", False, actual="accepted"),
    ]
    report = vh_mod.generate_full_report(results)
    expected_cat_stats = vh_mod.accuracy_by_category(results)
    expected_patterns = vh_mod.classify_patterns(expected_cat_stats)
    assert report["patterns"] == expected_patterns
    assert report["category_accuracy"] == expected_cat_stats


def test_generate_full_report_empty_results():
    """Empty results produce valid structure with zeroed stats."""
    report = vh_mod.generate_full_report([])
    assert report["summary"]["total"] == 0
    assert report["summary"]["resolved"] == 0
    assert report["resolved"] == []
    assert report["unresolved"] == []
    assert report["category_accuracy"] == {}
    assert report["patterns"] == {"validated": [], "invalid": [], "inconclusive": [], "no_data": []}


# --- print_report ---


def test_print_report_shows_header_and_summary(capsys):
    """print_report outputs the main header and summary statistics."""
    results = [
        _make_result("h1", "e1", "timing", True, actual="rejected"),
        _make_result("h2", "e2", "timing", False, actual="interview"),
        _make_result("h3", "e3", "role_fit", None),
    ]
    vh_mod.print_report(results)
    captured = capsys.readouterr().out
    assert "Hypothesis Validation Report" in captured
    assert "Total hypotheses: 3" in captured
    assert "Resolved: 2" in captured
    assert "Unresolved: 1" in captured
    assert "Accuracy:" in captured


def test_print_report_shows_category_accuracy(capsys):
    """print_report includes the Accuracy by Category section."""
    results = [
        _make_result("h1", "e1", "timing", True, actual="rejected"),
        _make_result("h2", "e2", "credential_gap", False, actual="accepted"),
    ]
    vh_mod.print_report(results)
    captured = capsys.readouterr().out
    assert "Accuracy by Category:" in captured
    assert "timing" in captured
    assert "credential_gap" in captured


def test_print_report_shows_validated_patterns(capsys):
    """print_report displays validated pattern section when present."""
    results = [
        _make_result("h1", "e1", "timing", True, actual="rejected"),
        _make_result("h2", "e2", "timing", True, actual="expired"),
    ]
    vh_mod.print_report(results)
    captured = capsys.readouterr().out
    assert "Validated Patterns" in captured
    assert "timing" in captured


def test_print_report_shows_invalid_assumptions(capsys):
    """print_report displays invalid assumption section when present."""
    results = [
        _make_result("h1", "e1", "resume_screen", False, actual="interview"),
        _make_result("h2", "e2", "resume_screen", False, actual="accepted"),
    ]
    vh_mod.print_report(results)
    captured = capsys.readouterr().out
    assert "Invalid Assumptions" in captured
    assert "resume_screen" in captured


def test_print_report_shows_resolved_hypotheses(capsys):
    """print_report lists resolved hypotheses with CORRECT/WRONG markers."""
    results = [
        _make_result("h1", "e1", "timing", True, actual="rejected"),
        _make_result("h2", "e2", "role_fit", False, actual="interview"),
    ]
    vh_mod.print_report(results)
    captured = capsys.readouterr().out
    assert "Resolved Hypotheses:" in captured
    assert "[CORRECT]" in captured
    assert "[WRONG]" in captured


def test_print_report_unresolved_only(capsys):
    """print_report with unresolved_only=True skips the full report header."""
    results = [
        _make_result("h1", "e1", "timing", True, actual="rejected"),
        _make_result("h2", "e2", "role_fit", None),
    ]
    vh_mod.print_report(results, unresolved_only=True)
    captured = capsys.readouterr().out
    # Should NOT contain the main header
    assert "Hypothesis Validation Report" not in captured
    # Should contain unresolved section
    assert "Unresolved Hypotheses (1):" in captured
    assert "e2" in captured


def test_print_report_no_unresolved_skips_section(capsys):
    """When all hypotheses are resolved, the unresolved section is absent."""
    results = [
        _make_result("h1", "e1", "timing", True, actual="rejected"),
        _make_result("h2", "e2", "timing", False, actual="interview"),
    ]
    vh_mod.print_report(results)
    captured = capsys.readouterr().out
    assert "Unresolved Hypotheses" not in captured
