"""Tests for scripts/standup_work_sections.py."""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from standup_work_sections import (
    compute_staged_submit_conversion,
    entry_has_portal_fields,
    section_execution_gap,
    section_health,
)


def _entry(
    *,
    status: str,
    name: str = "Entry",
    submitted_days_ago: int | None = None,
    last_touched_days_ago: int | None = None,
    with_portal: bool = False,
    score: float = 7.0,
) -> dict:
    data = {
        "id": name.lower().replace(" ", "-"),
        "name": name,
        "status": status,
        "fit": {"score": score},
        "timeline": {},
    }
    if submitted_days_ago is not None:
        data["timeline"]["submitted"] = (date.today() - timedelta(days=submitted_days_ago)).isoformat()
    if last_touched_days_ago is not None:
        data["last_touched"] = (date.today() - timedelta(days=last_touched_days_ago)).isoformat()
    if with_portal:
        data["portal_fields"] = {"fields": [{"name": "email"}]}
    return data


def _parse_date(value: str):
    return date.fromisoformat(value)


def test_section_health_basic():
    result = section_health(
        [
            _entry(status="research"),
            _entry(status="submitted", submitted_days_ago=2),
        ],
        actionable_statuses={"research", "qualified", "drafting", "staged"},
        parse_date_fn=_parse_date,
    )
    assert result["total"] == 2
    assert result["submitted"] == 1


def test_execution_helpers_and_conversion(capsys):
    assert entry_has_portal_fields({"portal_fields": {"fields": [{"name": "x"}]}}) is True
    num, den, rate = compute_staged_submit_conversion(
        [_entry(status="staged"), _entry(status="submitted")]
    )
    assert (num, den, round(rate, 2)) == (1, 2, 0.5)

    result = section_execution_gap(
        [
            _entry(status="staged", name="Stale", last_touched_days_ago=10, with_portal=False),
            _entry(status="staged", name="Fresh", last_touched_days_ago=1, with_portal=True),
            _entry(status="submitted", name="Submitted", submitted_days_ago=1),
        ],
        parse_date_fn=_parse_date,
        get_score_fn=lambda e: float(e.get("fit", {}).get("score", 0)),
        target_staged_submit_conversion=0.5,
        execution_stale_staged_days=7,
        load_recent_agent_runs_fn=lambda days=7: [],
    )
    output = capsys.readouterr().out
    assert "EXECUTION GAP SNAPSHOT" in output
    assert result["staged"] == 2
