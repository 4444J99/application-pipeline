#!/usr/bin/env python3
"""Feedback hypothesis capture: record structured outcome hypotheses for calibration.

Captures hypotheses when outcomes are recorded, enabling pattern analysis once
10+ outcomes exist. Designed for both interactive use and integration with
check_outcomes.py.

Usage:
    python scripts/feedback_capture.py --entry <id>
    python scripts/feedback_capture.py --entry <id> --outcome rejected \\
        --category resume_screen --hypothesis "Too many repos, no team PRs"
    python scripts/feedback_capture.py --list
    python scripts/feedback_capture.py --list --entry <id>
    python scripts/feedback_capture.py --analyze           # Pattern breakdown
"""

import argparse
import sys
from datetime import date
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import SIGNALS_DIR

HYPOTHESES_FILE = SIGNALS_DIR / "hypotheses.yaml"

VALID_CATEGORIES = [
    "resume_screen",     # Screened at resume review phase
    "cover_letter",      # Cover letter content or framing issue
    "credential_gap",    # Missing credential (degree, company, title)
    "timing",            # Role filled, headcount frozen, wrong cycle
    "auto_rejection",    # ATS filter before human review
    "portfolio_gap",     # Work samples insufficient for the bar
    "role_fit",          # Role scope mismatch (under/overqualified)
    "compensation",      # Comp expectations mismatch
    "ie_framing",        # Independent-engineer pattern-matched as contractor
    "other",             # Doesn't fit above categories
]

CATEGORY_DESCRIPTIONS = {
    "resume_screen":  "Screened at resume review (ATS or human)",
    "cover_letter":   "Cover letter content / framing / length issue",
    "credential_gap": "Missing expected credential or prior employer signal",
    "timing":         "External: role filled, freeze, wrong cycle",
    "auto_rejection": "ATS filter before human eyes",
    "portfolio_gap":  "Work samples or GitHub didn't meet the bar",
    "role_fit":       "Scope mismatch — under or overqualified",
    "compensation":   "Salary / rate expectations mismatch",
    "ie_framing":     "Solo-practitioner framing pattern-matched as contractor",
    "other":          "Doesn't fit above categories",
}


def load_hypotheses() -> list[dict]:
    """Load all recorded hypotheses."""
    if not HYPOTHESES_FILE.exists():
        return []
    with open(HYPOTHESES_FILE) as f:
        data = yaml.safe_load(f) or {}
    return data.get("hypotheses", []) or []


def save_hypotheses(hypotheses: list[dict]):
    """Save hypotheses to disk."""
    HYPOTHESES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(HYPOTHESES_FILE, "w") as f:
        yaml.dump({"hypotheses": hypotheses}, f, default_flow_style=False, sort_keys=False)


def add_hypothesis(record: dict):
    """Append a hypothesis record and persist."""
    hypotheses = load_hypotheses()
    # Deduplicate: if same entry + category + same date, update instead of append
    for existing in hypotheses:
        if (existing.get("entry_id") == record["entry_id"]
                and existing.get("category") == record["category"]
                and existing.get("date") == record["date"]):
            existing["hypothesis"] = record["hypothesis"]
            existing["outcome"] = record.get("outcome", existing.get("outcome"))
            save_hypotheses(hypotheses)
            print(f"Updated existing hypothesis for {record['entry_id']} [{record['category']}]")
            return
    hypotheses.append(record)
    save_hypotheses(hypotheses)
    preview = record["hypothesis"][:60]
    if len(record["hypothesis"]) > 60:
        preview += "..."
    print(f"Saved: [{record['category']}] {preview}")


def capture_interactive(entry_id: str, outcome: str | None = None) -> dict | None:
    """Run interactive hypothesis capture."""
    print(f"\nFEEDBACK HYPOTHESIS — {entry_id}")
    if outcome:
        print(f"Outcome: {outcome}")
    print("=" * 50)
    print("What category best describes why this outcome occurred?\n")

    for i, cat in enumerate(VALID_CATEGORIES, 1):
        desc = CATEGORY_DESCRIPTIONS[cat]
        print(f"  {i:>2}. {cat:<18s}  {desc}")

    choice = input("\nEnter number (or Enter to skip): ").strip()
    if not choice:
        return None

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(VALID_CATEGORIES):
            category = VALID_CATEGORIES[idx]
        else:
            category = "other"
    except ValueError:
        category = "other"

    print(f"\nCategory: {category} — {CATEGORY_DESCRIPTIONS[category]}")
    hypothesis = input("Hypothesis (what do you think happened?): ").strip()
    if not hypothesis:
        return None

    return {
        "entry_id": entry_id,
        "date": date.today().isoformat(),
        "outcome": outcome,
        "category": category,
        "hypothesis": hypothesis,
    }


def capture_noninteractive(
    entry_id: str,
    category: str,
    hypothesis: str,
    outcome: str | None = None,
) -> dict:
    """Build a hypothesis record from explicit args."""
    return {
        "entry_id": entry_id,
        "date": date.today().isoformat(),
        "outcome": outcome,
        "category": category,
        "hypothesis": hypothesis,
    }


