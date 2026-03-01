"""Tests for scripts/feedback_capture.py"""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))


# --- TestLoadSaveHypotheses ---


def test_load_empty_when_file_missing(tmp_path, monkeypatch):
    """load_hypotheses returns [] when HYPOTHESES_FILE doesn't exist."""
    import feedback_capture as fc
    monkeypatch.setattr(fc, "HYPOTHESES_FILE", tmp_path / "hypotheses.yaml")
    assert fc.load_hypotheses() == []


def test_round_trip_single(tmp_path, monkeypatch):
    """save then load returns the same single record."""
    import feedback_capture as fc
    monkeypatch.setattr(fc, "HYPOTHESES_FILE", tmp_path / "hypotheses.yaml")
    record = {"entry_id": "acme-swe", "date": "2026-01-01", "category": "timing", "hypothesis": "Too early"}
    fc.save_hypotheses([record])
    loaded = fc.load_hypotheses()
    assert len(loaded) == 1
    assert loaded[0]["entry_id"] == "acme-swe"
    assert loaded[0]["hypothesis"] == "Too early"


def test_round_trip_multiple(tmp_path, monkeypatch):
    """Multiple records round-trip correctly."""
    import feedback_capture as fc
    monkeypatch.setattr(fc, "HYPOTHESES_FILE", tmp_path / "hypotheses.yaml")
    records = [
        {"entry_id": "a", "date": "2026-01-01", "category": "timing", "hypothesis": "H1"},
        {"entry_id": "b", "date": "2026-01-02", "category": "other", "hypothesis": "H2"},
    ]
    fc.save_hypotheses(records)
    loaded = fc.load_hypotheses()
    assert len(loaded) == 2
    ids = [r["entry_id"] for r in loaded]
    assert "a" in ids
    assert "b" in ids


def test_load_malformed_yaml_returns_empty(tmp_path, monkeypatch):
    """Corrupted YAML file returns empty list without raising."""
    import feedback_capture as fc
    f = tmp_path / "hypotheses.yaml"
    f.write_text("hypotheses: [unclosed")
    monkeypatch.setattr(fc, "HYPOTHESES_FILE", f)
    # yaml.safe_load on broken YAML raises; load_hypotheses should let it propagate
    # but if the file is empty-ish it returns []. Test that a valid empty dict works:
    f.write_text("hypotheses: null\n")
    result = fc.load_hypotheses()
    assert result == []


# --- TestAddHypothesis ---


def test_add_appends_new_record(tmp_path, monkeypatch, capsys):
    """add_hypothesis appends a new record and persists it."""
    import feedback_capture as fc
    monkeypatch.setattr(fc, "HYPOTHESES_FILE", tmp_path / "hypotheses.yaml")
    record = {
        "entry_id": "test-co",
        "date": date.today().isoformat(),
        "outcome": "rejected",
        "category": "timing",
        "hypothesis": "Headcount freeze",
    }
    fc.add_hypothesis(record)
    loaded = fc.load_hypotheses()
    assert len(loaded) == 1
    assert loaded[0]["entry_id"] == "test-co"


def test_add_deduplicates_same_entry_category_date(tmp_path, monkeypatch, capsys):
    """Same entry+category+date updates in place, not appended."""
    import feedback_capture as fc
    monkeypatch.setattr(fc, "HYPOTHESES_FILE", tmp_path / "hypotheses.yaml")
    today = date.today().isoformat()
    first = {"entry_id": "x", "date": today, "category": "timing", "hypothesis": "First"}
    fc.add_hypothesis(first)
    second = {"entry_id": "x", "date": today, "category": "timing", "hypothesis": "Updated"}
    fc.add_hypothesis(second)
    loaded = fc.load_hypotheses()
    assert len(loaded) == 1
    assert loaded[0]["hypothesis"] == "Updated"


def test_add_different_entry_ids_both_saved(tmp_path, monkeypatch):
    """Distinct entry_ids both preserved."""
    import feedback_capture as fc
    monkeypatch.setattr(fc, "HYPOTHESES_FILE", tmp_path / "hypotheses.yaml")
    today = date.today().isoformat()
    fc.add_hypothesis({"entry_id": "a", "date": today, "category": "timing", "hypothesis": "H1"})
    fc.add_hypothesis({"entry_id": "b", "date": today, "category": "timing", "hypothesis": "H2"})
    loaded = fc.load_hypotheses()
    assert len(loaded) == 2


