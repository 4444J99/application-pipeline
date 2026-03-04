"""Work-planning standup section implementations."""

from __future__ import annotations

from datetime import date


def section_health(entries: list[dict], *, actionable_statuses: set[str], parse_date_fn) -> dict:
    """Pipeline-wide counts and velocity."""
    today = date.today()
    total = len(entries)
    by_status: dict[str, int] = {}
    actionable = 0
    submitted_count = 0
    last_submit_date = None

    for entry in entries:
        status = entry.get("status", "unknown")
        by_status[status] = by_status.get(status, 0) + 1

        if status in actionable_statuses:
            actionable += 1
        if status in ("submitted", "acknowledged", "interview"):
            submitted_count += 1

        timeline = entry.get("timeline", {})
        if isinstance(timeline, dict) and timeline.get("submitted"):
            submitted_date = parse_date_fn(timeline["submitted"])
            if submitted_date and (last_submit_date is None or submitted_date > last_submit_date):
                last_submit_date = submitted_date

    days_since = (today - last_submit_date).days if last_submit_date else None

    print("1. PIPELINE HEALTH")
    print(f"   Total entries: {total}")
    print(f"   Actionable (research/qualified/drafting/staged): {actionable}")
    print(f"   Submitted / awaiting response: {submitted_count}")
    if days_since is not None:
        print(f"   Days since last submission: {days_since}")
    else:
        print("   Days since last submission: NEVER (0 submissions)")
    print()

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
    print("   Status breakdown:")
    for status_name in status_order:
        count = by_status.get(status_name, 0)
        if count > 0:
            print(f"     {status_name:15s} {count:3d}  {'#' * count}")
    print()

    return {
        "total": total,
        "actionable": actionable,
        "submitted": submitted_count,
        "days_since_last_submission": days_since,
    }


def section_stale(
    entries: list[dict],
    *,
    actionable_statuses: set[str],
    get_deadline_fn,
    days_until_fn,
    parse_date_fn,
    at_risk_days: int,
    stagnation_days: int,
) -> dict:
    """Flag expired, at-risk, and stagnant entries."""
    today = date.today()
    expired = []
    at_risk = []
    stagnant = []

    for entry in entries:
        entry_id = entry.get("id", "?")
        status = entry.get("status", "")
        deadline_date, deadline_type = get_deadline_fn(entry)

        if deadline_date and days_until_fn(deadline_date) < 0 and status in actionable_statuses:
            expired.append((entry_id, entry.get("name", entry_id), deadline_date, status))
            continue

        if (
            deadline_date
            and deadline_type in ("hard", "fixed")
            and 0 <= days_until_fn(deadline_date) <= at_risk_days
            and status in ("research", "qualified")
        ):
            at_risk.append(
                (
                    entry_id,
                    entry.get("name", entry_id),
                    deadline_date,
                    status,
                    days_until_fn(deadline_date),
                )
            )
            continue

        if status in actionable_statuses:
            last_touched = parse_date_fn(entry.get("last_touched"))
            if last_touched:
                stale_days = (today - last_touched).days
                if stale_days > stagnation_days:
                    stagnant.append((entry_id, entry.get("name", entry_id), last_touched, stale_days, status))

    print("2. STALENESS ALERTS")

    if expired:
        print(f"   EXPIRED ({len(expired)}) — deadline passed, never submitted:")
        for _eid, name, deadline_date, status in expired:
            print(f"     !!! {name} — deadline was {deadline_date} ({abs(days_until_fn(deadline_date))}d ago) — {status}")
            print("         Action: archive with outcome=expired or withdraw")
    else:
        print("   EXPIRED: none")

    if at_risk:
        print(f"   AT-RISK ({len(at_risk)}) — hard deadline ≤{at_risk_days}d + early status:")
        for _eid, name, _deadline_date, status, days_left in at_risk:
            print(f"     !! {name} — {days_left}d left — still {status}")
            print("        Action: stage immediately or withdraw")
    else:
        print("   AT-RISK: none")

    if stagnant:
        stagnant.sort(key=lambda row: row[3], reverse=True)
        print(f"   STAGNANT ({len(stagnant)}) — no review in >{stagnation_days} days:")
        for _eid, name, last_touched, days_stale, status in stagnant[:10]:
            print(f"     {name} — {days_stale}d since last touch ({last_touched}) — {status}")
        if len(stagnant) > 10:
            print(f"     ... and {len(stagnant) - 10} more")
    else:
        print("   STAGNANT: none")

    print()
    return {
        "expired": len(expired),
        "at_risk": len(at_risk),
        "stagnant": len(stagnant),
    }


