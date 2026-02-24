#!/usr/bin/env python3
"""Submit applications to Greenhouse Job Board API.

Uses the public candidate-facing API to submit applications via multipart
form POST. Supports dry-run preview and batch submission for all Greenhouse
entries in the pipeline.

Usage:
    python scripts/greenhouse_submit.py --target together-ai          # dry-run preview
    python scripts/greenhouse_submit.py --target together-ai --submit # POST to Greenhouse
    python scripts/greenhouse_submit.py --batch                       # dry-run all
    python scripts/greenhouse_submit.py --batch --submit              # submit all
    python scripts/greenhouse_submit.py --init-answers --target together-ai  # generate answer template
    python scripts/greenhouse_submit.py --init-answers --batch               # generate all templates
    python scripts/greenhouse_submit.py --check-answers --batch              # validate all answers
"""

import argparse
import json
import os
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
ANSWERS_DIR = Path(__file__).resolve().parent / ".greenhouse-answers"

# URL pattern: job-boards.greenhouse.io/{board_token}/jobs/{job_id}
GREENHOUSE_URL_RE = re.compile(
    r"job-boards\.greenhouse\.io/(?P<board>[^/]+)/jobs/(?P<job_id>\d+)"
)

# Standard fields handled outside the answer system
STANDARD_FIELD_NAMES = {
    "first_name", "last_name", "email", "phone",
    "resume", "resume_text", "cover_letter", "cover_letter_text",
}

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


def fetch_job_data(board_token: str, job_id: str) -> dict | None:
    """Fetch full job data from the Greenhouse Job Board API.

    GET https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs/{job_id}?questions=true

    Returns the full job dict (title, content, location, departments, questions, etc.)
    or None on failure.
    """
    import urllib.request
    import urllib.error

    url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs/{job_id}?questions=true"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as e:
        print(f"  Warning: Could not fetch job data: {e}", file=sys.stderr)
        return None


def fetch_job_questions(board_token: str, job_id: str) -> list[dict]:
    """Fetch required custom questions from the Greenhouse Job Board API.

    GET https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs/{job_id}?questions=true

    Returns list of question dicts with 'label', 'required', 'fields' keys.
    """
    data = fetch_job_data(board_token, job_id)
    if data is None:
        return []
    return data.get("questions", [])


# ---------------------------------------------------------------------------
# Answer management
# ---------------------------------------------------------------------------


def get_custom_questions(questions: list[dict]) -> list[dict]:
    """Filter questions to only custom ones (not standard name/email/etc)."""
    custom = []
    for q in questions:
        fields = q.get("fields", [])
        # Skip if all fields are standard
        if fields and all(f.get("name") in STANDARD_FIELD_NAMES for f in fields):
            continue
        custom.append(q)
    return custom


def field_type_label(field: dict) -> str:
    """Human-readable type string for a question field."""
    ftype = field.get("type", "unknown")
    type_map = {
        "input_text": "text",
        "textarea": "textarea",
        "multi_value_single_select": "select",
        "input_file": "file",
    }
    return type_map.get(ftype, ftype)


def resolve_select_value(answer_str: str, values_list: list[dict]) -> int | str | None:
    """Resolve a string answer like 'Yes' to the integer value from the values list.

    Returns the integer value if matched, the original string if no values list,
    or None if no match found.
    """
    if not values_list:
        return answer_str
    answer_lower = str(answer_str).strip().lower()
    for v in values_list:
        if str(v.get("label", "")).strip().lower() == answer_lower:
            return v.get("value", answer_str)
    # Try matching against the value itself (in case user provided the int)
    for v in values_list:
        if str(v.get("value", "")).strip() == str(answer_str).strip():
            return v.get("value", answer_str)
    return None