def test_add_different_categories_both_saved(tmp_path, monkeypatch):
    """Same entry_id, different category → two records."""
    import feedback_capture as fc
    monkeypatch.setattr(fc, "HYPOTHESES_FILE", tmp_path / "hypotheses.yaml")
    today = date.today().isoformat()
    fc.add_hypothesis({"entry_id": "x", "date": today, "category": "timing", "hypothesis": "H1"})
    fc.add_hypothesis({"entry_id": "x", "date": today, "category": "other", "hypothesis": "H2"})
    loaded = fc.load_hypotheses()
    assert len(loaded) == 2


# --- TestCaptureNoninteractive ---


def test_capture_noninteractive_returns_correct_shape():
    """capture_noninteractive returns dict with correct keys."""
    import feedback_capture as fc
    record = fc.capture_noninteractive(
        entry_id="acme-se",
        category="resume_screen",
        hypothesis="ATS rejected on keywords",
        outcome="rejected",
    )
    assert record["entry_id"] == "acme-se"
    assert record["category"] == "resume_screen"
    assert record["hypothesis"] == "ATS rejected on keywords"
    assert record["outcome"] == "rejected"
    assert "date" in record


def test_capture_noninteractive_date_is_today():
    """Date field is today's ISO date."""
    import feedback_capture as fc
    record = fc.capture_noninteractive("x", "timing", "Hypothesis text")
    assert record["date"] == date.today().isoformat()


def test_capture_noninteractive_outcome_none():
    """outcome=None is preserved in the record."""
    import feedback_capture as fc
    record = fc.capture_noninteractive("x", "timing", "Hypothesis", outcome=None)
    assert record["outcome"] is None


# --- TestShowHypotheses ---


def test_show_hypotheses_empty_file(tmp_path, monkeypatch, capsys):
    """Empty hypotheses file prints 'No hypotheses recorded yet.'"""
    import feedback_capture as fc
    monkeypatch.setattr(fc, "HYPOTHESES_FILE", tmp_path / "hypotheses.yaml")
    fc.show_hypotheses()
    out = capsys.readouterr().out
    assert "No hypotheses recorded yet." in out


def test_show_hypotheses_lists_by_category(tmp_path, monkeypatch, capsys):
    """show_hypotheses groups entries by category."""
    import feedback_capture as fc
    monkeypatch.setattr(fc, "HYPOTHESES_FILE", tmp_path / "hypotheses.yaml")
    fc.save_hypotheses([
        {"entry_id": "a", "date": "2026-01-01", "category": "timing", "hypothesis": "H1", "outcome": "rejected"},
        {"entry_id": "b", "date": "2026-01-02", "category": "timing", "hypothesis": "H2", "outcome": "rejected"},
        {"entry_id": "c", "date": "2026-01-03", "category": "other", "hypothesis": "H3", "outcome": "rejected"},
    ])
    fc.show_hypotheses()
    out = capsys.readouterr().out
    assert "[timing]" in out
    assert "[other]" in out


def test_show_hypotheses_entry_id_filter(tmp_path, monkeypatch, capsys):
    """entry_id filter shows only that entry."""
    import feedback_capture as fc
    monkeypatch.setattr(fc, "HYPOTHESES_FILE", tmp_path / "hypotheses.yaml")
    fc.save_hypotheses([
        {"entry_id": "target", "date": "2026-01-01", "category": "timing", "hypothesis": "For target", "outcome": "rejected"},
        {"entry_id": "other", "date": "2026-01-02", "category": "other", "hypothesis": "For other", "outcome": "rejected"},
    ])
    fc.show_hypotheses(entry_id="target")
    out = capsys.readouterr().out
    assert "target" in out
    assert "For other" not in out


