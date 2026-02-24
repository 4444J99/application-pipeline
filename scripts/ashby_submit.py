#!/usr/bin/env python3
"""Submit applications to Ashby Application Form API.

Uses the Ashby posting API to fetch form schemas and submit applications
via multipart form POST. Supports dry-run preview and batch submission.

Usage:
    python scripts/ashby_submit.py --target <id>              # dry-run preview
    python scripts/ashby_submit.py --target <id> --submit     # POST to Ashby
    python scripts/ashby_submit.py --batch                    # dry-run all
    python scripts/ashby_submit.py --batch --submit           # submit all
    python scripts/ashby_submit.py --init-answers --target <id>   # generate answer template
    python scripts/ashby_submit.py --check-answers --batch        # validate all answers
"""

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

from pipeline_lib import (
    MATERIALS_DIR, REPO_ROOT, VARIANTS_DIR,
    load_entries, load_entry_by_id,
    strip_markdown,
    PIPELINE_DIR_ACTIVE,
)

CONFIG_PATH = Path(__file__).resolve().parent / ".submit-config.yaml"
ANSWERS_DIR = Path(__file__).resolve().parent / ".ashby-answers"

# URL pattern: jobs.ashbyhq.com/{company}/{uuid}
ASHBY_URL_RE = re.compile(
    r"jobs\.ashbyhq\.com/(?P<company>[^/]+)/(?P<posting_id>[a-f0-9-]+)"
)

ASHBY_API_BASE = "https://api.ashbyhq.com"

# Standard field paths handled outside the answer system
STANDARD_FIELD_PATHS = {"_systemfield_name", "_systemfield_email", "_systemfield_phone"}

# Label patterns for auto-fill (compiled once)
AUTO_FILL_PATTERNS = [
    (re.compile(r"website|portfolio|github|personal.*url", re.I), "portfolio_url"),
    (re.compile(r"linkedin", re.I), "linkedin"),
    (re.compile(r"pronounc|phonetic", re.I), "name_pronunciation"),
    (re.compile(r"pronoun", re.I), "pronouns"),
    (re.compile(r"address|city|location|plan on working|where.*located|where.*based", re.I), "location"),
]


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


def parse_ashby_url(url: str) -> tuple[str, str] | None:
    """Extract (company, posting_id) from an Ashby application URL.

    Returns None if the URL does not match the Ashby pattern.
    """
    m = ASHBY_URL_RE.search(url)
    if m:
        return m.group("company"), m.group("posting_id")
    return None


def _post_json(endpoint: str, payload: dict, api_key: str | None = None) -> dict | None:  # allow-secret
    """POST JSON to Ashby API and return parsed response."""
    import urllib.request
    import urllib.error
    import base64

    url = f"{ASHBY_API_BASE}/{endpoint}"
    data = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if api_key:
        credentials = base64.b64encode(f"{api_key}:".encode()).decode()
        headers["Authorization"] = f"Basic {credentials}"

    try:
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as e:
        print(f"  Warning: Ashby API error ({endpoint}): {e}", file=sys.stderr)
        return None


def fetch_posting_info(posting_id: str) -> dict | None:
    """Fetch posting info from the Ashby public posting API.

    POST https://api.ashbyhq.com/posting-api/posting-info
    Body: {"postingId": "<uuid>"}

    Returns the posting info dict or None on failure.
    """
    result = _post_json("posting-api/posting-info", {"postingId": posting_id})
    if result and result.get("success") is not False:
        return result
    return None


def fetch_form_schema(posting_id: str) -> list[dict]:
    """Fetch the application form schema for a posting.

    The form definition is included in the posting info under
    'applicationForm.sections[].fields[]'.

    Returns a flat list of field dicts.
    """
    info = fetch_posting_info(posting_id)
    if not info:
        return []

    form = info.get("applicationForm", {})
    if not isinstance(form, dict):
        return []

    fields = []
    for section in form.get("sections", []):
        for field in section.get("fields", []):
            fields.append(field)

    return fields


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


