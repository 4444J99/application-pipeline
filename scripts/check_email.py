#!/usr/bin/env python3
"""Email-based application status checker via macOS Mail.app.

Searches Gmail via Mail.app's AppleScript interface for ATS confirmation
and response emails, cross-references against submitted pipeline entries.

Requires: macOS with Mail.app configured for padavano.anthony@gmail account.

Usage:
    python scripts/check_email.py                    # Full scan
    python scripts/check_email.py --confirmations    # Submission confirmations only
    python scripts/check_email.py --responses        # Rejections/interviews only
    python scripts/check_email.py --days 30          # Limit search window
    python scripts/check_email.py --target <id>      # Check single entry
    python scripts/check_email.py --record --yes     # Record outcomes to pipeline YAMLs
"""

import argparse
import re
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import (
    PIPELINE_DIR_SUBMITTED,
    load_entries,
    load_entry_by_id,
    parse_date,
)

MAIL_ACCOUNT = "padavano.anthony@gmail"
MAILBOX = "[Gmail]/All Mail"

# ATS sender patterns and their subject-line signatures
ATS_SENDERS = [
    {
        "name": "Greenhouse",
        "sender": "no-reply@us.greenhouse-mail.io",
        "confirm_pattern": re.compile(
            r"Thank you for applying to (.+)", re.IGNORECASE
        ),
    },
    {
        "name": "Ashby",
        "sender": "no-reply@ashbyhq.com",
        "confirm_pattern": re.compile(
            r"Thank(?:s for applying| you for (?:applying|your application)) to (.+)",
            re.IGNORECASE,
        ),
    },
    {
        "name": "Cloudflare",
        "sender": "no-reply@cloudflare.com",
        "confirm_pattern": re.compile(
            r"Application Received\s*[-–—]\s*(.+)", re.IGNORECASE
        ),
    },
    {
        "name": "Figma",
        "sender": "no-reply@figma.com",
        "confirm_pattern": re.compile(
            r"Thank you for your application to (.+)", re.IGNORECASE
        ),
    },
    {
        "name": "Lever",
        "sender": "no-reply@hire.lever.co",
        "confirm_pattern": re.compile(
            r"Thank you for applying|Application.*received", re.IGNORECASE
        ),
    },
    {
        "name": "OpenAI",
        "sender": "no-reply@openai.com",
        "confirm_pattern": re.compile(
            r"Thank you for applying to (.+)", re.IGNORECASE
        ),
    },
    {
        "name": "Stripe",
        "sender": "no-reply@stripe.com",
        "confirm_pattern": re.compile(
            r"Thanks for applying to (.+)", re.IGNORECASE
        ),
    },
]

# Body-content keywords for response classification (processed in Python)
REJECTION_KEYWORDS = [
    "unfortunately",
    "not moving forward",
    "other candidates",
    "will not be",
    "decided not to",
    "not selected",
    "unable to offer",
    "position has been filled",
    "pursuing other candidates",
    "won't be moving forward",
    "regret to inform",
    "not be proceeding",
]

INTERVIEW_KEYWORDS = [
    "schedule an interview",
    "schedule a call",
    "like to speak with you",
    "next steps in the process",
    "move forward with your application",
    "invite you to",
    "phone screen",
    "technical interview",
    "would love to chat",
    "set up a time",
]

# Delimiter used to separate fields in AppleScript output
FIELD_SEP = "|||"
RECORD_SEP = "^^^"