def show_hypotheses(entry_id: str | None = None):
    """Display recorded hypotheses."""
    hypotheses = load_hypotheses()

    if entry_id:
        hypotheses = [h for h in hypotheses if h.get("entry_id") == entry_id]
        if not hypotheses:
            print(f"No hypotheses for: {entry_id}")
            return

    if not hypotheses:
        print("No hypotheses recorded yet.")
        print("\nRecord one: python scripts/feedback_capture.py --entry <id> --outcome rejected")
        return

    print(f"OUTCOME HYPOTHESES — {date.today().isoformat()}")
    print(f"{'=' * 60}")

    by_cat: dict[str, list] = {}
    for h in hypotheses:
        cat = h.get("category", "other")
        by_cat.setdefault(cat, []).append(h)

    for cat, items in sorted(by_cat.items(), key=lambda x: -len(x[1])):
        print(f"\n[{cat}] — {len(items)} {'entry' if len(items) == 1 else 'entries'}")
        for h in items:
            eid = h.get("entry_id", "?")
            outcome = h.get("outcome") or "?"
            text = h.get("hypothesis", "")
            date_str = h.get("date", "?")
            print(f"  {eid} ({outcome}, {date_str})")
            wrapped = text[:80] + ("..." if len(text) > 80 else "")
            print(f"    {wrapped}")

    print(f"\n{'=' * 60}")
    print(f"Total: {len(hypotheses)}")


def show_analysis():
    """Pattern analysis: category distribution and calibration status."""
    hypotheses = load_hypotheses()

    print(f"HYPOTHESIS PATTERN ANALYSIS — {date.today().isoformat()}")
    print(f"{'=' * 60}")
    print(f"Total hypotheses: {len(hypotheses)}")

    if len(hypotheses) < 5:
        remaining = 5 - len(hypotheses)
        print(f"  → {remaining} more needed for early pattern signal")
    elif len(hypotheses) < 10:
        remaining = 10 - len(hypotheses)
        print(f"  → {remaining} more needed for calibration-grade analysis")
    else:
        print("  → Sufficient data for scoring calibration")

    if not hypotheses:
        return

    # Category distribution
    by_cat: dict[str, int] = {}
    for h in hypotheses:
        cat = h.get("category", "other")
        by_cat[cat] = by_cat.get(cat, 0) + 1

    print(f"\nCategory breakdown (n={len(hypotheses)}):")
    for cat, count in sorted(by_cat.items(), key=lambda x: -x[1]):
        pct = count / len(hypotheses) * 100
        bar = "█" * count
        print(f"  {cat:<20s} {count:>3} ({pct:4.0f}%)  {bar}")

    # Outcome distribution
    by_outcome: dict[str, int] = {}
    for h in hypotheses:
        outcome = h.get("outcome") or "unrecorded"
        by_outcome[outcome] = by_outcome.get(outcome, 0) + 1

    print("\nOutcome breakdown:")
    for outcome, count in sorted(by_outcome.items(), key=lambda x: -x[1]):
        print(f"  {outcome:<20s} {count}")

    if len(hypotheses) >= 10:
        top_cat = max(by_cat, key=lambda k: by_cat[k])
        top_pct = by_cat[top_cat] / len(hypotheses) * 100
        print(f"\nDominant pattern: {top_cat} ({top_pct:.0f}% of outcomes)")
        print("  → Consider adjusting materials targeting this failure mode")


def main():
    parser = argparse.ArgumentParser(
        description="Capture and analyze outcome hypotheses for scoring calibration"
    )
    parser.add_argument("--entry", metavar="ENTRY_ID",
                        help="Entry ID to capture or display hypotheses for")
    parser.add_argument("--outcome", metavar="OUTCOME",
                        help="Outcome type (rejected, accepted, etc.)")
    parser.add_argument("--category", choices=VALID_CATEGORIES,
                        help="Hypothesis category (skips interactive prompt)")
    parser.add_argument("--hypothesis", metavar="TEXT",
                        help="Hypothesis text (skips interactive prompt)")
    parser.add_argument("--list", action="store_true",
                        help="List all recorded hypotheses (optionally for --entry)")
    parser.add_argument("--analyze", action="store_true",
                        help="Show category pattern analysis across all hypotheses")
    args = parser.parse_args()

    if args.analyze:
        show_analysis()
        return

    if args.list:
        show_hypotheses(entry_id=args.entry)
        return

    if not args.entry:
        parser.error("--entry is required (or use --list / --analyze)")

    # Non-interactive if both category and hypothesis provided
    if args.category and args.hypothesis:
        record = capture_noninteractive(
            entry_id=args.entry,
            category=args.category,
            hypothesis=args.hypothesis,
            outcome=args.outcome,
        )
        add_hypothesis(record)
        return

    # Interactive if TTY available
    if sys.stdin.isatty():
        record = capture_interactive(entry_id=args.entry, outcome=args.outcome)
        if record:
            add_hypothesis(record)
        else:
            print("No hypothesis recorded.")
    else:
        print("Non-interactive mode: provide --category and --hypothesis flags.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
