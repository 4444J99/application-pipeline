#!/usr/bin/env python3
"""Rejection learning engine: correlate scoring dimensions, blocks, timing,
and identity position with rejection outcomes.

Analyzes rejected entries against non-rejected entries to identify which
factors predict rejection. Generates actionable adjustment recommendations.

Usage:
    python scripts/rejection_learner.py                         # Full report
    python scripts/rejection_learner.py --dimension mission_alignment  # Single dimension
    python scripts/rejection_learner.py --json                  # JSON output
    python scripts/rejection_learner.py --min-samples 5         # Min samples for claims
"""

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import (
    DIMENSION_ORDER,
    PIPELINE_DIR_CLOSED,
    PIPELINE_DIR_SUBMITTED,
    load_entries,
    parse_date,
)

DEFAULT_MIN_SAMPLES = 3

# Outcome categories for grouping
REJECTION_OUTCOMES = {"rejected"}
NEGATIVE_OUTCOMES = {"rejected", "expired", "withdrawn"}
POSITIVE_OUTCOMES = {"accepted", "acknowledged", "interview"}
PENDING_OUTCOMES = {None, "null", ""}


def load_outcome_entries() -> list[dict]:
    """Load all entries from submitted/ and closed/ directories."""
    return load_entries(
        dirs=[PIPELINE_DIR_SUBMITTED, PIPELINE_DIR_CLOSED],
        include_filepath=True,
    )


def classify_entries(entries: list[dict]) -> dict[str, list[dict]]:
    """Separate entries by outcome category.

    Returns dict with keys: rejected, withdrawn, expired, acknowledged,
    positive (acknowledged/interview/accepted), pending (null outcome).
    """
    groups = {
        "rejected": [],
        "withdrawn": [],
        "expired": [],
        "acknowledged": [],
        "positive": [],
        "pending": [],
    }
    for entry in entries:
        outcome = entry.get("outcome")
        if outcome == "rejected":
            groups["rejected"].append(entry)
        elif outcome == "withdrawn":
            groups["withdrawn"].append(entry)
        elif outcome == "expired":
            groups["expired"].append(entry)
        elif outcome == "acknowledged":
            groups["acknowledged"].append(entry)
            groups["positive"].append(entry)
        elif outcome in ("interview", "accepted"):
            groups["positive"].append(entry)
        else:
            groups["pending"].append(entry)
    return groups


def _get_dimensions(entry: dict) -> dict[str, float]:
    """Extract dimension scores from an entry's fit.dimensions field."""
    fit = entry.get("fit", {})
    if not isinstance(fit, dict):
        return {}
    dims = fit.get("dimensions", {})
    if not isinstance(dims, dict):
        return {}
    result = {}
    for dim in DIMENSION_ORDER:
        val = dims.get(dim)
        if val is not None:
            try:
                result[dim] = float(val)
            except (ValueError, TypeError):
                pass
    return result


def _get_identity_position(entry: dict) -> str:
    """Extract identity position from fit or top-level field."""
    fit = entry.get("fit", {})
    if isinstance(fit, dict) and fit.get("identity_position"):
        return fit["identity_position"]
    return entry.get("identity_position", "unknown")


def _get_portal(entry: dict) -> str:
    """Extract portal type from target field."""
    target = entry.get("target", {})
    if isinstance(target, dict):
        return target.get("portal", "unknown") or "unknown"
    return "unknown"


def _get_blocks_used(entry: dict) -> list[str]:
    """Extract blocks_used list from submission field.

    Handles both dict-style (keyed by role) and list-style blocks.
    """
    submission = entry.get("submission", {})
    if not isinstance(submission, dict):
        return []
    blocks = submission.get("blocks_used", {})
    if isinstance(blocks, dict):
        return list(blocks.values())
    if isinstance(blocks, list):
        return blocks
    return []


