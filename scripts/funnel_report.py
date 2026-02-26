#!/usr/bin/env python3
"""Conversion funnel analytics by variable.

Calculates conversion rates segmented by channel, resume variant,
cover letter presence, follow-up count, identity position, and portal type.
Reads from pipeline YAML entries and conversion-log.yaml.

Usage:
    python scripts/funnel_report.py                # Full funnel summary
    python scripts/funnel_report.py --by channel   # Breakdown by channel
    python scripts/funnel_report.py --by position  # Breakdown by identity position
    python scripts/funnel_report.py --by portal    # Breakdown by portal type
    python scripts/funnel_report.py --by track     # Breakdown by track (job/grant/etc)
    python scripts/funnel_report.py --weekly       # Weekly submission velocity
    python scripts/funnel_report.py --targets      # Show conversion targets vs actual
"""

import argparse
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import (
    ALL_PIPELINE_DIRS,
    SIGNALS_DIR,
    load_entries,
    parse_date,
    STATUS_ORDER,
)

# Conversion targets (benchmarks from plan)
TARGETS = {
    "apply_to_phone": 0.10,       # 10% — industry avg for cold apply: 5-10%
    "phone_to_onsite": 0.33,      # 33%
    "onsite_to_offer": 0.33,      # 33%
    "full_funnel_cold": 0.01,     # 1% cold
    "full_funnel_followup": 0.05, # 5% with follow-up + tailoring
}

# Funnel stages in order
FUNNEL_STAGES = [
    "research", "qualified", "drafting", "staged", "deferred",
    "submitted", "acknowledged", "interview", "outcome",
]


def load_all_entries() -> list[dict]:
    """Load all pipeline entries across all directories."""
    return load_entries(include_filepath=True)


def load_conversion_log() -> list[dict]:
    """Load conversion log entries."""
    log_path = SIGNALS_DIR / "conversion-log.yaml"
    if not log_path.exists():
        return []
    with open(log_path) as f:
        data = yaml.safe_load(f) or {}
    return data.get("entries", []) or []


def get_stage_index(status: str) -> int:
    """Get numeric index for a pipeline status."""
    try:
        return FUNNEL_STAGES.index(status)
    except ValueError:
        return -1


def funnel_summary(entries: list[dict]):
    """Print overall funnel conversion summary."""
    stage_counts = Counter()
    outcome_counts = Counter()
    track_counts = Counter()

    for entry in entries:
        status = entry.get("status", "unknown")
        stage_counts[status] += 1
        track_counts[entry.get("track", "unknown")] += 1

        outcome = entry.get("outcome")
        if outcome:
            outcome_counts[outcome] += 1

    total = len(entries)

    print(f"Pipeline Funnel Summary — {date.today().isoformat()}")
    print(f"{'=' * 60}")
    print(f"Total entries: {total}")
    print()

    # Stage distribution
    print(f"Stage Distribution:")
    cumulative = total
    for stage in FUNNEL_STAGES:
        count = stage_counts.get(stage, 0)
        pct = (count / total * 100) if total else 0
        bar = "#" * int(pct / 2)
        print(f"  {stage:<15s} {count:>4d}  ({pct:>5.1f}%)  {bar}")

    print()

    # Conversion rates between stages
    print(f"Stage-to-Stage Conversion:")
    for i in range(len(FUNNEL_STAGES) - 1):
        current = FUNNEL_STAGES[i]
        next_stage = FUNNEL_STAGES[i + 1]
        # Count entries that reached at least next_stage
        reached_current = sum(
            1 for e in entries
            if get_stage_index(e.get("status", "")) >= i
        )
        reached_next = sum(
            1 for e in entries
            if get_stage_index(e.get("status", "")) >= i + 1
        )
        rate = (reached_next / reached_current * 100) if reached_current else 0
        print(f"  {current:<12s} → {next_stage:<12s}: {reached_next}/{reached_current} = {rate:.1f}%")

    print()

    # Track distribution
    print(f"Track Distribution:")
    for track, count in sorted(track_counts.items(), key=lambda x: -x[1]):
        pct = (count / total * 100) if total else 0
        print(f"  {track:<15s} {count:>4d}  ({pct:>5.1f}%)")

    if outcome_counts:
        print()
        print(f"Outcomes:")
        for outcome, count in sorted(outcome_counts.items(), key=lambda x: -x[1]):
            print(f"  {outcome:<15s} {count:>4d}")


