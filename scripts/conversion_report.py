#!/usr/bin/env python3
"""Analyze conversion rates by track, identity position, and framing."""

import sys

from pipeline_lib import SIGNALS_DIR, load_entries

CONVERSION_LOG = SIGNALS_DIR / "conversion-log.yaml"


def analyze_by_dimension(entries: list[dict], dimension: str, extract_fn) -> dict:
    """Analyze outcomes grouped by a dimension."""
    groups: dict[str, dict] = {}

    for entry in entries:
        key = extract_fn(entry)
        if key is None:
            continue

        if key not in groups:
            groups[key] = {"total": 0, "submitted": 0, "outcomes": 0,
                           "accepted": 0, "rejected": 0, "pending": 0}

        groups[key]["total"] += 1

        status = entry.get("status", "")
        if status in ("submitted", "acknowledged", "interview", "outcome"):
            groups[key]["submitted"] += 1

        outcome = entry.get("outcome")
        if outcome:
            groups[key]["outcomes"] += 1
            if outcome == "accepted":
                groups[key]["accepted"] += 1
            elif outcome == "rejected":
                groups[key]["rejected"] += 1
        elif status in ("submitted", "acknowledged", "interview"):
            groups[key]["pending"] += 1

    return groups


def print_report(title: str, groups: dict):
    """Print a conversion analysis report."""
    print(f"\n{title}")
    print("-" * len(title))

    if not groups:
        print("  No data available.")
        return

    for key, stats in sorted(groups.items(), key=lambda x: -x[1]["total"]):
        total = stats["total"]
        submitted = stats["submitted"]
        accepted = stats["accepted"]
        outcomes = stats["outcomes"]

        rate = f"{accepted}/{outcomes} ({100*accepted/outcomes:.0f}%)" if outcomes > 0 else "no outcomes yet"
        print(f"\n  {key}:")
        print(f"    Pipeline: {total} | Submitted: {submitted} | Outcomes: {outcomes}")
        print(f"    Conversion: {rate}")


def main():
    entries = load_entries()
    if not entries:
        print("No pipeline entries found.")
        sys.exit(1)

    print("=" * 60)
    print("CONVERSION REPORT")
    print("=" * 60)
    print(f"\nTotal pipeline entries: {len(entries)}")

    # Overall stats
    submitted = sum(1 for e in entries if e.get("status") in ("submitted", "acknowledged", "interview", "outcome"))
    with_outcome = sum(1 for e in entries if e.get("outcome"))
    accepted = sum(1 for e in entries if e.get("outcome") == "accepted")

    print(f"Submitted: {submitted}")
    print(f"With outcome: {with_outcome}")
    if with_outcome:
        print(f"Accepted: {accepted}/{with_outcome} ({100*accepted/with_outcome:.0f}%)")
    else:
        print("Accepted: no outcomes yet")

    # By track
    by_track = analyze_by_dimension(
        entries, "track", lambda e: e.get("track"))
    print_report("BY TRACK", by_track)

    # By identity position
    by_position = analyze_by_dimension(
        entries, "identity_position",
        lambda e: e.get("fit", {}).get("identity_position") if isinstance(e.get("fit"), dict) else None)
    print_report("BY IDENTITY POSITION", by_position)

    # By fit score bracket
    def score_bracket(entry):
        fit = entry.get("fit", {})
        if not isinstance(fit, dict):
            return None
        score = fit.get("score")
        if score is None:
            return None
        if score >= 9:
            return "9-10 (excellent)"
        if score >= 7:
            return "7-8 (good)"
        if score >= 5:
            return "5-6 (moderate)"
        return "1-4 (low)"

    by_score = analyze_by_dimension(entries, "fit score", score_bracket)
    print_report("BY FIT SCORE", by_score)

    print()


if __name__ == "__main__":
    main()
