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
from datetime import date, datetime, timedelta
from pathlib import Path

import standup_relationship_sections as _relationship_sections
import standup_work_sections as _work_sections
import yaml
from pipeline_lib import (
    ACTIONABLE_STATUSES,
    ALL_PIPELINE_DIRS,
    COMPANY_CAP,
    EFFORT_MINUTES,
    PIPELINE_DIR_RESEARCH_POOL,
    REPO_ROOT,
    SIGNALS_DIR,
    VALID_TRANSITIONS,
    compute_freshness_score,
    days_until,
    get_deadline,
    get_effort,
    get_mode_thresholds,
    get_score,
    load_entries,
    load_market_intelligence,
    parse_date,
    update_yaml_field,
)
from pipeline_lib import (
    update_last_touched as update_last_touched_content,
)
from standup_constants import (
    OUTREACH_BY_STATUS,
    PRACTICES_BY_CONTEXT,
    SECTIONS,
    build_next_status,
)
from standup_pipeline_sections import (
    _freshness_badge,
    section_job_freshness,
    section_jobs,
    section_opportunities,
)

STANDUP_LOG = SIGNALS_DIR / "standup-log.yaml"


def _get_stale_threshold(key: str, default: int) -> int:
    """Load a stale threshold from mode_thresholds first, then stale_thresholds_days, then default."""
    try:
        from pipeline_lib import get_mode_thresholds
        mode_t = get_mode_thresholds()
        # Map key names: entry_stale -> stale_days, entry_stagnant -> stagnant_days
        mode_key_map = {"entry_stale": "stale_days", "entry_stagnant": "stagnant_days"}
        mapped = mode_key_map.get(key)
        if mapped and mapped in mode_t:
            return int(mode_t[mapped])
    except ImportError:
        pass
    intel = load_market_intelligence()
    return intel.get("stale_thresholds_days", {}).get(key, default)


# Load thresholds from market intel (with hardcoded fallbacks)
STAGNATION_DAYS = _get_stale_threshold("entry_stale", 7)
URGENCY_DAYS = 14
AT_RISK_DAYS = 3
REPLENISH_THRESHOLD = 3  # precision mode: fewer entries, deeper work
EXECUTION_STALE_STAGED_DAYS = 7  # 7 days (precision mode: more time per entry)
TARGET_STAGED_SUBMIT_CONVERSION = 0.50
AGENT_ACTIONS_LOG = SIGNALS_DIR / "agent-actions.yaml"


# ---------------------------------------------------------------------------
# Section 1: Pipeline Health
# ---------------------------------------------------------------------------

def section_health(entries: list[dict]) -> dict:
    """Pipeline-wide counts and velocity."""
    return _work_sections.section_health(
        entries,
        actionable_statuses=ACTIONABLE_STATUSES,
        parse_date_fn=parse_date,
    )


# ---------------------------------------------------------------------------
# Section: Precision Mode Compliance
# ---------------------------------------------------------------------------

def section_precision_compliance(entries: list[dict]) -> dict:
    """Report precision-mode compliance metrics."""
    thresholds = get_mode_thresholds()
    return _work_sections.section_precision_compliance(
        entries,
        actionable_statuses=ACTIONABLE_STATUSES,
        parse_date_fn=parse_date,
        max_active=thresholds.get("max_active", 10),
        max_weekly_submissions=thresholds.get("max_weekly_submissions", 2),
        company_cap=COMPANY_CAP,
    )


# ---------------------------------------------------------------------------
# Section 2: Staleness Alerts
# ---------------------------------------------------------------------------

def section_stale(entries: list[dict]) -> dict:
    """Flag expired, at-risk, and stagnant entries."""
    return _work_sections.section_stale(
        entries,
        actionable_statuses=ACTIONABLE_STATUSES,
        get_deadline_fn=get_deadline,
        days_until_fn=days_until,
        parse_date_fn=parse_date,
        at_risk_days=AT_RISK_DAYS,
        stagnation_days=STAGNATION_DAYS,
    )


# ---------------------------------------------------------------------------
# Section 2b: Execution Gap Snapshot
# ---------------------------------------------------------------------------

def _entry_has_portal_fields(entry: dict) -> bool:
    """Return True when portal_fields.fields exists and is non-empty."""
    return _work_sections.entry_has_portal_fields(entry)


def _compute_staged_submit_conversion(entries: list[dict]) -> tuple[int, int, float]:
    """Compute operational staged->submitted conversion from current pipeline state."""
    return _work_sections.compute_staged_submit_conversion(entries)


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
    return _work_sections.section_execution_gap(
        entries,
        parse_date_fn=parse_date,
        get_score_fn=get_score,
        target_staged_submit_conversion=TARGET_STAGED_SUBMIT_CONVERSION,
        execution_stale_staged_days=EXECUTION_STALE_STAGED_DAYS,
        load_recent_agent_runs_fn=_load_recent_agent_runs,
    )


