#!/usr/bin/env python3
"""Outcome tracking: awaiting-response report, outcome recording, and stale alerts.

Tracks post-submission outcomes and response times across the pipeline.

Usage:
    python scripts/check_outcomes.py                 # Show entries awaiting response
    python scripts/check_outcomes.py --record <id> --outcome rejected --stage resume_screen
    python scripts/check_outcomes.py --record <id> --outcome acknowledged
    python scripts/check_outcomes.py --stale         # Entries >14d with no response
    python scripts/check_outcomes.py --summary       # Outcome statistics
"""

import argparse
import shutil
import sys
from datetime import date
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import (
    PIPELINE_DIR_CLOSED,
    PIPELINE_DIR_SUBMITTED,
    SIGNALS_DIR,
    load_entries,
    load_entry_by_id,
    parse_date,
    update_last_touched,
    update_yaml_field,
)

STALE_DAYS = 14
LIKELY_GHOSTED_DAYS = 30

VALID_OUTCOMES = {"accepted", "rejected", "withdrawn", "expired", "acknowledged"}
VALID_STAGES = {"resume_screen", "phone_screen", "technical", "onsite", "offer", "referral_screen"}

# Typical response windows by portal type (days)
TYPICAL_WINDOWS = {
    "greenhouse": (7, 21),
    "lever": (7, 21),
    "ashby": (7, 21),
    "workable": (7, 21),
    "submittable": (14, 60),
    "slideroom": (30, 90),
    "direct": (7, 30),
}


def get_submitted_entries() -> list[dict]:
    """Load all entries with submitted or acknowledged status."""
    entries = load_entries(
        dirs=[PIPELINE_DIR_SUBMITTED],
        include_filepath=True,
    )
    return [e for e in entries if e.get("status") in ("submitted", "acknowledged", "interview")]


def days_since_submission(entry: dict) -> int | None:
    """Calculate days since submission."""
    timeline = entry.get("timeline", {})
    if isinstance(timeline, dict):
        sub_date = parse_date(timeline.get("submitted"))
        if sub_date:
            return (date.today() - sub_date).days
    return None


def show_awaiting(entries: list[dict]):
    """Show all entries awaiting response."""
    if not entries:
        print("No entries awaiting response.")
        return

    print(f"ENTRIES AWAITING RESPONSE — {date.today().isoformat()}")
    print(f"{'=' * 70}")

    # Sort by days since submission (oldest first)
    def sort_key(e):
        days = days_since_submission(e)
        return days if days is not None else 0

    entries_sorted = sorted(entries, key=sort_key, reverse=True)

    for entry in entries_sorted:
        entry_id = entry.get("id", "?")
        name = entry.get("name", entry_id)
        status = entry.get("status", "?")
        days = days_since_submission(entry)

        target = entry.get("target", {})
        org = target.get("organization", "?") if isinstance(target, dict) else "?"
        portal = target.get("portal", "?") if isinstance(target, dict) else "?"

        conversion = entry.get("conversion", {})
        has_response = conversion.get("response_received") if isinstance(conversion, dict) else False

        # Expected window
        window = TYPICAL_WINDOWS.get(portal, (7, 30))
        window_str = f"typical: {window[0]}-{window[1]}d"

        # Status markers
        marker = ""
        if days is not None:
            if days > LIKELY_GHOSTED_DAYS:
                marker = " [LIKELY GHOSTED]"
            elif days > STALE_DAYS:
                marker = " [STALE]"
            elif has_response:
                marker = " [RESPONDED]"

        days_str = f"Day {days}" if days is not None else "Day ?"
        print(f"\n  {name}{marker}")
        print(f"    {org} | {status} | {days_str} | {portal} ({window_str})")

    print(f"\n{'=' * 70}")
    total_stale = sum(1 for e in entries if (days_since_submission(e) or 0) > STALE_DAYS)
    print(f"Total: {len(entries)} awaiting | {total_stale} stale (>{STALE_DAYS}d)")


