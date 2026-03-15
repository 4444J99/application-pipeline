#!/usr/bin/env python3
"""Skill-based job discovery across free public APIs.

Searches Remotive, Himalayas, and The Muse by keywords mapped to each of
the five identity positions.  Complements the company-locked source_jobs.py
with open-ended skill-based search, surfacing roles the ATS board polling
cannot find.

Usage:
    python scripts/discover_jobs.py                              # All positions, dry-run
    python scripts/discover_jobs.py --position creative-technologist  # Single position
    python scripts/discover_jobs.py --yes                        # Create entries in research_pool/
    python scripts/discover_jobs.py --limit 20 --min-score 6.0   # Filters
    python scripts/discover_jobs.py --apis remotive,himalayas     # Select APIs
"""

import argparse
import json
import sys
import time
from datetime import UTC, date, datetime
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ingest_top_roles import pre_score
from pipeline_lib import (
    ALL_PIPELINE_DIRS_WITH_POOL,
    http_request_with_retry,
    load_entries,
)
from source_jobs import (
    _slugify,
    create_pipeline_entry,
    deduplicate,
    write_pipeline_entry,
)

QUERIES_FILE = Path(__file__).resolve().parent / ".discovery-queries.yaml"
STATS_FILE = Path(__file__).resolve().parent / ".discovery-stats.yaml"

VALID_POSITIONS = [
    "independent-engineer",
    "systems-artist",
    "educator",
    "creative-technologist",
    "community-practitioner",
    "documentation-engineer",
    "governance-architect",
    "platform-orchestrator",
    "founder-operator",
]

# Default rate delay between requests (seconds)
DEFAULT_RATE_DELAY = 2.0
DEFAULT_MIN_SCORE = 5.0
DEFAULT_LIMIT = 50

# Maps identity position to the pipeline identity_position value
POSITION_MAP = {
    "independent-engineer": "independent-engineer",
    "systems-artist": "systems-artist",
    "educator": "educator",
    "creative-technologist": "creative-technologist",
    "community-practitioner": "community-practitioner",
}


# --- Query config loading ---


def load_queries() -> dict:
    """Load search configuration from .discovery-queries.yaml."""
    if not QUERIES_FILE.exists():
        print(f"Config not found: {QUERIES_FILE}", file=sys.stderr)
        print("Create it with position query sets.", file=sys.stderr)
        sys.exit(1)
    with open(QUERIES_FILE) as f:
        return yaml.safe_load(f) or {}


# --- API adapters ---


def fetch_remotive(search: str, category: str | None = None) -> list[dict]:
    """Search Remotive API for jobs matching a keyword.

    Remotive's search parameter only supports single-word queries.
    For multi-word queries we search the most distinctive word and
    post-filter results by the full phrase in the title/description.

    API docs: https://remotive.com/api/remote-jobs
    """
    # Remotive search only works with single words — pick the longest
    # (most distinctive) word from the query for the API call, then
    # post-filter against the full phrase.
    words = search.strip().split()
    api_term = max(words, key=len) if words else search
    full_phrase = search.lower()

    url = f"https://remotive.com/api/remote-jobs?search={_url_encode(api_term)}"
    if category:
        url += f"&category={_url_encode(category)}"
    url += "&limit=50"

    raw = http_request_with_retry(
        url,
        headers={"User-Agent": "application-pipeline/1.0"},
        timeout=15,
    )
    if not raw:
        return []

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []

    jobs = data.get("jobs", [])
    results = []
    for job in jobs:
        # Post-filter: title or description must contain full phrase
        title = job.get("title", "")
        desc = job.get("description", "")
        searchable = f"{title} {desc}".lower()
        if full_phrase not in searchable:
            continue

        pub_date = job.get("publication_date", "")
        posting_date = pub_date[:10] if pub_date else None
        company = job.get("company_name", "")
        results.append({
            "title": title,
            "id": str(job.get("id", "")),
            "url": job.get("url", ""),
            "location": job.get("candidate_required_location", ""),
            "company": _slugify(company),
            "company_display": company,
            "portal": "remotive",
            "company_url": "",
            "posting_date": posting_date,
        })
    return results


