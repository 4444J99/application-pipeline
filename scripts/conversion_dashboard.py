#!/usr/bin/env python3
"""Unified conversion intelligence dashboard.

Combines funnel analytics, outcome learning calibration, and hypothesis
pattern analysis into a single actionable report. Designed for the
"Analyze" session sequence when you need a holistic view of pipeline
conversion performance.

Usage:
    python scripts/conversion_dashboard.py                       # Full dashboard
    python scripts/conversion_dashboard.py --portal greenhouse   # Portal detail
    python scripts/conversion_dashboard.py --weekly              # Weekly trends
    python scripts/conversion_dashboard.py --save                # Save report to signals/
"""

import argparse
import sys
from collections import Counter
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_outcomes import (  # noqa: I001
    days_since_submission as co_days_since_submission,
    get_submitted_entries,  # noqa: F401 — public interface
)
from outcome_learner import (
    analyze_dimension_accuracy,
    collect_outcome_data,
    load_calibration,
)
from pipeline_lib import (
    ALL_PIPELINE_DIRS,
    ALL_PIPELINE_DIRS_WITH_POOL,  # noqa: F401 — public interface
    DIMENSION_ORDER,  # noqa: F401 — public interface
    PIPELINE_DIR_CLOSED,  # noqa: F401 — public interface
    PIPELINE_DIR_SUBMITTED,  # noqa: F401 — public interface
    SIGNALS_DIR,
    get_score,
    load_entries,
    parse_date,
)

try:
    from feedback_capture import load_hypotheses
except ImportError:
    def load_hypotheses() -> list[dict]:
        return []


# ---------------------------------------------------------------------------
# Portal performance
# ---------------------------------------------------------------------------

def compute_portal_stats(entries: list[dict]) -> dict:
    """Group submitted/acknowledged/interview/outcome entries by portal.

    Returns {"portals": {portal_name: {"submitted": int, "responses": int,
    "interviews": int, "response_rate": float}}}
    """
    submitted_statuses = {"submitted", "acknowledged", "interview", "outcome"}
    portals: dict[str, dict] = {}

    for entry in entries:
        status = entry.get("status", "")
        if status not in submitted_statuses:
            continue

        target = entry.get("target", {})
        portal = target.get("portal", "unknown") if isinstance(target, dict) else "unknown"

        if portal not in portals:
            portals[portal] = {"submitted": 0, "responses": 0, "interviews": 0, "outcomes": 0}

        portals[portal]["submitted"] += 1

        conversion = entry.get("conversion", {})
        if isinstance(conversion, dict) and conversion.get("response_received"):
            portals[portal]["responses"] += 1

        if status == "interview":
            portals[portal]["interviews"] += 1

        if status == "outcome" or entry.get("outcome"):
            portals[portal]["outcomes"] += 1

    # Calculate response rates
    for stats in portals.values():
        if stats["submitted"] > 0:
            stats["response_rate"] = stats["responses"] / stats["submitted"]
        else:
            stats["response_rate"] = 0.0

    return {"portals": portals}


# ---------------------------------------------------------------------------
# Identity position performance
# ---------------------------------------------------------------------------

def compute_position_stats(entries: list[dict]) -> dict:
    """Group entries by fit.identity_position.

    Returns {"positions": {position: {"total": int, "submitted": int,
    "accepted": int, "rejected": int}}}
    """
    positions: dict[str, dict] = {}

    for entry in entries:
        fit = entry.get("fit", {})
        position = fit.get("identity_position", "unset") if isinstance(fit, dict) else "unset"

        if position not in positions:
            positions[position] = {"total": 0, "submitted": 0, "accepted": 0, "rejected": 0}

        positions[position]["total"] += 1

        status = entry.get("status", "")
        if status in ("submitted", "acknowledged", "interview", "outcome"):
            positions[position]["submitted"] += 1

        outcome = entry.get("outcome")
        if outcome == "accepted":
            positions[position]["accepted"] += 1
        elif outcome == "rejected":
            positions[position]["rejected"] += 1

    return {"positions": positions}


# ---------------------------------------------------------------------------
# Track performance
# ---------------------------------------------------------------------------

