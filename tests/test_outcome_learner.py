"""Tests for scripts/outcome_learner.py"""

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from outcome_learner import (
    analyze_dimension_accuracy,
    collect_outcome_data,
    compute_weight_recommendations,
    cross_reference_hypotheses,
    generate_calibration_report,
    load_calibration,
    save_calibration,
)
from pipeline_lib import DIMENSION_ORDER


def _make_outcome_record(
    entry_id="test-entry",
    outcome="rejected",
    composite_score=6.0,
    dimension_scores=None,
    track="job",
    identity_position="independent-engineer",
):
    """Build a minimal outcome data record."""
    if dimension_scores is None:
        dimension_scores = {dim: 5 for dim in DIMENSION_ORDER}
    return {
        "entry_id": entry_id,
        "outcome": outcome,
        "composite_score": composite_score,
        "dimension_scores": dimension_scores,
        "track": track,
        "identity_position": identity_position,
    }


# --- analyze_dimension_accuracy ---


def test_analyze_dimension_accuracy_empty_data():
    """Empty data returns all dimensions with insufficient_data signal."""
    analysis = analyze_dimension_accuracy([])
    for dim in DIMENSION_ORDER:
        assert dim in analysis
        assert analysis[dim]["signal"] == "insufficient_data"


def test_analyze_dimension_accuracy_accepted_only():
    """Only accepted entries — rejected_avg is None, signal is insufficient_data."""
    data = [_make_outcome_record(outcome="accepted")]
    analysis = analyze_dimension_accuracy(data)
    for dim in DIMENSION_ORDER:
        assert analysis[dim]["accepted_avg"] is not None
        assert analysis[dim]["rejected_avg"] is None
        assert analysis[dim]["signal"] == "insufficient_data"


def test_analyze_dimension_accuracy_rejected_only():
    """Only rejected entries — accepted_avg is None."""
    data = [_make_outcome_record(outcome="rejected")]
    analysis = analyze_dimension_accuracy(data)
    for dim in DIMENSION_ORDER:
        assert analysis[dim]["accepted_avg"] is None
        assert analysis[dim]["rejected_avg"] is not None


def test_analyze_dimension_accuracy_neutral():
    """Similar scores for accepted and rejected → neutral signal."""
    dims = {dim: 5 for dim in DIMENSION_ORDER}
    data = [
        _make_outcome_record(outcome="accepted", dimension_scores=dims),
        _make_outcome_record(outcome="rejected", dimension_scores=dims),
    ]
    analysis = analyze_dimension_accuracy(data)
    for dim in DIMENSION_ORDER:
        assert analysis[dim]["signal"] == "neutral"
        assert analysis[dim]["delta"] == 0.0


def test_analyze_dimension_accuracy_overweighted():
    """Rejected scores higher than accepted → overweighted signal."""
    acc_dims = {dim: 3 for dim in DIMENSION_ORDER}
    rej_dims = {dim: 5 for dim in DIMENSION_ORDER}
    data = [
        _make_outcome_record(outcome="accepted", dimension_scores=acc_dims),
        _make_outcome_record(outcome="rejected", dimension_scores=rej_dims),
    ]
    analysis = analyze_dimension_accuracy(data)
    for dim in DIMENSION_ORDER:
        assert analysis[dim]["signal"] == "overweighted"
        assert analysis[dim]["delta"] < 0


def test_analyze_dimension_accuracy_underweighted():
    """Accepted scores much higher than rejected → underweighted signal."""
    acc_dims = {dim: 9 for dim in DIMENSION_ORDER}
    rej_dims = {dim: 3 for dim in DIMENSION_ORDER}
    data = [
        _make_outcome_record(outcome="accepted", dimension_scores=acc_dims),
        _make_outcome_record(outcome="rejected", dimension_scores=rej_dims),
    ]
    analysis = analyze_dimension_accuracy(data)
    for dim in DIMENSION_ORDER:
        assert analysis[dim]["signal"] == "underweighted"
        assert analysis[dim]["delta"] > 0


def test_analyze_dimension_accuracy_counts():
    """Accepted_n and rejected_n are counted correctly."""
    data = [
        _make_outcome_record(entry_id="a1", outcome="accepted"),
        _make_outcome_record(entry_id="a2", outcome="accepted"),
        _make_outcome_record(entry_id="r1", outcome="rejected"),
    ]
    analysis = analyze_dimension_accuracy(data)
    for dim in DIMENSION_ORDER:
        assert analysis[dim]["accepted_n"] == 2
        assert analysis[dim]["rejected_n"] == 1


