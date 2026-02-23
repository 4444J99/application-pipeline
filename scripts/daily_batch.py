#!/usr/bin/env python3
"""Generate a daily work plan sorted by deadline urgency + fit score.

Reads pipeline entries, prioritizes by deadline urgency (<14 days),
then sorts remaining by composite fit score. Groups by effort level
and fits within a time budget.
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
PIPELINE_DIRS = [
    REPO_ROOT / "pipeline" / "active",
    REPO_ROOT / "pipeline" / "submitted",
    REPO_ROOT / "pipeline" / "closed",
]

ACTIONABLE_STATUSES = {"qualified", "drafting", "staged"}

# Time estimates in minutes
EFFORT_MINUTES = {
    "quick": {"min": 15, "max": 45, "default": 30},
    "standard": {"min": 60, "max": 120, "default": 90},
    "deep": {"min": 180, "max": 360, "default": 270},
    "complex": {"min": 480, "max": 960, "default": 720},
}

URGENCY_DAYS = 14


def load_entries() -> list[dict]:
    """Load all pipeline YAML entries."""
    entries = []
    for pipeline_dir in PIPELINE_DIRS:
        if not pipeline_dir.exists():
            continue
        for filepath in sorted(pipeline_dir.glob("*.yaml")):
            if filepath.name.startswith("_"):
                continue
            with open(filepath) as f:
                data = yaml.safe_load(f)
            if isinstance(data, dict):
                entries.append(data)
    return entries


def parse_date(date_str) -> datetime | None:
    """Parse a date string into a datetime object."""
    if not date_str:
        return None
    try:
        return datetime.strptime(str(date_str), "%Y-%m-%d")
    except ValueError:
        return None


def get_effort_level(entry: dict) -> str:
    """Get effort level from submission, defaulting to 'standard'."""
    sub = entry.get("submission", {})
    if isinstance(sub, dict):
        return sub.get("effort_level", "standard") or "standard"
    return "standard"


def get_score(entry: dict) -> float:
    """Get composite fit score."""
    fit = entry.get("fit", {})
    if isinstance(fit, dict):
        return float(fit.get("score", 0))
    return 0.0


def get_deadline_info(entry: dict) -> tuple[datetime | None, str, int | None]:
    """Return (deadline_date, deadline_type, days_left)."""
    deadline = entry.get("deadline", {})
    if not isinstance(deadline, dict):
        return None, "unknown", None

    dtype = deadline.get("type", "unknown")
    date = parse_date(deadline.get("date"))

    if date:
        days_left = (date - datetime.now()).days
        return date, dtype, days_left

    return None, dtype, None


def format_amount(entry: dict) -> str:
    """Format amount for display."""
    amount = entry.get("amount", {})
    if not isinstance(amount, dict):
        return ""
    value = amount.get("value", 0)
    if value == 0:
        atype = amount.get("type", "")
        if atype == "in_kind":
            return "in-kind"
        return ""
    currency = amount.get("currency", "USD")
    if currency == "EUR":
        return f"EUR {value:,}"
    return f"${value:,}"


def format_entry_line(entry: dict, days_left: int | None = None) -> str:
    """Format a single entry for display."""
    name = entry.get("name", entry.get("id", "?"))
    status = entry.get("status", "?")
    effort = get_effort_level(entry)
    score = get_score(entry)
    amount = format_amount(entry)
    est = EFFORT_MINUTES.get(effort, EFFORT_MINUTES["standard"])

    deadline_str = ""
    if days_left is not None:
        dl = entry.get("deadline", {})
        date_str = dl.get("date", "") if isinstance(dl, dict) else ""
        deadline_str = f" — {date_str} ({days_left}d)"
    else:
        dl = entry.get("deadline", {})
        dtype = dl.get("type", "") if isinstance(dl, dict) else ""
        if dtype in ("rolling", "tba"):
            deadline_str = f" — {dtype}"

    amount_str = f" — {amount}" if amount else ""
    return (
        f"    {name}{deadline_str} — {status} — "
        f"{effort} (~{est['default']} min){amount_str}"
    )


def generate_batch(hours: float, show_all: bool = False):
    """Generate the daily work plan."""
    entries = load_entries()
    if not entries:
        print("No pipeline entries found.")
        sys.exit(1)

    budget_minutes = int(hours * 60)
    now = datetime.now()

    # Filter to actionable entries
    actionable = [e for e in entries if e.get("status") in ACTIONABLE_STATUSES]

    if not actionable:
        print("No actionable entries (qualified/drafting/staged).")
        return

    # Separate urgent (hard deadline <14 days) from the rest
    urgent = []
    by_score = []

    for entry in actionable:
        date, dtype, days_left = get_deadline_info(entry)

        # Skip past deadlines
        if days_left is not None and days_left < 0:
            continue

        if days_left is not None and days_left <= URGENCY_DAYS and dtype == "hard":
            urgent.append((days_left, entry))
        else:
            by_score.append(entry)

    # Sort urgent by days remaining (most urgent first)
    urgent.sort(key=lambda x: x[0])

    # Sort rest by score descending
    by_score.sort(key=lambda x: get_score(x), reverse=True)

    # Build the plan
    used_minutes = 0
    plan_urgent = []
    plan_scored = []
    overflow = []

    print(f"{'=' * 60}")
    print(f"DAILY WORK PLAN — {now.strftime('%A, %B %d, %Y')}")
    print(f"Budget: {hours:.1f} hours ({budget_minutes} min)")
    print(f"{'=' * 60}")

    # Urgent entries first
    if urgent:
        print(f"\n  URGENT (deadline <{URGENCY_DAYS}d):")
        for days_left, entry in urgent:
            effort = get_effort_level(entry)
            est = EFFORT_MINUTES.get(effort, EFFORT_MINUTES["standard"])["default"]
            marker = "!!!" if days_left <= 7 else "! "
            line = format_entry_line(entry, days_left)
            if used_minutes + est <= budget_minutes or show_all:
                print(f"  {marker} {line.strip()}")
                used_minutes += est
                plan_urgent.append(entry)
            else:
                overflow.append(("urgent", entry, days_left))

    # Scored entries
    if by_score:
        print(f"\n  BY SCORE:")
        for entry in by_score:
            effort = get_effort_level(entry)
            est = EFFORT_MINUTES.get(effort, EFFORT_MINUTES["standard"])["default"]
            score = get_score(entry)
            line = format_entry_line(entry)
            if used_minutes + est <= budget_minutes:
                print(f"    [{score:.1f}] {line.strip()}")
                used_minutes += est
                plan_scored.append(entry)
            elif show_all:
                print(f"    [{score:.1f}] {line.strip()}  [OVER BUDGET]")
                overflow.append(("scored", entry, None))
            else:
                overflow.append(("scored", entry, None))

    # Summary
    total = len(plan_urgent) + len(plan_scored)
    print(f"\n  {'─' * 40}")
    print(f"  Planned: {total} submissions | ~{used_minutes} min ({used_minutes / 60:.1f} hrs)")

    # Effort breakdown
    effort_counts = {}
    for entry in plan_urgent + plan_scored:
        effort = get_effort_level(entry)
        effort_counts[effort] = effort_counts.get(effort, 0) + 1
    if effort_counts:
        breakdown = ", ".join(f"{count} {level}" for level, count in
                              sorted(effort_counts.items(),
                                     key=lambda x: list(EFFORT_MINUTES.keys()).index(x[0])))
        print(f"  Effort mix: {breakdown}")

    remaining = budget_minutes - used_minutes
    if remaining > 15:
        print(f"  Buffer: {remaining} min remaining")

    if overflow:
        print(f"\n  DEFERRED ({len(overflow)} entries beyond today's budget):")
        for category, entry, days_left in overflow[:5]:
            score = get_score(entry)
            name = entry.get("name", entry.get("id", "?"))
            effort = get_effort_level(entry)
            if days_left is not None:
                print(f"    [{score:.1f}] {name} — {effort} — {days_left}d remaining")
            else:
                print(f"    [{score:.1f}] {name} — {effort}")
        if len(overflow) > 5:
            print(f"    ... and {len(overflow) - 5} more")

    print()


def main():
    parser = argparse.ArgumentParser(description="Generate daily application work plan")
    parser.add_argument("--hours", type=float, default=3.0,
                        help="Available hours for today's session (default: 3)")
    parser.add_argument("--all", action="store_true",
                        help="Show all entries including those beyond budget")
    args = parser.parse_args()

    generate_batch(args.hours, show_all=args.all)


if __name__ == "__main__":
    main()
