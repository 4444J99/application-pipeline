"""Tests for scripts/pipeline_entry_state.py."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from pipeline_entry_state import (
    can_advance,
    days_until,
    format_amount,
    get_deadline,
    get_effort,
    get_score,
    is_actionable,
    is_deferred,
    parse_date,
    parse_datetime,
)


def test_parse_date_and_parse_datetime():
    assert parse_date("2026-03-04") == date(2026, 3, 4)
    assert parse_datetime("2026-03-04").date() == date(2026, 3, 4)


def test_format_amount_and_deadline_helpers():
    assert format_amount({"value": 1234, "currency": "USD"}) == "$1,234"
    deadline_date, deadline_type = get_deadline({"deadline": {"date": "2026-03-10", "type": "hard"}})
    assert deadline_date == date(2026, 3, 10)
    assert deadline_type == "hard"


def test_effort_and_score_helpers():
    assert get_effort({"submission": {"effort_level": "deep"}}) == "deep"
    assert get_effort({}) == "standard"
    assert get_score({"fit": {"score": 8.2}}) == 8.2
    assert get_score({}) == 0.0


def test_state_helpers_and_days_until():
    entry = {"id": "x", "status": "research"}
    assert is_actionable(entry) is True
    assert is_deferred({"status": "deferred", "deferral": {"reason": "portal_closed"}}) is True
    can, reason = can_advance(entry, "qualified")
    assert can is True and "can advance" in reason
    assert days_until(date.today()) == 0