def test_analyze_skips_withdrawn():
    """Withdrawn entries don't contribute to accepted or rejected averages."""
    data = [
        _make_outcome_record(outcome="withdrawn"),
        _make_outcome_record(outcome="accepted"),
    ]
    analysis = analyze_dimension_accuracy(data)
    for dim in DIMENSION_ORDER:
        assert analysis[dim]["accepted_n"] == 1
        assert analysis[dim]["rejected_n"] == 0
        assert analysis[dim]["signal"] == "insufficient_data"


def test_analyze_missing_dimension_scores():
    """Entries with missing dimension scores are handled gracefully."""
    data = [
        _make_outcome_record(outcome="accepted", dimension_scores={}),
        _make_outcome_record(outcome="rejected", dimension_scores={"mission_alignment": 5}),
    ]
    analysis = analyze_dimension_accuracy(data)
    assert analysis["mission_alignment"]["rejected_n"] == 1
    assert analysis["mission_alignment"]["accepted_n"] == 0


# --- compute_weight_recommendations ---


def test_compute_weight_recommendations_no_signal():
    """All neutral signals → no weight changes, confidence 'none'."""
    analysis = {dim: {"signal": "neutral", "accepted_n": 5, "rejected_n": 5} for dim in DIMENSION_ORDER}
    base_weights = {dim: 1.0 / len(DIMENSION_ORDER) for dim in DIMENSION_ORDER}
    recs = compute_weight_recommendations(analysis, base_weights)
    assert recs["confidence"] == "none"
    assert not recs["sufficient_data"]


def test_compute_weight_recommendations_overweighted_decreases():
    """Overweighted dimension gets decreased weight."""
    analysis = {dim: {"signal": "neutral", "accepted_n": 15, "rejected_n": 15} for dim in DIMENSION_ORDER}
    analysis["portal_friction"]["signal"] = "overweighted"
    base_weights = {dim: 1.0 / len(DIMENSION_ORDER) for dim in DIMENSION_ORDER}
    recs = compute_weight_recommendations(analysis, base_weights)
    assert recs["adjustments"]["portal_friction"] == "decrease"


def test_compute_weight_recommendations_underweighted_increases():
    """Underweighted dimension gets increased weight."""
    analysis = {dim: {"signal": "neutral", "accepted_n": 15, "rejected_n": 15} for dim in DIMENSION_ORDER}
    analysis["mission_alignment"]["signal"] = "underweighted"
    base_weights = {dim: 1.0 / len(DIMENSION_ORDER) for dim in DIMENSION_ORDER}
    recs = compute_weight_recommendations(analysis, base_weights)
    assert recs["adjustments"]["mission_alignment"] == "increase"


def test_compute_weight_recommendations_weights_sum_to_one():
    """Recommended weights sum to 1.0."""
    analysis = {dim: {"signal": "neutral", "accepted_n": 15, "rejected_n": 15} for dim in DIMENSION_ORDER}
    analysis["portal_friction"]["signal"] = "overweighted"
    analysis["mission_alignment"]["signal"] = "underweighted"
    base_weights = {dim: 1.0 / len(DIMENSION_ORDER) for dim in DIMENSION_ORDER}
    recs = compute_weight_recommendations(analysis, base_weights)
    total = sum(recs["weights"].values())
    assert abs(total - 1.0) < 0.01


def test_compute_weight_recommendations_confidence_levels():
    """Confidence scales with sample size (avg_n = accepted_n + rejected_n per dimension)."""
    # avg_n = (accepted_n + rejected_n) * num_dims / num_dims = accepted_n + rejected_n
    for n, expected in [(2, "very_low"), (4, "low"), (6, "moderate"), (12, "high")]:
        analysis = {dim: {"signal": "neutral", "accepted_n": n, "rejected_n": n} for dim in DIMENSION_ORDER}
        analysis["mission_alignment"]["signal"] = "underweighted"
        base_weights = {dim: 1.0 / len(DIMENSION_ORDER) for dim in DIMENSION_ORDER}
        recs = compute_weight_recommendations(analysis, base_weights)
        assert recs["confidence"] == expected, f"n={n} expected {expected}, got {recs['confidence']}"


# --- generate_calibration_report ---


