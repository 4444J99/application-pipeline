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
    python scripts/market_intel.py --startup          # VC, seed/Series A, accelerators
    python scripts/market_intel.py --funding          # Cloud credits, RBF, grants
    python scripts/market_intel.py --differentiation  # Pitch deck, networking, proof of work
    python scripts/market_intel.py --meta             # Burnout, legal, insurance, blind spots
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
    "startup_funding_landscape": dict,
    "non_dilutive_funding": dict,
    "startup_mechanics": dict,
    "differentiation_signals": dict,
    "alternative_funding": dict,
    "meta_strategy": dict,
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


def section_startup(intel: dict):
    """Print startup funding landscape: VC metrics, seed/Series A, solo founder data."""
    sfl = intel.get("startup_funding_landscape", {})
    sm = intel.get("startup_mechanics", {})

    print("STARTUP FUNDING LANDSCAPE")
    print("=" * 55)
    print()

    # VC overview
    vc_total = sfl.get("vc_total_deployed_2025_usd", 0)
    ai_share = sfl.get("ai_share_of_vc_2025", 0)
    ai_total = sfl.get("ai_funding_total_2025_usd", 0)
    print("  VC MARKET (2025):")
    print(f"    Total deployed:        {fmt_currency(vc_total)}")
    print(f"    AI share:              {fmt_pct(ai_share)} ({fmt_currency(ai_total)})")
    conc = sfl.get("mega_deal_concentration_note", "")
    if conc:
        print(f"    Concentration:         {conc}")
    print(f"    Down-round rate Q3:    {fmt_pct(sfl.get('down_round_rate_q3_2025'))}")
    print()

    # Seed metrics
    seed = sfl.get("seed_metrics", {})
    print("  SEED ROUND METRICS:")
    print(f"    Median round:          {fmt_currency(seed.get('median_round_usd'))}")
    print(f"    Median pre-money:      {fmt_currency(seed.get('median_pre_money_valuation_usd'))}")
    arr_range = seed.get("expected_arr_usd", [])
    if len(arr_range) == 2:
        print(f"    Expected ARR:          {fmt_currency(arr_range[0])} – {fmt_currency(arr_range[1])}")
    print(f"    Closing time:          {fmt_days(seed.get('closing_days_median'))} median (was {fmt_days(seed.get('closing_days_2021'))} in 2021)")
    print(f"    SAFE prevalence:       {fmt_pct(seed.get('safe_prevalence_pre_seed'))} at pre-seed")
    print()

    # Series A
    series_a = sfl.get("series_a_metrics", {})
    print("  SERIES A METRICS:")
    print(f"    Median pre-money:      {fmt_currency(series_a.get('median_pre_money_valuation_usd'))}")
    a_arr = series_a.get("expected_arr_usd", [])
    if len(a_arr) == 2:
        print(f"    Expected ARR:          {fmt_currency(a_arr[0])} – {fmt_currency(a_arr[1])}")
    print(f"    Seed-to-A time:        {fmt_days(series_a.get('seed_to_a_days'))}")
    print(f"    Conversion rate:       {fmt_pct(series_a.get('conversion_rate_seed_to_a_2020_cohort'))} (2020 cohort)")
    print()

    # Solo founder
    solo = sm.get("solo_founder_data", {})
    print("  SOLO FOUNDER DATA:")
    print(f"    $1M+ revenue share:    {fmt_pct(solo.get('solo_pct_of_1m_revenue_companies'))}")
    print(f"    Share of exits:        {fmt_pct(solo.get('solo_pct_of_exits'))}")
    print()

    # Sectors
    winners = sfl.get("sector_winners_2026", [])
    losers = sfl.get("sector_losers_2026", [])
    print(f"  HOT SECTORS:    {', '.join(str(s) for s in winners)}")
    print(f"  COLD SECTORS:   {', '.join(str(s) for s in losers)}")
    print()

    # Accelerators
    acc = sm.get("accelerator_tier", {})
    if acc:
        print("  ACCELERATORS:")
        yc_rate = acc.get("yc_acceptance_rate")
        yc_deal = acc.get("yc_standard_deal", "")
        print(f"    YC acceptance:         {fmt_pct(yc_rate)}")
        print(f"    YC deal:               {yc_deal}")
        tier1 = acc.get("tier_1", [])
        print(f"    Tier 1:                {', '.join(str(t) for t in tier1)}")
    print()