def show_stale(entries: list[dict]):
    """Show only stale entries (>14 days, no response)."""
    stale = []
    for e in entries:
        days = days_since_submission(e)
        if days is None or days <= STALE_DAYS:
            continue
        conversion = e.get("conversion", {})
        has_response = conversion.get("response_received") if isinstance(conversion, dict) else False
        if has_response:
            continue
        stale.append((days, e))

    if not stale:
        print("No stale entries (all responded within 14 days or still within window).")
        return

    stale.sort(key=lambda x: -x[0])

    print(f"STALE SUBMISSIONS — No response after {STALE_DAYS}+ days")
    print(f"{'=' * 70}")

    for days, entry in stale:
        entry_id = entry.get("id", "?")
        name = entry.get("name", entry_id)
        target = entry.get("target", {})
        org = target.get("organization", "?") if isinstance(target, dict) else "?"

        action = "Follow up" if days <= LIKELY_GHOSTED_DAYS else "Consider withdrawn/ghosted"

        print(f"\n  [{days}d] {name}")
        print(f"    {org} — Suggested: {action}")

    print(f"\n{'=' * 70}")
    print(f"Total stale: {len(stale)}")
    print("\nLog follow-ups: python scripts/followup.py --log <id> --channel email --note \"...\"")
    print("Record outcome: python scripts/check_outcomes.py --record <id> --outcome rejected")


def record_outcome(
    entry_id: str,
    outcome: str,
    stage: str | None = None,
    note: str = "",
):
    """Record an outcome for a submitted entry."""
    filepath, entry = load_entry_by_id(entry_id)
    if not entry:
        print(f"Entry not found: {entry_id}", file=sys.stderr)
        sys.exit(1)

    if not filepath:
        print(f"No file path for entry: {entry_id}", file=sys.stderr)
        sys.exit(1)

    today_str = date.today().isoformat()
    content = filepath.read_text()

    # Update conversion fields
    data = yaml.safe_load(content)
    conversion = data.get("conversion", {})
    if not isinstance(conversion, dict):
        conversion = {}

    # Calculate time to response
    timeline = data.get("timeline", {})
    sub_date = parse_date(timeline.get("submitted")) if isinstance(timeline, dict) else None
    time_to_response = (date.today() - sub_date).days if sub_date else None

    # Update fields via YAML manipulation
    if outcome == "acknowledged":
        # Move to acknowledged status, not terminal
        content = update_yaml_field(content, "status", "acknowledged")
        # Set response received
        try:
            content = update_yaml_field(content, "response_received", "true", nested=True)
        except ValueError:
            pass
    elif outcome in ("accepted", "rejected", "withdrawn", "expired"):
        # Terminal outcome
        content = update_yaml_field(content, "status", "outcome")
        import re
        content = re.sub(
            r'^(outcome:)\s+.*$', rf'\1 {outcome}',
            content, count=1, flags=re.MULTILINE,
        )
        try:
            content = update_yaml_field(content, "response_received", "true", nested=True)
        except ValueError:
            pass

    # Set outcome_stage if provided
    if stage:
        try:
            content = update_yaml_field(content, "outcome_stage", stage, nested=True)
        except ValueError:
            # Add it to conversion section
            pass

    # Set time_to_response_days
    if time_to_response is not None:
        try:
            content = update_yaml_field(
                content, "time_to_response_days", str(time_to_response), nested=True,
            )
        except ValueError:
            pass

    # Set response_type
    try:
        content = update_yaml_field(content, "response_type", outcome, nested=True)
    except ValueError:
        pass

    content = update_last_touched(content)
    filepath.write_text(content)

    # Update conversion log
    _update_conversion_log(entry_id, outcome, stage, time_to_response)

    # Move to closed/ for terminal outcomes
    if outcome in ("accepted", "rejected", "withdrawn", "expired"):
        PIPELINE_DIR_CLOSED.mkdir(parents=True, exist_ok=True)
        dest = PIPELINE_DIR_CLOSED / filepath.name
        # Don't overwrite if already exists
        if dest.exists():
            dest = PIPELINE_DIR_CLOSED / f"{filepath.stem}-{today_str}{filepath.suffix}"
        shutil.move(str(filepath), str(dest))
        print(f"Moved to: pipeline/closed/{dest.name}")

    name = entry.get("name", entry_id)
    print(f"Recorded outcome for: {name}")
    print(f"  Outcome: {outcome}")
    if stage:
        print(f"  Stage: {stage}")
    if time_to_response is not None:
        print(f"  Time to response: {time_to_response} days")

    # Prompt for hypothesis capture on terminal outcomes
    if outcome in ("accepted", "rejected"):
        print(f"\n  → Capture hypothesis: python scripts/feedback_capture.py --entry {entry_id} --outcome {outcome}")


