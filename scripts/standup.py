#!/usr/bin/env python3
"""Daily standup — pipeline health, staleness detection, and execution protocol.

Single command to answer: "What is true right now?"

Usage:
    python scripts/standup.py                    # Full standup, 3hr budget
    python scripts/standup.py --hours 5          # Adjust time budget
    python scripts/standup.py --section health   # Single section
    python scripts/standup.py --touch artadia-nyc  # Mark entry as reviewed today
    python scripts/standup.py --log              # Append session to standup-log
"""

import argparse
import sys
from datetime import datetime, date
from pathlib import Path

import yaml

from pipeline_lib import (
    REPO_ROOT, PIPELINE_DIR_ACTIVE, PIPELINE_DIR_SUBMITTED, PIPELINE_DIR_CLOSED,
    SIGNALS_DIR, ALL_PIPELINE_DIRS, ACTIONABLE_STATUSES, EFFORT_MINUTES,
    load_entries, parse_date, get_effort, get_score, get_deadline, days_until,
)

STANDUP_LOG = SIGNALS_DIR / "standup-log.yaml"

STAGNATION_DAYS = 7
URGENCY_DAYS = 14
AT_RISK_DAYS = 3
REPLENISH_THRESHOLD = 5  # warn when fewer than this many actionable entries


# ---------------------------------------------------------------------------
# Section 1: Pipeline Health
# ---------------------------------------------------------------------------

def section_health(entries: list[dict]) -> dict:
    """Pipeline-wide counts and velocity."""
    today = date.today()
    total = len(entries)
    by_status: dict[str, int] = {}
    by_track: dict[str, int] = {}
    actionable = 0
    submitted_count = 0
    last_submit_date = None

    for e in entries:
        status = e.get("status", "unknown")
        track = e.get("track", "unknown")
        by_status[status] = by_status.get(status, 0) + 1
        by_track[track] = by_track.get(track, 0) + 1

        if status in ACTIONABLE_STATUSES:
            actionable += 1
        if status in ("submitted", "acknowledged", "interview"):
            submitted_count += 1

        tl = e.get("timeline", {})
        if isinstance(tl, dict) and tl.get("submitted"):
            sd = parse_date(tl["submitted"])
            if sd and (last_submit_date is None or sd > last_submit_date):
                last_submit_date = sd

    if last_submit_date:
        days_since = (today - last_submit_date).days
    else:
        days_since = None

    print("1. PIPELINE HEALTH")
    print(f"   Total entries: {total}")
    print(f"   Actionable (research/qualified/drafting/staged): {actionable}")
    print(f"   Submitted / awaiting response: {submitted_count}")
    if days_since is not None:
        print(f"   Days since last submission: {days_since}")
    else:
        print("   Days since last submission: NEVER (0 submissions)")
    print()

    status_order = ["research", "qualified", "drafting", "staged",
                    "submitted", "acknowledged", "interview", "outcome"]
    print("   Status breakdown:")
    for s in status_order:
        c = by_status.get(s, 0)
        if c > 0:
            bar = "#" * c
            print(f"     {s:15s} {c:3d}  {bar}")
    print()

    return {
        "total": total,
        "actionable": actionable,
        "submitted": submitted_count,
        "days_since_last_submission": days_since,
    }


# ---------------------------------------------------------------------------
# Section 2: Staleness Alerts
# ---------------------------------------------------------------------------

