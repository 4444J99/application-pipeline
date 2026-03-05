#!/usr/bin/env python3
"""Organization intelligence — aggregate pipeline data per organization.

Ranks organizations by composite opportunity score combining entry outcomes,
contact density, response times, and historical conversion rates.

Usage:
    python scripts/org_intelligence.py --all           # Rank all orgs
    python scripts/org_intelligence.py --org "Anthropic"  # Single org detail
    python scripts/org_intelligence.py --json          # JSON output
"""

import argparse
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import (
    SIGNALS_DIR,
    get_score,
    load_entries,
    parse_date,
)


def _load_contacts() -> list[dict]:
    """Load contacts from signals/contacts.yaml."""
    path = SIGNALS_DIR / "contacts.yaml"
    if not path.exists():
        return []
    with open(path) as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        return []
    return data.get("contacts", []) or []


def aggregate_org(org: str, entries: list[dict], contacts: list[dict]) -> dict:
    """Aggregate all pipeline data for a single organization."""
    org_lower = org.lower()

    # Filter entries for this org
    org_entries = []
    for e in entries:
        target = e.get("target", {})
        if isinstance(target, dict) and target.get("organization", "").lower() == org_lower:
            org_entries.append(e)

    # Filter contacts for this org
    org_contacts = [c for c in contacts if c.get("organization", "").lower() == org_lower]

    # Compute outcome stats
    outcomes = {"accepted": 0, "rejected": 0, "withdrawn": 0, "expired": 0, "pending": 0}
    for e in org_entries:
        outcome = e.get("outcome")
        if outcome in outcomes:
            outcomes[outcome] += 1
        else:
            outcomes["pending"] += 1

    # Score stats
    scores = [get_score(e) for e in org_entries if get_score(e) is not None]
    avg_score = sum(scores) / len(scores) if scores else 0.0

    # Response time estimation (days between submitted and outcome)
    response_days = []
    for e in org_entries:
        timeline = e.get("timeline", {})
        if isinstance(timeline, dict):
            sub = parse_date(timeline.get("submitted"))
            out = parse_date(timeline.get("outcome_date"))
            if sub and out:
                response_days.append((out - sub).days)
    avg_response = sum(response_days) / len(response_days) if response_days else None

    # Network density: contacts with interactions
    active_contacts = sum(1 for c in org_contacts if c.get("interactions"))
    total_interactions = sum(len(c.get("interactions", [])) for c in org_contacts)

    # Status distribution
    status_counts: dict[str, int] = {}
    for e in org_entries:
        s = e.get("status", "unknown")
        status_counts[s] = status_counts.get(s, 0) + 1

    return {
        "organization": org,
        "total_entries": len(org_entries),
        "total_contacts": len(org_contacts),
        "active_contacts": active_contacts,
        "total_interactions": total_interactions,
        "avg_score": round(avg_score, 2),
        "avg_response_days": round(avg_response, 1) if avg_response is not None else None,
        "outcomes": outcomes,
        "status_distribution": status_counts,
        "network_density": round(total_interactions / max(len(org_contacts), 1), 1),
        "tracks": list({e.get("track", "") for e in org_entries if e.get("track")}),
    }


def _opportunity_score(agg: dict) -> float:
    """Compute composite opportunity score for ranking."""
    score = 0.0
    # Base from avg fit score (0-10)
    score += agg.get("avg_score", 0) * 3
    # Network density bonus
    score += min(agg.get("network_density", 0), 10) * 2
    # Active contacts bonus
    score += min(agg.get("active_contacts", 0), 5) * 2
    # Outcome penalty/bonus
    outcomes = agg.get("outcomes", {})
    score += outcomes.get("accepted", 0) * 10
    score -= outcomes.get("rejected", 0) * 3
    # Fast response bonus
    avg_resp = agg.get("avg_response_days")
    if avg_resp is not None and avg_resp < 14:
        score += 5
    return round(score, 1)


def rank_orgs(entries: list[dict], contacts: list[dict]) -> list[dict]:
    """Aggregate and rank all organizations by composite opportunity score."""
    orgs: set[str] = set()
    for e in entries:
        target = e.get("target", {})
        if isinstance(target, dict):
            org = target.get("organization", "")
            if org:
                orgs.add(org)

    aggregated = []
    for org in sorted(orgs):
        agg = aggregate_org(org, entries, contacts)
        agg["opportunity_score"] = _opportunity_score(agg)
        aggregated.append(agg)

    return sorted(aggregated, key=lambda x: x["opportunity_score"], reverse=True)


def format_org_detail(agg: dict) -> str:
    """Format a single org's aggregated data."""
    lines = [f"Organization: {agg['organization']}", "=" * 50]
    lines.append(f"  Entries:          {agg['total_entries']}")
    lines.append(f"  Avg score:        {agg['avg_score']:.1f}")
    lines.append(f"  Contacts:         {agg['total_contacts']} ({agg['active_contacts']} active)")
    lines.append(f"  Interactions:     {agg['total_interactions']}")
    lines.append(f"  Network density:  {agg['network_density']:.1f}")
    if agg["avg_response_days"] is not None:
        lines.append(f"  Avg response:     {agg['avg_response_days']:.0f} days")
    lines.append(f"  Tracks:           {', '.join(agg['tracks']) if agg['tracks'] else '(none)'}")
    lines.append("\n  Outcomes:")
    for outcome, count in agg.get("outcomes", {}).items():
        if count > 0:
            lines.append(f"    {outcome:<15s} {count}")
    lines.append("\n  Status:")
    for status, count in agg.get("status_distribution", {}).items():
        lines.append(f"    {status:<20s} {count}")
    if "opportunity_score" in agg:
        lines.append(f"\n  Opportunity score: {agg['opportunity_score']:.1f}")
    return "\n".join(lines)


def format_rankings(ranked: list[dict], top_n: int = 20) -> str:
    """Format org rankings table."""
    lines = ["Organization Rankings", "=" * 80]
    lines.append(f"  {'Rank':<5s} {'Organization':<35s} {'Score':<8s} {'Entries':<8s} {'Contacts':<10s} {'OppScore'}")
    lines.append("  " + "-" * 78)
    for i, agg in enumerate(ranked[:top_n], 1):
        lines.append(
            f"  {i:<5d} {agg['organization']:<35s} "
            f"{agg['avg_score']:>5.1f}   {agg['total_entries']:>5d}    "
            f"{agg['total_contacts']:>5d}     {agg['opportunity_score']:>6.1f}"
        )
    if len(ranked) > top_n:
        lines.append(f"\n  ... and {len(ranked) - top_n} more organizations")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Organization intelligence aggregation")
    parser.add_argument("--all", action="store_true", help="Rank all organizations")
    parser.add_argument("--org", metavar="NAME", help="Show detail for a specific organization")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--top", type=int, default=20, help="Number of top orgs to show (default: 20)")
    args = parser.parse_args()

    entries = load_entries()
    contacts = _load_contacts()

    if args.org:
        agg = aggregate_org(args.org, entries, contacts)
        agg["opportunity_score"] = _opportunity_score(agg)
        if args.json:
            print(json.dumps(agg, indent=2, default=str))
        else:
            print(format_org_detail(agg))
        return

    ranked = rank_orgs(entries, contacts)
    if args.json:
        print(json.dumps(ranked, indent=2, default=str))
    else:
        print(format_rankings(ranked, top_n=args.top))


if __name__ == "__main__":
    main()
