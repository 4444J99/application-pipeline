#!/usr/bin/env python3
"""Quarterly OKR (Objectives & Key Results) tracker.

Set quarterly targets for pipeline metrics and measure progress.
Targets are stored in strategy/okr-targets.yaml.

Usage:
    python scripts/okr.py                     # Show current OKR progress
    python scripts/okr.py --set               # Interactive target setting
    python scripts/okr.py --json              # Machine-readable output
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import yaml
from pipeline_lib import (
    REPO_ROOT,
    load_entries,
    parse_date,
)

OKR_PATH = REPO_ROOT / "strategy" / "okr-targets.yaml"

# Default targets (used when no OKR file exists)
DEFAULT_TARGETS = {
    "quarter": "Q2-2026",
    "period_start": "2026-04-01",
    "period_end": "2026-06-30",
    "objectives": {
        "submissions": {
            "target": 12,
            "description": "Total submissions this quarter",
        },
        "conversion_rate": {
            "target": 0.15,
            "description": "Response rate (acknowledged+interview+accepted / submitted)",
        },
        "avg_score": {
            "target": 9.0,
            "description": "Average composite score of submitted entries",
        },
        "network_actions": {
            "target": 24,
            "description": "Total outreach actions logged (follow-ups, connects, DMs)",
        },
        "outcomes_collected": {
            "target": 10,
            "description": "Terminal outcomes received (accepted/rejected/withdrawn/expired)",
        },
    },
}


def load_targets() -> dict:
    """Load OKR targets from YAML, falling back to defaults."""
    if OKR_PATH.exists():
        with open(OKR_PATH) as f:
            data = yaml.safe_load(f) or {}
        return data
    return DEFAULT_TARGETS.copy()


def save_targets(targets: dict) -> None:
    """Save OKR targets to YAML."""
    OKR_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OKR_PATH, "w") as f:
        yaml.dump(targets, f, default_flow_style=False, sort_keys=False)
    print(f"Saved OKR targets to {OKR_PATH.relative_to(REPO_ROOT)}")


def compute_actuals(entries: list[dict], period_start: str, period_end: str) -> dict:
    """Compute actual values for each OKR metric within the period."""
    start = parse_date(period_start)
    end = parse_date(period_end)
    if not start or not end:
        return {}

    # Count submissions in period
    submissions = 0
    submitted_entries = []
    for e in entries:
        tl = e.get("timeline", {})
        if isinstance(tl, dict):
            sub_date = parse_date(tl.get("submitted"))
            if sub_date and start <= sub_date <= end:
                submissions += 1
                submitted_entries.append(e)

    # Conversion rate: responses among submitted entries in period
    responses = 0
    for e in submitted_entries:
        status = e.get("status", "")
        if status in ("acknowledged", "interview", "outcome"):
            responses += 1
        elif e.get("outcome"):
            responses += 1
    conversion_rate = responses / submissions if submissions > 0 else 0.0

    # Average score of submitted entries
    scores = []
    for e in submitted_entries:
        fit = e.get("fit", {})
        if isinstance(fit, dict):
            s = fit.get("composite") or fit.get("score")
            if s is not None:
                scores.append(float(s))
    avg_score = sum(scores) / len(scores) if scores else 0.0

    # Network actions in period
    network_actions = 0
    for e in entries:
        follow_ups = e.get("follow_up") or []
        for fu in follow_ups:
            if isinstance(fu, dict):
                fu_date = parse_date(fu.get("date"))
                if fu_date and start <= fu_date <= end:
                    network_actions += 1

    # Outcomes collected in period
    terminal = {"accepted", "rejected", "withdrawn", "expired"}
    outcomes_collected = 0
    for e in entries:
        if e.get("outcome") in terminal:
            tl = e.get("timeline", {})
            if isinstance(tl, dict):
                od = parse_date(tl.get("outcome_date"))
                if od and start <= od <= end:
                    outcomes_collected += 1

    return {
        "submissions": submissions,
        "conversion_rate": round(conversion_rate, 3),
        "avg_score": round(avg_score, 1),
        "network_actions": network_actions,
        "outcomes_collected": outcomes_collected,
    }


def compute_progress(targets: dict, actuals: dict) -> list[dict]:
    """Compute progress percentage for each objective."""
    objectives = targets.get("objectives", {})
    rows = []
    for key, obj in objectives.items():
        target_val = obj.get("target", 0)
        actual_val = actuals.get(key, 0)
        description = obj.get("description", key)

        if isinstance(target_val, float) and target_val > 0:
            pct = actual_val / target_val * 100
        elif isinstance(target_val, int) and target_val > 0:
            pct = actual_val / target_val * 100
        else:
            pct = 0.0

        status = "ON_TRACK" if pct >= 70 else ("AT_RISK" if pct >= 40 else "BEHIND")

        rows.append({
            "key": key,
            "description": description,
            "target": target_val,
            "actual": actual_val,
            "progress_pct": round(pct, 1),
            "status": status,
        })
    return rows


def quarter_elapsed_pct(period_start: str, period_end: str) -> float:
    """What percentage of the quarter has elapsed."""
    start = parse_date(period_start)
    end = parse_date(period_end)
    if not start or not end:
        return 0.0
    today = date.today()
    total_days = (end - start).days
    elapsed = (today - start).days
    if total_days <= 0:
        return 100.0
    return round(min(max(elapsed / total_days * 100, 0), 100), 1)


def format_report(targets: dict, progress: list[dict], elapsed_pct: float) -> str:
    """Format OKR progress as a human-readable report."""
    lines = []
    quarter = targets.get("quarter", "?")
    lines.append(f"QUARTERLY OKR PROGRESS — {quarter}")
    lines.append("=" * 60)
    lines.append(f"Period: {targets.get('period_start', '?')} to {targets.get('period_end', '?')}")
    lines.append(f"Quarter elapsed: {elapsed_pct}%")
    lines.append("")

    lines.append(f"  {'Objective':<25s} {'Target':>8s} {'Actual':>8s} {'Progress':>9s}  Status")
    lines.append(f"  {'-' * 25} {'-' * 8} {'-' * 8} {'-' * 9}  {'-' * 10}")

    for row in progress:
        target_str = f"{row['target']}" if isinstance(row["target"], int) else f"{row['target']:.0%}"
        actual_str = f"{row['actual']}" if isinstance(row["actual"], int) else f"{row['actual']:.1%}"
        pct_str = f"{row['progress_pct']:.0f}%"
        lines.append(f"  {row['key']:<25s} {target_str:>8s} {actual_str:>8s} {pct_str:>9s}  {row['status']}")

    lines.append("")

    # Pacing check
    behind = [r for r in progress if r["status"] == "BEHIND"]
    at_risk = [r for r in progress if r["status"] == "AT_RISK"]
    if behind:
        lines.append(f"BEHIND ({len(behind)}): {', '.join(r['key'] for r in behind)}")
    if at_risk:
        lines.append(f"AT RISK ({len(at_risk)}): {', '.join(r['key'] for r in at_risk)}")
    if not behind and not at_risk:
        lines.append("All objectives on track.")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Quarterly OKR tracker")
    parser.add_argument("--set", action="store_true", help="Save default targets to strategy/okr-targets.yaml")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    if args.set:
        save_targets(DEFAULT_TARGETS)
        return

    targets = load_targets()
    entries = load_entries()
    period_start = targets.get("period_start", "")
    period_end = targets.get("period_end", "")

    actuals = compute_actuals(entries, period_start, period_end)
    progress = compute_progress(targets, actuals)
    elapsed = quarter_elapsed_pct(period_start, period_end)

    if args.json:
        print(json.dumps({
            "targets": targets,
            "actuals": actuals,
            "progress": progress,
            "elapsed_pct": elapsed,
        }, indent=2, default=str))
        return

    print(format_report(targets, progress, elapsed))


if __name__ == "__main__":
    main()
