"""Tests for scripts/derive_profile.py"""

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from derive_profile import (
    ART_TRACKS,
    _nested_get,
    apply_derivations,
    derive_from_pipeline,
    load_profile,
    show_derivation_report,
)

# --- _nested_get ---


def test_nested_get_simple():
    """Gets nested value correctly."""
    d = {"a": {"b": 42}}
    assert _nested_get(d, "a", "b") == 42


def test_nested_get_missing():
    """Returns default for missing path."""
    d = {"a": {"c": 1}}
    assert _nested_get(d, "a", "b") is None
    assert _nested_get(d, "a", "b", default=False) is False


def test_nested_get_non_dict():
    """Returns default when intermediate isn't a dict."""
    d = {"a": "string_value"}
    assert _nested_get(d, "a", "b") is None


def test_nested_get_empty():
    """Empty dict returns default."""
    assert _nested_get({}, "a") is None


# --- derive_from_pipeline ---


def test_derive_returns_list():
    """derive_from_pipeline returns a list."""
    profile = {"startup": {"prior_grant_history": False}}
    updates = derive_from_pipeline(profile)
    assert isinstance(updates, list)


def test_derive_update_has_required_fields():
    """Each update has the required fields."""
    profile = {}
    updates = derive_from_pipeline(profile)
    for u in updates:
        assert "section" in u
        assert "field" in u
        assert "current_value" in u
        assert "derived_value" in u
        assert "reason" in u
        assert "confidence" in u


# --- apply_derivations ---


def test_apply_derivations_dry_run():
    """Dry run returns modified dict without writing."""
    profile = {"startup": {"prior_grant_history": False}}
    updates = [{
        "section": "startup",
        "field": "prior_grant_history",
        "current_value": False,
        "derived_value": True,
        "reason": "test",
        "confidence": "high",
    }]
    result = apply_derivations(profile, updates, dry_run=True)
    assert result["startup"]["prior_grant_history"] is True
    # Original unchanged
    assert profile["startup"]["prior_grant_history"] is False


def test_apply_derivations_creates_section():
    """Creates section if it doesn't exist."""
    profile = {}
    updates = [{
        "section": "startup",
        "field": "test_field",
        "current_value": None,
        "derived_value": True,
        "reason": "test",
        "confidence": "high",
    }]
    result = apply_derivations(profile, updates, dry_run=True)
    assert result["startup"]["test_field"] is True


def test_apply_derivations_empty_updates():
    """Empty updates returns unchanged copy."""
    profile = {"startup": {"x": 1}}
    result = apply_derivations(profile, [], dry_run=True)
    assert result == profile


def test_apply_derivations_writes_file(tmp_path, monkeypatch):
    """Non-dry-run writes to the profile file."""
    profile_file = tmp_path / "startup-profile.yaml"
    profile_file.write_text(yaml.dump({"startup": {"prior_grant_history": False}}))
    monkeypatch.setattr("derive_profile.PROFILE_FILE", profile_file)

    profile = {"startup": {"prior_grant_history": False}}
    updates = [{
        "section": "startup",
        "field": "prior_grant_history",
        "current_value": False,
        "derived_value": True,
        "reason": "test",
        "confidence": "high",
    }]
    apply_derivations(profile, updates, dry_run=False)

    # File should be updated
    with open(profile_file) as f:
        saved = yaml.safe_load(f)
    assert saved["startup"]["prior_grant_history"] is True


# --- load_profile ---


def test_load_profile_returns_dict():
    """load_profile returns a dict."""
    result = load_profile()
    assert isinstance(result, dict)


# --- show_derivation_report ---


def test_show_derivation_report_no_updates(capsys):
    """No updates prints 'No changes needed'."""
    show_derivation_report({}, [])
    out = capsys.readouterr().out
    assert "No changes needed" in out


def test_show_derivation_report_with_updates(capsys):
    """Updates are printed with field details."""
    updates = [{
        "section": "startup",
        "field": "prior_grant_history",
        "current_value": False,
        "derived_value": True,
        "reason": "2 submitted",
        "confidence": "high",
    }]
    show_derivation_report({}, updates)
    out = capsys.readouterr().out
    assert "prior_grant_history" in out
    assert "2 submitted" in out


# --- ART_TRACKS ---


def test_art_tracks_includes_expected():
    """ART_TRACKS contains the expected creative tracks."""
    for track in ("grant", "residency", "fellowship", "prize"):
        assert track in ART_TRACKS


def test_art_tracks_excludes_jobs():
    """ART_TRACKS does not include job/consulting."""
    assert "job" not in ART_TRACKS
    assert "consulting" not in ART_TRACKS
