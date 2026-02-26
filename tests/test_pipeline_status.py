"""Tests for scripts/pipeline_status.py pure computation functions."""

import sys
from datetime import datetime, timedelta
from pathlib import Path
from io import StringIO

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from pipeline_status import (
    print_summary,
    print_upcoming,
    print_rolling,
    print_top,
    print_benefits_check,
    BENEFITS_THRESHOLDS,
    IN_FLIGHT_STATUSES,
)


# --- Helpers ---

def _make_entry(
    entry_id="test-1",
    name="Test Entry",
    status="research",
    track="job",
    score=5.0,
    deadline_date=None,
    deadline_type="hard",
    location_class="domestic",
    organization="Test Org",
    amount_value=0,
    amount_currency="USD",
    benefits_cliff_note=None,
):
    entry = {
        "id": entry_id,
        "name": name,
        "status": status,
        "track": track,
        "fit": {"score": score},
        "target": {
            "organization": organization,
            "location_class": location_class,
        },
        "timeline": {},
    }
    if deadline_date:
        entry["deadline"] = {"date": deadline_date, "type": deadline_type}
    if amount_value:
        entry["amount"] = {
            "value": amount_value,
            "currency": amount_currency,
        }
        if benefits_cliff_note:
            entry["amount"]["benefits_cliff_note"] = benefits_cliff_note
    return entry


# --- print_summary ---

class TestPrintSummary:
    def test_shows_total(self, capsys):
        entries = [
            _make_entry(status="research"),
            _make_entry(entry_id="t2", status="qualified"),
        ]
        print_summary(entries)
        captured = capsys.readouterr()
        assert "Total entries: 2" in captured.out
        assert "APPLICATION PIPELINE STATUS" in captured.out

    def test_status_breakdown(self, capsys):
        entries = [
            _make_entry(status="research"),
            _make_entry(entry_id="t2", status="research"),
            _make_entry(entry_id="t3", status="submitted"),
        ]
        print_summary(entries)
        captured = capsys.readouterr()
        assert "research" in captured.out
        assert "submitted" in captured.out

    def test_track_breakdown(self, capsys):
        entries = [
            _make_entry(track="job"),
            _make_entry(entry_id="t2", track="grant"),
        ]
        print_summary(entries)
        captured = capsys.readouterr()
        assert "job" in captured.out
        assert "grant" in captured.out


# --- print_upcoming ---

class TestPrintUpcoming:
    def test_no_upcoming(self, capsys):
        entries = [_make_entry()]
        print_upcoming(entries, days=30)
        captured = capsys.readouterr()
        assert "No deadlines in this window" in captured.out

    def test_shows_upcoming_deadline(self, capsys):
        future = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d")
        entries = [
            _make_entry(
                name="Upcoming Grant",
                deadline_date=future,
                deadline_type="hard",
            ),
        ]
        print_upcoming(entries, days=30)
        captured = capsys.readouterr()
        assert "Upcoming Grant" in captured.out

    def test_urgency_markers(self, capsys):
        soon = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
        entries = [
            _make_entry(
                name="Urgent Deadline",
                deadline_date=soon,
                deadline_type="hard",
            ),
        ]
        print_upcoming(entries, days=30)
        captured = capsys.readouterr()
        assert "!!!" in captured.out


# --- print_rolling ---

class TestPrintRolling:
    def test_no_rolling(self, capsys):
        entries = [_make_entry()]
        print_rolling(entries)
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_shows_rolling(self, capsys):
        entries = [{
            "id": "r1",
            "name": "Rolling Opp",
            "status": "research",
            "deadline": {"type": "rolling"},
            "fit": {"score": 6},
        }]
        print_rolling(entries)
        captured = capsys.readouterr()
        assert "ROLLING" in captured.out
        assert "Rolling Opp" in captured.out


# --- print_top ---

class TestPrintTop:
    def test_filters_international(self, capsys):
        entries = [
            _make_entry(entry_id="d1", name="Domestic", location_class="domestic", status="qualified", score=8),
            _make_entry(entry_id="i1", name="International", location_class="international", status="qualified", score=9),
        ]
        print_top(entries, 10)
        captured = capsys.readouterr()
        assert "Domestic" in captured.out
        assert "International" not in captured.out

    def test_filters_non_actionable(self, capsys):
        entries = [
            _make_entry(entry_id="a1", name="Active", status="qualified", score=7),
            _make_entry(entry_id="s1", name="Submitted", status="submitted", score=9),
        ]
        print_top(entries, 10)
        captured = capsys.readouterr()
        assert "Active" in captured.out
        assert "Submitted" not in captured.out

    def test_respects_limit(self, capsys):
        entries = [
            _make_entry(entry_id=f"e{i}", name=f"Entry {i}", status="qualified", score=float(i))
            for i in range(10)
        ]
        print_top(entries, 3)
        captured = capsys.readouterr()
        assert "10 actionable US-accessible entries total" in captured.out


# --- print_benefits_check ---

class TestPrintBenefitsCheck:
    def test_no_in_flight(self, capsys):
        entries = [_make_entry(status="research", amount_value=50000)]
        print_benefits_check(entries)
        captured = capsys.readouterr()
        assert "No in-flight entries with compensation" in captured.out

    def test_in_flight_with_amount(self, capsys):
        entries = [
            _make_entry(
                name="Job Offer",
                status="submitted",
                amount_value=25000,
            ),
        ]
        print_benefits_check(entries)
        captured = capsys.readouterr()
        assert "Job Offer" in captured.out
        assert "$25,000" in captured.out

    def test_eur_conversion(self, capsys):
        entries = [
            _make_entry(
                name="Euro Grant",
                status="qualified",
                amount_value=10000,
                amount_currency="EUR",
            ),
        ]
        print_benefits_check(entries)
        captured = capsys.readouterr()
        assert "EUR 10,000" in captured.out

    def test_benefits_cliff_warning(self, capsys):
        entries = [
            _make_entry(
                name="High Pay Job",
                status="submitted",
                amount_value=50000,
            ),
        ]
        print_benefits_check(entries)
        captured = capsys.readouterr()
        assert "exceeds" in captured.out
