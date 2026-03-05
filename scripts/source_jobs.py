#!/usr/bin/env python3
"""Source job postings from public ATS APIs and create pipeline entries.

Polls Greenhouse, Lever, and Ashby job board APIs for matching postings,
filters by title keywords, deduplicates against existing pipeline entries,
and creates pipeline YAML files in pipeline/research_pool/.

By default, only jobs posted within 72 hours are included (--fresh-only).
Use --all to override and include older postings.

Usage:
    python scripts/source_jobs.py                     # Fetch all, dry-run (fresh only)
    python scripts/source_jobs.py --fetch --dry-run    # Show what would be created
    python scripts/source_jobs.py --fetch --yes        # Create pipeline entries
    python scripts/source_jobs.py --fetch --all        # Include older postings too
    python scripts/source_jobs.py --fetch --limit 10   # Top 10 only
    python scripts/source_jobs.py --list-sources       # Show configured companies
    python scripts/source_jobs.py --stats              # Show last fetch stats
"""

import argparse
import json
import re
import sys
from datetime import UTC, date, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import (
    ALL_PIPELINE_DIRS,
    ALL_PIPELINE_DIRS_WITH_POOL,
    JOB_STALE_HOURS,
    PIPELINE_DIR_RESEARCH_POOL,
    load_entries,
)
from source_jobs_constants import (
    HTTP_TIMEOUT,
    TITLE_EXCLUDES,
    TITLE_KEYWORDS,
)
from source_jobs_constants import (
    INTERNATIONAL_MARKERS as _INTERNATIONAL_MARKERS,
)
from source_jobs_constants import (
    US_CITIES as _US_CITIES,
)
from source_jobs_constants import (
    US_KEYWORDS as _US_KEYWORDS,
)
from source_jobs_constants import (
    US_STATES as _US_STATES,
)
from source_jobs_constants import (
    VALID_LOCATION_CLASSES as _VALID_LOCATION_CLASSES,
)

# Backward-compatible export used by tests and downstream importers.
VALID_LOCATION_CLASSES = _VALID_LOCATION_CLASSES

# Maximum posting age (in hours) for --fresh-only filter
FRESH_ONLY_MAX_HOURS = JOB_STALE_HOURS  # 72h default

SOURCES_FILE = Path(__file__).resolve().parent / ".job-sources.yaml"
STATS_FILE = Path(__file__).resolve().parent / ".job-source-stats.yaml"


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
    # Greenhouse boards — original
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
    "coreweave": "CoreWeave",
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
    # Greenhouse boards — expansion
    "databricks": "Databricks",
    "labelbox": "Labelbox",
    "snorkelai": "Snorkel AI",
    "inflectionai": "Inflection AI",
    "lightningai": "Lightning AI",
    "deepmind": "DeepMind",
    "cockroachlabs": "CockroachDB",
    "singlestore": "SingleStore",
    "fivetran": "Fivetran",
    "fastly": "Fastly",
    "postman": "Postman",
    "circleci": "CircleCI",
    "buildkite": "Buildkite",
    "brex": "Brex",
    "mercury": "Mercury",
    "gusto": "Gusto",
    "lattice": "Lattice",
    "justworks": "Justworks",
    "coinbase": "Coinbase",
    "robinhood": "Robinhood",
    "affirm": "Affirm",
    "marqeta": "Marqeta",
    "lithic": "Lithic",
    "alloy": "Alloy",
    "alchemy": "Alchemy",
    "relativity": "Relativity",
    "andurilindustries": "Anduril",
    "pagerduty": "PagerDuty",
    "newrelic": "New Relic",
    "honeycomb": "Honeycomb",
    "sumologic": "Sumo Logic",
    "contentful": "Contentful",
    "ghost": "Ghost",
    "dropbox": "Dropbox",
    "asana": "Asana",
    "duolingo": "Duolingo",
    "reddit": "Reddit",
    "discord": "Discord",
    "lyft": "Lyft",
    "instacart": "Instacart",
    "roblox": "Roblox",
    "squarespace": "Squarespace",
    "webflow": "Webflow",
    "grammarly": "Grammarly",
    "mixpanel": "Mixpanel",
    "amplitude": "Amplitude",
    "intercom": "Intercom",
    "calendly": "Calendly",
    "salesloft": "SalesLoft",
    "bitwarden": "Bitwarden",
    "wizinc": "Wiz",
    "neo4j": "Neo4j",
    "yugabyte": "YugabyteDB",
    "redis": "Redis",
    "dremio": "Dremio",
    "starburst": "Starburst",
    "tailscale": "Tailscale",
    "make": "Make",
    "rootly": "Rootly",
    "samsara": "Samsara",
    "toast": "Toast",
    "tripactions": "Navan",
    "warp": "Warp",
    "chime": "Chime",
    "sofi": "SoFi",
    "remote": "Remote",
    # Ashby boards — original
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
    # Ashby boards — expansion
    "sierra": "Sierra AI",
    "harvey": "Harvey AI",
    "cognition": "Cognition",
    "poolside": "Poolside AI",
    "pika": "Pika",
    "modal": "Modal",
    "langchain": "LangChain",
    "llamaindex": "LlamaIndex",
    "stainlessapi": "Stainless",
    "clerk": "Clerk",
    "axiom": "Axiom",
    "motherduck": "MotherDuck",
    "weaviate": "Weaviate",
    "pinecone": "Pinecone",
    "airbyte": "Airbyte",
    "snowflake": "Snowflake",
    "livekit": "LiveKit",
    "twenty": "Twenty",
    "zed": "Zed",
    "inngest": "Inngest",
    "sentry": "Sentry",
    "mintlify": "Mintlify",
    "gitbook": "GitBook",
    "semgrep": "Semgrep",
    "greptile": "Greptile",
    "raycast": "Raycast",
    "infisical": "Infisical",
    "doppler": "Doppler",
    "speakeasy": "Speakeasy",
    "n8n": "n8n",
    "windmill": "Windmill",
    "plane": "Plane",
    "deel": "Deel",
    "zapier": "Zapier",
    "prefect": "Prefect",
    "hightouch": "Hightouch",
    "retool": "Retool",
    "temporal": "Temporal",
    "assembly": "Assembly AI",
    "beam": "Beam",
    "fig": "Fig",
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
            posting_date = datetime.fromtimestamp(created_ms / 1000, tz=UTC).date().isoformat()
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


