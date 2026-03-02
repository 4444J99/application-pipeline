"""Tests for scripts/research_contacts.py"""

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from research_contacts import (
    PROTOCOL_STEPS,
    generate_followup_dates,
    generate_outreach_template,
    generate_research_prompt,
    has_contacts,
)


def _make_entry(
    entry_id="test-entry",
    name="Test Role",
    org="Test Corp",
    submitted_date=None,
):
    """Build a minimal pipeline entry for contact research tests."""
    entry = {
        "id": entry_id,
        "name": name,
        "status": "submitted",
        "target": {"organization": org, "url": "https://testcorp.com"},
        "timeline": {},
    }
    if submitted_date:
        entry["timeline"]["submitted"] = submitted_date
    return entry


# --- generate_research_prompt ---


def test_generate_research_prompt():
    """Returns non-empty string with org name and role."""
    entry = _make_entry(name="Senior Dev", org="Acme Inc")
    prompt = generate_research_prompt(entry)
    assert isinstance(prompt, str)
    assert len(prompt) > 0
    assert "Acme Inc" in prompt
    assert "Senior Dev" in prompt


# --- generate_outreach_template ---


def test_generate_outreach_template():
    """Returns list of dicts with required fields."""
    entry = _make_entry(org="Acme Inc")
    outreach = generate_outreach_template(entry)
    assert isinstance(outreach, list)
    assert len(outreach) >= 2
    for o in outreach:
        assert "type" in o
        assert "channel" in o
        assert "status" in o
        assert "contact" in o


# --- generate_followup_dates ---


def test_generate_followup_dates():
    """Returns 3 dates matching protocol steps."""
    sub_date = (date.today() - timedelta(days=3)).isoformat()
    entry = _make_entry(submitted_date=sub_date)
    follow_ups = generate_followup_dates(entry)
    assert len(follow_ups) == len(PROTOCOL_STEPS)
    for fu in follow_ups:
        assert "type" in fu
        assert "target_date" in fu
        assert "action" in fu
        assert "status" in fu


def test_generate_followup_dates_no_submission():
    """Uses today as fallback when no submission date."""
    entry = _make_entry()
    follow_ups = generate_followup_dates(entry)
    assert len(follow_ups) == len(PROTOCOL_STEPS)
    # First follow-up should be tomorrow or later (day >= 1)
    first_date = follow_ups[0]["target_date"]
    assert first_date >= date.today().isoformat()


def test_generate_followup_dates_all_pending():
    """All generated follow-ups start with status=pending."""
    entry = _make_entry(submitted_date=date.today().isoformat())
    follow_ups = generate_followup_dates(entry)
    for fu in follow_ups:
        assert fu["status"] == "pending"


def test_generate_followup_dates_order():
    """Follow-up dates are in chronological order."""
    entry = _make_entry(submitted_date=date.today().isoformat())
    follow_ups = generate_followup_dates(entry)
    dates = [fu["target_date"] for fu in follow_ups]
    assert dates == sorted(dates)


# --- has_contacts ---


def test_has_contacts_empty():
    """Entry with no outreach field returns False."""
    entry = _make_entry()
    assert has_contacts(entry) is False


def test_has_contacts_empty_list():
    """Entry with empty outreach list returns False."""
    entry = _make_entry()
    entry["outreach"] = []
    assert has_contacts(entry) is False


def test_has_contacts_with_contact():
    """Entry with populated outreach returns True."""
    entry = _make_entry()
    entry["outreach"] = [{"contact": "John Doe", "type": "warm_contact"}]
    assert has_contacts(entry) is True


def test_has_contacts_missing_contact_field():
    """Outreach items without 'contact' key return False."""
    entry = _make_entry()
    entry["outreach"] = [{"type": "warm_contact", "note": "placeholder"}]
    assert has_contacts(entry) is False


# --- generate_research_prompt edge cases ---


def test_generate_research_prompt_missing_url():
    """Prompt works when no URL in target."""
    entry = _make_entry(org="No URL Corp")
    entry["target"] = {"organization": "No URL Corp"}
    prompt = generate_research_prompt(entry)
    assert "No URL Corp" in prompt
    assert "Company page:" not in prompt


def test_generate_research_prompt_contains_linkedin():
    """Prompt includes LinkedIn search instructions."""
    entry = _make_entry()
    prompt = generate_research_prompt(entry)
    assert "LinkedIn" in prompt