def section_stale(entries: list[dict]) -> dict:
    """Flag expired, at-risk, and stagnant entries."""
    today = date.today()
    expired = []
    at_risk = []
    stagnant = []

    for e in entries:
        entry_id = e.get("id", "?")
        status = e.get("status", "")
        dl_date, dl_type = get_deadline(e)

        # Expired: past deadline + not yet submitted
        if dl_date and days_until(dl_date) < 0 and status in ACTIONABLE_STATUSES:
            expired.append((entry_id, e.get("name", entry_id), dl_date, status))
            continue

        # At-risk: hard deadline <3 days away + still in qualified
        if (dl_date and dl_type == "hard" and 0 <= days_until(dl_date) <= AT_RISK_DAYS
                and status in ("research", "qualified")):
            at_risk.append((entry_id, e.get("name", entry_id), dl_date, status,
                            days_until(dl_date)))

        # Stagnant: no activity in >7 days + actionable
        if status in ACTIONABLE_STATUSES:
            lt = parse_date(e.get("last_touched"))
            if lt:
                stale_days = (today - lt).days
                if stale_days > STAGNATION_DAYS:
                    stagnant.append((entry_id, e.get("name", entry_id),
                                     lt, stale_days, status))

    print("2. STALENESS ALERTS")

    if expired:
        print(f"   EXPIRED ({len(expired)}) — deadline passed, never submitted:")
        for eid, name, dl, status in expired:
            print(f"     !!! {name} — deadline was {dl} ({abs(days_until(dl))}d ago) — {status}")
            print(f"         Action: archive with outcome=expired or withdraw")
    else:
        print("   EXPIRED: none")

    if at_risk:
        print(f"   AT-RISK ({len(at_risk)}) — hard deadline ≤{AT_RISK_DAYS}d + early status:")
        for eid, name, dl, status, d in at_risk:
            print(f"     !! {name} — {d}d left — still {status}")
            print(f"        Action: stage immediately or withdraw")
    else:
        print("   AT-RISK: none")

    if stagnant:
        stagnant.sort(key=lambda x: x[3], reverse=True)
        print(f"   STAGNANT ({len(stagnant)}) — no review in >{STAGNATION_DAYS} days:")
        for eid, name, lt, days, status in stagnant[:10]:
            print(f"     {name} — {days}d since last touch ({lt}) — {status}")
        if len(stagnant) > 10:
            print(f"     ... and {len(stagnant) - 10} more")
    else:
        print("   STAGNANT: none")

    print()
    return {
        "expired": len(expired),
        "at_risk": len(at_risk),
        "stagnant": len(stagnant),
    }


# ---------------------------------------------------------------------------
# Section 3: Today's Work Plan (wraps daily_batch logic)
# ---------------------------------------------------------------------------

def section_plan(entries: list[dict], hours: float) -> dict:
    """Deadline-driven + score-sorted work plan within a time budget."""
    today = date.today()
    budget = int(hours * 60)
    used = 0

    actionable = [e for e in entries if e.get("status") in ACTIONABLE_STATUSES]
    urgent = []
    scored = []

    for e in actionable:
        dl_date, dl_type = get_deadline(e)
        if dl_date:
            d = days_until(dl_date)
            if d < 0:
                continue  # expired, handled in staleness
            if d <= URGENCY_DAYS and dl_type == "hard":
                urgent.append((d, e))
                continue
        scored.append(e)

    urgent.sort(key=lambda x: x[0])
    scored.sort(key=lambda x: get_score(x), reverse=True)

    print(f"3. TODAY'S WORK PLAN ({hours:.1f}h budget, {budget} min)")
    planned = []

    if urgent:
        print("   URGENT (deadline ≤14d):")
        for d, e in urgent:
            effort = get_effort(e)
            est = EFFORT_MINUTES.get(effort, 90)
            name = e.get("name", e.get("id", "?"))
            status = e.get("status", "?")
            marker = "!!!" if d <= 3 else "! "
            fits = used + est <= budget
            tag = "" if fits else " [OVER BUDGET]"
            print(f"     {marker} {name} — {d}d — {status} — "
                  f"{effort} (~{est}min){tag}")
            if fits:
                used += est
                planned.append(e)

    if scored:
        print("   BY SCORE:")
        for e in scored:
            effort = get_effort(e)
            est = EFFORT_MINUTES.get(effort, 90)
            score = get_score(e)
            name = e.get("name", e.get("id", "?"))
            status = e.get("status", "?")
            fits = used + est <= budget
            tag = "" if fits else " [OVER BUDGET]"
            print(f"     [{score:.1f}] {name} — {status} — "
                  f"{effort} (~{est}min){tag}")
            if fits:
                used += est
                planned.append(e)

    remaining = budget - used
    print(f"   ---")
    print(f"   Planned: {len(planned)} entries | ~{used} min ({used / 60:.1f}h)")
    if remaining > 15:
        print(f"   Buffer: {remaining} min remaining")
    print()

    return {"planned": len(planned), "used_minutes": used}


