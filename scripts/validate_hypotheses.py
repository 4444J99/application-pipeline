#!/usr/bin/env python3
"""Hypothesis validation: compare predicted vs actual outcomes.

Reads hypotheses from signals/hypotheses.yaml and matches them against
conversion-log.yaml outcomes to calculate prediction accuracy.

Usage:
    python scripts/validate_hypotheses.py                 # Full validation report
    python scripts/validate_hypotheses.py --unresolved    # Show only unresolved
    python scripts/validate_hypotheses.py --accuracy      # Accuracy stats only
"""

import argparse
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


def validate(hypotheses: list[dict], outcomes: dict[str, str]) -> list[dict]:
    """Match hypotheses against known outcomes."""
    results = []
    for hyp in hypotheses:
        entry_id = hyp.get("entry_id") or hyp.get("id")
        predicted = hyp.get("predicted_outcome") or hyp.get("prediction")
        actual = outcomes.get(entry_id) if entry_id else None

        result = {
            "hypothesis_id": hyp.get("hypothesis_id") or hyp.get("id", "?"),
            "entry_id": entry_id,
            "hypothesis": hyp.get("hypothesis") or hyp.get("reason", ""),
            "predicted": predicted,
            "actual": actual,
        }

        if actual and predicted:
            result["validated"] = actual == predicted
        else:
            result["validated"] = None  # unresolved

        results.append(result)
    return results


def print_report(results: list[dict], unresolved_only: bool = False) -> None:
    """Print validation report."""
    resolved = [r for r in results if r["validated"] is not None]
    unresolved = [r for r in results if r["validated"] is None]

    if not unresolved_only:
        correct = sum(1 for r in resolved if r["validated"])
        incorrect = sum(1 for r in resolved if not r["validated"])

        print("Hypothesis Validation Report")
        print("=" * 50)
        print(f"  Total hypotheses: {len(results)}")
        print(f"  Resolved: {len(resolved)}")
        print(f"  Unresolved: {len(unresolved)}")
        if resolved:
            accuracy = correct / len(resolved) * 100
            print(f"  Correct: {correct} | Incorrect: {incorrect}")
            print(f"  Accuracy: {accuracy:.1f}%")
        print()

        if resolved:
            print("Resolved Hypotheses:")
            for r in resolved:
                marker = "CORRECT" if r["validated"] else "WRONG"
                print(f"  [{marker}] {r['entry_id']}: {r['hypothesis'][:60]}")
                print(f"           predicted={r['predicted']} actual={r['actual']}")
            print()

    if unresolved:
        print(f"Unresolved Hypotheses ({len(unresolved)}):")
        for r in unresolved:
            print(f"  {r['entry_id'] or '?'}: {r['hypothesis'][:70]}")
            if r["predicted"]:
                print(f"    Predicted: {r['predicted']}")


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


def main():
    parser = argparse.ArgumentParser(description="Validate outcome hypotheses")
    parser.add_argument("--unresolved", action="store_true", help="Show only unresolved hypotheses")
    parser.add_argument("--accuracy", action="store_true", help="Show accuracy stats only")
    args = parser.parse_args()

    hypotheses = load_hypotheses()
    if not hypotheses:
        print("No hypotheses found in signals/hypotheses.yaml")
        return

    outcomes = build_outcome_map(load_conversion_log())
    results = validate(hypotheses, outcomes)

    if args.accuracy:
        stats = accuracy_stats(results)
        print(f"Hypothesis accuracy: {stats['accuracy']:.1f}% "
              f"({stats['correct']}/{stats['resolved']} resolved, "
              f"{stats['unresolved']} pending)")
        return

    print_report(results, unresolved_only=args.unresolved)


if __name__ == "__main__":
    main()
