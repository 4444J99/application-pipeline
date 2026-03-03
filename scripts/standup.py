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
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import yaml
from pipeline_lib import (
    ACTIONABLE_STATUSES,
    ALL_PIPELINE_DIRS,
    EFFORT_MINUTES,
    PIPELINE_DIR_RESEARCH_POOL,
    REPO_ROOT,
    SIGNALS_DIR,
    VALID_TRANSITIONS,
    compute_freshness_score,
    days_until,
    get_deadline,
    get_effort,
    get_freshness_tier,
    get_posting_age_hours,
    get_score,
    load_entries,
    parse_date,
    update_yaml_field,
)
from pipeline_lib import (
    update_last_touched as update_last_touched_content,
)

STANDUP_LOG = SIGNALS_DIR / "standup-log.yaml"
_INTEL_FILE = REPO_ROOT / "strategy" / "market-intelligence-2026.json"

# --- Market intel loader ---
_MARKET_INTEL: dict | None = None


def _load_market_intel() -> dict:
    global _MARKET_INTEL
    if _MARKET_INTEL is not None:
        return _MARKET_INTEL
    if _INTEL_FILE.exists():
        try:
            with open(_INTEL_FILE) as f:
                _MARKET_INTEL = json.load(f)
        except Exception:
            _MARKET_INTEL = {}
    else:
        _MARKET_INTEL = {}
    return _MARKET_INTEL


def _get_stale_threshold(key: str, default: int) -> int:
    """Load a stale threshold from market intel JSON, fallback to hardcoded default."""
    intel = _load_market_intel()
    return intel.get("stale_thresholds_days", {}).get(key, default)


