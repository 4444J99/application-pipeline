"""Tests for scripts/standup_relationship_sections.py."""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from standup_relationship_sections import section_followup, section_relationships


def _entry(*, status: str, submitted_days_ago: int | None = None, follow_up=None) -> dict:
    data = {
        "id": "entry-1",
        "name": "Entry 1",
        "status": status,
        "target": {"organization": "Org X"},
        "timeline": {},
    }
    if submitted_days_ago is not None:
        data["timeline"]["submitted"] = (date.today() - timedelta(days=submitted_days_ago)).isoformat()
    if follow_up is not None:
        data["follow_up"] = follow_up
    return data


def test_section_followup_no_submitted(capsys):
    section_followup([_entry(status="research")], parse_date_fn=date.fromisoformat)
    output = capsys.readouterr().out
    assert "FOLLOW-UP DASHBOARD" in output
    assert "No submitted entries" in output


def test_section_followup_overdue(capsys):
    section_followup([_entry(status="submitted", submitted_days_ago=30, follow_up=[])], parse_date_fn=date.fromisoformat)
    output = capsys.readouterr().out
    assert "OVERDUE" in output


def test_section_relationships_smoke(capsys):
    section_relationships([])
    output = capsys.readouterr().out
    assert "RELATIONSHIPS" in output