# ---------------------------------------------------------------------------
# Answer management
# ---------------------------------------------------------------------------


def is_standard_field(field: dict) -> bool:
    """Check if a field is a standard system field (name, email, etc)."""
    path = field.get("path", "")
    field_type = field.get("type", "")
    if path in STANDARD_FIELD_PATHS:
        return True
    if field_type == "File":
        return True
    return False


def get_custom_fields(fields: list[dict]) -> list[dict]:
    """Filter fields to only custom ones (not standard name/email/resume)."""
    return [f for f in fields if not is_standard_field(f)]


def field_type_label(field: dict) -> str:
    """Human-readable type string for a form field."""
    ftype = field.get("type", "unknown")
    type_map = {
        "String": "text",
        "LongText": "textarea",
        "ValueSelect": "select",
        "MultiValueSelect": "multi-select",
        "Boolean": "boolean",
        "File": "file",
        "Phone": "phone",
        "Email": "email",
    }
    return type_map.get(ftype, ftype)


def auto_fill_answers(fields: list[dict], config: dict, entry: dict) -> dict:
    """Auto-map standard question patterns to config/entry values.

    Returns dict of {field_path: answer_value} for auto-fillable fields.
    """
    answers = {}
    submission = entry.get("submission", {}) or {}
    portfolio_url = submission.get("portfolio_url", "") if isinstance(submission, dict) else ""

    source_map = {
        "portfolio_url": portfolio_url,
        "linkedin": config.get("linkedin", ""),
        "name_pronunciation": config.get("name_pronunciation", ""),
        "pronouns": config.get("pronouns", ""),
        "location": config.get("location", ""),
    }

    for field in get_custom_fields(fields):
        title = field.get("title", "")
        path = field.get("path", "")
        for pattern, source_key in AUTO_FILL_PATTERNS:
            if pattern.search(title):
                value = source_map.get(source_key, "")
                if value:
                    answers[path] = value
                break

    return answers


def load_answers(entry_id: str) -> dict | None:
    """Load answers from the per-entry YAML file.

    Returns dict of {field_path: answer_value}, or None if file doesn't exist.
    """
    answer_path = ANSWERS_DIR / f"{entry_id}.yaml"
    if not answer_path.exists():
        return None
    data = yaml.safe_load(answer_path.read_text())
    if not isinstance(data, dict):
        return None
    cleaned = {}
    for k, v in data.items():
        if v is None:
            continue
        sv = str(v).strip()
        if sv and sv != "FILL IN":
            cleaned[k] = v
    return cleaned


def merge_answers(auto_filled: dict, file_answers: dict | None) -> dict:
    """Merge auto-filled and file answers. File answers take precedence."""
    merged = dict(auto_filled)
    if file_answers:
        merged.update(file_answers)
    return merged


def validate_answers(fields: list[dict], merged_answers: dict) -> list[str]:
    """Validate that all required custom fields have answers.

    Returns list of error strings for missing/incomplete fields.
    """
    errors = []
    for field in get_custom_fields(fields):
        if not field.get("isRequired"):
            continue
        title = field.get("title", "?")
        path = field.get("path", "")
        if path not in merged_answers:
            errors.append(f"MISSING required: {title} ({path})")
        else:
            val = str(merged_answers[path]).strip()
            if not val or val == "FILL IN":
                errors.append(f"EMPTY required: {title} ({path})")
    return errors


