#!/usr/bin/env python3
"""Source job postings from public ATS APIs and create pipeline entries.

Polls Greenhouse, Lever, and Ashby job board APIs for matching postings,
filters by title keywords, deduplicates against existing pipeline entries,
and creates pipeline YAML files in pipeline/active/.

Usage:
    python scripts/source_jobs.py                     # Fetch all, dry-run
    python scripts/source_jobs.py --fetch --dry-run    # Show what would be created
    python scripts/source_jobs.py --fetch --yes        # Create pipeline entries
    python scripts/source_jobs.py --fetch --limit 10   # Top 10 only
    python scripts/source_jobs.py --list-sources       # Show configured companies
    python scripts/source_jobs.py --stats              # Show last fetch stats
"""

import argparse
import json
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import (
    PIPELINE_DIR_ACTIVE,
    PIPELINE_DIR_RESEARCH_POOL,
    ALL_PIPELINE_DIRS,
    ALL_PIPELINE_DIRS_WITH_POOL,
    load_entries,
)

SOURCES_FILE = Path(__file__).resolve().parent / ".job-sources.yaml"
STATS_FILE = Path(__file__).resolve().parent / ".job-source-stats.yaml"

# Title keyword filters (case-insensitive)
TITLE_KEYWORDS = [
    "software engineer", "developer", "engineering",
    "developer advocate", "developer relations", "devrel",
    "developer experience", "developer tools", "cli",
    "technical writer", "documentation engineer",
    "solutions engineer", "forward deployed",
    "infrastructure", "platform engineer",
    "agentic", "ai engineer", "ml engineer",
    "full stack", "backend", "frontend",
]

TITLE_EXCLUDES = [
    "senior staff", "staff engineer", "principal",
    "director", "vp", "head of", "manager",
    "intern", "co-op",
    "hardware", "mechanical", "electrical",
    "finance", "accounting", "legal", "counsel",
    "recruiter", "people ops", "hr ",
]

# Request timeout in seconds
HTTP_TIMEOUT = 15

# Display names for companies (board_token -> display name)
VALID_LOCATION_CLASSES = {"us-onsite", "us-remote", "remote-global", "international", "unknown"}

# US states and cities for location classification
_US_STATES = [
    "al", "ak", "az", "ar", "ca", "co", "ct", "de", "fl", "ga",
    "hi", "id", "il", "in", "ia", "ks", "ky", "la", "me", "md",
    "ma", "mi", "mn", "ms", "mo", "mt", "ne", "nv", "nh", "nj",
    "nm", "ny", "nc", "nd", "oh", "ok", "or", "pa", "ri", "sc",
    "sd", "tn", "tx", "ut", "vt", "va", "wa", "wv", "wi", "wy",
    "dc",
]
_US_CITIES = [
    "san francisco", "new york", "seattle", "austin", "chicago",
    "los angeles", "boston", "denver", "portland", "miami",
    "atlanta", "dallas", "houston", "phoenix", "philadelphia",
    "san jose", "san diego", "nashville", "raleigh", "pittsburgh",
    "minneapolis", "salt lake city", "boulder", "palo alto",
    "mountain view", "menlo park", "sunnyvale", "cupertino",
    "redmond", "bellevue", "brooklyn", "manhattan",
    "sf", "nyc",
]
_INTERNATIONAL_MARKERS = [
    "london", "uk", "united kingdom", "dublin", "ireland",
    "tokyo", "japan", "singapore", "korea", "seoul",
    "hyderabad", "india", "bangalore", "bengaluru", "mumbai",
    "hungary", "budapest", "netherlands", "amsterdam",
    "germany", "berlin", "munich", "france", "paris",
    "canada", "toronto", "vancouver", "montreal",
    "australia", "sydney", "melbourne",
    "brazil", "são paulo",
    "switzerland", "zürich", "zurich",
    "israel", "tel aviv",
    "poland", "warsaw",
    "spain", "madrid", "barcelona",
    "italy", "milan", "rome",
    "sweden", "stockholm",
    "emea", "apac",
]
_US_KEYWORDS = [
    "united states", "usa", " us ", "u.s.", "us-", "- us",
    "remote - us", "remote-us", "remote us", "us remote",
]


