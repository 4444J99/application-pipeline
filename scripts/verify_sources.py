#!/usr/bin/env python3
"""One-time verification of candidate ATS board slugs.

Tests Greenhouse and Ashby API endpoints to confirm which slugs return valid JSON.
Outputs YAML-ready lists of working slugs and a failure report.

Usage:
    python scripts/verify_sources.py                  # Test all candidates
    python scripts/verify_sources.py --greenhouse     # Greenhouse only
    python scripts/verify_sources.py --ashby          # Ashby only
"""

import argparse
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# ---------------------------------------------------------------------------
# Candidate slugs to test
# ---------------------------------------------------------------------------

GREENHOUSE_CANDIDATES = [
    # AI/ML
    "huggingface", "mistralai", "databricks", "anyscale", "weightsandbiases",
    "labelbox", "snorkelai", "allenai", "adeptai", "inflectionai",
    "midjourney", "jasperai", "writesonic", "copyai", "lightningai",
    "modallabs", "replicate", "stability", "deepmind", "cohereai",
    # Infrastructure/Platform
    "cockroachlabs", "timescaledb", "singlestore", "apollographql", "hasura",
    "prismaio", "airbyte", "fivetran", "prefectio", "dagsterio",
    "mux", "imgix", "fastly",
    # Developer Tools
    "postman", "gitpod", "circleci", "buildkite", "sentryio",
    "codeium", "tabnine",
    # Growth-Stage Tech
    "plaid", "brex", "mercury", "rippling", "gusto",
    "lattice", "deel", "remotehq", "oysterhr", "justworks",
    # Fintech/Infra
    "coinbase", "robinhood", "affirm", "marqeta", "lithic",
    "unit", "moov", "moderntreasury", "column",
    # Enterprise AI
    "palantir", "c3ai", "dataminr", "relativity", "h2oai", "datarobot",
    # Media/Content
    "spotify", "soundcloud", "shutterstock", "getty", "adoberesearch",
    # Defense/Govtech
    "anduril",
    # More DevTools / Infra
    "pagerduty", "newrelic", "hashicorp", "snyk", "sonarqube",
    "oktainc", "auth0", "contentful", "sanity", "stytch",
    "workos", "propelauth", "fly", "zerossl",
    "dopplerhq", "1password", "bitwarden",
]

ASHBY_CANDIDATES = [
    # AI/ML
    "stabilityai", "glean", "sierra", "harvey", "cognition",
    "magic", "poolside", "pika", "luma", "mistral",
    "cerebras", "fireworks", "groq", "deno", "val-town",
    # Infrastructure
    "clerk", "convex", "turso", "upstash", "axiom",
    "tinybird", "motherduck", "clickhouse", "duckdb", "qdrant",
    "weaviate", "pinecone", "chroma",
    # Developer Tools
    "cal", "twenty", "hoppscotch", "pieces", "zed",
    # Growth-Stage
    "liveblocks", "inngest", "trigger", "unkey",
    # More
    "vercel-ashby", "modal", "coreweave-ashby", "together-ashby",
    "retool", "airplane", "temporal", "stainlessapi", "speakeasyapi",
    "boundary", "buf", "encore",
]


def test_greenhouse(slug: str) -> tuple[bool, str]:
    """Test a Greenhouse board slug. Returns (valid, detail)."""
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
    try:
        req = Request(url, headers={"User-Agent": "pipeline-verify/1.0"})
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            job_count = len(data.get("jobs", []))
            return True, f"{job_count} jobs"
    except HTTPError as e:
        return False, f"HTTP {e.code}"
    except (URLError, TimeoutError, json.JSONDecodeError) as e:
        return False, str(e)[:60]


def test_ashby(slug: str) -> tuple[bool, str]:
    """Test an Ashby board slug. Returns (valid, detail)."""
    url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}"
    try:
        req = Request(url, headers={"User-Agent": "pipeline-verify/1.0"})
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            job_count = len(data.get("jobs", []))
            return True, f"{job_count} jobs"
    except HTTPError as e:
        return False, f"HTTP {e.code}"
    except (URLError, TimeoutError, json.JSONDecodeError) as e:
        return False, str(e)[:60]


def main():
    parser = argparse.ArgumentParser(description="Verify ATS board slugs")
    parser.add_argument("--greenhouse", action="store_true", help="Test Greenhouse only")
    parser.add_argument("--ashby", action="store_true", help="Test Ashby only")
    args = parser.parse_args()

    test_both = not args.greenhouse and not args.ashby

    if args.greenhouse or test_both:
        print("=" * 60)
        print("GREENHOUSE CANDIDATES")
        print("=" * 60)
        gh_valid = []
        gh_fail = []
        for slug in GREENHOUSE_CANDIDATES:
            valid, detail = test_greenhouse(slug)
            status = "OK" if valid else "FAIL"
            print(f"  [{status:4}] {slug:30} — {detail}")
            if valid:
                gh_valid.append(slug)
            else:
                gh_fail.append((slug, detail))

        print(f"\nGreenhouse: {len(gh_valid)} valid / {len(gh_fail)} failed")
        if gh_valid:
            print("\n# YAML-ready (add to .job-sources.yaml under greenhouse:)")
            for s in gh_valid:
                print(f"  - {s}")

    if args.ashby or test_both:
        print("\n" + "=" * 60)
        print("ASHBY CANDIDATES")
        print("=" * 60)
        ab_valid = []
        ab_fail = []
        for slug in ASHBY_CANDIDATES:
            valid, detail = test_ashby(slug)
            status = "OK" if valid else "FAIL"
            print(f"  [{status:4}] {slug:30} — {detail}")
            if valid:
                ab_valid.append(slug)
            else:
                ab_fail.append((slug, detail))

        print(f"\nAshby: {len(ab_valid)} valid / {len(ab_fail)} failed")
        if ab_valid:
            print("\n# YAML-ready (add to .job-sources.yaml under ashby:)")
            for s in ab_valid:
                print(f"  - {s}")


if __name__ == "__main__":
    main()
