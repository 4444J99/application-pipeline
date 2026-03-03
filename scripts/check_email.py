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

PIPELINE_DIR_CLOSED = Path(__file__).resolve().parent.parent / "pipeline" / "closed"

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
    {
        "name": "Gem",
        "sender": "no-reply@appreview.gem.com",
        "confirm_pattern": re.compile(
            r"Thank(?:s| you) for applying to (.+)", re.IGNORECASE
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


def _extract_role_from_subject(subject: str) -> str | None:
    """Extract the role title from a response email subject line.

    Recognizes patterns like:
      - "Anthropic Follow-Up for Developer Education Lead | Name"
      - "Your application for our Full Stack Engineer role at Stripe"
      - "Update on your Role Title application"
    """
    patterns = [
        # "Follow-Up for {Role} | Name" (Greenhouse)
        re.compile(r"Follow[- ]?Up for (.+?)(?:\s*\||\s*$)", re.IGNORECASE),
        # "Your application for our {Role} role at {Company}"
        re.compile(r"Your application for (?:our |the )?(.+?)\s+role\s+at\s+", re.IGNORECASE),
        # "Update on your {Role} application"
        re.compile(r"Update on your (.+?) application", re.IGNORECASE),
        # "Regarding your {Role} application"
        re.compile(r"Regarding your (.+?) application", re.IGNORECASE),
    ]
    for pat in patterns:
        m = pat.search(subject)
        if m:
            return m.group(1).strip()
    return None


def _match_role_to_entry(role_title: str, candidates: list[dict]) -> dict | None:
    """Fuzzy-match an extracted role title against candidate entries.

    Compares normalized words in the role title against each entry's title.
    Returns the best match, or None if no reasonable match found.
    """
    role_words = set(re.sub(r"[^a-z0-9\s]", "", role_title.lower()).split())
    # Filter out very common words that don't help distinguish roles
    stop_words = {"the", "a", "an", "and", "or", "for", "at", "in", "of", "to",
                   "senior", "staff", "lead", "jr", "ii", "iii",
                   "software", "engineer", "developer", "manager", "director"}
    role_words -= stop_words

    if not role_words:
        return None

    scored = []

    for entry in candidates:
        title = entry.get("title", "") or entry.get("name", "")
        title_words = set(re.sub(r"[^a-z0-9\s]", "", title.lower()).split()) - stop_words
        if not title_words:
            continue
        overlap = role_words & title_words
        if not overlap:
            continue
        # Primary: overlap ratio against role words (what % of the role matched)
        role_coverage = len(overlap) / len(role_words)
        # Secondary: prefer entries with fewer extraneous words (tighter match)
        extraneous = len(title_words - role_words)
        scored.append((role_coverage, -extraneous, entry))

    if not scored:
        return None

    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
    best_coverage = scored[0][0]

    # Require at least 40% of role words to match
    return scored[0][2] if best_coverage >= 0.4 else None


def _search_mail_by_subject(subject_fragment: str, days: int = 90) -> list[dict]:
    """Search Mail.app for messages with a subject containing the fragment.

    Sender-agnostic — catches rejections from any ATS or recruiter.
    Subject search is indexed and fast (unlike body search which can timeout).
    """
    escaped = subject_fragment.replace('"', '\\"')
    script = f'''
tell application "Mail"
    set cutoff to (current date) - {days} * days
    set msgs to (messages of mailbox "{MAILBOX}" of account "{MAIL_ACCOUNT}" ¬
        whose subject contains "{escaped}" and date received > cutoff)
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
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        return []

    if result.returncode != 0:
        return []

    raw = result.stdout.strip()
    if not raw:
        return []

    messages = []
    seen = set()
    for record in raw.split(RECORD_SEP):
        record = record.strip()
        if not record:
            continue
        parts = record.split(FIELD_SEP)
        if len(parts) >= 3:
            key = (parts[0].strip(), parts[2].strip())
            if key in seen:
                continue
            seen.add(key)
            messages.append({
                "subject": parts[0].strip(),
                "sender": parts[1].strip(),
                "date_str": parts[2].strip(),
            })
    return messages


def scan_responses(
    entries: list[dict],
    org_index: dict[str, list[dict]],
    days: int,
    target_id: str | None = None,
    closed_ids: set[str] | None = None,
) -> list[dict]:
    """Scan for rejection/interview response emails.

    Two-phase approach:
    1. Known ATS senders — targeted search by sender address
    2. Catch-all body scan — searches ALL emails for rejection/interview
       keywords regardless of sender, catching unknown ATS platforms

    Narrows matches to the specific role mentioned in the subject line
    to avoid broadcasting one rejection to all entries at an org.
    Skips entries already in closed/ to avoid false re-matches.
    """
    if closed_ids is None:
        closed_ids = set()
    responses = []
    seen_entry_ids = set()
    seen_subjects = set()

    # Build set of known org names for matching
    all_org_names = {}
    for norm_org, org_entries in org_index.items():
        if org_entries:
            target = org_entries[0].get("target", {})
            org_name = target.get("organization", "") if isinstance(target, dict) else ""
            if org_name:
                all_org_names[org_name.lower()] = org_entries

    def _process_email(email, body, source_label):
        """Process a single email: match to entry, classify, record."""
        subject_key = (email["subject"], email.get("date_str", ""))
        if subject_key in seen_subjects:
            return
        seen_subjects.add(subject_key)

        email_date = parse_apple_date(email["date_str"])
        matches = []

        # Try subject-based org matching
        subject_lower = email["subject"].lower()
        for org_name_lower, org_entries in all_org_names.items():
            if org_name_lower in subject_lower:
                matches = org_entries
                break

        # Also try body-based org matching if subject didn't match
        if not matches and body:
            body_lower = body.lower()
            for org_name_lower, org_entries in all_org_names.items():
                # Only match org names in the first 500 chars (avoid footer noise)
                if org_name_lower in body_lower[:500]:
                    matches = org_entries
                    break

        if not matches:
            return

        # Narrow to specific role
        if len(matches) > 1:
            role_title = _extract_role_from_subject(email["subject"])
            if role_title:
                specific = _match_role_to_entry(role_title, matches)
                if specific:
                    matches = [specific]
                else:
                    matches = [matches[0]]
            else:
                # Try role from body
                if body:
                    for entry in matches:
                        title = entry.get("title", "") or entry.get("name", "")
                        if title and title.lower() in body.lower():
                            matches = [entry]
                            break
                    else:
                        matches = [matches[0]]
                else:
                    matches = [matches[0]]

        classification = classify_email(email["subject"], body)

        if classification in ("rejection", "interview"):
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

            entry = matches[0]
            eid = entry.get("id", "")
            if target_id and eid != target_id:
                return
            if eid in closed_ids:
                return
            if eid in seen_entry_ids:
                return
            seen_entry_ids.add(eid)
            responses.append({
                "entry_id": eid,
                "entry_name": entry.get("name", eid),
                "classification": classification,
                "email_subject": email["subject"],
                "email_date": email_date,
                "snippet": snippet,
                "ats": source_label,
            })

    # Phase 1: Known ATS senders (fast, targeted)
    for ats in ATS_SENDERS:
        print(f"  Searching responses: {ats['name']}...")
        msgs = search_mail(ats["sender"], days)

        for email in msgs:
            if ats["confirm_pattern"].search(email["subject"]):
                continue
            body = get_email_body(ats["sender"], email["subject"][:60])
            _process_email(email, body, ats["name"])

    # Phase 2: Catch-all subject pattern scan (catches unknown ATS platforms)
    # Body-content search is too slow on large mailboxes; subject search is indexed.
    print("  Searching responses: catch-all (subject patterns)...")
    catchall_subject_patterns = [
        "Update from",           # Gem rejection pattern
        "Your application for",  # Stripe/generic rejection
        "Your candidacy",        # Generic rejection
        "An update on your",     # LinkedIn/generic
        "Regarding your",        # Formal rejection
        "We appreciate your interest",  # Generic rejection
    ]
    catchall_emails = []
    for pattern in catchall_subject_patterns:
        catchall_emails.extend(_search_mail_by_subject(pattern, days))

    # Deduplicate catch-all results
    seen_catchall = set()
    for email in catchall_emails:
        key = (email["subject"], email["date_str"])
        if key in seen_catchall:
            continue
        seen_catchall.add(key)
        # Skip if already seen from Phase 1
        if (email["subject"], email.get("date_str", "")) in seen_subjects:
            continue
        # Fetch body to verify it's actually a rejection/interview
        sender_addr = re.search(r"<([^>]+)>", email["sender"])
        sender_for_query = sender_addr.group(1) if sender_addr else email["sender"]
        body = get_email_body(sender_for_query, email["subject"][:60])
        _process_email(email, body, "catch-all")

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

    # Also index closed entries so already-processed rejections resolve
    # to the correct (closed) entry instead of a wrong living entry.
    closed_entries = load_entries(dirs=[PIPELINE_DIR_CLOSED], include_filepath=True)
    closed_ids = {e.get("id", "") for e in closed_entries}
    org_index_with_closed = build_org_index(submitted + closed_entries)

    confirmed, unconfirmed, responses = [], [], []

    if scan_confirm:
        confirmed, unconfirmed = scan_confirmations(
            submitted, org_index, args.days, args.target,
        )
        print_confirmations(confirmed, unconfirmed)

    if scan_respond:
        responses = scan_responses(
            submitted, org_index_with_closed, args.days, args.target,
            closed_ids=closed_ids,
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
