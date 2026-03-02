"""Tests for company cap enforcement (COMPANY_CAP, company_entry_counts, check_company_cap)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from pipeline_lib import COMPANY_CAP, check_company_cap, company_entry_counts


def _make_entry(org: str, status: str = "qualified") -> dict:
    return {"target": {"organization": org}, "status": status}


class TestCompanyCap:
    def test_cap_value(self):
        assert COMPANY_CAP == 3


class TestCompanyEntryCounts:
    def test_basic_counting(self):
        entries = [
            _make_entry("Anthropic", "qualified"),
            _make_entry("Anthropic", "drafting"),
            _make_entry("OpenAI", "staged"),
        ]
        counts = company_entry_counts(entries)
        assert counts["Anthropic"] == 2
        assert counts["OpenAI"] == 1

    def test_excludes_closed_statuses(self):
        entries = [
            _make_entry("Anthropic", "qualified"),
            _make_entry("Anthropic", "closed"),
            _make_entry("Anthropic", "expired"),
            _make_entry("Anthropic", "withdrawn"),
            _make_entry("Anthropic", "rejected"),
        ]
        counts = company_entry_counts(entries, actionable_only=True)
        assert counts["Anthropic"] == 1

    def test_includes_all_when_not_actionable_only(self):
        entries = [
            _make_entry("Anthropic", "qualified"),
            _make_entry("Anthropic", "closed"),
            _make_entry("Anthropic", "rejected"),
        ]
        counts = company_entry_counts(entries, actionable_only=False)
        assert counts["Anthropic"] == 3

    def test_missing_organization(self):
        entries = [{"target": {}, "status": "qualified"}]
        counts = company_entry_counts(entries)
        assert counts["Unknown"] == 1

    def test_missing_target(self):
        entries = [{"status": "qualified"}]
        counts = company_entry_counts(entries)
        assert counts["Unknown"] == 1

    def test_empty_entries(self):
        counts = company_entry_counts([])
        assert counts == {}


class TestCheckCompanyCap:
    def test_under_cap(self):
        entries = [_make_entry("Anthropic", "qualified")]
        allowed, count = check_company_cap("Anthropic", entries)
        assert allowed is True
        assert count == 1

    def test_at_cap(self):
        entries = [
            _make_entry("Anthropic", "qualified"),
            _make_entry("Anthropic", "drafting"),
            _make_entry("Anthropic", "staged"),
        ]
        allowed, count = check_company_cap("Anthropic", entries)
        assert allowed is False
        assert count == 3

    def test_over_cap(self):
        entries = [
            _make_entry("Anthropic", "qualified"),
            _make_entry("Anthropic", "drafting"),
            _make_entry("Anthropic", "staged"),
            _make_entry("Anthropic", "submitted"),
        ]
        allowed, count = check_company_cap("Anthropic", entries)
        assert allowed is False
        assert count == 4

    def test_closed_not_counted(self):
        entries = [
            _make_entry("Anthropic", "qualified"),
            _make_entry("Anthropic", "closed"),
            _make_entry("Anthropic", "rejected"),
            _make_entry("Anthropic", "expired"),
            _make_entry("Anthropic", "withdrawn"),
        ]
        allowed, count = check_company_cap("Anthropic", entries)
        assert allowed is True
        assert count == 1

    def test_custom_cap(self):
        entries = [_make_entry("Anthropic", "qualified")]
        allowed, count = check_company_cap("Anthropic", entries, cap=1)
        assert allowed is False
        assert count == 1

    def test_no_entries_for_org(self):
        entries = [_make_entry("OpenAI", "qualified")]
        allowed, count = check_company_cap("Anthropic", entries)
        assert allowed is True
        assert count == 0

    def test_empty_entries(self):
        allowed, count = check_company_cap("Anthropic", [])
        assert allowed is True
        assert count == 0

    def test_empty_org_name(self):
        entries = [_make_entry("", "qualified")]
        allowed, count = check_company_cap("", entries)
        # Empty org should still be counted
        assert count == 1
