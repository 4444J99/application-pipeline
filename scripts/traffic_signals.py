#!/usr/bin/env python3
"""Traffic signal monitor — detect visitor engagement across public properties.

Polls GitHub repo traffic (views, clones, referrers) and correlates with
pipeline submissions to generate follow-up signals. Any identifiable traffic
is a networking opportunity.

Data sources:
  - GitHub traffic API: 14-day views/clones/referrers per repo (requires push access)
  - Plausible analytics: portfolio site visitors and referrers (requires API key)

Signal types:
  - submission_correlated: Traffic spike on repos after submitting to a company
  - referrer_match: Traffic from a domain matching a pipeline target org
  - clone_spike: Unusual clone activity (someone evaluating the code)
  - organic_interest: Non-submission traffic from identifiable sources

Usage:
    python scripts/traffic_signals.py                    # Full scan + signal report
    python scripts/traffic_signals.py --json             # Machine-readable output
    python scripts/traffic_signals.py --save             # Save signals to signals/traffic-signals.yaml
    python scripts/traffic_signals.py --correlate        # Only show submission-correlated signals
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import (
    PIPELINE_DIR_SUBMITTED,
    SIGNALS_DIR,
    load_entries,
    parse_date,
)

# --- Config ---

PLAUSIBLE_SITE_ID = "4444j99.github.io"
PLAUSIBLE_API_KEY_PATH = Path.home() / ".config" / "plausible-api-key"
PLAUSIBLE_API_BASE = "https://plausible.io/api/v1"

# Repos to monitor for traffic (high-signal repos)
MONITORED_REPOS = [
    "4444J99/portfolio",
    "4444J99/4444J99",
    "4444J99/4444J99.github.io",
    "meta-organvm/organvm-corpvs-testamentvm",
    "meta-organvm/organvm-engine",
    "meta-organvm/stakeholder-portal",
    "meta-organvm/system-dashboard",
    "labores-profani-crux/agentic-titan",
    "ivviiviivvi/recursive-engine",
    "omni-dromenon-machina/sema-metra--alchemica-mundi",
]

# Baseline: normal daily traffic. Anything above this is a spike.
VIEWS_SPIKE_THRESHOLD = 5  # uniques per day
CLONES_SPIKE_THRESHOLD = 3  # unique cloners per day

# Company domain → org name mapping for referrer matching
DOMAIN_TO_ORG: dict[str, str] = {
    "anthropic.com": "Anthropic",
    "openai.com": "OpenAI",
    "cursor.sh": "Cursor",
    "cursor.com": "Cursor",
    "figma.com": "Figma",
    "notion.so": "Notion",
    "stripe.com": "Stripe",
    "cloudflare.com": "Cloudflare",
    "cohere.com": "Cohere",
    "coreweave.com": "CoreWeave",
    "scale.com": "Scale AI",
    "mongodb.com": "MongoDB",
    "elastic.co": "Elastic",
    "gitlab.com": "GitLab",
    "vercel.com": "Vercel",
    "netlify.com": "Netlify",
    "databricks.com": "Databricks",
    "anduril.com": "Anduril",
    "mercury.com": "Mercury",
    "ramp.com": "Ramp",
    "coinbase.com": "Coinbase",
    "sofi.com": "SoFi",
    "greenhouse.io": "_ATS_",  # generic ATS, not a company
    "lever.co": "_ATS_",
    "ashbyhq.com": "_ATS_",
    "linkedin.com": "_LINKEDIN_",
    "google.com": "_SEARCH_",
}

SIGNALS_PATH = SIGNALS_DIR / "traffic-signals.yaml"

# --- Data structures ---


@dataclass
class TrafficDay:
    date: str
    views: int
    uniques: int


@dataclass
class RepoTraffic:
    repo: str
    total_views: int
    total_uniques: int
    daily: list[TrafficDay]
    clones_total: int
    clones_uniques: int
    referrers: list[dict]  # [{referrer, count, uniques}]


@dataclass
class TrafficSignal:
    signal_type: str  # submission_correlated, referrer_match, clone_spike, organic_interest
    repo: str
    date: str
    description: str
    org: str  # matched organization or empty
    entry_id: str  # matched pipeline entry or empty
    strength: str  # high, medium, low
    referrer: str  # source domain if known
    metric_value: int  # the actual count that triggered the signal


# --- GitHub API ---


def _gh_api(endpoint: str) -> dict | list | None:
    """Call GitHub API via gh CLI. Returns parsed JSON or None on failure."""
    try:
        result = subprocess.run(
            ["gh", "api", endpoint],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode != 0:
            return None
        return json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
        return None


def fetch_repo_traffic(repo: str) -> RepoTraffic | None:
    """Fetch 14-day traffic data for a single repo."""
    views_data = _gh_api(f"repos/{repo}/traffic/views")
    clones_data = _gh_api(f"repos/{repo}/traffic/clones")
    referrers_data = _gh_api(f"repos/{repo}/traffic/popular/referrers")

    if views_data is None:
        return None

    daily = []
    for day in views_data.get("views", []):
        daily.append(TrafficDay(
            date=day["timestamp"][:10],
            views=day["count"],
            uniques=day["uniques"],
        ))

    return RepoTraffic(
        repo=repo,
        total_views=views_data.get("count", 0),
        total_uniques=views_data.get("uniques", 0),
        daily=daily,
        clones_total=clones_data.get("count", 0) if clones_data else 0,
        clones_uniques=clones_data.get("uniques", 0) if clones_data else 0,
        referrers=referrers_data if isinstance(referrers_data, list) else [],
    )


# --- Plausible API ---


def _get_plausible_key() -> str | None:
    """Read Plausible API key from config file."""
    if PLAUSIBLE_API_KEY_PATH.exists():
        return PLAUSIBLE_API_KEY_PATH.read_text().strip()
    import os
    return os.environ.get("PLAUSIBLE_API_KEY")


def _plausible_api(endpoint: str, params: dict) -> dict | None:
    """Call Plausible Stats API."""
    from urllib.parse import urlencode
    from urllib.request import Request, urlopen

    key = _get_plausible_key()
    if not key:
        return None
    params["site_id"] = PLAUSIBLE_SITE_ID
    url = f"{PLAUSIBLE_API_BASE}/{endpoint}?{urlencode(params)}"
    req = Request(url, headers={"Authorization": f"Bearer {key}"})
    try:
        with urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception:
        return None


def fetch_plausible_referrers(period: str = "30d") -> list[dict]:
    """Fetch top referrer sources from Plausible.

    Returns list of {source, visitors} dicts.
    """
    data = _plausible_api("stats/breakdown", {"period": period, "property": "visit:source"})
    if data and "results" in data:
        return data["results"]
    return []


def fetch_plausible_pages(period: str = "30d") -> list[dict]:
    """Fetch top pages from Plausible."""
    data = _plausible_api("stats/breakdown", {"period": period, "property": "event:page", "limit": "20"})
    if data and "results" in data:
        return data["results"]
    return []


def detect_plausible_signals(entries: list[dict]) -> list[TrafficSignal]:
    """Detect signals from Plausible analytics — referrer domains visiting the portfolio."""
    referrers = fetch_plausible_referrers()
    if not referrers:
        return []

    signals = []
    today = date.today().isoformat()

    for ref in referrers:
        source = ref.get("source", "")
        visitors = ref.get("visitors", 0)
        if not source or visitors < 1:
            continue

        org = _match_referrer_to_org(source)

        if org and not org.startswith("_"):
            entry_id = _find_entry_for_org(org, entries)
            signal_type = "submission_correlated" if entry_id else "organic_interest"
            strength = "high" if entry_id else ("medium" if visitors >= 3 else "low")
            signals.append(TrafficSignal(
                signal_type=signal_type,
                repo="portfolio (plausible)",
                date=today,
                description=f"{org} ({source}) sent {visitors} visitors to portfolio (30d)",
                org=org,
                entry_id=entry_id,
                strength=strength,
                referrer=source,
                metric_value=visitors,
            ))
        elif org == "_LINKEDIN_":
            signals.append(TrafficSignal(
                signal_type="organic_interest",
                repo="portfolio (plausible)",
                date=today,
                description=f"LinkedIn sent {visitors} visitors to portfolio (30d)",
                org="",
                entry_id="",
                strength="high" if visitors >= 5 else "medium",
                referrer=source,
                metric_value=visitors,
            ))
        elif not org and visitors >= 2:
            # Unknown source with meaningful traffic — networking opportunity
            signals.append(TrafficSignal(
                signal_type="organic_interest",
                repo="portfolio (plausible)",
                date=today,
                description=f"{source} sent {visitors} visitors to portfolio (30d)",
                org="",
                entry_id="",
                strength="medium" if visitors >= 5 else "low",
                referrer=source,
                metric_value=visitors,
            ))

    return signals


def fetch_all_traffic() -> list[RepoTraffic]:
    """Fetch traffic for all monitored repos."""
    results = []
    for repo in MONITORED_REPOS:
        traffic = fetch_repo_traffic(repo)
        if traffic:
            results.append(traffic)
    return results


# --- Signal Detection ---


def _get_submitted_entries() -> list[dict]:
    """Load submitted entries with their submission dates and organizations."""
    return load_entries(dirs=[PIPELINE_DIR_SUBMITTED])


def _match_referrer_to_org(referrer: str) -> str:
    """Match a referrer domain to an organization name."""
    referrer_lower = referrer.lower()
    for domain, org in DOMAIN_TO_ORG.items():
        if domain in referrer_lower:
            return org
    return ""


def _find_entry_for_org(org: str, entries: list[dict]) -> str:
    """Find a pipeline entry matching an organization."""
    for entry in entries:
        entry_org = (entry.get("target") or {}).get("organization", "")
        if entry_org.lower() == org.lower():
            return entry.get("id", "")
    return ""


def detect_referrer_signals(traffic_list: list[RepoTraffic], entries: list[dict]) -> list[TrafficSignal]:
    """Detect signals from referrer data — which domains are sending traffic."""
    signals = []
    today = date.today().isoformat()

    for traffic in traffic_list:
        for ref in traffic.referrers:
            referrer = ref.get("referrer", "")
            count = ref.get("count", 0)
            uniques = ref.get("uniques", 0)

            org = _match_referrer_to_org(referrer)
            if not org or org.startswith("_"):
                # Still record ATS and LinkedIn as networking signals
                if org == "_ATS_" and count >= 2:
                    signals.append(TrafficSignal(
                        signal_type="organic_interest",
                        repo=traffic.repo,
                        date=today,
                        description=f"ATS platform ({referrer}) sent {count} visits to {traffic.repo}",
                        org="",
                        entry_id="",
                        strength="medium" if count >= 5 else "low",
                        referrer=referrer,
                        metric_value=count,
                    ))
                elif org == "_LINKEDIN_" and count >= 1:
                    signals.append(TrafficSignal(
                        signal_type="organic_interest",
                        repo=traffic.repo,
                        date=today,
                        description=f"LinkedIn sent {count} visits to {traffic.repo}",
                        org="",
                        entry_id="",
                        strength="high" if count >= 3 else "medium",
                        referrer=referrer,
                        metric_value=count,
                    ))
                continue

            # Known company referrer
            entry_id = _find_entry_for_org(org, entries)
            signal_type = "submission_correlated" if entry_id else "organic_interest"
            strength = "high" if entry_id and uniques >= 2 else "medium" if entry_id else "low"

            signals.append(TrafficSignal(
                signal_type=signal_type,
                repo=traffic.repo,
                date=today,
                description=f"{org} ({referrer}) sent {count} visits ({uniques} unique) to {traffic.repo}",
                org=org,
                entry_id=entry_id,
                strength=strength,
                referrer=referrer,
                metric_value=count,
            ))

    return signals


def detect_spike_signals(traffic_list: list[RepoTraffic], entries: list[dict]) -> list[TrafficSignal]:
    """Detect traffic spikes that correlate with submission timing."""
    signals = []
    submitted_dates = {}
    for entry in entries:
        timeline = entry.get("timeline", {})
        if isinstance(timeline, dict):
            sub_date = parse_date(timeline.get("submitted"))
            if sub_date:
                org = (entry.get("target") or {}).get("organization", "")
                submitted_dates[entry.get("id", "")] = (sub_date, org)

    for traffic in traffic_list:
        for day in traffic.daily:
            if day.uniques < VIEWS_SPIKE_THRESHOLD:
                continue

            day_date = parse_date(day.date)
            if not day_date:
                continue

            # Check if this spike is within 7 days of a submission
            correlated_entry = ""
            correlated_org = ""
            for entry_id, (sub_date, org) in submitted_dates.items():
                days_after = (day_date - sub_date).days
                if 0 <= days_after <= 7:
                    correlated_entry = entry_id
                    correlated_org = org
                    break

            if correlated_entry:
                signals.append(TrafficSignal(
                    signal_type="submission_correlated",
                    repo=traffic.repo,
                    date=day.date,
                    description=f"Traffic spike ({day.uniques} uniques) on {traffic.repo} "
                                f"{(day_date - parse_date(str(submitted_dates[correlated_entry][0]))).days}d after submitting to {correlated_org}",
                    org=correlated_org,
                    entry_id=correlated_entry,
                    strength="high" if day.uniques >= 10 else "medium",
                    referrer="",
                    metric_value=day.uniques,
                ))
            elif day.uniques >= VIEWS_SPIKE_THRESHOLD * 2:
                # Big spike not correlated with any submission — organic interest
                signals.append(TrafficSignal(
                    signal_type="organic_interest",
                    repo=traffic.repo,
                    date=day.date,
                    description=f"Unusual traffic ({day.uniques} uniques) on {traffic.repo}",
                    org="",
                    entry_id="",
                    strength="medium",
                    referrer="",
                    metric_value=day.uniques,
                ))

    return signals


def _estimate_ci_clones(repo: str) -> int:
    """Estimate how many unique cloners are CI/Actions (not human).

    Each GitHub Actions run clones from a unique IP. We subtract the
    estimated CI clone count to avoid false positives.
    """
    data = _gh_api(f"repos/{repo}/actions/runs?per_page=1")
    if data and isinstance(data, dict):
        return min(data.get("total_count", 0) // 14, 50)  # rough daily average, capped
    return 0


def detect_clone_signals(traffic_list: list[RepoTraffic]) -> list[TrafficSignal]:
    """Detect unusual clone activity — someone evaluating the code.

    Subtracts estimated CI/Actions clones to avoid self-induced false positives.
    GitHub Actions runners use unique IPs, inflating the "unique cloners" count.
    """
    signals = []
    today = date.today().isoformat()

    for traffic in traffic_list:
        ci_estimate = _estimate_ci_clones(traffic.repo)
        adjusted_uniques = max(0, traffic.clones_uniques - ci_estimate)

        if adjusted_uniques >= CLONES_SPIKE_THRESHOLD:
            signals.append(TrafficSignal(
                signal_type="clone_spike",
                repo=traffic.repo,
                date=today,
                description=f"{adjusted_uniques} unique cloners on {traffic.repo} in last 14d "
                            f"(raw: {traffic.clones_uniques}, CI estimate: ~{ci_estimate})",
                org="",
                entry_id="",
                strength="high" if adjusted_uniques >= 20 else "medium",
                referrer="",
                metric_value=adjusted_uniques,
            ))

    return signals


# --- Output ---


def format_report(signals: list[TrafficSignal], traffic_list: list[RepoTraffic]) -> str:
    """Format human-readable signal report."""
    lines = []
    today = date.today()
    lines.append(f"TRAFFIC SIGNALS — {today.strftime('%A, %B %d, %Y')}")
    lines.append("=" * 60)

    # Summary
    lines.append(f"\nRepos monitored: {len(traffic_list)}")
    total_views = sum(t.total_views for t in traffic_list)
    total_uniques = sum(t.total_uniques for t in traffic_list)
    total_clones = sum(t.clones_uniques for t in traffic_list)
    lines.append(f"14-day totals: {total_views} views ({total_uniques} unique), {total_clones} unique cloners")

    if not signals:
        lines.append("\nNo actionable signals detected.")
        return "\n".join(lines)

    # Group by type
    by_type: dict[str, list[TrafficSignal]] = {}
    for s in signals:
        by_type.setdefault(s.signal_type, []).append(s)

    type_labels = {
        "submission_correlated": "SUBMISSION CORRELATED (follow up NOW)",
        "referrer_match": "COMPANY REFERRER MATCH",
        "clone_spike": "CODE EVALUATION (clone spike)",
        "organic_interest": "ORGANIC INTEREST (networking opportunity)",
    }

    for stype, label in type_labels.items():
        group = by_type.get(stype, [])
        if not group:
            continue
        # Sort by strength
        group.sort(key=lambda s: {"high": 0, "medium": 1, "low": 2}.get(s.strength, 3))
        lines.append(f"\n{label} ({len(group)}):")
        for s in group:
            icon = {"high": "!!!", "medium": " >>", "low": "   "}.get(s.strength, "   ")
            lines.append(f"  {icon} [{s.strength.upper():6s}] {s.description}")
            if s.entry_id:
                lines.append(f"             → Entry: {s.entry_id}")
            if s.org and not s.entry_id:
                lines.append(f"             → Org: {s.org} (no pipeline entry — create one?)")

    # Networking opportunities
    all_referrers = set()
    for t in traffic_list:
        for ref in t.referrers:
            all_referrers.add(ref.get("referrer", ""))
    if all_referrers:
        lines.append(f"\nAll referrer domains: {', '.join(sorted(all_referrers))}")

    return "\n".join(lines)


def save_signals(signals: list[TrafficSignal]) -> None:
    """Append signals to the traffic signals log."""
    SIGNALS_DIR.mkdir(parents=True, exist_ok=True)
    existing = []
    if SIGNALS_PATH.exists():
        existing = yaml.safe_load(SIGNALS_PATH.read_text()) or []
        if not isinstance(existing, list):
            existing = []

    new_entries = [asdict(s) for s in signals]
    existing.extend(new_entries)

    # Keep last 90 days only
    cutoff = (date.today() - timedelta(days=90)).isoformat()
    existing = [e for e in existing if e.get("date", "") >= cutoff]

    SIGNALS_PATH.write_text(yaml.dump(existing, default_flow_style=False, sort_keys=False))


# --- Main ---


def run_scan(save: bool = False, correlate_only: bool = False, as_json: bool = False) -> list[TrafficSignal]:
    """Run full traffic scan and return signals."""
    print("Fetching traffic data from GitHub...", file=sys.stderr)
    traffic_list = fetch_all_traffic()
    print(f"  {len(traffic_list)} repos responded", file=sys.stderr)

    entries = _get_submitted_entries()

    # Detect signals from all sources
    signals = []
    signals.extend(detect_referrer_signals(traffic_list, entries))
    signals.extend(detect_spike_signals(traffic_list, entries))
    signals.extend(detect_clone_signals(traffic_list))

    # Plausible analytics (portfolio site)
    print("Fetching Plausible analytics...", file=sys.stderr)
    plausible_signals = detect_plausible_signals(entries)
    if plausible_signals:
        print(f"  {len(plausible_signals)} Plausible signals", file=sys.stderr)
    else:
        print("  No Plausible data (key missing or no traffic yet)", file=sys.stderr)
    signals.extend(plausible_signals)

    if correlate_only:
        signals = [s for s in signals if s.signal_type == "submission_correlated"]

    # Deduplicate by (type, repo, org, date)
    seen = set()
    deduped = []
    for s in signals:
        key = (s.signal_type, s.repo, s.org, s.date)
        if key not in seen:
            seen.add(key)
            deduped.append(s)
    signals = sorted(deduped, key=lambda s: ({"high": 0, "medium": 1, "low": 2}.get(s.strength, 3), s.date))

    if as_json:
        print(json.dumps([asdict(s) for s in signals], indent=2))
    else:
        print(format_report(signals, traffic_list))

    if save and signals:
        save_signals(signals)
        print(f"\nSaved {len(signals)} signals to {SIGNALS_PATH}", file=sys.stderr)

    return signals


def main() -> int:
    parser = argparse.ArgumentParser(description="Traffic signal monitor for pipeline follow-ups")
    parser.add_argument("--save", action="store_true", help="Save signals to signals/traffic-signals.yaml")
    parser.add_argument("--correlate", action="store_true", help="Only show submission-correlated signals")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    signals = run_scan(save=args.save, correlate_only=args.correlate, as_json=args.json)
    return 0 if signals else 1


if __name__ == "__main__":
    sys.exit(main())