def fetch_himalayas(keywords: str) -> list[dict]:
    """Search Himalayas API for jobs matching keywords.

    API docs: https://himalayas.app/api
    """
    url = f"https://himalayas.app/jobs/api?q={_url_encode(keywords)}&limit=50"

    raw = http_request_with_retry(
        url,
        headers={"User-Agent": "application-pipeline/1.0"},
        timeout=15,
    )
    if not raw:
        return []

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []

    jobs = data.get("jobs", [])
    results = []
    for job in jobs:
        # pubDate is a Unix timestamp (seconds), not an ISO string
        pub_ts = job.get("pubDate")
        if isinstance(pub_ts, (int, float)) and pub_ts > 0:
            posting_date = datetime.fromtimestamp(pub_ts, tz=UTC).date().isoformat()
        else:
            posting_date = None

        company = job.get("companyName", "")
        title = _decode_html_entities(job.get("title", ""))
        locations = job.get("locationRestrictions", [])
        loc_str = ", ".join(locations) if isinstance(locations, list) else ""
        results.append({
            "title": title,
            "id": str(job.get("guid", "")),
            "url": job.get("applicationLink") or job.get("guid", ""),
            "location": loc_str,
            "company": _slugify(company),
            "company_display": company,
            "portal": "himalayas",
            "company_url": "",
            "posting_date": posting_date,
        })
    return results


def fetch_themuse(category: str, page: int = 0) -> list[dict]:
    """Fetch jobs from The Muse API by category.

    API docs: https://www.themuse.com/developers/api/v2
    """
    url = (
        f"https://www.themuse.com/api/public/jobs"
        f"?category={_url_encode(category)}&page={page}"
    )

    raw = http_request_with_retry(
        url,
        headers={"User-Agent": "application-pipeline/1.0"},
        timeout=15,
    )
    if not raw:
        return []

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []

    jobs = data.get("results", [])
    results = []
    for job in jobs:
        pub_date = job.get("publication_date", "")
        posting_date = pub_date[:10] if pub_date else None
        company_data = job.get("company", {})
        company = company_data.get("name", "") if isinstance(company_data, dict) else ""
        locations = job.get("locations", [])
        loc_str = ", ".join(loc.get("name", "") for loc in locations if isinstance(loc, dict))
        refs = job.get("refs", {})
        landing_page = refs.get("landing_page", "") if isinstance(refs, dict) else ""
        results.append({
            "title": job.get("name", ""),
            "id": str(job.get("id", "")),
            "url": landing_page,
            "location": loc_str,
            "company": _slugify(company),
            "company_display": company,
            "portal": "themuse",
            "company_url": "",
            "posting_date": posting_date,
        })
    return results


def _decode_html_entities(text: str) -> str:
    """Decode HTML entities like &#x2f; in API responses."""
    from html import unescape
    return unescape(text)


def _url_encode(text: str) -> str:
    """Percent-encode a query parameter value using %20 for spaces.

    Several APIs (Remotive, The Muse) don't interpret '+' as space,
    so we use quote() rather than quote_plus().
    """
    from urllib.parse import quote
    return quote(text)


# --- Normalization and dedup ---


def normalize_job(job: dict, source_api: str, position: str) -> dict:
    """Ensure consistent shape and tag with source metadata."""
    job["source_api"] = source_api
    job["identity_position"] = position
    if not job.get("portal"):
        job["portal"] = source_api
    return job


def cross_position_dedup(results: list[dict]) -> list[dict]:
    """Deduplicate across positions — keep highest-scored per company+title."""
    seen: dict[str, dict] = {}
    for job in results:
        key = f"{job.get('company', '').lower()}|{job.get('title', '').lower()}"
        if key not in seen or job.get("_score", 0) > seen[key].get("_score", 0):
            seen[key] = job
    return list(seen.values())


# --- Discovery orchestrator ---


def _title_matches_any_query(title: str, queries: list[str]) -> bool:
    """Check if a job title contains any word from any query string.

    Uses individual words from multi-word queries so "developer experience"
    matches titles containing "developer" or "experience".
    """
    title_lower = title.lower()
    for query in queries:
        words = query.lower().split()
        if any(w in title_lower for w in words if len(w) > 3):
            return True
    return False


