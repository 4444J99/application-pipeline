#!/usr/bin/env python3
"""Outcome tracking: awaiting-response report, outcome recording, and stale alerts.

Tracks post-submission outcomes and response times across the pipeline.

Usage:
    python scripts/check_outcomes.py                 # Show entries awaiting response
    python scripts/check_outcomes.py --record <id> --outcome rejected --stage resume_screen
    python scripts/check_outcomes.py --record <id> --outcome acknowledged
    python scripts/check_outcomes.py --stale         # Entries >14d with no response
    python scripts/check_outcomes.py --summary       # Outcome statistics
    python scripts/check_outcomes.py --failure-themes --months 1
"""

import argparse
import json
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
    atomic_write,
    load_entries,
    load_entry_by_id,
    parse_date,
    update_last_touched,
    update_yaml_field,
)


def _load_outcome_thresholds() -> tuple[int, int, dict]:
    """Load stale/ghosted thresholds and response windows from market intelligence JSON."""
    intel_file = Path(__file__).resolve().parent.parent / "strategy" / "market-intelligence-2026.json"
    default_windows = {
        "greenhouse": (7, 21), "lever": (7, 21), "ashby": (7, 21), "workable": (7, 21),
        "submittable": (14, 60), "slideroom": (30, 90), "direct": (7, 30),
    }
    if not intel_file.exists():
        return 14, 30, default_windows
    try:
        with open(intel_file) as f:
            intel = json.load(f)
        t = intel.get("stale_thresholds_days", {})
        stale = t.get("response_overdue_job", 14)
        ghosted = t.get("response_ghosted_job", 30)
        windows_raw = intel.get("typical_response_windows", {})
        windows = {k: tuple(v) for k, v in windows_raw.items() if isinstance(v, list) and len(v) == 2}
        if not windows:
            windows = default_windows
        return stale, ghosted, windows
    except Exception:
        return 14, 30, default_windows


STALE_DAYS, LIKELY_GHOSTED_DAYS, TYPICAL_WINDOWS = _load_outcome_thresholds()

VALID_OUTCOMES = {"accepted", "rejected", "withdrawn", "expired", "acknowledged"}
VALID_STAGES = {"resume_screen", "phone_screen", "technical", "onsite", "offer", "referral_screen"}
VALID_REJECTION_REASONS = {
    "skills_mismatch",
    "experience_gap",
    "domain_mismatch",
    "location_constraint",
    "compensation_mismatch",
    "sponsorship_constraint",
    "portfolio_mismatch",
    "timing_cycle",
    "headcount_pause",
    "no_response",
    "unknown",
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


def _iter_conversion_log_entries() -> list[dict]:
    """Load conversion log entries from signals/conversion-log.yaml."""
    path = SIGNALS_DIR / "conversion-log.yaml"
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text()) or {}
    if isinstance(data, dict):
        entries = data.get("entries", [])
        return entries if isinstance(entries, list) else []
    return data if isinstance(data, list) else []


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
    rejection_reason: str | None = None,
    rejection_theme: str | None = None,
    rejection_evidence: str = "",
    _hypothesis_category: str | None = None,
    _hypothesis_text: str | None = None,
):
    """Record an outcome for a submitted entry."""
    filepath, entry = load_entry_by_id(entry_id)
    if not entry:
        print(f"Entry not found: {entry_id}", file=sys.stderr)
        sys.exit(1)

    if not filepath:
        print(f"No file path for entry: {entry_id}", file=sys.stderr)
        sys.exit(1)

    current_status = entry.get("status", "")
    if current_status not in ("submitted", "acknowledged", "interview"):
        print(
            f"Warning: entry '{entry_id}' has status '{current_status}', "
            f"expected submitted/acknowledged/interview",
            file=sys.stderr,
        )
        sys.exit(1)

    import re

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

    # Update fields via structured manipulation
    data = yaml.safe_load(content) or {}
    if "conversion" not in data or not isinstance(data["conversion"], dict):
        data["conversion"] = {}
    
    conv = data["conversion"]

    if outcome == "acknowledged":
        data["status"] = "acknowledged"
        conv["response_received"] = True
    elif outcome in ("accepted", "rejected", "withdrawn", "expired"):
        data["status"] = "outcome"
        data["outcome"] = outcome
        conv["response_received"] = True

    if stage:
        conv["outcome_stage"] = stage

    if time_to_response is not None:
        conv["time_to_response_days"] = time_to_response

    conv["response_type"] = outcome

    if note:
        conv["outcome_note"] = note

    if outcome == "rejected":
        if rejection_reason:
            conv["rejection_reason"] = rejection_reason
        if rejection_theme:
            conv["rejection_theme"] = rejection_theme
        if rejection_evidence:
            conv["rejection_evidence"] = rejection_evidence

    # Re-serialize with preserved order where possible (using safe_load then dump)
    content = yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)

    content = update_last_touched(content)
    atomic_write(filepath, content)

    # Update conversion log
    _update_conversion_log(
        entry_id,
        outcome,
        stage,
        time_to_response,
        rejection_reason=rejection_reason,
        rejection_theme=rejection_theme,
    )

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
    if outcome == "rejected" and rejection_reason:
        print(f"  Rejection reason: {rejection_reason}")
    if outcome == "rejected" and rejection_theme:
        print(f"  Rejection theme: {rejection_theme}")
    if time_to_response is not None:
        print(f"  Time to response: {time_to_response} days")

    # Auto-capture hypothesis if flags provided, else prompt
    if outcome in ("accepted", "rejected"):
        if _hypothesis_category and _hypothesis_text:
            try:
                from feedback_capture import add_hypothesis, capture_noninteractive
                record = capture_noninteractive(
                    entry_id=entry_id,
                    category=_hypothesis_category,
                    hypothesis=_hypothesis_text,
                    outcome=outcome,
                )
                add_hypothesis(record)
            except ImportError:
                print("\n  → feedback_capture not available for auto-hypothesis")
        else:
            print("\n  → Capture hypothesis inline:")
            print(f"    python scripts/check_outcomes.py --record {entry_id} --outcome {outcome} "
                  f"--category <cat> --hypothesis \"...\"")
            print(f"  → Or interactively: python scripts/feedback_capture.py --entry {entry_id} --outcome {outcome}")