def generate_answer_template(
    entry_id: str, entry_name: str, company: str, posting_id: str,
    fields: list[dict], auto_filled: dict,
) -> str:
    """Render a YAML answer template with comments for each field."""
    lines = [
        f"# Generated for: {entry_name}",
        f"# Posting: {company}/{posting_id}",
        f"# Edit answers below, then run with --check-answers to validate",
        "",
    ]

    for field in get_custom_fields(fields):
        title = field.get("title", "?")
        path = field.get("path", "")
        required = field.get("isRequired", False)
        ftype = field_type_label(field)
        select_values = field.get("selectableValues", [])

        comment_parts = [f"# {title}"]
        type_str = f"# Type: {ftype}"
        if select_values:
            opts = ", ".join(v.get("label", "?") for v in select_values)
            type_str += f" | Options: {opts}"
        type_str += f" | {'Required' if required else 'Optional'}"
        comment_parts.append(type_str)
        lines.extend(comment_parts)

        if path in auto_filled:
            val = auto_filled[path]
            if "\n" in str(val):
                lines.append(f"{path}: |")
                for vline in str(val).split("\n"):
                    lines.append(f"  {vline}")
            else:
                lines.append(f'{path}: "{val}"')
        elif ftype == "textarea":
            lines.append(f"{path}: |")
            lines.append("  FILL IN")
        else:
            lines.append(f'{path}: "FILL IN"')

        lines.append("")

    return "\n".join(lines)


def init_answers_for_entry(
    entry: dict, config: dict, force: bool = False
) -> bool:
    """Generate answer template for a single entry. Returns True on success."""
    entry_id = entry.get("id", "?")
    name = entry.get("name", entry_id)

    portal = entry.get("target", {}).get("portal", "")
    if portal != "ashby":
        print(f"  Skipping {entry_id}: portal is '{portal}', not ashby")
        return False

    app_url = entry.get("target", {}).get("application_url", "")
    parsed = parse_ashby_url(app_url)
    if not parsed:
        print(f"  Error: Cannot parse Ashby URL for {entry_id}: {app_url}")
        return False
    company, posting_id = parsed

    answer_path = ANSWERS_DIR / f"{entry_id}.yaml"
    if answer_path.exists() and not force:
        print(f"  {entry_id}: Answer file exists (use --force to overwrite)")
        return False

    print(f"  Fetching form schema for {entry_id} ({company}/{posting_id})...")
    fields = fetch_form_schema(posting_id)
    custom_fields = get_custom_fields(fields)
    if not custom_fields:
        print(f"  {entry_id}: No custom fields found")
        return True

    auto_filled = auto_fill_answers(fields, config, entry)

    template = generate_answer_template(
        entry_id, name, company, posting_id, fields, auto_filled
    )

    ANSWERS_DIR.mkdir(parents=True, exist_ok=True)
    answer_path.write_text(template)

    auto_count = len(auto_filled)
    manual_count = len(custom_fields) - auto_count

    print(f"  {entry_id}: Wrote {answer_path.name}")
    print(f"    {len(custom_fields)} custom fields: {auto_count} auto-filled, {manual_count} need manual answers")
    return True


def check_answers_for_entry(entry: dict, config: dict) -> bool:
    """Validate answers for a single entry. Returns True if all required answered."""
    entry_id = entry.get("id", "?")

    portal = entry.get("target", {}).get("portal", "")
    if portal != "ashby":
        print(f"  Skipping {entry_id}: not ashby")
        return False

    app_url = entry.get("target", {}).get("application_url", "")
    parsed = parse_ashby_url(app_url)
    if not parsed:
        print(f"  Error: Cannot parse URL for {entry_id}")
        return False
    company, posting_id = parsed

    fields = fetch_form_schema(posting_id)
    if not fields:
        print(f"  {entry_id}: No form fields (cannot validate)")
        return False

    auto_filled = auto_fill_answers(fields, config, entry)
    file_answers = load_answers(entry_id)
    merged = merge_answers(auto_filled, file_answers)
    errors = validate_answers(fields, merged)

    if errors:
        print(f"  {entry_id}: {len(errors)} issue(s)")
        for err in errors:
            print(f"    - {err}")
        return False
    else:
        source_note = ""
        if file_answers is None:
            source_note = " (auto-fill only, no answer file)"
        print(f"  {entry_id}: All required fields answered{source_note}")
        return True