def search_mail(sender: str, days: int = 90) -> list[dict]:
    """Search Mail.app for messages from a sender within the time window.

    Returns list of dicts with keys: subject, sender, date_str.
    """
    script = f'''
tell application "Mail"
    set cutoff to (current date) - {days} * days
    set msgs to (messages of mailbox "{MAILBOX}" of account "{MAIL_ACCOUNT}" ¬
        whose sender contains "{sender}" and date received > cutoff)
    set results to ""
    repeat with m in msgs
        set results to results & (subject of m) & "{FIELD_SEP}" & (sender of m) & "{FIELD_SEP}" & ((date received of m) as string) & "{RECORD_SEP}"
    end repeat
    return results
end tell
'''
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=45,
        )
    except subprocess.TimeoutExpired:
        print(f"  Warning: Mail search timed out for sender '{sender}'", file=sys.stderr)
        return []

    if result.returncode != 0:
        stderr = result.stderr.strip()
        if "Mail got an error" in stderr or "not available" in stderr:
            print(f"  Warning: Mail.app error for '{sender}': {stderr[:120]}", file=sys.stderr)
        return []

    raw = result.stdout.strip()
    if not raw:
        return []

    messages = []
    for record in raw.split(RECORD_SEP):
        record = record.strip()
        if not record:
            continue
        parts = record.split(FIELD_SEP)
        if len(parts) >= 3:
            messages.append({
                "subject": parts[0].strip(),
                "sender": parts[1].strip(),
                "date_str": parts[2].strip(),
            })
    return messages


def get_email_body(sender: str, subject_fragment: str) -> str | None:
    """Fetch the body of a specific email for classification.

    Targeted query — only used for emails needing content-based classification.
    """
    escaped_subject = subject_fragment.replace('"', '\\"').replace("'", "'")
    script = f'''
tell application "Mail"
    set msgs to (messages of mailbox "{MAILBOX}" of account "{MAIL_ACCOUNT}" ¬
        whose sender contains "{sender}" and subject contains "{escaped_subject}")
    if (count of msgs) > 0 then
        return content of item 1 of msgs
    else
        return ""
    end if
end tell
'''
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        return None

    if result.returncode != 0:
        return None

    body = result.stdout.strip()
    return body if body else None


def parse_apple_date(date_str: str) -> date | None:
    """Parse AppleScript date string into a Python date.

    AppleScript dates look like: "Friday, February 21, 2026 at 3:45:00 PM"
    or "February 21, 2026 3:45:00 PM" depending on locale.
    """
    # Strip day-of-week prefix if present
    cleaned = re.sub(r"^\w+day,?\s*", "", date_str.strip())
    # Remove "at " before time
    cleaned = re.sub(r"\s+at\s+", " ", cleaned)

    for fmt in (
        "%B %d, %Y %I:%M:%S %p",
        "%B %d, %Y %H:%M:%S",
        "%d %B %Y %I:%M:%S %p",
        "%d %B %Y %H:%M:%S",
        "%m/%d/%Y %I:%M:%S %p",
        "%m/%d/%Y %H:%M:%S",
    ):
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue
    return None


def classify_email(subject: str, body: str | None) -> str:
    """Classify an email as confirmation, rejection, interview, or update.

    Subject-line patterns determine confirmations. Body content determines
    rejections and interviews.
    """
    # Check for confirmation patterns first (subject-line only)
    for ats in ATS_SENDERS:
        if ats["confirm_pattern"].search(subject):
            return "confirmation"

    if body:
        body_lower = body.lower()
        for kw in REJECTION_KEYWORDS:
            if kw in body_lower:
                return "rejection"
        for kw in INTERVIEW_KEYWORDS:
            if kw in body_lower:
                return "interview"

    return "update"


