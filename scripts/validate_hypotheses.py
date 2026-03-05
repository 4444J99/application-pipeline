#!/usr/bin/env python3
"""Hypothesis validation: compare predicted vs actual outcomes.

Reads hypotheses from signals/hypotheses.yaml and cross-references each
hypothesis's entry_id against conversion-log.yaml to determine whether
predictions were correct. Calculates accuracy by category to surface
validated patterns and invalid assumptions.

Usage:
    python scripts/validate_hypotheses.py                 # Full validation report
    python scripts/validate_hypotheses.py --unresolved    # Show only unresolved
    python scripts/validate_hypotheses.py --accuracy      # Accuracy stats only
    python scripts/validate_hypotheses.py --by-category   # Category accuracy breakdown
    python scripts/validate_hypotheses.py --patterns      # Show validated/invalid patterns
    python scripts/validate_hypotheses.py --json          # Machine-readable JSON output
"""

import argparse
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import SIGNALS_DIR


def load_hypotheses() -> list[dict]:
    """Load hypotheses.yaml."""
    path = SIGNALS_DIR / "hypotheses.yaml"
    if not path.exists():
        return []
    with open(path) as f:
        data = yaml.safe_load(f) or []
    if isinstance(data, dict):
        hypotheses = data.get("hypotheses", [])
        return hypotheses if isinstance(hypotheses, list) else []
    return data if isinstance(data, list) else []


def load_conversion_log() -> list[dict]:
    """Load conversion-log.yaml."""
    path = SIGNALS_DIR / "conversion-log.yaml"
    if not path.exists():
        return []
    with open(path) as f:
        data = yaml.safe_load(f) or []
    if isinstance(data, dict):
        entries = data.get("entries", [])
        return entries if isinstance(entries, list) else []
    return data if isinstance(data, list) else []


def build_outcome_map(log: list[dict]) -> dict[str, str]:
    """Map entry_id -> outcome from conversion log."""
    outcomes = {}
    for entry in log:
        eid = entry.get("entry_id") or entry.get("id")
        outcome = entry.get("outcome")
        if eid and outcome:
            outcomes[eid] = outcome
    return outcomes


def build_outcome_detail_map(log: list[dict]) -> dict[str, dict]:
    """Map entry_id -> full outcome detail (outcome, outcome_stage, feedback)."""
    details = {}
    for entry in log:
        eid = entry.get("entry_id") or entry.get("id")
        if not eid:
            continue
        details[eid] = {
            "outcome": entry.get("outcome"),
            "outcome_stage": entry.get("outcome_stage"),
            "feedback": entry.get("feedback"),
            "time_to_response_days": entry.get("time_to_response_days"),
        }
    return details


# Category correctness rules: given a hypothesis category, which outcomes
# confirm the hypothesis was directionally correct. A "timing" hypothesis
# predicts rejection due to external factors; if the entry was indeed
# rejected (not accepted), the hypothesis is considered correct.
# "acknowledged" is non-terminal -- it means no outcome yet.
CATEGORY_CONFIRMS_ON = {
    "timing": {"rejected", "expired"},
    "auto_rejection": {"rejected", "expired"},
    "resume_screen": {"rejected"},
    "cover_letter": {"rejected"},
    "credential_gap": {"rejected"},
    "portfolio_gap": {"rejected"},
    "role_fit": {"rejected", "withdrawn"},
    "compensation": {"rejected", "withdrawn"},
    "ie_framing": {"rejected"},
    "other": {"rejected"},
}

# Outcomes that disprove a negative hypothesis (entry succeeded despite concern).
CATEGORY_DISPROVES_ON = {
    "timing": {"accepted", "interview"},
    "auto_rejection": {"accepted", "interview"},
    "resume_screen": {"accepted", "interview"},
    "cover_letter": {"accepted", "interview"},
    "credential_gap": {"accepted", "interview"},
    "portfolio_gap": {"accepted", "interview"},
    "role_fit": {"accepted", "interview"},
    "compensation": {"accepted", "interview"},
    "ie_framing": {"accepted", "interview"},
    "other": {"accepted", "interview"},
}