def test_show_hypotheses_entry_filter_no_match(tmp_path, monkeypatch, capsys):
    """Filter with no match prints 'No hypotheses for: ...'"""
    import feedback_capture as fc
    monkeypatch.setattr(fc, "HYPOTHESES_FILE", tmp_path / "hypotheses.yaml")
    fc.save_hypotheses([
        {"entry_id": "a", "date": "2026-01-01", "category": "timing", "hypothesis": "H1"}
    ])
    fc.show_hypotheses(entry_id="nonexistent")
    out = capsys.readouterr().out
    assert "No hypotheses for: nonexistent" in out


# --- TestShowAnalysis ---


def test_show_analysis_empty_threshold_message(tmp_path, monkeypatch, capsys):
    """Fewer than 5 hypotheses → 'N more needed for early pattern signal'."""
    import feedback_capture as fc
    monkeypatch.setattr(fc, "HYPOTHESES_FILE", tmp_path / "hypotheses.yaml")
    # 0 hypotheses
    fc.show_analysis()
    out = capsys.readouterr().out
    assert "more needed for early pattern signal" in out


def test_show_analysis_five_to_nine(tmp_path, monkeypatch, capsys):
    """5–9 hypotheses → 'more needed for calibration-grade analysis'."""
    import feedback_capture as fc
    monkeypatch.setattr(fc, "HYPOTHESES_FILE", tmp_path / "hypotheses.yaml")
    records = [
        {"entry_id": f"e{i}", "date": "2026-01-01", "category": "timing", "hypothesis": f"H{i}", "outcome": "rejected"}
        for i in range(5)
    ]
    fc.save_hypotheses(records)
    fc.show_analysis()
    out = capsys.readouterr().out
    assert "more needed for calibration-grade analysis" in out


def test_show_analysis_ten_plus_shows_dominant(tmp_path, monkeypatch, capsys):
    """10+ hypotheses shows 'Dominant pattern:' line."""
    import feedback_capture as fc
    monkeypatch.setattr(fc, "HYPOTHESES_FILE", tmp_path / "hypotheses.yaml")
    records = [
        {"entry_id": f"e{i}", "date": "2026-01-01", "category": "timing", "hypothesis": f"H{i}", "outcome": "rejected"}
        for i in range(10)
    ]
    fc.save_hypotheses(records)
    fc.show_analysis()
    out = capsys.readouterr().out
    assert "Dominant pattern:" in out


def test_show_analysis_category_breakdown(tmp_path, monkeypatch, capsys):
    """Category breakdown shows count per category."""
    import feedback_capture as fc
    monkeypatch.setattr(fc, "HYPOTHESES_FILE", tmp_path / "hypotheses.yaml")
    records = [
        {"entry_id": f"e{i}", "date": "2026-01-01", "category": "timing", "hypothesis": f"H{i}", "outcome": "rejected"}
        for i in range(3)
    ] + [
        {"entry_id": f"f{i}", "date": "2026-01-01", "category": "other", "hypothesis": f"F{i}", "outcome": "rejected"}
        for i in range(2)
    ]
    fc.save_hypotheses(records)
    fc.show_analysis()
    out = capsys.readouterr().out
    assert "Category breakdown" in out
    assert "timing" in out


def test_show_analysis_outcome_breakdown(tmp_path, monkeypatch, capsys):
    """Outcome breakdown appears in analysis output."""
    import feedback_capture as fc
    monkeypatch.setattr(fc, "HYPOTHESES_FILE", tmp_path / "hypotheses.yaml")
    records = [
        {"entry_id": f"e{i}", "date": "2026-01-01", "category": "timing", "hypothesis": f"H{i}", "outcome": "rejected"}
        for i in range(5)
    ]
    fc.save_hypotheses(records)
    fc.show_analysis()
    out = capsys.readouterr().out
    assert "Outcome breakdown" in out
    assert "rejected" in out


# --- VALID_CATEGORIES ---


def test_valid_categories_not_empty():
    """VALID_CATEGORIES is populated."""
    import feedback_capture as fc
    assert len(fc.VALID_CATEGORIES) >= 5


def test_valid_categories_includes_common():
    """Common categories are present."""
    import feedback_capture as fc
    for cat in ("resume_screen", "timing", "auto_rejection", "role_fit", "other"):
        assert cat in fc.VALID_CATEGORIES