def auto_fill_answers(questions: list[dict], config: dict, entry: dict) -> dict:
    """Auto-map standard question patterns to config/entry values.

    Returns dict of {field_name: answer_value} for auto-fillable questions.
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

    for q in get_custom_questions(questions):
        label = q.get("label", "")
        fields = q.get("fields", [])
        for field in fields:
            fname = field.get("name", "")
            if fname in STANDARD_FIELD_NAMES:
                continue
            # Check each auto-fill pattern
            for pattern, source_key in AUTO_FILL_PATTERNS:
                if pattern.search(label):
                    value = source_map.get(source_key, "")
                    if value:
                        answers[fname] = value
                    break

    return answers


def load_answers(entry_id: str) -> dict | None:
    """Load answers from the per-entry YAML file.

    Returns dict of {field_name: answer_value}, or None if file doesn't exist.
    """
    answer_path = ANSWERS_DIR / f"{entry_id}.yaml"
    if not answer_path.exists():
        return None
    data = yaml.safe_load(answer_path.read_text())
    if not isinstance(data, dict):
        return None
    # Filter out None/empty and FILL IN placeholders
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


def validate_answers(questions: list[dict], merged_answers: dict) -> list[str]:
    """Validate that all required custom questions have answers.

    Returns list of error strings for missing/incomplete fields.
    """
    errors = []
    for q in get_custom_questions(questions):
        if not q.get("required"):
            continue
        label = q.get("label", "?")
        fields = q.get("fields", [])
        for field in fields:
            fname = field.get("name", "")
            if fname in STANDARD_FIELD_NAMES:
                continue
            if fname not in merged_answers:
                errors.append(f"MISSING required: {label} ({fname})")
            else:
                val = str(merged_answers[fname]).strip()
                if not val or val == "FILL IN":
                    errors.append(f"EMPTY required: {label} ({fname})")
    return errors


def resolve_all_answers(
    questions: list[dict], merged_answers: dict
) -> dict:
    """Resolve string answers to API values (e.g. 'Yes' -> 1 for selects).

    Returns dict of {field_name: resolved_value} ready for POST.
    """
    resolved = {}
    field_meta = {}
    for q in get_custom_questions(questions):
        for field in q.get("fields", []):
            fname = field.get("name", "")
            field_meta[fname] = field

    for fname, answer in merged_answers.items():
        field = field_meta.get(fname)
        if field and field.get("type") == "multi_value_single_select":
            values_list = field.get("values", [])
            resolved_val = resolve_select_value(answer, values_list)
            if resolved_val is not None:
                resolved[fname] = resolved_val
            else:
                # Keep original — will likely fail but lets the user see it
                resolved[fname] = answer
        else:
            resolved[fname] = answer

    return resolved


def generate_answer_template(
    entry_id: str, entry_name: str, board_token: str, job_id: str,
    questions: list[dict], auto_filled: dict,
) -> str:
    """Render a YAML answer template with comments for each question."""
    lines = [
        f"# Generated for: {entry_name}",
        f"# Job: {board_token}/{job_id}",
        f"# Edit answers below, then run with --check-answers to validate",
        "",
    ]

    for q in get_custom_questions(questions):
        label = q.get("label", "?")
        required = q.get("required", False)
        fields = q.get("fields", [])

        for field in fields:
            fname = field.get("name", "")
            if fname in STANDARD_FIELD_NAMES:
                continue
            ftype = field_type_label(field)
            values = field.get("values", [])

            # Build comment
            comment_parts = [f"# {label}"]
            type_str = f"# Type: {ftype}"
            if values:
                opts = ", ".join(v.get("label", "?") for v in values)
                type_str += f" | Options: {opts}"
            type_str += f" | {'Required' if required else 'Optional'}"
            comment_parts.append(type_str)

            lines.extend(comment_parts)

            # Value: auto-filled or placeholder
            if fname in auto_filled:
                val = auto_filled[fname]
                if "\n" in str(val):
                    lines.append(f"{fname}: |")
                    for vline in str(val).split("\n"):
                        lines.append(f"  {vline}")
                else:
                    lines.append(f'{fname}: "{val}"')
            elif ftype == "textarea":
                lines.append(f"{fname}: |")
                lines.append("  FILL IN")
            elif ftype == "select" and values:
                # Default to first option as hint
                lines.append(f'{fname}: "FILL IN"')
            else:
                lines.append(f'{fname}: "FILL IN"')

            lines.append("")

    return "\n".join(lines)


def init_answers_for_entry(
    entry: dict, config: dict, force: bool = False
) -> bool:
    """Generate answer template for a single entry. Returns True on success."""
    entry_id = entry.get("id", "?")
    name = entry.get("name", entry_id)

    portal = entry.get("target", {}).get("portal", "")
    if portal != "greenhouse":
        print(f"  Skipping {entry_id}: portal is '{portal}', not greenhouse")
        return False

    app_url = entry.get("target", {}).get("application_url", "")
    parsed = parse_greenhouse_url(app_url)
    if not parsed:
        print(f"  Error: Cannot parse Greenhouse URL for {entry_id}: {app_url}")
        return False
    board_token, job_id = parsed

    answer_path = ANSWERS_DIR / f"{entry_id}.yaml"
    if answer_path.exists() and not force:
        print(f"  {entry_id}: Answer file exists (use --force to overwrite)")
        return False

    print(f"  Fetching questions for {entry_id} ({board_token}/{job_id})...")
    questions = fetch_job_questions(board_token, job_id)
    if not questions:
        print(f"  Warning: No questions returned for {entry_id}")
        return False

    custom_qs = get_custom_questions(questions)
    if not custom_qs:
        print(f"  {entry_id}: No custom questions (only standard fields)")
        return True

    auto_filled = auto_fill_answers(questions, config, entry)

    template = generate_answer_template(
        entry_id, name, board_token, job_id, questions, auto_filled
    )

    ANSWERS_DIR.mkdir(parents=True, exist_ok=True)
    answer_path.write_text(template)

    # Count fields
    total_fields = sum(
        1 for q in custom_qs for f in q.get("fields", [])
        if f.get("name") not in STANDARD_FIELD_NAMES
    )
    auto_count = len(auto_filled)
    manual_count = total_fields - auto_count

    print(f"  {entry_id}: Wrote {answer_path.name}")
    print(f"    {total_fields} custom fields: {auto_count} auto-filled, {manual_count} need manual answers")
    return True


def check_answers_for_entry(entry: dict, config: dict) -> bool:
    """Validate answers for a single entry. Returns True if all required answered."""
    entry_id = entry.get("id", "?")
    name = entry.get("name", entry_id)

    portal = entry.get("target", {}).get("portal", "")
    if portal != "greenhouse":
        print(f"  Skipping {entry_id}: not greenhouse")
        return False

    app_url = entry.get("target", {}).get("application_url", "")
    parsed = parse_greenhouse_url(app_url)
    if not parsed:
        print(f"  Error: Cannot parse URL for {entry_id}")
        return False
    board_token, job_id = parsed

    questions = fetch_job_questions(board_token, job_id)
    if not questions:
        print(f"  {entry_id}: No questions (cannot validate)")
        return False

    auto_filled = auto_fill_answers(questions, config, entry)
    file_answers = load_answers(entry_id)
    merged = merge_answers(auto_filled, file_answers)
    errors = validate_answers(questions, merged)

    if errors:
        print(f"  {entry_id}: {len(errors)} issue(s)")
        for err in errors:
            print(f"    - {err}")
        return False
    else:
        source_note = ""
        if file_answers is None:
            source_note = " (auto-fill only, no answer file)"
        print(f"  {entry_id}: All required questions answered{source_note}")
        return True


# ---------------------------------------------------------------------------
# Core submission functions
# ---------------------------------------------------------------------------


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
    resolved_answers: dict | None = None,
    answer_sources: dict | None = None,
    validation_errors: list[str] | None = None,
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
        custom_qs = get_custom_questions(questions)
        if custom_qs and resolved_answers is not None:
            # Enhanced preview with answer status
            sources = answer_sources or {}
            print(f"  CUSTOM QUESTIONS ({len(custom_qs)}):")
            for q in custom_qs:
                label = q.get("label", "?")
                required = q.get("required", False)
                req_tag = "REQ" if required else "opt"
                fields = q.get("fields", [])
                for field in fields:
                    fname = field.get("name", "")
                    if fname in STANDARD_FIELD_NAMES:
                        continue
                    ftype = field_type_label(field)
                    if fname in resolved_answers:
                        val = resolved_answers[fname]
                        src = sources.get(fname, "?")
                        val_display = str(val)
                        if len(val_display) > 60:
                            val_display = val_display[:57] + "..."
                        print(f"    [{req_tag}] {label}")
                        print(f"          -> {val_display}  ({ftype}, {src})")
                    else:
                        print(f"    [{req_tag}] {label}")
                        print(f"          -> MISSING  ({ftype}, {fname})")
            print()

            if validation_errors:
                print(f"  ANSWER VALIDATION ({len(validation_errors)} issue(s)):")
                for err in validation_errors:
                    print(f"    ! {err}")
                print()
        else:
            # Fallback: simple question listing
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
    answers: dict | None = None,
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

    # Add custom question answers
    if answers:
        for fname, value in answers.items():
            add_field(fname, str(value))

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

    # Greenhouse Job Board API requires HTTP Basic auth (API key as username)
    gh_api_key = config.get("greenhouse_api_key", "") or os.environ.get("GREENHOUSE_API_KEY", "")
    if gh_api_key:
        import base64
        credentials = base64.b64encode(f"{gh_api_key}:".encode()).decode()
        headers["Authorization"] = f"Basic {credentials}"

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

    # Fetch job questions
    questions = fetch_job_questions(board_token, job_id)

    # Resolve custom question answers
    resolved_answers = {}
    answer_sources = {}
    validation_errors = []

    if questions:
        auto_filled = auto_fill_answers(questions, config, entry)
        file_answers = load_answers(entry_id)
        merged = merge_answers(auto_filled, file_answers)

        # Track sources for preview
        for fname in merged:
            if file_answers and fname in file_answers:
                answer_sources[fname] = "answer-file"
            elif fname in auto_filled:
                answer_sources[fname] = "auto"

        resolved_answers = resolve_all_answers(questions, merged)
        validation_errors = validate_answers(questions, merged)

    if not do_submit:
        preview_submission(
            entry, config, board_token, job_id,
            cover_letter_text, resume_path, questions,
            resolved_answers, answer_sources, validation_errors,
        )
        return True

    # Check for missing required answers before submitting
    if validation_errors:
        print(f"\n  Cannot submit {entry_id}: {len(validation_errors)} required answer(s) missing:")
        for err in validation_errors:
            print(f"    - {err}")
        print(f"  Run --init-answers --target {entry_id} to generate answer template")
        return False

    # Actually submit
    portfolio_url = ""
    submission = entry.get("submission", {})
    if isinstance(submission, dict):
        portfolio_url = submission.get("portfolio_url", "")

    print(f"\nSubmitting: {name} ({board_token}/{job_id})...")
    return submit_to_greenhouse(
        board_token, job_id, config,
        cover_letter_text, resume_path, portfolio_url,
        answers=resolved_answers,
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
    parser.add_argument("--init-answers", action="store_true",
                        help="Generate answer template YAML for custom questions")
    parser.add_argument("--check-answers", action="store_true",
                        help="Validate that all required questions have answers")
    parser.add_argument("--force", action="store_true",
                        help="Overwrite existing answer files (with --init-answers)")
    args = parser.parse_args()

    if not args.target and not args.batch:
        parser.error("Specify --target <id> or --batch")

    config = load_config()

    # Resolve entries
    if args.batch:
        entries = find_greenhouse_entries()
        if not entries:
            print("No Greenhouse entries found in active pipeline.")
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
        ok = process_entry(entries[0], config, args.submit)
        if not ok and args.submit:
            sys.exit(1)


if __name__ == "__main__":
    main()