# Non-terminal outcomes that leave a hypothesis unresolved.
NON_TERMINAL_OUTCOMES = {"acknowledged", None}


def validate(hypotheses: list[dict], outcomes: dict[str, str]) -> list[dict]:
    """Match hypotheses against known outcomes.

    Uses category-aware correctness: a hypothesis with category "timing"
    that predicts failure is validated if the entry was rejected/expired,
    and invalidated if the entry progressed to interview/accepted.
    Also supports legacy predicted_outcome exact matching.
    """
    results = []
    for hyp in hypotheses:
        entry_id = hyp.get("entry_id") or hyp.get("id")
        predicted = hyp.get("predicted_outcome") or hyp.get("prediction")
        category = hyp.get("category", "other")
        actual = outcomes.get(entry_id) if entry_id else None

        result = {
            "hypothesis_id": hyp.get("hypothesis_id") or hyp.get("id", "?"),
            "entry_id": entry_id,
            "category": category,
            "hypothesis": hyp.get("hypothesis") or hyp.get("reason", ""),
            "predicted": predicted,
            "actual": actual,
        }

        if actual in NON_TERMINAL_OUTCOMES:
            # No terminal outcome yet
            result["validated"] = None
        elif predicted and actual:
            # Legacy exact-match mode: predicted_outcome == actual outcome
            result["validated"] = actual == predicted
        elif actual:
            # Category-based validation: check if actual outcome confirms
            # or disproves the hypothesis category
            confirms = CATEGORY_CONFIRMS_ON.get(category, set())
            disproves = CATEGORY_DISPROVES_ON.get(category, set())
            if actual in confirms:
                result["validated"] = True
            elif actual in disproves:
                result["validated"] = False
            else:
                # Ambiguous outcome (e.g., "withdrawn" for a "timing" hypothesis)
                result["validated"] = None
        else:
            result["validated"] = None

        results.append(result)
    return results


def accuracy_stats(results: list[dict]) -> dict:
    """Return accuracy statistics as a dict (for velocity_report integration)."""
    resolved = [r for r in results if r["validated"] is not None]
    correct = sum(1 for r in resolved if r["validated"])
    return {
        "total": len(results),
        "resolved": len(resolved),
        "correct": correct,
        "incorrect": len(resolved) - correct,
        "accuracy": (correct / len(resolved) * 100) if resolved else 0.0,
        "unresolved": len(results) - len(resolved),
    }


def accuracy_by_category(results: list[dict]) -> dict[str, dict]:
    """Compute accuracy per hypothesis category.

    Returns dict mapping category -> {total, resolved, correct, incorrect,
    accuracy, pattern} where pattern is "validated_pattern" (>50% accurate),
    "invalid_assumption" (<30% accurate), or "inconclusive".
    """
    by_cat: dict[str, list[dict]] = {}
    for r in results:
        cat = r.get("category", "other")
        by_cat.setdefault(cat, []).append(r)

    category_stats = {}
    for cat, cat_results in sorted(by_cat.items()):
        resolved = [r for r in cat_results if r["validated"] is not None]
        correct = sum(1 for r in resolved if r["validated"])
        total = len(cat_results)
        resolved_n = len(resolved)
        accuracy = (correct / resolved_n * 100) if resolved_n else 0.0

        # Determine pattern classification
        if resolved_n == 0:
            pattern = "no_data"
        elif accuracy > 50.0:
            pattern = "validated_pattern"
        elif accuracy < 30.0:
            pattern = "invalid_assumption"
        else:
            pattern = "inconclusive"

        category_stats[cat] = {
            "total": total,
            "resolved": resolved_n,
            "correct": correct,
            "incorrect": resolved_n - correct,
            "accuracy": round(accuracy, 1),
            "pattern": pattern,
        }

    return category_stats


