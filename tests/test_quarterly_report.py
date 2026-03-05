"""Tests for scripts/quarterly_report.py."""

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from quarterly_report import (
    NEGATIVE_OUTCOMES,
    SUBMITTED_STATUSES,
    _quarter_label,
    _quarter_start,
    block_roi,
    conversion_by_channel,
    conversion_by_position,
    executive_summary,
    filter_by_period,
    format_markdown_report,
    generate_recommendations,
    network_proximity_correlation,
    pipeline_velocity,
    scoring_dimension_accuracy,
    seasonal_patterns,
)

# --- Helpers ---


def _make_entry(
    entry_id="test-entry",
    status="submitted",
    track="job",
    portal="greenhouse",
    position="independent-engineer",
    score=8.0,
    outcome=None,
    submitted_date=None,
    blocks_used=None,
    dimensions=None,
    network_proximity=None,
    time_to_response_days=None,
):
    """Build a test pipeline entry."""
    if submitted_date is None:
        submitted_date = date.today().isoformat()

    entry = {
        "id": entry_id,
        "status": status,
        "track": track,
        "outcome": outcome,
        "target": {"portal": portal, "organization": "TestOrg"},
        "fit": {
            "score": score,
            "identity_position": position,
            "dimensions": dimensions or {},
        },
        "submission": {
            "blocks_used": blocks_used or {},
            "variant_ids": {},
        },
        "timeline": {
            "researched": submitted_date,
            "date_added": submitted_date,
            "submitted": submitted_date,
        },
        "conversion": {},
        "tags": [],
        "_dir": "submitted",
        "_file": f"{entry_id}.yaml",
    }

    if network_proximity is not None:
        entry["fit"]["dimensions"]["network_proximity"] = network_proximity

    if time_to_response_days is not None:
        entry["conversion"]["time_to_response_days"] = time_to_response_days

    return entry


# --- Quarter helpers ---


def test_quarter_label_q1():
    """January should be Q1."""
    assert _quarter_label(date(2026, 1, 15)) == "2026-Q1"


def test_quarter_label_q2():
    """April should be Q2."""
    assert _quarter_label(date(2026, 4, 1)) == "2026-Q2"


def test_quarter_label_q3():
    """July should be Q3."""
    assert _quarter_label(date(2026, 7, 31)) == "2026-Q3"


def test_quarter_label_q4():
    """December should be Q4."""
    assert _quarter_label(date(2026, 12, 25)) == "2026-Q4"


def test_quarter_start():
    """Quarter start should be first day of the quarter."""
    assert _quarter_start(date(2026, 2, 15)) == date(2026, 1, 1)
    assert _quarter_start(date(2026, 5, 10)) == date(2026, 4, 1)
    assert _quarter_start(date(2026, 9, 30)) == date(2026, 7, 1)
    assert _quarter_start(date(2026, 12, 1)) == date(2026, 10, 1)


# --- Constants ---


def test_submitted_statuses_contains_expected():
    """Submitted statuses should include the expected values."""
    assert "submitted" in SUBMITTED_STATUSES
    assert "acknowledged" in SUBMITTED_STATUSES
    assert "interview" in SUBMITTED_STATUSES
    assert "outcome" in SUBMITTED_STATUSES


def test_negative_outcomes():
    """Negative outcomes should include rejected, expired, withdrawn."""
    assert "rejected" in NEGATIVE_OUTCOMES
    assert "expired" in NEGATIVE_OUTCOMES
    assert "withdrawn" in NEGATIVE_OUTCOMES


# --- filter_by_period ---


def test_filter_by_period_includes_recent():
    """Entries submitted within the period should be included."""
    today = date.today()
    entries = [
        _make_entry(entry_id="recent", submitted_date=today.isoformat()),
        _make_entry(entry_id="old", submitted_date=(today - timedelta(days=120)).isoformat()),
    ]
    result = filter_by_period(entries, 90)
    ids = [e["id"] for e in result]
    assert "recent" in ids
    assert "old" not in ids


def test_filter_by_period_includes_non_submitted():
    """Non-submitted entries within date_added window should be included."""
    today = date.today()
    entry = _make_entry(entry_id="research-entry", status="research",
                        submitted_date=today.isoformat())
    entry["timeline"]["submitted"] = None
    result = filter_by_period([entry], 90)
    assert len(result) == 1


# --- executive_summary ---


