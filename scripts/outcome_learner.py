#!/usr/bin/env python3
"""Outcome learning engine: analyze outcomes to calibrate scoring weights.

Reads outcome data from closed/submitted entries, compares pre-outcome scores
with actual results, and recommends scoring weight adjustments. Designed to
close the feedback loop between submission outcomes and the scoring rubric.

Usage:
    python scripts/outcome_learner.py                           # Full calibration report
    python scripts/outcome_learner.py --save                    # Write calibration to signals/
    python scripts/outcome_learner.py --hypotheses              # Cross-reference with hypothesis patterns
    python scripts/outcome_learner.py --validate-hypotheses     # Hypothesis validation + weight recommendations
"""

import argparse
import os
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
HISTORICAL_OUTCOMES_PATH = SIGNALS_DIR / "historical-outcomes.yaml"

# Minimum outcomes needed before recommending weight changes
MIN_OUTCOMES_FOR_CALIBRATION = 10

# How much to blend calibrated weights vs base weights (when n >= MIN_OUTCOMES)
CALIBRATION_BLEND_RATIO = 0.30

# Governance safeguards for automatic calibration application.
MIN_ACCEPTED_FOR_LOAD = 3
MIN_REJECTED_FOR_LOAD = 3
DEFAULT_MAX_AGE_DAYS = 45
DEFAULT_MAX_DIMENSION_DRIFT = 0.08


def _parse_iso_date(raw: str | None):
    if not raw:
        return None
    try:
        from datetime import datetime

        return datetime.strptime(str(raw), "%Y-%m-%d").date()
    except ValueError:
        return None


def compute_weight_drift(base_weights: dict, calibrated_weights: dict) -> dict:
    """Compute absolute drift per dimension between base and calibrated weights."""
    deltas = {}
    for dim in DIMENSION_ORDER:
        base = float(base_weights.get(dim, 0.0))
        calibrated = float(calibrated_weights.get(dim, 0.0))
        deltas[dim] = round(calibrated - base, 4)

    max_abs_delta = max((abs(v) for v in deltas.values()), default=0.0)
    return {
        "deltas": deltas,
        "max_abs_delta": round(max_abs_delta, 4),
    }


def drift_check_report(calibration: dict, base_weights: dict) -> str:
    """Generate a human-readable drift check report for calibration safety."""
    weights = calibration.get("weights", {}) if isinstance(calibration, dict) else {}
    if not isinstance(weights, dict) or not weights:
        return "No calibration weights available for drift check."

    drift = compute_weight_drift(base_weights, weights)
    budget = float(calibration.get("max_dimension_drift", DEFAULT_MAX_DIMENSION_DRIFT))
    lines = []
    lines.append(f"CALIBRATION DRIFT CHECK — {date.today().isoformat()}")
    lines.append("=" * 60)
    lines.append(f"Max absolute drift: {drift['max_abs_delta']:.3f} (budget: {budget:.3f})")
    lines.append("")
    lines.append(f"{'Dimension':<25s} {'Delta':>8s}")
    lines.append("-" * 60)
    for dim in DIMENSION_ORDER:
        delta = drift["deltas"].get(dim, 0.0)
        marker = " !!" if abs(delta) > budget else ""
        lines.append(f"{dim:<25s} {delta:>+8.3f}{marker}")
    return "\n".join(lines)


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


def load_historical_outcomes() -> list[dict]:
    """Load historical outcome records from signals/historical-outcomes.yaml.

    Returns simplified records without dimension scores (these predate the pipeline).
    Each record has: company, title, applied_date, channel, portal, outcome.
    """
    if not HISTORICAL_OUTCOMES_PATH.exists():
        return []
    try:
        with open(HISTORICAL_OUTCOMES_PATH) as f:
            data = yaml.safe_load(f)
        entries = data.get("entries", []) if isinstance(data, dict) else []
        return [e for e in entries if isinstance(e, dict) and e.get("outcome")]
    except Exception:  # noqa: BLE001
        return []