def classify_patterns(category_stats: dict[str, dict]) -> dict[str, list[str]]:
    """Classify categories into validated, invalid, and inconclusive patterns.

    Returns dict with keys "validated", "invalid", "inconclusive", "no_data",
    each mapping to a list of category names.
    """
    classified: dict[str, list[str]] = {
        "validated": [],
        "invalid": [],
        "inconclusive": [],
        "no_data": [],
    }
    for cat, stats in sorted(category_stats.items()):
        pattern = stats["pattern"]
        if pattern == "validated_pattern":
            classified["validated"].append(cat)
        elif pattern == "invalid_assumption":
            classified["invalid"].append(cat)
        elif pattern == "no_data":
            classified["no_data"].append(cat)
        else:
            classified["inconclusive"].append(cat)
    return classified


def print_report(results: list[dict], unresolved_only: bool = False) -> None:
    """Print full validation report with category breakdown."""
    resolved = [r for r in results if r["validated"] is not None]
    unresolved = [r for r in results if r["validated"] is None]

    if not unresolved_only:
        correct = sum(1 for r in resolved if r["validated"])
        incorrect = sum(1 for r in resolved if not r["validated"])

        print("Hypothesis Validation Report")
        print("=" * 60)
        print(f"  Total hypotheses: {len(results)}")
        print(f"  Resolved: {len(resolved)}")
        print(f"  Unresolved: {len(unresolved)}")
        if resolved:
            accuracy = correct / len(resolved) * 100
            print(f"  Correct: {correct} | Incorrect: {incorrect}")
            print(f"  Accuracy: {accuracy:.1f}%")
        print()

        # Category accuracy breakdown
        cat_stats = accuracy_by_category(results)
        if cat_stats:
            print("Accuracy by Category:")
            print(f"  {'Category':<20s} {'Total':>5s} {'Resolved':>8s} {'Correct':>7s} {'Accuracy':>8s}  Pattern")
            print("  " + "-" * 70)
            for cat, stats in sorted(cat_stats.items(), key=lambda x: -x[1]["total"]):
                acc_str = f"{stats['accuracy']:.0f}%" if stats["resolved"] > 0 else "n/a"
                pattern_label = stats["pattern"].replace("_", " ")
                marker = ""
                if stats["pattern"] == "validated_pattern":
                    marker = " [VALIDATED]"
                elif stats["pattern"] == "invalid_assumption":
                    marker = " [INVALID]"
                print(f"  {cat:<20s} {stats['total']:>5d} {stats['resolved']:>8d} "
                      f"{stats['correct']:>7d} {acc_str:>8s}  {pattern_label}{marker}")
            print()

        # Pattern summary
        patterns = classify_patterns(cat_stats)
        if patterns["validated"]:
            print("Validated Patterns (>50% accurate):")
            for cat in patterns["validated"]:
                stats = cat_stats[cat]
                print(f"  {cat}: {stats['accuracy']:.0f}% ({stats['correct']}/{stats['resolved']})")
            print()
        if patterns["invalid"]:
            print("Invalid Assumptions (<30% accurate):")
            for cat in patterns["invalid"]:
                stats = cat_stats[cat]
                print(f"  {cat}: {stats['accuracy']:.0f}% ({stats['correct']}/{stats['resolved']})")
            print()

        if resolved:
            print("Resolved Hypotheses:")
            for r in resolved:
                marker = "CORRECT" if r["validated"] else "WRONG"
                print(f"  [{marker}] {r['entry_id']}: {r['hypothesis'][:60]}")
                cat_label = f"category={r['category']}"
                pred_label = f" predicted={r['predicted']}" if r["predicted"] else ""
                print(f"           {cat_label}{pred_label} actual={r['actual']}")
            print()

    if unresolved:
        print(f"Unresolved Hypotheses ({len(unresolved)}):")
        for r in unresolved:
            status_note = f" (actual={r['actual']})" if r["actual"] else ""
            print(f"  {r['entry_id'] or '?'}: {r['hypothesis'][:70]}")
            print(f"    category={r['category']}{status_note}")


