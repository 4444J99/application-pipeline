#!/usr/bin/env python3
"""Market intelligence report — view and validate research-backed pipeline parameters.

Reads strategy/market-intelligence-2026.json and presents structured summaries
for use in daily standup, strategy planning, and script calibration.

Usage:
    python scripts/market_intel.py                    # Summary: conditions + benchmarks
    python scripts/market_intel.py --track job        # Track-specific benchmarks
    python scripts/market_intel.py --staleness        # Flag if intelligence is >90 days old
    python scripts/market_intel.py --calendar         # Grant timing calendar
    python scripts/market_intel.py --salary           # Compensation benchmarks
    python scripts/market_intel.py --sources          # Source count and last updated
    python scripts/market_intel.py --skills           # Skills signal summary
    python scripts/market_intel.py --channels         # Channel multiplier comparison
"""

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS_DIR.parent
INTEL_FILE = REPO_ROOT / "strategy" / "market-intelligence-2026.json"


_REQUIRED_INTEL_KEYS = {
    "meta": dict,
    "market_conditions": dict,
    "track_benchmarks": dict,
    "portal_friction_scores": dict,
    "skills_signals": dict,
    "follow_up_protocol": dict,
    "stale_thresholds_days": dict,
}


def validate_intel_schema(intel: dict) -> list[str]:
    """Return list of schema violations in market intelligence JSON."""
    issues = []
    for key, expected_type in _REQUIRED_INTEL_KEYS.items():
        if key not in intel:
            issues.append(f"missing required key: '{key}'")
        elif not isinstance(intel[key], expected_type):
            issues.append(
                f"key '{key}' expected {expected_type.__name__}, "
                f"got {type(intel[key]).__name__}"
            )
    return issues


def load_intel() -> dict:
    """Load market intelligence JSON, fail gracefully if missing or invalid."""
    if not INTEL_FILE.exists():
        print(f"Warning: {INTEL_FILE} not found. Using empty defaults.", file=sys.stderr)
        return {}
    with open(INTEL_FILE) as f:
        intel = json.load(f)
    schema_issues = validate_intel_schema(intel)
    if schema_issues:
        for issue in schema_issues:
            print(f"[WARN] market-intelligence-2026.json schema: {issue}", file=sys.stderr)
    return intel


def check_staleness(intel: dict) -> bool:
    """Return True if intelligence is stale (>90 days old)."""
    meta = intel.get("meta", {})
    last_updated = meta.get("last_updated")
    if not last_updated:
        return True
    try:
        updated_date = datetime.strptime(last_updated, "%Y-%m-%d").date()
        threshold = intel.get("stale_thresholds_days", {}).get("intelligence_staleness", 90)
        return (date.today() - updated_date).days > threshold
    except ValueError:
        return True


def fmt_pct(v) -> str:
    """Format float as percentage string."""
    if v is None:
        return "N/A"
    return f"{v * 100:.1f}%"


def fmt_days(v) -> str:
    """Format numeric as 'N days'."""
    if v is None:
        return "N/A"
    return f"{v}d"


def fmt_currency(v, currency="USD") -> str:
    """Format number as currency string."""
    if v is None:
        return "N/A"
    if v >= 1000:
        return f"${v:,.0f} {currency}"
    return f"${v} {currency}"


