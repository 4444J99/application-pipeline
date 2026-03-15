#!/usr/bin/env python3
"""Pipeline mode switcher — precision, volume, or hybrid.

Reads and updates the active pipeline mode in market-intelligence-2026.json.
Each mode has different thresholds for auto-qualify score, max active entries,
weekly submission caps, and staleness windows.

Usage:
    python scripts/pipeline_mode.py                # Show current mode
    python scripts/pipeline_mode.py --set volume   # Switch to volume mode
    python scripts/pipeline_mode.py --set hybrid   # Switch to hybrid mode
    python scripts/pipeline_mode.py --compare      # Compare all modes side-by-side
    python scripts/pipeline_mode.py --json          # Machine-readable output
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import REPO_ROOT

MARKET_JSON_PATH = REPO_ROOT / "strategy" / "market-intelligence-2026.json"

VALID_MODES = {"precision", "volume", "hybrid"}

MODE_DESCRIPTIONS = {
    "precision": "Max quality — 1-2 apps/week, score ≥ 9.0, deep research + warm paths",
    "volume": "Max throughput — up to 10 apps/week, score ≥ 7.0, fast iteration",
    "hybrid": "Balanced — up to 5 apps/week, score ≥ 8.0, selective volume",
}


def load_market_json() -> dict:
    """Load market-intelligence JSON."""
    if not MARKET_JSON_PATH.exists():
        return {}
    with open(MARKET_JSON_PATH) as f:
        return json.load(f)


def get_current_mode(market: dict | None = None) -> str:
    """Get the current pipeline mode."""
    if market is None:
        market = load_market_json()
    return market.get("precision_strategy", {}).get("mode", "precision")


def get_mode_thresholds(market: dict | None = None) -> dict:
    """Get the thresholds dict for all modes."""
    if market is None:
        market = load_market_json()
    return market.get("precision_strategy", {}).get("mode_thresholds", {})


def get_active_thresholds(market: dict | None = None) -> dict:
    """Get thresholds for the currently active mode."""
    if market is None:
        market = load_market_json()
    mode = get_current_mode(market)
    thresholds = get_mode_thresholds(market)
    return thresholds.get(mode, {})


def set_mode(new_mode: str, dry_run: bool = False) -> dict:
    """Switch the pipeline mode.

    Returns:
        dict with old_mode, new_mode, thresholds, and what changed.
    """
    if new_mode not in VALID_MODES:
        return {"status": "error", "error": f"Invalid mode: {new_mode}. Valid: {sorted(VALID_MODES)}"}

    market = load_market_json()
    old_mode = get_current_mode(market)
    thresholds = get_mode_thresholds(market)

    old_t = thresholds.get(old_mode, {})
    new_t = thresholds.get(new_mode, {})

    if old_mode == new_mode:
        return {
            "status": "no_change",
            "mode": old_mode,
            "thresholds": old_t,
            "message": f"Already in {new_mode} mode",
        }

    # Compute what changes
    changes = {}
    for key in set(list(old_t.keys()) + list(new_t.keys())):
        ov = old_t.get(key)
        nv = new_t.get(key)
        if ov != nv:
            changes[key] = {"old": ov, "new": nv}

    if not dry_run:
        market["precision_strategy"]["mode"] = new_mode
        with open(MARKET_JSON_PATH, "w") as f:
            json.dump(market, f, indent=2)
            f.write("\n")

    return {
        "status": "dry_run" if dry_run else "switched",
        "old_mode": old_mode,
        "new_mode": new_mode,
        "old_thresholds": old_t,
        "new_thresholds": new_t,
        "changes": changes,
        "message": f"{'Would switch' if dry_run else 'Switched'} {old_mode} → {new_mode}",
    }


def compare_modes(market: dict | None = None) -> dict:
    """Compare all modes side-by-side."""
    if market is None:
        market = load_market_json()
    current = get_current_mode(market)
    thresholds = get_mode_thresholds(market)

    return {
        "current_mode": current,
        "modes": {
            mode: {
                "active": mode == current,
                "description": MODE_DESCRIPTIONS.get(mode, ""),
                **thresholds.get(mode, {}),
            }
            for mode in VALID_MODES
        },
    }


def format_report(data: dict) -> str:
    """Format a human-readable mode report."""
    lines = []

    if "modes" in data:
        # Comparison view
        lines.append(f"  Current mode: {data['current_mode']}")
        lines.append("")
        for mode in ["precision", "volume", "hybrid"]:
            info = data["modes"].get(mode, {})
            marker = " ◀ ACTIVE" if info.get("active") else ""
            lines.append(f"  {mode.upper()}{marker}")
            lines.append(f"    {info.get('description', '')}")
            lines.append(f"    auto_qualify_min:     {info.get('auto_qualify_min', '?')}")
            lines.append(f"    max_active:           {info.get('max_active', '?')}")
            lines.append(f"    max_weekly_submissions:{info.get('max_weekly_submissions', '?')}")
            lines.append(f"    stale_days:           {info.get('stale_days', '?')}")
            lines.append(f"    stagnant_days:        {info.get('stagnant_days', '?')}")
            lines.append("")
    elif "changes" in data:
        # Switch result
        lines.append(f"  {data['message']}")
        if data.get("changes"):
            lines.append("")
            for key, vals in data["changes"].items():
                lines.append(f"    {key}: {vals['old']} → {vals['new']}")
    elif "thresholds" in data:
        # Current mode
        lines.append(f"  Mode: {data['mode']}")
        for k, v in data["thresholds"].items():
            lines.append(f"    {k}: {v}")
    else:
        lines.append(f"  {data.get('message', str(data))}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Pipeline mode switcher")
    parser.add_argument("--set", choices=sorted(VALID_MODES), help="Switch to a mode")
    parser.add_argument("--compare", action="store_true", help="Compare all modes")
    parser.add_argument("--dry-run", action="store_true", help="Preview mode switch")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    if args.set:
        result = set_mode(args.set, dry_run=args.dry_run)
    elif args.compare:
        result = compare_modes()
    else:
        market = load_market_json()
        mode = get_current_mode(market)
        thresholds = get_active_thresholds(market)
        result = {"mode": mode, "thresholds": thresholds, "description": MODE_DESCRIPTIONS.get(mode, "")}

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        print(format_report(result))


if __name__ == "__main__":
    main()