def breakdown_by(entries: list[dict], dimension: str):
    """Print conversion breakdown by a specific dimension."""
    groups = defaultdict(list)

    for entry in entries:
        key = _get_dimension_value(entry, dimension)
        groups[key].append(entry)

    print(f"Conversion Breakdown by {dimension.title()}")
    print(f"{'=' * 70}")

    # Header
    print(f"  {'Value':<30s} {'Total':>6s} {'Submit':>7s} {'Ack':>5s} {'Intv':>5s} {'Rate':>6s}")
    print(f"  {'-' * 30} {'-' * 6} {'-' * 7} {'-' * 5} {'-' * 5} {'-' * 6}")

    for key, group in sorted(groups.items(), key=lambda x: -len(x[1])):
        total = len(group)
        submitted = sum(1 for e in group if get_stage_index(e.get("status", "")) >= 4)
        acknowledged = sum(1 for e in group if get_stage_index(e.get("status", "")) >= 5)
        interview = sum(1 for e in group if get_stage_index(e.get("status", "")) >= 6)
        rate = (acknowledged / submitted * 100) if submitted else 0

        print(f"  {str(key):<30s} {total:>6d} {submitted:>7d} {acknowledged:>5d} {interview:>5d} {rate:>5.1f}%")

    print(f"\n{'=' * 70}")


def _get_dimension_value(entry: dict, dimension: str) -> str:
    """Extract a dimension value from an entry for grouping."""
    if dimension == "channel":
        conv = entry.get("conversion", {})
        if isinstance(conv, dict):
            return conv.get("channel") or "unknown"
        return "unknown"

    if dimension == "position":
        fit = entry.get("fit", {})
        if isinstance(fit, dict):
            return fit.get("identity_position") or "unset"
        return "unset"

    if dimension == "portal":
        target = entry.get("target", {})
        if isinstance(target, dict):
            return target.get("portal") or "unknown"
        return "unknown"

    if dimension == "track":
        return entry.get("track", "unknown")

    if dimension == "cover_letter":
        conv = entry.get("conversion", {})
        if isinstance(conv, dict):
            cl = conv.get("cover_letter_present")
            if cl is True:
                return "with_cover_letter"
            elif cl is False:
                return "no_cover_letter"
        # Infer from variant_ids
        sub = entry.get("submission", {})
        if isinstance(sub, dict):
            variants = sub.get("variant_ids", {})
            if isinstance(variants, dict) and variants.get("cover_letter"):
                return "with_cover_letter"
        return "unknown"

    if dimension == "follow_up":
        conv = entry.get("conversion", {})
        if isinstance(conv, dict):
            count = conv.get("follow_up_count", 0) or 0
            if count == 0:
                return "no_followup"
            elif count == 1:
                return "1_followup"
            else:
                return f"{count}+_followups"
        return "no_followup"

    return "unknown"


def weekly_velocity(entries: list[dict]):
    """Show weekly submission velocity."""
    print(f"Weekly Submission Velocity")
    print(f"{'=' * 60}")

    # Group submissions by week
    weekly = defaultdict(int)
    for entry in entries:
        timeline = entry.get("timeline", {})
        if isinstance(timeline, dict):
            sub_date = parse_date(timeline.get("submitted"))
            if sub_date:
                # ISO week start (Monday)
                week_start = sub_date - timedelta(days=sub_date.weekday())
                weekly[week_start] += 1

    if not weekly:
        print("  No submissions recorded yet.")
        return

    # Show last 8 weeks
    all_weeks = sorted(weekly.keys())
    for week in all_weeks[-8:]:
        count = weekly[week]
        bar = "#" * count
        week_end = week + timedelta(days=6)
        print(f"  {week.isoformat()} — {week_end.isoformat()}  {count:>3d}  {bar}")

    total = sum(weekly.values())
    weeks_active = len(weekly)
    avg = total / weeks_active if weeks_active else 0
    print(f"\n  Total: {total} submissions over {weeks_active} weeks")
    print(f"  Average: {avg:.1f}/week")

    # Daily rate
    if all_weeks:
        first = all_weeks[0]
        days_active = (date.today() - first).days or 1
        daily = total / days_active
        print(f"  Daily rate: {daily:.1f}/day")