def discover_for_position(
    position: str,
    cfg: dict,
    enabled_apis: set[str],
    rate_delay: float,
) -> list[dict]:
    """Run all queries for one identity position across enabled APIs."""
    queries = cfg.get("queries", [])
    remotive_cats = cfg.get("remotive_categories", [])
    themuse_cats = cfg.get("themuse_categories", [])
    results: list[dict] = []

    for query in queries:
        # Remotive (already post-filtered in fetch_remotive)
        if "remotive" in enabled_apis:
            for cat in (remotive_cats or [None]):
                jobs = fetch_remotive(query, category=cat)
                for job in jobs:
                    normalize_job(job, "remotive", position)
                results.extend(jobs)
                time.sleep(rate_delay)

        # Himalayas — post-filter by title relevance since its search
        # returns many unrelated results
        if "himalayas" in enabled_apis:
            jobs = fetch_himalayas(query)
            relevant = [j for j in jobs if _title_matches_any_query(j["title"], [query])]
            for job in relevant:
                normalize_job(job, "himalayas", position)
            results.extend(relevant)
            time.sleep(rate_delay)

    # The Muse: category-based — post-filter by title relevance to
    # the position's queries since categories are very broad
    if "themuse" in enabled_apis:
        for cat in themuse_cats:
            jobs = fetch_themuse(cat)
            relevant = [j for j in jobs if _title_matches_any_query(j["title"], queries)]
            for job in relevant:
                normalize_job(job, "themuse", position)
            results.extend(relevant)
            time.sleep(rate_delay)

    return results


def _get_existing_ids() -> set[str]:
    """Get IDs and application URLs of existing pipeline entries."""
    entries = load_entries(dirs=ALL_PIPELINE_DIRS_WITH_POOL)
    ids = set()
    for e in entries:
        if e.get("id"):
            ids.add(e["id"])
        target = e.get("target", {})
        if isinstance(target, dict) and target.get("application_url"):
            ids.add(target["application_url"])
    return ids


def create_discovery_entry(job: dict) -> tuple[str, dict]:
    """Create a pipeline entry dict tailored for discovery results.

    Wraps source_jobs.create_pipeline_entry and patches the identity
    position and source fields.
    """
    entry_id, entry = create_pipeline_entry(job)
    position = job.get("identity_position", "independent-engineer")
    entry["fit"]["identity_position"] = position
    entry["source"] = "discover_jobs.py"
    entry["tags"] = ["auto-sourced", "discovery", f"pos:{position}"]

    # For non-engineer positions, clear the default engineer resume
    if position != "independent-engineer":
        entry["submission"]["materials_attached"] = []

    return entry_id, entry


# --- Display ---


def display_results(results: list[dict], dry_run: bool = True):
    """Print discovered jobs with scores and URLs."""
    if not results:
        print("\nNo new jobs discovered.")
        return

    # Group by position
    by_position: dict[str, list[dict]] = {}
    for job in results:
        pos = job.get("identity_position", "unknown")
        by_position.setdefault(pos, []).append(job)

    for pos in VALID_POSITIONS:
        jobs = by_position.get(pos, [])
        if not jobs:
            continue
        print(f"\n--- {pos} ({len(jobs)} jobs) ---")
        for job in jobs:
            score = job.get("_score", 0)
            api = job.get("source_api", "?")
            prefix = "[dry-run] " if dry_run else "  + "
            print(f"  {prefix}{score:.1f}  {job['company_display']} — {job['title']} [{api}]")
            print(f"         {job.get('location', 'Remote')}  |  {job.get('url', 'N/A')}")


# --- CLI ---


