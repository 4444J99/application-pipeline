#!/usr/bin/env python3
"""Enrich company prestige scores from GitHub signals.

Augments the static HIGH_PRESTIGE dict in score_constants.py with
dynamic signals: GitHub org star counts, public repo counts, and
employee counts (from GitHub bio patterns). Produces a merged prestige
map that includes both manually curated and auto-discovered companies.

Surface 4 of the ecosystem integration spec.

Usage:
    python scripts/enrich_prestige.py                # Show enriched prestige
    python scripts/enrich_prestige.py --update       # Write enriched scores to cache
    python scripts/enrich_prestige.py --json         # Machine-readable output
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parent))

from score_constants import HIGH_PRESTIGE

REPO_ROOT = Path(__file__).resolve().parent.parent
CACHE_PATH = REPO_ROOT / "strategy" / "prestige-enrichment-cache.json"

# GitHub orgs for companies we know about
GITHUB_ORGS: dict[str, str] = {
    "Anthropic": "anthropics",
    "OpenAI": "openai",
    "Google": "google",
    "Stripe": "stripe",
    "Vercel": "vercel",
    "Cloudflare": "cloudflare",
    "Cursor": "getcursor",
    "Perplexity": "pplx-ai",
    "Replit": "replit",
    "Figma": "figma",
    "Notion": "makenotion",
    "Linear": "linearapp",
    "Hugging Face": "huggingface",
    "Cohere": "cohere-ai",
    "Together AI": "togethercomputer",
    "Scale AI": "scaleapi",
    "Runway": "runwayml",
    "ElevenLabs": "elevenlabs",
    "Mistral": "mistralai",
    "Netlify": "netlify",
    "Supabase": "supabase",
    "Neon": "neondatabase",
    "Grafana": "grafana",
    "PostHog": "PostHog",
    "Sentry": "getsentry",
}

GITHUB_API = "https://api.github.com"
RATE_DELAY = 1.5  # seconds between API calls


def _fetch_github_org(org: str) -> dict | None:
    """Fetch basic org info from GitHub API (unauthenticated)."""
    url = f"{GITHUB_API}/orgs/{org}"
    req = Request(url, headers={"Accept": "application/vnd.github+json"})
    try:
        with urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except (URLError, json.JSONDecodeError):
        return None


def _stars_to_prestige_boost(public_repos: int, followers: int) -> int:
    """Convert GitHub signals to a prestige score adjustment (0-2)."""
    # Large open-source presence = higher developer brand prestige
    if public_repos > 500 and followers > 10000:
        return 2
    if public_repos > 100 and followers > 2000:
        return 1
    return 0


def enrich_prestige(
    fetch_github: bool = True,
) -> dict[str, dict]:
    """Build enriched prestige map from static + dynamic signals.

    Returns {company_name: {score, source, github_repos, github_followers}}.
    """
    result: dict[str, dict] = {}

    # Start with static prestige
    for company, score in HIGH_PRESTIGE.items():
        result[company] = {
            "score": score,
            "source": "manual",
            "github_repos": None,
            "github_followers": None,
        }

    if not fetch_github:
        return result

    # Enrich with GitHub signals
    for company, org in GITHUB_ORGS.items():
        data = _fetch_github_org(org)
        if data is None:
            continue

        public_repos = data.get("public_repos", 0)
        followers = data.get("followers", 0)
        boost = _stars_to_prestige_boost(public_repos, followers)

        if company in result:
            result[company]["github_repos"] = public_repos
            result[company]["github_followers"] = followers
            if boost > 0:
                result[company]["score"] = min(10, result[company]["score"] + boost)
                result[company]["source"] = "manual+github"
        else:
            # New company not in static list
            base_score = 5 + boost
            result[company] = {
                "score": min(10, base_score),
                "source": "github",
                "github_repos": public_repos,
                "github_followers": followers,
            }

        time.sleep(RATE_DELAY)

    return result


def write_cache(data: dict, path: Path = CACHE_PATH) -> None:
    """Write enrichment cache."""
    from datetime import datetime, timezone
    cache = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "companies": data,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        json.dump(cache, f, indent=2)
        f.write("\n")


def load_cache(path: Path = CACHE_PATH) -> dict | None:
    """Load existing cache if fresh (< 7 days)."""
    if not path.is_file():
        return None
    try:
        from datetime import datetime, timedelta, timezone
        with path.open() as f:
            cache = json.load(f)
        generated = datetime.fromisoformat(cache.get("generated", ""))
        if (datetime.now(timezone.utc) - generated) > timedelta(days=7):
            return None
        return cache.get("companies")
    except Exception:
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Enrich company prestige from GitHub")
    parser.add_argument("--update", action="store_true", help="Fetch from GitHub and update cache")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--no-fetch", action="store_true", help="Use cache only, no API calls")
    args = parser.parse_args()

    if args.update:
        print("Fetching GitHub org data...")
        data = enrich_prestige(fetch_github=True)
        write_cache(data)
        print(f"  Enriched {len(data)} companies → {CACHE_PATH}")
    elif args.no_fetch:
        cached = load_cache()
        if cached:
            data = cached
            print(f"Using cached data ({len(data)} companies)")
        else:
            data = enrich_prestige(fetch_github=False)
            print("No fresh cache — showing static prestige only")
    else:
        cached = load_cache()
        if cached:
            data = cached
        else:
            data = enrich_prestige(fetch_github=False)

    if args.json:
        print(json.dumps(data, indent=2))
        return 0

    # Display sorted by score
    sorted_companies = sorted(data.items(), key=lambda x: -x[1]["score"])
    print(f"\n{'Company':<30} {'Score':>5}  {'Source':<15}  {'GH Repos':>8}  {'GH Followers':>12}")
    print("-" * 85)
    for company, info in sorted_companies[:40]:
        repos = info.get("github_repos") or ""
        followers = info.get("github_followers") or ""
        print(f"  {company:<28} {info['score']:>5}  {info['source']:<15}  {str(repos):>8}  {str(followers):>12}")

    if len(sorted_companies) > 40:
        print(f"  ... and {len(sorted_companies) - 40} more")

    return 0


if __name__ == "__main__":
    sys.exit(main())
