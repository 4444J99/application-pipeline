"""Tests for scripts/check_email_constants.py."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from check_email_constants import (
    ATS_SENDERS,
    FIELD_SEP,
    INTERVIEW_KEYWORDS,
    MAIL_ACCOUNT,
    MAILBOX,
    RECORD_SEP,
    REJECTION_KEYWORDS,
)


def test_mail_account_and_mailbox_present():
    assert "@" in MAIL_ACCOUNT
    assert MAILBOX


def test_sender_patterns_have_required_keys():
    assert ATS_SENDERS
    for sender in ATS_SENDERS:
        assert "name" in sender
        assert "sender" in sender
        assert "confirm_pattern" in sender


def test_classification_keyword_lists_non_empty():
    assert len(REJECTION_KEYWORDS) > 0
    assert len(INTERVIEW_KEYWORDS) > 0


def test_output_delimiters_are_distinct():
    assert FIELD_SEP != RECORD_SEP