def main():
    parser = argparse.ArgumentParser(
        description="Skill-based job discovery across free public APIs"
    )
    parser.add_argument(
        "--position", choices=VALID_POSITIONS,
        help="Search for a single identity position only",
    )
    parser.add_argument(
        "--yes", action="store_true",
        help="Create pipeline entries in research_pool/",
    )
    parser.add_argument(
        "--dry-run", action="store_true", default=False,
        help="Preview results without writing (default behavior)",
    )
    parser.add_argument(
        "--limit", type=int, default=DEFAULT_LIMIT,
        help=f"Max entries to create (default: {DEFAULT_LIMIT})",
    )
    parser.add_argument(
        "--min-score", type=float, default=DEFAULT_MIN_SCORE,
        help=f"Minimum pre-score threshold (default: {DEFAULT_MIN_SCORE})",
    )
    parser.add_argument(
        "--apis", type=str, default="",
        help="Comma-separated list of APIs to query (default: all enabled in config)",
    )
    args = parser.parse_args()

    # Default to dry-run if --yes not given
    is_write = args.yes and not args.dry_run

    config = load_queries()
    rate_delay = config.get("rate_delay", DEFAULT_RATE_DELAY)
    api_config = config.get("apis", {})
    positions_config = config.get("positions", {})

    # Determine enabled APIs
    if args.apis:
        enabled_apis = set(a.strip() for a in args.apis.split(","))
    else:
        enabled_apis = {api for api, on in api_config.items() if on}

    # Determine positions to search
    if args.position:
        search_positions = [args.position]
    else:
        search_positions = [p for p in VALID_POSITIONS if p in positions_config]

    print(f"Discovery search — APIs: {', '.join(sorted(enabled_apis))}")
    print(f"Positions: {', '.join(search_positions)}")
    print(f"Min score: {args.min_score}  |  Limit: {args.limit}")

    # Fetch existing for dedup
    existing_ids = _get_existing_ids()

    # Run discovery per position
    all_results: list[dict] = []
    for pos in search_positions:
        pos_cfg = positions_config.get(pos, {})
        if not pos_cfg:
            print(f"\n  [skip] No config for position: {pos}")
            continue
        print(f"\nSearching for {pos}...")
        results = discover_for_position(pos, pos_cfg, enabled_apis, rate_delay)
        print(f"  Raw results: {len(results)}")
        all_results.extend(results)

    if not all_results:
        print("\nNo results from any API.")
        return

    # Score all results
    for job in all_results:
        job["_score"] = pre_score(job)

    # Filter by min score
    scored = [j for j in all_results if j.get("_score", 0) >= args.min_score]
    print(f"\nAbove min score ({args.min_score}): {len(scored)}")

    # Cross-position dedup (keep highest score per company+title)
    deduped = cross_position_dedup(scored)
    print(f"After cross-position dedup: {len(deduped)}")

    # Dedup against existing pipeline
    new_jobs = deduplicate(deduped, existing_ids)
    print(f"After pipeline dedup: {len(new_jobs)}")

    # Sort by score descending
    new_jobs.sort(key=lambda j: j.get("_score", 0), reverse=True)

    # Apply limit
    if args.limit and len(new_jobs) > args.limit:
        new_jobs = new_jobs[:args.limit]

    print(f"\n{'=' * 60}")
    print(f"Discovered: {len(all_results)} raw → {len(new_jobs)} new")
    print(f"{'=' * 60}")

    if not new_jobs:
        print("\nNo new jobs to add.")
        _save_stats(len(all_results), 0, search_positions, enabled_apis)
        return

    display_results(new_jobs, dry_run=not is_write)

    # Create entries
    created = []
    if is_write:
        for job in new_jobs:
            entry_id, entry = create_discovery_entry(job)
            write_pipeline_entry(entry_id, entry)
            created.append(entry_id)

        print(f"\n{'=' * 60}")
        print(f"Created {len(created)} entries in pipeline/research_pool/")
        print("\nNext steps:")
        print("  python scripts/score.py --all          # Score new entries")
        print("  python scripts/advance.py --report     # Check advancement")
    else:
        print(f"\nWould create {len(new_jobs)} entries (run with --yes to create)")

    _save_stats(len(all_results), len(created) or len(new_jobs), search_positions, enabled_apis)


def _save_stats(total_raw: int, new_entries: int, positions: list[str], apis: set[str]):
    """Save discovery run stats."""
    stats = {
        "date": date.today().isoformat(),
        "timestamp": datetime.now(UTC).isoformat(),
        "total_raw": total_raw,
        "new_entries": new_entries,
        "positions_searched": positions,
        "apis_used": sorted(apis),
    }
    try:
        with open(STATS_FILE, "w") as f:
            yaml.dump(stats, f, default_flow_style=False, sort_keys=False)
    except OSError as e:
        print(f"  Warning: Could not write discovery stats to {STATS_FILE}: {e}")


if __name__ == "__main__":
    main()
