#!/usr/bin/env python3
"""Ingest historical job application data from LinkedIn and ApplyAll CSV exports.

Parses CSV datasets, deduplicates, classifies ATS portals, and writes a unified
historical-outcomes.yaml for consumption by outcome_learner.py and standards.py.

Usage:
    python scripts/ingest_historical.py                         # Dry-run preview
    python scripts/ingest_historical.py --write                 # Write historical-outcomes.yaml
    python scripts/ingest_historical.py --stats                 # Summary statistics only
    python scripts/ingest_historical.py --json                  # Machine-readable output
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import REPO_ROOT, SIGNALS_DIR, load_identity

INTAKE_DIR = REPO_ROOT / "intake"
LINKEDIN_DIR = INTAKE_DIR / "linkedin-export" / "LinkedInDataExport_12-25-2025" / "Jobs"
def get_applyall_csv_path() -> Path:
    """Return the path to the ApplyAll CSV, using identity if available."""
    full_name = load_identity()["person"]["full_name"]
    slug = full_name.replace(" ", "_")
    return INTAKE_DIR / f"{slug}_applied_applications.csv"

APPLYALL_CSV = get_applyall_csv_path()
OUTPUT_PATH = SIGNALS_DIR / "historical-outcomes.yaml"

# ATS portal classification from URL patterns
PORTAL_PATTERNS = {
    "greenhouse": [r"greenhouse\.io", r"boards\.greenhouse"],
    "lever": [r"jobs\.lever\.co"],
    "ashby": [r"jobs\.ashbyhq\.com"],
    "workday": [r"\.wd\d+\.", r"myworkdayjobs\.com"],
    "workable": [r"apply\.workable\.com"],
    "smartrecruiters": [r"jobs\.smartrecruiters\.com"],
    "icims": [r"\.icims\.com"],
    "rippling": [r"ats\.rippling\.com"],
    "linkedin": [r"linkedin\.com/jobs"],
}


def classify_portal(url: str) -> str:
    """Classify ATS portal from application URL."""
    if not url or url == "N/A":
        return "unknown"
    url_lower = url.lower()
    for portal, patterns in PORTAL_PATTERNS.items():
        if any(re.search(p, url_lower) for p in patterns):
            return portal
    return "other"


def _parse_linkedin_date(raw: str) -> str | None:
    """Parse LinkedIn date format '11/20/24, 8:15 AM' to ISO date."""
    if not raw:
        return None
    try:
        dt = datetime.strptime(raw.strip().strip('"'), "%m/%d/%y, %I:%M %p")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return None


def _parse_applyall_date(raw: str) -> str | None:
    """Parse ApplyAll date format '4/2/2025' to ISO date."""
    if not raw:
        return None
    try:
        dt = datetime.strptime(raw.strip().strip('"'), "%m/%d/%Y")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return None


def parse_linkedin_csv(filepath: Path) -> list[dict]:
    """Parse a single LinkedIn Job Applications CSV file."""
    records = []
    with open(filepath, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            company = (row.get("Company Name") or "").strip()
            if not company:
                continue
            title = (row.get("Job Title") or "").strip()
            url = (row.get("Job Url") or "").strip()
            applied = _parse_linkedin_date(row.get("Application Date", ""))
            records.append({
                "company": company,
                "title": title,
                "applied_date": applied,
                "url": url,
                "portal": classify_portal(url),
                "channel": "linkedin-easy-apply",
                "source": "linkedin-export",
                "outcome": "expired",
                "outcome_reason": "no_response",
            })
    return records


def parse_applyall_csv(filepath: Path) -> list[dict]:
    """Parse the ApplyAll applied applications CSV."""
    records = []
    with open(filepath, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            company = (row.get("Company") or "").strip()
            if not company:
                continue
            title = (row.get("Title") or "").strip()
            url = (row.get("URL") or "").strip()
            applied = _parse_applyall_date(row.get("Applied Date", ""))
            records.append({
                "company": company,
                "title": title,
                "applied_date": applied,
                "url": url if url != "N/A" else "",
                "portal": classify_portal(url),
                "channel": "applyall-blast",
                "source": "applyall-csv",
                "outcome": "expired",
                "outcome_reason": "no_response",
            })
    return records


def load_all_linkedin_csvs() -> list[dict]:
    """Load all LinkedIn Job Applications CSV files."""
    if not LINKEDIN_DIR.exists():
        return []
    records = []
    for csv_file in sorted(LINKEDIN_DIR.glob("Job Applications*.csv")):
        records.extend(parse_linkedin_csv(csv_file))
    return records


def deduplicate(records: list[dict]) -> list[dict]:
    """Deduplicate on (company_lower, title_lower, applied_date)."""
    seen = set()
    unique = []
    for r in records:
        key = (
            r["company"].lower().strip(),
            r["title"].lower().strip(),
            r.get("applied_date", ""),
        )
        if key not in seen:
            seen.add(key)
            unique.append(r)
    return unique


def compute_stats(records: list[dict]) -> dict:
    """Compute summary statistics from ingested records."""
    channels = Counter(r["channel"] for r in records)
    portals = Counter(r["portal"] for r in records)
    months: Counter = Counter()
    for r in records:
        d = r.get("applied_date", "")
        if d and len(d) >= 7:
            months[d[:7]] += 1
    return {
        "total": len(records),
        "by_channel": dict(channels.most_common()),
        "by_portal": dict(portals.most_common()),
        "by_month": dict(sorted(months.items())),
        "unique_companies": len({r["company"].lower() for r in records}),
        "date_range": {
            "earliest": min((r["applied_date"] for r in records if r.get("applied_date")), default=None),
            "latest": max((r["applied_date"] for r in records if r.get("applied_date")), default=None),
        },
    }


def write_historical_outcomes(records: list[dict], output_path: Path = OUTPUT_PATH) -> Path:
    """Write historical outcomes to YAML."""
    full_name = load_identity()["person"]["full_name"]
    slug = full_name.replace(" ", "_")
    data = {
        "metadata": {
            "generated": datetime.now().isoformat(),
            "source_files": [
                "intake/linkedin-export/LinkedInDataExport_12-25-2025/Jobs/Job Applications*.csv",
                f"intake/{slug}_applied_applications.csv",
            ],
            "total_records": len(records),
            "note": "Historical pre-pipeline applications. All outcomes are 'expired' (no response received).",
        },
        "stats": compute_stats(records),
        "entries": records,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest historical job application data")
    parser.add_argument("--write", action="store_true", help="Write historical-outcomes.yaml")
    parser.add_argument("--stats", action="store_true", help="Summary statistics only")
    parser.add_argument("--json", action="store_true", dest="json_output", help="JSON output")
    args = parser.parse_args()

    # Load from both sources
    linkedin_records = load_all_linkedin_csvs()
    applyall_records = []
    if APPLYALL_CSV.exists():
        applyall_records = parse_applyall_csv(APPLYALL_CSV)

    combined = linkedin_records + applyall_records
    deduped = deduplicate(combined)
    stats = compute_stats(deduped)

    if args.json_output:
        print(json.dumps(stats, indent=2))
        return

    if args.stats:
        print(f"Total records (pre-dedup): {len(combined)}")
        print(f"Total records (deduped):   {len(deduped)}")
        print(f"LinkedIn records:          {len(linkedin_records)}")
        print(f"ApplyAll records:          {len(applyall_records)}")
        print(f"Unique companies:          {stats['unique_companies']}")
        print(f"Date range:                {stats['date_range']['earliest']} to {stats['date_range']['latest']}")
        print("\nBy channel:")
        for ch, n in stats["by_channel"].items():
            print(f"  {ch}: {n}")
        print("\nBy portal:")
        for p, n in stats["by_portal"].items():
            print(f"  {p}: {n}")
        return

    if args.write:
        path = write_historical_outcomes(deduped)
        print(f"Wrote {len(deduped)} records to {path}")
        return

    # Dry-run: show what would be written
    print(f"DRY RUN — would write {len(deduped)} records to {OUTPUT_PATH}")
    print(f"  LinkedIn: {len(linkedin_records)}, ApplyAll: {len(applyall_records)}")
    print(f"  Removed {len(combined) - len(deduped)} duplicates")
    print("\nRun with --write to persist, or --stats for full statistics.")


if __name__ == "__main__":
    main()