def entry_has_portal_fields(entry: dict) -> bool:
    """Return True when portal_fields.fields exists and is non-empty."""
    portal_fields = entry.get("portal_fields")
    return (
        isinstance(portal_fields, dict)
        and isinstance(portal_fields.get("fields"), list)
        and len(portal_fields["fields"]) > 0
    )


def compute_staged_submit_conversion(entries: list[dict]) -> tuple[int, int, float]:
    """Compute operational staged->submitted conversion from current pipeline state."""
    in_funnel = {"staged", "submitted", "acknowledged", "interview", "outcome"}
    submitted_or_beyond = {"submitted", "acknowledged", "interview", "outcome"}

    denominator = sum(1 for entry in entries if entry.get("status") in in_funnel)
    numerator = sum(1 for entry in entries if entry.get("status") in submitted_or_beyond)
    rate = (numerator / denominator) if denominator else 0.0
    return numerator, denominator, rate


def section_execution_gap(
    entries: list[dict],
    *,
    parse_date_fn,
    get_score_fn,
    target_staged_submit_conversion: float,
    execution_stale_staged_days: int,
    load_recent_agent_runs_fn,
) -> dict:
    """Highlight operational bottlenecks that block staged->submitted flow."""
    today = date.today()
    staged_entries = [entry for entry in entries if entry.get("status") == "staged"]

    stale_staged = []
    missing_portal = []

    for entry in staged_entries:
        last_touched = parse_date_fn(entry.get("last_touched"))
        stale_days = (today - last_touched).days if last_touched else 999
        if stale_days > execution_stale_staged_days:
            stale_staged.append((stale_days, entry))
        if not entry_has_portal_fields(entry):
            missing_portal.append(entry)

    stale_staged.sort(key=lambda row: row[0], reverse=True)
    numerator, denominator, conversion_rate = compute_staged_submit_conversion(entries)

    print("2b. EXECUTION GAP SNAPSHOT")
    print(f"   Staged entries: {len(staged_entries)}")
    print(f"   Stale staged >{execution_stale_staged_days * 24}h: {len(stale_staged)}")
    print(f"   Staged missing portal_fields: {len(missing_portal)}")
    print(
        f"   Staged->Submitted: {conversion_rate * 100:.1f}% "
        f"({numerator}/{denominator}, target {target_staged_submit_conversion * 100:.0f}%)"
    )

    if conversion_rate < target_staged_submit_conversion:
        print("   !! Bottleneck: submission velocity below target")

    if stale_staged:
        print("   Top stale staged entries:")
        for stale_days, entry in stale_staged[:10]:
            name = entry.get("name", entry.get("id", "?"))
            score = get_score_fn(entry)
            print(f"     - {name} — {stale_days}d stale — fit {score:.1f}")

    if missing_portal:
        print("   Staged entries missing portal_fields:")
        for entry in missing_portal[:10]:
            name = entry.get("name", entry.get("id", "?"))
            print(f"     - {name}")

    recent_runs = load_recent_agent_runs_fn(days=7)
    execute_runs = [run for run in recent_runs if run.get("mode") == "execute"]
    executed_actions = sum(int(run.get("executed", 0)) for run in execute_runs)
    print(
        f"   Autonomous runs (7d): {len(execute_runs)} execute runs, "
        f"{executed_actions} actions executed"
    )
    if not execute_runs:
        print("   Action: install/load launchd agents or run `python scripts/agent.py --execute --yes`")

    print()
    return {
        "staged": len(staged_entries),
        "stale_staged": len(stale_staged),
        "missing_portal": len(missing_portal),
        "conversion_rate": round(conversion_rate, 3),
        "autonomous_runs": len(execute_runs),
    }