def _get_submission_timing(entry: dict) -> str | None:
    """Classify submission timing relative to deadline.

    Returns 'early' (>14 days before), 'mid' (7-14 days), 'late' (<7 days),
    or None if no deadline.
    """
    deadline_info = entry.get("deadline", {})
    if not isinstance(deadline_info, dict):
        return None
    deadline_raw = deadline_info.get("date")
    deadline_date = parse_date(deadline_raw)
    if not deadline_date:
        return None

    timeline = entry.get("timeline", {})
    if not isinstance(timeline, dict):
        return None
    submitted_raw = timeline.get("submitted")
    submitted_date = parse_date(submitted_raw)
    if not submitted_date:
        return None

    days_before = (deadline_date - submitted_date).days
    if days_before > 14:
        return "early"
    elif days_before >= 7:
        return "mid"
    else:
        return "late"


def _get_track(entry: dict) -> str:
    """Extract track from entry."""
    return entry.get("track", "unknown") or "unknown"


def _get_composite_score(entry: dict) -> float | None:
    """Extract composite score from fit field."""
    fit = entry.get("fit", {})
    if isinstance(fit, dict):
        score = fit.get("score")
        if score is not None:
            try:
                return float(score)
            except (ValueError, TypeError):
                pass
    return None


# --- Analysis functions ---


def analyze_dimension_weakness(
    rejected: list[dict],
    non_rejected: list[dict],
) -> dict[str, dict]:
    """Compare average dimension scores between rejected and non-rejected entries.

    Returns per-dimension analysis with means, delta, and weakness ranking.
    """
    analysis = {}

    for dim in DIMENSION_ORDER:
        rej_scores = [
            _get_dimensions(e).get(dim)
            for e in rejected
            if dim in _get_dimensions(e)
        ]
        non_rej_scores = [
            _get_dimensions(e).get(dim)
            for e in non_rejected
            if dim in _get_dimensions(e)
        ]
        rej_scores = [s for s in rej_scores if s is not None]
        non_rej_scores = [s for s in non_rej_scores if s is not None]

        rej_avg = sum(rej_scores) / len(rej_scores) if rej_scores else None
        non_rej_avg = (
            sum(non_rej_scores) / len(non_rej_scores)
            if non_rej_scores
            else None
        )

        delta = None
        if rej_avg is not None and non_rej_avg is not None:
            delta = round(rej_avg - non_rej_avg, 2)

        analysis[dim] = {
            "rejected_avg": round(rej_avg, 2) if rej_avg is not None else None,
            "non_rejected_avg": round(non_rej_avg, 2) if non_rej_avg is not None else None,
            "delta": delta,
            "rejected_n": len(rej_scores),
            "non_rejected_n": len(non_rej_scores),
        }

    return analysis


def analyze_position_rejection_rate(
    entries: list[dict],
) -> dict[str, dict]:
    """Calculate rejection rate per identity position."""
    position_groups: dict[str, list[dict]] = defaultdict(list)
    for entry in entries:
        pos = _get_identity_position(entry)
        position_groups[pos].append(entry)

    results = {}
    for pos, group in sorted(position_groups.items()):
        total = len(group)
        rejected = sum(1 for e in group if e.get("outcome") == "rejected")
        rate = rejected / total if total > 0 else 0.0
        results[pos] = {
            "total": total,
            "rejected": rejected,
            "rate": round(rate, 3),
        }
    return results


def analyze_portal_rejection_rate(
    entries: list[dict],
) -> dict[str, dict]:
    """Calculate rejection rate per portal type."""
    portal_groups: dict[str, list[dict]] = defaultdict(list)
    for entry in entries:
        portal = _get_portal(entry)
        portal_groups[portal].append(entry)

    results = {}
    for portal, group in sorted(portal_groups.items()):
        total = len(group)
        rejected = sum(1 for e in group if e.get("outcome") == "rejected")
        rate = rejected / total if total > 0 else 0.0
        results[portal] = {
            "total": total,
            "rejected": rejected,
            "rate": round(rate, 3),
        }
    return results


