"""Tests for discover_jobs.py — skill-based job discovery."""

import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../scripts")))

from discover_jobs import (
    DEFAULT_MIN_SCORE,
    QUERIES_FILE,
    VALID_POSITIONS,
    create_discovery_entry,
    cross_position_dedup,
    display_results,
    load_queries,
    normalize_job,
)

# --- Fixtures ---


def _make_job(**overrides):
    """Create a minimal job dict for testing."""
    base = {
        "title": "Creative Technologist",
        "id": "12345",
        "url": "https://example.com/jobs/12345",
        "location": "Remote",
        "company": "example-co",
        "company_display": "Example Co",
        "portal": "remotive",
        "company_url": "",
        "posting_date": "2026-03-01",
    }
    base.update(overrides)
    return base


# --- Query config ---


def test_valid_positions_list():
    """All five identity positions are defined."""
    assert len(VALID_POSITIONS) == 5
    assert "independent-engineer" in VALID_POSITIONS
    assert "systems-artist" in VALID_POSITIONS
    assert "educator" in VALID_POSITIONS
    assert "creative-technologist" in VALID_POSITIONS
    assert "community-practitioner" in VALID_POSITIONS


def test_load_queries_returns_dict():
    """load_queries returns a dict when config file exists."""
    if not QUERIES_FILE.exists():
        pytest.skip("No .discovery-queries.yaml found")
    cfg = load_queries()
    assert isinstance(cfg, dict)
    assert "positions" in cfg
    assert "apis" in cfg


def test_load_queries_has_position_entries():
    """Each position in config has queries list."""
    if not QUERIES_FILE.exists():
        pytest.skip("No .discovery-queries.yaml found")
    cfg = load_queries()
    positions = cfg.get("positions", {})
    for pos in VALID_POSITIONS:
        if pos in positions:
            assert "queries" in positions[pos], f"{pos} missing queries list"
            assert len(positions[pos]["queries"]) > 0, f"{pos} has empty queries"


# --- Normalization ---


def test_normalize_job_adds_fields():
    """normalize_job adds source_api and identity_position."""
    job = _make_job()
    result = normalize_job(job, "remotive", "creative-technologist")
    assert result["source_api"] == "remotive"
    assert result["identity_position"] == "creative-technologist"


def test_normalize_job_preserves_existing_portal():
    """normalize_job keeps portal if already set."""
    job = _make_job(portal="greenhouse")
    result = normalize_job(job, "remotive", "independent-engineer")
    assert result["portal"] == "greenhouse"


def test_normalize_job_sets_portal_from_source():
    """normalize_job sets portal from source_api if empty."""
    job = _make_job(portal="")
    result = normalize_job(job, "himalayas", "educator")
    assert result["portal"] == "himalayas"


# --- Cross-position dedup ---


def test_cross_position_dedup_keeps_highest_score():
    """Dedup keeps the entry with the highest score for same company+title."""
    job_low = _make_job()
    job_low["_score"] = 5.0
    job_low["identity_position"] = "educator"

    job_high = _make_job()
    job_high["_score"] = 8.0
    job_high["identity_position"] = "creative-technologist"

    result = cross_position_dedup([job_low, job_high])
    assert len(result) == 1
    assert result[0]["_score"] == 8.0
    assert result[0]["identity_position"] == "creative-technologist"


def test_cross_position_dedup_different_jobs():
    """Different company+title pairs are all kept."""
    job_a = _make_job(company="alpha", title="Engineer")
    job_a["_score"] = 7.0

    job_b = _make_job(company="beta", title="Designer")
    job_b["_score"] = 6.0

    result = cross_position_dedup([job_a, job_b])
    assert len(result) == 2


def test_cross_position_dedup_empty():
    """Empty input returns empty output."""
    assert cross_position_dedup([]) == []


# --- Entry creation ---


def test_create_discovery_entry_sets_position():
    """Discovery entries get the correct identity position."""
    job = _make_job(identity_position="systems-artist")
    entry_id, entry = create_discovery_entry(job)
    assert entry["fit"]["identity_position"] == "systems-artist"


def test_create_discovery_entry_sets_source():
    """Discovery entries are tagged with discover_jobs.py source."""
    job = _make_job(identity_position="educator")
    entry_id, entry = create_discovery_entry(job)
    assert entry["source"] == "discover_jobs.py"


def test_create_discovery_entry_tags():
    """Discovery entries have discovery-specific tags."""
    job = _make_job(identity_position="creative-technologist")
    _, entry = create_discovery_entry(job)
    assert "auto-sourced" in entry["tags"]
    assert "discovery" in entry["tags"]
    assert "pos:creative-technologist" in entry["tags"]


def test_create_discovery_entry_clears_resume_for_non_engineer():
    """Non-engineer positions don't get the default engineer resume."""
    job = _make_job(identity_position="systems-artist")
    _, entry = create_discovery_entry(job)
    assert entry["submission"]["materials_attached"] == []


def test_create_discovery_entry_keeps_resume_for_engineer():
    """Independent-engineer position keeps the default resume."""
    job = _make_job(identity_position="independent-engineer")
    _, entry = create_discovery_entry(job)
    assert len(entry["submission"]["materials_attached"]) > 0


def test_create_discovery_entry_id_format():
    """Entry ID is slugified company-title."""
    job = _make_job(company_display="Acme Corp", title="Creative Developer")
    entry_id, _ = create_discovery_entry(job)
    assert "acme-corp" in entry_id
    assert "creative-developer" in entry_id


# --- Display ---


def test_display_results_no_crash(capsys):
    """display_results handles empty list without error."""
    display_results([], dry_run=True)
    out = capsys.readouterr().out
    assert "No new jobs" in out


def test_display_results_groups_by_position(capsys):
    """display_results shows position headers."""
    job = _make_job(identity_position="creative-technologist")
    job["_score"] = 7.5
    job["source_api"] = "remotive"
    display_results([job], dry_run=True)
    out = capsys.readouterr().out
    assert "creative-technologist" in out
    assert "7.5" in out


# --- Default constants ---


def test_default_min_score():
    """Default minimum score is reasonable."""
    assert DEFAULT_MIN_SCORE >= 0.0
    assert DEFAULT_MIN_SCORE <= 10.0


# --- run.py integration ---


def test_discover_in_run_commands():
    """discover command is registered in run.py COMMANDS."""
    from run import COMMANDS, PARAM_COMMANDS
    assert "discover" in COMMANDS or "discover" in PARAM_COMMANDS