def test_executive_summary_counts():
    """Executive summary should count entries correctly."""
    entries = [
        _make_entry(entry_id="e1", status="submitted"),
        _make_entry(entry_id="e2", status="submitted", outcome="rejected"),
        _make_entry(entry_id="e3", status="submitted", outcome="accepted"),
        _make_entry(entry_id="e4", status="research"),
    ]
    result = executive_summary(entries, 90)
    assert result["total_entries"] == 4
    assert result["submitted"] == 3
    assert result["accepted"] == 1
    assert result["rejected"] == 1
    assert result["pending"] == 1


def test_executive_summary_conversion_rate():
    """Conversion rate should be accepted / submitted * 100."""
    entries = [
        _make_entry(entry_id="e1", status="submitted", outcome="accepted"),
        _make_entry(entry_id="e2", status="submitted", outcome="rejected"),
        _make_entry(entry_id="e3", status="submitted", outcome="rejected"),
        _make_entry(entry_id="e4", status="submitted", outcome="accepted"),
    ]
    result = executive_summary(entries, 90)
    assert result["conversion_rate"] == 50.0


def test_executive_summary_empty():
    """Empty entries should not raise errors."""
    result = executive_summary([], 90)
    assert result["total_entries"] == 0
    assert result["conversion_rate"] == 0.0


# --- conversion_by_position ---


def test_conversion_by_position_groups_correctly():
    """Entries should be grouped by identity position."""
    entries = [
        _make_entry(entry_id="e1", position="educator", outcome="accepted"),
        _make_entry(entry_id="e2", position="educator", outcome="rejected"),
        _make_entry(entry_id="e3", position="systems-artist"),
    ]
    result = conversion_by_position(entries)
    positions = {r["position"] for r in result}
    assert "educator" in positions
    assert "systems-artist" in positions

    educator = next(r for r in result if r["position"] == "educator")
    assert educator["submitted"] == 2
    assert educator["accepted"] == 1


# --- conversion_by_channel ---


def test_conversion_by_channel_groups_correctly():
    """Entries should be grouped by portal."""
    entries = [
        _make_entry(entry_id="e1", portal="greenhouse"),
        _make_entry(entry_id="e2", portal="ashby"),
        _make_entry(entry_id="e3", portal="greenhouse", outcome="accepted"),
    ]
    result = conversion_by_channel(entries)
    portals = {r["portal"] for r in result}
    assert "greenhouse" in portals
    assert "ashby" in portals


# --- block_roi ---


def test_block_roi_counts_blocks():
    """Block ROI should count blocks across submitted entries."""
    entries = [
        _make_entry(entry_id="e1", outcome="accepted",
                     blocks_used={"framing": "framings/independent-engineer"}),
        _make_entry(entry_id="e2", outcome="rejected",
                     blocks_used={"framing": "framings/independent-engineer",
                                  "evidence": "evidence/differentiators"}),
    ]
    result = block_roi(entries)
    ie_block = next(r for r in result if r["block"] == "framings/independent-engineer")
    assert ie_block["total"] == 2
    assert ie_block["accepted"] == 1
    assert ie_block["rejected"] == 1
    assert ie_block["acceptance_rate"] == 50.0


def test_block_roi_empty():
    """No submitted entries should return empty list."""
    entries = [_make_entry(entry_id="e1", status="research")]
    result = block_roi(entries)
    assert result == []


# --- network_proximity_correlation ---


def test_network_proximity_groups_outcomes():
    """Network proximity should group by outcome."""
    entries = [
        _make_entry(entry_id="e1", outcome="accepted", network_proximity=7),
        _make_entry(entry_id="e2", outcome="rejected", network_proximity=2),
        _make_entry(entry_id="e3", network_proximity=5),
    ]
    result = network_proximity_correlation(entries)
    assert result["accepted"]["average"] == 7.0
    assert result["rejected"]["average"] == 2.0
    assert result["pending"]["average"] == 5.0


def test_network_proximity_empty():
    """No network proximity data should return empty dict."""
    entries = [_make_entry(entry_id="e1")]
    result = network_proximity_correlation(entries)
    # Entry has no network_proximity dimension set in _make_entry default
    assert result == {} or all(v["count"] == 0 for v in result.values())


# --- scoring_dimension_accuracy ---


def test_scoring_dimension_compares_accepted_vs_rejected():
    """Should calculate delta between accepted and rejected dimension averages."""
    entries = [
        _make_entry(entry_id="e1", outcome="accepted",
                     dimensions={"mission_alignment": 9, "evidence_match": 8}),
        _make_entry(entry_id="e2", outcome="rejected",
                     dimensions={"mission_alignment": 5, "evidence_match": 4}),
    ]
    result = scoring_dimension_accuracy(entries)
    ma = next(r for r in result if r["dimension"] == "mission_alignment")
    assert ma["avg_accepted"] == 9.0
    assert ma["avg_rejected"] == 5.0
    assert ma["delta"] == 4.0
    assert ma["predictive"] is True


