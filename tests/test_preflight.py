"""Tests for scripts/preflight.py"""

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from preflight import check_entry, readiness_score

# --- Helpers ---


def _make_entry(**overrides) -> dict:
    """Create a test pipeline entry with sensible defaults."""
    future = (date.today() + timedelta(days=30)).isoformat()
    base = {
        "id": "test-entry",
        "name": "Test Entry",
        "track": "grant",
        "status": "staged",
        "target": {
            "organization": "Test Org",
            "application_url": "https://example.com/apply",
        },
        "deadline": {"date": future, "type": "hard"},
        "submission": {
            "effort_level": "quick",
            "blocks_used": {},
            "variant_ids": {},
            "materials_attached": [],
            "portfolio_url": "https://example.com/portfolio",
        },
    }
    base.update(overrides)
    return base


# --- check_entry ---


def test_check_entry_no_profile():
    """Flags when no profile exists for the entry — goes into errors."""
    entry = _make_entry(id="definitely-nonexistent-xyz")
    errors, warnings = check_entry(entry)
    assert any("no profile" in i for i in errors)


def test_check_entry_missing_portfolio_url():
    """Missing portfolio_url is advisory warning, not blocking error."""
    entry = _make_entry()
    entry["submission"]["portfolio_url"] = ""
    errors, warnings = check_entry(entry)
    assert any("portfolio_url" in i for i in warnings)
    assert not any("portfolio_url" in i for i in errors)


def test_check_entry_missing_application_url():
    """Missing application_url is a blocking error."""
    entry = _make_entry()
    entry["target"]["application_url"] = ""
    errors, warnings = check_entry(entry)
    assert any("application_url" in i for i in errors)


def test_check_entry_expired_deadline():
    """Flags when deadline has passed — goes into errors."""
    past = (date.today() - timedelta(days=5)).isoformat()
    entry = _make_entry()
    entry["deadline"] = {"date": past, "type": "hard"}
    errors, warnings = check_entry(entry)
    assert any("expired" in i for i in errors)


def test_check_entry_rolling_deadline_ok():
    """Rolling deadline doesn't flag as expired."""
    entry = _make_entry()
    entry["deadline"] = {"date": None, "type": "rolling"}
    errors, warnings = check_entry(entry)
    assert not any("expired" in i for i in errors)


def test_check_entry_material_not_found():
    """Flags when a referenced material file doesn't exist — goes into errors."""
    entry = _make_entry()
    entry["submission"]["materials_attached"] = ["nonexistent/file.pdf"]
    errors, warnings = check_entry(entry)
    assert any("material not found" in i for i in errors)


def test_check_entry_staged_requires_portal_fields():
    """Staged entries without portal_fields should fail preflight."""
    entry = _make_entry(id="definitely-nonexistent-xyz", status="staged", track="grant")
    entry.pop("portal_fields", None)
    errors, warnings = check_entry(entry)
    assert any("missing portal_fields on staged entry" in i for i in errors)


def test_check_entry_staged_job_missing_portal_fields_is_warning():
    """Staged jobs can proceed without portal_fields; this is advisory only."""
    entry = _make_entry(id="definitely-nonexistent-xyz", status="staged", track="job")
    entry.pop("portal_fields", None)
    errors, warnings = check_entry(entry)
    assert not any("missing portal_fields on staged entry" in i for i in errors)
    assert any("portal_fields not wired on staged job" in i for i in warnings)


def test_check_entry_real_artadia():
    """Integration test with real artadia-nyc entry (if available)."""
    from pipeline_lib import load_entry_by_id
    _, entry = load_entry_by_id("artadia-nyc")
    if entry is None:
        return  # skip if not available
    errors, warnings = check_entry(entry)
    # We expect artadia to have a profile and most fields — may still have issues
    assert not any("no profile" in i for i in errors)


def test_check_entry_mapped_profile():
    """Entries with profile ID mapping should find their profiles."""
    from pipeline_lib import load_entry_by_id
    _, entry = load_entry_by_id("creative-capital-2027")
    if entry is None:
        return  # skip if not available
    errors, warnings = check_entry(entry)
    assert not any("no profile" in i for i in errors)


def test_check_entry_all_ok():
    """Entry with no external dependencies passes basic structural checks."""
    # This tests structural checks only — profile/content checks depend on filesystem
    entry = _make_entry(id="definitely-nonexistent-xyz")
    errors, warnings = check_entry(entry)
    # Should have "no profile" in errors but not structural failures
    structural_errors = [i for i in errors if "application_url" in i
                         or "expired" in i or "material not found" in i]
    assert len(structural_errors) == 0


