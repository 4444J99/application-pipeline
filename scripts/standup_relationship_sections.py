"""Follow-up and relationship standup sections."""

from __future__ import annotations

from datetime import date


def section_followup(entries: list[dict], *, parse_date_fn) -> None:
    """Show follow-up dashboard: due/overdue actions for submitted entries."""
    submitted = [entry for entry in entries if entry.get("status") in ("submitted", "acknowledged")]

    print("8. FOLLOW-UP DASHBOARD")

    if not submitted:
        print("   No submitted entries to follow up on.")
        print()
        return

    today = date.today()
    due_entries = []
    overdue_entries = []
    upcoming_entries = []

    for entry in submitted:
        entry_id = entry.get("id", "?")
        name = entry.get("name", entry_id)
        target = entry.get("target", {})
        org = target.get("organization", "?") if isinstance(target, dict) else "?"

        timeline = entry.get("timeline", {})
        submitted_date = parse_date_fn(timeline.get("submitted")) if isinstance(timeline, dict) else None
        if not submitted_date:
            continue

        days_since = (today - submitted_date).days
        existing = entry.get("follow_up", []) or []
        existing_types = {fu.get("type") for fu in existing if isinstance(fu, dict)}

        protocol = [
            {"day_range": (1, 2), "type": "connect", "action": "Connect on LinkedIn"},
            {"day_range": (7, 10), "type": "dm", "action": "First follow-up DM/email"},
            {"day_range": (14, 21), "type": "check_in", "action": "Final follow-up"},
        ]

        for step in protocol:
            if step["type"] in existing_types:
                continue
            low, high = step["day_range"]
            if days_since > high:
                overdue_entries.append(
                    {
                        "id": entry_id,
                        "name": name,
                        "org": org,
                        "days": days_since,
                        "action": step["action"],
                        "window": f"Day {low}-{high}",
                    }
                )
            elif low <= days_since <= high:
                due_entries.append(
                    {
                        "id": entry_id,
                        "name": name,
                        "org": org,
                        "days": days_since,
                        "action": step["action"],
                        "window": f"Day {low}-{high}",
                    }
                )
            else:
                upcoming_entries.append(
                    {
                        "id": entry_id,
                        "name": name,
                        "org": org,
                        "days": days_since,
                        "due_in": low - days_since,
                        "action": step["action"],
                    }
                )

    if overdue_entries:
        print(f"   OVERDUE ({len(overdue_entries)}):")
        for item in overdue_entries[:5]:
            print(f"     !!! {item['org']} — {item['name']}")
            print(f"         Day {item['days']} — {item['action']} ({item['window']})")
        if len(overdue_entries) > 5:
            print(f"     ... and {len(overdue_entries) - 5} more")

    if due_entries:
        print(f"   DUE TODAY ({len(due_entries)}):")
        for item in due_entries[:5]:
            print(f"     >> {item['org']} — {item['name']}")
            print(f"        Day {item['days']} — {item['action']}")
        if len(due_entries) > 5:
            print(f"     ... and {len(due_entries) - 5} more")

    if not overdue_entries and not due_entries:
        if upcoming_entries:
            upcoming_entries.sort(key=lambda item: item["due_in"])
            print("   No actions due today. Next up:")
            for item in upcoming_entries[:3]:
                print(f"     in {item['due_in']}d — {item['org']} — {item['action']}")
        else:
            print("   All follow-up protocols complete for current submissions.")

    total_submitted = len(submitted)
    with_followups = sum(1 for entry in submitted if entry.get("follow_up"))
    print(
        f"\n   Submitted: {total_submitted} | With follow-ups: {with_followups} | "
        f"Overdue: {len(overdue_entries)} | Due: {len(due_entries)}"
    )
    print()


def section_relationships(entries: list[dict]) -> None:
    """Relationship cultivation: top score-impact targets, today's actions, dense orgs."""
    print("RELATIONSHIPS")
    print("-" * 40)

    try:
        from score import analyze_reachability

        reachable = []
        for entry in entries:
            if entry.get("status") not in {"research", "qualified", "drafting", "staged"}:
                continue
            result = analyze_reachability(entry, entries, 9.0)
            if result["current_composite"] >= 9.0:
                continue
            if result["reachable_with"]:
                best = next(
                    scenario
                    for scenario in result["scenarios"]
                    if scenario["level"] == result["reachable_with"]
                )
                reachable.append(
                    {
                        "entry_id": result["entry_id"],
                        "composite": result["current_composite"],
                        "delta": best["delta"],
                        "need": result["reachable_with"],
                    }
                )
        reachable.sort(key=lambda item: item["delta"], reverse=True)
        if reachable:
            print("\n   TOP CULTIVATION TARGETS (by score impact):")
            for item in reachable[:5]:
                print(
                    f"     {item['entry_id']:<35s} {item['composite']:.1f} "
                    f"(+{item['delta']:.1f} with {item['need']})"
                )
        else:
            print("\n   No entries where network cultivation alone unlocks 9.0")
    except ImportError:
        print("\n   (score module not available for reachability analysis)")

    try:
        from cultivate import get_today_actions

        actions = get_today_actions(entries)
        if actions:
            print(f"\n   TODAY'S CULTIVATION ACTIONS ({len(actions)}):")
            for action in actions[:5]:
                suffix = f" -> {action['contact']}" if action["contact"] else ""
                print(f"     {action['entry_id']}: {action['action_type']} via {action['channel']}{suffix}")
    except ImportError:
        pass

    try:
        from warm_intro_audit import scan_for_organizations

        org_map = scan_for_organizations(entries)
        dense = [(org, org_entries) for org, org_entries in org_map.items() if len(org_entries) >= 3]
        dense.sort(key=lambda item: len(item[1]), reverse=True)
        if dense:
            print("\n   DENSE ORGS (3+ entries — network leverage):")
            for org, org_entries in dense[:3]:
                ids = ", ".join(entry.get("id", "?") for entry in org_entries[:3])
                print(f"     {org} ({len(org_entries)} entries): {ids}")
    except ImportError:
        pass

    print()
