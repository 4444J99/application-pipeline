#!/usr/bin/env python3
"""Block-engagement correlation — identify which blocks correlate with being read vs silence.

Cross-tabulates block usage against engagement signal (reviewed vs never read)
rather than accept/reject. This gives actionable signal much earlier in the pipeline.

Signal definition:
  engaged (read): outcome is rejected, accepted, or interview — the application was reviewed
  silence (unread): outcome is expired, or status is submitted with no resolved outcome

Classification thresholds:
  effective: engagement rate > 60% with >= 3 resolved uses
  invisible: silence rate > 80% with >= 3 resolved uses
  insufficient: < 3 resolved uses

Usage:
    python scripts/block_engagement.py              # Full report
    python scripts/block_engagement.py --effective  # Only effective blocks
    python scripts/block_engagement.py --invisible  # Only invisible blocks
    python scripts/block_engagement.py --json       # JSON output
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import ALL_PIPELINE_DIRS, load_entries

MIN_USES_FOR_CLASSIFICATION = 3
EFFECTIVE_THRESHOLD = 0.60   # engagement rate above which a block is "effective"
INVISIBLE_THRESHOLD = 0.80   # silence rate above which a block is "invisible"


def classify_engagement(entry: dict) -> str | None:
    """Classify entry engagement signal.

    Returns 'engaged', 'silence', or None (exclude/ambiguous).
    """
    outcome = entry.get("outcome")
    status = entry.get("status", "")

    if outcome in ("rejected", "accepted", "interview"):
        return "engaged"

    if outcome in ("expired",):
        return "silence"

    # submitted with no outcome → likely unread (silence)
    if status in ("submitted",) and outcome is None:
        return "silence"

    return None


def _get_blocks_used(entry: dict) -> list[str]:
    """Extract block names/paths from an entry's submission.blocks_used."""
    submission = entry.get("submission", {})
    if not isinstance(submission, dict):
        return []
    blocks = submission.get("blocks_used", {})
    if isinstance(blocks, dict):
        return list(blocks.values())
    if isinstance(blocks, list):
        return blocks
    return []


def compute_block_engagement_tabs(entries: list[dict]) -> dict:
    """Cross-tabulate block usage against engagement signal.

    Returns: {block: {engaged: int, silence: int, total: int,
                       engagement_rate: float, silence_rate: float}}
    """
    tabs: dict[str, dict] = {}

    for entry in entries:
        signal = classify_engagement(entry)
        if signal is None:
            continue

        blocks = _get_blocks_used(entry)
        for block in blocks:
            if block not in tabs:
                tabs[block] = {"engaged": 0, "silence": 0, "total": 0}
            tabs[block]["total"] += 1
            tabs[block][signal] += 1

    # Compute rates
    for block, tab in tabs.items():
        total = tab["engaged"] + tab["silence"]
        tab["engagement_rate"] = round(tab["engaged"] / total, 3) if total > 0 else 0.0
        tab["silence_rate"] = round(tab["silence"] / total, 3) if total > 0 else 0.0

    return tabs


def classify_blocks(
    tabs: dict,
    min_uses: int = MIN_USES_FOR_CLASSIFICATION,
    effective_threshold: float = EFFECTIVE_THRESHOLD,
    invisible_threshold: float = INVISIBLE_THRESHOLD,
) -> dict:
    """Classify blocks into effective, invisible, and insufficient.

    effective: engagement rate > effective_threshold with >= min_uses resolved uses
    invisible: silence rate > invisible_threshold with >= min_uses resolved uses
    insufficient: < min_uses resolved uses
    """
    effective = []
    invisible = []
    insufficient = []

    for block, tab in sorted(tabs.items()):
        resolved = tab["engaged"] + tab["silence"]

        if resolved < min_uses:
            insufficient.append({
                "block": block,
                **tab,
                "category": "insufficient",
                "reason": f"only {resolved}/{min_uses} resolved uses",
            })
            continue

        if tab["engagement_rate"] > effective_threshold:
            effective.append({
                "block": block,
                **tab,
                "category": "effective",
            })
        elif tab["silence_rate"] > invisible_threshold:
            invisible.append({
                "block": block,
                **tab,
                "category": "invisible",
            })
        else:
            # Mixed signal — include in insufficient rather than creating a "neutral" category
            insufficient.append({
                "block": block,
                **tab,
                "category": "mixed",
                "reason": (
                    f"{tab['engagement_rate']:.0%} engagement, "
                    f"{tab['silence_rate']:.0%} silence"
                ),
            })

    # Sort by rate (descending) for readability
    effective.sort(key=lambda b: b["engagement_rate"], reverse=True)
    invisible.sort(key=lambda b: b["silence_rate"], reverse=True)

    return {"effective": effective, "invisible": invisible, "insufficient": insufficient}


