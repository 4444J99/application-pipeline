#!/usr/bin/env python3
"""Submit applications to Greenhouse Job Board API.

Uses the public candidate-facing API to submit applications via multipart
form POST. Supports dry-run preview and batch submission for all Greenhouse
entries in the pipeline.

Usage:
    python scripts/greenhouse_submit.py --target together-ai          # dry-run preview
    python scripts/greenhouse_submit.py --target together-ai --submit # POST to Greenhouse
    python scripts/greenhouse_submit.py --batch                       # dry-run all 4
    python scripts/greenhouse_submit.py --batch --submit              # submit all 4
"""

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

import yaml

from pipeline_lib import (
    MATERIALS_DIR, REPO_ROOT, VARIANTS_DIR,
    load_entries, load_entry_by_id,
    strip_markdown,
    PIPELINE_DIR_ACTIVE,
)

CONFIG_PATH = Path(__file__).resolve().parent / ".submit-config.yaml"

# URL pattern: job-boards.greenhouse.io/{board_token}/jobs/{job_id}
GREENHOUSE_URL_RE = re.compile(
    r"job-boards\.greenhouse\.io/(?P<board>[^/]+)/jobs/(?P<job_id>\d+)"
)


def load_config() -> dict:
    """Load personal info from .submit-config.yaml."""
    if not CONFIG_PATH.exists():
        print(f"Error: Config file not found: {CONFIG_PATH}", file=sys.stderr)
        print("Create it with first_name, last_name, email, phone fields.", file=sys.stderr)
        sys.exit(1)
    config = yaml.safe_load(CONFIG_PATH.read_text())
    if not isinstance(config, dict):
        print("Error: Config file is not a valid YAML dict.", file=sys.stderr)
        sys.exit(1)
    for field in ("first_name", "last_name", "email"):
        val = config.get(field, "")
        if not val or "FILL_IN" in str(val):
            print(f"Error: Fill in '{field}' in {CONFIG_PATH}", file=sys.stderr)
            sys.exit(1)
    return config


def parse_greenhouse_url(url: str) -> tuple[str, str] | None:
    """Extract (board_token, job_id) from a Greenhouse application URL."""
    m = GREENHOUSE_URL_RE.search(url)
    if m:
        return m.group("board"), m.group("job_id")
    return None


def resolve_cover_letter(entry: dict) -> str | None:
    """Resolve cover letter content from variant file, stripping markdown headers."""
    submission = entry.get("submission", {})
    if not isinstance(submission, dict):
        return None
    variant_ids = submission.get("variant_ids", {})
    if not isinstance(variant_ids, dict):
        return None
    cl_ref = variant_ids.get("cover_letter")
    if not cl_ref:
        return None
    variant_path = VARIANTS_DIR / cl_ref
    if not variant_path.suffix:
        variant_path = variant_path.with_suffix(".md")
    if not variant_path.exists():
        return None
    raw = variant_path.read_text().strip()
    # Strip the markdown header block (title, role, apply, salary, ---)
    lines = raw.split("\n")
    body_start = 0
    found_separator = False
    for i, line in enumerate(lines):
        if line.strip() == "---":
            if found_separator:
                body_start = i + 1
                break
            found_separator = True
    body = "\n".join(lines[body_start:]).strip()
    return strip_markdown(body)


def resolve_resume(entry: dict) -> Path | None:
    """Find the resume PDF from materials_attached."""
    submission = entry.get("submission", {})
    if not isinstance(submission, dict):
        return None
    materials = submission.get("materials_attached", [])
    if not isinstance(materials, list):
        return None
    for m in materials:
        mat_path = MATERIALS_DIR / m
        if mat_path.exists() and mat_path.suffix.lower() == ".pdf":
            return mat_path
    return None


def fetch_job_questions(board_token: str, job_id: str) -> list[dict]:
    """Fetch required custom questions from the Greenhouse Job Board API.

    GET https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs/{job_id}?questions=true

    Returns list of question dicts with 'label', 'required', 'fields' keys.
    """
    import urllib.request
    import urllib.error

    url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs/{job_id}?questions=true"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as e:
        print(f"  Warning: Could not fetch job questions: {e}", file=sys.stderr)
        return []

    questions = data.get("questions", [])
    return questions