# ---------------------------------------------------------------------------
# Core submission functions
# ---------------------------------------------------------------------------


def build_field_submissions(
    fields: list[dict], config: dict, entry: dict, merged_answers: dict
) -> list[dict]:
    """Build the fieldSubmissions list for Ashby applicationForm.submit.

    Each entry is {"path": "...", "value": "..."}.
    """
    submissions = []

    # Standard fields
    full_name = f"{config['first_name']} {config['last_name']}"
    submissions.append({"path": "_systemfield_name", "value": full_name})
    submissions.append({"path": "_systemfield_email", "value": config["email"]})
    phone = config.get("phone", "")
    if phone and "FILL_IN" not in phone:
        submissions.append({"path": "_systemfield_phone", "value": phone})

    # Custom field answers
    for field in get_custom_fields(fields):
        path = field.get("path", "")
        if path in merged_answers:
            value = merged_answers[path]
            # For select fields, resolve label to value
            select_values = field.get("selectableValues", [])
            if select_values:
                answer_lower = str(value).strip().lower()
                for sv in select_values:
                    if str(sv.get("label", "")).strip().lower() == answer_lower:
                        value = sv.get("value", value)
                        break
            submissions.append({"path": path, "value": str(value)})

    return submissions


def preview_submission(
    entry: dict,
    config: dict,
    company: str,
    posting_id: str,
    cover_letter_text: str,
    resume_path: Path | None,
    fields: list[dict],
    merged_answers: dict | None = None,
    validation_errors: list[str] | None = None,
) -> None:
    """Display a dry-run preview of what would be submitted."""
    entry_id = entry.get("id", "?")
    name = entry.get("name", entry_id)
    org = entry.get("target", {}).get("organization", "")

    print(f"\n{'=' * 60}")
    print(f"ASHBY SUBMISSION PREVIEW: {name}")
    print(f"{'=' * 60}")
    print(f"  Organization:  {org}")
    print(f"  Company slug:  {company}")
    print(f"  Posting ID:    {posting_id}")
    print(f"  API endpoint:  POST {ASHBY_API_BASE}/applicationForm.submit")
    print()
    print(f"  APPLICANT INFO:")
    full_name = f"{config['first_name']} {config['last_name']}"
    print(f"    Name:     {full_name}")
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

    if cover_letter_text:
        print(f"  COVER LETTER ({len(cover_letter_text)} chars, {len(cover_letter_text.split())} words):")
        cl_lines = cover_letter_text.split("\n")
        for line in cl_lines[:3]:
            print(f"    {line[:100]}")
        if len(cl_lines) > 3:
            print(f"    ... ({len(cl_lines) - 3} more lines)")
    else:
        print(f"  COVER LETTER: None")
    print()

    if resume_path:
        print(f"  RESUME: {resume_path.name} ({resume_path.stat().st_size:,} bytes)")
    else:
        print(f"  RESUME: NOT FOUND")
    print()

    if fields:
        custom_fields = get_custom_fields(fields)
        if custom_fields:
            answers = merged_answers or {}
            print(f"  CUSTOM FIELDS ({len(custom_fields)}):")
            for field in custom_fields:
                title = field.get("title", "?")
                path = field.get("path", "")
                required = field.get("isRequired", False)
                req_tag = "REQ" if required else "opt"
                ftype = field_type_label(field)
                if path in answers:
                    val = str(answers[path])
                    if len(val) > 60:
                        val = val[:57] + "..."
                    print(f"    [{req_tag}] {title}")
                    print(f"          -> {val}  ({ftype})")
                else:
                    print(f"    [{req_tag}] {title}")
                    print(f"          -> MISSING  ({ftype}, {path})")
            print()

    if validation_errors:
        print(f"  ANSWER VALIDATION ({len(validation_errors)} issue(s)):")
        for err in validation_errors:
            print(f"    ! {err}")
        print()

    print(f"  STATUS: DRY RUN — use --submit to POST")


