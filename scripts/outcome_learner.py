#!/usr/bin/env python3
"""Outcome learning engine: analyze outcomes to calibrate scoring weights.

Reads outcome data from closed/submitted entries, compares pre-outcome scores
with actual results, and recommends scoring weight adjustments. Designed to
close the feedback loop between submission outcomes and the scoring rubric.

Usage:
    python scripts/outcome_learner.py                    # Full calibration report
    python scripts/outcome_learner.py --save             # Write calibration to signals/
    python scripts/outcome_learner.py --hypotheses       # Cross-reference with hypothesis patterns
"""

import argparse
import sys
from datetime import date
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import (
    DIMENSION_ORDER,
    PIPELINE_DIR_CLOSED,
    PIPELINE_DIR_SUBMITTED,
    SIGNALS_DIR,
    load_entries,
)

CALIBRATION_FILE = SIGNALS_DIR / "weight-calibration.yaml"

# Minimum outcomes needed before recommending weight changes
MIN_OUTCOMES_FOR_CALIBRATION = 10

# How much to blend calibrated weights vs base weights (when n >= MIN_OUTCOMES)
CALIBRATION_BLEND_RATIO = 0.30


def collect_outcome_data() -> list[dict]:
    """Scan closed + submitted entries for those with outcomes and scores.

    Returns list of dicts with: entry_id, outcome, composite_score,
    dimension_scores (dict), track, identity_position.
    """
    entries = load_entries(
        dirs=[PIPELINE_DIR_CLOSED, PIPELINE_DIR_SUBMITTED],
        include_filepath=True,
    )

    data = []
    for entry in entries:
        outcome = entry.get("outcome")
        if not outcome:
            continue

        fit = entry.get("fit", {})
        if not isinstance(fit, dict):
            continue

        composite = fit.get("score")
        if composite is None:
            continue

        # Collect per-dimension scores
        dimensions = {}
        for dim in DIMENSION_ORDER:
            val = fit.get(dim)
            if val is not None and isinstance(val, (int, float)):
                dimensions[dim] = val

        data.append({
            "entry_id": entry.get("id", "?"),
            "outcome": outcome,
            "composite_score": float(composite),
            "dimension_scores": dimensions,
            "track": entry.get("track", "unknown"),
            "identity_position": fit.get("identity_position", "unset"),
        })

    return data


def analyze_dimension_accuracy(data: list[dict]) -> dict:
    """Compare average dimension scores for accepted vs rejected entries.

    Returns dict mapping dimension -> {accepted_avg, rejected_avg, delta,
    signal} where signal is "overweighted" if rejected scored higher,
    "underweighted" if accepted scored much higher, or "neutral".
    """
    accepted = [d for d in data if d["outcome"] == "accepted"]
    rejected = [d for d in data if d["outcome"] == "rejected"]

    analysis = {}
    for dim in DIMENSION_ORDER:
        acc_scores = [d["dimension_scores"][dim] for d in accepted if dim in d["dimension_scores"]]
        rej_scores = [d["dimension_scores"][dim] for d in rejected if dim in d["dimension_scores"]]

        acc_avg = sum(acc_scores) / len(acc_scores) if acc_scores else None
        rej_avg = sum(rej_scores) / len(rej_scores) if rej_scores else None

        if acc_avg is not None and rej_avg is not None:
            delta = acc_avg - rej_avg
            if delta < -0.5:
                signal = "overweighted"
            elif delta > 1.5:
                signal = "underweighted"
            else:
                signal = "neutral"
        else:
            delta = None
            signal = "insufficient_data"

        analysis[dim] = {
            "accepted_avg": acc_avg,
            "rejected_avg": rej_avg,
            "accepted_n": len(acc_scores),
            "rejected_n": len(rej_scores),
            "delta": delta,
            "signal": signal,
        }

    return analysis


