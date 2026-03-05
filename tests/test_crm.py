"""Tests for scripts/crm.py — lightweight relationship CRM."""

import sys
from datetime import date, timedelta
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from crm import (
    VALID_CHANNELS,
    VALID_INTERACTION_TYPES,
    add_contact,
    compute_stats,
    find_contact,
    get_contacts_by_org,
    get_interactions_per_week,
    get_orgs_covered,
    get_overdue_contacts,
    get_strength_distribution,
    get_uncovered_entries,
    link_entry,
    load_contacts,
    log_interaction,
    save_contacts,
    set_next_action,
    show_dashboard,
    show_stats,
    suggest_network_proximity,
)

# --- Helpers ---


def _make_contact(
    name="Jane Smith",
    organization="Anthropic",
    role="Engineering Manager",
    channel="linkedin",
    strength=3,
    interactions=None,
    pipeline_entries=None,
    tags=None,
    next_action="",
    next_action_date="",
):
    """Build a minimal contact dict for testing."""
    return {
        "name": name,
        "organization": organization,
        "role": role,
        "channel": channel,
        "relationship_strength": strength,
        "interactions": interactions or [],
        "pipeline_entries": pipeline_entries or [],
        "tags": tags or [],
        "next_action": next_action,
        "next_action_date": next_action_date,
    }


def _write_contacts(tmp_path, contacts):
    """Write contacts to a temporary contacts.yaml and patch CONTACTS_FILE."""
    contacts_file = tmp_path / "contacts.yaml"
    content = yaml.dump({"contacts": contacts}, default_flow_style=False, sort_keys=False)
    contacts_file.write_text(content)
    return contacts_file


# --- find_contact ---


def test_find_contact_exact_match():
    """Should find contact by exact name."""
    contacts = [_make_contact(name="Jane Smith"), _make_contact(name="Bob Jones")]
    result = find_contact(contacts, "Jane Smith")
    assert result is not None
    assert result["name"] == "Jane Smith"


def test_find_contact_case_insensitive():
    """Should find contact regardless of case."""
    contacts = [_make_contact(name="Jane Smith")]
    result = find_contact(contacts, "jane smith")
    assert result is not None
    assert result["name"] == "Jane Smith"


def test_find_contact_not_found():
    """Should return None when contact does not exist."""
    contacts = [_make_contact(name="Jane Smith")]
    result = find_contact(contacts, "Alice Wonderland")
    assert result is None


def test_find_contact_empty_list():
    """Should return None on empty contacts list."""
    assert find_contact([], "Jane Smith") is None


# --- add_contact ---


def test_add_contact_creates_entry(monkeypatch, tmp_path):
    """add_contact should create a new contact and save to disk."""
    contacts_file = tmp_path / "contacts.yaml"
    contacts_file.write_text("contacts: []\n")

    import crm

    monkeypatch.setattr(crm, "CONTACTS_FILE", contacts_file)

    result = add_contact(
        name="Alice Wonderland",
        organization="OpenAI",
        role="Research Scientist",
        channel="email",
        tags=["ai-lab", "research"],
    )

    assert result["name"] == "Alice Wonderland"
    assert result["organization"] == "OpenAI"
    assert result["role"] == "Research Scientist"
    assert result["channel"] == "email"
    assert result["relationship_strength"] == 1
    assert result["interactions"] == []
    assert result["pipeline_entries"] == []
    assert result["tags"] == ["ai-lab", "research"]

    # Verify persisted to disk
    saved = yaml.safe_load(contacts_file.read_text())
    assert len(saved["contacts"]) == 1
    assert saved["contacts"][0]["name"] == "Alice Wonderland"


def test_add_contact_duplicate_raises(monkeypatch, tmp_path):
    """add_contact should reject duplicate names."""
    contacts_file = _write_contacts(tmp_path, [_make_contact(name="Jane Smith")])

    import crm

    monkeypatch.setattr(crm, "CONTACTS_FILE", contacts_file)

    with pytest.raises(ValueError, match="already exists"):
        add_contact(name="Jane Smith", organization="Anthropic")


def test_add_contact_invalid_channel_raises(monkeypatch, tmp_path):
    """add_contact should reject invalid channels."""
    contacts_file = tmp_path / "contacts.yaml"
    contacts_file.write_text("contacts: []\n")

    import crm

    monkeypatch.setattr(crm, "CONTACTS_FILE", contacts_file)

    with pytest.raises(ValueError, match="Invalid channel"):
        add_contact(name="Alice", organization="OpenAI", channel="fax")