def _update_conversion_log(
    entry_id: str,
    outcome: str,
    stage: str | None,
    time_to_response: int | None,
    *,
    rejection_reason: str | None = None,
    rejection_theme: str | None = None,
):
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
            if outcome == "rejected":
                if rejection_reason:
                    log_entry["rejection_reason"] = rejection_reason
                if rejection_theme:
                    log_entry["rejection_theme"] = rejection_theme
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

    rejection_reasons = {}
    for e in all_entries:
        if e.get("outcome") != "rejected":
            continue
        conversion = e.get("conversion", {})
        if not isinstance(conversion, dict):
            continue
        reason = conversion.get("rejection_reason") or "unknown"
        rejection_reasons[reason] = rejection_reasons.get(reason, 0) + 1
    if rejection_reasons:
        print("\nTop rejection reasons:")
        for reason, count in sorted(rejection_reasons.items(), key=lambda item: (-item[1], item[0]))[:5]:
            print(f"  {reason:<24s} {count}")


def extract_failure_themes(entries: list[dict], months: int = 1) -> dict:
    """Extract monthly failure themes from terminal non-accept outcomes."""
    horizon_days = max(1, months) * 30
    today = date.today()

    by_reason: dict[str, int] = {}
    by_theme: dict[str, int] = {}
    by_stage: dict[str, int] = {}
    by_track: dict[str, int] = {}
    total = 0

    for entry in entries:
        outcome = entry.get("outcome")
        if outcome not in {"rejected", "withdrawn", "expired"}:
            continue

        timeline = entry.get("timeline", {})
        conversion = entry.get("conversion", {})
        if not isinstance(timeline, dict):
            timeline = {}
        if not isinstance(conversion, dict):
            conversion = {}

        outcome_date = (
            parse_date(timeline.get("outcome_date"))
            or parse_date(conversion.get("response_date"))
            or parse_date(entry.get("last_touched"))
        )
        if outcome_date is None:
            continue
        if (today - outcome_date).days > horizon_days:
            continue

        total += 1
        reason = conversion.get("rejection_reason") or "unknown"
        theme = conversion.get("rejection_theme") or "unspecified"
        stage = conversion.get("outcome_stage") or "unknown"
        track = entry.get("track") or "unknown"

        by_reason[reason] = by_reason.get(reason, 0) + 1
        by_theme[theme] = by_theme.get(theme, 0) + 1
        by_stage[stage] = by_stage.get(stage, 0) + 1
        by_track[track] = by_track.get(track, 0) + 1

    return {
        "months": months,
        "total_failures": total,
        "by_reason": dict(sorted(by_reason.items(), key=lambda item: (-item[1], item[0]))),
        "by_theme": dict(sorted(by_theme.items(), key=lambda item: (-item[1], item[0]))),
        "by_stage": dict(sorted(by_stage.items(), key=lambda item: (-item[1], item[0]))),
        "by_track": dict(sorted(by_track.items(), key=lambda item: (-item[1], item[0]))),
    }