def compute_weight_recommendations(analysis: dict, base_weights: dict) -> dict:
    """Suggest weight adjustments based on dimension accuracy analysis.

    Returns dict with: weights (recommended), adjustments (per-dimension),
    confidence, sample_size, sufficient_data.
    """
    adjustments = {}
    new_weights = dict(base_weights)

    overweighted = []
    underweighted = []

    for dim, stats in analysis.items():
        if stats["signal"] == "overweighted":
            overweighted.append(dim)
            adjustments[dim] = "decrease"
        elif stats["signal"] == "underweighted":
            underweighted.append(dim)
            adjustments[dim] = "increase"
        else:
            adjustments[dim] = "keep"

    # Only adjust if we have clear signal
    if not overweighted and not underweighted:
        return {
            "weights": new_weights,
            "adjustments": adjustments,
            "confidence": "none",
            "sufficient_data": False,
        }

    # Redistribute: take 0.02 from each overweighted, give to underweighted
    shift = 0.02
    total_shifted = 0.0

    for dim in overweighted:
        if dim in new_weights:
            actual_shift = min(shift, new_weights[dim] - 0.01)  # keep min 0.01
            new_weights[dim] = round(new_weights[dim] - actual_shift, 3)
            total_shifted += actual_shift

    if underweighted and total_shifted > 0:
        per_dim = total_shifted / len(underweighted)
        for dim in underweighted:
            if dim in new_weights:
                new_weights[dim] = round(new_weights[dim] + per_dim, 3)

    # Normalize to sum to 1.0
    total = sum(new_weights.values())
    if total > 0:
        new_weights = {k: round(v / total, 3) for k, v in new_weights.items()}

    # Determine confidence level
    total_n = sum(stats.get("accepted_n", 0) + stats.get("rejected_n", 0) for stats in analysis.values())
    avg_n = total_n / len(analysis) if analysis else 0

    if avg_n >= 20:
        confidence = "high"
    elif avg_n >= 10:
        confidence = "moderate"
    elif avg_n >= 5:
        confidence = "low"
    else:
        confidence = "very_low"

    return {
        "weights": new_weights,
        "adjustments": adjustments,
        "confidence": confidence,
        "sufficient_data": avg_n >= MIN_OUTCOMES_FOR_CALIBRATION,
    }


def generate_calibration_report(data: list[dict], analysis: dict, recommendations: dict) -> str:
    """Generate human-readable calibration report."""
    lines = []
    lines.append(f"OUTCOME LEARNING REPORT — {date.today().isoformat()}")
    lines.append("=" * 60)

    # Data summary
    outcomes = {}
    for d in data:
        outcomes[d["outcome"]] = outcomes.get(d["outcome"], 0) + 1

    lines.append(f"\nOutcomes collected: {len(data)}")
    for outcome, count in sorted(outcomes.items(), key=lambda x: -x[1]):
        lines.append(f"  {outcome:<15s} {count}")

    accepted_n = outcomes.get("accepted", 0)
    rejected_n = outcomes.get("rejected", 0)
    useful = accepted_n + rejected_n
    lines.append(f"\nUseful for calibration (accepted + rejected): {useful}")

    if useful < 2:
        lines.append("\nINSUFFICIENT DATA for calibration.")
        lines.append(f"Need at least 2 accepted + rejected outcomes (have {useful}).")
        lines.append("Record outcomes: python scripts/check_outcomes.py --record <id> --outcome <result>")
        return "\n".join(lines)

    # Dimension accuracy
    lines.append("\nDIMENSION ACCURACY (accepted_avg - rejected_avg):")
    lines.append(f"{'Dimension':<25s} {'Acc Avg':>8s} {'Rej Avg':>8s} {'Delta':>7s}  Signal")
    lines.append("-" * 65)

    for dim in DIMENSION_ORDER:
        stats = analysis.get(dim, {})
        acc = f"{stats['accepted_avg']:.1f}" if stats.get("accepted_avg") is not None else "n/a"
        rej = f"{stats['rejected_avg']:.1f}" if stats.get("rejected_avg") is not None else "n/a"
        delta = f"{stats['delta']:+.1f}" if stats.get("delta") is not None else "n/a"
        signal = stats.get("signal", "?")
        marker = " <--" if signal in ("overweighted", "underweighted") else ""
        lines.append(f"  {dim:<23s} {acc:>8s} {rej:>8s} {delta:>7s}  {signal}{marker}")

    # Recommendations
    lines.append("\nRECOMMENDATIONS:")
    lines.append(f"  Confidence: {recommendations['confidence']}")
    lines.append(f"  Sufficient data: {'yes' if recommendations['sufficient_data'] else 'no'}")

    if not recommendations["sufficient_data"]:
        remaining = MIN_OUTCOMES_FOR_CALIBRATION - useful
        lines.append(f"  Need {remaining} more accepted/rejected outcomes for auto-calibration.")
        lines.append("  Current weights remain unchanged.")
    else:
        lines.append("\n  Suggested weight changes:")
        for dim in DIMENSION_ORDER:
            adj = recommendations["adjustments"].get(dim, "keep")
            if adj != "keep":
                old = recommendations.get("_base_weights", {}).get(dim, "?")
                new = recommendations["weights"].get(dim, "?")
                lines.append(f"    {dim}: {old} -> {new} ({adj})")

    return "\n".join(lines)


def save_calibration(recommendations: dict, data: list[dict]) -> Path:
    """Write calibration to signals/weight-calibration.yaml."""
    SIGNALS_DIR.mkdir(parents=True, exist_ok=True)

    record = {
        "generated": date.today().isoformat(),
        "sample_size": len(data),
        "accepted_count": sum(1 for d in data if d["outcome"] == "accepted"),
        "rejected_count": sum(1 for d in data if d["outcome"] == "rejected"),
        "confidence": recommendations["confidence"],
        "sufficient_data": recommendations["sufficient_data"],
        "weights": recommendations["weights"],
        "adjustments": recommendations["adjustments"],
    }

    with open(CALIBRATION_FILE, "w") as f:
        yaml.dump(record, f, default_flow_style=False, sort_keys=False)

    return CALIBRATION_FILE