def analyze_block_correlation(
    rejected: list[dict],
    non_rejected: list[dict],
) -> dict[str, dict]:
    """Analyze which blocks correlate with rejection.

    For each block, compares its frequency in rejected vs non-rejected entries.
    A block that appears disproportionately in rejected entries may indicate
    poor fit or content quality issues for certain targets.
    """
    rej_block_counts: Counter = Counter()
    non_rej_block_counts: Counter = Counter()
    rej_total = len(rejected)
    non_rej_total = len(non_rejected)

    for entry in rejected:
        blocks = _get_blocks_used(entry)
        for block in set(blocks):
            rej_block_counts[block] += 1

    for entry in non_rejected:
        blocks = _get_blocks_used(entry)
        for block in set(blocks):
            non_rej_block_counts[block] += 1

    all_blocks = set(rej_block_counts.keys()) | set(non_rej_block_counts.keys())
    results = {}
    for block in sorted(all_blocks):
        rej_count = rej_block_counts.get(block, 0)
        non_rej_count = non_rej_block_counts.get(block, 0)
        rej_rate = rej_count / rej_total if rej_total > 0 else 0.0
        non_rej_rate = non_rej_count / non_rej_total if non_rej_total > 0 else 0.0
        # Positive lift means block appears more often in rejected entries
        lift = round(rej_rate - non_rej_rate, 3) if rej_total and non_rej_total else None

        results[block] = {
            "rejected_count": rej_count,
            "non_rejected_count": non_rej_count,
            "rejected_rate": round(rej_rate, 3),
            "non_rejected_rate": round(non_rej_rate, 3),
            "lift": lift,
        }
    return results


def analyze_timing_correlation(
    entries: list[dict],
) -> dict[str, dict]:
    """Analyze rejection rate by submission timing relative to deadline."""
    timing_groups: dict[str, list[dict]] = defaultdict(list)
    for entry in entries:
        timing = _get_submission_timing(entry)
        if timing:
            timing_groups[timing].append(entry)

    # Also add a "rolling" group for entries with no deadline
    for entry in entries:
        deadline_info = entry.get("deadline", {})
        if isinstance(deadline_info, dict):
            dtype = deadline_info.get("type", "")
            if dtype == "rolling":
                timing_groups["rolling"].append(entry)

    results = {}
    for timing, group in sorted(timing_groups.items()):
        total = len(group)
        rejected = sum(1 for e in group if e.get("outcome") == "rejected")
        rate = rejected / total if total > 0 else 0.0
        results[timing] = {
            "total": total,
            "rejected": rejected,
            "rate": round(rate, 3),
        }
    return results


def analyze_score_distribution(
    rejected: list[dict],
    non_rejected: list[dict],
) -> dict:
    """Compare composite score distributions between rejected and non-rejected."""
    rej_scores = [
        _get_composite_score(e) for e in rejected
        if _get_composite_score(e) is not None
    ]
    non_rej_scores = [
        _get_composite_score(e) for e in non_rejected
        if _get_composite_score(e) is not None
    ]

    def _stats(scores: list[float]) -> dict:
        if not scores:
            return {"mean": None, "min": None, "max": None, "n": 0}
        return {
            "mean": round(sum(scores) / len(scores), 2),
            "min": round(min(scores), 2),
            "max": round(max(scores), 2),
            "n": len(scores),
        }

    return {
        "rejected": _stats(rej_scores),
        "non_rejected": _stats(non_rej_scores),
    }


