#!/usr/bin/env python3
"""Engagement-based rubric recalibration — propose weight adjustments from read-vs-silence signal.

Uses engagement signal (was the application reviewed?) rather than accept/reject outcomes.
This closes the feedback loop earlier, since engagement data accumulates much faster.

Signal definition:
  engaged (read): outcome is rejected, accepted, or interview — the application was reviewed
  silence (unread): outcome is expired, withdrawn, or status is submitted/deferred with no outcome

Usage:
    python scripts/recalibrate_engagement.py              # Show proposal
    python scripts/recalibrate_engagement.py --json       # JSON output
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import ALL_PIPELINE_DIRS, DIMENSION_ORDER, REPO_ROOT, load_entries

# Import WEIGHTS from score.py (avoids circular import through pipeline_lib)
from score import WEIGHTS

MIN_PER_GROUP = 10  # Lower threshold than recalibrate.py's N=2 accepted
ENGAGEMENT_THRESHOLD = 0.03  # Min delta to propose a weight change


def classify_engagement(entry: dict) -> str | None:
    """Classify entry as 'engaged', 'silence', or None (exclude).

    engaged: application was reviewed — outcome is rejected, accepted, or interview
    silence: application was never read — outcome is expired/withdrawn, or
             status is submitted with no resolved outcome
    """
    outcome = entry.get("outcome")
    status = entry.get("status", "")

    if outcome in ("rejected", "accepted", "interview"):
        return "engaged"

    if outcome in ("expired",):
        return "silence"

    # submitted/acknowledged with no outcome → likely never read (silence)
    if status in ("submitted",) and outcome is None:
        return "silence"

    # withdrawn — ambiguous; could have been read or not. Exclude.
    return None


def split_by_engagement(entries: list[dict]) -> tuple[list[dict], list[dict]]:
    """Split entries with dimension scores into engaged vs silence groups."""
    engaged = []
    silence = []

    for entry in entries:
        dims = (entry.get("fit") or {}).get("dimensions")
        if not isinstance(dims, dict) or not dims:
            continue

        signal = classify_engagement(entry)
        if signal == "engaged":
            engaged.append(dims)
        elif signal == "silence":
            silence.append(dims)

    return engaged, silence


def compute_engagement_means(
    engaged: list[dict], silence: list[dict]
) -> dict[str, dict[str, float]]:
    """Compute mean dimension scores for each group."""
    means: dict[str, dict[str, float]] = {}

    for dim in DIMENSION_ORDER:
        e_vals = [d.get(dim) for d in engaged if isinstance(d.get(dim), (int, float))]
        s_vals = [d.get(dim) for d in silence if isinstance(d.get(dim), (int, float))]

        means[dim] = {
            "engaged": sum(e_vals) / len(e_vals) if e_vals else 5.0,
            "silence": sum(s_vals) / len(s_vals) if s_vals else 5.0,
            "engaged_n": len(e_vals),
            "silence_n": len(s_vals),
        }

    return means


def propose_weights(means: dict[str, dict[str, float]]) -> dict[str, float]:
    """Propose new weights based on engagement correlation.

    Dimensions where engaged mean > silence mean signal that scoring well on
    that dimension correlates with getting read. Normalize to sum to 1.0.
    """
    deltas = {}
    for dim in DIMENSION_ORDER:
        m = means[dim]
        # Positive delta = dimension predicts engagement (getting read)
        delta = max(0.01, m["engaged"] - m["silence"])
        deltas[dim] = delta

    total = sum(deltas.values())
    suggested = {dim: round(deltas[dim] / total, 4) for dim in DIMENSION_ORDER}

    # Re-normalize to exactly 1.0
    total_suggested = sum(suggested.values())
    if total_suggested > 0:
        last_dim = DIMENSION_ORDER[-1]
        suggested[last_dim] = round(1.0 - sum(
            suggested[d] for d in DIMENSION_ORDER[:-1]
        ), 4)

    return suggested


def run_analysis(entries: list[dict] | None = None) -> dict | None:
    """Run engagement-based recalibration analysis. Returns result dict or None."""
    if entries is None:
        entries = load_entries(dirs=ALL_PIPELINE_DIRS)

    engaged, silence = split_by_engagement(entries)

    if len(engaged) < MIN_PER_GROUP:
        return {
            "error": "insufficient_data",
            "engaged_n": len(engaged),
            "silence_n": len(silence),
            "required": MIN_PER_GROUP,
            "message": (
                f"Need at least {MIN_PER_GROUP} engaged entries (got {len(engaged)}). "
                f"Engage outcomes: rejected, accepted, interview."
            ),
        }

    if len(silence) < MIN_PER_GROUP:
        return {
            "error": "insufficient_data",
            "engaged_n": len(engaged),
            "silence_n": len(silence),
            "required": MIN_PER_GROUP,
            "message": (
                f"Need at least {MIN_PER_GROUP} silence entries (got {len(silence)}). "
                f"Silence = submitted with no outcome, or expired."
            ),
        }

    means = compute_engagement_means(engaged, silence)
    suggested = propose_weights(means)

    dimensions = []
    for dim in DIMENSION_ORDER:
        m = means[dim]
        current = WEIGHTS.get(dim, 0.0)
        new = suggested.get(dim, 0.0)
        delta = new - current
        correlation = m["engaged"] - m["silence"]
        dimensions.append({
            "dimension": dim,
            "current_weight": current,
            "suggested_weight": new,
            "delta": round(delta, 4),
            "engaged_mean": round(m["engaged"], 2),
            "silence_mean": round(m["silence"], 2),
            "correlation": round(correlation, 2),
            "engaged_n": m["engaged_n"],
            "silence_n": m["silence_n"],
            "significant": abs(delta) >= ENGAGEMENT_THRESHOLD,
        })

    max_delta = max(abs(d["delta"]) for d in dimensions)

    return {
        "date": date.today().isoformat(),
        "engaged_n": len(engaged),
        "silence_n": len(silence),
        "dimensions": dimensions,
        "suggested_weights": suggested,
        "max_delta": round(max_delta, 4),
        "assessment": (
            "well_calibrated" if max_delta < 0.02
            else "minor_adjustments" if max_delta < 0.05
            else "significant_recalibration"
        ),
    }


def print_report(result: dict) -> None:
    """Print human-readable engagement recalibration report."""
    if "error" in result:
        print(f"INSUFFICIENT DATA: {result['message']}")
        print(f"  Engaged entries: {result['engaged_n']} (need >= {result['required']})")
        print(f"  Silence entries: {result['silence_n']} (need >= {result['required']})")
        return

    print("ENGAGEMENT-BASED RECALIBRATION PROPOSAL")
    print(f"Date: {result['date']}")
    print(f"Signal: {result['engaged_n']} engaged entries vs {result['silence_n']} silence entries")
    print("=" * 72)
    print()

    header = f"  {'Dimension':<25s} {'Current':>8s} {'Suggest':>8s} {'Delta':>7s}  {'Eng.':>5s}  {'Sil.':>5s}  {'Corr':>5s}"
    print(header)
    print(f"  {'-' * 25} {'-' * 8} {'-' * 8} {'-' * 7}  {'-' * 5}  {'-' * 5}  {'-' * 5}")

    for d in result["dimensions"]:
        marker = " ***" if d["significant"] else ""
        print(
            f"  {d['dimension']:<25s}"
            f" {d['current_weight']:>7.1%}"
            f" {d['suggested_weight']:>7.1%}"
            f" {d['delta']:>+6.1%} "
            f" {d['engaged_mean']:>5.1f}"
            f"  {d['silence_mean']:>5.1f}"
            f"  {d['correlation']:>+5.2f}"
            f"{marker}"
        )

    print()
    cw = sum(d["current_weight"] for d in result["dimensions"])
    sw = sum(d["suggested_weight"] for d in result["dimensions"])
    print(f"  Sum check: current={cw:.3f}, suggested={sw:.3f}")
    print()

    assessment = result["assessment"]
    if assessment == "well_calibrated":
        print("  Current weights are well-calibrated (max delta < 2%). No changes needed.")
    elif assessment == "minor_adjustments":
        print("  Minor adjustments suggested. Consider applying at next quarterly review.")
    else:
        print("  Significant recalibration suggested. Review dimensions marked ***.")

    print()
    print("  INTERPRETATION: Corr > 0 means higher score on this dimension correlates")
    print("  with getting read (engaged). These dimensions predict visibility.")
    print()
    print("  NOTE: Engagement ≠ acceptance. This shows what gets read, not what wins.")
    print("  Cross-reference with recalibrate.py (accept/reject) for full picture.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Engagement-based rubric recalibration")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of table")
    args = parser.parse_args()

    result = run_analysis()

    if args.json:
        print(json.dumps(result, indent=2, default=str))
        return

    print_report(result)


if __name__ == "__main__":
    main()
