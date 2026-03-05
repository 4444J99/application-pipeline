#!/usr/bin/env python3
"""Tests for calendar_export.py — iCal generation from pipeline deadlines."""

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from calendar_export import (
    generate_calendar,
    generate_event_list,
    generate_vevent,
)


def _entry(entry_id, deadline_date=None, status="staged", score=8.0, follow_up=None):
    e = {
        "id": entry_id,
        "name": f"Test {entry_id}",
        "status": status,
        "fit": {"score": score},
        "deadline": {},
    }
    if deadline_date:
        e["deadline"] = {"date": str(deadline_date), "type": "hard"}
    if follow_up:
        e["follow_up"] = follow_up
    return e


class TestGenerateVevent:
    def test_basic_event(self):
        event = generate_vevent(
            uid="test-123",
            summary="Test Event",
            dtstart=date(2026, 4, 15),
            description="A test",
        )
        assert "BEGIN:VEVENT" in event
        assert "END:VEVENT" in event
        assert "UID:test-123" in event
        assert "SUMMARY:Test Event" in event
        assert "20260415" in event

    def test_default_alarms(self):
        event = generate_vevent(uid="x", summary="X", dtstart=date(2026, 4, 15))
        assert "TRIGGER:-P7D" in event
        assert "TRIGGER:-P1D" in event

    def test_custom_alarms(self):
        event = generate_vevent(uid="x", summary="X", dtstart=date(2026, 4, 15), alarms=[3])
        assert "TRIGGER:-P3D" in event
        assert "TRIGGER:-P7D" not in event

    def test_no_alarms(self):
        event = generate_vevent(uid="x", summary="X", dtstart=date(2026, 4, 15), alarms=[])
        assert "VALARM" not in event


class TestGenerateCalendar:
    def test_basic_calendar(self):
        entries = [_entry("test-1", deadline_date=date(2026, 4, 15))]
        cal = generate_calendar(entries)
        assert "BEGIN:VCALENDAR" in cal
        assert "END:VCALENDAR" in cal
        assert "DEADLINE: Test test-1" in cal

    def test_no_deadline_entries_excluded(self):
        entries = [_entry("no-deadline")]
        cal = generate_calendar(entries)
        assert "VEVENT" not in cal

    def test_follow_ups_excluded_by_default(self):
        future = date.today() + timedelta(days=5)
        entries = [_entry("test", follow_up={"connect_date": str(future)})]
        cal = generate_calendar(entries, include_followups=False)
        assert "FOLLOW-UP" not in cal

    def test_follow_ups_included(self):
        future = date.today() + timedelta(days=5)
        entries = [_entry("test", follow_up={"connect_date": str(future)})]
        cal = generate_calendar(entries, include_followups=True)
        assert "FOLLOW-UP CONNECT" in cal

    def test_past_followups_excluded(self):
        past = date.today() - timedelta(days=5)
        entries = [_entry("test", follow_up={"connect_date": str(past)})]
        cal = generate_calendar(entries, include_followups=True)
        assert "FOLLOW-UP" not in cal


class TestGenerateEventList:
    def test_basic_list(self):
        entries = [_entry("test-1", deadline_date=date(2026, 4, 15))]
        events = generate_event_list(entries)
        assert len(events) == 1
        assert events[0]["type"] == "deadline"
        assert events[0]["id"] == "test-1"

    def test_sorted_by_date(self):
        entries = [
            _entry("later", deadline_date=date(2026, 5, 1)),
            _entry("sooner", deadline_date=date(2026, 4, 1)),
        ]
        events = generate_event_list(entries)
        assert events[0]["id"] == "sooner"
        assert events[1]["id"] == "later"

    def test_empty_entries(self):
        assert generate_event_list([]) == []