def generate_recommendations(
    dim_analysis: dict[str, dict],
    position_analysis: dict[str, dict],
    portal_analysis: dict[str, dict],
    block_analysis: dict[str, dict],
    min_samples: int,
) -> list[str]:
    """Generate actionable recommendations from rejection analysis."""
    recs = []

    # Dimension-based recommendations
    weakness_ranking = sorted(
        [(dim, info) for dim, info in dim_analysis.items() if info["delta"] is not None],
        key=lambda x: x[1]["delta"],
    )
    for dim, info in weakness_ranking[:3]:
        if info["delta"] is not None and info["delta"] < -1.0:
            n = info["rejected_n"]
            if n >= min_samples:
                recs.append(
                    f"Dimension '{dim}' averages {abs(info['delta']):.1f} points lower "
                    f"in rejected entries (rej={info['rejected_avg']}, "
                    f"non-rej={info['non_rejected_avg']}). "
                    f"Prioritize targets with stronger {dim} scores."
                )

    # Position-based recommendations
    for pos, info in position_analysis.items():
        if info["total"] >= min_samples and info["rate"] > 0.5:
            recs.append(
                f"Identity position '{pos}' has {info['rate']:.0%} rejection rate "
                f"({info['rejected']}/{info['total']}). Consider refining the "
                f"framing or targeting different opportunities."
            )

    # Portal-based recommendations
    for portal, info in portal_analysis.items():
        if info["total"] >= min_samples and info["rate"] > 0.5:
            recs.append(
                f"Portal '{portal}' has {info['rate']:.0%} rejection rate "
                f"({info['rejected']}/{info['total']}). "
                f"Investigate portal-specific submission quality."
            )

    # Block-based recommendations
    risky_blocks = [
        (block, info) for block, info in block_analysis.items()
        if info["lift"] is not None
        and info["lift"] > 0.2
        and info["rejected_count"] >= min_samples
    ]
    risky_blocks.sort(key=lambda x: x[1]["lift"], reverse=True)
    for block, info in risky_blocks[:3]:
        recs.append(
            f"Block '{block}' appears {info['lift']:.0%} more often in rejected "
            f"entries. Review content quality or appropriateness of usage."
        )

    if not recs:
        recs.append("No statistically significant patterns detected yet.")

    return recs


# --- Full analysis runner ---


def run_full_analysis(
    entries: list[dict],
    min_samples: int = DEFAULT_MIN_SAMPLES,
) -> dict:
    """Run the complete rejection learning analysis.

    Returns a structured dict with all analysis results.
    """
    groups = classify_entries(entries)
    rejected = groups["rejected"]
    # Non-rejected = everything except rejected (includes pending)
    non_rejected = [e for e in entries if e.get("outcome") != "rejected"]

    result = {
        "summary": {
            "total_entries": len(entries),
            "rejected": len(rejected),
            "withdrawn": len(groups["withdrawn"]),
            "expired": len(groups["expired"]),
            "acknowledged": len(groups["acknowledged"]),
            "positive": len(groups["positive"]),
            "pending": len(groups["pending"]),
            "min_samples": min_samples,
            "date": date.today().isoformat(),
        },
        "dimension_weakness": analyze_dimension_weakness(rejected, non_rejected),
        "position_rejection_rate": analyze_position_rejection_rate(entries),
        "portal_rejection_rate": analyze_portal_rejection_rate(entries),
        "block_correlation": analyze_block_correlation(rejected, non_rejected),
        "timing_correlation": analyze_timing_correlation(entries),
        "score_distribution": analyze_score_distribution(rejected, non_rejected),
        "recommendations": [],
    }

    if len(rejected) >= min_samples:
        result["recommendations"] = generate_recommendations(
            result["dimension_weakness"],
            result["position_rejection_rate"],
            result["portal_rejection_rate"],
            result["block_correlation"],
            min_samples,
        )

    return result


# --- Report printing ---


