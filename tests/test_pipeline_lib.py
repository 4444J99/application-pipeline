"""Tests for scripts/pipeline_lib.py"""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from pipeline_lib import (
    REPO_ROOT, ALL_PIPELINE_DIRS, BLOCKS_DIR, VARIANTS_DIR,
    VALID_TRACKS, VALID_STATUSES, ACTIONABLE_STATUSES, STATUS_ORDER,
    EFFORT_MINUTES, PROFILE_ID_MAP, LEGACY_ID_MAP, LEGACY_DIR, PROFILES_DIR,
    load_entries, load_entry_by_id, parse_date, parse_datetime,
    format_amount, get_effort, get_score, get_deadline, days_until,
    load_profile, load_legacy_script, _parse_legacy_markdown, _extract_section_content,
    detect_portal,
)


# --- Constants ---

def test_repo_root_exists():
    assert REPO_ROOT.exists()
    assert (REPO_ROOT / "pipeline").exists()


def test_all_pipeline_dirs_exist():
    for d in ALL_PIPELINE_DIRS:
        assert d.exists(), f"Pipeline dir missing: {d}"


def test_blocks_dir_exists():
    assert BLOCKS_DIR.exists()


def test_variants_dir_exists():
    assert VARIANTS_DIR.exists()


def test_actionable_statuses_subset():
    assert ACTIONABLE_STATUSES.issubset(VALID_STATUSES)


def test_status_order_complete():
    assert set(STATUS_ORDER) == VALID_STATUSES


def test_effort_minutes_values():
    assert EFFORT_MINUTES["quick"] < EFFORT_MINUTES["standard"]
    assert EFFORT_MINUTES["standard"] < EFFORT_MINUTES["deep"]
    assert EFFORT_MINUTES["deep"] < EFFORT_MINUTES["complex"]


# --- load_entries ---

def test_load_entries_returns_list():
    entries = load_entries()
    assert isinstance(entries, list)
    assert len(entries) > 0


def test_load_entries_has_metadata():
    entries = load_entries()
    for entry in entries:
        assert "_dir" in entry
        assert "_file" in entry


def test_load_entries_include_filepath():
    entries = load_entries(include_filepath=True)
    for entry in entries:
        assert "_filepath" in entry
        assert isinstance(entry["_filepath"], Path)


def test_load_entries_skips_schema():
    entries = load_entries()
    filenames = [e["_file"] for e in entries]
    assert "_schema.yaml" not in filenames


# --- load_entry_by_id ---

def test_load_entry_by_id_found():
    filepath, data = load_entry_by_id("creative-capital-2027")
    assert filepath is not None
    assert data is not None
    assert data["id"] == "creative-capital-2027"


def test_load_entry_by_id_not_found():
    filepath, data = load_entry_by_id("nonexistent-entry-xyz")
    assert filepath is None
    assert data is None


# --- parse_date ---

def test_parse_date_valid():
    result = parse_date("2026-02-23")
    assert result == date(2026, 2, 23)


def test_parse_date_none():
    assert parse_date(None) is None


def test_parse_date_empty():
    assert parse_date("") is None


def test_parse_date_invalid():
    assert parse_date("not-a-date") is None


def test_parse_date_accepts_date_object():
    """PyYAML may parse dates as date objects — parse_date should handle them."""
    assert parse_date(date(2026, 2, 23)) == date(2026, 2, 23)


# --- parse_datetime ---

def test_parse_datetime_valid():
    result = parse_datetime("2026-02-23")
    assert result is not None
    assert result.year == 2026
    assert result.month == 2
    assert result.day == 23


def test_parse_datetime_none():
    assert parse_datetime(None) is None


# --- format_amount ---

def test_format_amount_usd():
    assert format_amount({"value": 50000, "currency": "USD"}) == "$50,000"


def test_format_amount_eur():
    assert format_amount({"value": 10000, "currency": "EUR"}) == "EUR 10,000"


def test_format_amount_zero():
    assert format_amount({"value": 0, "currency": "USD"}) == "—"


def test_format_amount_in_kind():
    assert format_amount({"value": 0, "type": "in_kind"}) == "In-kind"