def test_add_contact_no_file_yet(monkeypatch, tmp_path):
    """add_contact should create the file if it does not exist."""
    contacts_file = tmp_path / "contacts.yaml"
    # File does not exist yet

    import crm

    monkeypatch.setattr(crm, "CONTACTS_FILE", contacts_file)

    result = add_contact(name="Bob", organization="Stripe")
    assert result["name"] == "Bob"
    assert contacts_file.exists()


# --- log_interaction ---


def test_log_interaction_appends(monkeypatch, tmp_path):
    """log_interaction should append an interaction and bump strength."""
    contacts_file = _write_contacts(tmp_path, [_make_contact(name="Jane Smith", strength=3)])

    import crm

    monkeypatch.setattr(crm, "CONTACTS_FILE", contacts_file)

    result = log_interaction(
        name="Jane Smith",
        interaction_type="dm",
        note="Discussed Agent SDK role",
    )

    assert len(result["interactions"]) == 1
    assert result["interactions"][0]["type"] == "dm"
    assert result["interactions"][0]["note"] == "Discussed Agent SDK role"
    assert result["interactions"][0]["date"] == date.today().isoformat()
    assert result["relationship_strength"] == 4  # 3 + 1 (dm bump)


def test_log_interaction_meeting_bumps_by_two(monkeypatch, tmp_path):
    """Meeting interactions should bump strength by 2."""
    contacts_file = _write_contacts(tmp_path, [_make_contact(name="Jane Smith", strength=3)])

    import crm

    monkeypatch.setattr(crm, "CONTACTS_FILE", contacts_file)

    result = log_interaction(name="Jane Smith", interaction_type="meeting", note="In-person")
    assert result["relationship_strength"] == 5  # 3 + 2


def test_log_interaction_caps_at_ten(monkeypatch, tmp_path):
    """Strength should not exceed 10."""
    contacts_file = _write_contacts(tmp_path, [_make_contact(name="Jane Smith", strength=9)])

    import crm

    monkeypatch.setattr(crm, "CONTACTS_FILE", contacts_file)

    result = log_interaction(name="Jane Smith", interaction_type="meeting", note="Coffee")
    assert result["relationship_strength"] == 10  # capped at 10, not 11


def test_log_interaction_no_bump(monkeypatch, tmp_path):
    """bump_strength=False should leave strength unchanged."""
    contacts_file = _write_contacts(tmp_path, [_make_contact(name="Jane Smith", strength=5)])

    import crm

    monkeypatch.setattr(crm, "CONTACTS_FILE", contacts_file)

    result = log_interaction(name="Jane Smith", interaction_type="dm", note="Quick check", bump_strength=False)
    assert result["relationship_strength"] == 5


def test_log_interaction_unknown_contact_raises(monkeypatch, tmp_path):
    """log_interaction should raise if contact not found."""
    contacts_file = _write_contacts(tmp_path, [_make_contact(name="Jane Smith")])

    import crm

    monkeypatch.setattr(crm, "CONTACTS_FILE", contacts_file)

    with pytest.raises(ValueError, match="not found"):
        log_interaction(name="Ghost Person", interaction_type="dm", note="Hello")


def test_log_interaction_invalid_type_raises(monkeypatch, tmp_path):
    """log_interaction should reject invalid interaction types."""
    contacts_file = _write_contacts(tmp_path, [_make_contact(name="Jane Smith")])

    import crm

    monkeypatch.setattr(crm, "CONTACTS_FILE", contacts_file)

    with pytest.raises(ValueError, match="Invalid interaction type"):
        log_interaction(name="Jane Smith", interaction_type="smoke_signal", note="Hello")


# --- link_entry ---


def test_link_entry_adds_id(monkeypatch, tmp_path):
    """link_entry should add entry ID to pipeline_entries."""
    contacts_file = _write_contacts(tmp_path, [_make_contact(name="Jane Smith")])

    import crm

    monkeypatch.setattr(crm, "CONTACTS_FILE", contacts_file)

    result = link_entry(name="Jane Smith", entry_id="anthropic-se-claude-code")
    assert "anthropic-se-claude-code" in result["pipeline_entries"]


def test_link_entry_no_duplicates(monkeypatch, tmp_path):
    """link_entry should not duplicate an already-linked entry."""
    contacts_file = _write_contacts(
        tmp_path,
        [_make_contact(name="Jane Smith", pipeline_entries=["anthropic-se-claude-code"])],
    )

    import crm

    monkeypatch.setattr(crm, "CONTACTS_FILE", contacts_file)

    result = link_entry(name="Jane Smith", entry_id="anthropic-se-claude-code")
    assert result["pipeline_entries"].count("anthropic-se-claude-code") == 1


