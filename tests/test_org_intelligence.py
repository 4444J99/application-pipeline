#!/usr/bin/env python3
"""Tests for org_intelligence.py — organization aggregation and ranking."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from org_intelligence import (
    aggregate_org,
    format_org_detail,
    format_rankings,
    rank_orgs,
)


def _entry(entry_id, org="Acme", score=8.0, status="qualified", outcome=None, track="job"):
    return {
        "id": entry_id,
        "target": {"organization": org},
        "fit": {"score": score},
        "status": status,
        "outcome": outcome,
        "track": track,
    }


def _contact(name, org="Acme", interactions=None):
    return {
        "name": name,
        "organization": org,
        "interactions": interactions or [],
    }


class TestAggregateOrg:
    def test_basic_aggregation(self):
        entries = [_entry("a1", org="Acme", score=9.0), _entry("a2", org="Acme", score=7.0)]
        contacts = [_contact("Jane", org="Acme", interactions=[{"date": "2026-03-01"}])]
        agg = aggregate_org("Acme", entries, contacts)
        assert agg["total_entries"] == 2
        assert agg["total_contacts"] == 1
        assert agg["avg_score"] == 8.0
        assert agg["active_contacts"] == 1

    def test_case_insensitive_matching(self):
        entries = [_entry("a1", org="ACME"), _entry("a2", org="acme")]
        agg = aggregate_org("Acme", entries, [])
        assert agg["total_entries"] == 2

    def test_empty_org(self):
        agg = aggregate_org("NonExistent", [], [])
        assert agg["total_entries"] == 0
        assert agg["avg_score"] == 0.0

    def test_outcome_counts(self):
        entries = [
            _entry("a1", outcome="accepted"),
            _entry("a2", outcome="rejected"),
            _entry("a3"),
        ]
        agg = aggregate_org("Acme", entries, [])
        assert agg["outcomes"]["accepted"] == 1
        assert agg["outcomes"]["rejected"] == 1
        assert agg["outcomes"]["pending"] == 1


class TestRankOrgs:
    def test_ranking_order(self):
        entries = [
            _entry("a1", org="Good", score=9.5, outcome="accepted"),
            _entry("a2", org="Bad", score=5.0, outcome="rejected"),
        ]
        ranked = rank_orgs(entries, [])
        assert ranked[0]["organization"] == "Good"
        assert ranked[0]["opportunity_score"] > ranked[1]["opportunity_score"]

    def test_empty_entries(self):
        assert rank_orgs([], []) == []


class TestFormatting:
    def test_format_org_detail(self):
        agg = aggregate_org("Acme", [_entry("a1")], [])
        agg["opportunity_score"] = 25.0
        output = format_org_detail(agg)
        assert "Acme" in output
        assert "25.0" in output

    def test_format_rankings(self):
        ranked = [
            {"organization": "Alpha", "avg_score": 9.0, "total_entries": 5,
             "total_contacts": 3, "opportunity_score": 50.0},
        ]
        output = format_rankings(ranked)
        assert "Alpha" in output
        assert "50.0" in output