def submit_to_ashby(
    posting_id: str,
    api_key: str,  # allow-secret
    field_submissions: list[dict],
    resume_path: Path | None,
) -> bool:
    """POST application to Ashby applicationForm.submit.

    Uses multipart form data to support resume file upload.
    Returns True on success, False on failure.
    """
    import urllib.request
    import urllib.error
    import base64
    import uuid

    url = f"{ASHBY_API_BASE}/applicationForm.submit"

    boundary = uuid.uuid4().hex
    body_parts = []

    def add_field(name: str, value: str) -> None:
        body_parts.append(
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
            f"{value}\r\n"
        )

    # Add posting ID
    add_field("jobPostingId", posting_id)

    # Add field submissions as JSON
    add_field("fieldSubmissions", json.dumps(field_submissions))

    # Resume file upload
    resume_data = None
    if resume_path and resume_path.exists():
        resume_data = resume_path.read_bytes()
        body_parts.append(
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="resume"; filename="{resume_path.name}"\r\n'
            f"Content-Type: application/pdf\r\n\r\n"
        )

    # Assemble body
    text_body = "".join(body_parts).encode("utf-8")
    end_boundary = f"\r\n--{boundary}--\r\n".encode("utf-8")
    if resume_data:
        full_body = text_body + resume_data + end_boundary
    else:
        full_body = text_body + end_boundary

    headers = {
        "Content-Type": f"multipart/form-data; boundary={boundary}",
    }
    if api_key:
        credentials = base64.b64encode(f"{api_key}:".encode()).decode()
        headers["Authorization"] = f"Basic {credentials}"

    try:
        req = urllib.request.Request(url, data=full_body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:
            status = resp.status
            response_data = resp.read().decode()
        print(f"  Response: {status}")
        if status in (200, 201):
            try:
                result = json.loads(response_data)
                if result.get("success") is True:
                    app_id = result.get("applicationId", "unknown")
                    print(f"  SUCCESS: Application submitted to Ashby (ID: {app_id})")
                    return True
                else:
                    print(f"  Ashby returned success=false: {response_data[:500]}")
                    return False
            except json.JSONDecodeError:
                print(f"  SUCCESS: Application submitted (status {status})")
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
    """Process a single Ashby entry. Returns True if successful."""
    entry_id = entry.get("id", "?")
    name = entry.get("name", entry_id)

    portal = entry.get("target", {}).get("portal", "")
    if portal != "ashby":
        print(f"  Skipping {entry_id}: portal is '{portal}', not ashby")
        return False

    app_url = entry.get("target", {}).get("application_url", "")
    parsed = parse_ashby_url(app_url)
    if not parsed:
        print(f"  Error: Cannot parse Ashby URL for {entry_id}: {app_url}")
        return False
    company, posting_id = parsed

    cover_letter_text = resolve_cover_letter(entry) or ""
    resume_path = resolve_resume(entry)
    if not resume_path:
        print(f"  Error: No resume PDF found for {entry_id}")
        return False

    fields = fetch_form_schema(posting_id)

    merged_answers = {}
    validation_errors = []

    if fields:
        auto_filled = auto_fill_answers(fields, config, entry)
        file_answers = load_answers(entry_id)
        merged_answers = merge_answers(auto_filled, file_answers)
        validation_errors = validate_answers(fields, merged_answers)

    if not do_submit:
        preview_submission(
            entry, config, company, posting_id,
            cover_letter_text, resume_path, fields,
            merged_answers, validation_errors,
        )
        return True

    if validation_errors:
        print(f"\n  Cannot submit {entry_id}: {len(validation_errors)} required answer(s) missing:")
        for err in validation_errors:
            print(f"    - {err}")
        print(f"  Run --init-answers --target {entry_id} to generate answer template")
        return False

    # Get API key
    ashby_keys = config.get("ashby_api_keys", {})
    api_key = ""
    if isinstance(ashby_keys, dict):
        api_key = ashby_keys.get(company, "")  # allow-secret
    if not api_key:
        print(f"  Error: No Ashby API key for '{company}' in .submit-config.yaml")
        print(f"  Add ashby_api_keys.{company} to the config file")
        return False

    # Build field submissions
    field_submissions = build_field_submissions(fields, config, entry, merged_answers)

    print(f"\nSubmitting: {name} ({company}/{posting_id})...")
    return submit_to_ashby(posting_id, api_key, field_submissions, resume_path)


def find_ashby_entries() -> list[dict]:
    """Find all active pipeline entries with portal=ashby."""
    entries = load_entries(dirs=[PIPELINE_DIR_ACTIVE])
    return [e for e in entries if e.get("target", {}).get("portal") == "ashby"]


def main():
    parser = argparse.ArgumentParser(
        description="Submit applications to Ashby Application Form API"
    )
    parser.add_argument("--target", help="Target entry ID")
    parser.add_argument("--batch", action="store_true",
                        help="Process all Ashby entries in active pipeline")
    parser.add_argument("--submit", action="store_true",
                        help="Actually POST to Ashby (default is dry-run)")
    parser.add_argument("--init-answers", action="store_true",
                        help="Generate answer template YAML for custom fields")
    parser.add_argument("--check-answers", action="store_true",
                        help="Validate that all required fields have answers")
    parser.add_argument("--force", action="store_true",
                        help="Overwrite existing answer files (with --init-answers)")
    args = parser.parse_args()

    if not args.target and not args.batch:
        parser.error("Specify --target <id> or --batch")

    config = load_config()

    if args.batch:
        entries = find_ashby_entries()
        if not entries:
            print("No Ashby entries found in active pipeline.")
            sys.exit(1)
    else:
        _, entry = load_entry_by_id(args.target)
        if not entry:
            print(f"Error: No pipeline entry found for '{args.target}'", file=sys.stderr)
            sys.exit(1)
        entries = [entry]

    # --init-answers mode
    if args.init_answers:
        print(f"Generating answer templates for {len(entries)} entry(ies)...\n")
        results = []
        for entry in entries:
            ok = init_answers_for_entry(entry, config, force=args.force)
            results.append((entry.get("id"), ok))
        if len(results) > 1:
            print(f"\nSummary: {sum(1 for _, ok in results if ok)}/{len(results)} generated")
        return

    # --check-answers mode
    if args.check_answers:
        print(f"Checking answers for {len(entries)} entry(ies)...\n")
        results = []
        for entry in entries:
            ok = check_answers_for_entry(entry, config)
            results.append((entry.get("id"), ok))
        if len(results) > 1:
            passed = sum(1 for _, ok in results if ok)
            print(f"\nSummary: {passed}/{len(results)} fully answered")
        failed = sum(1 for _, ok in results if not ok)
        if failed:
            sys.exit(1)
        return

    # Standard preview/submit mode
    if args.batch:
        print(f"Found {len(entries)} Ashby entries:")
        for e in entries:
            print(f"  - {e.get('id')}: {e.get('name')}")
        print()

        results = []
        for entry in entries:
            ok = process_entry(entry, config, args.submit)
            results.append((entry.get("id"), ok))
            print()

        print("=" * 60)
        print("BATCH SUMMARY:")
        for eid, ok in results:
            status = "OK" if ok else "FAILED"
            print(f"  {eid}: {status}")
        failed = sum(1 for _, ok in results if not ok)
        if failed:
            sys.exit(1)
    else:
        ok = process_entry(entries[0], config, args.submit)
        if not ok and args.submit:
            sys.exit(1)


if __name__ == "__main__":
    main()