def compute_track_stats(entries: list[dict]) -> dict:
    """Group entries by track.

    Returns {"tracks": {track: {"total": int, "submitted": int,
    "avg_score": float, "avg_days_to_response": float | None}}}
    """
    tracks: dict[str, dict] = {}

    for entry in entries:
        track = entry.get("track", "unknown")

        if track not in tracks:
            tracks[track] = {
                "total": 0,
                "submitted": 0,
                "scores": [],
                "response_days": [],
            }

        tracks[track]["total"] += 1

        status = entry.get("status", "")
        if status in ("submitted", "acknowledged", "interview", "outcome"):
            tracks[track]["submitted"] += 1

        score = get_score(entry)
        if score > 0:
            tracks[track]["scores"].append(score)

        conversion = entry.get("conversion", {})
        if isinstance(conversion, dict):
            ttr = conversion.get("time_to_response_days")
            if ttr is not None and isinstance(ttr, (int, float)):
                tracks[track]["response_days"].append(ttr)

    # Compute averages and clean up internal lists
    result: dict[str, dict] = {}
    for track, data in tracks.items():
        avg_score = sum(data["scores"]) / len(data["scores"]) if data["scores"] else 0.0
        if data["response_days"]:
            avg_days = sum(data["response_days"]) / len(data["response_days"])
        else:
            avg_days = None

        result[track] = {
            "total": data["total"],
            "submitted": data["submitted"],
            "avg_score": round(avg_score, 1),
            "avg_days_to_response": round(avg_days, 1) if avg_days is not None else None,
        }

    return {"tracks": result}


# ---------------------------------------------------------------------------
# Response time analysis
# ---------------------------------------------------------------------------

