"""Constants for check_email.py."""

from __future__ import annotations

import re

MAIL_ACCOUNT = "padavano.anthony@gmail"
MAILBOX = "[Gmail]/All Mail"

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

FIELD_SEP = "|||"
RECORD_SEP = "^^^"
