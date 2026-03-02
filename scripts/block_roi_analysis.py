#!/usr/bin/env python3
"""Block ROI analysis: acceptance rate per narrative block.

Calculates which blocks appear in accepted vs rejected applications,
providing data-driven guidance for block selection in future submissions.

Usage:
    python scripts/block_roi_analysis.py                 # Full ROI report
    python scripts/block_roi_analysis.py --top 10        # Top 10 blocks by ROI
    python scripts/block_roi_analysis.py --json          # JSON output for dashboards
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import ALL_PIPELINE_DIRS, PIPELINE_DIR_CLOSED, load_entries


def gather_block_outcomes(entries: list[dict]) -> dict[str, dict]:
    """Map block paths to their outcome counts.

    Returns: {block_path: {"submitted": N, "accepted": N, "rejected": N, "interview": N}}
    """
    blocks: dict[str, dict] = defaultdict(lambda: {
        "submitted": 0, "accepted": 0, "rejected": 0, "interview": 0, "pending": 0,
    })

    for entry in entries:
        status = entry.get("status", "")
        outcome = entry.get("outcome")
        submission = entry.get("submission", {})
        if not isinstance(submission, dict):
            continue
        blocks_used = submission.get("blocks_used", {})
        if not isinstance(blocks_used, dict):
            continue

        # Only count entries that have been submitted
        if status not in ("submitted", "acknowledged", "interview", "outcome"):
            continue

        for slot, block_path in blocks_used.items():
            if not isinstance(block_path, str):
                continue
            blocks[block_path]["submitted"] += 1
            if outcome == "accepted":
                blocks[block_path]["accepted"] += 1
            elif outcome == "rejected":
                blocks[block_path]["rejected"] += 1
            elif status == "interview":
                blocks[block_path]["interview"] += 1
            else:
                blocks[block_path]["pending"] += 1

    return dict(blocks)


def calculate_roi(block_data: dict[str, dict]) -> list[dict]:
    """Calculate ROI for each block, sorted by acceptance rate."""
    results = []
    for block_path, counts in block_data.items():
        submitted = counts["submitted"]
        accepted = counts["accepted"]
        roi = (accepted / submitted * 100) if submitted > 0 else 0.0
        interview_rate = ((counts["interview"] + accepted) / submitted * 100) if submitted > 0 else 0.0

        results.append({
            "block": block_path,
            "submitted": submitted,
            "accepted": accepted,
            "rejected": counts["rejected"],
            "interview": counts["interview"],
            "pending": counts["pending"],
            "acceptance_rate": round(roi, 1),
            "interview_plus_rate": round(interview_rate, 1),
        })

    return sorted(results, key=lambda x: (-x["acceptance_rate"], -x["submitted"]))


def print_report(results: list[dict], top_n: int | None = None) -> None:
    """Print block ROI report."""
    if not results:
        print("No block usage data found in submitted entries.")
        return

    display = results[:top_n] if top_n else results

    print("Block ROI Analysis")
    print("=" * 80)
    print(f"{'Block':<40s} {'Sub':>4s} {'Acc':>4s} {'Rej':>4s} {'Int':>4s} {'ROI':>6s} {'Int+':>6s}")
    print("-" * 80)

    for r in display:
        block_name = r["block"]
        if len(block_name) > 38:
            block_name = "..." + block_name[-35:]
        print(f"{block_name:<40s} {r['submitted']:>4d} {r['accepted']:>4d} "
              f"{r['rejected']:>4d} {r['interview']:>4d} "
              f"{r['acceptance_rate']:>5.1f}% {r['interview_plus_rate']:>5.1f}%")

    total_sub = sum(r["submitted"] for r in results)
    total_acc = sum(r["accepted"] for r in results)
    print("-" * 80)
    print(f"{'TOTAL':<40s} {total_sub:>4d} {total_acc:>4d}")
    print(f"\nUnique blocks used: {len(results)}")
    if total_sub:
        print(f"Overall block-weighted acceptance: {total_acc / total_sub * 100:.1f}%")


def main():
    parser = argparse.ArgumentParser(description="Block ROI analysis")
    parser.add_argument("--top", type=int, help="Show top N blocks")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    dirs = list(ALL_PIPELINE_DIRS) + [PIPELINE_DIR_CLOSED]
    entries = load_entries(dirs=dirs)
    block_data = gather_block_outcomes(entries)
    results = calculate_roi(block_data)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print_report(results, top_n=args.top)


if __name__ == "__main__":
    main()