def compute_response_times(entries: list[dict]) -> dict:
    """Collect time_to_response_days and compute statistics.

    Returns {"overall": {"mean": float, "median": float, "min": int,
    "max": int, "n": int}, "by_portal": {portal: {...}}}
    """
    by_portal: dict[str, list[float]] = {}
    all_times: list[float] = []

    for entry in entries:
        conversion = entry.get("conversion", {})
        if not isinstance(conversion, dict):
            continue
        ttr = conversion.get("time_to_response_days")
        if ttr is None or not isinstance(ttr, (int, float)):
            continue

        all_times.append(float(ttr))

        target = entry.get("target", {})
        portal = target.get("portal", "unknown") if isinstance(target, dict) else "unknown"
        by_portal.setdefault(portal, []).append(float(ttr))

    def _stats(times: list[float]) -> dict:
        if not times:
            return {"mean": 0.0, "median": 0.0, "min": 0, "max": 0, "n": 0}
        sorted_t = sorted(times)
        n = len(sorted_t)
        if n % 2 == 0:
            median = (sorted_t[n // 2 - 1] + sorted_t[n // 2]) / 2.0
        else:
            median = sorted_t[n // 2]
        return {
            "mean": round(sum(sorted_t) / n, 1),
            "median": round(median, 1),
            "min": int(sorted_t[0]),
            "max": int(sorted_t[-1]),
            "n": n,
        }

    portal_stats = {portal: _stats(times) for portal, times in by_portal.items()}

    return {
        "overall": _stats(all_times),
        "by_portal": portal_stats,
    }


# ---------------------------------------------------------------------------
# Block effectiveness
# ---------------------------------------------------------------------------

def compute_block_effectiveness(entries: list[dict]) -> dict:
    """Track which blocks appear in accepted vs rejected entries.

    Returns {"blocks": {block_path: {"used_in": int, "accepted": int,
    "rejected": int, "rate": float}}}
    """
    blocks: dict[str, dict] = {}

    for entry in entries:
        outcome = entry.get("outcome")
        if not outcome:
            continue

        submission = entry.get("submission", {})
        if not isinstance(submission, dict):
            continue
        blocks_used = submission.get("blocks_used")
        if not blocks_used or not isinstance(blocks_used, list):
            continue

        for block_path in blocks_used:
            if not isinstance(block_path, str):
                continue
            if block_path not in blocks:
                blocks[block_path] = {"used_in": 0, "accepted": 0, "rejected": 0}
            blocks[block_path]["used_in"] += 1
            if outcome == "accepted":
                blocks[block_path]["accepted"] += 1
            elif outcome == "rejected":
                blocks[block_path]["rejected"] += 1

    # Calculate acceptance rates
    for stats in blocks.values():
        total_outcomes = stats["accepted"] + stats["rejected"]
        stats["rate"] = stats["accepted"] / total_outcomes if total_outcomes > 0 else 0.0

    return {"blocks": blocks}


# ---------------------------------------------------------------------------
# Portal detail view
# ---------------------------------------------------------------------------

def show_portal_detail(portal_name: str, entries: list[dict]) -> str:
    """Deep dive on a single portal: entries, timelines, outcomes."""
    lines = []
    lines.append(f"PORTAL DETAIL: {portal_name.upper()}")
    lines.append("=" * 60)

    portal_entries = []
    for entry in entries:
        target = entry.get("target", {})
        portal = target.get("portal", "") if isinstance(target, dict) else ""
        if portal.lower() == portal_name.lower():
            portal_entries.append(entry)

    if not portal_entries:
        lines.append(f"No entries found for portal '{portal_name}'.")
        return "\n".join(lines)

    # Summary counts
    status_counts = Counter(e.get("status", "?") for e in portal_entries)
    lines.append(f"\nTotal entries: {len(portal_entries)}")
    for status, count in sorted(status_counts.items()):
        lines.append(f"  {status:<20s} {count}")

    # Submitted entries detail
    submitted = [
        e for e in portal_entries
        if e.get("status") in ("submitted", "acknowledged", "interview", "outcome")
    ]
    if submitted:
        lines.append(f"\nSubmitted entries ({len(submitted)}):")
        lines.append(f"  {'Entry':<35s} {'Status':<14s} {'Days':>5s}  {'Score':>5s}  Outcome")
        lines.append("  " + "-" * 75)
        for entry in submitted:
            entry_id = entry.get("id", "?")
            status = entry.get("status", "?")
            days = co_days_since_submission(entry)
            days_str = str(days) if days is not None else "?"
            score = get_score(entry)
            outcome = entry.get("outcome", "—")
            lines.append(
                f"  {entry_id:<35s} {status:<14s} {days_str:>5s}  {score:>5.1f}  {outcome}"
            )

    # Response times for this portal
    times = []
    for entry in portal_entries:
        conversion = entry.get("conversion", {})
        if isinstance(conversion, dict):
            ttr = conversion.get("time_to_response_days")
            if ttr is not None and isinstance(ttr, (int, float)):
                times.append(float(ttr))

    if times:
        sorted_t = sorted(times)
        n = len(sorted_t)
        mean_t = sum(sorted_t) / n
        if n % 2 == 0:
            median_t = (sorted_t[n // 2 - 1] + sorted_t[n // 2]) / 2.0
        else:
            median_t = sorted_t[n // 2]
        lines.append(f"\nResponse times (n={n}):")
        lines.append(f"  Mean: {mean_t:.1f}d | Median: {median_t:.1f}d | Range: {sorted_t[0]:.0f}-{sorted_t[-1]:.0f}d")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Weekly trends
# ---------------------------------------------------------------------------

def compute_weekly_trends(entries: list[dict]) -> str:
    """Show submission counts by week for the last 8 weeks."""
    lines = []
    lines.append("WEEKLY SUBMISSION TRENDS")
    lines.append("=" * 60)

    today = date.today()
    weeks: dict[str, int] = {}

    for entry in entries:
        timeline = entry.get("timeline", {})
        if not isinstance(timeline, dict):
            continue
        sub_date = parse_date(timeline.get("submitted"))
        if not sub_date:
            continue
        delta = (today - sub_date).days
        if delta > 56:  # 8 weeks
            continue
        week_num = delta // 7
        week_label = f"Week -{week_num}" if week_num > 0 else "This week"
        weeks[week_label] = weeks.get(week_label, 0) + 1

    if not weeks:
        lines.append("No submissions in the last 8 weeks.")
        return "\n".join(lines)

    # Display in chronological order (oldest first)
    all_labels = [f"Week -{i}" for i in range(7, -1, -1)]
    all_labels[-1] = "This week"

    max_count = max(weeks.values()) if weeks else 1
    for label in all_labels:
        count = weeks.get(label, 0)
        bar = "#" * int(20 * count / max_count) if max_count > 0 and count > 0 else ""
        lines.append(f"  {label:<12s} {count:>3}  {bar}")

    total = sum(weeks.values())
    avg = total / min(8, len([w for w in weeks.values() if w > 0]) or 1)
    lines.append(f"\n  Total: {total} | Avg/week: {avg:.1f}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main dashboard generator
# ---------------------------------------------------------------------------

def generate_dashboard(entries: list[dict] | None = None) -> str:
    """Generate the unified conversion intelligence dashboard.

    Aggregates portal, position, track, response time, block effectiveness,
    calibration status, and hypothesis patterns into a formatted report.
    """
    if entries is None:
        entries = load_entries(dirs=ALL_PIPELINE_DIRS, include_filepath=True)

    lines = []
    lines.append(f"CONVERSION INTELLIGENCE DASHBOARD — {date.today().isoformat()}")
    lines.append("=" * 70)

    # --- Portal Performance ---
    portal_data = compute_portal_stats(entries)
    portals = portal_data["portals"]

    lines.append("\nPORTAL PERFORMANCE")
    lines.append("-" * 70)
    if portals:
        lines.append(f"  {'Portal':<20s} {'Submitted':>9s} {'Responses':>10s} {'Interviews':>11s} {'Rate':>7s}")
        lines.append("  " + "-" * 60)
        for portal, stats in sorted(portals.items(), key=lambda x: -x[1]["submitted"]):
            rate_str = f"{stats['response_rate']:.0%}"
            lines.append(
                f"  {portal:<20s} {stats['submitted']:>9} {stats['responses']:>10} "
                f"{stats['interviews']:>11} {rate_str:>7s}"
            )
    else:
        lines.append("  No submitted entries found.")

    # --- Identity Position Performance ---
    position_data = compute_position_stats(entries)
    positions = position_data["positions"]

    lines.append("\nIDENTITY POSITION PERFORMANCE")
    lines.append("-" * 70)
    if positions:
        lines.append(f"  {'Position':<28s} {'Total':>6s} {'Submitted':>10s} {'Accepted':>9s} {'Rejected':>9s}")
        lines.append("  " + "-" * 65)
        for position, stats in sorted(positions.items(), key=lambda x: -x[1]["total"]):
            lines.append(
                f"  {position:<28s} {stats['total']:>6} {stats['submitted']:>10} "
                f"{stats['accepted']:>9} {stats['rejected']:>9}"
            )
    else:
        lines.append("  No entries found.")

    # --- Track Performance ---
    track_data = compute_track_stats(entries)
    tracks = track_data["tracks"]

    lines.append("\nTRACK PERFORMANCE")
    lines.append("-" * 70)
    if tracks:
        lines.append(f"  {'Track':<16s} {'Total':>6s} {'Submitted':>10s} {'Avg Score':>10s} {'Avg Response':>13s}")
        lines.append("  " + "-" * 58)
        for track, stats in sorted(tracks.items(), key=lambda x: -x[1]["total"]):
            avg_resp = f"{stats['avg_days_to_response']}d" if stats["avg_days_to_response"] is not None else "—"
            lines.append(
                f"  {track:<16s} {stats['total']:>6} {stats['submitted']:>10} "
                f"{stats['avg_score']:>10.1f} {avg_resp:>13s}"
            )
    else:
        lines.append("  No entries found.")

    # --- Response Time Analysis ---
    response_data = compute_response_times(entries)
    overall = response_data["overall"]

    lines.append("\nRESPONSE TIME ANALYSIS")
    lines.append("-" * 70)
    if overall["n"] > 0:
        lines.append(
            f"  Overall (n={overall['n']}): mean={overall['mean']}d, "
            f"median={overall['median']}d, range={overall['min']}-{overall['max']}d"
        )
        by_portal = response_data["by_portal"]
        if by_portal:
            for portal, stats in sorted(by_portal.items()):
                lines.append(
                    f"  {portal}: mean={stats['mean']}d, median={stats['median']}d "
                    f"(n={stats['n']})"
                )
    else:
        lines.append("  No response time data available.")

    # --- Block Effectiveness ---
    block_data = compute_block_effectiveness(entries)
    blocks = block_data["blocks"]

    lines.append("\nBLOCK EFFECTIVENESS")
    lines.append("-" * 70)
    if blocks:
        lines.append(f"  {'Block':<40s} {'Used':>5s} {'Acc':>4s} {'Rej':>4s} {'Rate':>6s}")
        lines.append("  " + "-" * 62)
        for block_path, stats in sorted(blocks.items(), key=lambda x: -x[1]["rate"]):
            rate_str = f"{stats['rate']:.0%}"
            lines.append(
                f"  {block_path:<40s} {stats['used_in']:>5} {stats['accepted']:>4} "
                f"{stats['rejected']:>4} {rate_str:>6s}"
            )
    else:
        lines.append("  No block effectiveness data (need outcomes with blocks_used).")

    # --- Scoring Calibration Status ---
    lines.append("\nSCORING CALIBRATION STATUS")
    lines.append("-" * 70)
    calibration = load_calibration()
    if calibration:
        lines.append(f"  Calibration: ACTIVE (confidence={calibration.get('confidence', '?')})")
        lines.append(f"  Sample size: {calibration.get('sample_size', '?')}")
        lines.append(f"  Generated: {calibration.get('generated', '?')}")
        if calibration.get("adjustments"):
            changed = [
                dim for dim, adj in calibration["adjustments"].items()
                if adj != "keep"
            ]
            if changed:
                lines.append(f"  Adjusted dimensions: {', '.join(changed)}")
    else:
        outcome_data = collect_outcome_data()
        lines.append(f"  Calibration: PENDING (need {10 - len(outcome_data)} more outcomes)")
        lines.append(f"  Outcomes collected: {len(outcome_data)}")
        if outcome_data:
            analysis = analyze_dimension_accuracy(outcome_data)
            signals = [
                dim for dim, info in analysis.items()
                if info.get("signal") not in ("neutral", "insufficient_data")
            ]
            if signals:
                lines.append(f"  Early signals: {', '.join(signals)}")

    # --- Hypothesis Patterns ---
    lines.append("\nHYPOTHESIS PATTERNS")
    lines.append("-" * 70)
    hypotheses = load_hypotheses()
    if hypotheses:
        category_counts = Counter(h.get("category", "other") for h in hypotheses)
        lines.append(f"  Total hypotheses: {len(hypotheses)}")
        lines.append("  Top categories:")
        for cat, count in category_counts.most_common(5):
            lines.append(f"    {cat:<25s} {count}")

        # Outcome distribution among hypotheses
        outcome_counts = Counter(h.get("outcome") or "pending" for h in hypotheses)
        lines.append("  Outcome distribution:")
        for outcome, count in outcome_counts.most_common():
            lines.append(f"    {outcome:<15s} {count}")
    else:
        lines.append("  No hypotheses recorded yet.")
        lines.append("  Capture: python scripts/feedback_capture.py --entry <id>")

    # --- Data Quality ---
    lines.append("\nDATA QUALITY")
    lines.append("-" * 70)
    total_entries = len(entries)
    submitted_count = sum(
        1 for e in entries
        if e.get("status") in ("submitted", "acknowledged", "interview", "outcome")
    )
    with_outcomes = sum(1 for e in entries if e.get("outcome"))
    with_scores = sum(1 for e in entries if get_score(e) > 0)
    with_response_time = sum(
        1 for e in entries
        if isinstance(e.get("conversion", {}), dict)
        and e.get("conversion", {}).get("time_to_response_days") is not None
    )

    lines.append(f"  Total entries:        {total_entries}")
    lines.append(f"  Submitted:            {submitted_count}")
    lines.append(f"  With outcomes:        {with_outcomes}")
    lines.append(f"  With scores:          {with_scores}")
    lines.append(f"  With response times:  {with_response_time}")

    # Confidence assessment
    if with_outcomes >= 20:
        confidence = "HIGH — sufficient data for reliable analysis"
    elif with_outcomes >= 10:
        confidence = "MODERATE — trends emerging, confirm with more data"
    elif with_outcomes >= 5:
        confidence = "LOW — directional signals only"
    else:
        confidence = "VERY LOW — insufficient data, collect more outcomes"
    lines.append(f"  Confidence level:     {confidence}")

    lines.append("\n" + "=" * 70)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def generate_dashboard_data(entries: list[dict]) -> dict:
    """Generate structured dashboard data for JSON output."""
    return {
        "portals": compute_portal_stats(entries),
        "positions": compute_position_stats(entries),
        "tracks": compute_track_stats(entries),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Unified conversion intelligence dashboard",
    )
    parser.add_argument(
        "--portal",
        help="Show detailed view for a specific portal",
    )
    parser.add_argument(
        "--weekly",
        action="store_true",
        help="Show weekly submission trends",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save report to signals/conversion-dashboard.md",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON instead of formatted text",
    )
    args = parser.parse_args()

    entries = load_entries(dirs=ALL_PIPELINE_DIRS, include_filepath=True)

    if args.json:
        import json
        data = generate_dashboard_data(entries)
        print(json.dumps(data, indent=2, default=str))
        return

    if args.portal:
        report = show_portal_detail(args.portal, entries)
    elif args.weekly:
        report = compute_weekly_trends(entries)
    else:
        report = generate_dashboard(entries)

    print(report)

    if args.save:
        SIGNALS_DIR.mkdir(parents=True, exist_ok=True)
        out_path = SIGNALS_DIR / "conversion-dashboard.md"
        with open(out_path, "w") as f:
            f.write(report + "\n")
        print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
