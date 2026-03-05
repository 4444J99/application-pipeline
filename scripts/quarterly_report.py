#!/usr/bin/env python3
"""Quarterly "State of Applications" analytics report.

Generates a comprehensive markdown report covering conversion rates,
block ROI, network proximity correlation, scoring dimension accuracy,
seasonal patterns, pipeline velocity, and data-driven recommendations.

Usage:
    python scripts/quarterly_report.py                 # Full report to stdout
    python scripts/quarterly_report.py --save          # Save to strategy/quarterly-report-YYYY-QN.md
    python scripts/quarterly_report.py --json          # JSON output
    python scripts/quarterly_report.py --period 90     # Last N days (default: 90)
    python scripts/quarterly_report.py --compare       # Compare current quarter vs previous
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import yaml
from pipeline_lib import (
    ALL_PIPELINE_DIRS,
    DIMENSION_ORDER,
    PIPELINE_DIR_CLOSED,
    REPO_ROOT,
    SIGNALS_DIR,
    load_entries,
    parse_date,
)

STRATEGY_DIR = REPO_ROOT / "strategy"

# Statuses that indicate a submission reached the portal
SUBMITTED_STATUSES = {"submitted", "acknowledged", "interview", "outcome"}

# Terminal negative outcomes
NEGATIVE_OUTCOMES = {"rejected", "expired", "withdrawn"}


def _quarter_label(d: date) -> str:
    """Return 'YYYY-QN' label for a date."""
    q = (d.month - 1) // 3 + 1
    return f"{d.year}-Q{q}"


def _quarter_start(d: date) -> date:
    """Return the first day of the quarter containing date d."""
    q = (d.month - 1) // 3
    return date(d.year, q * 3 + 1, 1)


def load_all_entries() -> list[dict]:
    """Load all pipeline entries including closed."""
    dirs = list(ALL_PIPELINE_DIRS) + [PIPELINE_DIR_CLOSED]
    # Deduplicate in case PIPELINE_DIR_CLOSED is already in ALL_PIPELINE_DIRS
    seen = set()
    unique_dirs = []
    for d in dirs:
        if d not in seen:
            seen.add(d)
            unique_dirs.append(d)
    return load_entries(dirs=unique_dirs, include_filepath=True)


def load_conversion_log() -> list[dict]:
    """Load conversion log entries from signals/conversion-log.yaml."""
    log_path = SIGNALS_DIR / "conversion-log.yaml"
    if not log_path.exists():
        return []
    with open(log_path) as f:
        data = yaml.safe_load(f) or {}
    if isinstance(data, dict):
        entries = data.get("entries", [])
        return entries if isinstance(entries, list) else []
    return data if isinstance(data, list) else []


def _get_submitted_date(entry: dict) -> date | None:
    """Extract submission date from entry timeline."""
    timeline = entry.get("timeline", {})
    if isinstance(timeline, dict):
        return parse_date(timeline.get("submitted"))
    return None


def _get_identity_position(entry: dict) -> str:
    """Extract identity position from entry."""
    fit = entry.get("fit", {})
    if isinstance(fit, dict):
        return fit.get("identity_position") or "unknown"
    return "unknown"


def _get_portal(entry: dict) -> str:
    """Extract portal type from entry."""
    target = entry.get("target", {})
    if isinstance(target, dict):
        return target.get("portal") or "unknown"
    return "unknown"


def _get_outcome(entry: dict) -> str | None:
    """Extract outcome from entry."""
    return entry.get("outcome")


def _get_score(entry: dict) -> float | None:
    """Extract overall fit score from entry."""
    fit = entry.get("fit", {})
    if isinstance(fit, dict):
        raw = fit.get("score")
        if raw is not None:
            try:
                return float(raw)
            except (ValueError, TypeError):
                pass
    return None


def _get_dimensions(entry: dict) -> dict:
    """Extract scoring dimensions from entry."""
    fit = entry.get("fit", {})
    if isinstance(fit, dict):
        dims = fit.get("dimensions", {})
        if isinstance(dims, dict):
            return dims
    return {}


def _get_network_proximity(entry: dict) -> int | None:
    """Extract network_proximity dimension score from entry."""
    dims = _get_dimensions(entry)
    val = dims.get("network_proximity")
    if val is not None:
        try:
            return int(val)
        except (ValueError, TypeError):
            pass
    return None


def _get_blocks_used(entry: dict) -> list[str]:
    """Extract list of block paths from entry submission."""
    sub = entry.get("submission", {})
    if not isinstance(sub, dict):
        return []
    blocks = sub.get("blocks_used", {})
    if isinstance(blocks, dict):
        return [v for v in blocks.values() if isinstance(v, str)]
    if isinstance(blocks, list):
        return [b for b in blocks if isinstance(b, str)]
    return []


def _is_submitted(entry: dict) -> bool:
    """Check if entry has reached submitted status or beyond."""
    return entry.get("status", "") in SUBMITTED_STATUSES


def filter_by_period(entries: list[dict], period_days: int) -> list[dict]:
    """Filter entries to those with submission date within the last N days."""
    cutoff = date.today() - timedelta(days=period_days)
    result = []
    for entry in entries:
        sub_date = _get_submitted_date(entry)
        if sub_date and sub_date >= cutoff:
            result.append(entry)
        elif not sub_date:
            # Include non-submitted entries based on date_added or researched
            timeline = entry.get("timeline", {})
            if isinstance(timeline, dict):
                added = parse_date(timeline.get("date_added")) or parse_date(timeline.get("researched"))
                if added and added >= cutoff:
                    result.append(entry)
    return result


def filter_by_quarter(entries: list[dict], quarter_start: date, quarter_end: date) -> list[dict]:
    """Filter entries to those submitted within a specific quarter."""
    result = []
    for entry in entries:
        sub_date = _get_submitted_date(entry)
        if sub_date and quarter_start <= sub_date < quarter_end:
            result.append(entry)
    return result


# --- Report sections ---


def executive_summary(entries: list[dict], period_days: int) -> dict:
    """Generate executive summary statistics."""
    total = len(entries)
    submitted = [e for e in entries if _is_submitted(e)]
    outcomes = [e for e in submitted if _get_outcome(e)]
    accepted = [e for e in outcomes if _get_outcome(e) == "accepted"]
    rejected = [e for e in outcomes if _get_outcome(e) in NEGATIVE_OUTCOMES]
    pending = [e for e in submitted if not _get_outcome(e)]

    conversion_rate = (len(accepted) / len(submitted) * 100) if submitted else 0.0

    # Submissions per month
    months = max(period_days / 30.0, 1.0)
    subs_per_month = len(submitted) / months

    # Active pipeline (non-terminal entries)
    active = [e for e in entries if e.get("status") in (
        "research", "qualified", "drafting", "staged", "deferred",
        "submitted", "acknowledged", "interview",
    )]

    # Response rate: entries that got any response (acknowledged, interview, or outcome with feedback)
    responded = [e for e in submitted if e.get("status") in ("acknowledged", "interview", "outcome")]
    response_rate = (len(responded) / len(submitted) * 100) if submitted else 0.0

    return {
        "total_entries": total,
        "submitted": len(submitted),
        "accepted": len(accepted),
        "rejected": len(rejected),
        "pending": len(pending),
        "conversion_rate": round(conversion_rate, 1),
        "response_rate": round(response_rate, 1),
        "submissions_per_month": round(subs_per_month, 1),
        "active_pipeline_size": len(active),
        "period_days": period_days,
    }


def conversion_by_position(entries: list[dict]) -> list[dict]:
    """Conversion rates grouped by identity_position."""
    groups: dict[str, dict] = defaultdict(lambda: {
        "submitted": 0, "accepted": 0, "rejected": 0, "pending": 0, "responded": 0,
    })

    for entry in entries:
        if not _is_submitted(entry):
            continue
        pos = _get_identity_position(entry)
        groups[pos]["submitted"] += 1
        outcome = _get_outcome(entry)
        if outcome == "accepted":
            groups[pos]["accepted"] += 1
        elif outcome in NEGATIVE_OUTCOMES:
            groups[pos]["rejected"] += 1
        else:
            groups[pos]["pending"] += 1
        if entry.get("status") in ("acknowledged", "interview", "outcome"):
            groups[pos]["responded"] += 1

    results = []
    for pos, data in sorted(groups.items(), key=lambda x: -x[1]["submitted"]):
        rate = (data["accepted"] / data["submitted"] * 100) if data["submitted"] else 0
        resp_rate = (data["responded"] / data["submitted"] * 100) if data["submitted"] else 0
        results.append({
            "position": pos,
            "conversion_rate": round(rate, 1),
            "response_rate": round(resp_rate, 1),
            **data,
        })
    return results


def conversion_by_channel(entries: list[dict]) -> list[dict]:
    """Conversion rates grouped by portal type."""
    groups: dict[str, dict] = defaultdict(lambda: {
        "submitted": 0, "accepted": 0, "rejected": 0, "pending": 0, "responded": 0,
    })

    for entry in entries:
        if not _is_submitted(entry):
            continue
        portal = _get_portal(entry)
        groups[portal]["submitted"] += 1
        outcome = _get_outcome(entry)
        if outcome == "accepted":
            groups[portal]["accepted"] += 1
        elif outcome in NEGATIVE_OUTCOMES:
            groups[portal]["rejected"] += 1
        else:
            groups[portal]["pending"] += 1
        if entry.get("status") in ("acknowledged", "interview", "outcome"):
            groups[portal]["responded"] += 1

    results = []
    for portal, data in sorted(groups.items(), key=lambda x: -x[1]["submitted"]):
        rate = (data["accepted"] / data["submitted"] * 100) if data["submitted"] else 0
        resp_rate = (data["responded"] / data["submitted"] * 100) if data["submitted"] else 0
        results.append({
            "portal": portal,
            "conversion_rate": round(rate, 1),
            "response_rate": round(resp_rate, 1),
            **data,
        })
    return results


def block_roi(entries: list[dict]) -> list[dict]:
    """Block ROI: which blocks appear in accepted vs rejected submissions."""
    block_outcomes: dict[str, dict] = defaultdict(lambda: {
        "total": 0, "accepted": 0, "rejected": 0, "pending": 0,
    })

    for entry in entries:
        if not _is_submitted(entry):
            continue
        blocks = _get_blocks_used(entry)
        outcome = _get_outcome(entry)
        for block in blocks:
            block_outcomes[block]["total"] += 1
            if outcome == "accepted":
                block_outcomes[block]["accepted"] += 1
            elif outcome in NEGATIVE_OUTCOMES:
                block_outcomes[block]["rejected"] += 1
            else:
                block_outcomes[block]["pending"] += 1

    results = []
    for block, data in block_outcomes.items():
        acceptance_rate = (data["accepted"] / data["total"] * 100) if data["total"] else 0
        rejection_rate = (data["rejected"] / data["total"] * 100) if data["total"] else 0
        results.append({
            "block": block,
            "acceptance_rate": round(acceptance_rate, 1),
            "rejection_rate": round(rejection_rate, 1),
            **data,
        })
    # Sort by acceptance rate descending, then by volume
    results.sort(key=lambda x: (-x["acceptance_rate"], -x["total"]))
    return results


def network_proximity_correlation(entries: list[dict]) -> dict:
    """Average network_proximity score for each outcome category."""
    buckets: dict[str, list[int]] = defaultdict(list)

    for entry in entries:
        if not _is_submitted(entry):
            continue
        net = _get_network_proximity(entry)
        if net is None:
            continue
        outcome = _get_outcome(entry)
        if outcome == "accepted":
            buckets["accepted"].append(net)
        elif outcome in NEGATIVE_OUTCOMES:
            buckets["rejected"].append(net)
        else:
            buckets["pending"].append(net)

    result = {}
    for category, scores in sorted(buckets.items()):
        avg = sum(scores) / len(scores) if scores else 0
        result[category] = {
            "average": round(avg, 2),
            "count": len(scores),
            "min": min(scores) if scores else 0,
            "max": max(scores) if scores else 0,
        }
    return result


def scoring_dimension_accuracy(entries: list[dict]) -> list[dict]:
    """For each scoring dimension, compare avg score of accepted vs rejected."""
    dim_buckets: dict[str, dict[str, list[float]]] = {
        dim: {"accepted": [], "rejected": []}
        for dim in DIMENSION_ORDER
    }

    for entry in entries:
        if not _is_submitted(entry):
            continue
        outcome = _get_outcome(entry)
        if outcome not in ("accepted", *NEGATIVE_OUTCOMES):
            continue
        bucket_key = "accepted" if outcome == "accepted" else "rejected"
        dims = _get_dimensions(entry)
        for dim in DIMENSION_ORDER:
            val = dims.get(dim)
            if val is not None:
                try:
                    dim_buckets[dim][bucket_key].append(float(val))
                except (ValueError, TypeError):
                    pass

    results = []
    for dim in DIMENSION_ORDER:
        acc_scores = dim_buckets[dim]["accepted"]
        rej_scores = dim_buckets[dim]["rejected"]
        avg_acc = sum(acc_scores) / len(acc_scores) if acc_scores else 0
        avg_rej = sum(rej_scores) / len(rej_scores) if rej_scores else 0
        delta = round(avg_acc - avg_rej, 2)
        results.append({
            "dimension": dim,
            "avg_accepted": round(avg_acc, 2),
            "avg_rejected": round(avg_rej, 2),
            "delta": delta,
            "n_accepted": len(acc_scores),
            "n_rejected": len(rej_scores),
            "predictive": delta > 0.5 if (acc_scores and rej_scores) else None,
        })
    return results


def seasonal_patterns(entries: list[dict]) -> dict:
    """Submissions and outcomes by week and month."""
    weekly: dict[str, dict] = defaultdict(lambda: {"submitted": 0, "outcomes": 0, "accepted": 0})
    monthly: dict[str, dict] = defaultdict(lambda: {"submitted": 0, "outcomes": 0, "accepted": 0})

    for entry in entries:
        if not _is_submitted(entry):
            continue
        sub_date = _get_submitted_date(entry)
        if not sub_date:
            continue

        # Week (ISO Monday start)
        week_start = sub_date - timedelta(days=sub_date.weekday())
        week_label = week_start.isoformat()
        weekly[week_label]["submitted"] += 1

        # Month
        month_label = sub_date.strftime("%Y-%m")
        monthly[month_label]["submitted"] += 1

        outcome = _get_outcome(entry)
        if outcome:
            weekly[week_label]["outcomes"] += 1
            monthly[month_label]["outcomes"] += 1
            if outcome == "accepted":
                weekly[week_label]["accepted"] += 1
                monthly[month_label]["accepted"] += 1

    return {
        "weekly": [{"week": k, **v} for k, v in sorted(weekly.items())],
        "monthly": [{"month": k, **v} for k, v in sorted(monthly.items())],
    }


def pipeline_velocity(entries: list[dict]) -> list[dict]:
    """Average days spent at each pipeline stage."""
    # Track time between consecutive timeline events
    stage_transitions = [
        ("researched", "qualified", "research"),
        ("qualified", "drafting_started", "qualified"),
        ("drafting_started", "staged", "drafting"),
        ("staged", "submitted", "staged"),
        ("submitted", "response_date", "submitted_to_response"),
    ]

    stage_durations: dict[str, list[int]] = defaultdict(list)

    for entry in entries:
        timeline = entry.get("timeline", {})
        if not isinstance(timeline, dict):
            continue

        for from_key, to_key, stage_name in stage_transitions:
            from_date = parse_date(timeline.get(from_key))
            to_date = parse_date(timeline.get(to_key))
            if from_date and to_date:
                days = (to_date - from_date).days
                if days >= 0:
                    stage_durations[stage_name].append(days)

        # Also check conversion response time
        conv = entry.get("conversion", {})
        if isinstance(conv, dict):
            ttr = conv.get("time_to_response_days")
            if ttr is not None:
                try:
                    stage_durations["submitted_to_response"].append(int(ttr))
                except (ValueError, TypeError):
                    pass

    results = []
    for stage_name in ["research", "qualified", "drafting", "staged", "submitted_to_response"]:
        durations = stage_durations.get(stage_name, [])
        if durations:
            avg = sum(durations) / len(durations)
            median = sorted(durations)[len(durations) // 2]
            results.append({
                "stage": stage_name,
                "avg_days": round(avg, 1),
                "median_days": median,
                "min_days": min(durations),
                "max_days": max(durations),
                "count": len(durations),
            })
        else:
            results.append({
                "stage": stage_name,
                "avg_days": 0,
                "median_days": 0,
                "min_days": 0,
                "max_days": 0,
                "count": 0,
            })
    return results


def time_to_outcome(entries: list[dict]) -> dict:
    """Compute submission-to-outcome benchmarks by track and portal.

    Returns median, mean, min, max days from submitted → outcome date,
    grouped by track and portal.
    """
    by_track: dict[str, list[int]] = defaultdict(list)
    by_portal: dict[str, list[int]] = defaultdict(list)
    all_durations: list[int] = []

    for entry in entries:
        outcome = _get_outcome(entry)
        if not outcome or outcome not in {"accepted", "rejected", "withdrawn", "expired"}:
            continue
        timeline = entry.get("timeline", {})
        if not isinstance(timeline, dict):
            continue
        submitted_date = parse_date(timeline.get("submitted"))
        outcome_date = parse_date(timeline.get("outcome_date"))
        if not submitted_date or not outcome_date:
            continue
        days = (outcome_date - submitted_date).days
        if days < 0:
            continue
        all_durations.append(days)
        track = entry.get("track", "unknown")
        by_track[track].append(days)
        by_portal[_get_portal(entry)].append(days)

    def _stats(durations: list[int]) -> dict:
        if not durations:
            return {"median": 0, "mean": 0, "min": 0, "max": 0, "count": 0}
        s = sorted(durations)
        return {
            "median": s[len(s) // 2],
            "mean": round(sum(s) / len(s), 1),
            "min": s[0],
            "max": s[-1],
            "count": len(s),
        }

    return {
        "overall": _stats(all_durations),
        "by_track": {t: _stats(d) for t, d in sorted(by_track.items())},
        "by_portal": {p: _stats(d) for p, d in sorted(by_portal.items())},
    }


def generate_recommendations(
    summary: dict,
    position_data: list[dict],
    channel_data: list[dict],
    network_data: dict,
    dimension_data: list[dict],
    block_data: list[dict],
) -> list[str]:
    """Generate data-driven recommendations from analysis results."""
    recs = []

    # Conversion rate assessment
    if summary["conversion_rate"] == 0 and summary["submitted"] > 5:
        recs.append(
            f"Zero acceptances from {summary['submitted']} submissions. "
            "Prioritize warm introductions and referral paths over cold applications."
        )

    # Response rate insights
    if summary["response_rate"] > 0 and summary["conversion_rate"] == 0:
        recs.append(
            f"Response rate is {summary['response_rate']}% but conversion is 0%. "
            "Responses indicate materials are being reviewed; refine resume targeting "
            "and follow-up cadence."
        )

    # Network proximity correlation
    if "rejected" in network_data and "pending" in network_data:
        rej_avg = network_data["rejected"]["average"]
        pen_avg = network_data["pending"]["average"]
        if pen_avg > rej_avg + 1:
            recs.append(
                f"Pending entries have avg network_proximity {pen_avg} vs "
                f"rejected {rej_avg}. Higher network proximity correlates "
                "with longer consideration cycles."
            )
    if "accepted" in network_data:
        acc_avg = network_data["accepted"]["average"]
        if acc_avg >= 5:
            recs.append(
                f"Accepted entries average network_proximity {acc_avg}. "
                "Increase network_proximity weight: entries with score >=5 "
                "show stronger conversion."
            )

    # Position-level insights
    for pos in position_data:
        if pos["submitted"] >= 3 and pos["response_rate"] == 0:
            recs.append(
                f"Position '{pos['position']}' has {pos['submitted']} submissions "
                "with 0% response rate. Consider pivoting framing or targeting "
                "different organizations for this position."
            )

    # Channel insights
    for ch in channel_data:
        if ch["submitted"] >= 5 and ch["response_rate"] > 50:
            recs.append(
                f"Portal '{ch['portal']}' shows {ch['response_rate']}% response rate "
                f"from {ch['submitted']} submissions. Prioritize this channel."
            )

    # Scoring dimension accuracy
    predictive_dims = [d for d in dimension_data if d["predictive"] is True]
    non_predictive = [d for d in dimension_data if d["predictive"] is False]
    if predictive_dims:
        names = ", ".join(d["dimension"] for d in predictive_dims[:3])
        recs.append(
            f"Predictive dimensions (accepted > rejected by 0.5+): {names}. "
            "Consider increasing weights for these dimensions."
        )
    if non_predictive:
        names = ", ".join(d["dimension"] for d in non_predictive[:3])
        recs.append(
            f"Non-predictive dimensions: {names}. "
            "These do not differentiate accepted from rejected entries; "
            "consider reducing their weight."
        )

    # Block ROI
    high_roi = [b for b in block_data if b["acceptance_rate"] > 50 and b["total"] >= 2]
    low_roi = [b for b in block_data if b["rejection_rate"] > 75 and b["total"] >= 3]
    if high_roi:
        names = ", ".join(b["block"] for b in high_roi[:3])
        recs.append(f"High-ROI blocks (>50% acceptance): {names}. Use these more.")
    if low_roi:
        names = ", ".join(b["block"] for b in low_roi[:3])
        recs.append(f"Low-ROI blocks (>75% rejection): {names}. Revise or replace.")

    # Volume assessment
    if summary["submissions_per_month"] > 10:
        recs.append(
            f"Submitting {summary['submissions_per_month']}/month. "
            "Precision strategy recommends max 4-8/month. "
            "Reduce volume and increase per-application research time."
        )

    if not recs:
        recs.append("Insufficient outcome data for data-driven recommendations. "
                     "Continue tracking and revisit after more outcomes are recorded.")

    return recs


# --- Report formatting ---


def format_markdown_report(
    summary: dict,
    position_data: list[dict],
    channel_data: list[dict],
    block_data: list[dict],
    network_data: dict,
    dimension_data: list[dict],
    seasonal_data: dict,
    velocity_data: list[dict],
    recommendations: list[str],
    *,
    compare_data: dict | None = None,
    tto_data: dict | None = None,
) -> str:
    """Format the full report as markdown."""
    today = date.today()
    quarter = _quarter_label(today)
    lines = []

    lines.append(f"# Quarterly State of Applications -- {quarter}")
    lines.append(f"Generated: {today.isoformat()}")
    lines.append(f"Period: last {summary['period_days']} days")
    lines.append("")

    # Executive Summary
    lines.append("## 1. Executive Summary")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Total entries in period | {summary['total_entries']} |")
    lines.append(f"| Submitted | {summary['submitted']} |")
    lines.append(f"| Accepted | {summary['accepted']} |")
    lines.append(f"| Rejected/expired/withdrawn | {summary['rejected']} |")
    lines.append(f"| Pending response | {summary['pending']} |")
    lines.append(f"| Conversion rate | {summary['conversion_rate']}% |")
    lines.append(f"| Response rate | {summary['response_rate']}% |")
    lines.append(f"| Submissions/month | {summary['submissions_per_month']} |")
    lines.append(f"| Active pipeline size | {summary['active_pipeline_size']} |")
    lines.append("")

    if compare_data:
        lines.append("### Quarter-over-Quarter Comparison")
        lines.append("")
        lines.append("| Metric | Previous | Current | Delta |")
        lines.append("|--------|----------|---------|-------|")
        for key in ("submitted", "accepted", "rejected", "conversion_rate", "response_rate"):
            prev = compare_data.get("previous", {}).get(key, 0)
            curr = compare_data.get("current", {}).get(key, 0)
            if isinstance(prev, float) or isinstance(curr, float):
                delta = round(curr - prev, 1)
                sign = "+" if delta > 0 else ""
                lines.append(f"| {key} | {prev} | {curr} | {sign}{delta} |")
            else:
                delta = curr - prev
                sign = "+" if delta > 0 else ""
                lines.append(f"| {key} | {prev} | {curr} | {sign}{delta} |")
        lines.append("")

    # Conversion by Position
    lines.append("## 2. Conversion Rates by Identity Position")
    lines.append("")
    lines.append("| Position | Submitted | Accepted | Rejected | Pending | Conv% | Resp% |")
    lines.append("|----------|-----------|----------|----------|---------|-------|-------|")
    for row in position_data:
        lines.append(
            f"| {row['position']} | {row['submitted']} | {row['accepted']} | "
            f"{row['rejected']} | {row['pending']} | {row['conversion_rate']}% | "
            f"{row['response_rate']}% |"
        )
    lines.append("")

    # Conversion by Channel
    lines.append("## 3. Conversion Rates by Channel/Portal")
    lines.append("")
    lines.append("| Portal | Submitted | Accepted | Rejected | Pending | Conv% | Resp% |")
    lines.append("|--------|-----------|----------|----------|---------|-------|-------|")
    for row in channel_data:
        lines.append(
            f"| {row['portal']} | {row['submitted']} | {row['accepted']} | "
            f"{row['rejected']} | {row['pending']} | {row['conversion_rate']}% | "
            f"{row['response_rate']}% |"
        )
    lines.append("")

    # Block ROI
    lines.append("## 4. Block ROI")
    lines.append("")
    if block_data:
        lines.append("| Block | Total | Accepted | Rejected | Pending | Accept% | Reject% |")
        lines.append("|-------|-------|----------|----------|---------|---------|---------|")
        for row in block_data:
            lines.append(
                f"| {row['block']} | {row['total']} | {row['accepted']} | "
                f"{row['rejected']} | {row['pending']} | {row['acceptance_rate']}% | "
                f"{row['rejection_rate']}% |"
            )
    else:
        lines.append("No block usage data available for submitted entries.")
    lines.append("")

    # Network Proximity Correlation
    lines.append("## 5. Network Proximity Correlation")
    lines.append("")
    if network_data:
        lines.append("| Outcome | Avg Score | Count | Min | Max |")
        lines.append("|---------|-----------|-------|-----|-----|")
        for category in ("accepted", "pending", "rejected"):
            if category in network_data:
                d = network_data[category]
                lines.append(
                    f"| {category} | {d['average']} | {d['count']} | "
                    f"{d['min']} | {d['max']} |"
                )
    else:
        lines.append("No network proximity data available.")
    lines.append("")

    # Scoring Dimension Accuracy
    lines.append("## 6. Scoring Dimension Accuracy")
    lines.append("")
    lines.append("| Dimension | Avg Accepted | Avg Rejected | Delta | Predictive |")
    lines.append("|-----------|-------------|-------------|-------|------------|")
    for row in dimension_data:
        pred = "YES" if row["predictive"] is True else ("NO" if row["predictive"] is False else "N/A")
        lines.append(
            f"| {row['dimension']} | {row['avg_accepted']} | {row['avg_rejected']} | "
            f"{row['delta']} | {pred} |"
        )
    lines.append("")

    # Seasonal Patterns
    lines.append("## 7. Seasonal Patterns")
    lines.append("")
    lines.append("### Monthly")
    lines.append("")
    monthly = seasonal_data.get("monthly", [])
    if monthly:
        lines.append("| Month | Submitted | Outcomes | Accepted |")
        lines.append("|-------|-----------|----------|----------|")
        for row in monthly:
            lines.append(
                f"| {row['month']} | {row['submitted']} | {row['outcomes']} | "
                f"{row['accepted']} |"
            )
    else:
        lines.append("No monthly data available.")
    lines.append("")

    lines.append("### Weekly")
    lines.append("")
    weekly = seasonal_data.get("weekly", [])
    if weekly:
        lines.append("| Week Start | Submitted | Outcomes | Accepted |")
        lines.append("|------------|-----------|----------|----------|")
        for row in weekly:
            lines.append(
                f"| {row['week']} | {row['submitted']} | {row['outcomes']} | "
                f"{row['accepted']} |"
            )
    else:
        lines.append("No weekly data available.")
    lines.append("")

    # Pipeline Velocity
    lines.append("## 8. Pipeline Velocity")
    lines.append("")
    lines.append("| Stage | Avg Days | Median | Min | Max | N |")
    lines.append("|-------|----------|--------|-----|-----|---|")
    for row in velocity_data:
        lines.append(
            f"| {row['stage']} | {row['avg_days']} | {row['median_days']} | "
            f"{row['min_days']} | {row['max_days']} | {row['count']} |"
        )
    lines.append("")

    # Time to Outcome
    tto = tto_data or {}
    tto_overall = tto.get("overall", {})
    if tto_overall.get("count", 0) > 0:
        lines.append("## 9. Time to Outcome")
        lines.append("")
        lines.append(
            f"**Overall:** median {tto_overall['median']}d, "
            f"mean {tto_overall['mean']}d "
            f"(range {tto_overall['min']}-{tto_overall['max']}d, N={tto_overall['count']})"
        )
        lines.append("")
        by_track = tto.get("by_track", {})
        if by_track:
            lines.append("| Track | Median | Mean | Range | N |")
            lines.append("|-------|--------|------|-------|---|")
            for track, stats in by_track.items():
                lines.append(
                    f"| {track} | {stats['median']}d | {stats['mean']}d | "
                    f"{stats['min']}-{stats['max']}d | {stats['count']} |"
                )
            lines.append("")

    # Recommendations
    lines.append("## 10. Recommendations")
    lines.append("")
    for i, rec in enumerate(recommendations, 1):
        lines.append(f"{i}. {rec}")
    lines.append("")

    return "\n".join(lines)


def build_report(entries: list[dict], period_days: int, *, compare: bool = False) -> dict:
    """Build all report data sections and return as a dict."""
    period_entries = filter_by_period(entries, period_days)

    summary = executive_summary(period_entries, period_days)
    pos_data = conversion_by_position(period_entries)
    ch_data = conversion_by_channel(period_entries)
    blk_data = block_roi(period_entries)
    net_data = network_proximity_correlation(period_entries)
    dim_data = scoring_dimension_accuracy(period_entries)
    season_data = seasonal_patterns(period_entries)
    vel_data = pipeline_velocity(period_entries)
    tto_data = time_to_outcome(period_entries)
    recs = generate_recommendations(summary, pos_data, ch_data, net_data, dim_data, blk_data)

    compare_data = None
    if compare:
        today = date.today()
        current_q_start = _quarter_start(today)
        prev_q_end = current_q_start
        prev_q_start = _quarter_start(current_q_start - timedelta(days=1))

        current_entries = filter_by_quarter(entries, current_q_start, today + timedelta(days=1))
        prev_entries = filter_by_quarter(entries, prev_q_start, prev_q_end)

        current_summary = executive_summary(current_entries, (today - current_q_start).days or 1)
        prev_summary = executive_summary(prev_entries, (prev_q_end - prev_q_start).days or 1)

        compare_data = {
            "current": current_summary,
            "previous": prev_summary,
        }

    return {
        "summary": summary,
        "conversion_by_position": pos_data,
        "conversion_by_channel": ch_data,
        "block_roi": blk_data,
        "network_proximity": net_data,
        "scoring_dimensions": dim_data,
        "seasonal_patterns": season_data,
        "pipeline_velocity": vel_data,
        "time_to_outcome": tto_data,
        "recommendations": recs,
        "comparison": compare_data,
    }


def main():
    parser = argparse.ArgumentParser(description="Quarterly State of Applications report")
    parser.add_argument("--save", action="store_true", help="Save markdown to strategy/")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--period", type=int, default=90, help="Last N days (default: 90)")
    parser.add_argument("--compare", action="store_true",
                        help="Compare current quarter vs previous quarter")
    args = parser.parse_args()

    entries = load_all_entries()
    if not entries:
        print("No pipeline entries found.", file=sys.stderr)
        sys.exit(1)

    report_data = build_report(entries, args.period, compare=args.compare)

    if args.json:
        print(json.dumps(report_data, indent=2, default=str))
        return

    md = format_markdown_report(
        report_data["summary"],
        report_data["conversion_by_position"],
        report_data["conversion_by_channel"],
        report_data["block_roi"],
        report_data["network_proximity"],
        report_data["scoring_dimensions"],
        report_data["seasonal_patterns"],
        report_data["pipeline_velocity"],
        report_data["recommendations"],
        compare_data=report_data["comparison"],
        tto_data=report_data.get("time_to_outcome"),
    )

    if args.save:
        STRATEGY_DIR.mkdir(parents=True, exist_ok=True)
        today = date.today()
        quarter = _quarter_label(today)
        filename = f"quarterly-report-{quarter}.md"
        filepath = STRATEGY_DIR / filename
        filepath.write_text(md)
        print(f"Report saved to {filepath}")
    else:
        print(md)


if __name__ == "__main__":
    main()