def section_summary(intel: dict):
    """Print market conditions + key benchmarks summary."""
    meta = intel.get("meta", {})
    mc = intel.get("market_conditions", {})

    print("MARKET INTELLIGENCE SUMMARY")
    print("=" * 55)
    print(f"Version:       {meta.get('version', 'unknown')}")
    print(f"Last updated:  {meta.get('last_updated', 'unknown')}")
    print(f"Next review:   {meta.get('next_review', 'unknown')}")
    print(f"Sources:       {meta.get('sources_count', 0)}")

    stale = check_staleness(intel)
    if stale:
        print("!! STALE — intelligence >90 days old. Run research refresh.")
    print()

    print("MARKET CONDITIONS (2026 YTD)")
    print("-" * 40)
    layoffs = mc.get("layoffs_ytd_2026", 0)
    daily = mc.get("layoffs_daily_rate_2026", 0)
    as_of = mc.get("layoffs_ytd_2026_as_of", "")
    print(f"  Tech layoffs YTD:     {layoffs:,} ({daily}/day) as of {as_of}")
    print(f"  2025 total layoffs:   {mc.get('layoffs_total_2025', 0):,} across {mc.get('layoffs_events_2025', 0)} companies")
    print(f"  AI layoff share 2025: {fmt_pct(mc.get('ai_layoff_share_2025'))} of 2025 layoffs tied to AI")
    print(f"  SWE hiring YoY:       +{fmt_pct(mc.get('swe_hiring_yoy_growth'))} (recovery in progress)")
    print(f"  AI job postings:      +{fmt_pct(mc.get('ai_job_postings_growth_2024_2025'))} growth 2024→2025")
    ai_share_25 = mc.get("ai_ml_share_of_tech_jobs_2025", 0)
    ai_share_23 = mc.get("ai_ml_share_of_tech_jobs_2023", 0)
    print(f"  AI/ML share of jobs:  {fmt_pct(ai_share_23)} (2023) → {fmt_pct(ai_share_25)} (2025)")
    print(f"  Cold app viability:   {mc.get('cold_app_viability', 'unknown').upper()}")
    print(f"  AI content rejection: {fmt_pct(mc.get('ai_content_rejection_rate_generic'))} generic; {fmt_pct(mc.get('ai_content_rejection_rate_robotic'))} robotic")
    print()

    print("TRACK BENCHMARKS")
    print("-" * 40)
    benchmarks = intel.get("track_benchmarks", {})
    print(f"  {'Track':<12} {'Cold Rate':>10} {'Resp Days':>10} {'Accept':>8} {'Timeline':>12}")
    print(f"  {'-'*12} {'-'*10} {'-'*10} {'-'*8} {'-'*12}")
    for track, data in benchmarks.items():
        cold = fmt_pct(data.get("cold_response_rate") or data.get("acceptance_rate"))
        days = fmt_days(data.get("median_response_days"))
        accept = fmt_pct(data.get("acceptance_rate") or data.get("cold_response_rate"))
        timeline = data.get("conversion_timeline_weeks", [])
        tl_str = f"{timeline[0]}-{timeline[1]}w" if len(timeline) == 2 else "?"
        print(f"  {track:<12} {cold:>10} {days:>10} {accept:>8} {tl_str:>12}")
    print()


def section_track(intel: dict, track: str):
    """Print detailed benchmark for a specific track."""
    benchmarks = intel.get("track_benchmarks", {})
    if track not in benchmarks:
        available = ", ".join(benchmarks.keys())
        print(f"Track '{track}' not found. Available: {available}")
        return

    data = benchmarks[track]
    print(f"TRACK BENCHMARK: {track.upper()}")
    print("=" * 45)
    for k, v in data.items():
        if k == "note":
            continue
        if isinstance(v, float):
            print(f"  {k:<35} {fmt_pct(v)}")
        elif isinstance(v, list):
            print(f"  {k:<35} {v}")
        else:
            print(f"  {k:<35} {v}")
    note = data.get("note")
    if note:
        print(f"\n  NOTE: {note}")
    print()


