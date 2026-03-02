"""Tests for scripts/conversion_dashboard.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from conversion_dashboard import (
    compute_block_effectiveness,
    compute_portal_stats,
    compute_position_stats,
    compute_response_times,
    compute_track_stats,
    generate_dashboard,
)


def _make_entry(
    entry_id="test",
    portal="greenhouse",
    track="job",
    status="submitted",
    identity_position="independent-engineer",
    score=7.0,
    outcome=None,
    time_to_response=None,
    blocks_used=None,
    submitted_date="2026-01-15",
):
    entry = {
        "id": entry_id,
        "name": f"Test {entry_id}",
        "track": track,
        "status": status,
        "target": {"portal": portal, "organization": "Test Org"},
        "fit": {"score": score, "identity_position": identity_position},
        "timeline": {"submitted": submitted_date},
        "conversion": {},
    }
    if outcome:
        entry["outcome"] = outcome
        entry["status"] = "outcome"
    if time_to_response is not None:
        entry["conversion"]["time_to_response_days"] = time_to_response
        entry["conversion"]["response_received"] = True
    if blocks_used:
        entry["submission"] = {"blocks_used": blocks_used}
    return entry


# --- compute_portal_stats ---


def test_compute_portal_stats_empty():
    """Empty list returns empty portals dict."""
    result = compute_portal_stats([])
    assert result == {"portals": {}}


def test_compute_portal_stats_single():
    """One submitted entry returns correct portal stats."""
    entries = [_make_entry(portal="greenhouse")]
    result = compute_portal_stats(entries)
    assert "greenhouse" in result["portals"]
    assert result["portals"]["greenhouse"]["submitted"] == 1
    assert result["portals"]["greenhouse"]["responses"] == 0
    assert result["portals"]["greenhouse"]["interviews"] == 0


def test_compute_portal_stats_multiple_portals():
    """Entries group correctly by portal."""
    entries = [
        _make_entry(entry_id="a", portal="greenhouse"),
        _make_entry(entry_id="b", portal="lever"),
        _make_entry(entry_id="c", portal="greenhouse"),
    ]
    result = compute_portal_stats(entries)
    assert result["portals"]["greenhouse"]["submitted"] == 2
    assert result["portals"]["lever"]["submitted"] == 1


def test_compute_portal_stats_response_rate():
    """Response rate is calculated correctly."""
    entries = [
        _make_entry(entry_id="a", portal="greenhouse", time_to_response=5),
        _make_entry(entry_id="b", portal="greenhouse"),
        _make_entry(entry_id="c", portal="greenhouse", time_to_response=10),
        _make_entry(entry_id="d", portal="greenhouse"),
    ]
    result = compute_portal_stats(entries)
    # 2 responses out of 4 submitted = 50%
    assert result["portals"]["greenhouse"]["response_rate"] == 0.5


def test_compute_portal_stats_ignores_non_submitted():
    """Entries that are not in submitted-like statuses are excluded."""
    entries = [
        _make_entry(entry_id="a", portal="greenhouse", status="drafting"),
        _make_entry(entry_id="b", portal="greenhouse", status="qualified"),
    ]
    result = compute_portal_stats(entries)
    assert result == {"portals": {}}


# --- compute_position_stats ---


def test_compute_position_stats_empty():
    """Empty returns empty positions."""
    result = compute_position_stats([])
    assert result == {"positions": {}}


def test_compute_position_stats_groups():
    """Groups entries by identity_position with correct counts."""
    entries = [
        _make_entry(entry_id="a", identity_position="independent-engineer"),
        _make_entry(entry_id="b", identity_position="systems-artist"),
        _make_entry(entry_id="c", identity_position="independent-engineer", outcome="rejected"),
        _make_entry(entry_id="d", identity_position="systems-artist", outcome="accepted"),
    ]
    result = compute_position_stats(entries)
    positions = result["positions"]

    assert positions["independent-engineer"]["total"] == 2
    assert positions["independent-engineer"]["rejected"] == 1
    assert positions["systems-artist"]["total"] == 2
    assert positions["systems-artist"]["accepted"] == 1


def test_compute_position_stats_submitted_count():
    """Submitted count only includes entries with submitted-like statuses."""
    entries = [
        _make_entry(entry_id="a", identity_position="educator", status="drafting"),
        _make_entry(entry_id="b", identity_position="educator", status="submitted"),
        _make_entry(entry_id="c", identity_position="educator", status="interview"),
    ]
    result = compute_position_stats(entries)
    assert result["positions"]["educator"]["submitted"] == 2
    assert result["positions"]["educator"]["total"] == 3


# --- compute_track_stats ---


def test_compute_track_stats_empty():
    """Empty returns empty tracks."""
    result = compute_track_stats([])
    assert result == {"tracks": {}}


def test_compute_track_stats_counts():
    """Correct total and submitted counts per track."""
    entries = [
        _make_entry(entry_id="a", track="job", status="submitted"),
        _make_entry(entry_id="b", track="job", status="drafting"),
        _make_entry(entry_id="c", track="grant", status="submitted"),
    ]
    result = compute_track_stats(entries)
    tracks = result["tracks"]

    assert tracks["job"]["total"] == 2
    assert tracks["job"]["submitted"] == 1
    assert tracks["grant"]["total"] == 1
    assert tracks["grant"]["submitted"] == 1


def test_compute_track_stats_avg_score():
    """Average score is computed correctly per track."""
    entries = [
        _make_entry(entry_id="a", track="job", score=8.0),
        _make_entry(entry_id="b", track="job", score=6.0),
    ]
    result = compute_track_stats(entries)
    assert result["tracks"]["job"]["avg_score"] == 7.0


def test_compute_track_stats_no_response_days():
    """avg_days_to_response is None when no response data exists."""
    entries = [_make_entry(entry_id="a", track="grant")]
    result = compute_track_stats(entries)
    assert result["tracks"]["grant"]["avg_days_to_response"] is None


# --- compute_response_times ---


def test_compute_response_times_empty():
    """No data returns zeros."""
    result = compute_response_times([])
    assert result["overall"]["n"] == 0
    assert result["overall"]["mean"] == 0.0
    assert result["overall"]["median"] == 0.0
    assert result["by_portal"] == {}


def test_compute_response_times_with_data():
    """Calculates mean and median correctly."""
    entries = [
        _make_entry(entry_id="a", time_to_response=5),
        _make_entry(entry_id="b", time_to_response=10),
        _make_entry(entry_id="c", time_to_response=15),
    ]
    result = compute_response_times(entries)
    assert result["overall"]["n"] == 3
    assert result["overall"]["mean"] == 10.0
    assert result["overall"]["median"] == 10.0
    assert result["overall"]["min"] == 5
    assert result["overall"]["max"] == 15


def test_compute_response_times_even_count_median():
    """Median with even count averages the two middle values."""
    entries = [
        _make_entry(entry_id="a", time_to_response=4),
        _make_entry(entry_id="b", time_to_response=8),
        _make_entry(entry_id="c", time_to_response=12),
        _make_entry(entry_id="d", time_to_response=16),
    ]
    result = compute_response_times(entries)
    # Median of [4, 8, 12, 16] = (8 + 12) / 2 = 10.0
    assert result["overall"]["median"] == 10.0


def test_compute_response_times_by_portal():
    """Groups response times by portal."""
    entries = [
        _make_entry(entry_id="a", portal="greenhouse", time_to_response=7),
        _make_entry(entry_id="b", portal="lever", time_to_response=14),
        _make_entry(entry_id="c", portal="greenhouse", time_to_response=21),
    ]
    result = compute_response_times(entries)
    assert "greenhouse" in result["by_portal"]
    assert "lever" in result["by_portal"]
    assert result["by_portal"]["greenhouse"]["n"] == 2
    assert result["by_portal"]["lever"]["n"] == 1
    assert result["by_portal"]["greenhouse"]["mean"] == 14.0


def test_compute_response_times_ignores_missing():
    """Entries without time_to_response are excluded."""
    entries = [
        _make_entry(entry_id="a", time_to_response=10),
        _make_entry(entry_id="b"),  # no time_to_response
    ]
    result = compute_response_times(entries)
    assert result["overall"]["n"] == 1


# --- compute_block_effectiveness ---


def test_compute_block_effectiveness_no_blocks():
    """Entries without blocks_used return empty blocks dict."""
    entries = [_make_entry(entry_id="a", outcome="rejected")]
    result = compute_block_effectiveness(entries)
    assert result == {"blocks": {}}


def test_compute_block_effectiveness_with_outcomes():
    """Tracks accepted vs rejected block usage."""
    entries = [
        _make_entry(
            entry_id="a",
            outcome="accepted",
            blocks_used=["identity/2min", "projects/organvm-system"],
        ),
        _make_entry(
            entry_id="b",
            outcome="rejected",
            blocks_used=["identity/2min", "framings/systems-artist"],
        ),
        _make_entry(
            entry_id="c",
            outcome="rejected",
            blocks_used=["identity/2min"],
        ),
    ]
    result = compute_block_effectiveness(entries)
    blocks = result["blocks"]

    assert blocks["identity/2min"]["used_in"] == 3
    assert blocks["identity/2min"]["accepted"] == 1
    assert blocks["identity/2min"]["rejected"] == 2
    # rate = 1 / (1 + 2) = 0.333...
    assert round(blocks["identity/2min"]["rate"], 2) == 0.33

    assert blocks["projects/organvm-system"]["used_in"] == 1
    assert blocks["projects/organvm-system"]["accepted"] == 1
    assert blocks["projects/organvm-system"]["rate"] == 1.0


def test_compute_block_effectiveness_no_outcome_entries_ignored():
    """Entries without an outcome field are excluded entirely."""
    entries = [
        _make_entry(entry_id="a", blocks_used=["identity/2min"]),
    ]
    result = compute_block_effectiveness(entries)
    assert result == {"blocks": {}}


# --- generate_dashboard ---


def test_generate_dashboard_returns_string():
    """Returns a string."""
    result = generate_dashboard(entries=[])
    assert isinstance(result, str)


def test_generate_dashboard_has_header():
    """Contains the dashboard header."""
    result = generate_dashboard(entries=[])
    assert "CONVERSION INTELLIGENCE DASHBOARD" in result


def test_generate_dashboard_has_portal_section():
    """Contains portal performance section."""
    entries = [_make_entry(portal="greenhouse")]
    result = generate_dashboard(entries=entries)
    assert "PORTAL PERFORMANCE" in result
    assert "greenhouse" in result


def test_generate_dashboard_has_position_section():
    """Contains identity position section."""
    entries = [_make_entry(identity_position="systems-artist")]
    result = generate_dashboard(entries=entries)
    assert "IDENTITY POSITION PERFORMANCE" in result


def test_generate_dashboard_has_track_section():
    """Contains track performance section."""
    entries = [_make_entry(track="grant")]
    result = generate_dashboard(entries=entries)
    assert "TRACK PERFORMANCE" in result


def test_generate_dashboard_has_data_quality():
    """Contains data quality section."""
    result = generate_dashboard(entries=[])
    assert "DATA QUALITY" in result


def test_generate_dashboard_has_response_time_section():
    """Contains response time analysis section."""
    result = generate_dashboard(entries=[])
    assert "RESPONSE TIME ANALYSIS" in result


def test_generate_dashboard_has_block_section():
    """Contains block effectiveness section."""
    result = generate_dashboard(entries=[])
    assert "BLOCK EFFECTIVENESS" in result


def test_generate_dashboard_has_calibration_section():
    """Contains scoring calibration section."""
    result = generate_dashboard(entries=[])
    assert "SCORING CALIBRATION STATUS" in result


def test_generate_dashboard_has_hypothesis_section():
    """Contains hypothesis patterns section."""
    result = generate_dashboard(entries=[])
    assert "HYPOTHESIS PATTERNS" in result


def test_generate_dashboard_with_mixed_entries():
    """Dashboard renders without errors with a realistic mix of entries."""
    entries = [
        _make_entry(entry_id="a", portal="greenhouse", track="job", status="submitted"),
        _make_entry(entry_id="b", portal="lever", track="grant", status="submitted", score=8.5),
        _make_entry(
            entry_id="c", portal="greenhouse", track="job",
            outcome="rejected", time_to_response=12,
            blocks_used=["identity/2min"],
        ),
        _make_entry(
            entry_id="d", portal="ashby", track="job",
            outcome="accepted", time_to_response=7,
            identity_position="creative-technologist",
            blocks_used=["identity/2min", "projects/organvm-system"],
        ),
    ]
    result = generate_dashboard(entries=entries)
    assert "CONVERSION INTELLIGENCE DASHBOARD" in result
    assert "greenhouse" in result
    assert "lever" in result
    assert "ashby" in result