# ---------------------------------------------------------------------------
# Section 4: Outreach Suggestions
# ---------------------------------------------------------------------------

OUTREACH_BY_STATUS = {
    "research": [
        "Search for past grantees/winners — calibrate your framing",
        "Check for upcoming info sessions or webinars",
        "Search LinkedIn for warm contacts at the org",
    ],
    "qualified": [
        "Visit the actual portal — note field names and character limits",
        "Read 2-3 past winners' statements for tone/length calibration",
        "Check if you know anyone connected to this org",
    ],
    "drafting": [
        "Request references/recommendations (2+ weeks before deadline)",
        "Verify portfolio URL and work samples are live and current",
        "Prepare a brief for any recommenders (opportunity + your angle)",
    ],
    "staged": [
        "Submit 24-48 hours before deadline (portals crash at deadlines)",
        "Do a final check of all links in your materials",
        "Prepare a thank-you draft for anyone who helped",
    ],
    "submitted": [
        "Send thank-you emails within 48 hours to anyone who helped",
        "Verify you received a confirmation email from the portal",
        "Note expected response timeline from the org's website/materials",
    ],
}


def section_outreach(entries: list[dict]):
    """Per-target outreach checklists based on status and deadline proximity."""
    today = date.today()
    actionable = [e for e in entries if e.get("status") in ACTIONABLE_STATUSES]

    # Sort by deadline urgency then score
    def sort_key(e):
        dl_date, _ = get_deadline(e)
        if dl_date:
            d = days_until(dl_date)
            if d >= 0:
                return (0, d)
        return (1, -get_score(e))

    actionable.sort(key=sort_key)

    print("4. OUTREACH SUGGESTIONS")

    if not actionable:
        print("   No actionable entries.")
        print()
        return

    shown = 0
    for e in actionable:
        if shown >= 5:
            remaining = len(actionable) - shown
            if remaining > 0:
                print(f"   ... {remaining} more entries (run full standup to see all)")
            break

        status = e.get("status", "")
        name = e.get("name", e.get("id", "?"))
        tips = OUTREACH_BY_STATUS.get(status, [])
        existing = e.get("outreach", [])
        done_types = set()
        if isinstance(existing, list):
            for o in existing:
                if isinstance(o, dict) and o.get("status") == "done":
                    done_types.add(o.get("type", ""))

        dl_date, _ = get_deadline(e)
        dl_str = ""
        if dl_date:
            d = days_until(dl_date)
            if d >= 0:
                dl_str = f" — {d}d to deadline"

        print(f"   {name} [{status}]{dl_str}:")
        for tip in tips:
            print(f"     - {tip}")
        if done_types:
            print(f"     (already done: {', '.join(sorted(done_types))})")
        shown += 1

    print()


# ---------------------------------------------------------------------------
# Section 5: Best Practices
# ---------------------------------------------------------------------------

PRACTICES_BY_CONTEXT = {
    "pre_deadline_week": [
        "Submit 24-48 hours before the deadline — portals crash at the wire",
        "Check that all linked work samples/portfolio URLs are live",
        "Do a final proofread pass on all materials",
    ],
    "no_submissions_ever": [
        "Zero submissions means zero signal. Ship something this week.",
        "Start with the highest-scored quick-effort entry to build momentum",
        "A submitted imperfect application beats a perfect never-submitted one",
    ],
    "high_stagnation": [
        "Touch at least 3 entries today — even if just re-reading notes",
        "If an entry has been stagnant >14 days, decide: advance or withdraw",
    ],
    "networking_cadence": [
        "Target 2-3 outreach messages per week (quality over quantity)",
        "Warm introductions convert 5-10x better than cold emails",
    ],
    "reference_requests": [
        "Ask recommenders 2+ weeks before deadline",
        "Provide them a brief: what the opportunity is + your angle + deadline",
    ],
}