def section_calendar(intel: dict):
    """Print grant/deadline calendar."""
    calendar = intel.get("grant_calendar", {})
    today = date.today()

    print("GRANT & DEADLINE CALENDAR")
    print("=" * 55)
    print(f"Today: {today}")
    print()

    events = []
    for name, data in calendar.items():
        if not isinstance(data, dict):
            continue
        closes = data.get("closes")
        opens = data.get("opens")
        status = data.get("status", "open")

        # Build deadline info
        for label, field in [("CLOSES", closes), ("OPENS", opens)]:
            if field and field not in ("tba-fall-2026", "monitor-2026", "monitor", "rolling"):
                try:
                    d = datetime.strptime(field, "%Y-%m-%d").date()
                    days_left = (d - today).days
                    events.append((d, days_left, label, name, data))
                except ValueError:
                    pass

    events.sort(key=lambda x: x[0])

    for d, days_left, label, name, data in events:
        award = data.get("award_max") or data.get("award") or data.get("award_total_eur")
        award_str = f"${award:,}" if isinstance(award, int) else (f"€{award}" if "eur" in str(award).lower() else str(award) if award else "")
        if data.get("award_total_eur"):
            award_str = f"€{data['award_total_eur']:,}"

        urgency = ""
        if days_left < 0:
            urgency = " [PAST]"
        elif days_left <= 7:
            urgency = " [!!!URGENT]"
        elif days_left <= 14:
            urgency = " [!!SOON]"
        elif days_left <= 30:
            urgency = " [!UPCOMING]"

        print(f"  {label} {d} ({days_left:+d}d){urgency}")
        print(f"    {name.replace('_', ' ').title()}")
        if award_str:
            print(f"    Award: {award_str}")
        note = data.get("note", "")
        if note:
            print(f"    Note: {note}")
        print()

    # Show items with no parseable date
    print("  MONITOR / TBD:")
    for name, data in calendar.items():
        if not isinstance(data, dict):
            continue
        closes = data.get("closes", "")
        status = data.get("status", "")
        if closes in ("tba-fall-2026", "monitor-2026", "monitor", "rolling") or status in ("monitor", "nominations-closed"):
            award = data.get("award") or data.get("award_max")
            award_str = f"${award:,}" if isinstance(award, int) else ""
            print(f"    {name.replace('_', ' ').title()} — {status or closes} {award_str}")
    print()


def section_salary(intel: dict):
    """Print compensation benchmarks."""
    salaries = intel.get("salary_benchmarks", {})

    print("COMPENSATION BENCHMARKS")
    print("=" * 55)
    print(f"  {'Role':<28} {'Min':>10} {'Median':>10} {'Max':>10} {'Unit':<10}")
    print(f"  {'-'*28} {'-'*10} {'-'*10} {'-'*10} {'-'*10}")

    for role, data in salaries.items():
        if not isinstance(data, dict):
            continue
        lo = data.get("min", 0)
        hi = data.get("max", 0)
        med = data.get("median")
        currency = data.get("currency", "USD")
        unit = data.get("unit", "TC")
        symbol = "€" if currency == "EUR" else "$"

        lo_str = f"{symbol}{lo:,.0f}" if lo else "-"
        hi_str = f"{symbol}{hi:,.0f}" if hi else "-"
        med_str = f"{symbol}{med:,.0f}" if med else "-"
        label = role.replace("_", " ")
        print(f"  {label:<28} {lo_str:>10} {med_str:>10} {hi_str:>10} {unit:<10}")
    print()


def section_skills(intel: dict):
    """Print skills signal summary."""
    skills = intel.get("skills_signals", {})

    print("SKILLS SIGNAL INTELLIGENCE 2026")
    print("=" * 45)
    hot = skills.get("hot_2026", [])
    moderate = skills.get("moderate_2026", [])
    cooling = skills.get("cooling_2026", [])

    print(f"  HOT (strong demand):     {', '.join(hot)}")
    print(f"  MODERATE:                {', '.join(moderate)}")
    print(f"  COOLING:                 {', '.join(cooling)}")
    print()
    print(f"  Go job posting growth:   +{fmt_pct(skills.get('go_job_posting_growth'))}")
    print(f"  Kubernetes rank:         {skills.get('kubernetes_rank', 'N/A')}")
    print(f"  MCP adoption:            {skills.get('mcp_adoption', 'N/A')}")
    print(f"  Agentic AI 2025:         {skills.get('agentic_ai_market_share_2025', 'N/A')}")
    print()
    print("  SIGNAL WEIGHTS:")
    print(f"    Portfolio/artifacts:   {fmt_pct(skills.get('portfolio_signal_weight'))} of HMs review immediately")
    print(f"    GitHub public repos:   {fmt_pct(skills.get('github_public_signal_weight'))} signal weight")
    print(f"    Tech recruiters:       {fmt_pct(skills.get('tech_recruiters_who_review_github'))} review GitHub")
    print(f"    Creative portfolio:    {fmt_pct(skills.get('creative_fields_portfolio_resume_link_rate'))} include link on resume")
    note = skills.get("note")
    if note:
        print(f"\n  NOTE: {note}")
    print()


