#!/usr/bin/env python3
"""Calendar export — generate iCal (.ics) files from pipeline deadlines.

Pure stdlib iCal generation (VCALENDAR/VEVENT/VALARM text format).
Exports application deadlines with 7-day and 1-day alarms, follow-up dates,
and scheduled agent runs.

Usage:
    python scripts/calendar_export.py                          # Print to stdout
    python scripts/calendar_export.py --output ~/Calendar/pipeline.ics
    python scripts/calendar_export.py --follow-ups             # Include follow-up dates
    python scripts/calendar_export.py --json                   # JSON event list
"""

import argparse
import hashlib
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import (
    get_deadline,
    get_score,
    load_entries,
    parse_date,
)


def _uid(seed: str) -> str:
    """Generate a deterministic UID for an iCal event."""
    return hashlib.sha256(seed.encode()).hexdigest()[:16] + "@pipeline"


def generate_vevent(
    uid: str,
    summary: str,
    dtstart: date,
    description: str = "",
    alarms: list[int] | None = None,
) -> str:
    """Generate a VEVENT string in iCal format.

    Args:
        uid: Unique event identifier
        summary: Event title
        dtstart: Event date
        description: Event description
        alarms: List of days-before to trigger VALARM (default: [7, 1])
    """
    if alarms is None:
        alarms = [7, 1]

    dt_str = dtstart.strftime("%Y%m%d")
    lines = [
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTART;VALUE=DATE:{dt_str}",
        f"SUMMARY:{summary}",
    ]
    if description:
        # Escape newlines and commas per iCal spec
        desc = description.replace("\\", "\\\\").replace(",", "\\,").replace("\n", "\\n")
        lines.append(f"DESCRIPTION:{desc}")

    for days_before in alarms:
        lines.extend([
            "BEGIN:VALARM",
            f"TRIGGER:-P{days_before}D",
            "ACTION:DISPLAY",
            f"DESCRIPTION:Pipeline deadline in {days_before} day(s): {summary}",
            "END:VALARM",
        ])

    lines.append("END:VEVENT")
    return "\n".join(lines)


def generate_calendar(
    entries: list[dict],
    include_followups: bool = False,
) -> str:
    """Generate a full iCal calendar from pipeline entries.

    Args:
        entries: Pipeline entries with deadlines
        include_followups: Also include follow-up protocol dates
    """
    events = []

    for entry in entries:
        eid = entry.get("id", "unknown")
        name = entry.get("name", eid)
        status = entry.get("status", "")
        score = get_score(entry)

        # Deadline events
        deadline_date, _ = get_deadline(entry)
        if deadline_date and isinstance(deadline_date, date):
            score_str = f" [{score:.1f}]" if score else ""
            events.append(generate_vevent(
                uid=_uid(f"deadline-{eid}"),
                summary=f"DEADLINE: {name}{score_str}",
                dtstart=deadline_date,
                description=f"Pipeline entry: {eid}\\nStatus: {status}\\nScore: {score or 'N/A'}",
                alarms=[7, 1],
            ))

        # Follow-up events
        if include_followups:
            follow_up = entry.get("follow_up", {})
            if isinstance(follow_up, dict):
                for field in ("connect_date", "dm_date", "final_date"):
                    raw = follow_up.get(field)
                    if raw:
                        dt = parse_date(raw)
                        if dt and dt >= date.today():
                            label = field.replace("_date", "").upper()
                            events.append(generate_vevent(
                                uid=_uid(f"followup-{field}-{eid}"),
                                summary=f"FOLLOW-UP {label}: {name}",
                                dtstart=dt,
                                description=f"Follow-up action for {eid}",
                                alarms=[1],
                            ))

    cal_lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Application Pipeline//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Pipeline Deadlines",
    ]
    cal_lines.extend(events)
    cal_lines.append("END:VCALENDAR")
    return "\n".join(cal_lines)


def generate_event_list(entries: list[dict], include_followups: bool = False) -> list[dict]:
    """Generate a list of event dicts for JSON output."""
    events = []
    for entry in entries:
        eid = entry.get("id", "unknown")
        name = entry.get("name", eid)
        score = get_score(entry)

        deadline_date, _ = get_deadline(entry)
        if deadline_date and isinstance(deadline_date, date):
            events.append({
                "type": "deadline",
                "id": eid,
                "name": name,
                "date": str(deadline_date),
                "score": score,
                "status": entry.get("status", ""),
            })

        if include_followups:
            follow_up = entry.get("follow_up", {})
            if isinstance(follow_up, dict):
                for field in ("connect_date", "dm_date", "final_date"):
                    raw = follow_up.get(field)
                    if raw:
                        dt = parse_date(raw)
                        if dt and dt >= date.today():
                            events.append({
                                "type": f"followup_{field.replace('_date', '')}",
                                "id": eid,
                                "name": name,
                                "date": str(dt),
                            })

    events.sort(key=lambda e: e.get("date", ""))
    return events


def main():
    parser = argparse.ArgumentParser(description="Export pipeline deadlines to iCal format")
    parser.add_argument("--output", "-o", metavar="PATH", help="Write .ics file to path")
    parser.add_argument("--follow-ups", action="store_true", help="Include follow-up protocol dates")
    parser.add_argument("--json", action="store_true", help="Output JSON event list instead of iCal")
    args = parser.parse_args()

    entries = load_entries()

    if args.json:
        events = generate_event_list(entries, include_followups=args.follow_ups)
        print(json.dumps(events, indent=2, default=str))
        return

    ical = generate_calendar(entries, include_followups=args.follow_ups)

    if args.output:
        output_path = Path(args.output).expanduser()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(ical)
        print(f"Calendar exported to {output_path}")
    else:
        print(ical)


if __name__ == "__main__":
    main()
