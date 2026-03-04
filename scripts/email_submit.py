#!/usr/bin/env python3
"""Submit applications via email for grants, residencies, and custom portals.

Sends email submissions with cover letter body and resume/materials attachments
using SMTP. Supports dry-run preview and batch submission.

Usage:
    python scripts/email_submit.py --target <id>              # dry-run preview
    python scripts/email_submit.py --target <id> --submit     # send email
    python scripts/email_submit.py --batch                    # dry-run all
    python scripts/email_submit.py --batch --submit           # send all
    python scripts/email_submit.py --target <id> --record     # update YAML after sending

Requires smtp config in .submit-config.yaml:
    smtp:
      server: smtp.gmail.com
      port: 465
      email: you@gmail.com
      app_password: "..."
"""

import argparse
import smtplib
import sys
from datetime import date
from email.message import EmailMessage
from pathlib import Path
from urllib.parse import urlparse

from pipeline_lib import (
    MATERIALS_DIR,
    PIPELINE_DIR_ACTIVE,
    load_entries,
    load_entry_by_id,
    load_submit_config,
    resolve_cover_letter,
    resolve_resume,
    update_yaml_field,
)


def load_config() -> dict:
    """Load personal info from .submit-config.yaml."""
    return load_submit_config(strict=True)


def get_smtp_config(config: dict) -> dict:
    """Extract and validate SMTP settings from config."""
    smtp = config.get("smtp", {})
    if not isinstance(smtp, dict):
        return {}
    required = ("server", "port", "email", "app_password")
    for field in required:
        if not smtp.get(field):
            return {}
    return smtp


def extract_recipient(entry: dict) -> str | None:
    """Extract email recipient from entry target fields.

    Checks (in order):
      1. target.email field
      2. target.application_url if it's a mailto: link
    """
    target = entry.get("target", {}) or {}
    # Direct email field
    email = target.get("email")
    if email and "@" in email:
        return email
    # mailto: link in application_url
    app_url = target.get("application_url", "")
    if app_url.startswith("mailto:"):
        parsed = urlparse(app_url)
        addr = parsed.path
        if addr and "@" in addr:
            return addr
    return None


def is_email_entry(entry: dict) -> bool:
    """Check if entry is submittable via email."""
    portal = entry.get("target", {}).get("portal", "")
    if portal not in ("custom", "email"):
        return False
    return extract_recipient(entry) is not None


def find_email_entries() -> list[dict]:
    """Find all active entries submittable via email."""
    entries = load_entries(dirs=[PIPELINE_DIR_ACTIVE])
    return [e for e in entries if is_email_entry(e)]


def generate_subject(entry: dict) -> str:
    """Generate email subject line from entry."""
    submission = entry.get("submission", {}) or {}
    # Check for explicit subject override
    subject = submission.get("email_subject")
    if subject:
        return subject
    # Auto-generate from entry name
    name = entry.get("name", entry.get("id", "Application"))
    org = entry.get("target", {}).get("organization", "")
    if org:
        return f"Application: {name}"
    return f"Application: {name}"


def generate_body(entry: dict) -> str | None:
    """Generate email body from cover letter or explicit override."""
    submission = entry.get("submission", {}) or {}
    # Check for explicit body override
    body = submission.get("email_body")
    if body:
        return body
    # Fall back to cover letter
    return resolve_cover_letter(entry, strip_md=True)


def collect_attachments(entry: dict) -> list[Path]:
    """Collect all attachment files for the email."""
    attachments = []
    # Resume PDF
    resume = resolve_resume(entry)
    if resume and resume.exists():
        attachments.append(resume)
    # Additional materials (non-HTML, non-duplicate of resume)
    submission = entry.get("submission", {}) or {}
    materials = submission.get("materials_attached", []) or []
    for m in materials:
        mat_path = MATERIALS_DIR / m
        if not mat_path.exists():
            continue
        # Skip HTML source files and already-added resume
        if mat_path.suffix.lower() == ".html":
            continue
        if resume and mat_path.resolve() == resume.resolve():
            continue
        attachments.append(mat_path)
    return attachments


def build_email(entry: dict, config: dict) -> EmailMessage | None:
    """Build an EmailMessage for the entry. Returns None if missing data."""
    smtp_config = get_smtp_config(config)
    sender = smtp_config.get("email", config.get("email", ""))
    recipient = extract_recipient(entry)
    if not recipient:
        return None

    subject = generate_subject(entry)
    body = generate_body(entry)
    if not body:
        return None

    msg = EmailMessage()
    msg["From"] = f"{config.get('first_name', '')} {config.get('last_name', '')} <{sender}>"
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.set_content(body)

    # Add attachments
    for path in collect_attachments(entry):
        mime_type = "application/octet-stream"
        if path.suffix.lower() == ".pdf":
            mime_type = "application/pdf"
        maintype, subtype = mime_type.split("/", 1)
        msg.add_attachment(
            path.read_bytes(),
            maintype=maintype,
            subtype=subtype,
            filename=path.name,
        )

    return msg


