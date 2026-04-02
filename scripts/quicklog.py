#!/usr/bin/env python3
"""Register an external application submission into the pipeline.

Usage:
    python scripts/quicklog.py --org "Grafana Labs" --role "Staff AI Engineer" --date 2026-03-26
"""

import argparse
import re
import sys
from datetime import date
from pathlib import Path

import yaml

# Add scripts dir to path so we can import pipeline_lib
sys.path.append(str(Path(__file__).resolve().parent))

try:
    import pipeline_lib
except ImportError:
    # If run from root or elsewhere
    from scripts import pipeline_lib

REPO_ROOT = Path(__file__).resolve().parent.parent


def _slugify(text: str) -> str:
    """Convert text to kebab-case slug for pipeline entry IDs."""
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text.strip('-')[:60]


def main():
    parser = argparse.ArgumentParser(description="Quick-log an external submission")
    parser.add_argument("--org", required=True, help="Organization name")
    parser.add_argument("--role", required=True, help="Role title")
    parser.add_argument("--date", help="Submission date (YYYY-MM-DD), defaults to today")
    parser.add_argument("--track", default="job", help="Track (job, grant, etc.)")
    parser.add_argument("--status", default="submitted", help="Status (submitted, interview, etc.)")
    parser.add_argument("--url", help="Application or job URL")
    parser.add_argument("--portal", help="ATS portal name (greenhouse, lever, etc.)")
    parser.add_argument("--location", default="US | Remote", help="Location string")

    args = parser.parse_args()

    sub_date = args.date or date.today().isoformat()
    org_slug = _slugify(args.org)
    role_slug = _slugify(args.role)
    entry_id = f"{org_slug}-{role_slug}"

    # Check if entry already exists
    dest_dir = REPO_ROOT / "pipeline" / args.status
    if args.status == "submitted":
        dest_dir = pipeline_lib.PIPELINE_DIR_SUBMITTED
    elif args.status == "active":
        dest_dir = pipeline_lib.PIPELINE_DIR_ACTIVE
    elif args.status == "interview":
        # Usually interview entries stay in submitted/ or active/? 
        # Actually in this system, 'interview' status entries often live in 'submitted/' or 'active/'
        # based on the directory structure. 
        # Wait, the Grafana one was in pipeline/submitted/ but status was 'interview'.
        dest_dir = pipeline_lib.PIPELINE_DIR_SUBMITTED
    
    dest_path = dest_dir / f"{entry_id}.yaml"
    
    # Check other directories too
    for d in pipeline_lib.ALL_PIPELINE_DIRS_WITH_POOL:
        if (d / f"{entry_id}.yaml").exists():
            print(f"Error: Entry {entry_id} already exists in {d.name}/", file=sys.stderr)
            sys.exit(1)

    # Basic entry structure
    entry = {
        "id": entry_id,
        "name": f"{args.org} {args.role}",
        "track": args.track,
        "status": args.status,
        "outcome": None,
        "target": {
            "organization": args.org,
            "url": args.url or "",
            "application_url": args.url or "",
            "portal": args.portal or "custom",
            "location": args.location,
            "location_class": "us-remote" if "remote" in args.location.lower() else "unknown",
        },
        "deadline": {
            "date": None,
            "type": "rolling",
        },
        "amount": {
            "value": 0,
            "currency": "USD",
            "type": "salary" if args.track == "job" else "stipend",
        },
        "fit": {
            "score": 0.0,
            "identity_position": "platform-orchestrator", # Default fallback
            "dimensions": {d: 5 for d in pipeline_lib.DIMENSION_ORDER},
        },
        "submission": {
            "effort_level": "standard",
            "blocks_used": {},
            "variant_ids": {},
            "materials_attached": [],
        },
        "timeline": {
            "submitted": sub_date,
        },
        "tags": ["applied-outside-pipeline"],
        "source": "manual",
        "last_touched": date.today().isoformat(),
        "status_meta": {
            "submitted_by": pipeline_lib.get_operator_name(),
            "submitted_at": sub_date,
            "review_note": f"Applied directly outside pipeline; retroactively logged on {date.today().isoformat()}",
        }
    }

    if args.status == "interview":
        entry["timeline"]["interview"] = sub_date # Assume if logged as interview, it happened or is happening

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(dest_path, "w") as f:
        yaml.dump(entry, f, sort_keys=False, default_flow_style=False)

    print(f"Registered external submission: {entry_id}")
    print(f"Path: {dest_path.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