def format_report(classified: dict, tabs: dict) -> str:
    """Format block-engagement correlation report."""
    lines = ["Block-Engagement Correlation Report", "=" * 64]

    total_resolved = sum(t["engaged"] + t["silence"] for t in tabs.values())
    total_engaged = sum(t["engaged"] for t in tabs.values())
    total_silence = sum(t["silence"] for t in tabs.values())

    lines.append(
        f"\n  Signal pool: {total_resolved} resolved uses "
        f"({total_engaged} engaged, {total_silence} silence)"
    )
    if total_resolved < 15:
        lines.append(
            f"  DATA NOTICE: Only {total_resolved} resolved uses across all blocks."
        )
        lines.append(
            f"  Classification requires >= {MIN_USES_FOR_CLASSIFICATION} uses per block."
        )
        lines.append("  Results may be unreliable at this sample size.")

    lines.append(
        f"\nEFFECTIVE BLOCKS ({len(classified['effective'])} "
        f"— engagement rate > {EFFECTIVE_THRESHOLD:.0%} with >= {MIN_USES_FOR_CLASSIFICATION} uses):"
    )
    if classified["effective"]:
        for b in classified["effective"]:
            lines.append(
                f"  {b['block']:<45s} "
                f"{b['engagement_rate']:.0%} read  "
                f"({b['engaged']}/{b['engaged'] + b['silence']} uses)"
            )
    else:
        lines.append("  (none yet — need more resolved outcomes)")

    lines.append(
        f"\nINVISIBLE BLOCKS ({len(classified['invisible'])} "
        f"— silence rate > {INVISIBLE_THRESHOLD:.0%} with >= {MIN_USES_FOR_CLASSIFICATION} uses):"
    )
    if classified["invisible"]:
        for b in classified["invisible"]:
            lines.append(
                f"  {b['block']:<45s} "
                f"{b['silence_rate']:.0%} silence  "
                f"({b['silence']}/{b['engaged'] + b['silence']} uses)"
            )
    else:
        lines.append("  (none detected)")

    lines.append(
        f"\nINSUFFICIENT / MIXED ({len(classified['insufficient'])}):"
    )
    for b in classified["insufficient"][:10]:
        reason = b.get("reason", "")
        lines.append(f"  {b['block']:<45s} {reason} ({b['total']} uses)")
    if len(classified["insufficient"]) > 10:
        lines.append(f"  ... and {len(classified['insufficient']) - 10} more")

    lines.append("")
    lines.append("  INTERPRETATION:")
    lines.append("  effective = using this block correlates with your application being read")
    lines.append("  invisible = using this block correlates with silence (no review)")
    lines.append("  Signal: engaged = rejected/accepted/interview; silence = submitted/expired (no outcome)")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Block-engagement correlation analysis")
    parser.add_argument("--effective", action="store_true", help="Show only effective blocks")
    parser.add_argument("--invisible", action="store_true", help="Show only invisible blocks")
    parser.add_argument("--track", help="Filter to specific track (job, grant, residency, etc.)")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    entries = load_entries(dirs=ALL_PIPELINE_DIRS)
    if args.track:
        entries = [e for e in entries if e.get("track") == args.track]
        print(f"Filtered to track={args.track}: {len(entries)} entries\n")
    tabs = compute_block_engagement_tabs(entries)

    if not tabs:
        print("No block usage data found with engagement signal.")
        print("Blocks need resolved outcomes (rejected/accepted/interview/expired/submitted).")
        return

    classified = classify_blocks(tabs)

    if args.json:
        output: dict
        if args.effective:
            output = {"effective": classified["effective"]}
        elif args.invisible:
            output = {"invisible": classified["invisible"]}
        else:
            output = {
                **classified,
                "summary": {
                    "total_blocks": len(tabs),
                    "effective": len(classified["effective"]),
                    "invisible": len(classified["invisible"]),
                    "insufficient": len(classified["insufficient"]),
                },
            }
        print(json.dumps(output, indent=2, default=str))
        return

    if args.effective:
        if not classified["effective"]:
            print("No effective blocks found (need >= 3 uses with > 60% engagement rate).")
            return
        for b in classified["effective"]:
            print(
                f"  {b['block']:<45s} "
                f"{b['engagement_rate']:.0%} read  "
                f"({b['engaged']}/{b['engaged'] + b['silence']} uses)"
            )
    elif args.invisible:
        if not classified["invisible"]:
            print("No invisible blocks found (need >= 3 uses with > 80% silence rate).")
            return
        for b in classified["invisible"]:
            print(
                f"  {b['block']:<45s} "
                f"{b['silence_rate']:.0%} silence  "
                f"({b['silence']}/{b['engaged'] + b['silence']} uses)"
            )
    else:
        print(format_report(classified, tabs))


if __name__ == "__main__":
    main()