def section_funding(intel: dict):
    """Print non-dilutive + alternative funding landscape."""
    ndf = intel.get("non_dilutive_funding", {})
    af = intel.get("alternative_funding", {})

    print("NON-DILUTIVE & ALTERNATIVE FUNDING")
    print("=" * 55)
    print()

    # Cloud credits
    credits = ndf.get("cloud_credits", {})
    print("  CLOUD CREDITS (always pursue):")
    entries = [
        ("Microsoft Founders Hub", credits.get("microsoft_founders_hub_usd")),
        ("AWS Activate", credits.get("aws_activate_usd")),
        ("AWS Activate (AI)", credits.get("aws_activate_ai_usd")),
        ("Google Cloud (AI)", credits.get("google_cloud_ai_usd")),
        ("NVIDIA Inception", credits.get("nvidia_inception_aws_usd")),
    ]
    total = 0
    for name, amt in entries:
        if amt:
            total += amt
            print(f"    {name:<25} {fmt_currency(amt)}")
    print(f"    {'TOTAL':<25} {fmt_currency(total)}")
    print()

    # SBIR/STTR
    sbir = ndf.get("sbir_sttr", {})
    status = sbir.get("status", "unknown")
    pool = sbir.get("annual_pool_usd", 0)
    print(f"  SBIR/STTR: {status.upper()} (${pool / 1e9:.0f}B/year frozen)")
    print()

    # RBF
    rbf = af.get("revenue_based_financing", {})
    if rbf:
        print("  REVENUE-BASED FINANCING:")
        print(f"    Market size (2027):    {fmt_currency(rbf.get('market_size_2027_usd'))}")
        print(f"    Min MRR:               {fmt_currency(rbf.get('min_mrr_usd'))}")
        providers = rbf.get("providers", {})
        for name, data in providers.items():
            if isinstance(data, dict):
                print(f"    {name.title()}: {data}")
        print()

    # Crowdfunding
    ecf = af.get("equity_crowdfunding", {})
    if ecf:
        print(f"  EQUITY CROWDFUNDING (Reg CF cap: {fmt_currency(ecf.get('reg_cf_annual_cap_usd'))})")
        platforms = ecf.get("platforms", {})
        for name, data in platforms.items():
            if isinstance(data, dict):
                raised = data.get("2025_raised_usd")
                if raised:
                    print(f"    {name.title()}: {fmt_currency(raised)} raised in 2025")
        print()

    # Crypto grants
    cg = af.get("crypto_web3_grants", {})
    if cg:
        print("  CRYPTO / WEB3 GRANTS:")
        print(f"    Gitcoin total:         {fmt_currency(cg.get('gitcoin_total_distributed_usd'))}")
        print(f"    Gitcoin funded through: {cg.get('gitcoin_funded_through', 'unknown')}")
        esp_range = cg.get("ethereum_esp_range_usd", [0, 0])
        if isinstance(esp_range, list) and len(esp_range) >= 2:
            print(f"    Ethereum ESP range:    {fmt_currency(esp_range[0])} – {fmt_currency(esp_range[1])}")
        print()

    # Consulting / Fractional CTO
    fc = af.get("fractional_cto", {})
    if fc:
        print("  FRACTIONAL CTO:")
        print(f"    Rate range:            ${fc.get('hourly_rate_usd', [0, 0])[0]}-${fc.get('hourly_rate_usd', [0, 0])[1]}/hr")
        print(f"    Average:               ${fc.get('average_hourly_usd', 300)}/hr")
        print(f"    Market growth:         {fc.get('market_growth', 'unknown')}")
        print()


def section_differentiation(intel: dict):
    """Print differentiation signals summary."""
    ds = intel.get("differentiation_signals", {})

    print("DIFFERENTIATION SIGNALS")
    print("=" * 55)
    print()

    # Pitch deck
    pd = ds.get("pitch_deck", {})
    if pd:
        print("  PITCH DECK:")
        review_time = pd.get("median_review_time_seconds", 0)
        print(f"    Median review time:    {review_time}s ({review_time / 60:.1f} min)")
        print(f"    First 3 slides:        {fmt_pct(pd.get('first_3_slides_decision_weight'))} of decision")
        print(f"    Rejection rate:        {fmt_pct(pd.get('rejection_rate'))}")
        print(f"    Clear next step lift:  +{fmt_pct(pd.get('clear_next_step_meeting_lift'))} meetings")
        print()

    # Networking
    nw = ds.get("networking", {})
    if nw:
        print("  NETWORKING:")
        print(f"    Warm intro conversion: {fmt_pct(nw.get('warm_intro_conversion'))}")
        cold_range = nw.get("cold_email_response", [])
        if len(cold_range) == 2:
            print(f"    Cold email response:   {fmt_pct(cold_range[0])} – {fmt_pct(cold_range[1])}")
        print(f"    Unrealized warm paths: {nw.get('unrealized_warm_paths', 0)}")
        print()

    # Personal brand
    pb = ds.get("personal_brand", {})
    if pb:
        print("  PERSONAL BRAND:")
        print(f"    LinkedIn personal vs co: {pb.get('linkedin_profile_vs_company_engagement', 0)}x engagement")
        print(f"    GitHub recruiter review: {fmt_pct(pb.get('github_recruiter_review_rate'))}")
        print(f"    GitHub scan time:       {pb.get('github_scan_time_seconds', 0)}s")
        pinned = pb.get("optimal_pinned_projects", [])
        if len(pinned) == 2:
            print(f"    Optimal pinned repos:   {pinned[0]}-{pinned[1]}")
        print()

    # Proof of work
    pow_data = ds.get("proof_of_work", {})
    if pow_data:
        print("  PROOF OF WORK:")
        print(f"    Portfolio signal:       {fmt_pct(pow_data.get('portfolio_signal_weight'))}")
        print(f"    5+ reviews lift:        {pow_data.get('reviews_conversion_lift_5plus', 0)}x conversion")
        print()

    # AI differentiation
    ai = ds.get("ai_differentiation", {})
    if ai:
        print("  AI DIFFERENTIATION:")
        print(f"    Wrapper viability:     {ai.get('wrapper_viability', 'unknown')}")
        moats = ai.get("moat_factors", [])
        print(f"    Moat factors:          {', '.join(str(m) for m in moats)}")
        print(f"    Vertical > horizontal: {ai.get('vertical_beats_horizontal', False)}")
        print()


