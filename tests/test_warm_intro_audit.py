"""Tests for scripts/warm_intro_audit.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from warm_intro_audit import (
    display_audit,
    generate_audit_report,
    identify_referral_candidates,
    save_audit,
    scan_for_organizations,
    scan_submitted_for_contacts,
)

# --- Fixtures ---


def _entry(id, status="submitted", org="Acme", follow_up=None, response=False, channel="direct", track="job"):
    """Build a minimal pipeline entry for testing."""
    e = {
        "id": id,
        "status": status,
        "track": track,
        "channel": channel,
        "target": {"organization": org},
        "follow_up": follow_up or [],
        "conversion": {"response_received": response},
    }
    return e


# --- scan_submitted_for_contacts ---


def test_scan_contacts_finds_entries_with_contacts():
    entries = [
        _entry("a", follow_up=[{"contact": "Jane", "channel": "linkedin"}]),
        _entry("b"),
    ]
    result = scan_submitted_for_contacts(entries)
    assert len(result) == 1
    assert result[0]["id"] == "a"
    assert result[0]["contact_count"] == 1


def test_scan_contacts_finds_entries_with_response():
    entries = [_entry("a", response=True)]
    result = scan_submitted_for_contacts(entries)
    assert len(result) == 1
    assert result[0]["has_response"] is True


def test_scan_contacts_excludes_active_entries():
    entries = [
        _entry("a", status="drafting", follow_up=[{"contact": "Jane"}]),
    ]
    result = scan_submitted_for_contacts(entries)
    assert len(result) == 0


def test_scan_contacts_empty_followup_excluded():
    entries = [_entry("a", follow_up=[])]
    result = scan_submitted_for_contacts(entries)
    assert len(result) == 0


# --- scan_for_organizations ---


def test_scan_orgs_groups_by_org():
    entries = [
        _entry("a", org="Anthropic"),
        _entry("b", org="Anthropic"),
        _entry("c", org="Stripe"),
    ]
    result = scan_for_organizations(entries)
    assert "anthropic" in result
    assert len(result["anthropic"]) == 2
    assert "stripe" not in result  # only 1 entry


def test_scan_orgs_requires_two_or_more():
    entries = [_entry("a", org="Solo Inc")]
    result = scan_for_organizations(entries)
    assert len(result) == 0


def test_scan_orgs_case_insensitive():
    entries = [
        _entry("a", org="Anthropic"),
        _entry("b", org="anthropic"),
    ]
    result = scan_for_organizations(entries)
    assert "anthropic" in result


# --- identify_referral_candidates ---


def test_referral_candidates_from_org_with_contacts():
    entries = [
        _entry("sub-1", status="submitted", org="Anthropic", follow_up=[{"contact": "Jane"}]),
        _entry("act-1", status="qualified", org="Anthropic"),
    ]
    result = identify_referral_candidates(entries)
    assert len(result) == 1
    assert result[0]["id"] == "act-1"


def test_referral_candidates_high_density():
    entries = [
        _entry("a", status="submitted", org="BigCo"),
        _entry("b", status="submitted", org="BigCo"),
        _entry("c", status="submitted", org="BigCo"),
        _entry("d", status="drafting", org="BigCo"),
    ]
    result = identify_referral_candidates(entries)
    assert any(c["id"] == "d" for c in result)


def test_referral_candidates_excludes_submitted():
    entries = [
        _entry("a", status="submitted", org="Anthropic", follow_up=[{"contact": "Jane"}]),
        _entry("b", status="submitted", org="Anthropic"),
    ]
    result = identify_referral_candidates(entries)
    assert len(result) == 0  # both submitted, no active to convert


def test_referral_candidates_empty_when_no_density():
    entries = [
        _entry("a", status="qualified", org="Lonely Corp"),
    ]
    result = identify_referral_candidates(entries)
    assert len(result) == 0


# --- generate_audit_report ---


def test_report_has_required_keys():
    entries = [_entry("a"), _entry("b")]
    report = generate_audit_report(entries)
    assert "summary" in report
    assert "contact_entries" in report
    assert "dense_organizations" in report
    assert "referral_candidates" in report
    assert "recommendations" in report
    assert "generated" in report


def test_report_summary_counts():
    entries = [
        _entry("a", status="submitted"),
        _entry("b", status="acknowledged"),
        _entry("c", status="drafting"),
    ]
    report = generate_audit_report(entries)
    assert report["summary"]["total_submitted"] == 2
    assert report["summary"]["total_active"] == 1


def test_report_recommendations_nonempty():
    entries = [_entry("a")]
    report = generate_audit_report(entries)
    assert len(report["recommendations"]) > 0


# --- display_audit ---


def test_display_audit_prints(capsys):
    entries = [_entry("a"), _entry("b")]
    report = generate_audit_report(entries)
    display_audit(report)
    captured = capsys.readouterr()
    assert "WARM INTRO AUDIT" in captured.out


def test_display_audit_shows_referral_multiplier(capsys):
    entries = [_entry("a")]
    report = generate_audit_report(entries)
    display_audit(report)
    captured = capsys.readouterr()
    assert "8x" in captured.out


# --- save_audit ---


def test_save_audit_creates_file(tmp_path, monkeypatch):
    import warm_intro_audit as wia
    monkeypatch.setattr(wia, "SIGNALS_DIR", tmp_path)
    entries = [_entry("a"), _entry("b", org="Anthropic"), _entry("c", org="Anthropic")]
    report = generate_audit_report(entries)
    out = save_audit(report)
    assert out.exists()
    content = out.read_text()
    assert "Warm Intro Audit" in content
    assert "Recommendations" in content