def test_format_amount_variable():
    assert format_amount({"value": 0, "type": "variable"}) == "Variable"


def test_format_amount_none():
    assert format_amount(None) == "—"


def test_format_amount_not_dict():
    assert format_amount("invalid") == "—"


# --- get_effort ---

def test_get_effort_present():
    entry = {"submission": {"effort_level": "deep"}}
    assert get_effort(entry) == "deep"


def test_get_effort_missing():
    entry = {}
    assert get_effort(entry) == "standard"


def test_get_effort_null():
    entry = {"submission": {"effort_level": None}}
    assert get_effort(entry) == "standard"


# --- get_score ---

def test_get_score_present():
    entry = {"fit": {"score": 8.5}}
    assert get_score(entry) == 8.5


def test_get_score_missing():
    entry = {}
    assert get_score(entry) == 0.0


def test_get_score_zero():
    entry = {"fit": {"score": 0}}
    assert get_score(entry) == 0.0


# --- get_deadline ---

def test_get_deadline_hard():
    entry = {"deadline": {"date": "2026-03-01", "type": "hard"}}
    dl_date, dl_type = get_deadline(entry)
    assert dl_date == date(2026, 3, 1)
    assert dl_type == "hard"


def test_get_deadline_rolling():
    entry = {"deadline": {"date": None, "type": "rolling"}}
    dl_date, dl_type = get_deadline(entry)
    assert dl_date is None
    assert dl_type == "rolling"


def test_get_deadline_missing():
    entry = {}
    dl_date, dl_type = get_deadline(entry)
    assert dl_date is None
    assert dl_type == "unknown"


# --- days_until ---

def test_days_until_future():
    from datetime import timedelta
    future = date.today() + timedelta(days=10)
    assert days_until(future) == 10


def test_days_until_past():
    from datetime import timedelta
    past = date.today() - timedelta(days=5)
    assert days_until(past) == -5


def test_days_until_today():
    assert days_until(date.today()) == 0


# --- PROFILE_ID_MAP ---


def test_profile_id_map_entries():
    """All mapped IDs point to profiles that exist."""
    for entry_id, profile_id in PROFILE_ID_MAP.items():
        filepath = PROFILES_DIR / f"{profile_id}.json"
        assert filepath.exists(), f"PROFILE_ID_MAP: {entry_id} -> {profile_id}.json not found"


def test_profile_id_map_no_direct_match():
    """Mapped entry IDs should NOT have a direct profile (that's why they're mapped)."""
    for entry_id in PROFILE_ID_MAP:
        filepath = PROFILES_DIR / f"{entry_id}.json"
        assert not filepath.exists(), (
            f"{entry_id}.json exists directly — remove from PROFILE_ID_MAP"
        )


# --- load_profile with ID mapping ---


def test_load_profile_direct():
    """Direct match loads without needing the map."""
    profile = load_profile("artadia-nyc")
    assert profile is not None
    assert profile["target_id"] == "artadia-nyc"


def test_load_profile_mapped():
    """Mapped ID loads the correct profile."""
    profile = load_profile("creative-capital-2027")
    assert profile is not None
    assert profile["target_id"] == "creative-capital"


def test_load_profile_mapped_doris_duke():
    profile = load_profile("doris-duke-amt")
    assert profile is not None


def test_load_profile_mapped_prix_ars():
    profile = load_profile("prix-ars-electronica")
    assert profile is not None


def test_load_profile_all_mapped_entries():
    """Every entry in PROFILE_ID_MAP should successfully load a profile."""
    for entry_id in PROFILE_ID_MAP:
        profile = load_profile(entry_id)
        assert profile is not None, f"load_profile('{entry_id}') returned None"


def test_load_profile_nonexistent():
    profile = load_profile("definitely-does-not-exist-xyz")
    assert profile is None


# --- LEGACY_ID_MAP ---


def test_legacy_id_map_files_exist():
    """All legacy script files referenced in the map should exist."""
    for legacy_name in LEGACY_ID_MAP:
        filepath = LEGACY_DIR / f"{legacy_name}.md"
        assert filepath.exists(), f"LEGACY_ID_MAP: {legacy_name}.md not found"


