"""Tests for scripts/check_deferred.py."""

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import check_deferred as deferred_mod


class _FixedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):  # noqa: ARG003
        return cls(2026, 3, 10)


def test_check_deferred_entries_buckets_resume_dates(monkeypatch):
    monkeypatch.setattr(deferred_mod, "datetime", _FixedDateTime)
    entries = [
        {
            "id": "overdue-1",
            "status": "deferred",
            "deferral": {"resume_date": "2026-03-01", "reason": "hiring_pause"},
        },
        {
            "id": "upcoming-1",
            "status": "deferred",
            "deferral": {"resume_date": "2026-03-12", "reason": "portal_closed"},
        },
        {
            "id": "distant-1",
            "status": "deferred",
            "deferral": {"resume_date": "2026-04-10", "reason": "seasonal"},
        },
        {"id": "no-date", "status": "deferred", "deferral": {"reason": "unknown"}},
        {"id": "bad-date", "status": "deferred", "deferral": {"resume_date": "2026-99-99"}},
        {"id": "not-deferred", "status": "qualified", "deferral": {"resume_date": "2026-03-02"}},
    ]

    results = deferred_mod.check_deferred_entries(entries)
    assert [item[0]["id"] for item in results["overdue"]] == ["overdue-1"]
    assert results["overdue"][0][1] == 9
    assert [item[0]["id"] for item in results["upcoming"]] == ["upcoming-1"]
    assert results["upcoming"][0][1] == 2
    assert [item[0]["id"] for item in results["distant"]] == ["distant-1"]
    assert {item["id"] for item in results["no_date"]} == {"no-date", "bad-date"}


def test_format_entry_summary_uses_reason_and_defaults():
    entry = {"id": "entry-1", "name": "Entry One", "deferral": {"reason": "portal_closed"}}
    assert deferred_mod.format_entry_summary(entry) == "Entry One (entry-1) — reason: portal_closed"


def test_check_deferred_entries_empty_list(monkeypatch):
    monkeypatch.setattr(deferred_mod, "datetime", _FixedDateTime)
    results = deferred_mod.check_deferred_entries([])
    assert results["overdue"] == []
    assert results["upcoming"] == []
    assert results["distant"] == []
    assert results["no_date"] == []


def test_check_deferred_no_deferred_entries(monkeypatch):
    monkeypatch.setattr(deferred_mod, "datetime", _FixedDateTime)
    entries = [
        {"id": "active-1", "status": "qualified"},
        {"id": "active-2", "status": "staged"},
    ]
    results = deferred_mod.check_deferred_entries(entries)
    assert results["overdue"] == []
    assert results["upcoming"] == []
    assert results["distant"] == []
    assert results["no_date"] == []


def test_run_check_deferred_report_mode_output(capsys, monkeypatch):
    monkeypatch.setattr(deferred_mod, "datetime", _FixedDateTime)
    monkeypatch.setattr(
        deferred_mod,
        "load_entries",
        lambda **kw: [
            {
                "id": "test-d",
                "name": "Test Deferred",
                "status": "deferred",
                "deferral": {"resume_date": "2026-03-01", "reason": "paused"},
            }
        ],
    )
    deferred_mod.run_check_deferred(alert_mode=False, report_mode=True)
    output = capsys.readouterr().out
    assert "DEFERRED" in output.upper() or "test-d" in output