def load_calibration() -> dict | None:
    """Load calibration file if it exists and has sufficient data.

    Returns dict with 'weights' key if calibration is valid and has
    sufficient data, else None. Designed for import by score.py.
    """
    if not CALIBRATION_FILE.exists():
        return None

    try:
        with open(CALIBRATION_FILE) as f:
            cal = yaml.safe_load(f) or {}
    except Exception:
        return None

    if not cal.get("sufficient_data"):
        return None

    weights = cal.get("weights")
    if not weights or not isinstance(weights, dict):
        return None

    return cal


def cross_reference_hypotheses(data: list[dict], analysis: dict) -> str:
    """Cross-reference hypothesis categories with dimension accuracy."""
    try:
        from feedback_capture import CATEGORY_DESCRIPTIONS, load_hypotheses
    except ImportError:
        return "feedback_capture module not available."

    hypotheses = load_hypotheses()
    if not hypotheses:
        return "No hypotheses recorded yet.\nCapture: python scripts/feedback_capture.py --entry <id>"

    lines = []
    lines.append(f"HYPOTHESIS-DIMENSION CROSS-REFERENCE — {date.today().isoformat()}")
    lines.append("=" * 60)
    lines.append(f"Hypotheses: {len(hypotheses)} | Outcomes with scores: {len(data)}")

    # Category distribution
    by_cat: dict[str, int] = {}
    for h in hypotheses:
        cat = h.get("category", "other")
        by_cat[cat] = by_cat.get(cat, 0) + 1

    lines.append(f"\nHypothesis categories (n={len(hypotheses)}):")
    for cat, count in sorted(by_cat.items(), key=lambda x: -x[1]):
        desc = CATEGORY_DESCRIPTIONS.get(cat, cat)
        lines.append(f"  {cat:<20s} {count:>3}  {desc}")

    # Map categories to likely scoring dimensions
    CATEGORY_DIMENSION_MAP = {
        "resume_screen": ["evidence_match", "track_record_fit"],
        "cover_letter": ["mission_alignment", "evidence_match"],
        "credential_gap": ["track_record_fit"],
        "timing": ["deadline_feasibility"],
        "auto_rejection": ["portal_friction"],
        "portfolio_gap": ["evidence_match", "track_record_fit"],
        "role_fit": ["mission_alignment", "strategic_value"],
        "compensation": ["financial_alignment"],
        "ie_framing": ["mission_alignment", "track_record_fit"],
    }

    lines.append("\nCategory → Dimension correlations:")
    for cat, count in sorted(by_cat.items(), key=lambda x: -x[1]):
        dims = CATEGORY_DIMENSION_MAP.get(cat, [])
        if not dims:
            continue
        dim_signals = []
        for dim in dims:
            stats = analysis.get(dim, {})
            signal = stats.get("signal", "?")
            dim_signals.append(f"{dim}={signal}")
        lines.append(f"  {cat} ({count}x) → {', '.join(dim_signals)}")

    # Dominant failure mode
    if by_cat:
        top_cat = max(by_cat, key=lambda k: by_cat[k])
        top_pct = by_cat[top_cat] / len(hypotheses) * 100
        lines.append(f"\nDominant failure mode: {top_cat} ({top_pct:.0f}%)")
        related_dims = CATEGORY_DIMENSION_MAP.get(top_cat, [])
        if related_dims:
            lines.append(f"  Related dimensions: {', '.join(related_dims)}")
            lines.append("  Consider increasing weight on these dimensions.")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Outcome learning engine: calibrate scoring weights from outcome data"
    )
    parser.add_argument("--save", action="store_true",
                        help="Write calibration to signals/weight-calibration.yaml")
    parser.add_argument("--hypotheses", action="store_true",
                        help="Cross-reference hypothesis patterns with dimension accuracy")
    args = parser.parse_args()

    # Collect outcome data
    data = collect_outcome_data()
    analysis = analyze_dimension_accuracy(data)

    # Load base weights for recommendations
    try:
        from score import WEIGHTS
        base_weights = dict(WEIGHTS)
    except ImportError:
        base_weights = {dim: 1.0 / len(DIMENSION_ORDER) for dim in DIMENSION_ORDER}

    recommendations = compute_weight_recommendations(analysis, base_weights)
    recommendations["_base_weights"] = base_weights

    if args.hypotheses:
        print(cross_reference_hypotheses(data, analysis))
        return

    # Print calibration report
    report = generate_calibration_report(data, analysis, recommendations)
    print(report)

    if args.save:
        path = save_calibration(recommendations, data)
        print(f"\nCalibration saved to: {path}")


if __name__ == "__main__":
    main()
