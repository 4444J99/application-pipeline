#!/usr/bin/env python3
"""Submit applications to Lever Postings API.

Uses the public candidate-facing API to submit applications via multipart
form POST. Supports dry-run preview and batch submission for all Lever
entries in the pipeline.

Usage:
    python scripts/lever_submit.py --target <id>              # dry-run preview
    python scripts/lever_submit.py --target <id> --submit     # POST to Lever
    python scripts/lever_submit.py --batch                    # dry-run all
    python scripts/lever_submit.py --batch --submit           # submit all
    python scripts/lever_submit.py --init-answers --target <id>   # generate answer template
    python scripts/lever_submit.py --check-answers --batch        # validate all answers
"""

import json
import re
import sys
import time
from pathlib import Path

from ats_base import (
    auto_fill_answer,
    build_common_argparse,
    build_normalized_answer_index,
    clean_answer_mapping,
    find_dynamic_answer,
    load_answers_yaml,
    load_config,
)
from pipeline_lib import (
    PIPELINE_DIR_ACTIVE,
    load_entries,
    load_entry_by_id,
    resolve_cover_letter,
    resolve_resume,
)

ANSWERS_DIR = Path(__file__).resolve().parent / ".lever-answers"

# URL patterns:
#   jobs.lever.co/{company}/{posting_id}
#   jobs.eu.lever.co/{company}/{posting_id}
LEVER_URL_RE = re.compile(
    r"jobs\.(?P<region>eu\.)?lever\.co/(?P<company>[^/]+)/(?P<posting_id>[a-f0-9-]+)"
)


def parse_lever_url(url: str) -> tuple[str, str, bool] | None:
    """Extract (company, posting_id, is_eu) from a Lever application URL.

    Returns None if the URL does not match the Lever pattern.
    """
    m = LEVER_URL_RE.search(url)
    if m:
        is_eu = bool(m.group("region"))
        return m.group("company"), m.group("posting_id"), is_eu
    return None


def _api_base(is_eu: bool) -> str:
    """Return the Lever API base URL."""
    if is_eu:
        return "https://api.eu.lever.co/v0/postings"
    return "https://api.lever.co/v0/postings"


def fetch_posting_data(company: str, posting_id: str, is_eu: bool) -> dict | None:
    """Fetch posting data from the Lever Postings API.

    GET {base}/{company}/{posting_id}

    Returns the posting dict or None on failure.
    """
    import urllib.error
    import urllib.request

    base = _api_base(is_eu)
    url = f"{base}/{company}/{posting_id}"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as e:
        print(f"  Warning: Could not fetch posting data: {e}", file=sys.stderr)
        return None


def fetch_posting_questions(company: str, posting_id: str, is_eu: bool) -> list[dict]:
    """Fetch custom questions for a Lever posting.

    The Lever Postings API includes questions in the posting data.
    Returns list of question dicts with 'text', 'required', 'type' keys.
    """
    data = fetch_posting_data(company, posting_id, is_eu)
    if data is None:
        return []
    # Lever returns custom questions in "lists" (sometimes "customQuestions")
    return data.get("lists", [])



# ---------------------------------------------------------------------------
# Answer management
# ---------------------------------------------------------------------------


def get_custom_questions(questions: list[dict]) -> list[dict]:
    """Filter questions to only custom ones (not standard name/email/etc).

    Lever custom questions are dicts with 'text' and optionally 'required'.
    """
    custom = []
    for q in questions:
        text = q.get("text", "")
        # Skip empty questions
        if not text:
            continue
        custom.append(q)
    return custom


def auto_fill_answers(questions: list[dict], config: dict, entry: dict) -> dict:
    """Auto-map standard question patterns to config/entry values.

    Returns dict of {question_text: answer_value} for auto-fillable questions.
    """
    answers = {}
    submission = entry.get("submission", {}) or {}
    portfolio_url = submission.get("portfolio_url", "") if isinstance(submission, dict) else ""

    for q in get_custom_questions(questions):
        text = q.get("text", "")
        value = auto_fill_answer(text, config, portfolio_url)
        if value:
            answers[text] = value

    return answers


def load_answers(entry_id: str) -> dict | None:
    """Load answers from the per-entry YAML file.

    Returns dict of {question_text: answer_value}, or None if file doesn't exist.
    """
    answer_path = ANSWERS_DIR / f"{entry_id}.yaml"
    data = load_answers_yaml(answer_path)
    if data is None:
        return None
    return clean_answer_mapping(data)


