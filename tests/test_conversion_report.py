"""Tests for scripts/conversion_report.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from conversion_report import analyze_by_dimension, print_report, response_time_analysis


def _make_entry(
    entry_id="test-entry",
    track="job",
    status="research",
    outcome=None,
    score=5.0,
    identity_position="independent-engineer",
):
    """Build a minimal pipeline entry for conversion report tests."""
    entry = {
        "id": entry_id,
        "track": track,
        "status": status,
        "fit": {"score": score, "identity_position": identity_position},
        "conversion": {},
    }
    if outcome:
        entry["outcome"] = outcome
    return entry


# --- analyze_by_dimension ---


def test_analyze_by_dimension_grouping():
    """Groups entries by extract_fn correctly."""
    entries = [
        _make_entry(entry_id="e1", track="job"),
        _make_entry(entry_id="e2", track="grant"),
        _make_entry(entry_id="e3", track="job"),
    ]
    groups = analyze_by_dimension(entries, "track", lambda e: e.get("track"))
    assert "job" in groups
    assert "grant" in groups
    assert groups["job"]["total"] == 2
    assert groups["grant"]["total"] == 1


def test_analyze_by_dimension_counts():
    """Counts submitted/accepted/rejected correctly."""
    entries = [
        _make_entry(entry_id="e1", status="submitted"),
        _make_entry(entry_id="e2", status="outcome", outcome="accepted"),
        _make_entry(entry_id="e3", status="outcome", outcome="rejected"),
        _make_entry(entry_id="e4", status="research"),
    ]
    groups = analyze_by_dimension(entries, "track", lambda e: e.get("track"))
    job = groups["job"]
    assert job["total"] == 4
    assert job["submitted"] == 3  # submitted + 2 outcome
    assert job["accepted"] == 1
    assert job["rejected"] == 1


def test_analyze_by_dimension_none_key():
    """Entries where extract_fn returns None are skipped."""
    entries = [
        _make_entry(entry_id="e1", identity_position="educator"),
        _make_entry(entry_id="e2"),
    ]
    groups = analyze_by_dimension(
        entries, "position",
        lambda e: e.get("fit", {}).get("missing_field"),
    )
    assert groups == {}


def test_analyze_by_dimension_pending():
    """Submitted entries without outcome counted as pending."""
    entries = [
        _make_entry(entry_id="e1", status="submitted"),
        _make_entry(entry_id="e2", status="acknowledged"),
    ]
    groups = analyze_by_dimension(entries, "track", lambda e: e.get("track"))
    assert groups["job"]["pending"] == 2


def test_analyze_by_dimension_empty_entries():
    """Empty entries list returns empty dict."""
    groups = analyze_by_dimension([], "track", lambda e: e.get("track"))
    assert groups == {}


def test_analyze_by_dimension_interview_counted_as_submitted():
    """Interview status entries count toward submitted."""
    entries = [_make_entry(entry_id="e1", status="interview")]
    groups = analyze_by_dimension(entries, "track", lambda e: e.get("track"))
    assert groups["job"]["submitted"] == 1
    assert groups["job"]["pending"] == 1


def test_analyze_by_dimension_withdrawn_not_counted():
    """Withdrawn outcome is not accepted or rejected."""
    entries = [_make_entry(entry_id="e1", status="outcome", outcome="withdrawn")]
    groups = analyze_by_dimension(entries, "track", lambda e: e.get("track"))
    assert groups["job"]["accepted"] == 0
    assert groups["job"]["rejected"] == 0
    assert groups["job"]["outcomes"] == 1


def test_analyze_by_dimension_multiple_groups():
    """Multiple groups track independently."""
    entries = [
        _make_entry(entry_id="e1", track="job", status="submitted"),
        _make_entry(entry_id="e2", track="grant", status="submitted"),
        _make_entry(entry_id="e3", track="job", status="outcome", outcome="accepted"),
        _make_entry(entry_id="e4", track="grant", status="outcome", outcome="rejected"),
    ]
    groups = analyze_by_dimension(entries, "track", lambda e: e.get("track"))
    assert groups["job"]["accepted"] == 1
    assert groups["grant"]["rejected"] == 1


# --- score_bracket (tested as lambda in main) ---


def test_score_bracket_mapping():
    """Score bracket function maps scores to correct categories."""
    def score_bracket(entry):
        fit = entry.get("fit", {})
        if not isinstance(fit, dict):
            return None
        score = fit.get("score")
        if score is None:
            return None
        if score >= 9:
            return "9-10 (excellent)"
        if score >= 7:
            return "7-8 (good)"
        if score >= 5:
            return "5-6 (moderate)"
        return "1-4 (low)"

    assert score_bracket(_make_entry(score=9.5)) == "9-10 (excellent)"
    assert score_bracket(_make_entry(score=7.0)) == "7-8 (good)"
    assert score_bracket(_make_entry(score=5.5)) == "5-6 (moderate)"
    assert score_bracket(_make_entry(score=3.0)) == "1-4 (low)"
    assert score_bracket({"fit": None}) is None


# --- print_report ---


def test_print_report_empty_groups(capsys):
    """Empty groups prints 'No data available.'"""
    print_report("TEST REPORT", {})
    out = capsys.readouterr().out
    assert "No data available." in out


def test_print_report_shows_title(capsys):
    """Report shows the title."""
    groups = {"job": {"total": 1, "submitted": 0, "accepted": 0, "outcomes": 0}}
    print_report("MY TITLE", groups)
    out = capsys.readouterr().out
    assert "MY TITLE" in out


def test_print_report_shows_conversion_rate(capsys):
    """Report shows conversion rate when outcomes exist."""
    groups = {"job": {"total": 10, "submitted": 5, "accepted": 2, "outcomes": 4, "rejected": 2, "pending": 1}}
    print_report("RATES", groups)
    out = capsys.readouterr().out
    assert "50%" in out  # 2/4


# --- response_time_analysis ---


def test_response_time_analysis_no_data(capsys):
    """No response time data prints appropriate message."""
    entries = [_make_entry(status="research")]
    response_time_analysis(entries)
    out = capsys.readouterr().out
    assert "No response time data" in out


def test_response_time_analysis_with_data(capsys):
    """With response times, prints mean/median/min/max."""
    entries = [
        {**_make_entry(status="outcome"), "conversion": {"time_to_response_days": 10}},
        {**_make_entry(status="outcome"), "conversion": {"time_to_response_days": 20}},
    ]
    response_time_analysis(entries)
    out = capsys.readouterr().out
    assert "Mean:" in out
    assert "15.0" in out  # (10+20)/2