def test_link_entry_not_found_raises(monkeypatch, tmp_path):
    """link_entry should raise if contact not found."""
    contacts_file = _write_contacts(tmp_path, [_make_contact(name="Jane Smith")])

    import crm

    monkeypatch.setattr(crm, "CONTACTS_FILE", contacts_file)

    with pytest.raises(ValueError, match="not found"):
        link_entry(name="Ghost Person", entry_id="some-entry")


# --- Analytics ---


def test_strength_distribution():
    """Should count contacts per strength level."""
    contacts = [
        _make_contact(strength=3),
        _make_contact(name="B", strength=3),
        _make_contact(name="C", strength=7),
        _make_contact(name="D", strength=1),
    ]
    dist = get_strength_distribution(contacts)
    assert dist[1] == 1
    assert dist[3] == 2
    assert dist[7] == 1
    assert 5 not in dist


def test_strength_distribution_empty():
    """Empty contacts should return empty distribution."""
    assert get_strength_distribution([]) == {}


def test_interactions_per_week():
    """Should calculate average interactions per week."""
    today = date.today().isoformat()
    week_ago = (date.today() - timedelta(days=5)).isoformat()
    old = (date.today() - timedelta(days=60)).isoformat()

    contacts = [
        _make_contact(interactions=[
            {"date": today, "type": "dm", "note": "hello"},
            {"date": week_ago, "type": "email", "note": "follow up"},
            {"date": old, "type": "call", "note": "old call"},  # Outside 4-week window
        ]),
    ]
    # 2 interactions in 4 weeks = 0.5/week
    result = get_interactions_per_week(contacts, weeks=4)
    assert result == 0.5


def test_interactions_per_week_empty():
    """No contacts should return 0."""
    assert get_interactions_per_week([], weeks=4) == 0.0


def test_orgs_covered():
    """Should return sorted unique organizations."""
    contacts = [
        _make_contact(organization="Anthropic"),
        _make_contact(name="B", organization="Anthropic"),
        _make_contact(name="C", organization="Stripe"),
        _make_contact(name="D", organization="OpenAI"),
    ]
    orgs = get_orgs_covered(contacts)
    assert orgs == ["Anthropic", "OpenAI", "Stripe"]


def test_contacts_by_org_case_insensitive():
    """Should filter by org case-insensitively."""
    contacts = [
        _make_contact(name="A", organization="Anthropic"),
        _make_contact(name="B", organization="anthropic"),
        _make_contact(name="C", organization="Stripe"),
    ]
    result = get_contacts_by_org(contacts, "Anthropic")
    assert len(result) == 2


def test_overdue_contacts():
    """Should return contacts with overdue next_action_date."""
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    tomorrow = (date.today() + timedelta(days=1)).isoformat()

    contacts = [
        _make_contact(name="A", next_action="Send DM", next_action_date=yesterday),
        _make_contact(name="B", next_action="Send email", next_action_date=tomorrow),
        _make_contact(name="C"),  # No action set
    ]
    overdue = get_overdue_contacts(contacts)
    assert len(overdue) == 1
    assert overdue[0]["name"] == "A"


def test_overdue_contacts_no_action_text():
    """Contact with date but no action text should not be overdue."""
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    contacts = [_make_contact(next_action="", next_action_date=yesterday)]
    assert get_overdue_contacts(contacts) == []


# --- compute_stats ---


def test_compute_stats_comprehensive():
    """compute_stats should return all expected keys."""
    contacts = [
        _make_contact(name="A", organization="Anthropic", strength=3, interactions=[
            {"date": date.today().isoformat(), "type": "dm", "note": "test"},
        ]),
        _make_contact(name="B", organization="Stripe", strength=7),
    ]
    stats = compute_stats(contacts)
    assert stats["total_contacts"] == 2
    assert stats["orgs_covered"] == 2
    assert stats["total_interactions"] == 1
    assert stats["overdue_actions"] == 0
    assert isinstance(stats["strength_distribution"], dict)
    assert isinstance(stats["interactions_per_week"], float)


def test_compute_stats_empty():
    """compute_stats on empty list should return zeros."""
    stats = compute_stats([])
    assert stats["total_contacts"] == 0
    assert stats["orgs_covered"] == 0
    assert stats["total_interactions"] == 0


# --- suggest_network_proximity ---