def map_file_answers_to_questions(questions: list[dict], file_answers: dict | None) -> dict:
    """Project dynamic answer-file keys onto current Lever question texts."""
    if not file_answers:
        return {}

    projected: dict[str, object] = {}
    normalized_index = build_normalized_answer_index(file_answers)

    for question in get_custom_questions(questions):
        text = question.get("text", "")
        if not text:
            continue
        answer = find_dynamic_answer(
            file_answers,
            field_key=text,
            label=text,
            normalized_index=normalized_index,
        )
        if answer is not None:
            projected[text] = answer
    return projected


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
        text = q.get("text", "?")
        if text not in merged_answers:
            errors.append(f"MISSING required: {text}")
        else:
            val = str(merged_answers[text]).strip()
            if not val or val == "FILL IN":
                errors.append(f"EMPTY required: {text}")
    return errors


def generate_answer_template(
    entry_id: str, entry_name: str, company: str, posting_id: str,
    questions: list[dict], auto_filled: dict,
) -> str:
    """Render a YAML answer template with comments for each question."""
    lines = [
        f"# Generated for: {entry_name}",
        f"# Posting: {company}/{posting_id}",
        "# Edit answers below, then run with --check-answers to validate",
        "",
    ]

    for q in get_custom_questions(questions):
        text = q.get("text", "?")
        required = q.get("required", False)

        comment_parts = [f"# {text}"]
        comment_parts.append(f"# {'Required' if required else 'Optional'}")
        lines.extend(comment_parts)

        # Sanitize key for YAML (quote if needed)
        yaml_key = f'"{text}"'

        if text in auto_filled:
            val = auto_filled[text]
            if "\n" in str(val):
                lines.append(f"{yaml_key}: |")
                for vline in str(val).split("\n"):
                    lines.append(f"  {vline}")
            else:
                lines.append(f'{yaml_key}: "{val}"')
        else:
            lines.append(f'{yaml_key}: "FILL IN"')

        lines.append("")

    return "\n".join(lines)


def init_answers_for_entry(
    entry: dict, config: dict, force: bool = False
) -> bool:
    """Generate answer template for a single entry. Returns True on success."""
    entry_id = entry.get("id", "?")
    name = entry.get("name", entry_id)

    portal = entry.get("target", {}).get("portal", "")
    if portal != "lever":
        print(f"  Skipping {entry_id}: portal is '{portal}', not lever")
        return False

    app_url = entry.get("target", {}).get("application_url", "")
    parsed = parse_lever_url(app_url)
    if not parsed:
        print(f"  Error: Cannot parse Lever URL for {entry_id}: {app_url}")
        return False
    company, posting_id, is_eu = parsed

    answer_path = ANSWERS_DIR / f"{entry_id}.yaml"
    if answer_path.exists() and not force:
        print(f"  {entry_id}: Answer file exists (use --force to overwrite)")
        return False

    print(f"  Fetching questions for {entry_id} ({company}/{posting_id})...")
    questions = fetch_posting_questions(company, posting_id, is_eu)
    custom_qs = get_custom_questions(questions)
    if not custom_qs:
        print(f"  {entry_id}: No custom questions found")
        return True

    auto_filled = auto_fill_answers(questions, config, entry)

    template = generate_answer_template(
        entry_id, name, company, posting_id, questions, auto_filled
    )

    ANSWERS_DIR.mkdir(parents=True, exist_ok=True)
    answer_path.write_text(template)

    auto_count = len(auto_filled)
    manual_count = len(custom_qs) - auto_count

    print(f"  {entry_id}: Wrote {answer_path.name}")
    print(f"    {len(custom_qs)} custom fields: {auto_count} auto-filled, {manual_count} need manual answers")
    return True


def check_answers_for_entry(entry: dict, config: dict) -> bool:
    """Validate answers for a single entry. Returns True if all required answered."""
    entry_id = entry.get("id", "?")

    portal = entry.get("target", {}).get("portal", "")
    if portal != "lever":
        print(f"  Skipping {entry_id}: not lever")
        return False

    app_url = entry.get("target", {}).get("application_url", "")
    parsed = parse_lever_url(app_url)
    if not parsed:
        print(f"  Error: Cannot parse URL for {entry_id}")
        return False
    company, posting_id, is_eu = parsed

    questions = fetch_posting_questions(company, posting_id, is_eu)
    if not questions:
        print(f"  {entry_id}: No questions (cannot validate)")
        return False

    auto_filled = auto_fill_answers(questions, config, entry)
    file_answers = load_answers(entry_id)
    mapped_file_answers = map_file_answers_to_questions(questions, file_answers)
    merged = merge_answers(auto_filled, mapped_file_answers)
    errors = validate_answers(questions, merged)

    if errors:
        print(f"  {entry_id}: {len(errors)} issue(s)")
        for err in errors:
            print(f"    - {err}")
        return False
    else:
        source_note = ""
        if not mapped_file_answers:
            source_note = " (auto-fill only, no answer file)"
        print(f"  {entry_id}: All required questions answered{source_note}")
        return True