def _posting_age_hours(job: dict) -> float | None:
    """Compute posting age in hours from the job's posting_date.

    Returns None if posting_date is missing or unparseable.
    """
    posting_date = job.get("posting_date")
    if not posting_date:
        return None
    try:
        d = datetime.strptime(str(posting_date), "%Y-%m-%d").replace(tzinfo=UTC)
        now = datetime.now(UTC)
        return (now - d).total_seconds() / 3600.0
    except (ValueError, TypeError):
        return None


def _format_posting_age(job: dict) -> str:
    """Format posting age as a human-readable string like '[2h ago]' or '[3d ago]'.

    Returns '[??]' if age is unknown.
    """
    hours = _posting_age_hours(job)
    if hours is None:
        return "[??]"
    if hours < 1:
        return "[<1h ago]"
    if hours < 24:
        return f"[{int(hours)}h ago]"
    days = hours / 24.0
    if days < 1.5:
        return "[1d ago]"
    return f"[{int(days)}d ago]"


def filter_by_freshness(jobs: list[dict], max_hours: float = FRESH_ONLY_MAX_HOURS) -> tuple[list[dict], list[dict]]:
    """Split jobs into fresh (within max_hours) and stale (older).

    Jobs with no posting_date are treated as fresh (benefit of the doubt).

    Returns:
        (fresh_jobs, skipped_jobs)
    """
    fresh = []
    skipped = []
    for job in jobs:
        hours = _posting_age_hours(job)
        if hours is not None and hours > max_hours:
            skipped.append(job)
        else:
            fresh.append(job)
    return fresh, skipped


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
            "date_added": today,
            "discovered": datetime.now(UTC).isoformat(),
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
    if any(c in text for c in ":#{}[]|>&*!%@`'\"\n"):
        if "'" not in text:
            return f"'{text}'"
        if '"' not in text:
            return f'"{text}"'
        # Both quote types present — escape double quotes in double-quoted string
        escaped = text.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
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
    parser.add_argument("--fresh-only", action="store_true", default=True,
                        help="Only include jobs posted within 72h (default for --fetch)")
    parser.add_argument("--all", action="store_true", dest="include_all",
                        help="Include all jobs regardless of posting age (overrides --fresh-only)")
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
            print("\nNext steps:")
            print("  python scripts/score.py --all          # Re-score with location penalty")
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

        # Apply freshness filter (default: only jobs <72h old)
        skipped_stale = []
        if not args.include_all:
            unique_jobs, skipped_stale = filter_by_freshness(unique_jobs)
            if skipped_stale:
                print(f"\nSkipped {len(skipped_stale)} stale postings (>{int(FRESH_ONLY_MAX_HOURS)}h old):")
                for job in skipped_stale[:10]:
                    age_str = _format_posting_age(job)
                    print(f"    {age_str} {job['company_display']} — {job['title']}")
                if len(skipped_stale) > 10:
                    print(f"    ... and {len(skipped_stale) - 10} more")
                print("  Use --all to include older postings.")

        # Apply limit
        if args.limit and args.limit > 0:
            unique_jobs = unique_jobs[:args.limit]

        print(f"\n{'=' * 60}")
        print(f"Total matched: {len(all_jobs)}")
        print(f"After dedup:   {len(unique_jobs) + len(skipped_stale)}")
        if skipped_stale:
            print(f"Skipped stale: {len(skipped_stale)}")
        print(f"Fresh & new:   {len(unique_jobs)}")
        if args.limit:
            print(f"Limited to:    {args.limit}")
        print(f"{'=' * 60}")

        # Auto-source balance check: alert if >80% are tech jobs
        if unique_jobs:
            job_track_count = sum(1 for j in unique_jobs if j.get("track", "job") == "job")
            total_new = len(unique_jobs)
            job_pct = job_track_count / total_new * 100 if total_new > 0 else 0
            if job_pct > 80 and total_new >= 5:
                print(f"\n  AUTO-SOURCE BALANCE: {job_pct:.0f}% tech jobs ({job_track_count}/{total_new})")
                print("  Consider adding non-ATS sources (grants, residencies, fellowships)")
                print("  to maintain pipeline diversity across tracks.")

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
            age_str = _format_posting_age(job)

            if args.yes and not args.dry_run:
                write_pipeline_entry(entry_id, entry)
                created.append(entry_id)
                print(f"  + {entry_id}")
                print(f"    {company} — {title} {age_str}")
                print(f"    {job['url']}")
            else:
                print(f"  [dry-run] {entry_id}")
                print(f"    {company} — {title} [{portal}] {age_str}")
                print(f"    {job['url']}")
                created.append(entry_id)

        print(f"\n{'=' * 60}")
        if args.yes and not args.dry_run:
            print(f"Created {len(created)} pipeline entries in pipeline/research_pool/")
            print("\nNext steps:")
            print("  python scripts/score.py --all          # Score new entries")
            print("  python scripts/advance.py --report     # Check advancement")
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