def test_suggest_proximity_direct_contact():
    """Direct linked contact should return 8."""
    contacts = [
        _make_contact(name="A", organization="Anthropic", pipeline_entries=["anthropic-se"]),
    ]
    assert suggest_network_proximity(contacts, "anthropic-se") == 8


def test_suggest_proximity_no_contacts():
    """No contacts at all should return 2."""
    assert suggest_network_proximity([], "some-entry") == 2


# --- Valid constants ---


def test_valid_channels_non_empty():
    """VALID_CHANNELS should contain expected values."""
    assert "linkedin" in VALID_CHANNELS
    assert "email" in VALID_CHANNELS
    assert "referral" in VALID_CHANNELS


def test_valid_interaction_types_non_empty():
    """VALID_INTERACTION_TYPES should contain expected values."""
    assert "connect" in VALID_INTERACTION_TYPES
    assert "dm" in VALID_INTERACTION_TYPES
    assert "meeting" in VALID_INTERACTION_TYPES
    assert "referral_ask" in VALID_INTERACTION_TYPES


# --- load/save round-trip ---


def test_save_and_load_roundtrip(monkeypatch, tmp_path):
    """Contacts saved to disk should round-trip through load_contacts."""
    contacts_file = tmp_path / "contacts.yaml"

    import crm

    monkeypatch.setattr(crm, "CONTACTS_FILE", contacts_file)

    original = [
        _make_contact(name="A", organization="X", strength=5),
        _make_contact(name="B", organization="Y", strength=8),
    ]
    save_contacts(original)

    loaded = load_contacts()
    assert len(loaded) == 2
    assert loaded[0]["name"] == "A"
    assert loaded[1]["name"] == "B"
    assert loaded[0]["relationship_strength"] == 5


def test_load_contacts_missing_file(monkeypatch, tmp_path):
    """load_contacts should return empty list if file missing."""
    import crm

    monkeypatch.setattr(crm, "CONTACTS_FILE", tmp_path / "nonexistent.yaml")

    assert load_contacts() == []


def test_load_contacts_empty_file(monkeypatch, tmp_path):
    """load_contacts should return empty list if file is empty."""
    contacts_file = tmp_path / "contacts.yaml"
    contacts_file.write_text("")

    import crm

    monkeypatch.setattr(crm, "CONTACTS_FILE", contacts_file)

    assert load_contacts() == []


# --- set_next_action ---


def test_set_next_action_persists(monkeypatch, tmp_path):
    """set_next_action should set action and date, persisting to disk."""
    contacts_file = _write_contacts(tmp_path, [_make_contact(name="Jane Smith")])

    import crm

    monkeypatch.setattr(crm, "CONTACTS_FILE", contacts_file)

    result = set_next_action(name="Jane Smith", action="Send follow-up DM", action_date="2026-03-10")

    assert result["next_action"] == "Send follow-up DM"
    assert result["next_action_date"] == "2026-03-10"

    # Verify persisted to disk
    saved = yaml.safe_load(contacts_file.read_text())
    contact = saved["contacts"][0]
    assert contact["next_action"] == "Send follow-up DM"
    assert contact["next_action_date"] == "2026-03-10"


def test_set_next_action_not_found_raises(monkeypatch, tmp_path):
    """set_next_action should raise ValueError when contact not found."""
    contacts_file = _write_contacts(tmp_path, [_make_contact(name="Jane Smith")])

    import crm

    monkeypatch.setattr(crm, "CONTACTS_FILE", contacts_file)

    with pytest.raises(ValueError, match="not found"):
        set_next_action(name="Ghost Person", action="Send email")


def test_set_next_action_empty_date(monkeypatch, tmp_path):
    """set_next_action should work with empty action_date."""
    contacts_file = _write_contacts(tmp_path, [
        _make_contact(name="Jane Smith", next_action="Old action", next_action_date="2026-01-01"),
    ])

    import crm

    monkeypatch.setattr(crm, "CONTACTS_FILE", contacts_file)

    result = set_next_action(name="Jane Smith", action="Review portfolio")

    assert result["next_action"] == "Review portfolio"
    assert result["next_action_date"] == ""


# --- get_uncovered_entries ---


def _make_entry(entry_id, org, status="qualified", score=7.0):
    """Build a minimal pipeline entry dict for testing."""
    return {
        "id": entry_id,
        "status": status,
        "target": {"organization": org, "application_url": f"https://example.com/{entry_id}"},
        "fit": {"score": score},
    }


