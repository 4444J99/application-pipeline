"""Tests for scripts/submit_ready.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from submit_ready import (
    PORTAL_SCRIPTS,
    apply_company_cap,
    gather_ready_entries,
    group_by_portal,
)

# --- PORTAL_SCRIPTS ---


def test_portal_scripts_defined():
    """PORTAL_SCRIPTS has entries for greenhouse, ashby, lever, and email."""
    assert "greenhouse" in PORTAL_SCRIPTS
    assert "ashby" in PORTAL_SCRIPTS
    assert "lever" in PORTAL_SCRIPTS
    assert "email" in PORTAL_SCRIPTS


def test_portal_scripts_values_are_tuples():
    """Each PORTAL_SCRIPTS value is a (script_name, supports_record) tuple."""
    for portal, value in PORTAL_SCRIPTS.items():
        assert isinstance(value, tuple), f"{portal} value is not a tuple"
        assert len(value) == 2, f"{portal} tuple has wrong length"
        script_name, supports_record = value
        assert isinstance(script_name, str), f"{portal} script_name is not str"
        assert script_name.endswith(".py"), f"{portal} script_name missing .py suffix"
        assert isinstance(supports_record, bool), f"{portal} supports_record is not bool"


def test_portal_scripts_email_supports_record():
    """Email submitter supports --record flag."""
    _, supports_record = PORTAL_SCRIPTS["email"]
    assert supports_record is True


def test_portal_scripts_greenhouse_no_record():
    """Greenhouse submitter does not support --record flag (handled externally)."""
    _, supports_record = PORTAL_SCRIPTS["greenhouse"]
    assert supports_record is False


# --- gather_ready_entries ---


def test_gather_ready_entries_returns_list():
    """gather_ready_entries returns a list."""
    result = gather_ready_entries()
    assert isinstance(result, list)


def test_gather_ready_entries_items_are_dicts():
    """Each item returned by gather_ready_entries is a dict with audit keys."""
    result = gather_ready_entries()
    for item in result:
        assert isinstance(item, dict)
        assert "id" in item
        assert "portal" in item
        assert "ready" in item
        assert item["ready"] is True  # gather_ready_entries filters to ready only
        assert "_org" in item  # organization is attached for company cap


def test_gather_ready_entries_portal_filter():
    """gather_ready_entries filters by portal when specified."""
    # This should not raise and should return a list (possibly empty)
    result = gather_ready_entries(portal_filter="greenhouse")
    assert isinstance(result, list)
    for item in result:
        assert item["portal"] == "greenhouse"


def test_gather_ready_entries_unknown_portal_filter():
    """gather_ready_entries returns empty list for non-existent portal."""
    result = gather_ready_entries(portal_filter="nonexistent_portal_xyz")
    assert result == []


# --- group_by_portal ---


def test_group_by_portal():
    """group_by_portal groups results by portal type."""
    results = [
        {"id": "entry-1", "portal": "greenhouse", "ready": True},
        {"id": "entry-2", "portal": "greenhouse", "ready": True},
        {"id": "entry-3", "portal": "ashby", "ready": True},
        {"id": "entry-4", "portal": "email", "ready": True},
    ]
    groups = group_by_portal(results)
    assert isinstance(groups, dict)
    assert "greenhouse" in groups
    assert "ashby" in groups
    assert "email" in groups
    assert len(groups["greenhouse"]) == 2
    assert len(groups["ashby"]) == 1
    assert len(groups["email"]) == 1


def test_group_by_portal_empty():
    """group_by_portal returns empty dict for empty input."""
    groups = group_by_portal([])
    assert groups == {}


def test_group_by_portal_single():
    """group_by_portal handles single-item list."""
    groups = group_by_portal([{"id": "only", "portal": "lever", "ready": True}])
    assert "lever" in groups
    assert len(groups["lever"]) == 1


def test_group_by_portal_preserves_all_fields():
    """group_by_portal preserves all fields in result dicts."""
    results = [
        {
            "id": "test-entry",
            "portal": "greenhouse",
            "ready": True,
            "pass_count": 6,
            "total_checks": 6,
            "_org": "TestOrg",
        },
    ]
    groups = group_by_portal(results)
    entry = groups["greenhouse"][0]
    assert entry["id"] == "test-entry"
    assert entry["pass_count"] == 6
    assert entry["_org"] == "TestOrg"


# --- apply_company_cap ---


def test_apply_company_cap():
    """apply_company_cap limits entries per organization."""
    results = [
        {"id": "anthropic-1", "_org": "Anthropic"},
        {"id": "anthropic-2", "_org": "Anthropic"},
        {"id": "anthropic-3", "_org": "Anthropic"},
        {"id": "stripe-1", "_org": "Stripe"},
        {"id": "stripe-2", "_org": "Stripe"},
    ]
    filtered = apply_company_cap(results, max_per_company=2)
    assert len(filtered) == 4  # 2 Anthropic + 2 Stripe

    # Check that the first two Anthropic entries are kept
    anthropic_ids = [r["id"] for r in filtered if r["_org"] == "Anthropic"]
    assert len(anthropic_ids) == 2
    assert "anthropic-1" in anthropic_ids
    assert "anthropic-2" in anthropic_ids

    # Stripe entries should all pass (only 2)
    stripe_ids = [r["id"] for r in filtered if r["_org"] == "Stripe"]
    assert len(stripe_ids) == 2


def test_apply_company_cap_zero_disables():
    """apply_company_cap with max_per_company=0 returns all entries (no cap)."""
    results = [
        {"id": "entry-1", "_org": "Org"},
        {"id": "entry-2", "_org": "Org"},
        {"id": "entry-3", "_org": "Org"},
    ]
    filtered = apply_company_cap(results, max_per_company=0)
    assert len(filtered) == 3


def test_apply_company_cap_one():
    """apply_company_cap with max_per_company=1 keeps only first entry per org."""
    results = [
        {"id": "a-1", "_org": "A"},
        {"id": "a-2", "_org": "A"},
        {"id": "b-1", "_org": "B"},
        {"id": "b-2", "_org": "B"},
        {"id": "b-3", "_org": "B"},
    ]
    filtered = apply_company_cap(results, max_per_company=1)
    assert len(filtered) == 2
    ids = [r["id"] for r in filtered]
    assert "a-1" in ids
    assert "b-1" in ids


def test_apply_company_cap_high_limit():
    """apply_company_cap with limit higher than any org's count returns all."""
    results = [
        {"id": "x-1", "_org": "X"},
        {"id": "x-2", "_org": "X"},
        {"id": "y-1", "_org": "Y"},
    ]
    filtered = apply_company_cap(results, max_per_company=100)
    assert len(filtered) == 3


def test_apply_company_cap_empty():
    """apply_company_cap handles empty input list."""
    filtered = apply_company_cap([], max_per_company=2)
    assert filtered == []


def test_apply_company_cap_unknown_org():
    """apply_company_cap handles missing _org gracefully."""
    results = [
        {"id": "no-org-1"},
        {"id": "no-org-2"},
        {"id": "no-org-3"},
    ]
    # Missing _org defaults to "unknown" in the function
    filtered = apply_company_cap(results, max_per_company=2)
    assert len(filtered) == 2