# Load thresholds from market intel (with hardcoded fallbacks)
STAGNATION_DAYS = _get_stale_threshold("entry_stale", 7)
URGENCY_DAYS = 14
AT_RISK_DAYS = 3
REPLENISH_THRESHOLD = 5  # warn when fewer than this many actionable entries
EXECUTION_STALE_STAGED_DAYS = 3  # 72h
TARGET_STAGED_SUBMIT_CONVERSION = 0.70
AGENT_ACTIONS_LOG = SIGNALS_DIR / "agent-actions.yaml"


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

    status_order = ["research", "qualified", "drafting", "staged", "deferred",
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

        # At-risk: hard/fixed deadline <3 days away + still in qualified
        if (dl_date and dl_type in ("hard", "fixed") and 0 <= days_until(dl_date) <= AT_RISK_DAYS
                and status in ("research", "qualified")):
            at_risk.append((entry_id, e.get("name", entry_id), dl_date, status,
                            days_until(dl_date)))
            continue

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
            print("         Action: archive with outcome=expired or withdraw")
    else:
        print("   EXPIRED: none")

    if at_risk:
        print(f"   AT-RISK ({len(at_risk)}) — hard deadline ≤{AT_RISK_DAYS}d + early status:")
        for eid, name, dl, status, d in at_risk:
            print(f"     !! {name} — {d}d left — still {status}")
            print("        Action: stage immediately or withdraw")
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
# Section 2b: Execution Gap Snapshot
# ---------------------------------------------------------------------------

def _entry_has_portal_fields(entry: dict) -> bool:
    """Return True when portal_fields.fields exists and is non-empty."""
    portal_fields = entry.get("portal_fields")
    return (
        isinstance(portal_fields, dict)
        and isinstance(portal_fields.get("fields"), list)
        and len(portal_fields["fields"]) > 0
    )


def _compute_staged_submit_conversion(entries: list[dict]) -> tuple[int, int, float]:
    """Compute operational staged->submitted conversion from current pipeline state."""
    in_funnel = {"staged", "submitted", "acknowledged", "interview", "outcome"}
    submitted_or_beyond = {"submitted", "acknowledged", "interview", "outcome"}

    denominator = sum(1 for e in entries if e.get("status") in in_funnel)
    numerator = sum(1 for e in entries if e.get("status") in submitted_or_beyond)

    rate = (numerator / denominator) if denominator else 0.0
    return numerator, denominator, rate


def _load_recent_agent_runs(days: int = 7) -> list[dict]:
    """Load recent agent run records from signals/agent-actions.yaml."""
    if not AGENT_ACTIONS_LOG.exists():
        return []

    try:
        with open(AGENT_ACTIONS_LOG) as f:
            data = yaml.safe_load(f) or {}
    except Exception:
        return []

    runs = data.get("runs", [])
    if not isinstance(runs, list):
        return []

    cutoff = datetime.now() - timedelta(days=days)
    recent: list[dict] = []
    for run in runs:
        if not isinstance(run, dict):
            continue
        ts = run.get("timestamp")
        if not ts:
            continue
        try:
            run_dt = datetime.fromisoformat(str(ts))
        except ValueError:
            continue
        if run_dt >= cutoff:
            recent.append(run)

    recent.sort(key=lambda x: str(x.get("timestamp")), reverse=True)
    return recent


def section_execution_gap(entries: list[dict]) -> dict:
    """Highlight operational bottlenecks that block staged->submitted flow."""
    today = date.today()
    staged_entries = [e for e in entries if e.get("status") == "staged"]

    stale_staged = []
    missing_portal = []

    for e in staged_entries:
        lt = parse_date(e.get("last_touched"))
        stale_days = (today - lt).days if lt else 999
        if stale_days > EXECUTION_STALE_STAGED_DAYS:
            stale_staged.append((stale_days, e))
        if not _entry_has_portal_fields(e):
            missing_portal.append(e)

    stale_staged.sort(key=lambda x: x[0], reverse=True)
    numerator, denominator, conversion_rate = _compute_staged_submit_conversion(entries)

    print("2b. EXECUTION GAP SNAPSHOT")
    print(f"   Staged entries: {len(staged_entries)}")
    print(
        f"   Stale staged >{EXECUTION_STALE_STAGED_DAYS * 24}h: {len(stale_staged)}"
    )
    print(f"   Staged missing portal_fields: {len(missing_portal)}")
    print(
        f"   Staged->Submitted: {conversion_rate * 100:.1f}% "
        f"({numerator}/{denominator}, target {TARGET_STAGED_SUBMIT_CONVERSION * 100:.0f}%)"
    )

    if conversion_rate < TARGET_STAGED_SUBMIT_CONVERSION:
        print("   !! Bottleneck: submission velocity below target")

    if stale_staged:
        print("   Top stale staged entries:")
        for stale_days, entry in stale_staged[:10]:
            name = entry.get("name", entry.get("id", "?"))
            score = get_score(entry)
            print(f"     - {name} — {stale_days}d stale — fit {score:.1f}")

    if missing_portal:
        print("   Staged entries missing portal_fields:")
        for entry in missing_portal[:10]:
            name = entry.get("name", entry.get("id", "?"))
            print(f"     - {name}")

    recent_runs = _load_recent_agent_runs(days=7)
    execute_runs = [r for r in recent_runs if r.get("mode") == "execute"]
    executed_actions = sum(int(r.get("executed", 0)) for r in execute_runs)
    print(
        f"   Autonomous runs (7d): {len(execute_runs)} execute runs, "
        f"{executed_actions} actions executed"
    )
    if not execute_runs:
        print("   Action: install/load launchd agents or run `python scripts/agent.py --execute --yes`")

    print()
    return {
        "staged": len(staged_entries),
        "stale_staged": len(stale_staged),
        "missing_portal": len(missing_portal),
        "conversion_rate": round(conversion_rate, 3),
        "autonomous_runs": len(execute_runs),
    }


# ---------------------------------------------------------------------------
# Section 3: Today's Work Plan (wraps daily_batch logic)
# ---------------------------------------------------------------------------

def section_plan(entries: list[dict], hours: float) -> dict:
    """Deadline-driven + score-sorted work plan within a time budget."""
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
            if d <= URGENCY_DAYS and dl_type in ("hard", "fixed"):
                urgent.append((d, e))
                continue
        scored.append(e)

    urgent.sort(key=lambda x: x[0])
    # Rank by score, weighting job entries by posting freshness so hot jobs
    # surface above warm ones even at equal score.
    def _plan_sort_key(e):
        base = get_score(e)
        if e.get("track") == "job":
            return base * compute_freshness_score(e)
        return base

    scored.sort(key=_plan_sort_key, reverse=True)

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
        print("   BY SCORE (jobs weighted by freshness):")
        for e in scored:
            effort = get_effort(e)
            est = EFFORT_MINUTES.get(effort, 90)
            name = e.get("name", e.get("id", "?"))
            status = e.get("status", "?")
            fits = used + est <= budget
            tag = "" if fits else " [OVER BUDGET]"
            effective = _plan_sort_key(e)
            freshness_suffix = ""
            if e.get("track") == "job":
                badge = _freshness_badge(e)
                if badge:
                    freshness_suffix = f" {badge}"
            print(f"     [{effective:.1f}] {name} — {status} — "
                  f"{effort} (~{est}min){tag}{freshness_suffix}")
            if fits:
                used += est
                planned.append(e)

    remaining = budget - used
    print("   ---")
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
    tips_shown = set()

    print("5. BEST PRACTICES")

    # Check if any entry has deadline this week
    for e in entries:
        dl_date, dl_type = get_deadline(e)
        if dl_date and dl_type in ("hard", "fixed") and 0 <= days_until(dl_date) <= 7:
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

    # Show research pool size
    pool_entries = load_entries(dirs=[PIPELINE_DIR_RESEARCH_POOL])
    if pool_entries:
        pool_high = sum(1 for e in pool_entries if get_score(e) >= 7.0)
        print(f"   Research pool: {len(pool_entries)} entries ({pool_high} scoring >= 7.0)")
        if len(live) < REPLENISH_THRESHOLD and pool_high > 0:
            print("   Tip: run `python scripts/score.py --auto-qualify --dry-run` to promote top entries")

    print()


# ---------------------------------------------------------------------------
# Section 7: Deferred Entries
# ---------------------------------------------------------------------------

def section_deferred(entries: list[dict]):
    """Show entries with status=deferred and their resume dates."""
    deferred = [e for e in entries if e.get("status") == "deferred"]

    print("7. DEFERRED ENTRIES")

    if not deferred:
        print("   No deferred entries.")
        print()
        return

    today = date.today()
    print(f"   {len(deferred)} entry(ies) deferred (blocked by external factors):")
    for e in deferred:
        name = e.get("name", e.get("id", "?"))
        deferral = e.get("deferral", {})
        reason = deferral.get("reason", "unknown") if isinstance(deferral, dict) else "unknown"
        resume_date_str = deferral.get("resume_date") if isinstance(deferral, dict) else None
        note = deferral.get("note", "") if isinstance(deferral, dict) else ""

        resume_info = ""
        if resume_date_str:
            rd = parse_date(resume_date_str)
            if rd:
                d = (rd - today).days
                if d > 0:
                    resume_info = f" — resumes in {d}d ({resume_date_str})"
                elif d == 0:
                    resume_info = f" — RESUME TODAY ({resume_date_str})"
                else:
                    resume_info = f" — PAST RESUME DATE ({resume_date_str}, {abs(d)}d ago)"

        print(f"     {name} [{reason}]{resume_info}")
        if note:
            print(f"       {note}")

    print()


# ---------------------------------------------------------------------------
# Section 7b: Signal Freshness
# ---------------------------------------------------------------------------

def section_signal_freshness():
    """Check staleness of signal files and pipeline backups."""
    import time

    print("   SIGNAL FRESHNESS:")
    signals = {
        SIGNALS_DIR / "conversion-log.yaml": ("conversion-log", 1),
        SIGNALS_DIR / "hypotheses.yaml": ("hypotheses", 3),
        SIGNALS_DIR / "standup-log.yaml": ("standup-log", 2),
    }
    # Check backup freshness across both repo root and backups/.
    backup_candidates = list(REPO_ROOT.glob("pipeline-backup-*.tar.gz"))
    backup_dir = REPO_ROOT / "backups"
    if backup_dir.exists():
        backup_candidates.extend(backup_dir.glob("pipeline-backup-*.tar.gz"))
    latest_backup = max(backup_candidates, key=lambda p: p.stat().st_mtime) if backup_candidates else None

    stale_count = 0
    for filepath, (label, max_days) in signals.items():
        if not filepath.exists():
            print(f"     {label}: MISSING")
            stale_count += 1
            continue
        mtime = filepath.stat().st_mtime
        age_days = (time.time() - mtime) / 86400
        if age_days > max_days:
            print(f"     {label}: STALE ({age_days:.1f}d old, max {max_days}d)")
            stale_count += 1
        else:
            print(f"     {label}: OK ({age_days:.1f}d old)")

    if latest_backup:
        backup_age = (time.time() - latest_backup.stat().st_mtime) / 86400
        if backup_age > 7:
            print(f"     backup: STALE ({backup_age:.0f}d old, run backup_pipeline.py)")
            stale_count += 1
        else:
            print(f"     backup: OK ({backup_age:.0f}d old)")
    else:
        print("     backup: NONE (run backup_pipeline.py)")
        stale_count += 1

    if stale_count == 0:
        print("     All signals fresh.")
    print()


# ---------------------------------------------------------------------------
# Section 8: Follow-Up Dashboard
# ---------------------------------------------------------------------------

def section_followup(entries: list[dict]):
    """Show follow-up dashboard: due/overdue actions for submitted entries."""
    submitted = [e for e in entries if e.get("status") in ("submitted", "acknowledged")]

    print("8. FOLLOW-UP DASHBOARD")

    if not submitted:
        print("   No submitted entries to follow up on.")
        print()
        return

    today = date.today()
    due_entries = []
    overdue_entries = []
    upcoming_entries = []

    for e in submitted:
        entry_id = e.get("id", "?")
        name = e.get("name", entry_id)
        target = e.get("target", {})
        org = target.get("organization", "?") if isinstance(target, dict) else "?"

        tl = e.get("timeline", {})
        sub_date = parse_date(tl.get("submitted")) if isinstance(tl, dict) else None
        if not sub_date:
            continue

        days_since = (today - sub_date).days
        existing = e.get("follow_up", []) or []
        existing_types = {fu.get("type") for fu in existing if isinstance(fu, dict)}

        # Follow-up protocol: connect (day 1-2), dm (day 7-10), check_in (day 14-21)
        protocol = [
            {"day_range": (1, 2), "type": "connect", "action": "Connect on LinkedIn"},
            {"day_range": (7, 10), "type": "dm", "action": "First follow-up DM/email"},
            {"day_range": (14, 21), "type": "check_in", "action": "Final follow-up"},
        ]

        for step in protocol:
            if step["type"] in existing_types:
                continue
            low, high = step["day_range"]
            if days_since > high:
                overdue_entries.append({
                    "id": entry_id, "name": name, "org": org,
                    "days": days_since, "action": step["action"],
                    "window": f"Day {low}-{high}",
                })
            elif low <= days_since <= high:
                due_entries.append({
                    "id": entry_id, "name": name, "org": org,
                    "days": days_since, "action": step["action"],
                    "window": f"Day {low}-{high}",
                })
            else:
                upcoming_entries.append({
                    "id": entry_id, "name": name, "org": org,
                    "days": days_since, "due_in": low - days_since,
                    "action": step["action"],
                })

    if overdue_entries:
        print(f"   OVERDUE ({len(overdue_entries)}):")
        for item in overdue_entries[:5]:
            print(f"     !!! {item['org']} — {item['name']}")
            print(f"         Day {item['days']} — {item['action']} ({item['window']})")
        if len(overdue_entries) > 5:
            print(f"     ... and {len(overdue_entries) - 5} more")

    if due_entries:
        print(f"   DUE TODAY ({len(due_entries)}):")
        for item in due_entries[:5]:
            print(f"     >> {item['org']} — {item['name']}")
            print(f"        Day {item['days']} — {item['action']}")
        if len(due_entries) > 5:
            print(f"     ... and {len(due_entries) - 5} more")

    if not overdue_entries and not due_entries:
        if upcoming_entries:
            upcoming_entries.sort(key=lambda x: x["due_in"])
            print("   No actions due today. Next up:")
            for item in upcoming_entries[:3]:
                print(f"     in {item['due_in']}d — {item['org']} — {item['action']}")
        else:
            print("   All follow-up protocols complete for current submissions.")

    # Summary line
    total_submitted = len(submitted)
    with_followups = sum(1 for e in submitted if e.get("follow_up"))
    print(f"\n   Submitted: {total_submitted} | With follow-ups: {with_followups} | "
          f"Overdue: {len(overdue_entries)} | Due: {len(due_entries)}")
    print()


# ---------------------------------------------------------------------------
# Section 9: Session Log
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

    print("9. SESSION LOG")
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
            content = filepath.read_text()
            content = update_last_touched_content(content)
            filepath.write_text(content)
            print(f"Touched: {entry_id} — last_touched set to {today}")
            return

    print(f"Entry not found: {entry_id}")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

SECTIONS = {
    "health": "Pipeline health counts and velocity",
    "wins": "Recent milestones and achievements",
    "stale": "Staleness alerts (expired, at-risk, stagnant)",
    "execution": "Execution bottlenecks (stale staged, portal wiring, conversion)",
    "plan": "Today's work plan",
    "outreach": "Outreach suggestions per target",
    "practices": "Context-sensitive best practice reminders",
    "replenish": "Pipeline replenishment alerts",
    "deferred": "Deferred entries awaiting external unblock",
    "followup": "Follow-up dashboard for submitted entries",
    "readiness": "Staged entry readiness scores and blockers",
    "log": "Append session record to standup-log.yaml",
    "jobs": "Job pipeline status",
    "jobfreshness": "Job posting freshness tiers (hot/warm/cooling/stale)",
    "opportunities": "Opportunity pipeline (grants/residencies/prizes/writing)",
    "market": "Market conditions, hot skills, and upcoming grant deadlines",
    "funding": "Funding pulse: viability score, top pathways, urgent blind spots",
}


# ---------------------------------------------------------------------------
# Section: Wins (recent milestones and achievements)
# ---------------------------------------------------------------------------


def section_wins(entries: list[dict]):
    """Highlight recent milestones to maintain momentum."""
    from datetime import timedelta

    today = date.today()
    window = timedelta(days=7)
    wins = []

    for e in entries:
        timeline = e.get("timeline", {})
        if not isinstance(timeline, dict):
            continue
        name = e.get("name", e.get("id", "?"))

        # Recently submitted
        sub_date = parse_date(timeline.get("submitted"))
        if sub_date and (today - sub_date) <= window:
            wins.append((sub_date, f"Submitted: {name}"))

        # Got a response (acknowledged/interview)
        ack_date = parse_date(timeline.get("acknowledged"))
        if ack_date and (today - ack_date) <= window:
            wins.append((ack_date, f"Response received: {name}"))

        intv_date = parse_date(timeline.get("interview"))
        if intv_date and (today - intv_date) <= window:
            wins.append((intv_date, f"Interview stage: {name}"))

        # Accepted
        outcome = e.get("outcome")
        outcome_date = parse_date(timeline.get("outcome_date"))
        if outcome == "accepted" and outcome_date and (today - outcome_date) <= window:
            wins.append((outcome_date, f"ACCEPTED: {name}"))

    print("RECENT WINS (last 7 days)")
    if not wins:
        print("  No milestones this week — keep pushing!")
    else:
        wins.sort(key=lambda x: x[0], reverse=True)
        for dt, desc in wins:
            print(f"  {dt.isoformat()} — {desc}")

    print()


# ---------------------------------------------------------------------------
# Section: Readiness (staged entry submission readiness)
# ---------------------------------------------------------------------------

def section_readiness(entries: list[dict]):
    """Show staged entries with readiness scores and blockers."""
    from preflight import check_entry, readiness_score

    staged = [e for e in entries if e.get("status") == "staged"]

    print("STAGED ENTRY READINESS")

    if not staged:
        print("   No staged entries.")
        print()
        return

    # Compute readiness for each
    scored = []
    for e in staged:
        rscore = readiness_score(e)
        errors, warnings = check_entry(e)
        scored.append((rscore, e, errors, warnings))

    # Sort by readiness score descending
    scored.sort(key=lambda x: -x[0])

    ready_now = [s for s in scored if s[0] >= 4]
    not_ready = [s for s in scored if s[0] < 4]

    if ready_now:
        print(f"   READY TO SUBMIT NOW ({len(ready_now)}):")
        for rscore, e, errors, warnings in ready_now:
            name = e.get("name", e.get("id", "?"))
            dl_date, dl_type = get_deadline(e)
            dl_str = ""
            if dl_date:
                d = days_until(dl_date)
                dl_str = f" — {d}d" if d >= 0 else " — EXPIRED"
            elif dl_type in ("rolling", "tba"):
                dl_str = f" — {dl_type}"
            print(f"     [{rscore}/5] {name}{dl_str}")
            for issue in errors[:2]:
                print(f"            [ERROR] {issue}")
            for issue in warnings[:2]:
                print(f"            [WARN]  {issue}")

    if not_ready:
        print(f"   NEEDS WORK ({len(not_ready)}):")
        for rscore, e, errors, warnings in not_ready:
            name = e.get("name", e.get("id", "?"))
            print(f"     [{rscore}/5] {name}")
            for issue in errors[:3]:
                print(f"            [ERROR] {issue}")
            for issue in warnings[:2]:
                print(f"            [WARN]  {issue}")

    print()


# ---------------------------------------------------------------------------
# Job freshness badge helper
# ---------------------------------------------------------------------------

_FRESHNESS_BADGES = {
    "hot": "[HOT <24h]",
    "warm": "[WARM 24-48h]",
    "cooling": "[COOLING 48-72h]",
    "stale": "[STALE >72h]",
}


def _freshness_badge(entry: dict) -> str:
    """Return a freshness indicator string for a job entry.

    Non-job entries return an empty string.  Job entries with no parseable
    date return '[AGE?]'.
    """
    if entry.get("track") != "job":
        return ""
    age = get_posting_age_hours(entry)
    if age is None:
        return "[AGE?]"
    tier = get_freshness_tier(entry)
    return _FRESHNESS_BADGES.get(tier, "[AGE?]")


# ---------------------------------------------------------------------------
# Section: Job Pipeline
# ---------------------------------------------------------------------------

def section_jobs(entries: list[dict]):
    """Display job-track pipeline sorted by score and submission status."""
    job_entries = [e for e in entries if e.get("track") == "job"]

    print("JOB PIPELINE")
    if not job_entries:
        print("   No job-track entries in pipeline.")
        print()
        return

    # Group by status
    by_status: dict[str, list] = {}
    for e in job_entries:
        status = e.get("status", "unknown")
        by_status.setdefault(status, []).append(e)

    # Show counts
    print(f"   Total job entries: {len(job_entries)}")
    status_order = ["research", "qualified", "drafting", "staged", "deferred",
                    "submitted", "acknowledged", "interview", "outcome"]
    status_parts = []
    for s in status_order:
        c = len(by_status.get(s, []))
        if c:
            status_parts.append(f"{s}={c}")
    print(f"   Status: {', '.join(status_parts)}")
    print()

    # Actionable jobs sorted by score
    actionable_jobs = [e for e in job_entries if e.get("status") in ACTIONABLE_STATUSES]
    actionable_jobs.sort(key=lambda e: get_score(e), reverse=True)

    if actionable_jobs:
        print("   Actionable (by score):")
        for e in actionable_jobs:
            entry_id = e.get("id", "?")
            name = e.get("name", entry_id)
            score = get_score(e)
            status = e.get("status", "?")
            portal = e.get("target", {}).get("portal", "?") if isinstance(e.get("target"), dict) else "?"
            tags_str = ""
            tags = e.get("tags", [])
            if isinstance(tags, list) and "auto-sourced" in tags:
                tags_str = " [auto]"
            freshness_badge = _freshness_badge(e)
            print(f"     [{score:.1f}] {name} — {status} [{portal}]{tags_str} {freshness_badge}")

    # Submitted jobs
    submitted_jobs = [e for e in job_entries if e.get("status") in ("submitted", "acknowledged", "interview")]
    if submitted_jobs:
        print("   Awaiting response:")
        for e in submitted_jobs:
            name = e.get("name", e.get("id", "?"))
            status = e.get("status", "?")
            tl = e.get("timeline", {})
            sub_date = tl.get("submitted", "") if isinstance(tl, dict) else ""
            days_str = ""
            if sub_date:
                sd = parse_date(sub_date)
                if sd:
                    days_waiting = (date.today() - sd).days
                    days_str = f" ({days_waiting}d ago)"
            print(f"     {name} — {status}{days_str}")

    print()


# ---------------------------------------------------------------------------
# Section: Job Freshness
# ---------------------------------------------------------------------------

def section_job_freshness(entries: list[dict]):
    """Show job posting freshness breakdown: hot/warm/cooling/stale counts and listings."""
    job_entries = [e for e in entries
                   if e.get("track") == "job" and e.get("status") in ACTIONABLE_STATUSES]

    print("JOB FRESHNESS")

    if not job_entries:
        print("   No actionable job entries.")
        print()
        return

    # Bucket entries by tier
    buckets: dict[str, list[dict]] = {
        "hot": [], "warm": [], "cooling": [], "stale": [], "unknown": [],
    }
    for e in job_entries:
        age = get_posting_age_hours(e)
        if age is None:
            buckets["unknown"].append(e)
        else:
            tier = get_freshness_tier(e) or "unknown"
            buckets[tier].append(e)

    hot = buckets["hot"]
    warm = buckets["warm"]
    cooling = buckets["cooling"]
    stale = buckets["stale"]
    unknown = buckets["unknown"]

    print(f"   HOT: {len(hot)}  |  WARM: {len(warm)}  |  COOLING: {len(cooling)}  |  STALE: {len(stale)}  |  AGE?: {len(unknown)}")
    print()

    if hot:
        print("   HOT — submit NOW:")
        for e in sorted(hot, key=lambda x: get_score(x), reverse=True):
            name = e.get("name", e.get("id", "?"))
            score = get_score(e)
            print(f"     [{score:.1f}] {name}")

    if warm:
        print("   WARM — still viable today:")
        for e in sorted(warm, key=lambda x: get_score(x), reverse=True):
            name = e.get("name", e.get("id", "?"))
            score = get_score(e)
            print(f"     [{score:.1f}] {name}")

    if cooling:
        print("   COOLING — submit only if staged:")
        for e in sorted(cooling, key=lambda x: get_score(x), reverse=True):
            name = e.get("name", e.get("id", "?"))
            score = get_score(e)
            print(f"     [{score:.1f}] {name}")

    if stale:
        print(f"   {len(stale)} stale job entries — candidates for auto-expire")

    if unknown:
        print(f"   {len(unknown)} entries with no posting date (cannot determine freshness)")

    print()


# ---------------------------------------------------------------------------
# Section: Opportunity Pipeline
# ---------------------------------------------------------------------------

def section_opportunities(entries: list[dict]):
    """Display non-job pipeline sorted by deadline."""
    opp_entries = [e for e in entries
                   if e.get("track") != "job"
                   and e.get("status") in ACTIONABLE_STATUSES]

    print("OPPORTUNITY PIPELINE (grants/residencies/prizes/writing)")
    if not opp_entries:
        print("   No actionable non-job entries.")
        print()
        return

    # Sort by deadline (hard deadlines first), then by score
    def opp_sort_key(e):
        dl_date, dl_type = get_deadline(e)
        if dl_date:
            d = days_until(dl_date)
            if d >= 0 and dl_type in ("hard", "fixed"):
                return (0, d, -get_score(e))
        return (1, 9999, -get_score(e))

    opp_entries.sort(key=opp_sort_key)

    print(f"   Actionable opportunities: {len(opp_entries)}")
    print()
    for e in opp_entries[:15]:
        name = e.get("name", e.get("id", "?"))
        score = get_score(e)
        status = e.get("status", "?")
        track = e.get("track", "?")
        dl_date, dl_type = get_deadline(e)
        dl_str = ""
        if dl_date:
            d = days_until(dl_date)
            if d < 0:
                dl_str = f" EXPIRED {abs(d)}d ago"
            elif dl_type in ("hard", "fixed"):
                dl_str = f" {d}d left"
            else:
                dl_str = f" ~{d}d ({dl_type})"
        elif dl_type in ("rolling", "tba"):
            dl_str = f" {dl_type}"
        effort = get_effort(e)
        print(f"     [{score:.1f}] {name}")
        print(f"           {track} — {status} — {effort}{dl_str}")

    if len(opp_entries) > 15:
        print(f"     ... and {len(opp_entries) - 15} more")
    print()


# ---------------------------------------------------------------------------
# Section: Market Intelligence
# ---------------------------------------------------------------------------

def section_market():
    """Print market conditions, hot skills, and upcoming grant deadlines from market intel."""
    intel = _load_market_intel()
    if not intel:
        print("MARKET INTELLIGENCE")
        print("   No data — run: python scripts/market_intel.py --sources")
        print()
        return

    meta = intel.get("meta", {})
    mc = intel.get("market_conditions", {})
    skills = intel.get("skills_signals", {})
    calendar = intel.get("grant_calendar", {})
    today = date.today()

    print("MARKET INTELLIGENCE")
    print(f"   Version: {meta.get('version', '?')} | Sources: {meta.get('sources_count', 0)} | Updated: {meta.get('last_updated', '?')}")
    print()

    # Market conditions summary
    layoffs = mc.get("layoffs_ytd_2026", 0)
    cold_viability = mc.get("cold_app_viability", "unknown").upper()
    ai_rejection = mc.get("ai_content_rejection_rate_generic", 0)
    swe_growth = mc.get("swe_hiring_yoy_growth", 0)
    print("   CONDITIONS:")
    print(f"     Tech layoffs YTD:  {layoffs:,} (cold app viability: {cold_viability})")
    print(f"     SWE hiring YoY:    +{swe_growth*100:.1f}% recovery")
    print(f"     AI rejection rate: {ai_rejection*100:.0f}% of HMs reject generic AI content")
    print()

    # Hot skills
    hot = skills.get("hot_2026", [])
    if hot:
        print(f"   HOT SKILLS 2026: {', '.join(hot)}")
    print()

    # Upcoming calendar items
    print("   UPCOMING DEADLINES:")
    events = []
    for name, data in calendar.items():
        if not isinstance(data, dict):
            continue
        closes = data.get("closes")
        if closes and closes not in ("tba-fall-2026", "monitor-2026", "monitor", "rolling"):
            try:
                from datetime import datetime as _dt
                d = _dt.strptime(closes, "%Y-%m-%d").date()
                days_left = (d - today).days
                if -7 <= days_left <= 60:
                    award = data.get("award_max") or data.get("award") or data.get("award_total_eur")
                    award_str = f"${award:,}" if isinstance(award, int) and "eur" not in name else (f"€{award}" if "eur" in name.lower() else str(award) if award else "")
                    if data.get("award_total_eur"):
                        award_str = f"€{data['award_total_eur']:,}"
                    urgency = "!!!" if days_left <= 7 else ("!!" if days_left <= 14 else "")
                    label = name.replace("_", " ").title()
                    print(f"     {urgency:>4} {label}: closes {closes} ({days_left:+d}d) {award_str}")
                    events.append((days_left, name))
            except ValueError:
                pass
    if not events:
        print("     No deadlines in next 60 days.")
    print()


def section_funding():
    """Print funding pulse: viability score, top pathways, urgent blind spots."""
    try:
        from funding_scorer import (
            load_startup_profile,
            run_pathway_scorer,
            score_blindspots,
            score_viability,
        )
        from score import load_market_intelligence
    except ImportError:
        print("FUNDING PULSE")
        print("   Error: funding_scorer not available")
        print()
        return

    profile = load_startup_profile()
    intel = load_market_intelligence()

    # Viability
    viability = score_viability(profile, intel)
    print("FUNDING PULSE")
    print(f"   Viability: {viability['composite']}/{viability['max']} — {viability['band']}")
    print()

    # Top 3 pathways
    pathways = run_pathway_scorer(profile, intel)
    print("   TOP PATHWAYS:")
    for i, p in enumerate(pathways[:3], 1):
        eligible = "YES" if p["eligible"] else "no"
        print(f"     {i}. [{p['score']:4.1f}/10] {p['pathway']:<28s} (eligible: {eligible})")
    print()

    # Urgent blind spots
    blindspots = score_blindspots(profile, intel)
    if blindspots["urgent"]:
        print("   !! URGENT BLIND SPOTS:")
        for cat, label, note in blindspots["urgent"]:
            print(f"      [{cat}] {label}")
        print()

    completion = blindspots["completed"]
    total = blindspots["total"]
    print(f"   Blind spots: {completion}/{total} addressed")
    print()


def run_standup(hours: float, section: str | None, do_log: bool, track_filter: str | None = None):
    """Run the full standup or a single section.

    Args:
        track_filter: "jobs" for job-only standup, "opportunities" for non-jobs,
                      None for both (default).
    """
    entries = load_entries()
    if not entries:
        print("No pipeline entries found.")
        sys.exit(1)

    today = date.today()
    print("=" * 60)
    print(f"DAILY STANDUP — {today.strftime('%A, %B %d, %Y')}")
    print("=" * 60)
    print()

    # Standalone sections (no entries needed)
    if section == "market":
        section_market()
        return
    if section == "funding":
        section_funding()
        return

    # Track-filtered views
    if track_filter == "jobs" or section == "jobs":
        section_jobs(entries)
        return

    if section == "jobfreshness":
        section_job_freshness(entries)
        return

    if track_filter == "opportunities" or section == "opportunities":
        section_opportunities(entries)
        return

    health_stats = {}
    stale_stats = {}
    plan_stats = {}

    if section is None or section == "health":
        health_stats = section_health(entries)

    # Show dual-track summary when running full standup
    if section is None:
        section_market()
        section_jobs(entries)
        section_opportunities(entries)

    if section is None or section == "wins":
        section_wins(entries)
    if section is None or section == "stale":
        stale_stats = section_stale(entries)
    if section is None or section == "execution":
        section_execution_gap(entries)
    if section is None or section == "plan":
        plan_stats = section_plan(entries, hours)
    if section is None or section == "outreach":
        section_outreach(entries)
    if section is None or section == "practices":
        section_practices(entries, stale_stats)
    if section is None or section == "replenish":
        section_replenish(entries)
    if section is None or section == "deferred":
        section_deferred(entries)
    if section is None or section == "freshness":
        section_signal_freshness()
    if section is None or section == "followup":
        section_followup(entries)
    if section is None or section == "readiness":
        section_readiness(entries)
    if do_log or section == "log":
        # Need all stats for logging — suppress stdout if not already displayed
        import contextlib
        import io
        if not health_stats:
            with contextlib.redirect_stdout(io.StringIO()):
                health_stats = section_health(entries)
        if not stale_stats:
            with contextlib.redirect_stdout(io.StringIO()):
                stale_stats = section_stale(entries)
        if not plan_stats:
            with contextlib.redirect_stdout(io.StringIO()):
                plan_stats = section_plan(entries, hours)
        section_log(health_stats, stale_stats, plan_stats)


# ---------------------------------------------------------------------------
# Triage mode
# ---------------------------------------------------------------------------

# Derive forward-only advancement map from canonical VALID_TRANSITIONS.
# For each actionable status, the "next" status is the natural pipeline progression.
_FORWARD_PATH = ["research", "qualified", "drafting", "staged", "submitted"]
NEXT_STATUS = {}
for _i, _s in enumerate(_FORWARD_PATH[:-1]):
    _next = _FORWARD_PATH[_i + 1]
    if _next in VALID_TRANSITIONS.get(_s, set()):
        NEXT_STATUS[_s] = _next


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
    print("For each entry: [a]dvance  [w]ithdraw  [t]ouch  [s]kip  [q]uit\n")

    advanced = 0
    withdrawn = 0
    touched = 0

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
        print("  [w] Withdraw  [t] Touch (mark reviewed)  [s] Skip  [q] Quit")

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
            print("  -> Withdrawn\n")
        elif choice == "t" and filepath:
            _triage_update_entry(filepath, entry_id, touch=True)
            touched += 1
            print("  -> Touched\n")
        else:
            print("  -> Skipped\n")

    print(f"Triage complete: {advanced} advanced, {withdrawn} withdrawn, {touched} touched")


def _triage_update_entry(
    filepath: Path,
    entry_id: str,
    status: str | None = None,
    withdraw: bool = False,
    reason: str = "",
    touch: bool = False,
):
    """Update an entry file during triage."""
    content = filepath.read_text()

    if touch:
        content = update_last_touched_content(content)

    if status and not withdraw:
        content = update_yaml_field(content, "status", status)

    if withdraw:
        content = update_yaml_field(content, "status", "outcome")
        content = update_yaml_field(content, "outcome", "withdrawn")
        if reason:
            # Add withdrawal_reason if not present
            if "withdrawal_reason:" not in content:
                content = content.rstrip() + f"\nwithdrawal_reason:\n  reason: strategic_shift\n  detail: \"{reason}\"\n  date: \"{date.today().isoformat()}\"\n  reopen: false\n"

    filepath.write_text(content)


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
    parser.add_argument("--jobs", action="store_true",
                        help="Show job pipeline status only")
    parser.add_argument("--opportunities", action="store_true",
                        help="Show opportunity pipeline only (grants/residencies/prizes/writing)")
    args = parser.parse_args()

    if args.touch:
        touch_entry(args.touch)
        return

    if args.triage:
        run_triage()
        return

    track_filter = None
    if args.jobs:
        track_filter = "jobs"
    elif args.opportunities:
        track_filter = "opportunities"

    run_standup(args.hours, args.section, args.log, track_filter=track_filter)


if __name__ == "__main__":
    main()
