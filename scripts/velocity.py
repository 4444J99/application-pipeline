#!/usr/bin/env python3
"""Submission velocity tracking and pipeline throughput metrics.

Fills signals/patterns.md with actionable data about pipeline health,
staleness distribution, and conversion funnel rates.

Usage:
    python scripts/velocity.py                    # Display velocity stats
    python scripts/velocity.py --update-signals   # Write to signals/patterns.md
"""

import argparse
import sys
from collections import Counter
from datetime import date, timedelta

from pipeline_lib import (
    SIGNALS_DIR, STATUS_ORDER,
    load_entries, parse_date, get_effort, get_deadline, days_until,
    ACTIONABLE_STATUSES,
)

PATTERNS_FILE = SIGNALS_DIR / "patterns.md"


def compute_velocity(entries: list[dict]) -> dict:
    """Compute all velocity metrics from pipeline entries."""
    today = date.today()
    metrics = {}

    # --- Submission history ---
    submit_dates = []
    for e in entries:
        tl = e.get("timeline", {})
        if isinstance(tl, dict) and tl.get("submitted"):
            sd = parse_date(tl["submitted"])
            if sd:
                submit_dates.append(sd)

    submit_dates.sort()

    if submit_dates:
        metrics["last_submission"] = submit_dates[-1].isoformat()
        metrics["days_since_last"] = (today - submit_dates[-1]).days
        metrics["total_submitted"] = len(submit_dates)

        # Weekly/monthly rates
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        metrics["submitted_last_7d"] = sum(1 for d in submit_dates if d >= week_ago)
        metrics["submitted_last_30d"] = sum(1 for d in submit_dates if d >= month_ago)
    else:
        metrics["last_submission"] = None
        metrics["days_since_last"] = None
        metrics["total_submitted"] = 0
        metrics["submitted_last_7d"] = 0
        metrics["submitted_last_30d"] = 0

    # --- Status distribution ---
    status_counts = Counter()
    for e in entries:
        status_counts[e.get("status", "unknown")] += 1
    metrics["status_distribution"] = dict(status_counts)

    # --- Effort distribution (actionable only) ---
    effort_counts = Counter()
    for e in entries:
        if e.get("status") in ACTIONABLE_STATUSES:
            effort_counts[get_effort(e)] += 1
    metrics["effort_distribution"] = dict(effort_counts)

    # --- Staleness distribution ---
    staleness_buckets = {"0-7d": 0, "8-14d": 0, "15-30d": 0, "30d+": 0, "never": 0}
    for e in entries:
        if e.get("status") not in ACTIONABLE_STATUSES:
            continue
        lt = parse_date(e.get("last_touched"))
        if not lt:
            staleness_buckets["never"] += 1
        else:
            days_stale = (today - lt).days
            if days_stale <= 7:
                staleness_buckets["0-7d"] += 1
            elif days_stale <= 14:
                staleness_buckets["8-14d"] += 1
            elif days_stale <= 30:
                staleness_buckets["15-30d"] += 1
            else:
                staleness_buckets["30d+"] += 1
    metrics["staleness_distribution"] = staleness_buckets

    # --- Conversion funnel ---
    # How many entries have reached each stage
    stage_reached = Counter()
    for e in entries:
        tl = e.get("timeline", {})
        if not isinstance(tl, dict):
            continue
        if tl.get("researched"):
            stage_reached["researched"] += 1
        if tl.get("qualified"):
            stage_reached["qualified"] += 1
        if tl.get("materials_ready"):
            stage_reached["materials_ready"] += 1
        if tl.get("submitted"):
            stage_reached["submitted"] += 1
        if tl.get("acknowledged"):
            stage_reached["acknowledged"] += 1
        if tl.get("outcome_date"):
            stage_reached["outcome"] += 1
    metrics["funnel"] = dict(stage_reached)

    # --- Outcome breakdown ---
    outcome_counts = Counter()
    for e in entries:
        outcome = e.get("outcome")
        if outcome:
            outcome_counts[outcome] += 1
    metrics["outcomes"] = dict(outcome_counts)

    # --- Track distribution ---
    track_counts = Counter()
    for e in entries:
        track_counts[e.get("track", "unknown")] += 1
    metrics["track_distribution"] = dict(track_counts)

    # --- Deadline pressure ---
    upcoming = {"this_week": 0, "next_2_weeks": 0, "next_month": 0}
    for e in entries:
        if e.get("status") not in ACTIONABLE_STATUSES:
            continue
        dl_date, dl_type = get_deadline(e)
        if dl_date and dl_type in ("hard", "fixed"):
            d = days_until(dl_date)
            if 0 <= d <= 7:
                upcoming["this_week"] += 1
            elif 0 <= d <= 14:
                upcoming["next_2_weeks"] += 1
            elif 0 <= d <= 30:
                upcoming["next_month"] += 1
    metrics["deadline_pressure"] = upcoming

    return metrics


