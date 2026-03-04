"""Tests for scripts/standup_pipeline_sections.py."""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from standup_pipeline_sections import (
    _freshness_badge,
    section_job_freshness,
    section_jobs,
    section_opportunities,
)


def _entry(
    *,
    entry_id: str,
    name: str,
    track: str = "job",
    status: str = "qualified",
    score: float = 7.0,
    deadline_days: int | None = None,
    posting_hours_ago: int | None = None,
) -> dict:
    entry = {
        "id": entry_id,
        "name": name,
        "track": track,
        "status": status,
        "fit": {"score": score},
        "target": {"portal": "greenhouse"},
        "submission": {"effort_level": "quick"},
        "timeline": {},
    }
    if deadline_days is not None:
        entry["deadline"] = {
            "date": (date.today() + timedelta(days=deadline_days)).isoformat(),
            "type": "hard",
        }
    if posting_hours_ago is not None:
        entry["target"]["posting_date"] = (
            date.today() - timedelta(days=max(posting_hours_ago // 24, 0))
        ).isoformat()
    return entry


def test_freshness_badge_non_job_is_empty():
    assert _freshness_badge(_entry(entry_id="g1", name="Grant", track="grant")) == ""


def test_section_jobs_prints_pipeline(capsys):
    entries = [
        _entry(entry_id="j1", name="Role A", track="job", status="qualified", score=8.0),
        _entry(entry_id="j2", name="Role B", track="job", status="submitted", score=6.4),
    ]
    section_jobs(entries)
    output = capsys.readouterr().out
    assert "JOB PIPELINE" in output
    assert "Role A" in output
    assert "Total job entries: 2" in output


def test_section_job_freshness_empty(capsys):
    section_job_freshness([_entry(entry_id="g1", name="Grant", track="grant")])
    output = capsys.readouterr().out
    assert "JOB FRESHNESS" in output
    assert "No actionable job entries" in output


def test_section_opportunities_prints_items(capsys):
    entries = [
        _entry(
            entry_id="o1",
            name="Grant A",
            track="grant",
            status="qualified",
            score=8.3,
            deadline_days=5,
        ),
    ]
    section_opportunities(entries)
    output = capsys.readouterr().out
    assert "OPPORTUNITY PIPELINE" in output
    assert "Grant A" in output
