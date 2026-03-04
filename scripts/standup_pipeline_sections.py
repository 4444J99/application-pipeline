#!/usr/bin/env python3
"""Standup sections for job and opportunity pipeline reporting."""

from __future__ import annotations

from datetime import date

from pipeline_lib import (
    ACTIONABLE_STATUSES,
    days_until,
    get_deadline,
    get_effort,
    get_freshness_tier,
    get_posting_age_hours,
    get_score,
    parse_date,
)

_FRESHNESS_BADGES = {
    "hot": "[HOT <24h]",
    "warm": "[WARM 24-48h]",
    "cooling": "[COOLING 48-72h]",
    "stale": "[STALE >72h]",
}


def _freshness_badge(entry: dict) -> str:
    """Return a freshness indicator string for a job entry."""
    if entry.get("track") != "job":
        return ""
    age = get_posting_age_hours(entry)
    if age is None:
        return "[AGE?]"
    tier = get_freshness_tier(entry)
    return _FRESHNESS_BADGES.get(tier, "[AGE?]")


def section_jobs(entries: list[dict]) -> None:
    """Display job-track pipeline sorted by score and submission status."""
    job_entries = [e for e in entries if e.get("track") == "job"]

    print("JOB PIPELINE")
    if not job_entries:
        print("   No job-track entries in pipeline.")
        print()
        return

    by_status: dict[str, list] = {}
    for e in job_entries:
        status = e.get("status", "unknown")
        by_status.setdefault(status, []).append(e)

    print(f"   Total job entries: {len(job_entries)}")
    status_order = [
        "research",
        "qualified",
        "drafting",
        "staged",
        "deferred",
        "submitted",
        "acknowledged",
        "interview",
        "outcome",
    ]
    status_parts = []
    for status_name in status_order:
        count = len(by_status.get(status_name, []))
        if count:
            status_parts.append(f"{status_name}={count}")
    print(f"   Status: {', '.join(status_parts)}")
    print()

    actionable_jobs = [e for e in job_entries if e.get("status") in ACTIONABLE_STATUSES]
    actionable_jobs.sort(key=get_score, reverse=True)

    if actionable_jobs:
        print("   Actionable (by score):")
        for entry in actionable_jobs:
            entry_id = entry.get("id", "?")
            name = entry.get("name", entry_id)
            score = get_score(entry)
            status = entry.get("status", "?")
            portal = entry.get("target", {}).get("portal", "?") if isinstance(entry.get("target"), dict) else "?"
            tags_str = ""
            tags = entry.get("tags", [])
            if isinstance(tags, list) and "auto-sourced" in tags:
                tags_str = " [auto]"
            freshness_badge = _freshness_badge(entry)
            print(f"     [{score:.1f}] {name} — {status} [{portal}]{tags_str} {freshness_badge}")

    submitted_jobs = [e for e in job_entries if e.get("status") in ("submitted", "acknowledged", "interview")]
    if submitted_jobs:
        print("   Awaiting response:")
        for entry in submitted_jobs:
            name = entry.get("name", entry.get("id", "?"))
            status = entry.get("status", "?")
            timeline = entry.get("timeline", {})
            submitted_date = timeline.get("submitted", "") if isinstance(timeline, dict) else ""
            days_str = ""
            if submitted_date:
                parsed = parse_date(submitted_date)
                if parsed:
                    days_waiting = (date.today() - parsed).days
                    days_str = f" ({days_waiting}d ago)"
            print(f"     {name} — {status}{days_str}")

    print()


def section_job_freshness(entries: list[dict]) -> None:
    """Show job posting freshness breakdown for actionable job entries."""
    job_entries = [e for e in entries if e.get("track") == "job" and e.get("status") in ACTIONABLE_STATUSES]

    print("JOB FRESHNESS")

    if not job_entries:
        print("   No actionable job entries.")
        print()
        return

    buckets: dict[str, list[dict]] = {
        "hot": [],
        "warm": [],
        "cooling": [],
        "stale": [],
        "unknown": [],
    }
    for entry in job_entries:
        age = get_posting_age_hours(entry)
        if age is None:
            buckets["unknown"].append(entry)
        else:
            tier = get_freshness_tier(entry) or "unknown"
            buckets[tier].append(entry)

    hot = buckets["hot"]
    warm = buckets["warm"]
    cooling = buckets["cooling"]
    stale = buckets["stale"]
    unknown = buckets["unknown"]

    print(
        f"   HOT: {len(hot)}  |  WARM: {len(warm)}  |  COOLING: {len(cooling)}"
        f"  |  STALE: {len(stale)}  |  AGE?: {len(unknown)}"
    )
    print()

    if hot:
        print("   HOT — submit NOW:")
        for entry in sorted(hot, key=get_score, reverse=True):
            name = entry.get("name", entry.get("id", "?"))
            score = get_score(entry)
            print(f"     [{score:.1f}] {name}")

    if warm:
        print("   WARM — still viable today:")
        for entry in sorted(warm, key=get_score, reverse=True):
            name = entry.get("name", entry.get("id", "?"))
            score = get_score(entry)
            print(f"     [{score:.1f}] {name}")

    if cooling:
        print("   COOLING — submit only if staged:")
        for entry in sorted(cooling, key=get_score, reverse=True):
            name = entry.get("name", entry.get("id", "?"))
            score = get_score(entry)
            print(f"     [{score:.1f}] {name}")

    if stale:
        print(f"   {len(stale)} stale job entries — candidates for auto-expire")

    if unknown:
        print(f"   {len(unknown)} entries with no posting date (cannot determine freshness)")

    print()


def section_opportunities(entries: list[dict]) -> None:
    """Display non-job pipeline sorted by deadline."""
    opp_entries = [e for e in entries if e.get("track") != "job" and e.get("status") in ACTIONABLE_STATUSES]

    print("OPPORTUNITY PIPELINE (grants/residencies/prizes/writing)")
    if not opp_entries:
        print("   No actionable non-job entries.")
        print()
        return

    def opp_sort_key(entry: dict) -> tuple[int, int, float]:
        deadline_date, deadline_type = get_deadline(entry)
        if deadline_date:
            days_left = days_until(deadline_date)
            if days_left >= 0 and deadline_type in ("hard", "fixed"):
                return (0, days_left, -get_score(entry))
        return (1, 9999, -get_score(entry))

    opp_entries.sort(key=opp_sort_key)

    print(f"   Actionable opportunities: {len(opp_entries)}")
    print()
    for entry in opp_entries[:15]:
        name = entry.get("name", entry.get("id", "?"))
        score = get_score(entry)
        status = entry.get("status", "?")
        track = entry.get("track", "?")
        deadline_date, deadline_type = get_deadline(entry)
        deadline_str = ""
        if deadline_date:
            days_left = days_until(deadline_date)
            if days_left < 0:
                deadline_str = f" EXPIRED {abs(days_left)}d ago"
            elif deadline_type in ("hard", "fixed"):
                deadline_str = f" {days_left}d left"
            else:
                deadline_str = f" ~{days_left}d ({deadline_type})"
        elif deadline_type in ("rolling", "tba"):
            deadline_str = f" {deadline_type}"
        effort = get_effort(entry)
        print(f"     [{score:.1f}] {name}")
        print(f"           {track} — {status} — {effort}{deadline_str}")

    if len(opp_entries) > 15:
        print(f"     ... and {len(opp_entries) - 15} more")
    print()

