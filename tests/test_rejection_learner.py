"""Tests for scripts/rejection_learner.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from pipeline_lib import DIMENSION_ORDER
from rejection_learner import (
    analyze_block_correlation,
    analyze_dimension_weakness,
    analyze_portal_rejection_rate,
    analyze_position_rejection_rate,
    analyze_score_distribution,
    classify_entries,
    generate_recommendations,
    run_full_analysis,
)


def _make_entry(
    entry_id="test-entry",
    outcome=None,
    score=6.0,
    identity_position="independent-engineer",
    portal="greenhouse",
    track="job",
    blocks_used=None,
    dimension_overrides=None,
    deadline_date=None,
    submitted_date=None,
):
    """Build a minimal pipeline entry for testing."""
    dims = {dim: 5 for dim in DIMENSION_ORDER}
    if dimension_overrides:
        dims.update(dimension_overrides)
    entry = {
        "id": entry_id,
        "outcome": outcome,
        "track": track,
        "status": "outcome" if outcome else "submitted",
        "fit": {
            "score": score,
            "identity_position": identity_position,
            "dimensions": dims,
        },
        "target": {
            "portal": portal,
            "organization": "TestOrg",
        },
        "submission": {
            "blocks_used": blocks_used or {},
        },
        "deadline": {
            "date": deadline_date,
            "type": "rolling" if not deadline_date else "fixed",
        },
        "timeline": {
            "submitted": submitted_date,
        },
    }
    return entry


# --- classify_entries ---


def test_classify_entries_separates_outcomes():
    """Entries are correctly classified by outcome."""
    entries = [
        _make_entry(entry_id="rej-1", outcome="rejected"),
        _make_entry(entry_id="rej-2", outcome="rejected"),
        _make_entry(entry_id="wd-1", outcome="withdrawn"),
        _make_entry(entry_id="exp-1", outcome="expired"),
        _make_entry(entry_id="ack-1", outcome="acknowledged"),
        _make_entry(entry_id="intv-1", outcome="interview"),
        _make_entry(entry_id="pend-1", outcome=None),
    ]
    groups = classify_entries(entries)
    assert len(groups["rejected"]) == 2
    assert len(groups["withdrawn"]) == 1
    assert len(groups["expired"]) == 1
    assert len(groups["acknowledged"]) == 1
    # positive includes acknowledged + interview
    assert len(groups["positive"]) == 2
    assert len(groups["pending"]) == 1


# --- analyze_dimension_weakness ---


def test_dimension_weakness_detects_lower_rejected_scores():
    """Rejected entries with lower dimension scores produce negative deltas."""
    rejected = [
        _make_entry(
            entry_id="rej-1",
            outcome="rejected",
            dimension_overrides={"mission_alignment": 3, "evidence_match": 4},
        ),
        _make_entry(
            entry_id="rej-2",
            outcome="rejected",
            dimension_overrides={"mission_alignment": 4, "evidence_match": 3},
        ),
    ]
    non_rejected = [
        _make_entry(
            entry_id="good-1",
            outcome="acknowledged",
            dimension_overrides={"mission_alignment": 8, "evidence_match": 9},
        ),
        _make_entry(
            entry_id="good-2",
            outcome=None,
            dimension_overrides={"mission_alignment": 7, "evidence_match": 8},
        ),
    ]
    analysis = analyze_dimension_weakness(rejected, non_rejected)

    # mission_alignment: rejected avg=3.5, non-rejected avg=7.5, delta=-4.0
    assert analysis["mission_alignment"]["delta"] < 0
    assert analysis["mission_alignment"]["rejected_avg"] == 3.5
    assert analysis["mission_alignment"]["non_rejected_avg"] == 7.5

    # evidence_match: rejected avg=3.5, non-rejected avg=8.5, delta=-5.0
    assert analysis["evidence_match"]["delta"] < 0
    assert analysis["evidence_match"]["rejected_avg"] == 3.5


def test_dimension_weakness_no_delta_when_no_rejected():
    """When there are no rejected entries, deltas are None."""
    rejected = []
    non_rejected = [
        _make_entry(entry_id="good-1", outcome="acknowledged"),
    ]
    analysis = analyze_dimension_weakness(rejected, non_rejected)
    for dim in DIMENSION_ORDER:
        assert analysis[dim]["rejected_avg"] is None
        assert analysis[dim]["delta"] is None


# --- analyze_position_rejection_rate ---


def test_position_rejection_rate_calculation():
    """Rejection rates are calculated correctly per identity position."""
    entries = [
        _make_entry(entry_id="ie-1", outcome="rejected", identity_position="independent-engineer"),
        _make_entry(entry_id="ie-2", outcome="rejected", identity_position="independent-engineer"),
        _make_entry(entry_id="ie-3", outcome="acknowledged", identity_position="independent-engineer"),
        _make_entry(entry_id="sa-1", outcome=None, identity_position="systems-artist"),
        _make_entry(entry_id="sa-2", outcome=None, identity_position="systems-artist"),
    ]
    result = analyze_position_rejection_rate(entries)
    assert result["independent-engineer"]["total"] == 3
    assert result["independent-engineer"]["rejected"] == 2
    assert abs(result["independent-engineer"]["rate"] - 0.667) < 0.01
    assert result["systems-artist"]["rejected"] == 0
    assert result["systems-artist"]["rate"] == 0.0


# --- analyze_portal_rejection_rate ---


def test_portal_rejection_rate_calculation():
    """Rejection rates are calculated per portal type."""
    entries = [
        _make_entry(entry_id="gh-1", outcome="rejected", portal="greenhouse"),
        _make_entry(entry_id="gh-2", outcome="rejected", portal="greenhouse"),
        _make_entry(entry_id="gh-3", outcome=None, portal="greenhouse"),
        _make_entry(entry_id="ash-1", outcome=None, portal="ashby"),
    ]
    result = analyze_portal_rejection_rate(entries)
    assert result["greenhouse"]["total"] == 3
    assert result["greenhouse"]["rejected"] == 2
    assert abs(result["greenhouse"]["rate"] - 0.667) < 0.01
    assert result["ashby"]["rejected"] == 0


# --- analyze_block_correlation ---


def test_block_correlation_detects_overrepresented_blocks():
    """Blocks appearing more often in rejected entries get positive lift."""
    rejected = [
        _make_entry(
            entry_id="rej-1",
            outcome="rejected",
            blocks_used={"framing": "framings/risky-block", "evidence": "evidence/differentiators"},
        ),
        _make_entry(
            entry_id="rej-2",
            outcome="rejected",
            blocks_used={"framing": "framings/risky-block"},
        ),
    ]
    non_rejected = [
        _make_entry(
            entry_id="good-1",
            outcome="acknowledged",
            blocks_used={"framing": "framings/safe-block", "evidence": "evidence/differentiators"},
        ),
        _make_entry(
            entry_id="good-2",
            outcome=None,
            blocks_used={"framing": "framings/safe-block", "evidence": "evidence/differentiators"},
        ),
    ]
    result = analyze_block_correlation(rejected, non_rejected)

    # framings/risky-block: 100% in rejected, 0% in non-rejected -> lift = 1.0
    assert result["framings/risky-block"]["rejected_count"] == 2
    assert result["framings/risky-block"]["non_rejected_count"] == 0
    assert result["framings/risky-block"]["lift"] == 1.0

    # evidence/differentiators: 50% in rejected, 100% in non-rejected -> lift = -0.5
    assert result["evidence/differentiators"]["lift"] == -0.5

    # framings/safe-block: 0% in rejected, 100% in non-rejected -> lift = -1.0
    assert result["framings/safe-block"]["lift"] == -1.0


def test_block_correlation_handles_list_blocks():
    """Block extraction works with list-style blocks_used."""
    rejected = [
        _make_entry(
            entry_id="rej-1",
            outcome="rejected",
            blocks_used=["identity/2min", "projects/krypto-velamen"],
        ),
    ]
    non_rejected = [
        _make_entry(
            entry_id="good-1",
            outcome="acknowledged",
            blocks_used=["identity/2min", "projects/organvm-system"],
        ),
    ]
    result = analyze_block_correlation(rejected, non_rejected)
    assert "identity/2min" in result
    assert "projects/krypto-velamen" in result
    assert "projects/organvm-system" in result


# --- analyze_score_distribution ---


def test_score_distribution_means():
    """Composite score distribution computes correct means."""
    rejected = [
        _make_entry(entry_id="rej-1", outcome="rejected", score=5.0),
        _make_entry(entry_id="rej-2", outcome="rejected", score=6.0),
    ]
    non_rejected = [
        _make_entry(entry_id="good-1", outcome="acknowledged", score=8.0),
        _make_entry(entry_id="good-2", outcome=None, score=9.0),
    ]
    result = analyze_score_distribution(rejected, non_rejected)
    assert result["rejected"]["mean"] == 5.5
    assert result["rejected"]["min"] == 5.0
    assert result["rejected"]["max"] == 6.0
    assert result["non_rejected"]["mean"] == 8.5


# --- run_full_analysis ---


def test_full_analysis_insufficient_data():
    """With fewer rejections than min_samples, recommendations are empty."""
    entries = [
        _make_entry(entry_id="rej-1", outcome="rejected"),
        _make_entry(entry_id="good-1", outcome="acknowledged"),
    ]
    result = run_full_analysis(entries, min_samples=5)
    assert result["summary"]["rejected"] == 1
    assert result["recommendations"] == []


def test_full_analysis_with_sufficient_data():
    """With enough rejections, analysis populates all sections."""
    entries = []
    # Create 5 rejected entries with weak mission_alignment
    for i in range(5):
        entries.append(
            _make_entry(
                entry_id=f"rej-{i}",
                outcome="rejected",
                score=5.0,
                dimension_overrides={"mission_alignment": 3},
            )
        )
    # Create 5 non-rejected entries with strong mission_alignment
    for i in range(5):
        entries.append(
            _make_entry(
                entry_id=f"good-{i}",
                outcome="acknowledged",
                score=8.0,
                dimension_overrides={"mission_alignment": 9},
            )
        )

    result = run_full_analysis(entries, min_samples=3)
    assert result["summary"]["rejected"] == 5
    assert result["summary"]["positive"] == 5
    assert len(result["dimension_weakness"]) == len(DIMENSION_ORDER)
    assert result["dimension_weakness"]["mission_alignment"]["delta"] < 0
    # Recommendations should be non-empty with 5 rejections and clear signal
    assert len(result["recommendations"]) > 0


# --- generate_recommendations ---


def test_recommendations_dimension_weakness():
    """Recommendations flag dimensions with delta < -1.0."""
    dim_analysis = {
        dim: {
            "rejected_avg": 4.0,
            "non_rejected_avg": 7.0,
            "delta": -3.0,
            "rejected_n": 5,
            "non_rejected_n": 10,
        }
        if dim == "mission_alignment"
        else {
            "rejected_avg": 5.0,
            "non_rejected_avg": 5.0,
            "delta": 0.0,
            "rejected_n": 5,
            "non_rejected_n": 10,
        }
        for dim in DIMENSION_ORDER
    }
    recs = generate_recommendations(
        dim_analysis=dim_analysis,
        position_analysis={},
        portal_analysis={},
        block_analysis={},
        min_samples=3,
    )
    assert any("mission_alignment" in r for r in recs)


def test_recommendations_no_patterns():
    """No strong patterns yields the default message."""
    dim_analysis = {
        dim: {
            "rejected_avg": 5.0,
            "non_rejected_avg": 5.0,
            "delta": 0.0,
            "rejected_n": 2,
            "non_rejected_n": 10,
        }
        for dim in DIMENSION_ORDER
    }
    recs = generate_recommendations(
        dim_analysis=dim_analysis,
        position_analysis={},
        portal_analysis={},
        block_analysis={},
        min_samples=5,
    )
    assert any("No statistically significant" in r for r in recs)


# --- analyze_timing_correlation ---

from rejection_learner import analyze_timing_correlation, print_report, print_single_dimension


def test_timing_correlation_early_mid_late():
    """Entries are classified by days-before-deadline into early/mid/late."""
    entries = [
        # Early: submitted 20 days before deadline
        _make_entry(
            entry_id="early-1",
            outcome="rejected",
            deadline_date="2026-04-01",
            submitted_date="2026-03-12",
        ),
        # Mid: submitted 10 days before deadline
        _make_entry(
            entry_id="mid-1",
            outcome="rejected",
            deadline_date="2026-04-01",
            submitted_date="2026-03-22",
        ),
        # Late: submitted 3 days before deadline
        _make_entry(
            entry_id="late-1",
            outcome=None,
            deadline_date="2026-04-01",
            submitted_date="2026-03-29",
        ),
        # Another late entry, rejected
        _make_entry(
            entry_id="late-2",
            outcome="rejected",
            deadline_date="2026-04-01",
            submitted_date="2026-03-30",
        ),
    ]
    result = analyze_timing_correlation(entries)
    assert "early" in result
    assert result["early"]["total"] == 1
    assert result["early"]["rejected"] == 1
    assert result["early"]["rate"] == 1.0

    assert "mid" in result
    assert result["mid"]["total"] == 1
    assert result["mid"]["rejected"] == 1

    assert "late" in result
    assert result["late"]["total"] == 2
    assert result["late"]["rejected"] == 1
    assert result["late"]["rate"] == 0.5


def test_timing_correlation_rolling_group():
    """Entries with deadline.type='rolling' land in the rolling group."""
    entries = [
        _make_entry(
            entry_id="rolling-1",
            outcome="rejected",
            deadline_date=None,
            submitted_date="2026-03-01",
        ),
        _make_entry(
            entry_id="rolling-2",
            outcome=None,
            deadline_date=None,
            submitted_date="2026-03-05",
        ),
    ]
    # _make_entry sets type="rolling" when deadline_date is None
    result = analyze_timing_correlation(entries)
    assert "rolling" in result
    assert result["rolling"]["total"] == 2
    assert result["rolling"]["rejected"] == 1
    assert result["rolling"]["rate"] == 0.5


def test_timing_correlation_empty_entries():
    """Empty entry list produces empty result."""
    result = analyze_timing_correlation([])
    assert result == {}


def test_timing_correlation_no_deadline_no_submitted():
    """Entries with missing dates are excluded from timing groups (except rolling)."""
    entries = [
        _make_entry(
            entry_id="no-dates",
            outcome="rejected",
            deadline_date=None,
            submitted_date=None,
        ),
    ]
    result = analyze_timing_correlation(entries)
    # Should only appear in rolling (because type=rolling), not early/mid/late
    assert "early" not in result
    assert "mid" not in result
    assert "late" not in result
    assert "rolling" in result


def test_timing_correlation_mixed_fixed_and_rolling():
    """Fixed-deadline entries get timing classification while rolling entries get rolling group."""
    entries = [
        _make_entry(
            entry_id="fixed-early",
            outcome="rejected",
            deadline_date="2026-05-01",
            submitted_date="2026-04-01",
        ),
        _make_entry(
            entry_id="rolling-entry",
            outcome=None,
            deadline_date=None,
            submitted_date="2026-04-10",
        ),
    ]
    result = analyze_timing_correlation(entries)
    assert "early" in result
    assert result["early"]["total"] == 1
    assert "rolling" in result
    assert result["rolling"]["total"] == 1


# --- print_report (rejection_learner) ---


def test_print_report_shows_header_and_summary(capsys):
    """print_report outputs the main header line and entry counts."""
    entries = []
    for i in range(5):
        entries.append(
            _make_entry(entry_id=f"rej-{i}", outcome="rejected", score=5.0)
        )
    for i in range(3):
        entries.append(
            _make_entry(entry_id=f"good-{i}", outcome="acknowledged", score=8.0)
        )
    analysis = run_full_analysis(entries, min_samples=3)
    print_report(analysis, min_samples=3)
    captured = capsys.readouterr().out
    assert "Rejection Patterns Report" in captured
    assert "Total entries analyzed:" in captured
    assert "Rejected:" in captured
    assert "Acknowledged:" in captured


def test_print_report_shows_dimension_section(capsys):
    """print_report displays the Dimension Weakness Ranking section."""
    entries = []
    for i in range(5):
        entries.append(
            _make_entry(
                entry_id=f"rej-{i}",
                outcome="rejected",
                score=5.0,
                dimension_overrides={"mission_alignment": 3},
            )
        )
    for i in range(5):
        entries.append(
            _make_entry(
                entry_id=f"good-{i}",
                outcome="acknowledged",
                score=8.0,
                dimension_overrides={"mission_alignment": 9},
            )
        )
    analysis = run_full_analysis(entries, min_samples=3)
    print_report(analysis, min_samples=3)
    captured = capsys.readouterr().out
    assert "Dimension Weakness Ranking" in captured
    assert "mission_alignment" in captured


def test_print_report_shows_position_and_portal_sections(capsys):
    """print_report includes position and portal rejection rate tables."""
    entries = []
    for i in range(4):
        entries.append(
            _make_entry(
                entry_id=f"rej-{i}",
                outcome="rejected",
                portal="greenhouse",
                identity_position="independent-engineer",
            )
        )
    entries.append(
        _make_entry(
            entry_id="good-1",
            outcome="acknowledged",
            portal="ashby",
            identity_position="systems-artist",
        )
    )
    analysis = run_full_analysis(entries, min_samples=3)
    print_report(analysis, min_samples=3)
    captured = capsys.readouterr().out
    assert "Rejection Rate by Identity Position" in captured
    assert "independent-engineer" in captured
    assert "Rejection Rate by Portal Type" in captured
    assert "greenhouse" in captured


def test_print_report_shows_recommendations(capsys):
    """print_report displays the Recommended Adjustments section."""
    entries = []
    for i in range(5):
        entries.append(
            _make_entry(
                entry_id=f"rej-{i}",
                outcome="rejected",
                score=4.0,
                dimension_overrides={"mission_alignment": 2},
            )
        )
    for i in range(5):
        entries.append(
            _make_entry(
                entry_id=f"good-{i}",
                outcome="acknowledged",
                score=9.0,
                dimension_overrides={"mission_alignment": 9},
            )
        )
    analysis = run_full_analysis(entries, min_samples=3)
    print_report(analysis, min_samples=3)
    captured = capsys.readouterr().out
    assert "Recommended Adjustments" in captured


def test_print_report_insufficient_data(capsys):
    """With too few rejections, print_report shows insufficient data message."""
    entries = [
        _make_entry(entry_id="rej-1", outcome="rejected"),
        _make_entry(entry_id="good-1", outcome="acknowledged"),
    ]
    analysis = run_full_analysis(entries, min_samples=5)
    print_report(analysis, min_samples=5)
    captured = capsys.readouterr().out
    assert "DATA NOTICE" in captured


def test_print_report_shows_timing_section(capsys):
    """print_report includes the timing correlation section when data exists."""
    entries = []
    for i in range(4):
        entries.append(
            _make_entry(
                entry_id=f"rej-{i}",
                outcome="rejected",
                deadline_date="2026-05-01",
                submitted_date="2026-04-28",
            )
        )
    entries.append(
        _make_entry(
            entry_id="good-1",
            outcome="acknowledged",
            deadline_date="2026-05-01",
            submitted_date="2026-04-01",
        )
    )
    analysis = run_full_analysis(entries, min_samples=3)
    print_report(analysis, min_samples=3)
    captured = capsys.readouterr().out
    assert "Rejection Rate by Submission Timing" in captured


# --- print_single_dimension ---


def test_print_single_dimension_header_and_stats(capsys, monkeypatch):
    """print_single_dimension shows the dimension name and statistics."""
    entries = []
    for i in range(4):
        entries.append(
            _make_entry(
                entry_id=f"rej-{i}",
                outcome="rejected",
                dimension_overrides={"mission_alignment": 3},
            )
        )
    for i in range(3):
        entries.append(
            _make_entry(
                entry_id=f"good-{i}",
                outcome="acknowledged",
                dimension_overrides={"mission_alignment": 8},
            )
        )
    analysis = run_full_analysis(entries, min_samples=3)

    # Monkeypatch load_outcome_entries to return our test entries
    import rejection_learner as rl_mod
    monkeypatch.setattr(rl_mod, "load_outcome_entries", lambda: entries)

    print_single_dimension(analysis, "mission_alignment")
    captured = capsys.readouterr().out
    assert "Dimension Analysis: mission_alignment" in captured
    assert "Rejected average:" in captured
    assert "Non-rejected average:" in captured
    assert "Delta:" in captured


def test_print_single_dimension_strong_predictor_signal(capsys, monkeypatch):
    """print_single_dimension shows STRONG PREDICTOR for delta < -2.0."""
    entries = []
    for i in range(4):
        entries.append(
            _make_entry(
                entry_id=f"rej-{i}",
                outcome="rejected",
                dimension_overrides={"evidence_match": 2},
            )
        )
    for i in range(4):
        entries.append(
            _make_entry(
                entry_id=f"good-{i}",
                outcome="acknowledged",
                dimension_overrides={"evidence_match": 9},
            )
        )
    analysis = run_full_analysis(entries, min_samples=3)

    import rejection_learner as rl_mod
    monkeypatch.setattr(rl_mod, "load_outcome_entries", lambda: entries)

    print_single_dimension(analysis, "evidence_match")
    captured = capsys.readouterr().out
    assert "STRONG PREDICTOR" in captured


def test_print_single_dimension_unknown_exits(monkeypatch):
    """print_single_dimension exits with error for unknown dimension."""
    entries = [_make_entry(entry_id="e1", outcome="rejected")]
    analysis = run_full_analysis(entries, min_samples=1)

    import pytest
    with pytest.raises(SystemExit):
        print_single_dimension(analysis, "nonexistent_dimension")
