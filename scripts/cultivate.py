#!/usr/bin/env python3
"""Relationship cultivation workflow — pre-submission network building.

Identifies entries where network improvement could push score >= threshold,
suggests concrete actions, and logs cultivation activity.

Usage:
    python scripts/cultivate.py --candidates        # Entries where network unlocks 9.0
    python scripts/cultivate.py --today             # Today's planned cultivation actions
    python scripts/cultivate.py --plan <entry-id>   # Cultivation plan for single entry
    python scripts/cultivate.py --log <id> --action connect --channel linkedin --contact "Name" --note "DM sent"
"""

import argparse
import sys
from datetime import date, datetime
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import (
    SIGNALS_DIR,
    atomic_write,
    load_entries,
    update_last_touched,
)
from score import analyze_reachability


def get_cultivation_candidates(entries: list[dict], all_entries: list[dict],
                               threshold: float = 9.0) -> list[dict]:
    """Entries where network improvement could push score >= threshold.

    Returns list of dicts with reachability info, sorted by gap (smallest first).
    """
    candidates = []
    for entry in entries:
        status = entry.get("status", "")
        if status not in {"research", "qualified", "drafting", "staged"}:
            continue
        result = analyze_reachability(entry, all_entries, threshold)
        if result["current_composite"] >= threshold:
            continue  # already above
        if result["reachable_with"]:
            candidates.append({
                "entry_id": result["entry_id"],
                "name": entry.get("name", result["entry_id"]),
                "status": status,
                "current_composite": result["current_composite"],
                "current_network": result["current_network"],
                "reachable_with": result["reachable_with"],
                "scenarios": result["scenarios"],
                "org": (entry.get("target") or {}).get("organization", ""),
                "application_url": (entry.get("target") or {}).get("application_url", ""),
            })
    # Sort by gap: entries closest to threshold first
    candidates.sort(key=lambda c: c["current_composite"], reverse=True)
    return candidates


def get_today_actions(entries: list[dict]) -> list[dict]:
    """Pre-submission outreach items with target_date <= today."""
    today = date.today()
    actions = []
    for entry in entries:
        outreach = entry.get("outreach") or []
        if not isinstance(outreach, list):
            continue
        entry_id = entry.get("id", "unknown")
        for o in outreach:
            if not isinstance(o, dict):
                continue
            if o.get("type") != "pre_submission":
                continue
            if o.get("status") == "done":
                continue
            target_date_str = o.get("target_date")
            if target_date_str:
                try:
                    td = date.fromisoformat(str(target_date_str).strip().strip('"'))
                    if td > today:
                        continue
                except (ValueError, TypeError):
                    pass
            actions.append({
                "entry_id": entry_id,
                "name": entry.get("name", entry_id),
                "action_type": o.get("action_type", "outreach"),
                "channel": o.get("channel", "unknown"),
                "contact": o.get("contact", ""),
                "note": o.get("note", ""),
                "target_date": target_date_str,
            })
    return actions


def suggest_actions(candidate: dict) -> list[str]:
    """Concrete suggestions with score delta for a cultivation candidate."""
    suggestions = []
    for scenario in candidate.get("scenarios", []):
        level = scenario["level"]
        delta = scenario["delta"]
        composite = scenario["composite"]
        crosses = scenario["crosses_threshold"]
        marker = " [UNLOCKS]" if crosses else ""
        if level == "acquaintance":
            suggestions.append(
                f"LinkedIn connect would move network 1->{scenario['network_score']} "
                f"(+{delta:.1f} pts -> {composite:.1f}){marker}"
            )
        elif level == "warm":
            suggestions.append(
                f"Coffee chat / DM exchange would move network -> {scenario['network_score']} "
                f"(+{delta:.1f} pts -> {composite:.1f}){marker}"
            )
        elif level == "strong":
            suggestions.append(
                f"Referral / warm intro would move network -> {scenario['network_score']} "
                f"(+{delta:.1f} pts -> {composite:.1f}){marker}"
            )
        elif level == "internal":
            suggestions.append(
                f"Internal champion would move network -> {scenario['network_score']} "
                f"(+{delta:.1f} pts -> {composite:.1f}){marker}"
            )
    return suggestions


def log_cultivation_action(entry_id: str, action_type: str, channel: str,
                           contact: str, note: str):
    """Log to entry outreach[] (type=pre_submission) + signals/outreach-log.yaml."""
    from pipeline_lib import load_entry_by_id

    filepath, entry = load_entry_by_id(entry_id)
    if not filepath:
        print(f"Entry not found: {entry_id}", file=sys.stderr)
        sys.exit(1)

    today_str = date.today().isoformat()
    now_str = datetime.now().isoformat(timespec="seconds")

    # Add to outreach[] in YAML
    content = filepath.read_text()
    outreach_entry = (
        f'\n  - type: pre_submission\n'
        f'    action_type: {action_type}\n'
        f'    channel: {channel}\n'
        f'    contact: "{contact}"\n'
        f'    note: "{note}"\n'
        f'    date: "{today_str}"\n'
        f'    status: done\n'
    )

    if "\noutreach:" in content:
        content = content.replace("\noutreach:", "\noutreach:" + outreach_entry, 1)
    else:
        content += f"\noutreach:{outreach_entry}"

    content = update_last_touched(content)
    atomic_write(filepath, content)
    print(f"Logged cultivation action for {entry_id}: {action_type} via {channel}")

    # Also append to signals/outreach-log.yaml
    log_path = SIGNALS_DIR / "outreach-log.yaml"
    SIGNALS_DIR.mkdir(parents=True, exist_ok=True)

    if log_path.exists():
        try:
            with open(log_path) as f:
                log_data = yaml.safe_load(f) or {}
        except Exception:
            log_data = {}
    else:
        log_data = {}

    log_entries = log_data.get("entries", [])
    if not isinstance(log_entries, list):
        log_entries = []
    log_entries.append({
        "entry_id": entry_id,
        "type": "pre_submission",
        "action_type": action_type,
        "channel": channel,
        "contact": contact,
        "note": note,
        "timestamp": now_str,
    })
    log_data["entries"] = log_entries

    with open(log_path, "w") as f:
        yaml.dump(log_data, f, default_flow_style=False, sort_keys=False)