def print_report(analysis: dict, min_samples: int = DEFAULT_MIN_SAMPLES):
    """Print the full rejection patterns report to stdout."""
    summary = analysis["summary"]
    n_rejected = summary["rejected"]

    print(f"Rejection Patterns Report — {summary['date']}")
    print("=" * 65)
    print(f"Total entries analyzed: {summary['total_entries']}")
    print(f"  Rejected:     {summary['rejected']}")
    print(f"  Withdrawn:    {summary['withdrawn']}")
    print(f"  Expired:      {summary['expired']}")
    print(f"  Acknowledged: {summary['acknowledged']}")
    print(f"  Positive:     {summary['positive']}")
    print(f"  Pending:      {summary['pending']}")
    print()

    if n_rejected < min_samples:
        print(
            f"Insufficient data: {n_rejected} rejection(s), "
            f"need at least {min_samples}"
        )
        return

    # Score distribution
    score_dist = analysis["score_distribution"]
    print("Composite Score Distribution")
    print("-" * 40)
    rej_stats = score_dist["rejected"]
    non_stats = score_dist["non_rejected"]
    if rej_stats["mean"] is not None:
        print(f"  Rejected:     mean={rej_stats['mean']}, range=[{rej_stats['min']}-{rej_stats['max']}], n={rej_stats['n']}")
    if non_stats["mean"] is not None:
        print(f"  Non-rejected: mean={non_stats['mean']}, range=[{non_stats['min']}-{non_stats['max']}], n={non_stats['n']}")
    print()

    # Dimension weakness ranking
    dim_data = analysis["dimension_weakness"]
    print("Dimension Weakness Ranking (rejected vs non-rejected)")
    print("-" * 65)
    print(f"  {'Dimension':<25s} {'Rej Avg':>8s} {'Non-Rej':>8s} {'Delta':>7s} {'N(rej)':>7s}")
    print(f"  {'-' * 25} {'-' * 8} {'-' * 8} {'-' * 7} {'-' * 7}")
    ranked = sorted(
        dim_data.items(),
        key=lambda x: x[1]["delta"] if x[1]["delta"] is not None else 999,
    )
    for dim, info in ranked:
        rej_str = f"{info['rejected_avg']:.1f}" if info["rejected_avg"] is not None else "—"
        non_str = f"{info['non_rejected_avg']:.1f}" if info["non_rejected_avg"] is not None else "—"
        delta_str = f"{info['delta']:+.1f}" if info["delta"] is not None else "—"
        marker = " **" if info["delta"] is not None and info["delta"] < -1.0 else ""
        print(f"  {dim:<25s} {rej_str:>8s} {non_str:>8s} {delta_str:>7s} {info['rejected_n']:>7d}{marker}")
    print("  ** = dimension is notably weaker in rejected entries")
    print()

    # Position rejection rates
    pos_data = analysis["position_rejection_rate"]
    print("Rejection Rate by Identity Position")
    print("-" * 50)
    print(f"  {'Position':<30s} {'Total':>6s} {'Rej':>5s} {'Rate':>7s}")
    print(f"  {'-' * 30} {'-' * 6} {'-' * 5} {'-' * 7}")
    for pos, info in sorted(pos_data.items(), key=lambda x: -x[1]["rate"]):
        rate_str = f"{info['rate']:.0%}" if info["total"] >= min_samples else f"{info['rate']:.0%}*"
        print(f"  {pos:<30s} {info['total']:>6d} {info['rejected']:>5d} {rate_str:>7s}")
    print("  * = below min sample threshold")
    print()

    # Portal rejection rates
    portal_data = analysis["portal_rejection_rate"]
    print("Rejection Rate by Portal Type")
    print("-" * 50)
    print(f"  {'Portal':<20s} {'Total':>6s} {'Rej':>5s} {'Rate':>7s}")
    print(f"  {'-' * 20} {'-' * 6} {'-' * 5} {'-' * 7}")
    for portal, info in sorted(portal_data.items(), key=lambda x: -x[1]["rate"]):
        rate_str = f"{info['rate']:.0%}" if info["total"] >= min_samples else f"{info['rate']:.0%}*"
        print(f"  {portal:<20s} {info['total']:>6d} {info['rejected']:>5d} {rate_str:>7s}")
    print()

    # Block correlation
    block_data = analysis["block_correlation"]
    print("Block Correlation with Rejection")
    print("-" * 65)
    # Only show blocks with non-zero rejection count, sorted by lift
    block_items = [
        (b, info) for b, info in block_data.items()
        if info["rejected_count"] > 0
    ]
    block_items.sort(key=lambda x: x[1]["lift"] if x[1]["lift"] is not None else 0, reverse=True)
    if block_items:
        print(f"  {'Block':<40s} {'Rej':>4s} {'Non':>4s} {'Lift':>7s}")
        print(f"  {'-' * 40} {'-' * 4} {'-' * 4} {'-' * 7}")
        for block, info in block_items[:15]:
            lift_str = f"{info['lift']:+.1%}" if info["lift"] is not None else "—"
            print(f"  {block:<40s} {info['rejected_count']:>4d} {info['non_rejected_count']:>4d} {lift_str:>7s}")
    else:
        print("  No block correlation data available.")
    print()

    # Timing correlation
    timing_data = analysis["timing_correlation"]
    if timing_data:
        print("Rejection Rate by Submission Timing")
        print("-" * 50)
        print(f"  {'Timing':<15s} {'Total':>6s} {'Rej':>5s} {'Rate':>7s}")
        print(f"  {'-' * 15} {'-' * 6} {'-' * 5} {'-' * 7}")
        for timing, info in sorted(timing_data.items()):
            rate_str = f"{info['rate']:.0%}"
            print(f"  {timing:<15s} {info['total']:>6d} {info['rejected']:>5d} {rate_str:>7s}")
        print()

    # Recommendations
    recs = analysis.get("recommendations", [])
    if recs:
        print("Recommended Adjustments")
        print("-" * 65)
        for i, rec in enumerate(recs, 1):
            print(f"  {i}. {rec}")
        print()