def section_channels(intel: dict):
    """Print channel multiplier comparison."""
    channels = intel.get("channel_multipliers", {})
    follow_up = intel.get("follow_up_protocol", {})

    print("CHANNEL MULTIPLIERS")
    print("=" * 45)
    print(f"  {'Channel':<25} {'Multiplier':>12} {'Response Rate':>15}")
    print(f"  {'-'*25} {'-'*12} {'-'*15}")

    for channel, data in channels.items():
        mult = data.get("response_rate_multiplier", 1.0)
        rr_range = data.get("response_rate_range")
        if rr_range:
            rr_str = f"{fmt_pct(rr_range[0])} – {fmt_pct(rr_range[1])}"
        else:
            rr_str = "-"
        print(f"  {channel:<25} {mult:>12.1f}x {rr_str:>15}")
    print()

    print("FOLLOW-UP PROTOCOL (research-backed)")
    print("-" * 45)
    print(f"  Connect window:  Day {follow_up.get('connect_window_days', [1,3])}")
    print(f"  First DM:        Day {follow_up.get('first_dm_days', [7,10])}")
    print(f"  Final DM:        Day {follow_up.get('second_dm_days', [14,21])}")
    print(f"  Max follow-ups:  {follow_up.get('max_follow_ups', 2)}")
    print(f"  Follow-up lift:  +{fmt_pct(follow_up.get('follow_up_offer_lift', 0))} more offers")
    print(f"  HMs who expect:  {fmt_pct(follow_up.get('hiring_managers_who_expect_followup', 0))}")
    print(f"  Candidates who:  {fmt_pct(follow_up.get('candidates_who_actually_followup', 0))} actually follow up")
    print(f"  Best days:       {', '.join(follow_up.get('best_days_of_week', []))}")
    note = follow_up.get("note")
    if note:
        print(f"\n  NOTE: {note}")
    print()


def section_sources(intel: dict):
    """Print source count and metadata."""
    meta = intel.get("meta", {})
    stale = check_staleness(intel)

    print("MARKET INTELLIGENCE METADATA")
    print("=" * 45)
    print(f"  Version:        {meta.get('version', 'unknown')}")
    print(f"  Sources:        {meta.get('sources_count', 0)}")
    print(f"  Last updated:   {meta.get('last_updated', 'unknown')}")
    print(f"  Next review:    {meta.get('next_review', 'unknown')}")
    print(f"  Status:         {'!! STALE — refresh needed' if stale else 'OK — within review window'}")
    note = meta.get("note")
    if note:
        print(f"  Note:           {note}")
    print()
    print("  Data file:      strategy/market-intelligence-2026.json")
    print("  Corpus file:    strategy/market-research-corpus.md")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Market intelligence report — pipeline parameters from research corpus"
    )
    parser.add_argument("--track", metavar="TRACK",
                        help="Show detailed benchmark for a specific track (job, grant, residency, etc.)")
    parser.add_argument("--staleness", action="store_true",
                        help="Check if intelligence is stale (>90 days old)")
    parser.add_argument("--calendar", action="store_true",
                        help="Show grant/deadline timing calendar")
    parser.add_argument("--salary", action="store_true",
                        help="Show compensation benchmarks")
    parser.add_argument("--skills", action="store_true",
                        help="Show skills signal summary")
    parser.add_argument("--channels", action="store_true",
                        help="Show channel multiplier comparison")
    parser.add_argument("--sources", action="store_true",
                        help="Show source count and last updated")
    args = parser.parse_args()

    intel = load_intel()
    if not intel:
        print("Error: no market intelligence data available.", file=sys.stderr)
        sys.exit(1)

    if args.staleness:
        stale = check_staleness(intel)
        meta = intel.get("meta", {})
        print(f"Last updated: {meta.get('last_updated', 'unknown')}")
        print(f"Status: {'STALE — refresh needed' if stale else 'OK — within 90-day window'}")
        sys.exit(1 if stale else 0)

    if args.sources:
        section_sources(intel)
        return

    if args.track:
        section_track(intel, args.track)
        return

    if args.calendar:
        section_calendar(intel)
        return

    if args.salary:
        section_salary(intel)
        return

    if args.skills:
        section_skills(intel)
        return

    if args.channels:
        section_channels(intel)
        return

    # Default: full summary
    section_summary(intel)
    section_skills(intel)
    section_calendar(intel)


if __name__ == "__main__":
    main()
