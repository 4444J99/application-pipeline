#!/usr/bin/env python3
"""Block-outcome correlation — identify which blocks correlate with success.

Cross-tabulates block usage against submission outcomes to classify blocks
as golden (correlated with acceptance), neutral, or toxic (correlated with
rejection).

Usage:
    python scripts/block_outcomes.py             # Full report
    python scripts/block_outcomes.py --golden    # Only golden blocks
    python scripts/block_outcomes.py --toxic     # Only toxic blocks
    python scripts/block_outcomes.py --json      # JSON output
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import load_entries


def _get_blocks_used(entry: dict) -> list[str]:
    """Extract block paths from an entry's submission.blocks_used."""
    submission = entry.get("submission", {})
    if not isinstance(submission, dict):
        return []
    blocks = submission.get("blocks_used", {})
    if isinstance(blocks, dict):
        return list(blocks.values())
    if isinstance(blocks, list):
        return blocks
    return []


def compute_block_cross_tabs(entries: list[dict]) -> dict:
    """Cross-tabulate block usage against outcomes.

    Returns: {block_path: {used: int, accepted: int, rejected: int, pending: int,
              position: {pos: count}, portal: {portal: count}}}
    """
    resolved_entries = [
        e for e in entries
        if e.get("outcome") in {"accepted", "rejected"} or e.get("status") == "submitted"
    ]

    cross_tabs: dict[str, dict] = {}
    for entry in resolved_entries:
        blocks = _get_blocks_used(entry)
        outcome = entry.get("outcome")
        position = (entry.get("fit", {}) or {}).get("identity_position", "unknown")
        portal = (entry.get("target", {}) or {}).get("portal", "unknown")

        for block in blocks:
            if block not in cross_tabs:
                cross_tabs[block] = {
                    "used": 0, "accepted": 0, "rejected": 0, "pending": 0,
                    "position": {}, "portal": {},
                }
            tab = cross_tabs[block]
            tab["used"] += 1
            if outcome == "accepted":
                tab["accepted"] += 1
            elif outcome == "rejected":
                tab["rejected"] += 1
            else:
                tab["pending"] += 1
            tab["position"][position] = tab["position"].get(position, 0) + 1
            tab["portal"][portal] = tab["portal"].get(portal, 0) + 1

    return cross_tabs


def classify_blocks(cross_tabs: dict) -> dict:
    """Classify blocks into golden/neutral/toxic based on acceptance rate.

    Golden: acceptance rate > 50% with >= 2 uses
    Toxic: rejection rate > 75% with >= 2 uses
    Neutral: everything else
    """
    golden = []
    neutral = []
    toxic = []

    for block, tab in sorted(cross_tabs.items()):
        resolved = tab["accepted"] + tab["rejected"]
        if resolved < 2:
            neutral.append({"block": block, **tab, "category": "neutral", "reason": "insufficient data"})
            continue

        accept_rate = tab["accepted"] / resolved
        reject_rate = tab["rejected"] / resolved

        if accept_rate > 0.5:
            golden.append({"block": block, **tab, "category": "golden", "accept_rate": round(accept_rate, 2)})
        elif reject_rate > 0.75:
            toxic.append({"block": block, **tab, "category": "toxic", "reject_rate": round(reject_rate, 2)})
        else:
            neutral.append({"block": block, **tab, "category": "neutral",
                           "accept_rate": round(accept_rate, 2), "reject_rate": round(reject_rate, 2)})

    return {"golden": golden, "neutral": neutral, "toxic": toxic}


def format_block_report(classified: dict) -> str:
    """Format block-outcome correlation report."""
    lines = ["Block-Outcome Correlation Report", "=" * 60]

    lines.append(f"\nGOLDEN BLOCKS ({len(classified['golden'])} — correlated with acceptance):")
    if classified["golden"]:
        for b in classified["golden"]:
            lines.append(f"  {b['block']:<45s} {b['accept_rate']:.0%} accept ({b['used']} uses)")
    else:
        lines.append("  (none yet — need more resolved outcomes)")

    lines.append(f"\nTOXIC BLOCKS ({len(classified['toxic'])} — correlated with rejection):")
    if classified["toxic"]:
        for b in classified["toxic"]:
            lines.append(f"  {b['block']:<45s} {b['reject_rate']:.0%} reject ({b['used']} uses)")
    else:
        lines.append("  (none detected)")

    lines.append(f"\nNEUTRAL BLOCKS ({len(classified['neutral'])}):")
    for b in classified["neutral"][:10]:
        reason = b.get("reason", f"{b.get('accept_rate', 0):.0%} accept")
        lines.append(f"  {b['block']:<45s} {reason} ({b['used']} uses)")
    if len(classified["neutral"]) > 10:
        lines.append(f"  ... and {len(classified['neutral']) - 10} more")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Block-outcome correlation analysis")
    parser.add_argument("--golden", action="store_true", help="Show only golden blocks")
    parser.add_argument("--toxic", action="store_true", help="Show only toxic blocks")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    entries = load_entries()
    cross_tabs = compute_block_cross_tabs(entries)
    classified = classify_blocks(cross_tabs)

    if args.json:
        if args.golden:
            print(json.dumps(classified["golden"], indent=2, default=str))
        elif args.toxic:
            print(json.dumps(classified["toxic"], indent=2, default=str))
        else:
            print(json.dumps(classified, indent=2, default=str))
        return

    if args.golden:
        for b in classified["golden"]:
            print(f"  {b['block']:<45s} {b['accept_rate']:.0%} accept ({b['used']} uses)")
    elif args.toxic:
        for b in classified["toxic"]:
            print(f"  {b['block']:<45s} {b['reject_rate']:.0%} reject ({b['used']} uses)")
    else:
        print(format_block_report(classified))


if __name__ == "__main__":
    main()