def section_meta(intel: dict):
    """Print meta strategy: burnout, legal, insurance, blind spots."""
    ms = intel.get("meta_strategy", {})

    print("META STRATEGY & BLIND SPOTS")
    print("=" * 55)
    print()

    # Burnout
    burnout = ms.get("founder_burnout", {})
    if burnout:
        print("  FOUNDER BURNOUT:")
        print(f"    Prevalence:            {fmt_pct(burnout.get('prevalence'))}")
        mitigation = burnout.get("mitigation", [])
        if mitigation:
            print(f"    Mitigation:            {', '.join(str(m) for m in mitigation)}")
        print()

    # Legal
    legal = ms.get("legal_landmines", {})
    if legal:
        print("  LEGAL LANDMINES:")
        print(f"    83(b) deadline:        {legal.get('83b_election_deadline_days', 30)} days from stock grant")
        print("    FTC noncompete:        ban failed — check state-specific")
        print(f"    IP assignment:         {'CRITICAL' if legal.get('ip_assignment_critical') else 'recommended'}")
        print(f"    DE franchise tax:      {legal.get('delaware_franchise_tax_note', 'use Assumed Par Value method')}")
        print()

    # Insurance
    ins = ms.get("insurance", {})
    if ins:
        print("  INSURANCE:")
        print(f"    D&O monthly:           {fmt_currency(ins.get('d_and_o_monthly_usd'))}")
        print(f"    Cyber insurance:       {ins.get('cyber_insurance', 'recommended')}")
        print()

    # Timing
    timing = ms.get("timing_considerations", {})
    if timing:
        print("  TIMING:")
        print(f"    Grant cycle lead:      {timing.get('grant_cycle_alignment', 'N/A')}")
        print(f"    Market vs execution:   {timing.get('market_timing_vs_execution', 'N/A')}")
        print()

    # First-time founder
    ftf = ms.get("first_time_founder_gap", {})
    if ftf:
        gaps = ftf.get("knowledge_gaps", [])
        print(f"  FIRST-TIME FOUNDER GAPS: {', '.join(str(g) for g in gaps)}")
        print()

    # Special categories
    print("  SPECIAL FUNDING CATEGORIES:")
    disability = ms.get("disability_grants", {})
    if disability:
        print(f"    Disability grants:     {disability.get('competition_level', 'N/A')}")
    climate = ms.get("climate_impact_framing", {})
    if climate:
        print(f"    ESG PE market:         {fmt_currency(climate.get('esg_pe_total_usd'))}")
    eu = ms.get("eu_ai_act_as_moat", {})
    if eu:
        print(f"    EU AI Act as moat:     {eu.get('compliance_as_differentiator', False)}")
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
    parser.add_argument("--startup", action="store_true",
                        help="Show startup funding landscape (VC, seed, Series A, accelerators)")
    parser.add_argument("--funding", action="store_true",
                        help="Show non-dilutive + alternative funding (cloud credits, RBF, grants)")
    parser.add_argument("--differentiation", action="store_true",
                        help="Show differentiation signals (pitch deck, networking, proof of work)")
    parser.add_argument("--meta", action="store_true",
                        help="Show meta strategy (burnout, legal, insurance, blind spots)")
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

    if args.startup:
        section_startup(intel)
        return

    if args.funding:
        section_funding(intel)
        return

    if args.differentiation:
        section_differentiation(intel)
        return

    if args.meta:
        section_meta(intel)
        return

    # Default: full summary
    section_summary(intel)
    section_skills(intel)
    section_calendar(intel)


if __name__ == "__main__":
    main()