# --- load_legacy_script ---


def test_load_legacy_script_direct():
    """Direct match loads a legacy script."""
    result = load_legacy_script("artadia-nyc")
    assert result is not None
    assert isinstance(result, dict)
    assert "artist_statement" in result


def test_load_legacy_script_mapped():
    """Mapped entry ID loads the correct legacy script."""
    result = load_legacy_script("creative-capital-2027")
    assert result is not None
    assert isinstance(result, dict)


def test_load_legacy_script_nonexistent():
    result = load_legacy_script("definitely-does-not-exist-xyz")
    assert result is None


def test_load_legacy_script_has_bio():
    """Artadia legacy script should include a bio section."""
    result = load_legacy_script("artadia-nyc")
    assert result is not None
    assert "bio" in result


def test_load_legacy_script_no_preflight():
    """Parsed legacy scripts should not contain pre-flight sections."""
    result = load_legacy_script("artadia-nyc")
    assert result is not None
    for key in result:
        assert "pre-flight" not in key.lower()
        assert "post-submission" not in key.lower()


# --- _parse_legacy_markdown ---


def test_parse_legacy_markdown_basic():
    md = """# Title

## Artist Statement

**~250 words**

---

This is my artist statement content.
It has multiple lines.

---

## Bio

---

Short bio here.

---
"""
    result = _parse_legacy_markdown(md)
    assert "artist_statement" in result
    assert "bio" in result
    assert "artist statement content" in result["artist_statement"]
    assert "Short bio" in result["bio"]


def test_parse_legacy_markdown_skips_preflight():
    md = """## Pre-flight (2 minutes)

- [ ] Check this
- [ ] Check that

## Artist Statement

---

Real content here.

---
"""
    result = _parse_legacy_markdown(md)
    assert "artist_statement" in result
    assert "pre-flight" not in " ".join(result.keys()).lower()


def test_parse_legacy_markdown_project_description():
    md = """## Project Description / Why This Opportunity

---

This describes the project in detail.

---
"""
    result = _parse_legacy_markdown(md)
    assert "project_description" in result


# --- _extract_section_content ---


def test_extract_section_content_between_delimiters():
    text = """
**~250 words**

---

Real content is here.
Multiple lines of it.

---

Some notes after.
"""
    result = _extract_section_content(text)
    assert result is not None
    assert "Real content" in result


def test_extract_section_content_no_delimiters():
    text = """
This is just raw content without any delimiters.
It should still be extracted if it's long enough.
"""
    result = _extract_section_content(text)
    assert result is not None


def test_extract_section_content_only_metadata():
    text = """
**~250 words**

> Note: this is instructions only
"""
    result = _extract_section_content(text)
    assert result is None


# --- detect_portal ---


def test_detect_portal_greenhouse():
    assert detect_portal("https://job-boards.greenhouse.io/anthropic/jobs/123") == "greenhouse"
    assert detect_portal("https://boards-api.greenhouse.io/v1/boards/x/jobs/1") == "greenhouse"


def test_detect_portal_lever():
    assert detect_portal("https://jobs.lever.co/acme/abc-123") == "lever"
    assert detect_portal("https://jobs.eu.lever.co/euro/abc-123") == "lever"


def test_detect_portal_ashby():
    assert detect_portal("https://jobs.ashbyhq.com/cohere/1fa01a03-9253") == "ashby"


def test_detect_portal_workable():
    assert detect_portal("https://apply.workable.com/huggingface/j/abc/") == "workable"


def test_detect_portal_smartrecruiters():
    assert detect_portal("https://jobs.smartrecruiters.com/Acme/abc") == "smartrecruiters"


def test_detect_portal_submittable():
    assert detect_portal("https://artadia.submittable.com/submit/abc") == "submittable"


def test_detect_portal_slideroom():
    assert detect_portal("https://watermillcenter.slideroom.com/") == "slideroom"


def test_detect_portal_unknown():
    assert detect_portal("https://example.com/apply") is None
    assert detect_portal("") is None
    assert detect_portal("not-a-url") is None