def build_form_data(
    config: dict,
    entry: dict,
    cover_letter_text: str,
    resume_path: Path,
    questions: list[dict],
) -> dict:
    """Build the form fields dict for the Greenhouse submission.

    Returns dict with 'fields' (key-value pairs) and 'files' (key-path pairs).
    """
    fields = {
        "first_name": config["first_name"],
        "last_name": config["last_name"],
        "email": config["email"],
    }
    if config.get("phone"):
        fields["phone"] = config["phone"]

    # Portfolio URL
    submission = entry.get("submission", {})
    if isinstance(submission, dict):
        portfolio_url = submission.get("portfolio_url", "")
        if portfolio_url:
            # Try to find a website/portfolio question, otherwise use mapped field
            fields["website_url"] = portfolio_url

    files = {"resume": str(resume_path)}

    return {"fields": fields, "files": files, "cover_letter_text": cover_letter_text}


def preview_submission(
    entry: dict,
    config: dict,
    board_token: str,
    job_id: str,
    cover_letter_text: str,
    resume_path: Path | None,
    questions: list[dict],
) -> None:
    """Display a dry-run preview of what would be submitted."""
    entry_id = entry.get("id", "?")
    name = entry.get("name", entry_id)
    org = entry.get("target", {}).get("organization", "")

    print(f"\n{'=' * 60}")
    print(f"GREENHOUSE SUBMISSION PREVIEW: {name}")
    print(f"{'=' * 60}")
    print(f"  Organization:  {org}")
    print(f"  Board token:   {board_token}")  # allow-secret
    print(f"  Job ID:        {job_id}")
    print(f"  API endpoint:  POST https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs/{job_id}")
    print()
    print(f"  APPLICANT INFO:")
    print(f"    Name:     {config['first_name']} {config['last_name']}")
    print(f"    Email:    {config['email']}")
    phone = config.get("phone", "")
    if phone and "FILL_IN" not in phone:
        print(f"    Phone:    {phone}")
    submission = entry.get("submission", {})
    portfolio_url = ""
    if isinstance(submission, dict):
        portfolio_url = submission.get("portfolio_url", "")
    if portfolio_url:
        print(f"    Portfolio: {portfolio_url}")
    print()

    print(f"  COVER LETTER ({len(cover_letter_text)} chars, {len(cover_letter_text.split())} words):")
    # Show first 3 lines
    cl_lines = cover_letter_text.split("\n")
    for line in cl_lines[:3]:
        print(f"    {line[:100]}")
    if len(cl_lines) > 3:
        print(f"    ... ({len(cl_lines) - 3} more lines)")
    print()

    if resume_path:
        print(f"  RESUME: {resume_path.name} ({resume_path.stat().st_size:,} bytes)")
    else:
        print(f"  RESUME: NOT FOUND")
    print()

    if questions:
        required_qs = [q for q in questions if q.get("required")]
        optional_qs = [q for q in questions if not q.get("required")]
        if required_qs:
            print(f"  REQUIRED QUESTIONS ({len(required_qs)}):")
            for q in required_qs:
                label = q.get("label", "?")
                print(f"    * {label}")
        if optional_qs:
            print(f"  OPTIONAL QUESTIONS ({len(optional_qs)}):")
            for q in optional_qs:
                label = q.get("label", "?")
                print(f"      {label}")
        print()
    else:
        print("  QUESTIONS: None fetched (API may not have returned them)")
        print()

    print(f"  STATUS: DRY RUN — use --submit to POST")


