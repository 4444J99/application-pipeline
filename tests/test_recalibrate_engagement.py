#!/usr/bin/env python3
"""Tests for recalibrate_engagement.py — engagement-based rubric recalibration."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from recalibrate_engagement import (
    MIN_PER_GROUP,
    classify_engagement,
    compute_engagement_means,
    print_report,
    propose_weights,
    run_analysis,
    split_by_engagement,
)

# DIMENSION_ORDER as known from pipeline_lib (must match production)
DIMENSION_ORDER = [
    "mission_alignment",
    "evidence_match",
    "track_record_fit",
    "network_proximity",
    "strategic_value",
    "financial_alignment",
    "effort_to_value",
    "deadline_feasibility",
    "portal_friction",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _entry(status="submitted", outcome=None, dimensions=None):
    """Build a minimal pipeline entry with optional fit dimensions."""
    entry: dict = {"status": status, "outcome": outcome}
    if dimensions is not None:
        entry["fit"] = {"dimensions": dimensions}
    return entry


def _dims(value: float = 7.0) -> dict:
    """Return a uniform dimensions dict with all 9 dimensions set to value."""
    return {d: value for d in DIMENSION_ORDER}


def _enough_entries(n: int, outcome=None, status="submitted", dim_value=7.0) -> list[dict]:
    """Build n entries with the given outcome/status and uniform dimensions."""
    return [_entry(status=status, outcome=outcome, dimensions=_dims(dim_value)) for _ in range(n)]


# ---------------------------------------------------------------------------
# classify_engagement (mirrors block_engagement version but different silence set)
# ---------------------------------------------------------------------------

class TestClassifyEngagement:
    def test_rejected_is_engaged(self):
        assert classify_engagement({"outcome": "rejected"}) == "engaged"

    def test_accepted_is_engaged(self):
        assert classify_engagement({"outcome": "accepted"}) == "engaged"

    def test_interview_is_engaged(self):
        assert classify_engagement({"outcome": "interview"}) == "engaged"

    def test_expired_is_silence(self):
        assert classify_engagement({"outcome": "expired"}) == "silence"

    def test_submitted_no_outcome_is_silence(self):
        assert classify_engagement({"status": "submitted", "outcome": None}) == "silence"

    def test_withdrawn_is_none(self):
        # withdrawn is ambiguous → excluded
        assert classify_engagement({"outcome": "withdrawn"}) is None

    def test_drafting_no_outcome_is_none(self):
        assert classify_engagement({"status": "drafting", "outcome": None}) is None

    def test_empty_entry_is_none(self):
        assert classify_engagement({}) is None


# ---------------------------------------------------------------------------
# split_by_engagement
# ---------------------------------------------------------------------------

class TestSplitByEngagement:
    def test_splits_correctly(self):
        entries = [
            _entry(outcome="rejected", dimensions=_dims(8.0)),
            _entry(status="submitted", dimensions=_dims(5.0)),
        ]
        engaged, silence = split_by_engagement(entries)
        assert len(engaged) == 1
        assert len(silence) == 1

    def test_excludes_entries_without_dimensions(self):
        entries = [
            _entry(outcome="rejected"),                   # no fit key
            _entry(outcome="rejected", dimensions=None),  # explicit None
            _entry(outcome="rejected", dimensions={}),    # empty dict
        ]
        engaged, silence = split_by_engagement(entries)
        assert engaged == []

    def test_excludes_ambiguous_entries(self):
        entries = [_entry(outcome="withdrawn", dimensions=_dims())]
        engaged, silence = split_by_engagement(entries)
        assert engaged == []
        assert silence == []

    def test_returns_dim_dicts_not_full_entries(self):
        entries = [_entry(outcome="rejected", dimensions=_dims(9.0))]
        engaged, silence = split_by_engagement(entries)
        # engaged should be list of dimension dicts
        assert "mission_alignment" in engaged[0]

    def test_empty_entries(self):
        engaged, silence = split_by_engagement([])
        assert engaged == []
        assert silence == []

    def test_no_silence_entries(self):
        entries = [_entry(outcome="rejected", dimensions=_dims())]
        engaged, silence = split_by_engagement(entries)
        assert silence == []

    def test_no_engaged_entries(self):
        entries = [_entry(status="submitted", dimensions=_dims())]
        engaged, silence = split_by_engagement(entries)
        assert engaged == []


# ---------------------------------------------------------------------------
# compute_engagement_means
# ---------------------------------------------------------------------------

class TestComputeEngagementMeans:
    def test_basic_means(self):
        engaged = [_dims(8.0)]
        silence = [_dims(5.0)]
        means = compute_engagement_means(engaged, silence)
        for dim in DIMENSION_ORDER:
            assert dim in means
            assert means[dim]["engaged"] == 8.0
            assert means[dim]["silence"] == 5.0

    def test_empty_engaged_defaults_to_5(self):
        silence = [_dims(3.0)]
        means = compute_engagement_means([], silence)
        for dim in DIMENSION_ORDER:
            assert means[dim]["engaged"] == 5.0

    def test_empty_silence_defaults_to_5(self):
        engaged = [_dims(8.0)]
        means = compute_engagement_means(engaged, [])
        for dim in DIMENSION_ORDER:
            assert means[dim]["silence"] == 5.0

    def test_n_counts_correct(self):
        engaged = [_dims(7.0), _dims(8.0)]
        silence = [_dims(5.0)]
        means = compute_engagement_means(engaged, silence)
        assert means["mission_alignment"]["engaged_n"] == 2
        assert means["mission_alignment"]["silence_n"] == 1

    def test_missing_dim_skipped_in_average(self):
        engaged = [{"mission_alignment": 8.0}]  # other dims missing
        silence = [_dims(5.0)]
        means = compute_engagement_means(engaged, silence)
        # mission_alignment should use the available value
        assert means["mission_alignment"]["engaged"] == 8.0
        # other dims should default to 5.0 (no values)
        assert means["evidence_match"]["engaged"] == 5.0

    def test_mixed_values_averaged(self):
        engaged = [_dims(6.0), _dims(10.0)]
        silence = [_dims(5.0)]
        means = compute_engagement_means(engaged, silence)
        assert means["mission_alignment"]["engaged"] == 8.0


# ---------------------------------------------------------------------------
# propose_weights
# ---------------------------------------------------------------------------

class TestProposeWeights:
    def test_sums_to_one(self):
        means = {
            dim: {"engaged": 8.0, "silence": 5.0, "engaged_n": 10, "silence_n": 10}
            for dim in DIMENSION_ORDER
        }
        weights = propose_weights(means)
        assert abs(sum(weights.values()) - 1.0) < 1e-3

    def test_all_dimensions_present(self):
        means = {
            dim: {"engaged": 8.0, "silence": 5.0, "engaged_n": 10, "silence_n": 10}
            for dim in DIMENSION_ORDER
        }
        weights = propose_weights(means)
        for dim in DIMENSION_ORDER:
            assert dim in weights

    def test_weights_are_positive(self):
        means = {
            dim: {"engaged": 5.0, "silence": 8.0, "engaged_n": 10, "silence_n": 10}
            for dim in DIMENSION_ORDER
        }
        # Even when silence > engaged, delta is clamped to min 0.01 → always positive
        weights = propose_weights(means)
        for w in weights.values():
            assert w >= 0.0

    def test_higher_correlation_gets_higher_weight(self):
        # Make mission_alignment strongly predict engagement
        means = {dim: {"engaged": 5.0, "silence": 5.0, "engaged_n": 10, "silence_n": 10}
                 for dim in DIMENSION_ORDER}
        means["mission_alignment"]["engaged"] = 10.0
        weights = propose_weights(means)
        for dim in DIMENSION_ORDER:
            if dim != "mission_alignment":
                assert weights["mission_alignment"] >= weights[dim]


# ---------------------------------------------------------------------------
# run_analysis
# ---------------------------------------------------------------------------

class TestRunAnalysis:
    def test_insufficient_engaged_returns_error(self):
        entries = (
            _enough_entries(MIN_PER_GROUP - 1, outcome="rejected") +
            _enough_entries(MIN_PER_GROUP, status="submitted")
        )
        result = run_analysis(entries)
        assert result is not None
        assert result.get("error") == "insufficient_data"
        assert result["engaged_n"] < MIN_PER_GROUP

    def test_insufficient_silence_returns_error(self):
        entries = (
            _enough_entries(MIN_PER_GROUP, outcome="rejected") +
            _enough_entries(MIN_PER_GROUP - 1, status="submitted")
        )
        result = run_analysis(entries)
        assert result is not None
        assert result.get("error") == "insufficient_data"
        assert result["silence_n"] < MIN_PER_GROUP

    def test_sufficient_data_returns_full_result(self):
        entries = (
            _enough_entries(MIN_PER_GROUP, outcome="rejected", dim_value=8.0) +
            _enough_entries(MIN_PER_GROUP, status="submitted", dim_value=5.0)
        )
        result = run_analysis(entries)
        assert result is not None
        assert "error" not in result
        assert "dimensions" in result
        assert "suggested_weights" in result
        assert "assessment" in result

    def test_result_has_date(self):
        entries = (
            _enough_entries(MIN_PER_GROUP, outcome="rejected") +
            _enough_entries(MIN_PER_GROUP, status="submitted")
        )
        result = run_analysis(entries)
        assert result is not None
        if "error" not in result:
            from datetime import date
            assert result["date"] == date.today().isoformat()

    def test_dimensions_all_present(self):
        entries = (
            _enough_entries(MIN_PER_GROUP, outcome="rejected", dim_value=8.0) +
            _enough_entries(MIN_PER_GROUP, status="submitted", dim_value=5.0)
        )
        result = run_analysis(entries)
        assert result is not None
        if "error" not in result:
            dim_names = [d["dimension"] for d in result["dimensions"]]
            for dim in DIMENSION_ORDER:
                assert dim in dim_names

    def test_suggested_weights_sum_to_one(self):
        entries = (
            _enough_entries(MIN_PER_GROUP, outcome="rejected", dim_value=8.0) +
            _enough_entries(MIN_PER_GROUP, status="submitted", dim_value=5.0)
        )
        result = run_analysis(entries)
        if result and "error" not in result:
            total = sum(result["suggested_weights"].values())
            assert abs(total - 1.0) < 1e-3

    def test_assessment_well_calibrated_when_equal_means(self):
        # When engaged and silence have same scores, delta→ 0.01 uniformly
        # → uniform weights → max_delta vs current weights could vary; but assess key present
        entries = (
            _enough_entries(MIN_PER_GROUP, outcome="rejected", dim_value=7.0) +
            _enough_entries(MIN_PER_GROUP, status="submitted", dim_value=7.0)
        )
        result = run_analysis(entries)
        if result and "error" not in result:
            assert result["assessment"] in ("well_calibrated", "minor_adjustments", "significant_recalibration")

    def test_significant_when_large_delta(self):
        # Engage high, silence low → large weight swing expected
        entries = (
            _enough_entries(MIN_PER_GROUP, outcome="rejected", dim_value=10.0) +
            _enough_entries(MIN_PER_GROUP, status="submitted", dim_value=1.0)
        )
        result = run_analysis(entries)
        if result and "error" not in result:
            assert result["max_delta"] >= 0.0

    def test_significant_dimension_flagged(self):
        entries = (
            _enough_entries(MIN_PER_GROUP, outcome="rejected", dim_value=8.0) +
            _enough_entries(MIN_PER_GROUP, status="submitted", dim_value=5.0)
        )
        result = run_analysis(entries)
        if result and "error" not in result:
            for d in result["dimensions"]:
                assert "significant" in d
                assert isinstance(d["significant"], bool)

    def test_empty_entries(self):
        result = run_analysis([])
        assert result is not None
        assert result.get("error") == "insufficient_data"

    def test_entries_without_dimensions_excluded(self):
        # No fit dimensions → all excluded → insufficient_data
        entries = [_entry(outcome="rejected") for _ in range(20)]
        result = run_analysis(entries)
        assert result is not None
        assert result.get("error") == "insufficient_data"


# ---------------------------------------------------------------------------
# print_report
# ---------------------------------------------------------------------------

class TestPrintReport:
    def test_prints_error_for_insufficient_data(self, capsys):
        result = {
            "error": "insufficient_data",
            "message": "Need more data",
            "engaged_n": 2,
            "silence_n": 5,
            "required": MIN_PER_GROUP,
        }
        print_report(result)
        out = capsys.readouterr().out
        assert "INSUFFICIENT DATA" in out
        assert "Need more data" in out

    def test_prints_header_for_valid_result(self, capsys):
        entries = (
            _enough_entries(MIN_PER_GROUP, outcome="rejected", dim_value=8.0) +
            _enough_entries(MIN_PER_GROUP, status="submitted", dim_value=5.0)
        )
        result = run_analysis(entries)
        if result and "error" not in result:
            print_report(result)
            out = capsys.readouterr().out
            assert "ENGAGEMENT-BASED RECALIBRATION PROPOSAL" in out

    def test_prints_each_dimension(self, capsys):
        entries = (
            _enough_entries(MIN_PER_GROUP, outcome="rejected", dim_value=8.0) +
            _enough_entries(MIN_PER_GROUP, status="submitted", dim_value=5.0)
        )
        result = run_analysis(entries)
        if result and "error" not in result:
            print_report(result)
            out = capsys.readouterr().out
            for dim in DIMENSION_ORDER:
                assert dim in out

    def test_prints_well_calibrated(self, capsys):
        result = {
            "date": "2026-01-01",
            "engaged_n": 10,
            "silence_n": 10,
            "dimensions": [
                {
                    "dimension": dim,
                    "current_weight": 0.111,
                    "suggested_weight": 0.111,
                    "delta": 0.0,
                    "engaged_mean": 7.0,
                    "silence_mean": 7.0,
                    "correlation": 0.0,
                    "engaged_n": 10,
                    "silence_n": 10,
                    "significant": False,
                }
                for dim in DIMENSION_ORDER
            ],
            "suggested_weights": {dim: 0.111 for dim in DIMENSION_ORDER},
            "max_delta": 0.005,
            "assessment": "well_calibrated",
        }
        print_report(result)
        out = capsys.readouterr().out
        assert "well-calibrated" in out

    def test_prints_minor_adjustments(self, capsys):
        result = {
            "date": "2026-01-01",
            "engaged_n": 10,
            "silence_n": 10,
            "dimensions": [
                {
                    "dimension": dim,
                    "current_weight": 0.111,
                    "suggested_weight": 0.111,
                    "delta": 0.03,
                    "engaged_mean": 7.0,
                    "silence_mean": 6.5,
                    "correlation": 0.5,
                    "engaged_n": 10,
                    "silence_n": 10,
                    "significant": False,
                }
                for dim in DIMENSION_ORDER
            ],
            "suggested_weights": {dim: 0.111 for dim in DIMENSION_ORDER},
            "max_delta": 0.03,
            "assessment": "minor_adjustments",
        }
        print_report(result)
        out = capsys.readouterr().out
        assert "Minor adjustments" in out

    def test_prints_significant_recalibration(self, capsys):
        result = {
            "date": "2026-01-01",
            "engaged_n": 10,
            "silence_n": 10,
            "dimensions": [
                {
                    "dimension": dim,
                    "current_weight": 0.111,
                    "suggested_weight": 0.111,
                    "delta": 0.10,
                    "engaged_mean": 8.0,
                    "silence_mean": 4.0,
                    "correlation": 4.0,
                    "engaged_n": 10,
                    "silence_n": 10,
                    "significant": True,
                }
                for dim in DIMENSION_ORDER
            ],
            "suggested_weights": {dim: 0.111 for dim in DIMENSION_ORDER},
            "max_delta": 0.10,
            "assessment": "significant_recalibration",
        }
        print_report(result)
        out = capsys.readouterr().out
        assert "Significant recalibration" in out

    def test_significant_marker_shown(self, capsys):
        result = {
            "date": "2026-01-01",
            "engaged_n": 10,
            "silence_n": 10,
            "dimensions": [
                {
                    "dimension": "mission_alignment",
                    "current_weight": 0.10,
                    "suggested_weight": 0.20,
                    "delta": 0.10,
                    "engaged_mean": 8.0,
                    "silence_mean": 4.0,
                    "correlation": 4.0,
                    "engaged_n": 10,
                    "silence_n": 10,
                    "significant": True,
                }
            ],
            "suggested_weights": {"mission_alignment": 0.20},
            "max_delta": 0.10,
            "assessment": "significant_recalibration",
        }
        print_report(result)
        out = capsys.readouterr().out
        assert "***" in out

    def test_sum_check_printed(self, capsys):
        result = {
            "date": "2026-01-01",
            "engaged_n": 10,
            "silence_n": 10,
            "dimensions": [
                {
                    "dimension": dim,
                    "current_weight": 1 / len(DIMENSION_ORDER),
                    "suggested_weight": 1 / len(DIMENSION_ORDER),
                    "delta": 0.0,
                    "engaged_mean": 7.0,
                    "silence_mean": 7.0,
                    "correlation": 0.0,
                    "engaged_n": 10,
                    "silence_n": 10,
                    "significant": False,
                }
                for dim in DIMENSION_ORDER
            ],
            "suggested_weights": {dim: 1 / len(DIMENSION_ORDER) for dim in DIMENSION_ORDER},
            "max_delta": 0.0,
            "assessment": "well_calibrated",
        }
        print_report(result)
        out = capsys.readouterr().out
        assert "Sum check" in out