def collect_all_outcome_data() -> list[dict]:
    """Collect outcome data from both pipeline entries and historical records.

    Pipeline records have full dimension scores. Historical records have
    channel/portal/date but no dimension scores. Consumers must handle
    the difference (check for 'composite_score' key presence).
    """
    pipeline = collect_outcome_data()
    historical = load_historical_outcomes()
    # Normalize historical records to match pipeline record shape
    for h in historical:
        h.setdefault("entry_id", f"hist-{h.get('company', '?')}-{h.get('applied_date', '?')}")
        h.setdefault("composite_score", None)
        h.setdefault("dimension_scores", {})
        h.setdefault("track", "job")
        h.setdefault("identity_position", "unset")
    return pipeline + historical


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
    lines.append("  Auto-apply requires review approval: yes")

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
        "base_weights": recommendations.get("_base_weights", {}),
        "approved": False if recommendations["sufficient_data"] else True,
        "approved_by": None,
        "approved_at": None,
        "max_age_days": DEFAULT_MAX_AGE_DAYS,
        "max_dimension_drift": DEFAULT_MAX_DIMENSION_DRIFT,
        "calibration_blend_ratio": CALIBRATION_BLEND_RATIO,
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

    # New calibration records require explicit approval before score.py auto-applies.
    if "approved" in cal and not cal.get("approved"):
        return None

    accepted_count = cal.get("accepted_count")
    rejected_count = cal.get("rejected_count")
    if accepted_count is not None and int(accepted_count) < MIN_ACCEPTED_FOR_LOAD:
        return None
    if rejected_count is not None and int(rejected_count) < MIN_REJECTED_FOR_LOAD:
        return None

    generated = _parse_iso_date(cal.get("generated"))
    max_age_days = int(cal.get("max_age_days", DEFAULT_MAX_AGE_DAYS))
    if generated is not None:
        age_days = (date.today() - generated).days
        if age_days > max_age_days:
            return None

    base_weights = cal.get("base_weights", {})
    if isinstance(base_weights, dict) and base_weights:
        drift = compute_weight_drift(base_weights, weights)
        max_drift_budget = float(cal.get("max_dimension_drift", DEFAULT_MAX_DIMENSION_DRIFT))
        if drift["max_abs_delta"] > max_drift_budget:
            return None

    return cal


def approve_calibration(reviewer: str) -> Path:
    """Mark the calibration file as approved for auto-application."""
    if not CALIBRATION_FILE.exists():
        raise FileNotFoundError(f"Calibration file not found: {CALIBRATION_FILE}")

    data = yaml.safe_load(CALIBRATION_FILE.read_text()) or {}
    if not isinstance(data, dict):
        raise ValueError("Calibration file is not a YAML mapping")

    data["approved"] = True
    data["approved_by"] = reviewer
    data["approved_at"] = date.today().isoformat()

    with open(CALIBRATION_FILE, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)
    return CALIBRATION_FILE


# Map hypothesis categories to the scoring dimensions they most affect.
# Used by cross_reference_hypotheses and validate_hypotheses_with_weights.
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