def _update_conversion_log(entry_id: str, outcome: str, stage: str | None, time_to_response: int | None):
    """Update the conversion log with outcome data."""
    log_path = SIGNALS_DIR / "conversion-log.yaml"
    if not log_path.exists():
        return

    with open(log_path) as f:
        log_data = yaml.safe_load(f) or {}

    entries = log_data.get("entries", []) or []
    for log_entry in entries:
        if isinstance(log_entry, dict) and log_entry.get("id") == entry_id:
            log_entry["outcome"] = outcome
            log_entry["response_date"] = date.today().isoformat()
            if time_to_response is not None:
                log_entry["time_to_response_days"] = time_to_response
            if stage:
                log_entry["outcome_stage"] = stage
            break

    log_data["entries"] = entries
    with open(log_path, "w") as f:
        yaml.dump(log_data, f, default_flow_style=False, sort_keys=False)


def show_summary(entries: list[dict]):
    """Show outcome statistics summary."""
    # Also load closed entries for complete picture
    closed = load_entries(dirs=[PIPELINE_DIR_CLOSED], include_filepath=True)
    all_entries = entries + closed

    submitted_count = len([e for e in all_entries
                          if e.get("status") in ("submitted", "acknowledged", "interview", "outcome")])

    outcomes = {}
    response_times = []
    for e in all_entries:
        outcome = e.get("outcome")
        if outcome:
            outcomes[outcome] = outcomes.get(outcome, 0) + 1

        conversion = e.get("conversion", {})
        if isinstance(conversion, dict):
            ttr = conversion.get("time_to_response_days")
            if ttr and isinstance(ttr, (int, float)) and ttr > 0:
                response_times.append(ttr)

    print(f"OUTCOME SUMMARY — {date.today().isoformat()}")
    print(f"{'=' * 50}")
    print(f"Total submitted (all time): {submitted_count}")
    print(f"With recorded outcome: {sum(outcomes.values())}")
    print(f"Awaiting response: {len(entries)}")

    if outcomes:
        print("\nOutcomes:")
        for outcome, count in sorted(outcomes.items(), key=lambda x: -x[1]):
            print(f"  {outcome:<15s} {count}")

    if response_times:
        avg_ttr = sum(response_times) / len(response_times)
        min_ttr = min(response_times)
        max_ttr = max(response_times)
        print("\nResponse Time (days):")
        print(f"  Mean: {avg_ttr:.1f} | Min: {min_ttr} | Max: {max_ttr}")
        print(f"  Sample size: {len(response_times)}")
    else:
        print("\nNo response time data recorded yet.")

    no_response = sum(1 for e in entries if (days_since_submission(e) or 0) > STALE_DAYS)
    if no_response:
        print(f"\nStale (>{STALE_DAYS}d, no response): {no_response}")


def main():
    parser = argparse.ArgumentParser(
        description="Outcome tracking: awaiting-response report, recording, stale alerts"
    )
    parser.add_argument("--record", metavar="ENTRY_ID",
                        help="Record an outcome for a submitted entry")
    parser.add_argument("--outcome", choices=sorted(VALID_OUTCOMES),
                        help="Outcome type (required with --record)")
    parser.add_argument("--stage", choices=sorted(VALID_STAGES),
                        help="Outcome stage (optional with --record)")
    parser.add_argument("--note", default="",
                        help="Note about the outcome")
    parser.add_argument("--stale", action="store_true",
                        help="Show only stale entries (>14d, no response)")
    parser.add_argument("--summary", action="store_true",
                        help="Show outcome statistics summary")
    args = parser.parse_args()

    if args.record:
        if not args.outcome:
            parser.error("--outcome is required when using --record")
        record_outcome(args.record, args.outcome, stage=args.stage, note=args.note)
        return

    entries = get_submitted_entries()

    if args.stale:
        show_stale(entries)
    elif args.summary:
        show_summary(entries)
    else:
        show_awaiting(entries)


if __name__ == "__main__":
    main()
