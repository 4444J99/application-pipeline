#!/usr/bin/env python3
"""Phase analytics: compare Volume (Phase 1) vs Precision (Phase 2) strategies.

Phase 1 (Fall 2024 – Spring 2025): ~1,725 cold applications via LinkedIn/ApplyAll
Phase 2 (Early 2026 – Present): Targeted precision applications via direct portals

Usage:
    python scripts/phase_analytics.py               # Full comparison report
    python scripts/phase_analytics.py --velocity     # Monthly velocity curve
    python scripts/phase_analytics.py --json         # Machine-readable output
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import SIGNALS_DIR

HISTORICAL_PATH = SIGNALS_DIR / "historical-outcomes.yaml"
CONVERSION_LOG_PATH = SIGNALS_DIR / "conversion-log.yaml"

PHASE_1_CHANNELS = {"linkedin-easy-apply", "applyall-blast"}


def classify_phase(channel: str, applied_date: str | None = None) -> int:
    """Classify an application into Phase 1 or Phase 2."""
    if channel in PHASE_1_CHANNELS:
        return 1
    return 2


def _load_historical() -> list[dict]:
    if not HISTORICAL_PATH.exists():
        return []
    with open(HISTORICAL_PATH) as f:
        data = yaml.safe_load(f)
    return data.get("entries", []) if isinstance(data, dict) else []


def _load_conversion_log() -> list[dict]:
    if not CONVERSION_LOG_PATH.exists():
        return []
    with open(CONVERSION_LOG_PATH) as f:
        data = yaml.safe_load(f)
    return data.get("entries", []) if isinstance(data, dict) else []


def compute_monthly_velocity(records: list[dict]) -> dict[str, int]:
    """Count applications per month."""
    months: Counter = Counter()
    for r in records:
        d = r.get("applied_date") or r.get("submitted") or ""
        if d and len(d) >= 7:
            months[d[:7]] += 1
    return dict(sorted(months.items()))


def _outcome_stats(records: list[dict]) -> dict:
    outcomes = Counter()
    for r in records:
        outcomes[r.get("outcome") or "pending"] += 1
    total = len(records)
    positive = outcomes.get("accepted", 0) + outcomes.get("acknowledged", 0) + outcomes.get("interview", 0)
    response_rate = positive / total if total else 0
    return {
        "total": total,
        "outcomes": dict(outcomes),
        "positive_responses": positive,
        "response_rate": round(response_rate, 4),
    }


def compute_phase_comparison() -> dict:
    """Compute Phase 1 vs Phase 2 aggregate comparison."""
    historical = _load_historical()
    conversion = _load_conversion_log()

    phase_1 = [r for r in historical if classify_phase(r.get("channel", ""), r.get("applied_date")) == 1]
    phase_2_hist = [r for r in historical if classify_phase(r.get("channel", ""), r.get("applied_date")) == 2]

    # Conversion log entries are all Phase 2 (pipeline era)
    phase_2_conv = []
    for c in conversion:
        phase_2_conv.append({
            "applied_date": c.get("submitted"),
            "channel": c.get("channel", "direct"),
            "portal": c.get("portal"),
            "outcome": c.get("outcome"),
        })
    phase_2 = phase_2_hist + phase_2_conv

    # Portal distribution
    p1_portals = Counter(r.get("portal", "unknown") for r in phase_1)
    p2_portals = Counter(r.get("portal", "unknown") for r in phase_2)

    return {
        "phase_1": {
            **_outcome_stats(phase_1),
            "label": "Volume Optimization (Fall 2024 - Spring 2025)",
            "channels": dict(Counter(r.get("channel", "?") for r in phase_1)),
            "portals": dict(p1_portals.most_common()),
            "monthly_velocity": compute_monthly_velocity(phase_1),
        },
        "phase_2": {
            **_outcome_stats(phase_2),
            "label": "Precision Targeting (Early 2026 - Present)",
            "channels": dict(Counter(r.get("channel", "?") for r in phase_2)),
            "portals": dict(p2_portals.most_common()),
            "monthly_velocity": compute_monthly_velocity(phase_2),
        },
        "improvement": {
            "volume_ratio": (len(phase_1) / len(phase_2)) if phase_2 else None,
            "response_rate_delta": (
                (_outcome_stats(phase_2)["response_rate"] - _outcome_stats(phase_1)["response_rate"])
                if phase_1 and phase_2 else None
            ),
        },
    }


def format_report(comparison: dict) -> str:
    lines = [
        "=" * 70,
        "  PHASE ANALYTICS — Volume vs Precision",
        "=" * 70,
        "",
    ]
    for phase_key in ("phase_1", "phase_2"):
        p = comparison[phase_key]
        lines.append(f"  {p['label']}")
        lines.append(f"  {'─' * 50}")
        lines.append(f"    Applications:    {p['total']}")
        lines.append(f"    Response rate:    {p['response_rate']:.1%}")
        lines.append(f"    Positive:        {p['positive_responses']}")
        lines.append(f"    Outcomes:        {p['outcomes']}")
        lines.append(f"    Channels:        {p['channels']}")
        lines.append("")

    imp = comparison["improvement"]
    lines.append("  COMPARISON")
    lines.append(f"  {'─' * 50}")
    if imp["volume_ratio"]:
        lines.append(f"    Phase 1 sent {imp['volume_ratio']:.0f}x more applications")
    if imp["response_rate_delta"] is not None:
        lines.append(f"    Response rate improvement: {imp['response_rate_delta']:+.1%}")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 1 vs Phase 2 analytics")
    parser.add_argument("--velocity", action="store_true", help="Monthly velocity only")
    parser.add_argument("--json", action="store_true", dest="json_output", help="JSON output")
    args = parser.parse_args()

    comparison = compute_phase_comparison()

    if args.json_output:
        print(json.dumps(comparison, indent=2))
        return

    if args.velocity:
        for phase_key in ("phase_1", "phase_2"):
            p = comparison[phase_key]
            print(f"\n{p['label']}:")
            for month, count in p["monthly_velocity"].items():
                bar = "█" * min(count // 10, 50)
                print(f"  {month}: {count:>4d} {bar}")
        return

    print(format_report(comparison))


if __name__ == "__main__":
    main()
