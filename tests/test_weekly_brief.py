"""Tests for scripts/weekly_brief.py."""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import weekly_brief as wb


def test_compute_readiness_summary_aggregates_blockers(monkeypatch):
    active_entries = [
        {"id": "a1", "status": "staged"},
        {"id": "a2", "status": "qualified"},
        {"id": "a3", "status": "drafting"},
    ]

    fake_results = {
        "a1": {
            "id": "a1",
            "status": "staged",
            "ready": False,
            "results": {"staged_sla": False, "review_approved": False, "resume_pdf": True},
        },
        "a2": {
            "id": "a2",
            "status": "qualified",
            "ready": True,
            "results": {"resume_pdf": True, "cover_letter": True},
        },
        "a3": {
            "id": "a3",
            "status": "drafting",
            "ready": False,
            "results": {"resume_pdf": False, "cover_letter": False},
        },
    }

    monkeypatch.setattr(wb, "check_entry", lambda entry, deep=False, config=None: fake_results[entry["id"]])
    summary = wb.compute_readiness_summary(active_entries)

    assert summary["total_audited"] == 3
    assert summary["ready"] == 1
    assert summary["blocked"] == 2
    assert summary["staged_sla_breaches"] == 1
    assert summary["staged_review_pending"] == 1
    blocker_names = {item["check"] for item in summary["top_blockers"]}
    assert "staged_sla" in blocker_names
    assert "review_approved" in blocker_names


def test_build_brief_payload_wires_sections(monkeypatch):
    today = date.today().isoformat()

    active = [
        {
            "id": "active-1",
            "status": "qualified",
            "timeline": {"submitted": today},
            "target": {"portal": "greenhouse"},
        }
    ]
    submitted = [
        {
            "id": "submitted-1",
            "status": "submitted",
            "timeline": {"submitted": today},
            "target": {"portal": "ashby"},
        }
    ]
    closed = [
        {
            "id": "closed-1",
            "status": "outcome",
            "timeline": {"submitted": today},
            "target": {"portal": "greenhouse"},
        }
    ]

    def fake_load_entries(*, dirs=None, include_filepath=False):
        if dirs == [wb.PIPELINE_DIR_ACTIVE]:
            return active
        if dirs == [wb.PIPELINE_DIR_SUBMITTED]:
            return submitted
        if dirs == [wb.PIPELINE_DIR_CLOSED]:
            return closed
        return []

    monkeypatch.setattr(wb, "load_entries", fake_load_entries)
    monkeypatch.setattr(
        wb,
        "check_entry",
        lambda entry, deep=False, config=None: {
            "id": entry["id"],
            "status": entry["status"],
            "ready": True,
            "results": {"resume_pdf": True},
        },
    )
    monkeypatch.setattr(
        wb,
        "generate_audit_report",
        lambda entries: {
            "summary": {
                "warm_path_pct": 42,
                "dense_organizations": 2,
                "referral_candidates": 3,
                "outreach_queue": 1,
            },
            "outreach_queue": [
                {
                    "organization": "example",
                    "entry_id": "active-1",
                    "assignee": "4jp",
                    "due_date": today,
                    "next_action": "request intro",
                }
            ],
        },
    )
    monkeypatch.setattr(
        wb,
        "extract_failure_themes",
        lambda entries, months=1: {
            "months": months,
            "total_failures": 1,
            "by_reason": {"skills_mismatch": 1},
            "by_theme": {"scope": 1},
            "by_track": {"creative-technologist": 1},
        },
    )
    monkeypatch.setattr(
        wb,
        "load_conversion_log",
        lambda: [{"submission_date": today, "response_date": today, "outcome": "accepted", "portal": "greenhouse"}],
    )
    monkeypatch.setattr(wb, "load_hypotheses", lambda: [])

    payload = wb.build_brief_payload(week_days=7, failure_months=1)

    assert payload["snapshot"]["total_entries"] == 3
    assert payload["snapshot"]["weekly_submissions"] == 3
    assert payload["readiness"]["ready"] == 1
    assert payload["conversion"]["weekly_acceptances"] == 1
    assert payload["outreach"]["outreach_queue_count"] == 1
    assert payload["failures"]["total_failures"] == 1
    assert payload["recommendations"]


def test_format_markdown_has_expected_sections():
    payload = {
        "generated_at": "2026-03-04T10:00:00",
        "week_days": 7,
        "failure_months": 1,
        "snapshot": {
            "total_entries": 10,
            "active_entries": 4,
            "submitted_entries": 3,
            "closed_entries": 3,
            "actionable": 4,
            "submitted_awaiting": 2,
            "statuses": {"qualified": 2},
            "weekly_submissions": 2,
            "weekly_submissions_by_portal": {"greenhouse": 2},
        },
        "readiness": {
            "total_audited": 4,
            "ready": 2,
            "blocked": 2,
            "staged_sla_breaches": 1,
            "staged_review_pending": 1,
            "top_blockers": [{"check": "review_approved", "count": 1}],
        },
        "conversion": {
            "weekly_log_submissions": 2,
            "weekly_responses": 1,
            "weekly_acceptances": 1,
            "weekly_response_rate": 0.5,
            "weekly_acceptance_rate": 1.0,
            "weekly_portals": {"greenhouse": 2},
            "hypothesis_accuracy": {"accuracy": 0.6, "correct": 3, "total": 5},
        },
        "outreach": {
            "warm_path_pct": 50,
            "dense_organizations": 2,
            "referral_candidates": 3,
            "outreach_queue_count": 1,
            "outreach_queue": [
                {
                    "organization": "example",
                    "entry_id": "entry-1",
                    "assignee": "4jp",
                    "due_date": "2026-03-07",
                    "next_action": "request intro",
                }
            ],
        },
        "failures": {
            "total_failures": 2,
            "top_reasons": [{"reason": "skills_mismatch", "count": 2}],
            "top_themes": [{"theme": "scope", "count": 1}],
            "by_track": {"creative-technologist": 2},
        },
        "recommendations": ["clear blockers"],
    }

    report = wb.format_markdown(payload)
    assert "# Weekly Executive Brief" in report
    assert "## Pipeline Snapshot" in report
    assert "## Readiness & Blockers" in report
    assert "## Conversion & Learning" in report
    assert "## Warm Intro Priorities" in report
    assert "## Failure Themes" in report
    assert "## Executive Actions" in report


def test_save_brief_writes_dated_and_latest(tmp_path, monkeypatch):
    monkeypatch.setattr(wb, "SIGNALS_DIR", tmp_path)
    dated, latest = wb.save_brief("# test")
    assert dated.exists()
    assert latest.exists()
    assert latest.read_text() == "# test"
