#!/usr/bin/env python3
"""Triage automation: demote sub-threshold staged entries, resolve org-cap violations.

Designed to reduce pipeline congestion by enforcing score thresholds and
organizational caps on actionable entries.

Usage:
    python scripts/triage.py                          # Report only (dry-run)
    python scripts/triage.py --execute --yes           # Apply changes
    python scripts/triage.py --org-cap                 # Org-cap resolution only
    python scripts/triage.py --min-score 8.5           # Custom threshold
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import (
    ALL_PIPELINE_DIRS,
    COMPANY_CAP,
    get_score,
    load_entries,
    update_yaml_field,
)


def _load_entry_path(entry_id: str) -> Path | None:
    """Find the YAML file path for an entry ID."""
    for d in ALL_PIPELINE_DIRS:
        path = d / f"{entry_id}.yaml"
        if path.exists():
            return path
    return None


def triage_staged_backlog(
    entries: list[dict],
    min_score: float = 9.0,
    dry_run: bool = True,
) -> list[dict]:
    """Demote staged entries below min_score back to qualified.

    Returns list of action dicts: {id, score, action, applied}.
    """
    actions = []
    for entry in entries:
        if entry.get("status") != "staged":
            continue
        score = get_score(entry)
        if score is None or score >= min_score:
            continue
        action = {
            "id": entry.get("id", "unknown"),
            "score": score,
            "action": "demote staged → qualified",
            "applied": False,
        }
        if not dry_run:
            path = _load_entry_path(entry["id"])
            if path:
                content = path.read_text()
                content = update_yaml_field(content, "status", "qualified")
                path.write_text(content)
                action["applied"] = True
        actions.append(action)
    return actions


def triage_org_cap(
    entries: list[dict],
    cap: int = COMPANY_CAP,
    dry_run: bool = True,
) -> list[dict]:
    """For orgs exceeding cap, defer lower-scored entries.

    Keeps the highest-scored entry per org active; defers the rest.
    Returns list of action dicts: {id, org, score, action, applied}.
    """
    actionable = {"research", "qualified", "drafting", "staged", "submitted", "acknowledged", "interview"}
    org_map: dict[str, list[dict]] = {}
    for entry in entries:
        if entry.get("status") not in actionable:
            continue
        target = entry.get("target", {})
        if not isinstance(target, dict):
            continue
        org = target.get("organization", "")
        if not org:
            continue
        org_map.setdefault(org.lower(), []).append(entry)

    actions = []
    for org, org_entries in sorted(org_map.items()):
        if len(org_entries) <= cap:
            continue
        # Sort by score descending; keep top `cap`
        scored = sorted(org_entries, key=lambda e: get_score(e) or 0, reverse=True)
        to_defer = scored[cap:]
        for entry in to_defer:
            action = {
                "id": entry.get("id", "unknown"),
                "org": org,
                "score": get_score(entry),
                "action": f"defer (org-cap: {len(org_entries)} > {cap})",
                "applied": False,
            }
            if not dry_run:
                path = _load_entry_path(entry["id"])
                if path:
                    content = path.read_text()
                    content = update_yaml_field(content, "status", "deferred")
                    path.write_text(content)
                    action["applied"] = True
            actions.append(action)
    return actions


def format_triage_report(staged_actions: list[dict], cap_actions: list[dict]) -> str:
    """Format a human-readable triage report."""
    lines = ["Pipeline Triage Report", "=" * 50]

    if staged_actions:
        lines.append(f"\nStaged Backlog ({len(staged_actions)} entries below threshold):")
        for a in staged_actions:
            status = "APPLIED" if a["applied"] else "DRY-RUN"
            lines.append(f"  [{status}] {a['id']} (score {a['score']:.1f}) → {a['action']}")
    else:
        lines.append("\nStaged Backlog: all entries meet threshold.")

    if cap_actions:
        lines.append(f"\nOrg-Cap Resolution ({len(cap_actions)} entries to defer):")
        for a in cap_actions:
            status = "APPLIED" if a["applied"] else "DRY-RUN"
            lines.append(f"  [{status}] {a['id']} ({a['org']}, score {a.get('score', 'N/A')}) → {a['action']}")
    else:
        lines.append("\nOrg-Cap: no violations.")

    return "\n".join(lines)


def generate_triage_data(
    entries: list[dict],
    min_score: float = 9.0,
    cap: int = COMPANY_CAP,
    dry_run: bool = True,
) -> dict:
    """Generate structured triage data for JSON output."""
    staged = triage_staged_backlog(entries, min_score=min_score, dry_run=dry_run)
    org_cap = triage_org_cap(entries, cap=cap, dry_run=dry_run)
    return {
        "staged_demotions": staged,
        "org_cap_deferrals": org_cap,
        "summary": {
            "staged_below_threshold": len(staged),
            "org_cap_violations": len(org_cap),
            "dry_run": dry_run,
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Pipeline triage: enforce score thresholds and org caps")
    parser.add_argument("--min-score", type=float, default=9.0, help="Minimum score for staged entries (default: 9.0)")
    parser.add_argument("--org-cap", action="store_true", help="Run org-cap resolution only")
    parser.add_argument("--execute", action="store_true", help="Apply changes (default: dry-run)")
    parser.add_argument("--yes", action="store_true", help="Skip confirmation prompt")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of formatted text")
    args = parser.parse_args()

    dry_run = not args.execute
    entries = load_entries()

    if args.execute and not args.yes:
        print("This will modify pipeline YAML files. Continue? (yes/no): ", end="")
        if input().strip().lower() != "yes":
            print("Aborted.")
            sys.exit(0)

    if args.json:
        import json
        data = generate_triage_data(entries, min_score=args.min_score, dry_run=dry_run)
        print(json.dumps(data, indent=2, default=str))
        return

    if args.org_cap:
        cap_actions = triage_org_cap(entries, dry_run=dry_run)
        report = format_triage_report([], cap_actions)
    else:
        staged_actions = triage_staged_backlog(entries, min_score=args.min_score, dry_run=dry_run)
        cap_actions = triage_org_cap(entries, dry_run=dry_run)
        report = format_triage_report(staged_actions, cap_actions)

    print(report)


if __name__ == "__main__":
    main()