def normalize_org(name: str) -> str:
    """Normalize an organization name for fuzzy matching."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def build_org_index(entries: list[dict]) -> dict[str, list[dict]]:
    """Build a lookup from normalized org name to list of entries."""
    index: dict[str, list[dict]] = {}
    for entry in entries:
        target = entry.get("target", {})
        if not isinstance(target, dict):
            continue
        org = target.get("organization", "")
        if org:
            key = normalize_org(org)
            index.setdefault(key, []).append(entry)
    return index


def extract_company_from_subject(subject: str) -> str | None:
    """Extract company name from ATS confirmation subject lines."""
    # ATS entries whose subject captures the role, not the company
    COMPANY_OVERRIDE = {"Cloudflare"}

    for ats in ATS_SENDERS:
        m = ats["confirm_pattern"].search(subject)
        if m:
            if ats["name"] in COMPANY_OVERRIDE:
                return ats["name"]
            company = m.group(1).strip() if m.lastindex else None
            # Clean trailing punctuation or role text
            if company:
                company = re.sub(r"\s*[!.]$", "", company)
            return company
    return None


def match_email_to_entries(
    email: dict,
    org_index: dict[str, list[dict]],
    email_date: date | None,
) -> list[dict]:
    """Match an email to pipeline entries.

    Strategy: extract company from subject → normalize → lookup in org index.
    For orgs with multiple entries, rank by submission date proximity.
    """
    company = extract_company_from_subject(email["subject"])
    if not company:
        return []

    norm = normalize_org(company)
    # Try exact match first, then prefix match
    candidates = org_index.get(norm, [])
    if not candidates:
        for key, entries in org_index.items():
            if key.startswith(norm) or norm.startswith(key):
                candidates = entries
                break

    if not candidates:
        return []

    if len(candidates) == 1 or email_date is None:
        return candidates

    # Rank by date proximity to submitted date
    def date_proximity(entry):
        timeline = entry.get("timeline", {})
        sub_date = parse_date(timeline.get("submitted")) if isinstance(timeline, dict) else None
        if sub_date and email_date:
            return abs((email_date - sub_date).days)
        return 999

    return sorted(candidates, key=date_proximity)


def scan_confirmations(
    entries: list[dict],
    org_index: dict[str, list[dict]],
    days: int,
    target_id: str | None = None,
) -> tuple[list[dict], list[dict]]:
    """Scan for submission confirmation emails.

    Returns (confirmed, unconfirmed) lists of result dicts.
    """
    # Collect all confirmation emails across ATS senders
    all_emails = []
    for ats in ATS_SENDERS:
        print(f"  Searching: {ats['name']} ({ats['sender']})...")
        msgs = search_mail(ats["sender"], days)
        for msg in msgs:
            msg["ats"] = ats["name"]
        all_emails.extend(msgs)

    print(f"  Found {len(all_emails)} ATS emails total\n")

    # Match emails to entries
    confirmed = []
    matched_ids = set()

    for email in all_emails:
        email_date = parse_apple_date(email["date_str"])
        matches = match_email_to_entries(email, org_index, email_date)

        for entry in matches:
            eid = entry.get("id", "")
            if target_id and eid != target_id:
                continue
            if eid in matched_ids:
                continue
            matched_ids.add(eid)
            confirmed.append({
                "entry_id": eid,
                "entry_name": entry.get("name", eid),
                "email_subject": email["subject"],
                "email_date": email_date,
                "ats": email["ats"],
                "status": "CONFIRMED",
            })

    # Find unconfirmed entries
    unconfirmed = []
    for entry in entries:
        eid = entry.get("id", "")
        if target_id and eid != target_id:
            continue
        if eid not in matched_ids:
            unconfirmed.append({
                "entry_id": eid,
                "entry_name": entry.get("name", eid),
                "status": "UNCONFIRMED",
            })

    return confirmed, unconfirmed


def scan_responses(
    entries: list[dict],
    org_index: dict[str, list[dict]],
    days: int,
    target_id: str | None = None,
) -> list[dict]:
    """Scan for rejection/interview response emails.

    Fetches email bodies for non-confirmation emails and classifies them.
    """
    responses = []

    for ats in ATS_SENDERS:
        print(f"  Searching responses: {ats['name']}...")
        msgs = search_mail(ats["sender"], days)

        for email in msgs:
            # Skip pure confirmations
            if ats["confirm_pattern"].search(email["subject"]):
                continue

            email_date = parse_apple_date(email["date_str"])
            matches = match_email_to_entries(email, org_index, email_date)

            if not matches:
                # Try broader subject-based matching
                subject_lower = email["subject"].lower()
                for norm_org, org_entries in org_index.items():
                    org_name = ""
                    if org_entries:
                        target = org_entries[0].get("target", {})
                        org_name = target.get("organization", "") if isinstance(target, dict) else ""
                    if org_name and org_name.lower() in subject_lower:
                        matches = org_entries
                        break

            if not matches:
                continue

            # Fetch body for classification
            body = get_email_body(ats["sender"], email["subject"][:60])
            classification = classify_email(email["subject"], body)

            if classification in ("rejection", "interview"):
                # Extract a snippet for display
                snippet = ""
                if body:
                    body_lower = body.lower()
                    keywords = REJECTION_KEYWORDS if classification == "rejection" else INTERVIEW_KEYWORDS
                    for kw in keywords:
                        idx = body_lower.find(kw)
                        if idx != -1:
                            start = max(0, idx - 20)
                            end = min(len(body), idx + len(kw) + 40)
                            snippet = body[start:end].replace("\n", " ").strip()
                            break

                for entry in matches:
                    eid = entry.get("id", "")
                    if target_id and eid != target_id:
                        continue
                    responses.append({
                        "entry_id": eid,
                        "entry_name": entry.get("name", eid),
                        "classification": classification,
                        "email_subject": email["subject"],
                        "email_date": email_date,
                        "snippet": snippet,
                        "ats": ats["name"],
                    })

    return responses


def print_confirmations(confirmed: list[dict], unconfirmed: list[dict]):
    """Print the confirmation report."""
    print("=== Submission Confirmations ===")

    for item in sorted(confirmed, key=lambda x: x.get("email_date") or date.min, reverse=True):
        date_str = item["email_date"].isoformat() if item["email_date"] else "?"
        print(f'  CONFIRMED  {item["entry_id"]} ({date_str}) — "{item["email_subject"][:70]}"')

    if unconfirmed:
        print()
        for item in sorted(unconfirmed, key=lambda x: x["entry_id"]):
            print(f'  UNCONFIRMED  {item["entry_id"]} — No matching email found')

    print()


def print_responses(responses: list[dict]):
    """Print the responses report."""
    if not responses:
        print("=== Responses Detected ===")
        print("  No rejection or interview emails found.")
        print()
        return

    print("=== Responses Detected ===")
    for item in responses:
        tag = item["classification"].upper()
        snippet_display = f' — "{item["snippet"]}"' if item["snippet"] else ""
        date_str = item["email_date"].isoformat() if item["email_date"] else "?"
        print(f"  {tag}  {item['entry_id']} ({date_str}){snippet_display}")
    print()


def print_summary(confirmed: list[dict], unconfirmed: list[dict], responses: list[dict]):
    """Print the summary line."""
    rejections = sum(1 for r in responses if r["classification"] == "rejection")
    interviews = sum(1 for r in responses if r["classification"] == "interview")
    total = len(confirmed) + len(unconfirmed)

    print("=== Summary ===")
    print(
        f"  Confirmed: {len(confirmed)}/{total} | "
        f"Unconfirmed: {len(unconfirmed)} | "
        f"Rejections: {rejections} | "
        f"Interviews: {interviews}"
    )


def record_outcomes(
    responses: list[dict],
    confirmed: list[dict] | None = None,
    entries: list[dict] | None = None,
    dry_run: bool = True,
):
    """Record detected outcomes to pipeline YAMLs via check_outcomes.record_outcome.

    Processes both:
    - Confirmed submissions → acknowledged (only for entries still in 'submitted' status)
    - Response emails → rejected/interview
    """
    from check_outcomes import record_outcome

    # Build set of entry statuses for acknowledge filtering
    status_by_id = {}
    if entries:
        for e in entries:
            status_by_id[e.get("id", "")] = e.get("status", "")

    # Auto-acknowledge confirmed entries that are still in 'submitted' status
    ack_candidates = []
    if confirmed:
        ack_candidates = [
            c for c in confirmed
            if status_by_id.get(c["entry_id"]) == "submitted"
        ]

    actionable = [r for r in responses if r["classification"] in ("rejection", "interview")]

    if not ack_candidates and not actionable:
        print("\nNo actionable outcomes to record.")
        return

    print(f"\n{'=== Recording Outcomes ===' if not dry_run else '=== Outcomes to Record (dry run) ==='}")

    # Acknowledge confirmed submissions
    for item in ack_candidates:
        if dry_run:
            print(f"  Would acknowledge: {item['entry_id']}")
        else:
            print(f"  Acknowledging: {item['entry_id']}")
            try:
                record_outcome(item["entry_id"], "acknowledged")
            except (SystemExit, Exception) as e:
                print(f"    Error acknowledging {item['entry_id']}: {e}", file=sys.stderr)

    # Record rejections and interviews
    for item in actionable:
        outcome = "rejected" if item["classification"] == "rejection" else "interview"
        if dry_run:
            print(f"  Would record: {item['entry_id']} → {outcome}")
        else:
            print(f"  Recording: {item['entry_id']} → {outcome}")
            try:
                if outcome == "rejected":
                    record_outcome(item["entry_id"], "rejected", stage="resume_screen")
                else:
                    record_outcome(item["entry_id"], "acknowledged")
                    print("    Note: Interview detected — review manually for status update")
            except (SystemExit, Exception) as e:
                print(f"    Error recording {item['entry_id']}: {e}", file=sys.stderr)

    if not dry_run:
        ack_count = len(ack_candidates)
        resp_count = len(actionable)
        print(f"\n  Done: {ack_count} acknowledged, {resp_count} responses recorded")


def check_mail_available() -> bool:
    """Verify Mail.app is running and the account is accessible."""
    script = f'''
tell application "Mail"
    try
        set acct to account "{MAIL_ACCOUNT}"
        return "ok"
    on error
        return "not found"
    end try
end tell
'''
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0 and "ok" in result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Check email for application confirmations and responses"
    )
    parser.add_argument(
        "--confirmations", action="store_true",
        help="Only check submission confirmations",
    )
    parser.add_argument(
        "--responses", action="store_true",
        help="Only check for rejections/interviews",
    )
    parser.add_argument(
        "--days", type=int, default=90,
        help="Search window in days (default: 90)",
    )
    parser.add_argument(
        "--target", metavar="ENTRY_ID",
        help="Check a single entry",
    )
    parser.add_argument(
        "--record", action="store_true",
        help="Record detected outcomes to pipeline YAMLs",
    )
    parser.add_argument(
        "--yes", action="store_true",
        help="Execute recording (without this, --record is dry-run)",
    )
    args = parser.parse_args()

    # Default: full scan (both confirmations and responses)
    scan_confirm = not args.responses
    scan_respond = not args.confirmations

    # Verify Mail.app access
    print("Checking Mail.app access...")
    if not check_mail_available():
        print(
            "Error: Cannot access Mail.app or account not found.\n"
            f"Ensure Mail.app is running with account '{MAIL_ACCOUNT}' configured.",
            file=sys.stderr,
        )
        sys.exit(1)
    print("Mail.app access OK\n")

    # Load submitted entries
    entries = load_entries(dirs=[PIPELINE_DIR_SUBMITTED], include_filepath=True)
    submitted = [
        e for e in entries
        if e.get("status") in ("submitted", "acknowledged", "interview")
    ]

    if args.target:
        submitted = [e for e in submitted if e.get("id") == args.target]
        if not submitted:
            # Try loading directly in case it's not in submitted dir
            filepath, data = load_entry_by_id(args.target)
            if data:
                submitted = [data]
            else:
                print(f"Entry not found: {args.target}", file=sys.stderr)
                sys.exit(1)

    if not submitted:
        print("No submitted entries found.")
        sys.exit(0)

    print(f"Checking {len(submitted)} submitted entries (last {args.days} days)\n")

    org_index = build_org_index(submitted)

    confirmed, unconfirmed, responses = [], [], []

    if scan_confirm:
        confirmed, unconfirmed = scan_confirmations(
            submitted, org_index, args.days, args.target,
        )
        print_confirmations(confirmed, unconfirmed)

    if scan_respond:
        responses = scan_responses(
            submitted, org_index, args.days, args.target,
        )
        print_responses(responses)

    print_summary(
        confirmed if scan_confirm else [],
        unconfirmed if scan_confirm else [],
        responses if scan_respond else [],
    )

    if args.record:
        record_outcomes(
            responses,
            confirmed=confirmed if scan_confirm else None,
            entries=submitted,
            dry_run=not args.yes,
        )


if __name__ == "__main__":
    main()