# --- seasonal_patterns ---


def test_seasonal_monthly_groups():
    """Submissions should be grouped by month."""
    entries = [
        _make_entry(entry_id="e1", submitted_date="2026-02-24"),
        _make_entry(entry_id="e2", submitted_date="2026-02-25"),
        _make_entry(entry_id="e3", submitted_date="2026-03-01"),
    ]
    result = seasonal_patterns(entries)
    months = {r["month"] for r in result["monthly"]}
    assert "2026-02" in months
    assert "2026-03" in months

    feb = next(r for r in result["monthly"] if r["month"] == "2026-02")
    assert feb["submitted"] == 2


# --- pipeline_velocity ---


def test_pipeline_velocity_uses_response_time():
    """Should track time_to_response_days from conversion data."""
    entries = [
        _make_entry(entry_id="e1", time_to_response_days=3),
        _make_entry(entry_id="e2", time_to_response_days=7),
    ]
    result = pipeline_velocity(entries)
    response_stage = next((r for r in result if r["stage"] == "submitted_to_response"), None)
    assert response_stage is not None
    assert response_stage["count"] == 2
    assert response_stage["avg_days"] == 5.0


# --- generate_recommendations ---


def test_recommendations_zero_conversion():
    """Should recommend warm intros when conversion is zero with submissions."""
    summary = {
        "submitted": 10, "accepted": 0, "rejected": 5, "pending": 5,
        "conversion_rate": 0.0, "response_rate": 30.0,
        "submissions_per_month": 5.0, "total_entries": 15,
        "active_pipeline_size": 10, "period_days": 90,
    }
    recs = generate_recommendations(summary, [], [], {}, [], [])
    assert any("warm" in r.lower() or "referral" in r.lower() for r in recs)


def test_recommendations_returns_list():
    """Should always return a list."""
    summary = {
        "submitted": 0, "accepted": 0, "rejected": 0, "pending": 0,
        "conversion_rate": 0.0, "response_rate": 0.0,
        "submissions_per_month": 0.0, "total_entries": 0,
        "active_pipeline_size": 0, "period_days": 90,
    }
    recs = generate_recommendations(summary, [], [], {}, [], [])
    assert isinstance(recs, list)
    assert len(recs) >= 1


# --- format_markdown_report ---


def test_markdown_report_contains_sections():
    """Report should contain all 9 section headers."""
    summary = {
        "submitted": 1, "accepted": 0, "rejected": 0, "pending": 1,
        "conversion_rate": 0.0, "response_rate": 0.0,
        "submissions_per_month": 1.0, "total_entries": 1,
        "active_pipeline_size": 1, "period_days": 90,
    }
    md = format_markdown_report(
        summary, [], [], [], {}, [], {"weekly": [], "monthly": []}, [],
        ["Test recommendation"],
    )
    assert "## 1. Executive Summary" in md
    assert "## 2. Conversion Rates by Identity Position" in md
    assert "## 3. Conversion Rates by Channel/Portal" in md
    assert "## 4. Block ROI" in md
    assert "## 5. Network Proximity Correlation" in md
    assert "## 6. Scoring Dimension Accuracy" in md
    assert "## 7. Seasonal Patterns" in md
    assert "## 8. Pipeline Velocity" in md
    assert "## 10. Recommendations" in md


def test_markdown_report_includes_comparison_when_provided():
    """Report should include QoQ comparison section when compare_data is given."""
    summary = {
        "submitted": 1, "accepted": 0, "rejected": 0, "pending": 1,
        "conversion_rate": 0.0, "response_rate": 0.0,
        "submissions_per_month": 1.0, "total_entries": 1,
        "active_pipeline_size": 1, "period_days": 90,
    }
    compare_data = {
        "current": {"submitted": 5, "accepted": 1, "rejected": 2,
                     "conversion_rate": 20.0, "response_rate": 50.0},
        "previous": {"submitted": 3, "accepted": 0, "rejected": 1,
                      "conversion_rate": 0.0, "response_rate": 33.3},
    }
    md = format_markdown_report(
        summary, [], [], [], {}, [], {"weekly": [], "monthly": []}, [],
        ["Test recommendation"],
        compare_data=compare_data,
    )
    assert "Quarter-over-Quarter Comparison" in md
    assert "Previous" in md
    assert "Current" in md