# --- Base resume detection ---


def test_check_entry_flags_base_resume():
    """Base resume is now a CRITICAL error (blocking submission)."""
    entry = _make_entry()
    entry["submission"]["materials_attached"] = ["resumes/base/multimedia-specialist.pdf"]
    errors, warnings = check_entry(entry)
    assert any("base resume" in i.lower() for i in errors)
    assert any("critical" in i.lower() for i in errors)


def test_check_entry_no_flag_for_tailored_resume():
    """Does not flag tailored resume as base."""
    entry = _make_entry()
    entry["submission"]["materials_attached"] = [
        "resumes/batch-03/test-entry/test-entry-resume.pdf"
    ]
    errors, warnings = check_entry(entry)
    assert not any("base resume" in i.lower() for i in warnings)
    assert not any("base resume" in i.lower() for i in errors)


# --- readiness_score ---


def test_readiness_score_empty_entry():
    """Entry with minimal fields gets a low score."""
    entry = _make_entry(id="definitely-nonexistent-xyz")
    entry["submission"]["materials_attached"] = []
    entry["submission"]["blocks_used"] = {}
    entry["submission"]["variant_ids"] = {}
    score = readiness_score(entry)
    assert 0 <= score <= 5


def test_readiness_score_resume_point():
    """Tailored resume contributes +1 to readiness score."""
    entry_base = _make_entry(id="definitely-nonexistent-xyz")
    entry_base["submission"]["materials_attached"] = ["resumes/base/multimedia-specialist.pdf"]

    entry_tailored = _make_entry(id="definitely-nonexistent-xyz")
    entry_tailored["submission"]["materials_attached"] = [
        "resumes/batch-03/test/test-resume.pdf"
    ]

    score_base = readiness_score(entry_base)
    score_tailored = readiness_score(entry_tailored)
    assert score_tailored > score_base


def test_readiness_score_blocks_point():
    """Populated blocks_used contributes +1."""
    entry_empty = _make_entry(id="definitely-nonexistent-xyz")
    entry_empty["submission"]["blocks_used"] = {}

    entry_blocks = _make_entry(id="definitely-nonexistent-xyz")
    entry_blocks["submission"]["blocks_used"] = {"framing": "framings/test"}

    assert readiness_score(entry_blocks) > readiness_score(entry_empty)


def test_readiness_score_cover_letter_point():
    """Cover letter variant contributes +1."""
    entry_no_cl = _make_entry(id="definitely-nonexistent-xyz")
    entry_no_cl["submission"]["variant_ids"] = {}

    entry_cl = _make_entry(id="definitely-nonexistent-xyz")
    entry_cl["submission"]["variant_ids"] = {"cover_letter": "cover-letters/test"}

    assert readiness_score(entry_cl) > readiness_score(entry_no_cl)


def test_readiness_score_staged_requires_portal_fields():
    """Staged entries should not get portal readiness credit without portal_fields."""
    no_portal = _make_entry(id="definitely-nonexistent-xyz", status="staged")
    no_portal.pop("portal_fields", None)

    with_portal = _make_entry(id="definitely-nonexistent-xyz", status="staged")
    with_portal["portal_fields"] = {"fields": [{"name": "bio"}]}

    assert readiness_score(with_portal) > readiness_score(no_portal)


def test_readiness_score_staged_job_portal_fields_optional():
    """Staged jobs keep portal readiness point from application_url without portal_fields."""
    job_no_portal = _make_entry(id="definitely-nonexistent-xyz", status="staged", track="job")
    job_no_portal.pop("portal_fields", None)

    job_with_portal = _make_entry(id="definitely-nonexistent-xyz", status="staged", track="job")
    job_with_portal["portal_fields"] = {"fields": [{"name": "bio"}]}

    assert readiness_score(job_no_portal) == readiness_score(job_with_portal)


def test_readiness_score_deadline_safe_point():
    """Deadline >3d or rolling gives +1."""
    future = (date.today() + timedelta(days=30)).isoformat()
    entry = _make_entry(id="definitely-nonexistent-xyz")
    entry["deadline"] = {"date": future, "type": "hard"}
    score_safe = readiness_score(entry)

    entry_tight = _make_entry(id="definitely-nonexistent-xyz")
    entry_tight["deadline"] = {"date": (date.today() + timedelta(days=1)).isoformat(), "type": "hard"}
    score_tight = readiness_score(entry_tight)

    assert score_safe > score_tight


def test_readiness_score_max_is_five():
    """Score cannot exceed 5."""
    entry = _make_entry(id="definitely-nonexistent-xyz")
    score = readiness_score(entry)
    assert score <= 5