def validate_hypotheses_with_weights(base_weights: dict) -> dict:
    """Run hypothesis validation and generate weight adjustment recommendations.

    Closes the hypothesis -> outcome -> adjustment loop:
    1. Loads and validates hypotheses against conversion log outcomes
    2. Computes per-category accuracy
    3. For validated patterns (>50% accurate), recommends increasing related
       dimension weights
    4. For invalid assumptions (<30% accurate), recommends decreasing related
       dimension weights

    Returns dict with: report (str), adjustments (dict), yaml_snippet (str),
    category_accuracy (dict), patterns (dict).
    """
    from validate_hypotheses import (
        accuracy_by_category,
        build_outcome_map,
        classify_patterns,
        load_conversion_log,
        load_hypotheses,
        validate,
    )

    hypotheses = load_hypotheses()
    if not hypotheses:
        return {
            "report": "No hypotheses found. Capture with: python scripts/feedback_capture.py --entry <id>",
            "adjustments": {},
            "yaml_snippet": "",
            "category_accuracy": {},
            "patterns": {"validated": [], "invalid": [], "inconclusive": [], "no_data": []},
        }

    outcomes = build_outcome_map(load_conversion_log())
    results = validate(hypotheses, outcomes)
    cat_stats = accuracy_by_category(results)
    patterns = classify_patterns(cat_stats)

    # Build weight adjustment recommendations from validated/invalid patterns
    dimension_adjustments: dict[str, dict] = {}
    for dim in DIMENSION_ORDER:
        dimension_adjustments[dim] = {
            "direction": "keep",
            "reason": [],
            "confidence_sources": [],
        }

    # Validated patterns -> increase related dimensions
    for cat in patterns["validated"]:
        stats = cat_stats[cat]
        dims = CATEGORY_DIMENSION_MAP.get(cat, [])
        for dim in dims:
            if dim in dimension_adjustments:
                dimension_adjustments[dim]["direction"] = "increase"
                dimension_adjustments[dim]["reason"].append(
                    f"{cat} predictions {stats['accuracy']:.0f}% accurate ({stats['correct']}/{stats['resolved']})"
                )
                dimension_adjustments[dim]["confidence_sources"].append(cat)

    # Invalid assumptions -> decrease related dimensions
    for cat in patterns["invalid"]:
        stats = cat_stats[cat]
        dims = CATEGORY_DIMENSION_MAP.get(cat, [])
        for dim in dims:
            if dim in dimension_adjustments:
                # Only override to decrease if not already set to increase by
                # a stronger (validated) signal
                if dimension_adjustments[dim]["direction"] != "increase":
                    dimension_adjustments[dim]["direction"] = "decrease"
                dimension_adjustments[dim]["reason"].append(
                    f"{cat} predictions only {stats['accuracy']:.0f}% accurate -- invalid assumption"
                )
                dimension_adjustments[dim]["confidence_sources"].append(cat)

    # Compute recommended weights
    new_weights = dict(base_weights)
    shift = 0.02
    increase_dims = [d for d, a in dimension_adjustments.items() if a["direction"] == "increase"]
    decrease_dims = [d for d, a in dimension_adjustments.items() if a["direction"] == "decrease"]

    total_freed = 0.0
    for dim in decrease_dims:
        if dim in new_weights:
            actual_shift = min(shift, new_weights[dim] - 0.01)
            new_weights[dim] = round(new_weights[dim] - actual_shift, 4)
            total_freed += actual_shift

    if increase_dims and total_freed > 0:
        per_dim = total_freed / len(increase_dims)
        for dim in increase_dims:
            if dim in new_weights:
                new_weights[dim] = round(new_weights[dim] + per_dim, 4)

    # Normalize to 1.0
    total = sum(new_weights.values())
    if total > 0:
        new_weights = {k: round(v / total, 3) for k, v in new_weights.items()}

    # Generate YAML snippet for agent-rules.yaml
    yaml_lines = []
    yaml_lines.append("# Hypothesis-validated weight adjustments")
    yaml_lines.append(f"# Generated from {len(hypotheses)} hypotheses, "
                      f"{sum(s['resolved'] for s in cat_stats.values())} resolved")
    yaml_lines.append("hypothesis_weight_adjustments:")
    has_adjustments = False
    for dim in DIMENSION_ORDER:
        adj = dimension_adjustments[dim]
        if adj["direction"] != "keep":
            has_adjustments = True
            reason_str = "; ".join(adj["reason"])
            yaml_lines.append(f"  {dim}:")
            yaml_lines.append(f"    direction: {adj['direction']}")
            yaml_lines.append(f"    current: {base_weights.get(dim, 0.0)}")
            yaml_lines.append(f"    recommended: {new_weights.get(dim, 0.0)}")
            yaml_lines.append(f"    reason: \"{reason_str}\"")

    if not has_adjustments:
        yaml_lines.append("  # No adjustments recommended (insufficient validated patterns)")

    yaml_snippet = "\n".join(yaml_lines)

    # Generate human-readable report
    report_lines = []
    report_lines.append("HYPOTHESIS-VALIDATED WEIGHT ADJUSTMENTS")
    report_lines.append("=" * 60)
    report_lines.append(f"Hypotheses analyzed: {len(hypotheses)}")
    resolved_n = sum(s["resolved"] for s in cat_stats.values())
    report_lines.append(f"Resolved: {resolved_n}")
    report_lines.append("")

    if patterns["validated"]:
        report_lines.append("Validated Patterns (>50% accuracy):")
        for cat in patterns["validated"]:
            s = cat_stats[cat]
            dims = CATEGORY_DIMENSION_MAP.get(cat, [])
            dim_str = ", ".join(dims) if dims else "no mapped dimensions"
            report_lines.append(f"  {cat}: {s['accuracy']:.0f}% ({s['correct']}/{s['resolved']}) -> {dim_str}")
        report_lines.append("")

    if patterns["invalid"]:
        report_lines.append("Invalid Assumptions (<30% accuracy):")
        for cat in patterns["invalid"]:
            s = cat_stats[cat]
            dims = CATEGORY_DIMENSION_MAP.get(cat, [])
            dim_str = ", ".join(dims) if dims else "no mapped dimensions"
            report_lines.append(f"  {cat}: {s['accuracy']:.0f}% ({s['correct']}/{s['resolved']}) -> {dim_str}")
        report_lines.append("")

    if has_adjustments:
        report_lines.append("Recommended Weight Changes:")
        report_lines.append(f"  {'Dimension':<25s} {'Current':>8s} {'New':>8s}  Direction")
        report_lines.append("  " + "-" * 55)
        for dim in DIMENSION_ORDER:
            adj = dimension_adjustments[dim]
            if adj["direction"] != "keep":
                current = base_weights.get(dim, 0.0)
                new = new_weights.get(dim, 0.0)
                report_lines.append(f"  {dim:<25s} {current:>8.3f} {new:>8.3f}  {adj['direction']}")
        report_lines.append("")
        report_lines.append("Apply to strategy/agent-rules.yaml:")
        report_lines.append("  python scripts/outcome_learner.py --validate-hypotheses")
    else:
        report_lines.append("No weight adjustments recommended.")
        if resolved_n == 0:
            report_lines.append("  Record outcomes first: python scripts/check_outcomes.py --record <id> --outcome <result>")
        else:
            report_lines.append("  All patterns are inconclusive (30-50% accuracy). Need more data.")

    report = "\n".join(report_lines)

    return {
        "report": report,
        "adjustments": {
            dim: {
                "direction": dimension_adjustments[dim]["direction"],
                "current": base_weights.get(dim, 0.0),
                "recommended": new_weights.get(dim, 0.0),
                "reason": dimension_adjustments[dim]["reason"],
            }
            for dim in DIMENSION_ORDER
            if dimension_adjustments[dim]["direction"] != "keep"
        },
        "yaml_snippet": yaml_snippet,
        "category_accuracy": cat_stats,
        "patterns": patterns,
    }


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
    parser.add_argument("--drift-check", action="store_true",
                        help="Check drift between calibrated and base weights")
    parser.add_argument("--approve", action="store_true",
                        help="Approve saved calibration for score.py auto-application")
    parser.add_argument("--validate-hypotheses", action="store_true",
                        help="Run hypothesis validation and generate weight adjustment YAML snippet")
    parser.add_argument("--reviewer", default=os.environ.get("PIPELINE_OPERATOR") or os.environ.get("USER") or "unknown",
                        help="Reviewer handle for --approve")
    args = parser.parse_args()

    # Load base weights for recommendations
    try:
        from score import WEIGHTS
        base_weights = dict(WEIGHTS)
    except ImportError:
        base_weights = {dim: 1.0 / len(DIMENSION_ORDER) for dim in DIMENSION_ORDER}

    if args.validate_hypotheses:
        result = validate_hypotheses_with_weights(base_weights)
        print(result["report"])
        if result["yaml_snippet"]:
            print()
            print("--- YAML Snippet for strategy/agent-rules.yaml ---")
            print(result["yaml_snippet"])
        return

    if args.drift_check:
        if not CALIBRATION_FILE.exists():
            print(f"No calibration file found at {CALIBRATION_FILE}")
            return
        calibration = yaml.safe_load(CALIBRATION_FILE.read_text()) or {}
        print(drift_check_report(calibration, base_weights))
        return

    if args.approve:
        try:
            path = approve_calibration(args.reviewer)
        except (FileNotFoundError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            raise SystemExit(1)
        print(f"Approved calibration: {path}")
        print(f"Reviewer: {args.reviewer}")
        return

    # Collect outcome data
    data = collect_outcome_data()
    analysis = analyze_dimension_accuracy(data)

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
