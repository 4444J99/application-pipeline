"""Tests for scripts/standup_work_sections.py."""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from standup_work_sections import (
    compute_staged_submit_conversion,
    entry_has_portal_fields,
    section_deferred,
    section_execution_gap,
    section_health,
    section_outreach,
    section_plan,
    section_practices,
    section_precision_compliance,
    section_replenish,
    section_stale,
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


def _parse_date(value):
    if not value:
        return None
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


# ---------------------------------------------------------------------------
# Helpers for new section tests
# ---------------------------------------------------------------------------

ACTIONABLE = {"research", "qualified", "drafting", "staged"}


def _days_until(d):
    return (d - date.today()).days


def _get_deadline_none(_entry):
    return (None, None)


def _get_score(entry):
    return float(entry.get("fit", {}).get("score", 0))


# ---------------------------------------------------------------------------
# section_stale
# ---------------------------------------------------------------------------


def test_section_stale_stagnant_entry(capsys):
    """An actionable entry untouched for 30+ days shows up as stagnant."""
    entries = [
        _entry(status="qualified", name="Old Target", last_touched_days_ago=35),
        _entry(status="research", name="Fresh Target", last_touched_days_ago=2),
    ]

    result = section_stale(
        entries,
        actionable_statuses=ACTIONABLE,
        get_deadline_fn=_get_deadline_none,
        days_until_fn=_days_until,
        parse_date_fn=_parse_date,
        at_risk_days=14,
        stagnation_days=14,
    )

    output = capsys.readouterr().out
    assert result["stagnant"] == 1
    assert result["expired"] == 0
    assert result["at_risk"] == 0
    assert "Old Target" in output
    assert "NEEDS REVIEW" in output


def test_section_stale_expired_entry(capsys):
    """An entry whose hard deadline has passed appears as expired."""
    past_deadline = date.today() - timedelta(days=3)

    def get_deadline_past(entry):
        if entry.get("id") == "expired-one":
            return (past_deadline, "hard")
        return (None, None)

    entries = [
        {
            "id": "expired-one",
            "name": "Expired Grant",
            "status": "research",
            "last_touched": (date.today() - timedelta(days=1)).isoformat(),
        },
    ]

    result = section_stale(
        entries,
        actionable_statuses=ACTIONABLE,
        get_deadline_fn=get_deadline_past,
        days_until_fn=_days_until,
        parse_date_fn=_parse_date,
        at_risk_days=14,
        stagnation_days=14,
    )

    output = capsys.readouterr().out
    assert result["expired"] == 1
    assert "Expired Grant" in output


def test_section_stale_at_risk_entry(capsys):
    """An entry with a hard deadline within at_risk_days in early status shows at-risk."""
    upcoming_deadline = date.today() + timedelta(days=5)

    def get_deadline_soon(entry):
        if entry.get("id") == "urgent-one":
            return (upcoming_deadline, "hard")
        return (None, None)

    entries = [
        {
            "id": "urgent-one",
            "name": "Urgent Grant",
            "status": "research",
            "last_touched": date.today().isoformat(),
        },
    ]

    result = section_stale(
        entries,
        actionable_statuses=ACTIONABLE,
        get_deadline_fn=get_deadline_soon,
        days_until_fn=_days_until,
        parse_date_fn=_parse_date,
        at_risk_days=14,
        stagnation_days=14,
    )

    output = capsys.readouterr().out
    assert result["at_risk"] == 1
    assert "Urgent Grant" in output
    assert "AT-RISK" in output


# ---------------------------------------------------------------------------
# section_plan
# ---------------------------------------------------------------------------


def test_section_plan_scored_entries(capsys):
    """Entries are planned within budget and sorted by score."""
    entries = [
        _entry(status="qualified", name="High Score", score=9.5),
        _entry(status="drafting", name="Low Score", score=6.0),
    ]

    result = section_plan(
        entries,
        5.0,
        actionable_statuses=ACTIONABLE,
        urgency_days=14,
        effort_minutes={"quick": 30, "moderate": 60, "deep": 120},
        get_deadline_fn=_get_deadline_none,
        days_until_fn=_days_until,
        get_score_fn=_get_score,
        compute_freshness_score_fn=lambda e: 1.0,
        get_effort_fn=lambda e: "quick",
        freshness_badge_fn=lambda e: "",
    )

    output = capsys.readouterr().out
    assert result["planned"] == 2
    assert result["used_minutes"] == 60  # 2 x 30 min
    assert "TODAY'S WORK PLAN" in output
    assert "High Score" in output
    assert "Low Score" in output


def test_section_plan_budget_overflow(capsys):
    """Entries exceeding budget are flagged OVER BUDGET."""
    entries = [
        _entry(status="qualified", name="Big Task", score=9.0),
        _entry(status="drafting", name="Another Task", score=8.0),
    ]

    result = section_plan(
        entries,
        1.0,  # only 60 minutes
        actionable_statuses=ACTIONABLE,
        urgency_days=14,
        effort_minutes={"deep": 120},
        get_deadline_fn=_get_deadline_none,
        days_until_fn=_days_until,
        get_score_fn=_get_score,
        compute_freshness_score_fn=lambda e: 1.0,
        get_effort_fn=lambda e: "deep",
        freshness_badge_fn=lambda e: "",
    )

    output = capsys.readouterr().out
    # Only the first fits (budget=60, each=120 → nothing fits)
    assert result["planned"] == 0
    assert "OVER BUDGET" in output


# ---------------------------------------------------------------------------
# section_outreach
# ---------------------------------------------------------------------------


def test_section_outreach_status_tips(capsys):
    """Entries with different statuses get different outreach tips."""
    entries = [
        _entry(status="research", name="Research Target"),
        _entry(status="drafting", name="Drafting Target"),
    ]

    outreach_by_status = {
        "research": ["Identify hiring manager on LinkedIn"],
        "drafting": ["Send warm intro email"],
    }

    section_outreach(
        entries,
        actionable_statuses=ACTIONABLE,
        get_deadline_fn=_get_deadline_none,
        days_until_fn=_days_until,
        get_score_fn=_get_score,
        outreach_by_status=outreach_by_status,
    )

    output = capsys.readouterr().out
    assert "OUTREACH SUGGESTIONS" in output
    assert "Identify hiring manager on LinkedIn" in output
    assert "Send warm intro email" in output


def test_section_outreach_empty(capsys):
    """No actionable entries prints no-entries message."""
    section_outreach(
        [_entry(status="submitted", name="Already Sent")],
        actionable_statuses=ACTIONABLE,
        get_deadline_fn=_get_deadline_none,
        days_until_fn=_days_until,
        get_score_fn=_get_score,
        outreach_by_status={},
    )

    output = capsys.readouterr().out
    assert "No actionable entries" in output


# ---------------------------------------------------------------------------
# section_practices
# ---------------------------------------------------------------------------


def test_section_practices_high_stagnation(capsys):
    """When stagnant>5, shows high_stagnation tips."""
    entries = [_entry(status="research")]

    practices_by_context = {
        "pre_deadline_week": ["Review final checklist"],
        "no_submissions_ever": ["Submit your first application"],
        "high_stagnation": ["Triage stale entries: withdraw or advance"],
        "networking_cadence": ["Send 2 LinkedIn messages this week"],
    }

    section_practices(
        entries,
        {"stagnant": 8},
        get_deadline_fn=_get_deadline_none,
        days_until_fn=_days_until,
        practices_by_context=practices_by_context,
    )

    output = capsys.readouterr().out
    assert "BEST PRACTICES" in output
    assert "Triage stale entries" in output
    assert "Submit your first application" in output
    assert "Send 2 LinkedIn messages" in output


def test_section_practices_pre_deadline(capsys):
    """Hard deadline within 7 days triggers pre_deadline_week tips."""
    upcoming = date.today() + timedelta(days=3)

    def get_deadline_3d(entry):
        return (upcoming, "hard")

    entries = [_entry(status="qualified")]

    practices_by_context = {
        "pre_deadline_week": ["Final review before submission"],
        "no_submissions_ever": ["Get first submission out"],
        "high_stagnation": ["Triage entries"],
        "networking_cadence": ["Reach out"],
    }

    section_practices(
        entries,
        {"stagnant": 0},
        get_deadline_fn=get_deadline_3d,
        days_until_fn=_days_until,
        practices_by_context=practices_by_context,
    )

    output = capsys.readouterr().out
    assert "Final review before submission" in output


# ---------------------------------------------------------------------------
# section_replenish
# ---------------------------------------------------------------------------


def test_section_replenish_below_threshold(capsys):
    """When actionable < threshold, prints replenishment alert."""
    entries = [
        _entry(status="qualified", name="Only One"),
    ]

    section_replenish(
        entries,
        actionable_statuses=ACTIONABLE,
        get_deadline_fn=_get_deadline_none,
        days_until_fn=_days_until,
        replenish_threshold=5,
        load_entries_fn=lambda dirs: [],
        pipeline_dir_research_pool=Path("/fake/research_pool"),
        get_score_fn=_get_score,
    )

    output = capsys.readouterr().out
    assert "PIPELINE REPLENISHMENT" in output
    assert "Below threshold" in output
    assert "Research new perfect-fit targets" in output


def test_section_replenish_above_threshold(capsys):
    """When actionable >= threshold, prints OK message."""
    entries = [
        _entry(status="qualified", name="A"),
        _entry(status="drafting", name="B"),
        _entry(status="staged", name="C"),
    ]

    section_replenish(
        entries,
        actionable_statuses=ACTIONABLE,
        get_deadline_fn=_get_deadline_none,
        days_until_fn=_days_until,
        replenish_threshold=3,
        load_entries_fn=lambda dirs: [],
        pipeline_dir_research_pool=Path("/fake/research_pool"),
        get_score_fn=_get_score,
    )

    output = capsys.readouterr().out
    assert "OK" in output


# ---------------------------------------------------------------------------
# section_deferred
# ---------------------------------------------------------------------------


def test_section_deferred_with_resume_date(capsys):
    """Deferred entries display with resume_date info."""
    future = (date.today() + timedelta(days=10)).isoformat()
    entries = [
        {
            "id": "deferred-grant",
            "name": "Deferred Grant",
            "status": "deferred",
            "deferral": {
                "reason": "cycle not open",
                "resume_date": future,
                "note": "Opens in April",
            },
        },
        _entry(status="qualified", name="Active Entry"),
    ]

    section_deferred(entries, parse_date_fn=_parse_date)

    output = capsys.readouterr().out
    assert "DEFERRED ENTRIES" in output
    assert "Deferred Grant" in output
    assert "cycle not open" in output
    assert "resumes in 10d" in output
    assert "Opens in April" in output


def test_section_deferred_none(capsys):
    """No deferred entries prints clean message."""
    entries = [_entry(status="qualified", name="Active")]

    section_deferred(entries, parse_date_fn=_parse_date)

    output = capsys.readouterr().out
    assert "No deferred entries" in output


def test_section_deferred_past_resume_date(capsys):
    """Deferred entry with past resume date shows PAST RESUME DATE."""
    past = (date.today() - timedelta(days=5)).isoformat()
    entries = [
        {
            "id": "overdue-deferred",
            "name": "Overdue Deferral",
            "status": "deferred",
            "deferral": {"reason": "portal paused", "resume_date": past},
        },
    ]

    section_deferred(entries, parse_date_fn=_parse_date)

    output = capsys.readouterr().out
    assert "PAST RESUME DATE" in output
    assert "Overdue Deferral" in output


# ---------------------------------------------------------------------------
# section_precision_compliance
# ---------------------------------------------------------------------------


def test_section_precision_compliance_over_active(capsys):
    """Over max_active triggers OVER_LIMIT."""
    entries = [
        _entry(status="qualified", name=f"Entry {i}") for i in range(12)
    ]

    result = section_precision_compliance(
        entries,
        actionable_statuses=ACTIONABLE,
        parse_date_fn=_parse_date,
        max_active=10,
        max_weekly_submissions=2,
        company_cap=1,
    )

    output = capsys.readouterr().out
    assert result["actionable_count"] == 12
    assert result["actionable_compliant"] is False
    assert "OVER_LIMIT" in output
    assert "PRECISION MODE COMPLIANCE" in output


def test_section_precision_compliance_over_org_cap(capsys):
    """Multiple entries for same org exceeding company_cap triggers OVER_LIMIT."""
    entries = [
        {
            "id": "acme-1",
            "name": "Acme Role 1",
            "status": "qualified",
            "target": {"organization": "Acme Corp"},
            "fit": {"score": 8.0},
            "timeline": {},
        },
        {
            "id": "acme-2",
            "name": "Acme Role 2",
            "status": "drafting",
            "target": {"organization": "Acme Corp"},
            "fit": {"score": 7.0},
            "timeline": {},
        },
    ]

    result = section_precision_compliance(
        entries,
        actionable_statuses=ACTIONABLE,
        parse_date_fn=_parse_date,
        max_active=10,
        max_weekly_submissions=2,
        company_cap=1,
    )

    output = capsys.readouterr().out
    assert result["over_cap_orgs"] == 1
    assert result["actionable_compliant"] is True  # only 2 entries, under 10
    assert "Acme Corp" in output
    assert "OVER_LIMIT" in output


def test_section_precision_compliance_all_compliant(capsys):
    """When all metrics are within limits, all_compliant is True."""
    entries = [
        _entry(status="qualified", name="Only Entry"),
    ]

    result = section_precision_compliance(
        entries,
        actionable_statuses=ACTIONABLE,
        parse_date_fn=_parse_date,
        max_active=10,
        max_weekly_submissions=2,
        company_cap=1,
    )

    output = capsys.readouterr().out
    assert result["all_compliant"] is True
    assert result["actionable_compliant"] is True
    assert result["weekly_compliant"] is True
    assert "All metrics within precision-mode limits" in output


def test_section_precision_compliance_weekly_submissions(capsys):
    """Recent submissions within 7 days counted for weekly compliance."""
    recent_date = (date.today() - timedelta(days=2)).isoformat()
    entries = [
        {
            "id": "sub-1",
            "name": "Recent Sub 1",
            "status": "submitted",
            "timeline": {"submitted": recent_date},
            "fit": {"score": 8.0},
        },
        {
            "id": "sub-2",
            "name": "Recent Sub 2",
            "status": "submitted",
            "timeline": {"submitted": recent_date},
            "fit": {"score": 7.0},
        },
        {
            "id": "sub-3",
            "name": "Recent Sub 3",
            "status": "submitted",
            "timeline": {"submitted": recent_date},
            "fit": {"score": 7.5},
        },
    ]

    result = section_precision_compliance(
        entries,
        actionable_statuses=ACTIONABLE,
        parse_date_fn=_parse_date,
        max_active=10,
        max_weekly_submissions=2,
        company_cap=1,
    )

    assert result["weekly_submissions"] == 3
    assert result["weekly_compliant"] is False