def print_single_dimension(analysis: dict, dimension: str):
    """Print detailed analysis for a single dimension."""
    dim_data = analysis["dimension_weakness"].get(dimension)
    if not dim_data:
        print(f"Unknown dimension: {dimension}", file=sys.stderr)
        print(f"Valid dimensions: {', '.join(DIMENSION_ORDER)}", file=sys.stderr)
        sys.exit(1)

    summary = analysis["summary"]
    print(f"Dimension Analysis: {dimension}")
    print("=" * 50)
    print(f"Entries analyzed: {summary['total_entries']} ({summary['rejected']} rejected)")
    print()
    print(f"  Rejected average:     {dim_data['rejected_avg']}" if dim_data["rejected_avg"] is not None else "  Rejected average:     —")
    print(f"  Non-rejected average: {dim_data['non_rejected_avg']}" if dim_data["non_rejected_avg"] is not None else "  Non-rejected average: —")
    print(f"  Delta:                {dim_data['delta']:+.2f}" if dim_data["delta"] is not None else "  Delta:                —")
    print(f"  Rejected sample size: {dim_data['rejected_n']}")
    print(f"  Non-rejected sample:  {dim_data['non_rejected_n']}")
    print()

    if dim_data["delta"] is not None:
        if dim_data["delta"] < -2.0:
            print(f"  Signal: STRONG PREDICTOR — {dimension} is substantially lower in rejected entries.")
        elif dim_data["delta"] < -1.0:
            print(f"  Signal: MODERATE PREDICTOR — {dimension} trends lower in rejected entries.")
        elif dim_data["delta"] < 0:
            print(f"  Signal: WEAK — slight trend toward lower {dimension} in rejections.")
        else:
            print(f"  Signal: NOT PREDICTIVE — {dimension} is similar or higher in rejected entries.")

    # Show per-entry breakdown
    print()
    print(f"  {'Entry':<50s} {'Score':>6s} {'Outcome':>10s}")
    print(f"  {'-' * 50} {'-' * 6} {'-' * 10}")
    entries = load_outcome_entries()
    for entry in sorted(entries, key=lambda e: _get_dimensions(e).get(dimension, 0)):
        dims = _get_dimensions(entry)
        score = dims.get(dimension)
        if score is None:
            continue
        outcome = entry.get("outcome") or "pending"
        eid = entry.get("id", "?")[:48]
        marker = " <<" if outcome == "rejected" else ""
        print(f"  {eid:<50s} {score:>6.1f} {outcome:>10s}{marker}")


def main():
    parser = argparse.ArgumentParser(
        description="Rejection learning engine: correlate factors with rejection outcomes"
    )
    parser.add_argument(
        "--dimension",
        help="Analyze a single scoring dimension in detail",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    parser.add_argument(
        "--min-samples",
        type=int,
        default=DEFAULT_MIN_SAMPLES,
        help=f"Minimum rejection samples for statistical claims (default: {DEFAULT_MIN_SAMPLES})",
    )
    args = parser.parse_args()

    entries = load_outcome_entries()
    if not entries:
        print("No entries found in submitted/ or closed/.", file=sys.stderr)
        sys.exit(1)

    analysis = run_full_analysis(entries, min_samples=args.min_samples)

    if args.json:
        print(json.dumps(analysis, indent=2, default=str))
    elif args.dimension:
        print_single_dimension(analysis, args.dimension)
    else:
        print_report(analysis, min_samples=args.min_samples)


if __name__ == "__main__":
    main()