def section_plan(
    entries: list[dict],
    hours: float,
    *,
    actionable_statuses: set[str],
    urgency_days: int,
    effort_minutes: dict[str, int],
    get_deadline_fn,
    days_until_fn,
    get_score_fn,
    compute_freshness_score_fn,
    get_effort_fn,
    freshness_badge_fn,
) -> dict:
    """Deadline-driven + score-sorted work plan within a time budget."""
    budget = int(hours * 60)
    used = 0
    actionable = [entry for entry in entries if entry.get("status") in actionable_statuses]
    urgent: list[tuple[int, dict]] = []
    scored: list[dict] = []

    for entry in actionable:
        deadline_date, deadline_type = get_deadline_fn(entry)
        if deadline_date:
            days_left = days_until_fn(deadline_date)
            if days_left < 0:
                continue
            if days_left <= urgency_days and deadline_type in ("hard", "fixed"):
                urgent.append((days_left, entry))
                continue
        scored.append(entry)

    urgent.sort(key=lambda row: row[0])

    def plan_sort_key(entry: dict) -> float:
        base = get_score_fn(entry)
        if entry.get("track") == "job":
            return base * compute_freshness_score_fn(entry)
        return base

    scored.sort(key=plan_sort_key, reverse=True)

    print(f"3. TODAY'S WORK PLAN ({hours:.1f}h budget, {budget} min)")
    planned = []

    if urgent:
        print("   URGENT (deadline ≤14d):")
        for days_left, entry in urgent:
            effort = get_effort_fn(entry)
            est = effort_minutes.get(effort, 90)
            name = entry.get("name", entry.get("id", "?"))
            status = entry.get("status", "?")
            marker = "!!!" if days_left <= 3 else "! "
            fits = used + est <= budget
            tag = "" if fits else " [OVER BUDGET]"
            print(f"     {marker} {name} — {days_left}d — {status} — {effort} (~{est}min){tag}")
            if fits:
                used += est
                planned.append(entry)

    if scored:
        print("   BY SCORE (jobs weighted by freshness):")
        for entry in scored:
            effort = get_effort_fn(entry)
            est = effort_minutes.get(effort, 90)
            name = entry.get("name", entry.get("id", "?"))
            status = entry.get("status", "?")
            fits = used + est <= budget
            tag = "" if fits else " [OVER BUDGET]"
            effective = plan_sort_key(entry)
            freshness_suffix = ""
            if entry.get("track") == "job":
                badge = freshness_badge_fn(entry)
                if badge:
                    freshness_suffix = f" {badge}"
            print(f"     [{effective:.1f}] {name} — {status} — {effort} (~{est}min){tag}{freshness_suffix}")
            if fits:
                used += est
                planned.append(entry)

    remaining = budget - used
    print("   ---")
    print(f"   Planned: {len(planned)} entries | ~{used} min ({used / 60:.1f}h)")
    if remaining > 15:
        print(f"   Buffer: {remaining} min remaining")
    print()

    return {"planned": len(planned), "used_minutes": used}


def section_outreach(
    entries: list[dict],
    *,
    actionable_statuses: set[str],
    get_deadline_fn,
    days_until_fn,
    get_score_fn,
    outreach_by_status: dict[str, list[str]],
) -> None:
    """Per-target outreach checklists based on status and deadline proximity."""
    actionable = [entry for entry in entries if entry.get("status") in actionable_statuses]

    def sort_key(entry: dict) -> tuple[int, float]:
        deadline_date, _deadline_type = get_deadline_fn(entry)
        if deadline_date:
            days_left = days_until_fn(deadline_date)
            if days_left >= 0:
                return (0, float(days_left))
        return (1, -get_score_fn(entry))

    actionable.sort(key=sort_key)

    print("4. OUTREACH SUGGESTIONS")
    if not actionable:
        print("   No actionable entries.")
        print()
        return

    shown = 0
    for entry in actionable:
        if shown >= 5:
            remaining = len(actionable) - shown
            if remaining > 0:
                print(f"   ... {remaining} more entries (run full standup to see all)")
            break

        status = entry.get("status", "")
        name = entry.get("name", entry.get("id", "?"))
        tips = outreach_by_status.get(status, [])
        existing = entry.get("outreach", [])
        done_types = set()
        if isinstance(existing, list):
            for outreach_item in existing:
                if isinstance(outreach_item, dict) and outreach_item.get("status") == "done":
                    done_types.add(outreach_item.get("type", ""))

        deadline_date, _deadline_type = get_deadline_fn(entry)
        deadline_str = ""
        if deadline_date:
            days_left = days_until_fn(deadline_date)
            if days_left >= 0:
                deadline_str = f" — {days_left}d to deadline"

        print(f"   {name} [{status}]{deadline_str}:")
        for tip in tips:
            print(f"     - {tip}")
        if done_types:
            print(f"     (already done: {', '.join(sorted(done_types))})")
        shown += 1

    print()