def generate_full_report(results: list[dict]) -> dict:
    """Generate a structured report suitable for JSON output or integration.

    Returns dict with summary, category_accuracy, patterns, resolved, unresolved.
    """
    stats = accuracy_stats(results)
    cat_stats = accuracy_by_category(results)
    patterns = classify_patterns(cat_stats)

    resolved = [
        {
            "entry_id": r["entry_id"],
            "category": r["category"],
            "hypothesis": r["hypothesis"],
            "predicted": r["predicted"],
            "actual": r["actual"],
            "correct": r["validated"],
        }
        for r in results if r["validated"] is not None
    ]
    unresolved = [
        {
            "entry_id": r["entry_id"],
            "category": r["category"],
            "hypothesis": r["hypothesis"],
            "actual": r["actual"],
        }
        for r in results if r["validated"] is None
    ]

    return {
        "summary": stats,
        "category_accuracy": cat_stats,
        "patterns": patterns,
        "resolved": resolved,
        "unresolved": unresolved,
    }


def main():
    parser = argparse.ArgumentParser(description="Validate outcome hypotheses")
    parser.add_argument("--unresolved", action="store_true", help="Show only unresolved hypotheses")
    parser.add_argument("--accuracy", action="store_true", help="Show accuracy stats only")
    parser.add_argument("--by-category", action="store_true", help="Show accuracy by category")
    parser.add_argument("--patterns", action="store_true", help="Show validated/invalid pattern classification")
    parser.add_argument("--json", action="store_true", help="Machine-readable JSON output")
    args = parser.parse_args()

    hypotheses = load_hypotheses()
    if not hypotheses:
        print("No hypotheses found in signals/hypotheses.yaml")
        return

    outcomes = build_outcome_map(load_conversion_log())
    results = validate(hypotheses, outcomes)

    if args.json:
        report = generate_full_report(results)
        print(json.dumps(report, indent=2))
        return

    if args.accuracy:
        stats = accuracy_stats(results)
        print(f"Hypothesis accuracy: {stats['accuracy']:.1f}% "
              f"({stats['correct']}/{stats['resolved']} resolved, "
              f"{stats['unresolved']} pending)")
        return

    if args.by_category:
        cat_stats = accuracy_by_category(results)
        print("Hypothesis Accuracy by Category")
        print("=" * 60)
        print(f"  {'Category':<20s} {'Total':>5s} {'Resolved':>8s} {'Correct':>7s} {'Accuracy':>8s}  Pattern")
        print("  " + "-" * 70)
        for cat, stats in sorted(cat_stats.items(), key=lambda x: -x[1]["total"]):
            acc_str = f"{stats['accuracy']:.0f}%" if stats["resolved"] > 0 else "n/a"
            print(f"  {cat:<20s} {stats['total']:>5d} {stats['resolved']:>8d} "
                  f"{stats['correct']:>7d} {acc_str:>8s}  {stats['pattern'].replace('_', ' ')}")
        return

    if args.patterns:
        cat_stats = accuracy_by_category(results)
        patterns = classify_patterns(cat_stats)
        print("Hypothesis Pattern Classification")
        print("=" * 60)
        if patterns["validated"]:
            print("\nValidated Patterns (>50% accuracy -- trust these signals):")
            for cat in patterns["validated"]:
                s = cat_stats[cat]
                print(f"  {cat}: {s['accuracy']:.0f}% ({s['correct']}/{s['resolved']})")
        if patterns["invalid"]:
            print("\nInvalid Assumptions (<30% accuracy -- stop using these):")
            for cat in patterns["invalid"]:
                s = cat_stats[cat]
                print(f"  {cat}: {s['accuracy']:.0f}% ({s['correct']}/{s['resolved']})")
        if patterns["inconclusive"]:
            print("\nInconclusive (30-50% accuracy -- need more data):")
            for cat in patterns["inconclusive"]:
                s = cat_stats[cat]
                print(f"  {cat}: {s['accuracy']:.0f}% ({s['correct']}/{s['resolved']})")
        if patterns["no_data"]:
            print(f"\nNo resolved data: {', '.join(patterns['no_data'])}")
        return

    print_report(results, unresolved_only=args.unresolved)


if __name__ == "__main__":
    main()