# ---------------------------------------------------------------------------
# Core submission functions
# ---------------------------------------------------------------------------


def preview_submission(
    entry: dict,
    config: dict,
    company: str,
    posting_id: str,
    is_eu: bool,
    cover_letter_text: str,
    resume_path: Path | None,
    questions: list[dict],
    merged_answers: dict | None = None,
    validation_errors: list[str] | None = None,
) -> None:
    """Display a dry-run preview of what would be submitted."""
    entry_id = entry.get("id", "?")
    name = entry.get("name", entry_id)
    org = entry.get("target", {}).get("organization", "")
    base = _api_base(is_eu)

    print(f"\n{'=' * 60}")
    print(f"LEVER SUBMISSION PREVIEW: {name}")
    print(f"{'=' * 60}")
    print(f"  Organization:  {org}")
    print(f"  Company slug:  {company}")
    print(f"  Posting ID:    {posting_id}")
    print(f"  Region:        {'EU' if is_eu else 'US'}")
    print(f"  API endpoint:  POST {base}/{company}/{posting_id}")
    print()
    print("  APPLICANT INFO:")
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
        print("  COVER LETTER: None (will be sent as 'comments' field)")
    print()

    if resume_path:
        print(f"  RESUME: {resume_path.name} ({resume_path.stat().st_size:,} bytes)")
    else:
        print("  RESUME: NOT FOUND")
    print()

    if questions:
        custom_qs = get_custom_questions(questions)
        if custom_qs:
            print(f"  CUSTOM QUESTIONS ({len(custom_qs)}):")
            answers = merged_answers or {}
            for q in custom_qs:
                text = q.get("text", "?")
                required = q.get("required", False)
                req_tag = "REQ" if required else "opt"
                if text in answers:
                    val = str(answers[text])
                    if len(val) > 60:
                        val = val[:57] + "..."
                    print(f"    [{req_tag}] {text}")
                    print(f"          -> {val}")
                else:
                    print(f"    [{req_tag}] {text}")
                    print("          -> MISSING")
            print()

    if validation_errors:
        print(f"  ANSWER VALIDATION ({len(validation_errors)} issue(s)):")
        for err in validation_errors:
            print(f"    ! {err}")
        print()

    print("  STATUS: DRY RUN — use --submit to POST")