def section_practices(entries: list[dict], stale_stats: dict):
    """Context-sensitive reminders from strategy docs."""
    today = date.today()
    tips_shown = set()

    print("5. BEST PRACTICES")

    # Check if any entry has deadline this week
    for e in entries:
        dl_date, dl_type = get_deadline(e)
        if dl_date and dl_type == "hard" and 0 <= days_until(dl_date) <= 7:
            if "pre_deadline_week" not in tips_shown:
                tips_shown.add("pre_deadline_week")
                for tip in PRACTICES_BY_CONTEXT["pre_deadline_week"]:
                    print(f"   - {tip}")

    # No submissions ever
    has_submission = any(
        e.get("status") in ("submitted", "acknowledged", "interview", "outcome")
        for e in entries
    )
    if not has_submission and "no_submissions_ever" not in tips_shown:
        tips_shown.add("no_submissions_ever")
        for tip in PRACTICES_BY_CONTEXT["no_submissions_ever"]:
            print(f"   - {tip}")

    # High stagnation
    if stale_stats.get("stagnant", 0) > 5 and "high_stagnation" not in tips_shown:
        tips_shown.add("high_stagnation")
        for tip in PRACTICES_BY_CONTEXT["high_stagnation"]:
            print(f"   - {tip}")

    # Always show networking cadence
    if "networking_cadence" not in tips_shown:
        tips_shown.add("networking_cadence")
        for tip in PRACTICES_BY_CONTEXT["networking_cadence"]:
            print(f"   - {tip}")

    if not tips_shown:
        print("   No context-specific tips today.")

    print()


# ---------------------------------------------------------------------------
# Section 6: Pipeline Replenishment
# ---------------------------------------------------------------------------

def section_replenish(entries: list[dict]):
    """Alert when actionable count drops below threshold."""
    actionable = [e for e in entries if e.get("status") in ACTIONABLE_STATUSES]
    # Exclude expired
    today = date.today()
    live = []
    for e in actionable:
        dl_date, _ = get_deadline(e)
        if dl_date and days_until(dl_date) < 0:
            continue
        live.append(e)

    # Count by track
    by_track: dict[str, int] = {}
    for e in live:
        track = e.get("track", "unknown")
        by_track[track] = by_track.get(track, 0) + 1

    print("6. PIPELINE REPLENISHMENT")
    print(f"   Live actionable entries: {len(live)}")

    if len(live) < REPLENISH_THRESHOLD:
        print(f"   !! Below threshold ({REPLENISH_THRESHOLD}). Research new targets.")
        print("   Check targets/ directory for pre-researched opportunities.")
    else:
        print(f"   OK — above minimum threshold ({REPLENISH_THRESHOLD})")

    # Track diversity check
    if by_track:
        print("   By track:")
        for track, count in sorted(by_track.items(), key=lambda x: -x[1]):
            print(f"     {track}: {count}")

    # Check for track gaps
    desired_tracks = {"grant", "residency", "job", "fellowship", "writing"}
    missing = desired_tracks - set(by_track.keys())
    if missing:
        print(f"   Gaps: no live entries in {', '.join(sorted(missing))}")

    print()


# ---------------------------------------------------------------------------
# Section 7: Session Log
# ---------------------------------------------------------------------------

def section_log(health_stats: dict, stale_stats: dict, plan_stats: dict):
    """Append daily record to signals/standup-log.yaml."""
    today = date.today().isoformat()

    record = {
        "date": today,
        "total": health_stats.get("total", 0),
        "actionable": health_stats.get("actionable", 0),
        "submitted": health_stats.get("submitted", 0),
        "days_since_last_submission": health_stats.get("days_since_last_submission"),
        "expired": stale_stats.get("expired", 0),
        "at_risk": stale_stats.get("at_risk", 0),
        "stagnant": stale_stats.get("stagnant", 0),
        "planned_today": plan_stats.get("planned", 0),
        "planned_minutes": plan_stats.get("used_minutes", 0),
    }

    # Load existing log
    if STANDUP_LOG.exists():
        with open(STANDUP_LOG) as f:
            log_data = yaml.safe_load(f) or {}
    else:
        log_data = {}

    sessions = log_data.get("sessions", [])
    if not isinstance(sessions, list):
        sessions = []

    # Replace today's entry if already logged
    sessions = [s for s in sessions if s.get("date") != today]
    sessions.append(record)
    log_data["sessions"] = sessions

    STANDUP_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(STANDUP_LOG, "w") as f:
        yaml.dump(log_data, f, default_flow_style=False, sort_keys=False)

    print("7. SESSION LOG")
    print(f"   Logged to {STANDUP_LOG.relative_to(REPO_ROOT)}")
    print()