def section_practices(
    entries: list[dict],
    stale_stats: dict,
    *,
    get_deadline_fn,
    days_until_fn,
    practices_by_context: dict[str, list[str]],
) -> None:
    """Context-sensitive reminders from strategy docs."""
    tips_shown = set()

    print("5. BEST PRACTICES")

    for entry in entries:
        deadline_date, deadline_type = get_deadline_fn(entry)
        if deadline_date and deadline_type in ("hard", "fixed") and 0 <= days_until_fn(deadline_date) <= 7:
            if "pre_deadline_week" not in tips_shown:
                tips_shown.add("pre_deadline_week")
                for tip in practices_by_context["pre_deadline_week"]:
                    print(f"   - {tip}")

    has_submission = any(
        entry.get("status") in ("submitted", "acknowledged", "interview", "outcome")
        for entry in entries
    )
    if not has_submission and "no_submissions_ever" not in tips_shown:
        tips_shown.add("no_submissions_ever")
        for tip in practices_by_context["no_submissions_ever"]:
            print(f"   - {tip}")

    if stale_stats.get("stagnant", 0) > 5 and "high_stagnation" not in tips_shown:
        tips_shown.add("high_stagnation")
        for tip in practices_by_context["high_stagnation"]:
            print(f"   - {tip}")

    if "networking_cadence" not in tips_shown:
        tips_shown.add("networking_cadence")
        for tip in practices_by_context["networking_cadence"]:
            print(f"   - {tip}")

    if not tips_shown:
        print("   No context-specific tips today.")

    print()


def section_replenish(
    entries: list[dict],
    *,
    actionable_statuses: set[str],
    get_deadline_fn,
    days_until_fn,
    replenish_threshold: int,
    load_entries_fn,
    pipeline_dir_research_pool,
    get_score_fn,
) -> None:
    """Alert when actionable count drops below threshold."""
    actionable = [entry for entry in entries if entry.get("status") in actionable_statuses]
    live = []
    for entry in actionable:
        deadline_date, _deadline_type = get_deadline_fn(entry)
        if deadline_date and days_until_fn(deadline_date) < 0:
            continue
        live.append(entry)

    by_track: dict[str, int] = {}
    for entry in live:
        track = entry.get("track", "unknown")
        by_track[track] = by_track.get(track, 0) + 1

    print("6. PIPELINE REPLENISHMENT")
    print(f"   Live actionable entries: {len(live)}")

    if len(live) < replenish_threshold:
        print(f"   !! Below threshold ({replenish_threshold}). Research new perfect-fit targets.")
        print("   Focus on roles with warm paths (network_proximity >= 5).")
    else:
        print(f"   OK — pipeline lean and focused ({len(live)} entries, threshold {replenish_threshold})")

    if by_track:
        print("   By track:")
        for track, count in sorted(by_track.items(), key=lambda item: -item[1]):
            print(f"     {track}: {count}")

    desired_tracks = {"grant", "residency", "job", "fellowship", "writing"}
    missing = desired_tracks - set(by_track.keys())
    if missing:
        print(f"   Gaps: no live entries in {', '.join(sorted(missing))}")

    pool_entries = load_entries_fn(dirs=[pipeline_dir_research_pool])
    if pool_entries:
        pool_high = sum(1 for entry in pool_entries if get_score_fn(entry) >= 9.0)
        print(f"   Research pool: {len(pool_entries)} entries ({pool_high} scoring >= 9.0)")
        if len(live) < replenish_threshold and pool_high > 0:
            print("   Tip: run `python scripts/score.py --auto-qualify --dry-run` to preview top entries (threshold 9.0)")

    print()


def section_deferred(entries: list[dict], *, parse_date_fn) -> None:
    """Show entries with status=deferred and their resume dates."""
    deferred = [entry for entry in entries if entry.get("status") == "deferred"]

    print("7. DEFERRED ENTRIES")
    if not deferred:
        print("   No deferred entries.")
        print()
        return

    today = date.today()
    print(f"   {len(deferred)} entry(ies) deferred (blocked by external factors):")
    for entry in deferred:
        name = entry.get("name", entry.get("id", "?"))
        deferral = entry.get("deferral", {})
        reason = deferral.get("reason", "unknown") if isinstance(deferral, dict) else "unknown"
        resume_date_str = deferral.get("resume_date") if isinstance(deferral, dict) else None
        note = deferral.get("note", "") if isinstance(deferral, dict) else ""

        resume_info = ""
        if resume_date_str:
            resume_date = parse_date_fn(resume_date_str)
            if resume_date:
                days_delta = (resume_date - today).days
                if days_delta > 0:
                    resume_info = f" — resumes in {days_delta}d ({resume_date_str})"
                elif days_delta == 0:
                    resume_info = f" — RESUME TODAY ({resume_date_str})"
                else:
                    resume_info = f" — PAST RESUME DATE ({resume_date_str}, {abs(days_delta)}d ago)"

        print(f"     {name} [{reason}]{resume_info}")
        if note:
            print(f"       {note}")

    print()