def format_report(metrics: dict) -> str:
    """Format metrics into a readable markdown report."""
    lines = []
    today = date.today()

    lines.append("# Pipeline Velocity Report")
    lines.append(f"\n*Generated: {today.isoformat()}*\n")

    # Submission velocity
    lines.append("## Submission Velocity\n")
    if metrics["last_submission"]:
        lines.append(f"- Last submission: {metrics['last_submission']} "
                      f"({metrics['days_since_last']} days ago)")
    else:
        lines.append("- Last submission: **NEVER** (0 submissions)")
    lines.append(f"- Total submitted: {metrics['total_submitted']}")
    lines.append(f"- Last 7 days: {metrics['submitted_last_7d']}")
    lines.append(f"- Last 30 days: {metrics['submitted_last_30d']}")

    # Status distribution
    lines.append("\n## Status Distribution\n")
    lines.append("| Status | Count |")
    lines.append("|--------|-------|")
    for status in STATUS_ORDER:
        count = metrics["status_distribution"].get(status, 0)
        if count > 0:
            bar = "#" * count
            lines.append(f"| {status} | {count} {bar} |")

    # Effort distribution
    lines.append("\n## Effort Distribution (Actionable)\n")
    lines.append("| Effort | Count |")
    lines.append("|--------|-------|")
    for effort in ["quick", "standard", "deep", "complex"]:
        count = metrics["effort_distribution"].get(effort, 0)
        if count > 0:
            lines.append(f"| {effort} | {count} |")

    # Staleness
    lines.append("\n## Staleness (Actionable Entries)\n")
    lines.append("| Window | Count |")
    lines.append("|--------|-------|")
    for bucket, count in metrics["staleness_distribution"].items():
        if count > 0:
            lines.append(f"| {bucket} | {count} |")

    # Conversion funnel
    lines.append("\n## Conversion Funnel\n")
    funnel = metrics["funnel"]
    funnel_order = ["researched", "qualified", "materials_ready", "submitted",
                    "acknowledged", "outcome"]
    total = max(funnel.get("researched", 0), 1)
    for stage in funnel_order:
        count = funnel.get(stage, 0)
        pct = count / total * 100 if total else 0
        bar = "#" * int(pct / 5)
        lines.append(f"- {stage}: {count} ({pct:.0f}%) {bar}")

    # Outcomes
    if metrics["outcomes"]:
        lines.append("\n## Outcomes\n")
        for outcome, count in sorted(metrics["outcomes"].items()):
            lines.append(f"- {outcome}: {count}")

    # Deadline pressure
    lines.append("\n## Deadline Pressure\n")
    dp = metrics["deadline_pressure"]
    lines.append(f"- This week: {dp['this_week']} hard deadlines")
    lines.append(f"- Next 2 weeks: {dp['next_2_weeks']} hard deadlines")
    lines.append(f"- Next month: {dp['next_month']} hard deadlines")

    # Hypotheses (keep from original)
    lines.append("\n## Hypotheses to Test\n")
    lines.append("1. Does the systems-artist framing convert better than "
                  "creative-technologist for grants?")
    lines.append("2. Does the 60s block or the 2min block earn more interview callbacks?")
    lines.append("3. Do applications with benefits-cliff notes affect acceptance rates?")
    lines.append("4. Which project descriptions generate the most interest?")
    lines.append("5. Do hand-written cover letters outperform composed-from-blocks versions?")

    return "\n".join(lines) + "\n"


def display_velocity(metrics: dict):
    """Print velocity metrics to stdout."""
    print("PIPELINE VELOCITY")
    print("=" * 60)
    print()

    # Submission
    if metrics["last_submission"]:
        print(f"  Last submission: {metrics['last_submission']} "
              f"({metrics['days_since_last']}d ago)")
    else:
        print("  Last submission: NEVER")
    print(f"  Total submitted: {metrics['total_submitted']}")
    print(f"  Last 7d: {metrics['submitted_last_7d']} | "
          f"Last 30d: {metrics['submitted_last_30d']}")
    print()

    # Status
    print("  Status distribution:")
    for status in STATUS_ORDER:
        count = metrics["status_distribution"].get(status, 0)
        if count > 0:
            bar = "#" * count
            print(f"    {status:15s} {count:3d}  {bar}")
    print()

    # Staleness
    print("  Staleness (actionable):")
    for bucket, count in metrics["staleness_distribution"].items():
        if count > 0:
            print(f"    {bucket:10s} {count}")
    print()

    # Funnel
    print("  Conversion funnel:")
    funnel = metrics["funnel"]
    total = max(funnel.get("researched", 0), 1)
    for stage in ["researched", "qualified", "materials_ready", "submitted",
                  "acknowledged", "outcome"]:
        count = funnel.get(stage, 0)
        pct = count / total * 100 if total else 0
        print(f"    {stage:20s} {count:3d}  ({pct:.0f}%)")
    print()

    # Deadline pressure
    dp = metrics["deadline_pressure"]
    print(f"  Deadlines: {dp['this_week']} this week | "
          f"{dp['next_2_weeks']} in 2 weeks | {dp['next_month']} in 30d")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Pipeline velocity tracking and metrics"
    )
    parser.add_argument("--update-signals", action="store_true",
                        help="Write report to signals/patterns.md")
    args = parser.parse_args()

    entries = load_entries()
    if not entries:
        print("No pipeline entries found.")
        sys.exit(1)

    metrics = compute_velocity(entries)
    display_velocity(metrics)

    if args.update_signals:
        report = format_report(metrics)
        PATTERNS_FILE.write_text(report)
        print(f"Updated: {PATTERNS_FILE.relative_to(SIGNALS_DIR.parent)}")


if __name__ == "__main__":
    main()