# ---------------------------------------------------------------------------
# Touch command
# ---------------------------------------------------------------------------

def touch_entry(entry_id: str):
    """Update last_touched on a pipeline entry to today."""
    today = date.today().isoformat()

    for pipeline_dir in ALL_PIPELINE_DIRS:
        filepath = pipeline_dir / f"{entry_id}.yaml"
        if filepath.exists():
            with open(filepath) as f:
                data = yaml.safe_load(f)
            if isinstance(data, dict):
                data["last_touched"] = today
                with open(filepath, "w") as f:
                    yaml.dump(data, f, default_flow_style=False, sort_keys=False)
                print(f"Touched: {entry_id} — last_touched set to {today}")
                return

    print(f"Entry not found: {entry_id}")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

SECTIONS = {
    "health": "Pipeline health counts and velocity",
    "stale": "Staleness alerts (expired, at-risk, stagnant)",
    "plan": "Today's work plan",
    "outreach": "Outreach suggestions per target",
    "practices": "Context-sensitive best practice reminders",
    "replenish": "Pipeline replenishment alerts",
    "log": "Append session record to standup-log.yaml",
}


def run_standup(hours: float, section: str | None, do_log: bool):
    """Run the full standup or a single section."""
    entries = load_entries()
    if not entries:
        print("No pipeline entries found.")
        sys.exit(1)

    today = date.today()
    print("=" * 60)
    print(f"DAILY STANDUP — {today.strftime('%A, %B %d, %Y')}")
    print("=" * 60)
    print()

    health_stats = {}
    stale_stats = {}
    plan_stats = {}

    if section is None or section == "health":
        health_stats = section_health(entries)
    if section is None or section == "stale":
        stale_stats = section_stale(entries)
    if section is None or section == "plan":
        plan_stats = section_plan(entries, hours)
    if section is None or section == "outreach":
        section_outreach(entries)
    if section is None or section == "practices":
        section_practices(entries, stale_stats)
    if section is None or section == "replenish":
        section_replenish(entries)
    if do_log or section == "log":
        # Need all stats for logging
        if not health_stats:
            health_stats = section_health(entries)
        if not stale_stats:
            stale_stats = section_stale(entries)
        if not plan_stats:
            plan_stats = section_plan(entries, hours)
        section_log(health_stats, stale_stats, plan_stats)


# ---------------------------------------------------------------------------
# Triage mode
# ---------------------------------------------------------------------------

NEXT_STATUS = {
    "research": "qualified",
    "qualified": "drafting",
    "drafting": "staged",
    "staged": "submitted",
}


