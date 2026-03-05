#!/usr/bin/env python3
"""Warm intro audit — systematically identifies warm referral paths in the pipeline.

The 8x referral multiplier is the single highest-leverage channel for applications.
This script audits submitted and active entries to find warm intro opportunities
by analyzing organization density, existing contacts, and referral candidates.

Usage:
    python scripts/warm_intro_audit.py            # Show audit report
    python scripts/warm_intro_audit.py --save      # Save report to signals/
    python scripts/warm_intro_audit.py --json      # JSON output
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import (
    ALL_PIPELINE_DIRS,
    SIGNALS_DIR,
    load_entries,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


def _get_org(entry: dict) -> str:
    """Extract organization name from entry, normalized to lowercase."""
    target = entry.get("target", {})
    org = target.get("organization", "")
    return (org or "").strip().lower()


def _get_channel(entry: dict) -> str:
    """Extract submission channel from entry."""
    return entry.get("channel", entry.get("source", ""))


def _has_contacts(entry: dict) -> bool:
    """Check if entry has any follow-up contacts populated."""
    follow_up = entry.get("follow_up")
    if not follow_up:
        return False
    if isinstance(follow_up, list):
        return len(follow_up) > 0
    return False


def _get_contacts(entry: dict) -> list[dict]:
    """Get follow-up contact entries."""
    follow_up = entry.get("follow_up")
    if isinstance(follow_up, list):
        return follow_up
    return []


def _has_response(entry: dict) -> bool:
    """Check if entry has received any response."""
    conversion = entry.get("conversion", {})
    return bool(conversion.get("response_received"))


def scan_submitted_for_contacts(entries: list[dict]) -> list[dict]:
    """Find submitted entries with existing contacts or responses.

    These represent established connections that could become warm intros.
    """
    results = []
    submitted = [e for e in entries if e.get("status") in ("submitted", "acknowledged", "interview")]
    for entry in submitted:
        contacts = _get_contacts(entry)
        has_resp = _has_response(entry)
        if contacts or has_resp:
            results.append({
                "id": entry.get("id", "unknown"),
                "organization": _get_org(entry),
                "contact_count": len(contacts),
                "has_response": has_resp,
                "status": entry.get("status"),
            })
    return results


def scan_for_organizations(entries: list[dict]) -> dict[str, list[dict]]:
    """Group entries by organization, filtering to orgs with multiple entries.

    Companies with multiple entries = higher network density = better warm intro potential.
    """
    org_map = defaultdict(list)
    for entry in entries:
        org = _get_org(entry)
        if org:
            org_map[org].append({
                "id": entry.get("id", "unknown"),
                "status": entry.get("status", "unknown"),
                "track": entry.get("track", "unknown"),
            })

    # Only keep orgs with 2+ entries (network density signal)
    return {org: items for org, items in sorted(org_map.items()) if len(items) >= 2}


def identify_referral_candidates(entries: list[dict]) -> list[dict]:
    """Find entries where channel is direct/cold but org has network density.

    These are prime candidates for warm intro conversion.
    """
    # Build org density map
    org_counts = defaultdict(int)
    org_with_contacts = set()
    for entry in entries:
        org = _get_org(entry)
        if org:
            org_counts[org] += 1
            if _has_contacts(entry) or _has_response(entry):
                org_with_contacts.add(org)

    candidates = []
    for entry in entries:
        org = _get_org(entry)
        status = entry.get("status", "")
        if not org:
            continue
        # Look for active/qualified entries at orgs where we have existing connections
        if status in ("qualified", "drafting", "staged", "research") and org in org_with_contacts:
            candidates.append({
                "id": entry.get("id", "unknown"),
                "organization": org,
                "status": status,
                "org_entry_count": org_counts[org],
                "reason": "Org has existing contacts from other applications",
            })
        # High-density orgs with direct channel = warm intro possible
        elif status in ("qualified", "drafting", "staged") and org_counts[org] >= 3:
            candidates.append({
                "id": entry.get("id", "unknown"),
                "organization": org,
                "status": status,
                "org_entry_count": org_counts[org],
                "reason": f"High org density ({org_counts[org]} entries) — likely has warm paths",
            })

    return candidates


def build_outreach_queue(
    referral_candidates: list[dict],
    *,
    assignee: str = "4jp",
    limit: int = 5,
) -> list[dict]:
    """Build top-N warm intro outreach queue with owner/date/action fields."""
    if not referral_candidates:
        return []

    status_priority = {"staged": 4, "drafting": 3, "qualified": 2, "research": 1}
    by_org: dict[str, dict] = {}
    for candidate in referral_candidates:
        org = (candidate.get("organization") or "").strip().lower()
        if not org:
            continue
        current = by_org.get(org)
        rank = (
            int(candidate.get("org_entry_count", 0)),
            status_priority.get(candidate.get("status", ""), 0),
        )
        if current is None:
            by_org[org] = dict(candidate)
            by_org[org]["_rank"] = rank
            continue
        if rank > current.get("_rank", (0, 0)):
            merged = dict(candidate)
            merged["_rank"] = rank
            by_org[org] = merged

    ordered = sorted(
        by_org.values(),
        key=lambda item: (
            item.get("_rank", (0, 0))[0],
            item.get("_rank", (0, 0))[1],
            item.get("organization", ""),
        ),
        reverse=True,
    )

    due_date = (date.today() + timedelta(days=2)).isoformat()
    queue = []
    for candidate in ordered[:limit]:
        reason = candidate.get("reason", "")
        if "existing contacts" in reason.lower():
            next_action = "Request intro from existing contact; send warm outreach in 24h."
        else:
            next_action = "Research referral path and send intro request."
        queue.append(
            {
                "organization": candidate.get("organization"),
                "entry_id": candidate.get("id"),
                "status": candidate.get("status"),
                "org_entry_count": int(candidate.get("org_entry_count", 0)),
                "assignee": assignee,
                "due_date": due_date,
                "next_action": next_action,
            }
        )
    return queue


def generate_audit_report(entries: list[dict]) -> dict:
    """Generate comprehensive warm intro audit report."""
    contact_entries = scan_submitted_for_contacts(entries)
    dense_orgs = scan_for_organizations(entries)
    referral_candidates = identify_referral_candidates(entries)
    outreach_queue = build_outreach_queue(referral_candidates)

    submitted = [e for e in entries if e.get("status") in ("submitted", "acknowledged", "interview")]
    active = [e for e in entries if e.get("status") in ("qualified", "drafting", "staged")]

    # Count warm vs cold paths
    with_contacts = len(contact_entries)
    total_submitted = len(submitted)
    warm_pct = round(with_contacts / total_submitted * 100) if total_submitted > 0 else 0

    return {
        "generated": str(date.today()),
        "summary": {
            "total_submitted": total_submitted,
            "total_active": len(active),
            "entries_with_contacts": with_contacts,
            "warm_path_pct": warm_pct,
            "dense_organizations": len(dense_orgs),
            "referral_candidates": len(referral_candidates),
            "outreach_queue": len(outreach_queue),
        },
        "contact_entries": contact_entries,
        "dense_organizations": {
            org: {"count": len(items), "entries": items}
            for org, items in dense_orgs.items()
        },
        "referral_candidates": referral_candidates,
        "outreach_queue": outreach_queue,
        "recommendations": _generate_recommendations(contact_entries, dense_orgs, referral_candidates),
    }


def _generate_recommendations(contact_entries, dense_orgs, referral_candidates) -> list[str]:
    """Generate actionable recommendations from audit data."""
    recs = []

    if not contact_entries:
        recs.append("No contacts on submitted entries — prioritize LinkedIn research for top-3 orgs")
    else:
        recs.append(f"{len(contact_entries)} entries have contacts — follow up on stale connections")

    if dense_orgs:
        top_orgs = sorted(dense_orgs.items(), key=lambda x: len(x[1]), reverse=True)[:3]
        org_names = [org.title() for org, _ in top_orgs]
        recs.append(f"Highest org density: {', '.join(org_names)} — research internal referrals")

    if referral_candidates:
        recs.append(f"{len(referral_candidates)} active entries could convert to warm intros")

    recs.append("8x referral multiplier: 80% of effort should go to warm paths")

    return recs


def display_audit(report: dict) -> None:
    """Print formatted audit report to stdout."""
    s = report["summary"]

    print("WARM INTRO AUDIT")
    print("=" * 60)
    print()
    print(f"  Generated: {report['generated']}")
    print()
    print(f"  Submitted entries:      {s['total_submitted']}")
    print(f"  Active entries:         {s['total_active']}")
    print(f"  With contacts:          {s['entries_with_contacts']} ({s['warm_path_pct']}%)")
    print(f"  Dense organizations:    {s['dense_organizations']}")
    print(f"  Referral candidates:    {s['referral_candidates']}")
    print(f"  Outreach queue:         {s['outreach_queue']}")
    print()

    # Contact entries
    if report["contact_entries"]:
        print("  ENTRIES WITH EXISTING CONTACTS")
        print(f"  {'-' * 40}")
        for ce in report["contact_entries"]:
            resp = " (responded)" if ce["has_response"] else ""
            print(f"    {ce['id']:<45s} [{ce['organization']}] {ce['contact_count']} contacts{resp}")
        print()

    # Dense orgs
    if report["dense_organizations"]:
        print("  HIGH-DENSITY ORGANIZATIONS")
        print(f"  {'-' * 40}")
        for org, data in report["dense_organizations"].items():
            print(f"    {org.title():<30s} {data['count']} entries")
            for e in data["entries"]:
                print(f"      - {e['id']} ({e['status']})")
        print()

    # Referral candidates
    if report["referral_candidates"]:
        print("  REFERRAL CANDIDATES (cold → warm conversion)")
        print(f"  {'-' * 40}")
        for rc in report["referral_candidates"]:
            print(f"    {rc['id']:<45s} {rc['reason']}")
        print()

    if report["outreach_queue"]:
        print("  TOP OUTREACH QUEUE")
        print(f"  {'-' * 40}")
        for item in report["outreach_queue"]:
            print(
                f"    {item['organization']:<25s} {item['entry_id']} "
                f"(owner={item['assignee']}, due={item['due_date']})"
            )
            print(f"      next: {item['next_action']}")
        print()

    # Recommendations
    print("  RECOMMENDATIONS")
    print(f"  {'-' * 40}")
    for i, rec in enumerate(report["recommendations"], 1):
        print(f"    {i}. {rec}")
    print()


def save_audit(report: dict) -> Path:
    """Save audit report to signals/warm-intro-audit.md."""
    SIGNALS_DIR.mkdir(parents=True, exist_ok=True)
    out = SIGNALS_DIR / "warm-intro-audit.md"

    s = report["summary"]
    lines = [
        "# Warm Intro Audit",
        "",
        f"Generated: {report['generated']}",
        "",
        "## Summary",
        "",
        f"- Submitted entries: {s['total_submitted']}",
        f"- Active entries: {s['total_active']}",
        f"- With contacts: {s['entries_with_contacts']} ({s['warm_path_pct']}%)",
        f"- Dense organizations: {s['dense_organizations']}",
        f"- Referral candidates: {s['referral_candidates']}",
        f"- Outreach queue: {s['outreach_queue']}",
        "",
        "## Recommendations",
        "",
    ]
    for i, rec in enumerate(report["recommendations"], 1):
        lines.append(f"{i}. {rec}")

    lines.append("")

    if report["dense_organizations"]:
        lines.append("## High-Density Organizations")
        lines.append("")
        for org, data in report["dense_organizations"].items():
            lines.append(f"### {org.title()} ({data['count']} entries)")
            for e in data["entries"]:
                lines.append(f"- {e['id']} ({e['status']})")
            lines.append("")

    if report["referral_candidates"]:
        lines.append("## Referral Candidates")
        lines.append("")
        for rc in report["referral_candidates"]:
            lines.append(f"- **{rc['id']}** — {rc['reason']}")
        lines.append("")

    if report["outreach_queue"]:
        lines.append("## Outreach Queue")
        lines.append("")
        for item in report["outreach_queue"]:
            lines.append(
                f"- **{item['organization']}** (`{item['entry_id']}`): owner `{item['assignee']}`, "
                f"due `{item['due_date']}` — {item['next_action']}"
            )
        lines.append("")

    out.write_text("\n".join(lines))
    return out


def main():
    parser = argparse.ArgumentParser(
        description="Warm intro audit — identify warm referral paths in the pipeline"
    )
    parser.add_argument("--save", action="store_true",
                        help="Save report to signals/warm-intro-audit.md")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON")
    args = parser.parse_args()

    entries = load_entries(ALL_PIPELINE_DIRS)
    report = generate_audit_report(entries)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        display_audit(report)

    if args.save:
        out = save_audit(report)
        print(f"  Saved to: {out}")


if __name__ == "__main__":
    main()