def classify_location(loc: str) -> str:
    """Classify a location string for US accessibility.

    Returns one of: us-onsite, us-remote, remote-global, international, unknown.
    """
    if not loc or not loc.strip():
        return "unknown"

    loc_lower = loc.lower().strip()

    # Check for explicit international markers first
    has_international = any(m in loc_lower for m in _INTERNATIONAL_MARKERS)

    # Check for US indicators
    has_us_city = any(c in loc_lower for c in _US_CITIES)
    has_us_state = False
    import re as _re
    for state in _US_STATES:
        # Match ", CA" at end of string or followed by non-alpha (space, semicolon, pipe)
        # Require comma prefix + non-alpha suffix to avoid matching words like "india" -> "in"
        if _re.search(rf", {state}(?:[^a-z]|$)", loc_lower):
            has_us_state = True
            break
    has_us_keyword = any(k in loc_lower for k in _US_KEYWORDS)
    has_us = has_us_city or has_us_state or has_us_keyword

    # Check for remote indicators
    is_remote = "remote" in loc_lower

    # Classification logic
    if has_international and not has_us:
        return "international"

    if has_us and is_remote:
        return "us-remote"

    if has_us:
        return "us-onsite"

    if is_remote:
        # "Remote" with no country qualifier — could be global
        return "remote-global"

    return "unknown"


COMPANY_DISPLAY_NAMES = {
    # Greenhouse boards
    "anthropic": "Anthropic",
    "runwayml": "Runway",
    "scaleai": "Scale AI",
    "figma": "Figma",
    "vercel": "Vercel",
    "assemblyai": "AssemblyAI",
    "stripe": "Stripe",
    "togetherai": "Together AI",
    "temporaltechnologies": "Temporal",
    "cloudflare": "Cloudflare",
    "dbtlabsinc": "dbt Labs",
    "sourcegraph91": "Sourcegraph",
    "coreweave": "Weights & Biases",
    "launchdarkly": "LaunchDarkly",
    "datadog": "Datadog",
    "wikimedia": "Wikimedia",
    "mozilla": "Mozilla",
    "gitlab": "GitLab",
    "twilio": "Twilio",
    "mongodb": "MongoDB",
    "elastic": "Elastic",
    "grafanalabs": "Grafana Labs",
    "netlify": "Netlify",
    "planetscale": "PlanetScale",
    "airtable": "Airtable",
    # Ashby boards
    "cohere": "Cohere",
    "posthog": "PostHog",
    "openai": "OpenAI",
    "notion": "Notion",
    "supabase": "Supabase",
    "linear": "Linear",
    "replit": "Replit",
    "deepgram": "Deepgram",
    "cursor": "Cursor",
    "ramp": "Ramp",
    "character": "Character AI",
    "perplexity": "Perplexity",
    "railway": "Railway",
    "render": "Render",
    "resend": "Resend",
    "elevenlabs": "ElevenLabs",
    "neon": "Neon",
    "warp": "Warp",
}


def load_sources() -> dict:
    """Load company lists from .job-sources.yaml."""
    if not SOURCES_FILE.exists():
        print(f"Sources file not found: {SOURCES_FILE}", file=sys.stderr)
        print("Create it with greenhouse/lever/ashby company lists.", file=sys.stderr)
        sys.exit(1)
    with open(SOURCES_FILE) as f:
        data = yaml.safe_load(f)
    return data or {}


def _http_get(url: str) -> bytes:
    """GET request with User-Agent header and timeout."""
    req = Request(url, headers={"User-Agent": "application-pipeline/1.0"})
    with urlopen(req, timeout=HTTP_TIMEOUT) as resp:
        return resp.read()


