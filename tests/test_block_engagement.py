#!/usr/bin/env python3
"""Tests for block_engagement.py — block-engagement correlation analysis."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from block_engagement import (
    _get_blocks_used,
    classify_blocks,
    classify_engagement,
    compute_block_engagement_tabs,
    format_report,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _entry(
    status="submitted",
    outcome=None,
    blocks=None,
    track="job",
):
    """Build a minimal pipeline entry dict."""
    return {
        "status": status,
        "outcome": outcome,
        "track": track,
        "submission": {"blocks_used": blocks or {}},
    }


# ---------------------------------------------------------------------------
# classify_engagement
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
        e = {"status": "submitted", "outcome": None}
        assert classify_engagement(e) == "silence"

    def test_withdrawn_is_none(self):
        assert classify_engagement({"outcome": "withdrawn"}) is None

    def test_drafting_no_outcome_is_none(self):
        e = {"status": "drafting", "outcome": None}
        assert classify_engagement(e) is None

    def test_qualified_no_outcome_is_none(self):
        e = {"status": "qualified", "outcome": None}
        assert classify_engagement(e) is None

    def test_empty_entry_is_none(self):
        assert classify_engagement({}) is None

    def test_missing_status_with_null_outcome_is_none(self):
        # No status key, no outcome → falls through to None
        assert classify_engagement({"outcome": None}) is None


# ---------------------------------------------------------------------------
# _get_blocks_used
# ---------------------------------------------------------------------------

class TestGetBlocksUsed:
    def test_dict_blocks(self):
        entry = {"submission": {"blocks_used": {"intro": "identity/2min", "body": "projects/organvm"}}}
        result = _get_blocks_used(entry)
        assert set(result) == {"identity/2min", "projects/organvm"}

    def test_list_blocks(self):
        entry = {"submission": {"blocks_used": ["identity/2min", "projects/organvm"]}}
        result = _get_blocks_used(entry)
        assert result == ["identity/2min", "projects/organvm"]

    def test_missing_submission(self):
        assert _get_blocks_used({}) == []

    def test_missing_blocks_used(self):
        assert _get_blocks_used({"submission": {}}) == []

    def test_none_submission(self):
        assert _get_blocks_used({"submission": None}) == []

    def test_empty_dict_blocks(self):
        assert _get_blocks_used({"submission": {"blocks_used": {}}}) == []

    def test_empty_list_blocks(self):
        assert _get_blocks_used({"submission": {"blocks_used": []}}) == []

    def test_non_dict_submission(self):
        assert _get_blocks_used({"submission": "bad"}) == []


# ---------------------------------------------------------------------------
# compute_block_engagement_tabs
# ---------------------------------------------------------------------------

class TestComputeBlockEngagementTabs:
    def test_empty_entries(self):
        assert compute_block_engagement_tabs([]) == {}

    def test_basic_engaged_silence(self):
        entries = [
            _entry(outcome="accepted", blocks={"a": "block/alpha"}),
            _entry(outcome="rejected", blocks={"a": "block/alpha"}),
            _entry(status="submitted", blocks={"a": "block/alpha"}),
        ]
        tabs = compute_block_engagement_tabs(entries)
        assert "block/alpha" in tabs
        t = tabs["block/alpha"]
        assert t["engaged"] == 2
        assert t["silence"] == 1
        assert t["total"] == 3
        assert round(t["engagement_rate"], 3) == round(2 / 3, 3)
        assert round(t["silence_rate"], 3) == round(1 / 3, 3)

    def test_excludes_none_signal(self):
        # withdrawn/drafting entries should not appear in tabs
        entries = [
            _entry(outcome="withdrawn", blocks={"a": "block/beta"}),
            _entry(status="drafting", blocks={"a": "block/beta"}),
        ]
        tabs = compute_block_engagement_tabs(entries)
        assert tabs == {}

    def test_multiple_blocks_per_entry(self):
        entry = _entry(outcome="rejected", blocks={"a": "block/x", "b": "block/y"})
        tabs = compute_block_engagement_tabs([entry])
        assert "block/x" in tabs
        assert "block/y" in tabs
        assert tabs["block/x"]["engaged"] == 1
        assert tabs["block/y"]["engaged"] == 1

    def test_list_blocks_counted(self):
        entry = {
            "status": "submitted",
            "outcome": "rejected",
            "track": "job",
            "submission": {"blocks_used": ["block/list-a", "block/list-b"]},
        }
        tabs = compute_block_engagement_tabs([entry])
        assert "block/list-a" in tabs
        assert "block/list-b" in tabs

    def test_rates_sum_to_one(self):
        entries = [
            _entry(outcome="accepted", blocks={"a": "block/z"}),
            _entry(outcome="expired", blocks={"a": "block/z"}),
        ]
        tabs = compute_block_engagement_tabs(entries)
        t = tabs["block/z"]
        assert abs(t["engagement_rate"] + t["silence_rate"] - 1.0) < 1e-6

    def test_entry_with_no_blocks_skipped(self):
        entries = [
            _entry(outcome="accepted", blocks={}),
        ]
        tabs = compute_block_engagement_tabs(entries)
        assert tabs == {}


# ---------------------------------------------------------------------------
# classify_blocks
# ---------------------------------------------------------------------------

class TestClassifyBlocks:
    def _make_tabs(self, engaged, silence):
        total = engaged + silence
        return {
            "engaged": engaged,
            "silence": silence,
            "total": total,
            "engagement_rate": engaged / total if total > 0 else 0.0,
            "silence_rate": silence / total if total > 0 else 0.0,
        }

    def test_effective_classification(self):
        # > 60% engagement with >= 3 uses
        tabs = {"block/effective": self._make_tabs(3, 0)}
        result = classify_blocks(tabs)
        assert len(result["effective"]) == 1
        assert result["effective"][0]["block"] == "block/effective"
        assert result["effective"][0]["category"] == "effective"

    def test_invisible_classification(self):
        # > 80% silence with >= 3 uses
        tabs = {"block/invisible": self._make_tabs(0, 5)}
        result = classify_blocks(tabs)
        assert len(result["invisible"]) == 1
        assert result["invisible"][0]["category"] == "invisible"

    def test_insufficient_when_too_few_uses(self):
        # Only 2 resolved uses — below MIN_USES_FOR_CLASSIFICATION=3
        tabs = {"block/small": self._make_tabs(1, 1)}
        result = classify_blocks(tabs)
        assert len(result["insufficient"]) == 1
        assert result["insufficient"][0]["category"] == "insufficient"

    def test_mixed_classification(self):
        # 50% engagement / 50% silence with >= 3 uses → mixed (goes to insufficient)
        tabs = {"block/mixed": self._make_tabs(2, 2)}
        result = classify_blocks(tabs)
        assert any(b["category"] == "mixed" for b in result["insufficient"])

    def test_empty_tabs(self):
        result = classify_blocks({})
        assert result == {"effective": [], "invisible": [], "insufficient": []}

    def test_multiple_blocks_sorted_by_rate(self):
        tabs = {
            "block/hi": self._make_tabs(9, 1),   # 90% engagement
            "block/med": self._make_tabs(7, 3),   # 70% engagement
        }
        result = classify_blocks(tabs)
        rates = [b["engagement_rate"] for b in result["effective"]]
        assert rates == sorted(rates, reverse=True)

    def test_custom_thresholds(self):
        # With lower effective threshold, block/mid becomes effective
        tabs = {"block/mid": self._make_tabs(3, 3)}
        result = classify_blocks(tabs, min_uses=3, effective_threshold=0.40)
        # 50% engagement > 40% threshold → effective
        assert len(result["effective"]) == 1

    def test_reason_field_in_insufficient(self):
        tabs = {"block/new": self._make_tabs(1, 0)}
        result = classify_blocks(tabs)
        item = result["insufficient"][0]
        assert "reason" in item


# ---------------------------------------------------------------------------
# format_report
# ---------------------------------------------------------------------------

class TestFormatReport:
    def _make_classified(self):
        return {"effective": [], "invisible": [], "insufficient": []}

    def _make_tabs(self, engaged=5, silence=3):
        total = engaged + silence
        return {
            "block/x": {
                "engaged": engaged,
                "silence": silence,
                "total": total,
                "engagement_rate": engaged / total,
                "silence_rate": silence / total,
            }
        }

    def test_header_present(self):
        classified = self._make_classified()
        report = format_report(classified, self._make_tabs())
        assert "Block-Engagement Correlation Report" in report

    def test_signal_pool_shown(self):
        classified = self._make_classified()
        report = format_report(classified, self._make_tabs(engaged=5, silence=3))
        assert "Signal pool:" in report
        assert "8 resolved" in report

    def test_data_notice_when_small_pool(self):
        classified = self._make_classified()
        tabs = {"block/x": {"engaged": 1, "silence": 1, "total": 2,
                             "engagement_rate": 0.5, "silence_rate": 0.5}}
        report = format_report(classified, tabs)
        assert "DATA NOTICE" in report

    def test_no_data_notice_when_enough(self):
        classified = self._make_classified()
        # 15+ resolved → no notice
        tabs = {"block/x": {"engaged": 10, "silence": 5, "total": 15,
                             "engagement_rate": 0.67, "silence_rate": 0.33}}
        report = format_report(classified, tabs)
        assert "DATA NOTICE" not in report

    def test_effective_none_message(self):
        classified = self._make_classified()
        report = format_report(classified, self._make_tabs())
        assert "none yet" in report

    def test_invisible_none_message(self):
        classified = self._make_classified()
        report = format_report(classified, self._make_tabs())
        assert "none detected" in report

    def test_effective_blocks_listed(self):
        classified = {
            "effective": [{"block": "block/good", "engagement_rate": 0.9, "engaged": 9, "silence": 1, "total": 10, "category": "effective"}],
            "invisible": [],
            "insufficient": [],
        }
        tabs = {"block/good": {"engaged": 9, "silence": 1, "total": 10, "engagement_rate": 0.9, "silence_rate": 0.1}}
        report = format_report(classified, tabs)
        assert "block/good" in report

    def test_insufficient_truncated_at_10(self):
        items = [
            {"block": f"block/{i}", "total": 1, "engaged": 0, "silence": 0,
             "engagement_rate": 0.0, "silence_rate": 0.0, "category": "insufficient", "reason": "only 0/3"}
            for i in range(15)
        ]
        classified = {"effective": [], "invisible": [], "insufficient": items}
        tabs = {f"block/{i}": {"engaged": 0, "silence": 0, "total": 0, "engagement_rate": 0.0, "silence_rate": 0.0}
                for i in range(15)}
        report = format_report(classified, tabs)
        assert "and 5 more" in report

    def test_interpretation_footer(self):
        classified = self._make_classified()
        report = format_report(classified, self._make_tabs())
        assert "INTERPRETATION" in report


# ---------------------------------------------------------------------------
# Integration: full pipeline from entries → report
# ---------------------------------------------------------------------------

class TestFullPipeline:
    def test_effective_block_emerges(self):
        entries = [
            _entry(outcome="accepted", blocks={"a": "block/winner"}),
            _entry(outcome="rejected", blocks={"a": "block/winner"}),
            _entry(outcome="interview", blocks={"a": "block/winner"}),
            _entry(outcome="rejected", blocks={"a": "block/winner"}),
        ]
        tabs = compute_block_engagement_tabs(entries)
        classified = classify_blocks(tabs)
        assert any(b["block"] == "block/winner" for b in classified["effective"])

    def test_invisible_block_emerges(self):
        entries = [
            _entry(outcome="expired", blocks={"a": "block/ghost"}),
            _entry(status="submitted", blocks={"a": "block/ghost"}),
            _entry(status="submitted", blocks={"a": "block/ghost"}),
            _entry(status="submitted", blocks={"a": "block/ghost"}),
            _entry(status="submitted", blocks={"a": "block/ghost"}),
        ]
        tabs = compute_block_engagement_tabs(entries)
        classified = classify_blocks(tabs)
        assert any(b["block"] == "block/ghost" for b in classified["invisible"])

    def test_zero_entries_produces_empty_tabs(self):
        tabs = compute_block_engagement_tabs([])
        assert tabs == {}

    def test_no_blocks_in_engaged_entries(self):
        entries = [
            _entry(outcome="accepted"),
            _entry(outcome="rejected"),
        ]
        tabs = compute_block_engagement_tabs(entries)
        assert tabs == {}