def test_get_uncovered_entries_returns_uncovered(monkeypatch):
    """Should return entries whose org is not in contacts."""
    import crm

    contacts = [_make_contact(name="A", organization="Anthropic")]
    test_entries = [
        _make_entry("anthropic-se", "Anthropic", status="qualified", score=9.0),
        _make_entry("stripe-eng", "Stripe", status="drafting", score=8.5),
        _make_entry("openai-re", "OpenAI", status="staged", score=7.0),
    ]
    monkeypatch.setattr(crm, "load_entries", lambda include_filepath=True: test_entries)

    result = get_uncovered_entries(contacts)

    ids = [e["id"] for e in result]
    assert "anthropic-se" not in ids
    assert "stripe-eng" in ids
    assert "openai-re" in ids


def test_get_uncovered_entries_excludes_non_actionable(monkeypatch):
    """Should exclude entries with non-actionable statuses like research and closed."""
    import crm

    contacts = []  # No contacts — everything is uncovered if actionable
    test_entries = [
        _make_entry("active-one", "Stripe", status="qualified", score=9.0),
        _make_entry("research-one", "OpenAI", status="research", score=8.0),
        _make_entry("closed-one", "Google", status="closed", score=7.0),
        _make_entry("submitted-one", "Meta", status="submitted", score=6.0),
    ]
    monkeypatch.setattr(crm, "load_entries", lambda include_filepath=True: test_entries)

    result = get_uncovered_entries(contacts)

    ids = [e["id"] for e in result]
    assert "active-one" in ids
    assert "submitted-one" in ids
    assert "research-one" not in ids
    assert "closed-one" not in ids


def test_get_uncovered_entries_sorted_by_score_desc(monkeypatch):
    """Should return entries sorted by score descending."""
    import crm

    contacts = []
    test_entries = [
        _make_entry("low", "A Corp", status="qualified", score=5.0),
        _make_entry("high", "B Corp", status="drafting", score=9.5),
        _make_entry("mid", "C Corp", status="staged", score=7.0),
    ]
    monkeypatch.setattr(crm, "load_entries", lambda include_filepath=True: test_entries)

    result = get_uncovered_entries(contacts)

    scores = [e["fit"]["score"] for e in result]
    assert scores == [9.5, 7.0, 5.0]


# --- show_stats ---


def test_show_stats_prints_expected_sections(capsys):
    """show_stats should print CRM Statistics header and key sections."""
    contacts = [
        _make_contact(name="A", organization="Anthropic", strength=5, interactions=[
            {"date": date.today().isoformat(), "type": "dm", "note": "test"},
        ]),
        _make_contact(name="B", organization="Stripe", strength=8),
    ]

    show_stats(contacts)
    output = capsys.readouterr().out

    assert "CRM Statistics" in output
    assert "Total contacts: 2" in output
    assert "Organizations covered: 2" in output
    assert "Total interactions: 1" in output
    assert "Overdue actions: 0" in output
    assert "Strength Distribution:" in output
    assert "Organizations:" in output
    assert "Anthropic" in output
    assert "Stripe" in output


def test_show_stats_empty_contacts(capsys):
    """show_stats should work with empty contacts list."""
    show_stats([])
    output = capsys.readouterr().out

    assert "CRM Statistics" in output
    assert "Total contacts: 0" in output
    assert "Organizations covered: 0" in output
    assert "Total interactions: 0" in output


# --- show_dashboard ---


def test_show_dashboard_non_empty(monkeypatch, capsys):
    """show_dashboard should print expected sections for non-empty contacts."""
    import crm

    # Mock get_uncovered_entries to avoid loading real pipeline files
    monkeypatch.setattr(crm, "get_uncovered_entries", lambda contacts: [])

    contacts = [
        _make_contact(name="A", organization="Anthropic", strength=5, interactions=[
            {"date": date.today().isoformat(), "type": "dm", "note": "test"},
        ]),
        _make_contact(
            name="B",
            organization="Stripe",
            strength=8,
            next_action="Send DM",
            next_action_date=(date.today() - timedelta(days=2)).isoformat(),
        ),
    ]

    show_dashboard(contacts)
    output = capsys.readouterr().out

    assert "Relationship CRM Dashboard" in output
    assert "Contacts: 2" in output
    assert "Organizations: 2" in output
    assert "Relationship Strength Distribution:" in output
    assert "Contacts by Organization:" in output
    assert "Anthropic" in output
    assert "Stripe" in output
    # Overdue section (B has overdue action)
    assert "Overdue Actions" in output


def test_show_dashboard_empty_contacts(capsys):
    """show_dashboard should print 'No contacts' message for empty list."""
    show_dashboard([])
    output = capsys.readouterr().out

    assert "No contacts" in output
