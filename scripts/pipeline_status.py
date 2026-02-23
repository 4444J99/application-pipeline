#!/usr/bin/env python3
"""Show current pipeline state and upcoming deadlines."""

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
PIPELINE_DIRS = [
    ("active", REPO_ROOT / "pipeline" / "active"),
    ("submitted", REPO_ROOT / "pipeline" / "submitted"),
    ("closed", REPO_ROOT / "pipeline" / "closed"),
]

STATUS_ORDER = [
    "research", "qualified", "drafting", "staged",
    "submitted", "acknowledged", "interview", "outcome",
]


def load_entries() -> list[dict]:
    """Load all pipeline YAML entries."""
    entries = []
    for stage, pipeline_dir in PIPELINE_DIRS:
        if not pipeline_dir.exists():
            continue
        for filepath in sorted(pipeline_dir.glob("*.yaml")):
            if filepath.name.startswith("_"):
                continue
            with open(filepath) as f:
                data = yaml.safe_load(f)
            if isinstance(data, dict):
                data["_dir"] = stage
                data["_file"] = filepath.name
                entries.append(data)
    return entries


def parse_date(date_str: str | None) -> datetime | None:
    """Parse a date string into a datetime object."""
    if not date_str:
        return None
    try:
        return datetime.strptime(str(date_str), "%Y-%m-%d")
    except ValueError:
        return None


def format_amount(amount: dict | None) -> str:
    """Format amount for display."""
    if not amount or not isinstance(amount, dict):
        return "—"
    value = amount.get("value", 0)
    currency = amount.get("currency", "USD")
    if value == 0:
        atype = amount.get("type", "")
        if atype == "in_kind":
            return "In-kind"
        if atype == "variable":
            return "Variable"
        return "—"
    if currency == "EUR":
        return f"EUR {value:,}"
    return f"${value:,}"