def run_candidates(threshold: float = 9.0):
    """Show cultivation candidates with suggestions."""
    all_entries = load_entries()
    candidates = get_cultivation_candidates(all_entries, all_entries, threshold)

    print(f"CULTIVATION CANDIDATES (network -> score >= {threshold})")
    print("=" * 60)

    if not candidates:
        print("\nNo entries where network cultivation alone can reach threshold.")
        print("Consider lowering threshold or improving non-network dimensions.")
        return

    for c in candidates:
        org = f" @ {c['org']}" if c["org"] else ""
        print(f"\n  {c['entry_id']}{org}")
        print(f"  Score: {c['current_composite']:.1f}  Network: {c['current_network']}  "
              f"Need: {c['reachable_with']}")
        for s in suggest_actions(c):
            print(f"    -> {s}")

    print(f"\n{'=' * 60}")
    print(f"Total: {len(candidates)} candidates")


def run_plan(entry_id: str, threshold: float = 9.0):
    """Show detailed cultivation plan for a single entry."""
    all_entries = load_entries()
    entry = next((e for e in all_entries if e.get("id") == entry_id), None)
    if not entry:
        print(f"Entry not found: {entry_id}", file=sys.stderr)
        sys.exit(1)

    result = analyze_reachability(entry, all_entries, threshold)
    org = (entry.get("target") or {}).get("organization", "")

    print(f"CULTIVATION PLAN: {entry_id}")
    if org:
        print(f"Organization: {org}")
    print(f"Current score: {result['current_composite']:.1f}  Network: {result['current_network']}")
    print(f"Threshold: {threshold}")
    print()

    if result["current_composite"] >= threshold:
        print("Already above threshold — no cultivation needed.")
        return

    if not result["reachable_with"]:
        print("UNREACHABLE via network alone. Improve non-network dimensions first.")
        if result["scenarios"]:
            best = result["scenarios"][-1]
            print(f"  Best case (internal): {best['composite']:.1f} (+{best['delta']:.1f})")
        return

    print("NETWORK SCENARIOS:")
    for s in result["scenarios"]:
        marker = " <-- UNLOCKS" if s["crosses_threshold"] else ""
        print(f"  {s['level']:<15s} network={s['network_score']:>2d}  -> {s['composite']:.1f}  "
              f"(+{s['delta']:.1f}){marker}")

    print()
    print("SUGGESTED ACTIONS:")
    candidate = {
        "scenarios": result["scenarios"],
        "reachable_with": result["reachable_with"],
    }
    for s in suggest_actions(candidate):
        print(f"  {s}")

    # Check existing outreach
    outreach = entry.get("outreach") or []
    if outreach:
        print(f"\nEXISTING OUTREACH ({len(outreach)}):")
        for o in outreach:
            if isinstance(o, dict):
                print(f"  {o.get('channel', '?')} -> {o.get('contact', '?')} "
                      f"({o.get('status', '?')}) {o.get('date', '')}")

    # Check existing network info
    network = entry.get("network") or {}
    if isinstance(network, dict) and network:
        print("\nNETWORK INFO:")
        for k, v in network.items():
            print(f"  {k}: {v}")


def run_today():
    """Show today's cultivation actions."""
    all_entries = load_entries()
    actions = get_today_actions(all_entries)

    print("TODAY'S CULTIVATION ACTIONS")
    print("=" * 60)

    if not actions:
        print("\nNo pre-submission outreach actions due today.")
        return

    for a in actions:
        print(f"  {a['entry_id']}: {a['action_type']} via {a['channel']}")
        if a["contact"]:
            print(f"    Contact: {a['contact']}")
        if a["note"]:
            print(f"    Note: {a['note']}")

    print(f"\n{'=' * 60}")
    print(f"Total: {len(actions)} actions due")


def main():
    parser = argparse.ArgumentParser(description="Relationship cultivation workflow")
    parser.add_argument("--candidates", action="store_true",
                        help="Show entries where network cultivation unlocks threshold")
    parser.add_argument("--today", action="store_true",
                        help="Show today's planned cultivation actions")
    parser.add_argument("--plan", metavar="ENTRY_ID",
                        help="Generate cultivation plan for single entry")
    parser.add_argument("--log", metavar="ENTRY_ID",
                        help="Log a cultivation action for an entry")
    parser.add_argument("--action", help="Action type (connect, dm, coffee, referral)")
    parser.add_argument("--channel", help="Channel (linkedin, email, twitter, in_person)")
    parser.add_argument("--contact", help="Contact name")
    parser.add_argument("--note", help="Action note")
    parser.add_argument("--threshold", type=float, default=9.0,
                        help="Score threshold (default: 9.0)")
    args = parser.parse_args()

    if args.log:
        if not all([args.action, args.channel, args.contact]):
            parser.error("--log requires --action, --channel, and --contact")
        log_cultivation_action(args.log, args.action, args.channel,
                               args.contact, args.note or "")
    elif args.plan:
        run_plan(args.plan, args.threshold)
    elif args.today:
        run_today()
    elif args.candidates:
        run_candidates(args.threshold)
    else:
        # Default: show candidates
        run_candidates(args.threshold)


if __name__ == "__main__":
    main()