def run_triage():
    """Interactive walk-through of stagnant and actionable entries.

    For each entry, prompts: advance / withdraw / defer / skip.
    """
    entries = load_entries(include_filepath=True)
    today = date.today()

    # Find stagnant + actionable entries, sorted by staleness
    candidates = []
    for e in entries:
        status = e.get("status", "")
        if status not in ACTIONABLE_STATUSES:
            continue
        lt = parse_date(e.get("last_touched"))
        stale_days = (today - lt).days if lt else 999
        candidates.append((stale_days, e))

    candidates.sort(key=lambda x: -x[0])  # most stale first

    if not candidates:
        print("No actionable entries to triage.")
        return

    print("=" * 60)
    print(f"TRIAGE MODE — {len(candidates)} actionable entries")
    print("=" * 60)
    print("For each entry: [a]dvance  [w]ithdraw  [d]efer  [s]kip  [q]uit\n")

    advanced = 0
    withdrawn = 0
    deferred = 0

    for stale_days, entry in candidates:
        entry_id = entry.get("id", "?")
        name = entry.get("name", entry_id)
        status = entry.get("status", "?")
        score = get_score(entry)
        dl_date, dl_type = get_deadline(entry)

        dl_str = ""
        if dl_date:
            d = days_until(dl_date)
            if d < 0:
                dl_str = f" | EXPIRED {abs(d)}d ago"
            else:
                dl_str = f" | {d}d to deadline"
        elif dl_type in ("rolling", "tba"):
            dl_str = f" | {dl_type}"

        stale_str = f"{stale_days}d stale" if stale_days < 999 else "never touched"

        print(f"  {name}")
        print(f"  Status: {status} | Score: {score:.1f}{dl_str} | {stale_str}")

        next_status = NEXT_STATUS.get(status)
        if next_status:
            print(f"  [a] Advance to '{next_status}' + touch")
        print(f"  [w] Withdraw  [d] Defer (touch only)  [s] Skip  [q] Quit")

        try:
            choice = input("  > ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n  Quitting triage.")
            break

        filepath = entry.get("_filepath")

        if choice == "q":
            break
        elif choice == "a" and next_status and filepath:
            _triage_update_entry(filepath, entry_id, status=next_status, touch=True)
            advanced += 1
            print(f"  -> Advanced to {next_status}\n")
        elif choice == "w" and filepath:
            reason = ""
            try:
                reason = input("  Reason (optional): ").strip()
            except (EOFError, KeyboardInterrupt):
                pass
            _triage_update_entry(filepath, entry_id, withdraw=True, reason=reason, touch=True)
            withdrawn += 1
            print(f"  -> Withdrawn\n")
        elif choice == "d" and filepath:
            _triage_update_entry(filepath, entry_id, touch=True)
            deferred += 1
            print(f"  -> Deferred (touched)\n")
        else:
            print(f"  -> Skipped\n")

    print(f"Triage complete: {advanced} advanced, {withdrawn} withdrawn, {deferred} deferred")


def _triage_update_entry(
    filepath: Path,
    entry_id: str,
    status: str | None = None,
    withdraw: bool = False,
    reason: str = "",
    touch: bool = False,
):
    """Update an entry file during triage."""
    import re

    with open(filepath) as f:
        content = f.read()

    if touch:
        today_str = date.today().isoformat()
        if re.search(r"^last_touched:", content, re.MULTILINE):
            content = re.sub(
                r"^(last_touched:\s+).*$",
                rf'\1"{today_str}"',
                content,
                count=1,
                flags=re.MULTILINE,
            )
        else:
            content = content.rstrip() + f'\nlast_touched: "{today_str}"\n'

    if status and not withdraw:
        content = re.sub(
            r"^(status:\s+).*$",
            rf"\1{status}",
            content,
            count=1,
            flags=re.MULTILINE,
        )

    if withdraw:
        content = re.sub(
            r"^(status:\s+).*$",
            r"\1outcome",
            content,
            count=1,
            flags=re.MULTILINE,
        )
        content = re.sub(
            r"^(outcome:\s+).*$",
            r"\1withdrawn",
            content,
            count=1,
            flags=re.MULTILINE,
        )
        if reason:
            # Add withdrawal_reason if not present
            if "withdrawal_reason:" not in content:
                content = content.rstrip() + f"\nwithdrawal_reason:\n  reason: strategic_shift\n  detail: \"{reason}\"\n  date: \"{date.today().isoformat()}\"\n  reopen: false\n"

    with open(filepath, "w") as f:
        f.write(content)


def main():
    parser = argparse.ArgumentParser(
        description="Daily standup — pipeline health, staleness detection, execution protocol"
    )
    parser.add_argument("--hours", type=float, default=3.0,
                        help="Available hours for today's session (default: 3)")
    parser.add_argument("--section", choices=list(SECTIONS.keys()),
                        help="Run a single section only")
    parser.add_argument("--touch", metavar="ENTRY_ID",
                        help="Mark an entry as reviewed today (sets last_touched)")
    parser.add_argument("--log", action="store_true",
                        help="Append session record to standup-log.yaml")
    parser.add_argument("--triage", action="store_true",
                        help="Interactive triage: walk through stagnant entries one-by-one")
    args = parser.parse_args()

    if args.touch:
        touch_entry(args.touch)
        return

    if args.triage:
        run_triage()
        return

    run_standup(args.hours, args.section, args.log)


if __name__ == "__main__":
    main()