def preview_entry(entry: dict, config: dict) -> bool:
    """Preview what would be sent for an entry. Returns True if sendable."""
    eid = entry.get("id", "unknown")
    name = entry.get("name", eid)
    status = entry.get("status", "")
    recipient = extract_recipient(entry)

    print(f"--- {eid} ---")
    print(f"  Name:      {name}")
    print(f"  Status:    {status}")
    print(f"  Recipient: {recipient or 'MISSING'}")

    if not recipient:
        print("  SKIP: No email recipient found")
        return False

    subject = generate_subject(entry)
    print(f"  Subject:   {subject}")

    body = generate_body(entry)
    if body:
        preview = body[:120].replace("\n", " ")
        print(f"  Body:      {preview}...")
    else:
        print("  Body:      MISSING (no cover letter or email_body)")
        print("  SKIP: No body content")
        return False

    attachments = collect_attachments(entry)
    if attachments:
        for a in attachments:
            size_kb = a.stat().st_size / 1024
            print(f"  Attach:    {a.name} ({size_kb:.0f} KB)")
    else:
        print("  Attach:    (none)")

    resume = resolve_resume(entry)
    if not resume:
        print("  WARNING: No resume PDF found")

    print("  Ready:     YES")
    return True


def send_entry(entry: dict, config: dict) -> bool:
    """Send email for an entry. Returns True on success."""
    eid = entry.get("id", "unknown")
    smtp_config = get_smtp_config(config)
    if not smtp_config:
        print(f"  {eid}: ERROR — smtp config missing in .submit-config.yaml")
        return False

    msg = build_email(entry, config)
    if not msg:
        print(f"  {eid}: ERROR — could not build email (missing recipient or body)")
        return False

    recipient = extract_recipient(entry)
    print(f"  {eid}: Sending to {recipient}...", end=" ")

    try:
        with smtplib.SMTP_SSL(smtp_config["server"], int(smtp_config["port"])) as server:
            server.login(smtp_config["email"], smtp_config["app_password"])
            server.send_message(msg)
        print("SENT")
        return True
    except smtplib.SMTPException as e:
        print(f"FAILED — {e}")
        return False


def record_submission(entry_id: str) -> bool:
    """Update pipeline YAML to record email submission."""
    filepath, entry = load_entry_by_id(entry_id)
    if not filepath or not entry:
        print(f"Error: Entry '{entry_id}' not found", file=sys.stderr)
        return False

    content = filepath.read_text()
    today = date.today().isoformat()

    try:
        content = update_yaml_field(content, "status", "submitted", nested=False)
        content = update_yaml_field(content, "submitted", f"'{today}'",
                                    nested=True, parent_key="timeline")
    except ValueError as e:
        print(f"Warning: Could not update field: {e}", file=sys.stderr)

    filepath.write_text(content)
    print(f"  {entry_id}: Recorded submission (status=submitted, date={today})")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Submit applications via email (grants, residencies, custom portals)"
    )
    parser.add_argument("--target", help="Target entry ID")
    parser.add_argument("--batch", action="store_true",
                        help="Process all email-submittable entries in active pipeline")
    parser.add_argument("--submit", action="store_true",
                        help="Actually send emails (default is dry-run preview)")
    parser.add_argument("--record", action="store_true",
                        help="Record submission in pipeline YAML (use after sending)")
    args = parser.parse_args()

    if not args.target and not args.batch:
        parser.error("Specify --target <id> or --batch")

    config = load_config()

    # --record mode: just update YAML
    if args.record:
        if not args.target:
            parser.error("--record requires --target <id>")
        ok = record_submission(args.target)
        sys.exit(0 if ok else 1)

    # Resolve entries
    if args.batch:
        entries = find_email_entries()
        if not entries:
            print("No email-submittable entries found in active pipeline.")
            print("(Entries need portal: custom/email and a target.email or mailto: URL)")
            sys.exit(0)
    else:
        _, entry = load_entry_by_id(args.target)
        if not entry:
            print(f"Error: No pipeline entry found for '{args.target}'", file=sys.stderr)
            sys.exit(1)
        if not is_email_entry(entry):
            print(f"Warning: '{args.target}' is not configured for email submission")
            print(f"  portal: {entry.get('target', {}).get('portal', 'N/A')}")
            print(f"  recipient: {extract_recipient(entry) or 'NONE'}")
            # Still allow preview in dry-run mode
            if args.submit:
                sys.exit(1)
        entries = [entry]

    if args.batch:
        print(f"Found {len(entries)} email-submittable entries:")
        for e in entries:
            print(f"  - {e.get('id')}: {e.get('name')}")
        print()

    if args.submit:
        smtp_config = get_smtp_config(config)
        if not smtp_config:
            print("Error: smtp config missing in .submit-config.yaml", file=sys.stderr)
            print("Required fields: smtp.server, smtp.port, smtp.email, smtp.app_password",
                  file=sys.stderr)
            sys.exit(1)

    # Process entries
    results = []
    for entry in entries:
        if args.submit:
            ok = send_entry(entry, config)
        else:
            ok = preview_entry(entry, config)
        results.append((entry.get("id"), ok))
        print()

    # Summary
    if len(results) > 1:
        print("=" * 60)
        mode = "SEND" if args.submit else "PREVIEW"
        print(f"BATCH {mode} SUMMARY:")
        for eid, ok in results:
            status = "OK" if ok else "SKIP"
            print(f"  {eid}: {status}")
        ready = sum(1 for _, ok in results if ok)
        print(f"\n{ready}/{len(results)} ready for submission")

    failed = sum(1 for _, ok in results if not ok)
    if failed and args.submit:
        sys.exit(1)


if __name__ == "__main__":
    main()