def submit_to_greenhouse(
    board_token: str,
    job_id: str,
    config: dict,
    cover_letter_text: str,
    resume_path: Path,
    portfolio_url: str = "",
) -> bool:
    """POST application to Greenhouse Job Board API.

    Returns True on success, False on failure.
    """
    import urllib.request
    import urllib.error
    import uuid

    url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs/{job_id}"

    # Build multipart form data manually
    boundary = uuid.uuid4().hex
    body_parts = []

    def add_field(name: str, value: str) -> None:
        body_parts.append(
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
            f"{value}\r\n"
        )

    add_field("first_name", config["first_name"])
    add_field("last_name", config["last_name"])
    add_field("email", config["email"])
    phone = config.get("phone", "")
    if phone and "FILL_IN" not in phone:
        add_field("phone", phone)
    if portfolio_url:
        add_field("website_url", portfolio_url)
    add_field("cover_letter", cover_letter_text)

    # File upload for resume
    resume_data = resume_path.read_bytes()
    body_parts.append(
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="resume"; filename="{resume_path.name}"\r\n'
        f"Content-Type: application/pdf\r\n\r\n"
    )

    # Assemble the body
    text_body = "".join(body_parts).encode("utf-8")
    end_boundary = f"\r\n--{boundary}--\r\n".encode("utf-8")
    full_body = text_body + resume_data + end_boundary

    headers = {
        "Content-Type": f"multipart/form-data; boundary={boundary}",
    }

    try:
        req = urllib.request.Request(url, data=full_body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:
            status = resp.status
            response_data = resp.read().decode()
        print(f"  Response: {status}")
        if status in (200, 201):
            print(f"  SUCCESS: Application submitted to Greenhouse")
            return True
        else:
            print(f"  Unexpected status: {status}")
            print(f"  Body: {response_data[:500]}")
            return False
    except urllib.error.HTTPError as e:
        print(f"  HTTP Error: {e.code} {e.reason}")
        try:
            error_body = e.read().decode()
            print(f"  Body: {error_body[:500]}")
        except Exception:
            pass
        return False
    except urllib.error.URLError as e:
        print(f"  Connection error: {e.reason}")
        return False


def process_entry(entry: dict, config: dict, do_submit: bool) -> bool:
    """Process a single Greenhouse entry. Returns True if successful."""
    entry_id = entry.get("id", "?")
    name = entry.get("name", entry_id)

    # Verify portal type
    portal = entry.get("target", {}).get("portal", "")
    if portal != "greenhouse":
        print(f"  Skipping {entry_id}: portal is '{portal}', not greenhouse")
        return False

    # Parse URL
    app_url = entry.get("target", {}).get("application_url", "")
    parsed = parse_greenhouse_url(app_url)
    if not parsed:
        print(f"  Error: Cannot parse Greenhouse URL for {entry_id}: {app_url}")
        return False
    board_token, job_id = parsed

    # Resolve cover letter
    cover_letter_text = resolve_cover_letter(entry)
    if not cover_letter_text:
        print(f"  Error: No cover letter found for {entry_id}")
        return False

    # Resolve resume
    resume_path = resolve_resume(entry)
    if not resume_path:
        print(f"  Error: No resume PDF found for {entry_id}")
        return False

    # Fetch job questions (informational)
    questions = fetch_job_questions(board_token, job_id)

    if not do_submit:
        preview_submission(entry, config, board_token, job_id,
                           cover_letter_text, resume_path, questions)
        return True

    # Actually submit
    portfolio_url = ""
    submission = entry.get("submission", {})
    if isinstance(submission, dict):
        portfolio_url = submission.get("portfolio_url", "")

    print(f"\nSubmitting: {name} ({board_token}/{job_id})...")
    return submit_to_greenhouse(
        board_token, job_id, config,
        cover_letter_text, resume_path, portfolio_url,
    )


def find_greenhouse_entries() -> list[dict]:
    """Find all active pipeline entries with portal=greenhouse."""
    entries = load_entries(dirs=[PIPELINE_DIR_ACTIVE])
    return [e for e in entries if e.get("target", {}).get("portal") == "greenhouse"]


def main():
    parser = argparse.ArgumentParser(
        description="Submit applications to Greenhouse Job Board API"
    )
    parser.add_argument("--target", help="Target entry ID")
    parser.add_argument("--batch", action="store_true",
                        help="Process all Greenhouse entries in active pipeline")
    parser.add_argument("--submit", action="store_true",
                        help="Actually POST to Greenhouse (default is dry-run)")
    args = parser.parse_args()

    if not args.target and not args.batch:
        parser.error("Specify --target <id> or --batch")

    config = load_config()

    if args.batch:
        entries = find_greenhouse_entries()
        if not entries:
            print("No Greenhouse entries found in active pipeline.")
            sys.exit(1)
        print(f"Found {len(entries)} Greenhouse entries:")
        for e in entries:
            print(f"  - {e.get('id')}: {e.get('name')}")
        print()

        results = []
        for entry in entries:
            ok = process_entry(entry, config, args.submit)
            results.append((entry.get("id"), ok))
            print()

        # Summary
        print("=" * 60)
        print("BATCH SUMMARY:")
        for eid, ok in results:
            status = "OK" if ok else "FAILED"
            print(f"  {eid}: {status}")
        failed = sum(1 for _, ok in results if not ok)
        if failed:
            sys.exit(1)
    else:
        _, entry = load_entry_by_id(args.target)
        if not entry:
            print(f"Error: No pipeline entry found for '{args.target}'", file=sys.stderr)
            sys.exit(1)
        ok = process_entry(entry, config, args.submit)
        if not ok and args.submit:
            sys.exit(1)


if __name__ == "__main__":
    main()
