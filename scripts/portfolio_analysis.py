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


def query_network(entries: list[dict]) -> dict:
    """Network proximity score distribution, avg by track/position, acceptance rate by score."""
    from collections import defaultdict

    submitted = _submitted_entries(entries)

    # Distribution of network_proximity scores
    score_dist: dict[int, int] = defaultdict(int)
    # Track averages
    track_sums: dict[str, list[int]] = defaultdict(list)
    # Position averages
    position_sums: dict[str, list[int]] = defaultdict(list)
    # Acceptance rate by network score
    network_outcomes: dict[int, dict] = defaultdict(lambda: {"accepted": 0, "rejected": 0, "total": 0})

    for entry in entries:
        fit = entry.get("fit", {})
        if not isinstance(fit, dict):
            continue
        dims = fit.get("dimensions", {})
        if not isinstance(dims, dict):
            continue
        net_score = dims.get("network_proximity")
        if net_score is None:
            continue
        net_score = int(net_score)
        score_dist[net_score] += 1
        track = entry.get("track", "unknown")
        track_sums[track].append(net_score)
        position = fit.get("identity_position", "unknown")
        position_sums[position].append(net_score)

    for entry in submitted:
        fit = entry.get("fit", {})
        if not isinstance(fit, dict):
            continue
        dims = fit.get("dimensions", {})
        if not isinstance(dims, dict):
            continue
        net_score = dims.get("network_proximity")
        if net_score is None:
            continue
        net_score = int(net_score)
        outcome = entry.get("outcome")
        network_outcomes[net_score]["total"] += 1
        if outcome == "accepted":
            network_outcomes[net_score]["accepted"] += 1
        elif outcome == "rejected":
            network_outcomes[net_score]["rejected"] += 1

    # Format results
    dist_results = [{"network_score": k, "count": v} for k, v in sorted(score_dist.items())]
    track_results = []
    for track, scores in sorted(track_sums.items()):
        avg = sum(scores) / len(scores) if scores else 0
        track_results.append({"track": track, "avg_network": round(avg, 1), "count": len(scores)})
    position_results = []
    for pos, scores in sorted(position_sums.items()):
        avg = sum(scores) / len(scores) if scores else 0
        position_results.append({"position": pos, "avg_network": round(avg, 1), "count": len(scores)})
    outcome_results = []
    for score_val, data in sorted(network_outcomes.items()):
        rate = (data["accepted"] / data["total"] * 100) if data["total"] > 0 else 0
        outcome_results.append({"network_score": score_val, "rate": round(rate, 1), **data})

    return {
        "distribution": dist_results,
        "by_track": track_results,
        "by_position": position_results,
        "outcomes_by_network": outcome_results,
    }


def print_section(title: str, data: dict) -> None:
    """Print a single analysis section."""
    print(f"\n{title}")
    print("=" * 60)
    for key, items in data.items():
        if not items:
            print("  No data available.")
            continue
        print(f"\n  {key}:")
        for item in items:
            # Standard format: items with accepted/rejected/total/rate
            if "total" in item and "accepted" in item:
                label_key = [k for k in item if k not in ("accepted", "rejected", "total", "rate")][0]
                print(f"    {str(item[label_key]):<30s}  {item['total']:>3d} submitted  "
                      f"{item['accepted']:>3d} accepted  ({item['rate']}%)")
            else:
                # Generic format: print all key-value pairs
                parts = [f"{k}={v}" for k, v in item.items()]
                print(f"    {', '.join(parts)}")


def main():
    parser = argparse.ArgumentParser(description="Portfolio analysis engine")
    parser.add_argument("--query", choices=["blocks", "position", "channel", "variants", "network"],
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
        "network": ("Network Proximity ROI", query_network),
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