def show_failure_themes(submitted_entries: list[dict], months: int = 1) -> None:
    """Display failure themes for the specified monthly window."""
    closed_entries = load_entries(dirs=[PIPELINE_DIR_CLOSED], include_filepath=True)
    all_entries = submitted_entries + closed_entries
    themes = extract_failure_themes(all_entries, months=months)

    print(f"FAILURE THEMES — last {months} month(s)")
    print("=" * 70)
    print(f"Total failures analyzed: {themes['total_failures']}")
    if themes["total_failures"] == 0:
        print("No failure outcomes found in the selected window.")
        return

    def _print_block(title: str, payload: dict[str, int]) -> None:
        print(f"\n{title}:")
        for key, count in list(payload.items())[:8]:
            print(f"  {key:<28s} {count}")

    _print_block("Top reasons", themes["by_reason"])
    _print_block("Top themes", themes["by_theme"])
    _print_block("Top stages", themes["by_stage"])
    _print_block("By track", themes["by_track"])


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
    parser.add_argument(
        "--rejection-reason",
        choices=sorted(VALID_REJECTION_REASONS),
        help="Structured rejection reason (for --outcome rejected)",
    )
    parser.add_argument(
        "--rejection-theme",
        default="",
        help="Free-text failure theme (for --outcome rejected)",
    )
    parser.add_argument(
        "--rejection-evidence",
        default="",
        help="Evidence snippet supporting rejection taxonomy",
    )
    parser.add_argument("--category",
                        help="Hypothesis category (auto-capture with --record)")
    parser.add_argument("--hypothesis", metavar="TEXT",
                        help="Hypothesis text (auto-capture with --record)")
    parser.add_argument("--stale", action="store_true",
                        help="Show only stale entries (>14d, no response)")
    parser.add_argument("--summary", action="store_true",
                        help="Show outcome statistics summary")
    parser.add_argument("--failure-themes", action="store_true",
                        help="Show monthly failure themes from rejected/expired/withdrawn outcomes")
    parser.add_argument("--months", type=int, default=1,
                        help="Time window for --failure-themes (default: 1)")
    args = parser.parse_args()

    if args.record:
        if not args.outcome:
            parser.error("--outcome is required when using --record")
        if args.outcome != "rejected" and (args.rejection_reason or args.rejection_theme or args.rejection_evidence):
            parser.error("--rejection-* flags are only valid with --outcome rejected")
        # Validate hypothesis category if provided
        if args.category:
            try:
                from feedback_capture import VALID_CATEGORIES
                if args.category not in VALID_CATEGORIES:
                    parser.error(f"--category must be one of: {', '.join(VALID_CATEGORIES)}")
            except ImportError:
                pass
        record_outcome(
            args.record, args.outcome,
            stage=args.stage, note=args.note,
            rejection_reason=args.rejection_reason,
            rejection_theme=args.rejection_theme or None,
            rejection_evidence=args.rejection_evidence,
            _hypothesis_category=args.category,
            _hypothesis_text=args.hypothesis,
        )
        return

    entries = get_submitted_entries()

    if args.stale:
        show_stale(entries)
    elif args.failure_themes:
        show_failure_themes(entries, months=args.months)
    elif args.summary:
        show_summary(entries)
    else:
        show_awaiting(entries)


if __name__ == "__main__":
    main()