def _http_post_json(url: str, body: dict) -> bytes:
    """POST JSON request with timeout."""
    data = json.dumps(body).encode("utf-8")
    req = Request(
        url,
        data=data,
        headers={
            "User-Agent": "application-pipeline/1.0",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urlopen(req, timeout=HTTP_TIMEOUT) as resp:
        return resp.read()


def fetch_greenhouse_jobs(board: str) -> list[dict]:
    """Fetch jobs from Greenhouse public job board API.

    Returns list of normalized job dicts.
    """
    url = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs"
    try:
        raw = _http_get(url)
        data = json.loads(raw)
    except (HTTPError, URLError, json.JSONDecodeError) as e:
        print(f"  [greenhouse/{board}] Error: {e}", file=sys.stderr)
        return []

    jobs = data.get("jobs", [])
    results = []
    for job in jobs:
        raw_date = job.get("updated_at", "")
        posting_date = raw_date[:10] if raw_date else None
        results.append({
            "title": job.get("title", ""),
            "id": str(job.get("id", "")),
            "url": job.get("absolute_url", ""),
            "location": job.get("location", {}).get("name", ""),
            "company": board,
            "company_display": COMPANY_DISPLAY_NAMES.get(board, board.title()),
            "portal": "greenhouse",
            "company_url": f"https://boards.greenhouse.io/{board}",
            "posting_date": posting_date,
        })
    return results


def fetch_lever_jobs(company: str) -> list[dict]:
    """Fetch jobs from Lever public postings API.

    Returns list of normalized job dicts.
    """
    url = f"https://api.lever.co/v0/postings/{company}?mode=json"
    try:
        raw = _http_get(url)
        jobs = json.loads(raw)
    except (HTTPError, URLError, json.JSONDecodeError) as e:
        print(f"  [lever/{company}] Error: {e}", file=sys.stderr)
        return []

    if not isinstance(jobs, list):
        return []

    results = []
    for job in jobs:
        created_ms = job.get("createdAt")
        if created_ms:
            posting_date = datetime.fromtimestamp(created_ms / 1000, tz=timezone.utc).date().isoformat()
        else:
            posting_date = None
        results.append({
            "title": job.get("text", ""),
            "id": job.get("id", ""),
            "url": job.get("hostedUrl", "") or job.get("applyUrl", ""),
            "location": job.get("categories", {}).get("location", ""),
            "company": company,
            "company_display": COMPANY_DISPLAY_NAMES.get(company, company.title()),
            "portal": "lever",
            "company_url": f"https://jobs.lever.co/{company}",
            "posting_date": posting_date,
        })
    return results


def fetch_ashby_jobs(company: str) -> list[dict]:
    """Fetch jobs from Ashby public job board API.

    Returns list of normalized job dicts.
    """
    url = f"https://api.ashbyhq.com/posting-api/job-board/{company}"
    try:
        raw = _http_get(url)
        data = json.loads(raw)
    except (HTTPError, URLError, json.JSONDecodeError) as e:
        print(f"  [ashby/{company}] Error: {e}", file=sys.stderr)
        return []

    jobs = data.get("jobs", [])
    results = []
    for job in jobs:
        posting_url = f"https://jobs.ashbyhq.com/{company}/{job.get('id', '')}"
        raw_date = job.get("publishedDate") or job.get("updatedAt", "")
        posting_date = raw_date[:10] if raw_date else None
        results.append({
            "title": job.get("title", ""),
            "id": str(job.get("id", "")),
            "url": posting_url,
            "location": job.get("location", ""),
            "company": company,
            "company_display": COMPANY_DISPLAY_NAMES.get(company, company.title()),
            "portal": "ashby",
            "company_url": f"https://jobs.ashbyhq.com/{company}",
            "posting_date": posting_date,
        })
    return results


def filter_by_title(jobs: list[dict], keywords: list[str], excludes: list[str]) -> list[dict]:
    """Filter jobs where title matches any keyword and no exclude."""
    matched = []
    for job in jobs:
        title_lower = job["title"].lower()

        # Check excludes first
        if any(exc in title_lower for exc in excludes):
            continue

        # Check keywords
        if any(kw in title_lower for kw in keywords):
            matched.append(job)

    return matched


def _slugify(text: str) -> str:
    """Convert text to kebab-case slug for pipeline entry IDs."""
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text.strip('-')[:60]


def _get_existing_ids() -> set[str]:
    """Get IDs and application URLs of existing pipeline entries (including research pool)."""
    entries = load_entries(dirs=ALL_PIPELINE_DIRS_WITH_POOL)
    ids = set()
    for e in entries:
        if e.get("id"):
            ids.add(e["id"])
        # Also track by application URL for dedup
        target = e.get("target", {})
        if isinstance(target, dict) and target.get("application_url"):
            ids.add(target["application_url"])
    return ids


def deduplicate(jobs: list[dict], existing_ids: set[str]) -> list[dict]:
    """Remove jobs that are already in the pipeline (by ID or URL)."""
    unique = []
    seen_slugs = set()
    for job in jobs:
        slug = f"{_slugify(job['company_display'])}-{_slugify(job['title'])}"
        if slug in existing_ids or slug in seen_slugs:
            continue
        if job["url"] in existing_ids:
            continue
        seen_slugs.add(slug)
        unique.append(job)
    return unique


def create_pipeline_entry(job: dict) -> tuple[str, dict]:
    """Generate a pipeline YAML dict for a job posting.

    Returns (entry_id, yaml_dict).
    """
    company_slug = _slugify(job["company_display"])
    title_slug = _slugify(job["title"])
    entry_id = f"{company_slug}-{title_slug}"

    today = date.today().isoformat()

    entry = {
        "id": entry_id,
        "name": f"{job['company_display']} {job['title']}",
        "track": "job",
        "status": "research",
        "outcome": None,
        "target": {
            "organization": job["company_display"],
            "url": job.get("company_url", ""),
            "application_url": job["url"],
            "portal": job["portal"],
            "location": job.get("location", ""),
            "location_class": classify_location(job.get("location", "")),
        },
        "deadline": {
            "date": None,
            "type": "rolling",
        },
        "amount": {
            "value": 0,
            "currency": "USD",
            "type": "salary",
        },
        "fit": {
            "score": 0,
            "identity_position": "independent-engineer",
        },
        "submission": {
            "effort_level": "standard",
            "blocks_used": {},
            "variant_ids": {},
            "materials_attached": [
                "resumes/independent-engineer-resume.html",
            ],
            "portfolio_url": "https://4444j99.github.io/portfolio/",
        },
        "timeline": {
            "researched": today,
            "posting_date": job.get("posting_date"),
        },
        "conversion": {
            "response_received": False,
            "response_type": None,
            "time_to_response_days": None,
            "feedback": None,
        },
        "tags": ["auto-sourced"],
        "source": "source_jobs.py",
        "last_touched": today,
    }

    return entry_id, entry


def write_pipeline_entry(entry_id: str, entry: dict) -> Path:
    """Write a pipeline entry YAML file to pipeline/research_pool/."""
    PIPELINE_DIR_RESEARCH_POOL.mkdir(parents=True, exist_ok=True)
    filepath = PIPELINE_DIR_RESEARCH_POOL / f"{entry_id}.yaml"
    with open(filepath, "w") as f:
        yaml.dump(entry, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
    return filepath


def save_stats(stats: dict):
    """Save fetch statistics to .job-source-stats.yaml."""
    stats["date"] = date.today().isoformat()
    with open(STATS_FILE, "w") as f:
        yaml.dump(stats, f, default_flow_style=False, sort_keys=False)


def show_stats():
    """Display last fetch statistics."""
    if not STATS_FILE.exists():
        print("No fetch stats found. Run --fetch first.")
        return
    with open(STATS_FILE) as f:
        stats = yaml.safe_load(f)
    print("Last fetch stats:")
    for key, val in (stats or {}).items():
        print(f"  {key}: {val}")


def show_sources():
    """Display configured company sources."""
    sources = load_sources()
    for portal, companies in sources.items():
        if not companies:
            continue
        print(f"\n{portal} ({len(companies)} companies):")
        for c in companies:
            display = COMPANY_DISPLAY_NAMES.get(c, c)
            print(f"  {c:<20s} → {display}")


def backfill_locations(dry_run: bool = False) -> int:
    """Add target.location and target.location_class to existing entries.

    Parses 'Location: ...' from the notes field, populates structured
    target fields, and cleans the location line out of notes.

    Returns number of entries updated.
    """
    updated = 0
    for pipeline_dir in ALL_PIPELINE_DIRS:
        if not pipeline_dir.exists():
            continue
        for filepath in sorted(pipeline_dir.glob("*.yaml")):
            if filepath.name.startswith("_"):
                continue

            with open(filepath) as f:
                content = f.read()

            data = yaml.safe_load(content)
            if not isinstance(data, dict):
                continue

            target = data.get("target", {})
            if not isinstance(target, dict):
                continue

            # Skip if already has location_class
            if target.get("location_class"):
                continue

            # Extract location from notes field
            notes = data.get("notes") or ""
            location = ""

            if isinstance(notes, str) and notes.startswith("Location: "):
                # Extract location — may be followed by additional context
                loc_text = notes[len("Location: "):]
                # Location ends at first period, newline, or end of string
                loc_end = len(loc_text)
                for sep in [".", "\n"]:
                    idx = loc_text.find(sep)
                    if idx != -1 and idx < loc_end:
                        loc_end = idx
                location = loc_text[:loc_end].strip()
                # Remaining text becomes new notes
                remaining = loc_text[loc_end:].lstrip(". ").strip()
                new_notes = remaining if remaining else ""
            elif isinstance(notes, str) and "\nLocation: " in notes:
                # Multi-line notes with location somewhere inside
                lines = notes.split("\n")
                remaining = []
                for line in lines:
                    if line.startswith("Location: "):
                        location = line[len("Location: "):].strip()
                    else:
                        remaining.append(line)
                new_notes = "\n".join(remaining).strip()
            else:
                # No location in notes — use target.location if present
                location = target.get("location", "")
                new_notes = notes

            if not location:
                continue

            loc_class = classify_location(location)

            if dry_run:
                print(f"  [dry-run] {filepath.stem}: {location!r} -> {loc_class}")
                updated += 1
                continue

            # Update via YAML round-trip to preserve formatting
            # Add location and location_class to target section
            import re as _re

            # Insert location fields after portal line in target section
            portal_pattern = _re.compile(
                r"^(\s+portal:\s+\S+)\s*$", _re.MULTILINE
            )
            match = portal_pattern.search(content)
            if match:
                indent_match = _re.match(r"(\s+)", match.group(0))
                indent = indent_match.group(1) if indent_match else "  "
                insert_pos = match.end()
                loc_lines = f"\n{indent}location: {_yaml_quote(location)}\n{indent}location_class: {loc_class}"
                content = content[:insert_pos] + loc_lines + content[insert_pos:]

            # Clean location out of notes
            if new_notes != notes:
                if not new_notes:
                    # Remove entire notes field (may be multiline with indented continuation)
                    content = _re.sub(
                        r"^notes:[ \t]+[^\n]*\n(?:[ \t]+[^\n]*\n)*",
                        "", content, count=1, flags=_re.MULTILINE,
                    )
                else:
                    # Replace notes value (handles multiline YAML strings)
                    content = _re.sub(
                        r"^notes:[ \t]+[^\n]*\n(?:[ \t]+[^\n]*\n)*",
                        f"notes: {_yaml_quote(new_notes)}\n",
                        content, count=1, flags=_re.MULTILINE,
                    )

            # Verify still valid YAML
            try:
                yaml.safe_load(content)
            except yaml.YAMLError as e:
                print(f"  WARNING: Skipping {filepath.stem} — YAML invalid after edit: {e}",
                      file=sys.stderr)
                continue

            with open(filepath, "w") as f:
                f.write(content)

            print(f"  {filepath.stem}: {location!r} -> {loc_class}")
            updated += 1

    return updated


def _yaml_quote(text: str) -> str:
    """Quote a string for inline YAML if it contains special characters."""
    if not text:
        return "''"
    # If it contains single quotes, use double quotes; otherwise single quotes
    if any(c in text for c in ":#{}[]|>&*!%@`'\"\n"):
        if "'" not in text:
            return f"'{text}'"
        return f'"{text}"'
    return text


def main():
    parser = argparse.ArgumentParser(
        description="Source job postings from public ATS APIs"
    )
    parser.add_argument("--fetch", action="store_true",
                        help="Fetch jobs from all configured sources")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be created without writing files")
    parser.add_argument("--yes", action="store_true",
                        help="Actually create pipeline entry files")
    parser.add_argument("--limit", type=int, default=0,
                        help="Limit number of entries created (0 = unlimited)")
    parser.add_argument("--list-sources", action="store_true",
                        help="Show configured company sources")
    parser.add_argument("--stats", action="store_true",
                        help="Show last fetch statistics")
    parser.add_argument("--backfill-locations", action="store_true",
                        help="Add target.location and target.location_class to existing entries")
    args = parser.parse_args()

    if args.list_sources:
        show_sources()
        return

    if args.stats:
        show_stats()
        return

    if args.backfill_locations:
        print("Backfilling location data on existing pipeline entries...")
        count = backfill_locations(dry_run=args.dry_run)
        print(f"\n{'=' * 60}")
        print(f"Updated {count} entries" + (" (dry run)" if args.dry_run else ""))
        if not args.dry_run and count:
            print(f"\nNext steps:")
            print(f"  python scripts/score.py --all          # Re-score with location penalty")
        return

    if not args.fetch and not args.dry_run and not args.yes:
        # Default: fetch + dry-run
        args.fetch = True
        args.dry_run = True

    if args.fetch or args.dry_run or args.yes:
        sources = load_sources()
        existing_ids = _get_existing_ids()

        all_jobs = []
        fetched_counts = {}

        # Fetch from all portals
        greenhouse_boards = sources.get("greenhouse") or []
        lever_companies = sources.get("lever") or []
        ashby_companies = sources.get("ashby") or []

        print(f"Fetching from {len(greenhouse_boards)} Greenhouse boards...")
        for board in greenhouse_boards:
            jobs = fetch_greenhouse_jobs(board)
            display = COMPANY_DISPLAY_NAMES.get(board, board)
            filtered = filter_by_title(jobs, TITLE_KEYWORDS, TITLE_EXCLUDES)
            fetched_counts[f"greenhouse/{board}"] = {"total": len(jobs), "matched": len(filtered)}
            if filtered:
                print(f"  {display}: {len(filtered)} matched / {len(jobs)} total")
            all_jobs.extend(filtered)

        print(f"\nFetching from {len(lever_companies)} Lever boards...")
        for company in lever_companies:
            jobs = fetch_lever_jobs(company)
            display = COMPANY_DISPLAY_NAMES.get(company, company)
            filtered = filter_by_title(jobs, TITLE_KEYWORDS, TITLE_EXCLUDES)
            fetched_counts[f"lever/{company}"] = {"total": len(jobs), "matched": len(filtered)}
            if filtered:
                print(f"  {display}: {len(filtered)} matched / {len(jobs)} total")
            all_jobs.extend(filtered)

        print(f"\nFetching from {len(ashby_companies)} Ashby boards...")
        for company in ashby_companies:
            jobs = fetch_ashby_jobs(company)
            display = COMPANY_DISPLAY_NAMES.get(company, company)
            filtered = filter_by_title(jobs, TITLE_KEYWORDS, TITLE_EXCLUDES)
            fetched_counts[f"ashby/{company}"] = {"total": len(jobs), "matched": len(filtered)}
            if filtered:
                print(f"  {display}: {len(filtered)} matched / {len(jobs)} total")
            all_jobs.extend(filtered)

        # Deduplicate
        unique_jobs = deduplicate(all_jobs, existing_ids)

        # Apply limit
        if args.limit and args.limit > 0:
            unique_jobs = unique_jobs[:args.limit]

        print(f"\n{'=' * 60}")
        print(f"Total matched: {len(all_jobs)}")
        print(f"After dedup:   {len(unique_jobs)}")
        if args.limit:
            print(f"Limited to:    {args.limit}")
        print(f"{'=' * 60}")

        if not unique_jobs:
            print("\nNo new jobs to add.")
            save_stats({
                "total_fetched": sum(v["total"] for v in fetched_counts.values()),
                "total_matched": len(all_jobs),
                "new_entries": 0,
            })
            return

        # Create entries
        created = []
        for job in unique_jobs:
            entry_id, entry = create_pipeline_entry(job)
            portal = job["portal"]
            company = job["company_display"]
            title = job["title"]

            if args.yes and not args.dry_run:
                filepath = write_pipeline_entry(entry_id, entry)
                created.append(entry_id)
                print(f"  + {entry_id}")
                print(f"    {company} — {title}")
                print(f"    {job['url']}")
            else:
                print(f"  [dry-run] {entry_id}")
                print(f"    {company} — {title} [{portal}]")
                print(f"    {job['url']}")
                created.append(entry_id)

        print(f"\n{'=' * 60}")
        if args.yes and not args.dry_run:
            print(f"Created {len(created)} pipeline entries in pipeline/research_pool/")
            print(f"\nNext steps:")
            print(f"  python scripts/score.py --all          # Score new entries")
            print(f"  python scripts/advance.py --report     # Check advancement")
        else:
            print(f"Would create {len(created)} pipeline entries (run with --yes to create)")

        save_stats({
            "total_fetched": sum(v["total"] for v in fetched_counts.values()),
            "total_matched": len(all_jobs),
            "new_entries": len(created),
            "sources": fetched_counts,
        })


if __name__ == "__main__":
    main()
