"""Tests for scripts/generate_job_profile.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from generate_job_profile import (
    EVIDENCE_BY_POSITION,
    STANDARD_WORK_SAMPLES,
    find_entries_without_profiles,
    generate_profile,
    profile_exists,
)
from pipeline_lib import PROFILES_DIR

# ---------------------------------------------------------------------------
# generate_profile
# ---------------------------------------------------------------------------


def test_generate_profile_basic_fields():
    """Generated profile has all required fields."""
    entry = {
        "id": "test-corp-swe",
        "name": "Test Corp: Software Engineer",
        "track": "job",
        "status": "qualified",
        "fit": {"identity_position": "independent-engineer"},
        "target": {"application_url": "https://example.com/apply", "compensation": "$150K"},
    }
    profile = generate_profile(entry)

    assert profile["target_id"] == "test-corp-swe"
    assert profile["target_name"] == "Test Corp: Software Engineer"
    assert profile["category"] == "Job"
    assert profile["primary_position"] == "independent-engineer"
    assert profile["auto_generated"] is True
    assert "generated" in profile
    assert isinstance(profile["work_samples"], list)
    assert len(profile["work_samples"]) > 0
    assert isinstance(profile["evidence_highlights"], list)
    assert len(profile["evidence_highlights"]) > 0


def test_generate_profile_default_position():
    """Missing identity position defaults to independent-engineer."""
    entry = {"id": "no-fit", "name": "No Fit Entry", "track": "job"}
    profile = generate_profile(entry)
    assert profile["primary_position"] == "independent-engineer"


def test_generate_profile_optional_amount():
    """Compensation is included when present in target."""
    entry = {
        "id": "with-comp",
        "name": "With Comp",
        "track": "job",
        "target": {"compensation": "$200K"},
    }
    profile = generate_profile(entry)
    assert profile["amount"] == "$200K"


def test_generate_profile_no_amount_when_missing():
    """No amount field when compensation is absent."""
    entry = {"id": "no-comp", "name": "No Comp", "track": "job", "target": {}}
    profile = generate_profile(entry)
    assert "amount" not in profile


def test_generate_profile_work_samples_match_standard():
    """Work samples use the standard set."""
    entry = {"id": "std", "name": "Standard", "track": "job"}
    profile = generate_profile(entry)
    assert profile["work_samples"] == STANDARD_WORK_SAMPLES


def test_generate_profile_evidence_by_position():
    """Evidence highlights match the identity position."""
    for position, expected in EVIDENCE_BY_POSITION.items():
        entry = {"id": f"pos-{position}", "name": "Test", "track": "job", "fit": {"identity_position": position}}
        profile = generate_profile(entry)
        assert profile["evidence_highlights"] == expected


# ---------------------------------------------------------------------------
# find_entries_without_profiles
# ---------------------------------------------------------------------------


def test_find_entries_without_profiles_filters_non_auto_sourced():
    """Only auto-sourced entries are considered."""
    entries = [
        {"id": "manual-entry", "tags": ["curated"], "status": "qualified"},
        {"id": "auto-entry", "tags": ["auto-sourced"], "status": "qualified"},
    ]
    # The auto-entry will likely not have a profile (entry ID doesn't match real profiles)
    result = find_entries_without_profiles(entries)
    ids = [e["id"] for e in result]
    assert "manual-entry" not in ids


def test_find_entries_without_profiles_skips_terminal():
    """Terminal status entries are excluded."""
    entries = [
        {"id": "withdrawn-entry", "tags": ["auto-sourced"], "status": "withdrawn"},
        {"id": "outcome-entry", "tags": ["auto-sourced"], "status": "outcome"},
    ]
    result = find_entries_without_profiles(entries)
    assert len(result) == 0


def test_find_entries_without_profiles_skips_existing():
    """Entries with existing profiles are excluded."""
    # Use a known profile ID that exists
    existing_profiles = [p.stem for p in PROFILES_DIR.glob("*.json") if p.stem != "profiles-index"]
    if existing_profiles:
        entry_id = existing_profiles[0]
        entries = [{"id": entry_id, "tags": ["auto-sourced"], "status": "qualified"}]
        result = find_entries_without_profiles(entries)
        assert len(result) == 0


# ---------------------------------------------------------------------------
# profile_exists
# ---------------------------------------------------------------------------


def test_profile_exists_real_profiles():
    """Known real profiles are detected as existing."""
    existing = [p.stem for p in PROFILES_DIR.glob("*.json") if p.stem != "profiles-index"]
    if existing:
        assert profile_exists(existing[0]) is True


def test_profile_exists_nonexistent():
    """Non-existent profile ID returns False."""
    assert profile_exists("zzz-nonexistent-company-12345") is False


def test_profile_exists_via_map():
    """PROFILE_ID_MAP entries resolve correctly."""
    # creative-capital-2027 maps to creative-capital.json
    if (PROFILES_DIR / "creative-capital.json").exists():
        assert profile_exists("creative-capital-2027") is True