def test_generate_calibration_report_insufficient_data():
    """Report notes insufficient data when only withdrawn outcomes."""
    data = [_make_outcome_record(outcome="withdrawn")]
    analysis = analyze_dimension_accuracy(data)
    base = {dim: 1.0 / len(DIMENSION_ORDER) for dim in DIMENSION_ORDER}
    recs = compute_weight_recommendations(analysis, base)
    report = generate_calibration_report(data, analysis, recs)
    assert "INSUFFICIENT DATA" in report


def test_generate_calibration_report_with_data():
    """Report includes dimension accuracy table when data exists."""
    data = [
        _make_outcome_record(outcome="accepted"),
        _make_outcome_record(outcome="rejected"),
    ]
    analysis = analyze_dimension_accuracy(data)
    base = {dim: 1.0 / len(DIMENSION_ORDER) for dim in DIMENSION_ORDER}
    recs = compute_weight_recommendations(analysis, base)
    report = generate_calibration_report(data, analysis, recs)
    assert "DIMENSION ACCURACY" in report
    assert "mission_alignment" in report


def test_generate_calibration_report_outcome_counts():
    """Report shows correct outcome counts."""
    data = [
        _make_outcome_record(entry_id="a1", outcome="accepted"),
        _make_outcome_record(entry_id="r1", outcome="rejected"),
        _make_outcome_record(entry_id="w1", outcome="withdrawn"),
    ]
    analysis = analyze_dimension_accuracy(data)
    base = {dim: 1.0 / len(DIMENSION_ORDER) for dim in DIMENSION_ORDER}
    recs = compute_weight_recommendations(analysis, base)
    report = generate_calibration_report(data, analysis, recs)
    assert "Outcomes collected: 3" in report


# --- save_calibration / load_calibration ---


def test_save_calibration_writes_file(tmp_path, monkeypatch):
    """save_calibration writes a valid YAML file."""
    monkeypatch.setattr("outcome_learner.SIGNALS_DIR", tmp_path)
    monkeypatch.setattr("outcome_learner.CALIBRATION_FILE", tmp_path / "weight-calibration.yaml")

    recs = {
        "weights": {"mission_alignment": 0.25},
        "adjustments": {"mission_alignment": "keep"},
        "confidence": "low",
        "sufficient_data": False,
    }
    data = [_make_outcome_record()]
    path = save_calibration(recs, data)
    assert path.exists()

    with open(path) as f:
        saved = yaml.safe_load(f)
    assert saved["confidence"] == "low"
    assert saved["sample_size"] == 1


def test_load_calibration_returns_none_when_missing(tmp_path, monkeypatch):
    """load_calibration returns None when file doesn't exist."""
    monkeypatch.setattr("outcome_learner.CALIBRATION_FILE", tmp_path / "nonexistent.yaml")
    assert load_calibration() is None


def test_load_calibration_returns_none_when_insufficient(tmp_path, monkeypatch):
    """load_calibration returns None when sufficient_data is False."""
    cal_file = tmp_path / "weight-calibration.yaml"
    cal_file.write_text(yaml.dump({
        "sufficient_data": False,
        "weights": {"mission_alignment": 0.25},
    }))
    monkeypatch.setattr("outcome_learner.CALIBRATION_FILE", cal_file)
    assert load_calibration() is None


def test_load_calibration_returns_data_when_sufficient(tmp_path, monkeypatch):
    """load_calibration returns calibration dict when data is sufficient."""
    cal_file = tmp_path / "weight-calibration.yaml"
    cal_file.write_text(yaml.dump({
        "sufficient_data": True,
        "weights": {"mission_alignment": 0.25},
        "confidence": "moderate",
    }))
    monkeypatch.setattr("outcome_learner.CALIBRATION_FILE", cal_file)
    result = load_calibration()
    assert result is not None
    assert result["sufficient_data"] is True
    assert "weights" in result


# --- cross_reference_hypotheses ---


def test_cross_reference_no_hypotheses(monkeypatch):
    """Returns message when no hypotheses exist."""
    monkeypatch.setattr("outcome_learner.load_hypotheses", lambda: [], raising=False)
    # Import may fail if feedback_capture not available, test the function directly
    data = [_make_outcome_record()]
    analysis = analyze_dimension_accuracy(data)
    result = cross_reference_hypotheses(data, analysis)
    assert "hypothes" in result.lower()


# --- collect_outcome_data ---


def test_collect_outcome_data_returns_list():
    """collect_outcome_data returns a list (may be empty)."""
    data = collect_outcome_data()
    assert isinstance(data, list)