def print_summary(entries: list[dict]):
    """Print pipeline summary by status."""
    status_counts: dict[str, int] = {}
    track_counts: dict[str, int] = {}

    for entry in entries:
        status = entry.get("status", "unknown")
        track = entry.get("track", "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
        track_counts[track] = track_counts.get(track, 0) + 1

    print("=" * 60)
    print("APPLICATION PIPELINE STATUS")
    print("=" * 60)
    print(f"\nTotal entries: {len(entries)}\n")

    print("By Status:")
    for status in STATUS_ORDER:
        count = status_counts.get(status, 0)
        if count > 0:
            bar = "#" * count
            print(f"  {status:15s} {count:3d}  {bar}")

    print("\nBy Track:")
    for track, count in sorted(track_counts.items(), key=lambda x: -x[1]):
        print(f"  {track:15s} {count:3d}")


def print_upcoming(entries: list[dict], days: int = 30):
    """Print entries with upcoming deadlines."""
    now = datetime.now()
    cutoff = now + timedelta(days=days)
    upcoming = []

    for entry in entries:
        deadline = entry.get("deadline", {})
        if not isinstance(deadline, dict):
            continue
        date = parse_date(deadline.get("date"))
        if date and now <= date <= cutoff:
            upcoming.append((date, entry))

    upcoming.sort(key=lambda x: x[0])

    print(f"\n{'=' * 60}")
    print(f"UPCOMING DEADLINES (next {days} days)")
    print("=" * 60)

    if not upcoming:
        print("\n  No deadlines in this window.")
        return

    for date, entry in upcoming:
        days_left = (date - now).days
        name = entry.get("name", entry.get("id", "?"))
        status = entry.get("status", "?")
        amount = format_amount(entry.get("amount"))
        fit = entry.get("fit", {})
        score = fit.get("score", "?") if isinstance(fit, dict) else "?"

        urgency = "!!!" if days_left <= 7 else "! " if days_left <= 14 else "  "
        print(f"\n  {urgency} {date.strftime('%b %d')} ({days_left}d) — {name}")
        print(f"      Status: {status} | Fit: {score}/10 | Amount: {amount}")


def print_rolling(entries: list[dict]):
    """Print rolling/TBA entries."""
    rolling = []
    for entry in entries:
        deadline = entry.get("deadline", {})
        if not isinstance(deadline, dict):
            continue
        dtype = deadline.get("type", "")
        if dtype in ("rolling", "tba"):
            rolling.append(entry)

    if not rolling:
        return

    print(f"\n{'=' * 60}")
    print("ROLLING / TBA DEADLINES")
    print("=" * 60)

    for entry in rolling:
        name = entry.get("name", entry.get("id", "?"))
        status = entry.get("status", "?")
        amount = format_amount(entry.get("amount"))
        fit = entry.get("fit", {})
        score = fit.get("score", "?") if isinstance(fit, dict) else "?"
        print(f"\n  {name}")
        print(f"      Status: {status} | Fit: {score}/10 | Amount: {amount}")


BENEFITS_THRESHOLDS = {
    "snap": {"limit": 20352, "program": "SNAP"},
    "medicaid": {"limit": 21597, "program": "Medicaid (NY)"},
    "fair_fares": {"limit": 22692, "program": "Fair Fares NYC"},
    "essential_plan": {"limit": 39125, "program": "Essential Plan (NY)"},
}

IN_FLIGHT_STATUSES = {"qualified", "drafting", "staged", "submitted", "acknowledged", "interview"}


def print_benefits_check(entries: list[dict]):
    """Check total in-flight compensation against benefits thresholds."""
    print(f"\n{'=' * 60}")
    print("BENEFITS CLIFF CHECK")
    print("=" * 60)

    in_flight = []
    total_usd = 0

    for entry in entries:
        status = entry.get("status", "")
        if status not in IN_FLIGHT_STATUSES:
            continue

        amount = entry.get("amount", {})
        if not isinstance(amount, dict):
            continue

        value = amount.get("value", 0)
        currency = amount.get("currency", "USD")
        if value <= 0:
            continue

        # Convert EUR to approximate USD for threshold comparison
        if currency == "EUR":
            value_usd = int(value * 1.10)
        else:
            value_usd = value

        cliff_note = amount.get("benefits_cliff_note")
        name = entry.get("name", entry.get("id", "?"))
        in_flight.append((name, value_usd, currency, value, cliff_note, status))
        total_usd += value_usd

    if not in_flight:
        print("\n  No in-flight entries with compensation.")
        return

    print(f"\n  In-flight entries with compensation ({len(in_flight)}):\n")
    for name, value_usd, currency, raw_value, cliff_note, status in in_flight:
        amt_str = f"EUR {raw_value:,}" if currency == "EUR" else f"${raw_value:,}"
        flag = " !!!" if cliff_note else ""
        print(f"    {name}")
        print(f"      {amt_str} ({status}){flag}")
        if cliff_note:
            print(f"      Cliff note: {cliff_note}")

    print(f"\n  Total in-flight (USD): ${total_usd:,}")
    print(f"\n  Threshold analysis (if ALL accepted):")
    for key, info in BENEFITS_THRESHOLDS.items():
        limit = info["limit"]
        program = info["program"]
        if total_usd > limit:
            print(f"    !!! {program}: ${total_usd:,} exceeds ${limit:,} limit")
        else:
            remaining = limit - total_usd
            print(f"    OK  {program}: ${remaining:,} remaining under ${limit:,} limit")


def write_index(entries: list[dict]):
    """Write current pipeline summary to INDEX.md."""
    status_counts: dict[str, int] = {}
    track_counts: dict[str, int] = {}

    for entry in entries:
        status = entry.get("status", "unknown")
        track = entry.get("track", "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
        track_counts[track] = track_counts.get(track, 0) + 1

    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = [
        "# Pipeline Index",
        "",
        f"Generated by `pipeline_status.py --write-index` on {now}.",
        "",
        "Run `python scripts/pipeline_status.py` for live status.",
        "",
        "## Directories",
        "",
        "- `active/` — Applications in pipeline stages: research through staged",
        "- `submitted/` — Submitted, awaiting response",
        "- `closed/` — Final outcomes (accepted/rejected/withdrawn/expired)",
        "",
        "## Current State",
        "",
        f"**{len(entries)} entries** across {len(track_counts)} tracks:",
        "",
    ]

    for status in STATUS_ORDER:
        count = status_counts.get(status, 0)
        if count > 0:
            lines.append(f"- {count} {status}")

    lines.append("")
    lines.append("### By Track")
    lines.append("")
    for track, count in sorted(track_counts.items(), key=lambda x: -x[1]):
        lines.append(f"- {track}: {count}")

    lines.append("")
    lines.append("See `_schema.yaml` for the entry format.")
    lines.append("")

    index_path = REPO_ROOT / "pipeline" / "INDEX.md"
    index_path.write_text("\n".join(lines))
    print(f"Wrote {index_path}")


def main():
    parser = argparse.ArgumentParser(description="Pipeline status report")
    parser.add_argument("--upcoming", type=int, default=30,
                        help="Show deadlines within N days (default: 30)")
    parser.add_argument("--all", action="store_true",
                        help="Show all entries including rolling")
    parser.add_argument("--benefits-check", action="store_true",
                        help="Show benefits cliff analysis for in-flight entries")
    parser.add_argument("--write-index", action="store_true",
                        help="Write current summary to pipeline/INDEX.md")
    args = parser.parse_args()

    entries = load_entries()
    if not entries:
        print("No pipeline entries found.")
        sys.exit(1)

    if args.write_index:
        write_index(entries)
        return

    print_summary(entries)
    print_upcoming(entries, args.upcoming)

    if args.all:
        print_rolling(entries)

    if args.benefits_check:
        print_benefits_check(entries)

    print()


if __name__ == "__main__":
    main()