def show_targets(entries: list[dict]):
    """Compare actual conversion rates against targets."""
    submitted = [e for e in entries if get_stage_index(e.get("status", "")) >= 4]
    acknowledged = [e for e in entries if get_stage_index(e.get("status", "")) >= 5]
    interview = [e for e in entries if get_stage_index(e.get("status", "")) >= 6]
    outcome_offer = [e for e in entries if e.get("outcome") == "accepted"]

    n_sub = len(submitted)
    n_ack = len(acknowledged)
    n_int = len(interview)
    n_offer = len(outcome_offer)

    print(f"Conversion Targets vs Actual")
    print(f"{'=' * 60}")

    print(f"\n  {'Metric':<30s} {'Target':>8s} {'Actual':>8s} {'Status':>8s}")
    print(f"  {'-' * 30} {'-' * 8} {'-' * 8} {'-' * 8}")

    # Apply → Phone Screen (submitted → acknowledged/interview)
    actual_phone = (n_ack / n_sub) if n_sub else 0
    target_phone = TARGETS["apply_to_phone"]
    status = "OK" if actual_phone >= target_phone else "BELOW"
    print(f"  {'Apply → Response':<30s} {target_phone:>7.0%} {actual_phone:>7.0%} {status:>8s}")

    # Phone → Onsite
    actual_onsite = (n_int / n_ack) if n_ack else 0
    target_onsite = TARGETS["phone_to_onsite"]
    status = "OK" if actual_onsite >= target_onsite or n_ack == 0 else "BELOW"
    print(f"  {'Response → Interview':<30s} {target_onsite:>7.0%} {actual_onsite:>7.0%} {status:>8s}")

    # Onsite → Offer
    actual_offer = (n_offer / n_int) if n_int else 0
    target_offer = TARGETS["onsite_to_offer"]
    status = "OK" if actual_offer >= target_offer or n_int == 0 else "BELOW"
    print(f"  {'Interview → Offer':<30s} {target_offer:>7.0%} {actual_offer:>7.0%} {status:>8s}")

    # Full funnel
    actual_full = (n_offer / n_sub) if n_sub else 0
    target_full = TARGETS["full_funnel_followup"]
    status = "OK" if actual_full >= target_full or n_sub == 0 else "BELOW"
    print(f"  {'Full Funnel':<30s} {target_full:>7.0%} {actual_full:>7.0%} {status:>8s}")

    print(f"\n  Raw counts: {n_sub} submitted → {n_ack} responded → {n_int} interview → {n_offer} offer")

    # Volume target
    total_pipeline = len(entries)
    print(f"\n  Pipeline size: {total_pipeline} entries")
    print(f"  Sweet spot: 21-80 total applications (30.89% success rate)")
    if total_pipeline < 21:
        print(f"  Status: BELOW minimum — need {21 - total_pipeline} more entries")
    elif total_pipeline <= 80:
        print(f"  Status: IN sweet spot")
    else:
        print(f"  Status: ABOVE sweet spot — diminishing returns")


def main():
    parser = argparse.ArgumentParser(description="Conversion funnel analytics")
    parser.add_argument("--by", choices=["channel", "position", "portal", "track", "cover_letter", "follow_up"],
                        help="Breakdown by dimension")
    parser.add_argument("--weekly", action="store_true", help="Weekly submission velocity")
    parser.add_argument("--targets", action="store_true", help="Show conversion targets vs actual")
    args = parser.parse_args()

    entries = load_all_entries()
    if not entries:
        print("No pipeline entries found.", file=sys.stderr)
        sys.exit(1)

    if args.by:
        breakdown_by(entries, args.by)
    elif args.weekly:
        weekly_velocity(entries)
    elif args.targets:
        show_targets(entries)
    else:
        funnel_summary(entries)


if __name__ == "__main__":
    main()
