"""Tests for scripts/source_jobs.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from source_jobs import (
    _slugify,
    classify_location,
    create_pipeline_entry,
    filter_by_title,
    VALID_LOCATION_CLASSES,
)


# --- _slugify ---


def test_normalize_job_id():
    """ID normalization produces valid kebab-case."""
    assert _slugify("Senior Software Engineer") == "senior-software-engineer"
    assert _slugify("AI/ML Engineer (Remote)") == "aiml-engineer-remote"
    assert _slugify("Developer Advocate, Platform") == "developer-advocate-platform"


def test_slugify_truncation():
    """Long titles are truncated to 60 chars."""
    long_title = "A " * 50  # very long
    result = _slugify(long_title)
    assert len(result) <= 60


# --- create_pipeline_entry ---


def test_build_entry_yaml():
    """Generated entry has required schema fields."""
    job = {
        "title": "Software Engineer",
        "id": "12345",
        "url": "https://example.com/apply",
        "location": "San Francisco, CA",
        "company": "testco",
        "company_display": "TestCo",
        "portal": "greenhouse",
        "company_url": "https://boards.greenhouse.io/testco",
    }
    entry_id, entry = create_pipeline_entry(job)
    assert entry_id == "testco-software-engineer"
    assert entry["track"] == "job"
    assert entry["status"] == "research"
    assert entry["target"]["organization"] == "TestCo"
    assert entry["target"]["application_url"] == "https://example.com/apply"
    assert entry["target"]["portal"] == "greenhouse"
    assert "timeline" in entry
    assert "conversion" in entry
    assert "tags" in entry
    assert "auto-sourced" in entry["tags"]


# --- classify_location ---


def test_location_us_onsite():
    """US city classified as us-onsite."""
    assert classify_location("San Francisco, CA") == "us-onsite"


def test_location_us_remote():
    """Remote US classified as us-remote."""
    assert classify_location("Remote - US") == "us-remote"
    assert classify_location("United States (Remote)") == "us-remote"


def test_location_international():
    """International locations classified correctly."""
    assert classify_location("London, UK") == "international"
    assert classify_location("Tokyo, Japan") == "international"


def test_location_remote_global():
    """Plain 'Remote' classified as remote-global."""
    assert classify_location("Remote") == "remote-global"


def test_location_unknown():
    """Empty or ambiguous classified as unknown."""
    assert classify_location("") == "unknown"
    assert classify_location("   ") == "unknown"


def test_location_classes_complete():
    """All classify_location outputs are in VALID_LOCATION_CLASSES."""
    test_locs = ["San Francisco, CA", "Remote - US", "London, UK", "Remote", ""]
    for loc in test_locs:
        result = classify_location(loc)
        assert result in VALID_LOCATION_CLASSES, f"{loc!r} -> {result!r} not in valid set"


# --- filter_by_title ---


def test_filter_by_title_match():
    """Matching title passes filter."""
    jobs = [
        {"title": "Senior Software Engineer"},
        {"title": "Marketing Manager"},
    ]
    result = filter_by_title(jobs, ["software engineer"], ["intern"])
    assert len(result) == 1
    assert result[0]["title"] == "Senior Software Engineer"


def test_filter_by_title_exclude():
    """Excluded title filtered out."""
    jobs = [{"title": "Staff Engineer, Platform"}]
    result = filter_by_title(jobs, ["engineer"], ["staff engineer"])
    assert len(result) == 0
