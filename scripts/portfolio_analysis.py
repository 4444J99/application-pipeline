#!/usr/bin/env python3
"""Portfolio analysis engine: cross-pipeline insights for strategic decisions.

Queries pipeline data to answer:
- Which blocks appear in accepted applications?
- What identity position has the highest conversion rate?
- Which channels perform best?
- Do variant V2 applications convert higher than V1?

Usage:
    python scripts/portfolio_analysis.py                  # Full analysis
    python scripts/portfolio_analysis.py --query blocks   # Block effectiveness
    python scripts/portfolio_analysis.py --query position # Position conversion
    python scripts/portfolio_analysis.py --query channel  # Channel performance
    python scripts/portfolio_analysis.py --query variants # Variant comparison
    python scripts/portfolio_analysis.py --json           # JSON output
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import ALL_PIPELINE_DIRS, PIPELINE_DIR_CLOSED, load_entries


def _submitted_entries(entries: list[dict]) -> list[dict]:
    """Filter to entries that reached submitted or beyond."""
    return [
        e for e in entries
        if e.get("status") in ("submitted", "acknowledged", "interview", "outcome")
    ]


def query_blocks(entries: list[dict]) -> dict:
    """Which blocks appear in accepted vs rejected applications?"""
    submitted = _submitted_entries(entries)
    block_outcomes: dict[str, dict] = defaultdict(lambda: {"accepted": 0, "rejected": 0, "total": 0})

    for entry in submitted:
        outcome = entry.get("outcome")
        blocks_used = (entry.get("submission") or {}).get("blocks_used", {})
        if not isinstance(blocks_used, dict):
            continue
        for block_path in blocks_used.values():
            if isinstance(block_path, str):
                block_outcomes[block_path]["total"] += 1
                if outcome == "accepted":
                    block_outcomes[block_path]["accepted"] += 1
                elif outcome == "rejected":
                    block_outcomes[block_path]["rejected"] += 1

    results = []
    for block, data in block_outcomes.items():
        rate = (data["accepted"] / data["total"] * 100) if data["total"] > 0 else 0
        results.append({"block": block, "rate": round(rate, 1), **data})
    return {"blocks": sorted(results, key=lambda x: -x["rate"])}


def query_position(entries: list[dict]) -> dict:
    """What identity position has the highest conversion rate?"""
    submitted = _submitted_entries(entries)
    pos_outcomes: dict[str, dict] = defaultdict(lambda: {"accepted": 0, "rejected": 0, "total": 0})

    for entry in submitted:
        outcome = entry.get("outcome")
        position = (entry.get("fit") or {}).get("identity_position", "unknown")
        pos_outcomes[position]["total"] += 1
        if outcome == "accepted":
            pos_outcomes[position]["accepted"] += 1
        elif outcome == "rejected":
            pos_outcomes[position]["rejected"] += 1

    results = []
    for pos, data in pos_outcomes.items():
        rate = (data["accepted"] / data["total"] * 100) if data["total"] > 0 else 0
        results.append({"position": pos, "rate": round(rate, 1), **data})
    return {"positions": sorted(results, key=lambda x: -x["rate"])}


def query_channel(entries: list[dict]) -> dict:
    """Which channels (portals) perform best?"""
    submitted = _submitted_entries(entries)
    ch_outcomes: dict[str, dict] = defaultdict(lambda: {"accepted": 0, "rejected": 0, "total": 0})

    for entry in submitted:
        outcome = entry.get("outcome")
        portal = (entry.get("target") or {}).get("portal", "unknown")
        ch_outcomes[portal]["total"] += 1
        if outcome == "accepted":
            ch_outcomes[portal]["accepted"] += 1
        elif outcome == "rejected":
            ch_outcomes[portal]["rejected"] += 1

    results = []
    for ch, data in ch_outcomes.items():
        rate = (data["accepted"] / data["total"] * 100) if data["total"] > 0 else 0
        results.append({"channel": ch, "rate": round(rate, 1), **data})
    return {"channels": sorted(results, key=lambda x: -x["rate"])}


def query_variants(entries: list[dict]) -> dict:
    """Do applications using different variant versions convert differently?"""
    submitted = _submitted_entries(entries)
    var_outcomes: dict[str, dict] = defaultdict(lambda: {"accepted": 0, "rejected": 0, "total": 0})

    for entry in submitted:
        outcome = entry.get("outcome")
        variant_ids = (entry.get("submission") or {}).get("variant_ids", {})
        if not isinstance(variant_ids, dict):
            continue
        cl_ref = variant_ids.get("cover_letter", "")
        if not cl_ref:
            var_outcomes["no_cover_letter"]["total"] += 1
            if outcome == "accepted":
                var_outcomes["no_cover_letter"]["accepted"] += 1
            elif outcome == "rejected":
                var_outcomes["no_cover_letter"]["rejected"] += 1
            continue

        # Classify by variant version or type
        if "-v2" in cl_ref or "-alchemized" in cl_ref:
            key = "v2_or_alchemized"
        elif "-v1" in cl_ref:
            key = "v1"
        else:
            key = "other"
        var_outcomes[key]["total"] += 1
        if outcome == "accepted":
            var_outcomes[key]["accepted"] += 1
        elif outcome == "rejected":
            var_outcomes[key]["rejected"] += 1

    results = []
    for var, data in var_outcomes.items():
        rate = (data["accepted"] / data["total"] * 100) if data["total"] > 0 else 0
        results.append({"variant_type": var, "rate": round(rate, 1), **data})
    return {"variants": sorted(results, key=lambda x: -x["rate"])}


def print_section(title: str, data: dict) -> None:
    """Print a single analysis section."""
    print(f"\n{title}")
    print("=" * 60)
    for key, items in data.items():
        if not items:
            print("  No data available.")
            continue
        for item in items:
            label_key = [k for k in item if k not in ("accepted", "rejected", "total", "rate")][0]
            print(f"  {item[label_key]:<30s}  {item['total']:>3d} submitted  "
                  f"{item['accepted']:>3d} accepted  ({item['rate']}%)")


def main():
    parser = argparse.ArgumentParser(description="Portfolio analysis engine")
    parser.add_argument("--query", choices=["blocks", "position", "channel", "variants"],
                        help="Run a specific query")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    dirs = list(ALL_PIPELINE_DIRS) + [PIPELINE_DIR_CLOSED]
    entries = load_entries(dirs=dirs)

    queries = {
        "blocks": ("Block Effectiveness", query_blocks),
        "position": ("Identity Position Conversion", query_position),
        "channel": ("Channel Performance", query_channel),
        "variants": ("Variant Comparison", query_variants),
    }

    if args.query:
        title, fn = queries[args.query]
        result = fn(entries)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print_section(title, result)
    else:
        all_results = {}
        for key, (title, fn) in queries.items():
            result = fn(entries)
            all_results[key] = result
            if not args.json:
                print_section(title, result)

        if args.json:
            print(json.dumps(all_results, indent=2))


if __name__ == "__main__":
    main()