# ---------------------------------------------------------------------------
# Section 3: Today's Work Plan (wraps daily_batch logic)
# ---------------------------------------------------------------------------

def section_plan(entries: list[dict], hours: float) -> dict:
    """Deadline-driven + score-sorted work plan within a time budget."""
    return _work_sections.section_plan(
        entries,
        hours,
        actionable_statuses=ACTIONABLE_STATUSES,
        urgency_days=URGENCY_DAYS,
        effort_minutes=EFFORT_MINUTES,
        get_deadline_fn=get_deadline,
        days_until_fn=days_until,
        get_score_fn=get_score,
        compute_freshness_score_fn=compute_freshness_score,
        get_effort_fn=get_effort,
        freshness_badge_fn=_freshness_badge,
    )


# ---------------------------------------------------------------------------
# Section 4: Outreach Suggestions
# ---------------------------------------------------------------------------

def section_outreach(entries: list[dict]):
    """Per-target outreach checklists based on status and deadline proximity."""
    _work_sections.section_outreach(
        entries,
        actionable_statuses=ACTIONABLE_STATUSES,
        get_deadline_fn=get_deadline,
        days_until_fn=days_until,
        get_score_fn=get_score,
        outreach_by_status=OUTREACH_BY_STATUS,
    )


# ---------------------------------------------------------------------------
# Section 5: Best Practices
# ---------------------------------------------------------------------------

def section_practices(entries: list[dict], stale_stats: dict):
    """Context-sensitive reminders from strategy docs."""
    _work_sections.section_practices(
        entries,
        stale_stats,
        get_deadline_fn=get_deadline,
        days_until_fn=days_until,
        practices_by_context=PRACTICES_BY_CONTEXT,
    )


# ---------------------------------------------------------------------------
# Section 6: Pipeline Replenishment
# ---------------------------------------------------------------------------

def section_replenish(entries: list[dict]):
    """Alert when actionable count drops below threshold."""
    _work_sections.section_replenish(
        entries,
        actionable_statuses=ACTIONABLE_STATUSES,
        get_deadline_fn=get_deadline,
        days_until_fn=days_until,
        replenish_threshold=REPLENISH_THRESHOLD,
        load_entries_fn=load_entries,
        pipeline_dir_research_pool=PIPELINE_DIR_RESEARCH_POOL,
        get_score_fn=get_score,
    )


# ---------------------------------------------------------------------------
# Section 7: Deferred Entries
# ---------------------------------------------------------------------------

def section_deferred(entries: list[dict]):
    """Show entries with status=deferred and their resume dates."""
    _work_sections.section_deferred(
        entries,
        parse_date_fn=parse_date,
    )


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

    # Market intelligence freshness
    from pipeline_market import check_market_intel_freshness
    market_status = check_market_intel_freshness(REPO_ROOT)
    if market_status["age_days"] < 0:
        print("     market-intel: MISSING")
        stale_count += 1
    elif market_status["warning"]:
        print(f"     market-intel: {market_status['warning']}")
        stale_count += 1
    else:
        print(f"     market-intel: OK ({market_status['age_days']:.0f}d old)")

    if stale_count == 0:
        print("     All signals fresh.")
    print()


# ---------------------------------------------------------------------------
# Section 8: Follow-Up Dashboard
# ---------------------------------------------------------------------------

def section_followup(entries: list[dict]):
    """Show follow-up dashboard: due/overdue actions for submitted entries."""
    _relationship_sections.section_followup(
        entries,
        parse_date_fn=parse_date,
    )


# ---------------------------------------------------------------------------
# Section: Relationships (cultivation dashboard)
# ---------------------------------------------------------------------------

def section_relationships(entries: list[dict]):
    """Relationship cultivation: top score-impact targets, today's actions, dense orgs."""
    _relationship_sections.section_relationships(entries)


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
# Section: Market Intelligence
# ---------------------------------------------------------------------------

def section_market():
    """Print market conditions, hot skills, and upcoming grant deadlines from market intel."""
    intel = load_market_intelligence()
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
    try:
        from pipeline_lib import get_mode_review_status
        review = get_mode_review_status()
        mode_label = review["mode"].upper()
        days_left = review["days_until_review"]
        if review["past_review"]:
            print(f"Mode: {mode_label} | REVIEW OVERDUE by {abs(days_left)}d — evaluate results")
        elif days_left <= 7:
            print(f"Mode: {mode_label} | Review in {days_left}d — prepare evaluation")
        else:
            print(f"Mode: {mode_label} | Review in {days_left}d")
    except ImportError:
        pass
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

    if section is None or section == "compliance":
        section_precision_compliance(entries)

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
    if section is None or section == "relationships":
        section_relationships(entries)
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

NEXT_STATUS = build_next_status(VALID_TRANSITIONS)


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
