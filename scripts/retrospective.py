#!/usr/bin/env python3
"""Monthly retrospective prompt generator.

Generates a structured reflection prompt based on pipeline data from the
past month, surfacing patterns, wins, misses, and adjustment opportunities.

Usage:
    python scripts/retrospective.py             # Print prompt to stdout
    python scripts/retrospective.py --save      # Save to strategy/retrospectives/
    python scripts/retrospective.py --json      # JSON output
"""

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import (
    REPO_ROOT,
    load_entries,
    parse_date,
)


def _get_month_entries(entries: list[dict], lookback_days: int = 30) -> list[dict]:
    """Filter entries touched in the last N days."""
    cutoff = date.today() - timedelta(days=lookback_days)
    result = []
    for e in entries:
        lt = parse_date(e.get("last_touched"))
        if lt and lt >= cutoff:
            result.append(e)
    return result


def _count_by_status(entries: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for e in entries:
        s = e.get("status", "unknown")
        counts[s] = counts.get(s, 0) + 1
    return counts


def _count_outcomes(entries: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for e in entries:
        o = e.get("outcome")
        if o:
            counts[o] = counts.get(o, 0) + 1
    return counts


def _top_scores(entries: list[dict], n: int = 5) -> list[dict]:
    scored = []
    for e in entries:
        fit = e.get("fit", {})
        if isinstance(fit, dict):
            s = fit.get("composite") or fit.get("score")
            if s is not None:
                scored.append({"id": e.get("id", "?"), "score": float(s), "track": e.get("track", "?")})
    scored.sort(key=lambda x: -x["score"])
    return scored[:n]


def build_prompt(entries: list[dict], lookback_days: int = 30) -> dict:
    """Build the retrospective data and prompt."""
    month_entries = _get_month_entries(entries, lookback_days)
    status_counts = _count_by_status(month_entries)
    outcome_counts = _count_outcomes(month_entries)
    top = _top_scores(month_entries)

    today = date.today()
    period_start = today - timedelta(days=lookback_days)

    # Count submissions this period
    submitted_count = 0
    for e in entries:
        tl = e.get("timeline", {})
        if isinstance(tl, dict):
            sd = parse_date(tl.get("submitted"))
            if sd and sd >= period_start:
                submitted_count += 1

    data = {
        "period": f"{period_start.isoformat()} to {today.isoformat()}",
        "entries_touched": len(month_entries),
        "submissions": submitted_count,
        "status_distribution": status_counts,
        "outcomes": outcome_counts,
        "top_scores": top,
    }

    questions = [
        "What application(s) felt most aligned with your identity positions this month?",
        "Which submissions were you most confident about? Were those predictions accurate?",
        f"You touched {len(month_entries)} entries this period. Was the volume right, too high, or too low?",
        "Did any rejection or non-response reveal a blind spot in your scoring rubric?",
        "What relationship-building actions had the most impact? Any warm leads emerging?",
        "Are there tracks (grant, job, fellowship) you should increase or decrease focus on?",
        "What block or narrative module needs updating based on recent feedback?",
        "What's one thing you'd do differently next month?",
    ]

    if outcome_counts.get("rejected", 0) > 0:
        questions.append(
            f"You had {outcome_counts['rejected']} rejection(s). "
            "What pattern do you notice across them?"
        )

    if submitted_count == 0:
        questions.append(
            "No submissions this period. Was this intentional (research phase) "
            "or a pipeline stall?"
        )

    return {"data": data, "questions": questions}


def format_prompt(result: dict) -> str:
    """Format the retrospective as readable text."""
    data = result["data"]
    questions = result["questions"]
    lines = []

    lines.append(f"MONTHLY RETROSPECTIVE — {data['period']}")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"Entries touched:  {data['entries_touched']}")
    lines.append(f"Submissions:      {data['submissions']}")
    lines.append("")

    if data["status_distribution"]:
        lines.append("Status Distribution:")
        for status, count in sorted(data["status_distribution"].items()):
            lines.append(f"  {status:<20s} {count}")
        lines.append("")

    if data["outcomes"]:
        lines.append("Outcomes:")
        for outcome, count in sorted(data["outcomes"].items()):
            lines.append(f"  {outcome:<20s} {count}")
        lines.append("")

    if data["top_scores"]:
        lines.append("Top Scores:")
        for t in data["top_scores"]:
            lines.append(f"  {t['id']:<40s} {t['score']:>5.1f}  ({t['track']})")
        lines.append("")

    lines.append("REFLECTION QUESTIONS")
    lines.append("-" * 40)
    for i, q in enumerate(questions, 1):
        lines.append(f"\n{i}. {q}")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Monthly retrospective prompt generator")
    parser.add_argument("--save", action="store_true", help="Save to strategy/retrospectives/")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--days", type=int, default=30, help="Lookback period (default: 30)")
    args = parser.parse_args()

    entries = load_entries()
    result = build_prompt(entries, args.days)

    if args.json:
        print(json.dumps(result, indent=2, default=str))
        return

    output = format_prompt(result)
    print(output)

    if args.save:
        retro_dir = REPO_ROOT / "strategy" / "retrospectives"
        retro_dir.mkdir(parents=True, exist_ok=True)
        filepath = retro_dir / f"{date.today().isoformat()}-retrospective.md"
        filepath.write_text(output)
        print(f"\nSaved to {filepath}")


if __name__ == "__main__":
    main()
