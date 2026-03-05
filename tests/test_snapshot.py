#!/usr/bin/env python3
"""Tests for snapshot.py — daily pipeline snapshots and trend tracking."""

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from snapshot import (
    capture_snapshot,
    compute_deltas,
    compute_slope,
    compute_trends,
    detect_inflections,
    load_snapshot,
    save_snapshot,
)


def _entry(entry_id, status="qualified", score=8.0, org="Acme", last_touched=None):
    e = {
        "id": entry_id,
        "status": status,
        "fit": {"score": score},
        "target": {"organization": org},
    }
    if last_touched:
        e["last_touched"] = last_touched
    return e


class TestCaptureSnapshot:
    def test_basic_capture(self):
        entries = [
            _entry("a", status="qualified", score=9.5),
            _entry("b", status="staged", score=7.0),
            _entry("c", status="submitted", score=8.0),
        ]
        snap = capture_snapshot(entries)
        assert snap["total_entries"] == 3
        assert snap["actionable_count"] == 2  # qualified + staged
        assert snap["date"] == str(date.today())
        assert "status_distribution" in snap

    def test_avg_score(self):
        entries = [_entry("a", score=8.0), _entry("b", score=10.0)]
        snap = capture_snapshot(entries)
        assert snap["avg_score"] == 9.0

    def test_scores_above_9(self):
        entries = [_entry("a", score=9.5), _entry("b", score=8.5), _entry("c", score=9.0)]
        snap = capture_snapshot(entries)
        assert snap["scores_above_9"] == 2

    def test_empty_entries(self):
        snap = capture_snapshot([])
        assert snap["total_entries"] == 0
        assert snap["avg_score"] == 0.0

    def test_stale_count(self):
        old_date = str(date.today() - timedelta(days=20))
        entries = [_entry("stale", last_touched=old_date)]
        snap = capture_snapshot(entries)
        assert snap["stale_count"] == 1


class TestSaveLoadSnapshot:
    def test_save_and_load(self, tmp_path, monkeypatch):
        import snapshot as snap_mod
        monkeypatch.setattr(snap_mod, "SNAPSHOTS_DIR", tmp_path)
        data = {"date": "2026-03-05", "total_entries": 10}
        path = save_snapshot(data)
        assert path.exists()
        loaded = load_snapshot("2026-03-05")
        assert loaded["total_entries"] == 10

    def test_load_missing(self, tmp_path, monkeypatch):
        import snapshot as snap_mod
        monkeypatch.setattr(snap_mod, "SNAPSHOTS_DIR", tmp_path)
        assert load_snapshot("1999-01-01") is None


class TestComputeDeltas:
    def test_positive_delta(self):
        current = {"total_entries": 15, "actionable_count": 5, "stale_count": 2,
                    "avg_score": 8.5, "org_cap_violations": 1, "scores_above_9": 3}
        previous = {"total_entries": 10, "actionable_count": 3, "stale_count": 4,
                     "avg_score": 8.0, "org_cap_violations": 2, "scores_above_9": 1}
        deltas = compute_deltas(current, previous)
        assert deltas["total_entries"] == 5
        assert deltas["stale_count"] == -2


class TestComputeSlope:
    def test_increasing(self):
        assert compute_slope([1, 2, 3, 4, 5]) > 0

    def test_decreasing(self):
        assert compute_slope([5, 4, 3, 2, 1]) < 0

    def test_flat(self):
        assert compute_slope([3, 3, 3, 3]) == 0.0

    def test_single_value(self):
        assert compute_slope([5]) == 0.0


class TestDetectInflections:
    def test_peak_detected(self):
        snapshots = [{"val": 1}, {"val": 5}, {"val": 2}]
        inflections = detect_inflections(snapshots, "val")
        assert len(inflections) == 1
        assert "peak" in inflections[0]

    def test_trough_detected(self):
        snapshots = [{"val": 5}, {"val": 1}, {"val": 5}]
        inflections = detect_inflections(snapshots, "val")
        assert len(inflections) == 1
        assert "trough" in inflections[0]

    def test_no_inflection(self):
        snapshots = [{"val": 1}, {"val": 2}, {"val": 3}]
        inflections = detect_inflections(snapshots, "val")
        assert inflections == []


class TestComputeTrends:
    def test_empty_snapshots(self):
        result = compute_trends([])
        assert "error" in result

    def test_with_snapshots(self):
        today = date.today()
        snapshots = [
            {"date": str(today - timedelta(days=1)), "total_entries": 10,
             "actionable_count": 5, "stale_count": 2, "avg_score": 8.0,
             "org_cap_violations": 1, "scores_above_9": 2},
            {"date": str(today), "total_entries": 12,
             "actionable_count": 6, "stale_count": 1, "avg_score": 8.5,
             "org_cap_violations": 0, "scores_above_9": 3},
        ]
        result = compute_trends(snapshots)
        assert "current" in result
        assert "windows" in result