def submit_to_lever(
    company: str,
    posting_id: str,
    is_eu: bool,
    config: dict,
    cover_letter_text: str,
    resume_path: Path,
    portfolio_url: str = "",
    answers: dict | None = None,
) -> bool:
    """POST application to Lever Postings API.

    Returns True on success, False on failure.
    """
    import urllib.error
    import urllib.request
    import uuid

    base = _api_base(is_eu)

    # Lever API key from config
    lever_keys = config.get("lever_api_keys", {})
    api_key = ""
    if isinstance(lever_keys, dict):
        api_key = lever_keys.get(company, "")  # allow-secret

    url = f"{base}/{company}/{posting_id}"

    # Build multipart form data
    boundary = uuid.uuid4().hex
    body_parts = []

    def add_field(name: str, value: str) -> None:
        body_parts.append(
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
            f"{value}\r\n"
        )

    full_name = f"{config['first_name']} {config['last_name']}"
    add_field("name", full_name)
    add_field("email", config["email"])
    phone = config.get("phone", "")
    if phone and "FILL_IN" not in phone:
        add_field("phone", phone)
    if portfolio_url:
        add_field("urls[0]", portfolio_url)
    if cover_letter_text:
        add_field("comments", cover_letter_text)

    # Add custom question answers
    if answers:
        for q_text, value in answers.items():
            # Lever uses customQuestions[] format
            add_field(f"customQuestions[{q_text}]", str(value))

    # File upload for resume
    resume_data = resume_path.read_bytes()
    body_parts.append(
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="resume"; filename="{resume_path.name}"\r\n'
        f"Content-Type: application/pdf\r\n\r\n"
    )

    # Assemble the body
    text_body = "".join(body_parts).encode("utf-8")
    end_boundary = f"\r\n--{boundary}--\r\n".encode()
    full_body = text_body + resume_data + end_boundary

    headers = {
        "Content-Type": f"multipart/form-data; boundary={boundary}",
    }
    if api_key:
        import base64
        creds = base64.b64encode(f"{api_key}:".encode()).decode()
        headers["Authorization"] = f"Basic {creds}"

    try:
        req = urllib.request.Request(url, data=full_body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:
            status = resp.status
            response_data = resp.read().decode()
        print(f"  Response: {status}")
        if status in (200, 201):
            try:
                result = json.loads(response_data)
                if result.get("ok"):
                    app_id = result.get("applicationId", "unknown")
                    print(f"  SUCCESS: Application submitted to Lever (ID: {app_id})")
                    return True
                else:
                    print(f"  Lever returned ok=false: {response_data[:500]}")
                    return False
            except json.JSONDecodeError:
                print(f"  SUCCESS: Application submitted (status {status})")
                return True
        else:
            print(f"  Unexpected status: {status}")
            print(f"  Body: {response_data[:500]}")
            return False
    except urllib.error.HTTPError as e:
        status_code = e.code
        print(f"  HTTP Error: {status_code} {e.reason}")
        if status_code == 429:
            print("  Rate limited — Lever allows 2 POST requests/second")
        try:
            error_body = e.read().decode()
            print(f"  Body: {error_body[:500]}")
        except Exception as read_err:
            print(f"  Warning: Could not read error response body: {read_err}")
        return False
    except urllib.error.URLError as e:
        print(f"  Connection error: {e.reason}")
        return False


def process_entry(entry: dict, config: dict, do_submit: bool) -> bool:
    """Process a single Lever entry. Returns True if successful."""
    entry_id = entry.get("id", "?")
    name = entry.get("name", entry_id)

    # Status gate: prevent duplicate submissions
    status = entry.get("status", "")
    if do_submit and status in ("submitted", "acknowledged", "interview", "outcome"):
        print(f"  BLOCKED: {entry_id} already has status '{status}' — refusing duplicate submission")
        return False
    if do_submit and status != "staged":
        print(f"  WARNING: {entry_id} has status '{status}' (expected 'staged'), proceeding with caution")

    portal = entry.get("target", {}).get("portal", "")
    if portal != "lever":
        print(f"  Skipping {entry_id}: portal is '{portal}', not lever")
        return False

    app_url = entry.get("target", {}).get("application_url", "")
    parsed = parse_lever_url(app_url)
    if not parsed:
        print(f"  Error: Cannot parse Lever URL for {entry_id}: {app_url}")
        return False
    company, posting_id, is_eu = parsed

    cover_letter_text = resolve_cover_letter(entry) or ""
    resume_path = resolve_resume(entry)
    if not resume_path:
        print(f"  Error: No resume PDF found for {entry_id}")
        return False

    questions = fetch_posting_questions(company, posting_id, is_eu)

    merged_answers = {}
    validation_errors = []

    if questions:
        auto_filled = auto_fill_answers(questions, config, entry)
        file_answers = load_answers(entry_id)
        mapped_file_answers = map_file_answers_to_questions(questions, file_answers)
        merged_answers = merge_answers(auto_filled, mapped_file_answers)
        validation_errors = validate_answers(questions, merged_answers)

    if not do_submit:
        preview_submission(
            entry, config, company, posting_id, is_eu,
            cover_letter_text, resume_path, questions,
            merged_answers, validation_errors,
        )
        return True

    if validation_errors:
        print(f"\n  Cannot submit {entry_id}: {len(validation_errors)} required answer(s) missing:")
        for err in validation_errors:
            print(f"    - {err}")
        print(f"  Run --init-answers --target {entry_id} to generate answer template")
        return False

    portfolio_url = ""
    submission = entry.get("submission", {})
    if isinstance(submission, dict):
        portfolio_url = submission.get("portfolio_url", "")

    print(f"\nSubmitting: {name} ({company}/{posting_id})...")
    return submit_to_lever(
        company, posting_id, is_eu, config,
        cover_letter_text, resume_path, portfolio_url,
        answers=merged_answers,
    )


def find_lever_entries() -> list[dict]:
    """Find all active pipeline entries with portal=lever."""
    entries = load_entries(dirs=[PIPELINE_DIR_ACTIVE])
    return [e for e in entries if e.get("target", {}).get("portal") == "lever"]


def main():
    parser = build_common_argparse("Lever Postings")
    args = parser.parse_args()

    if not args.target and not args.batch:
        parser.error("Specify --target <id> or --batch")

    config = load_config()

    if args.batch:
        entries = find_lever_entries()
        if not entries:
            print("No Lever entries found in active pipeline.")
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
        print(f"Found {len(entries)} Lever entries:")
        for e in entries:
            print(f"  - {e.get('id')}: {e.get('name')}")
        print()

        results = []
        for i, entry in enumerate(entries):
            ok = process_entry(entry, config, args.submit)
            results.append((entry.get("id"), ok))
            print()
            # Rate limit between batch submissions to respect Lever's 2 req/s limit
            if args.submit and i < len(entries) - 1:
                time.sleep(0.5)

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
