"""Tests for scripts/source_jobs_constants.py."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from source_jobs_constants import (
    HTTP_TIMEOUT,
    INTERNATIONAL_MARKERS,
    TITLE_EXCLUDES,
    TITLE_KEYWORDS,
    US_CITIES,
    US_KEYWORDS,
    US_STATES,
    VALID_LOCATION_CLASSES,
)


def test_title_filters_non_empty():
    assert TITLE_KEYWORDS
    assert TITLE_EXCLUDES


def test_location_class_domain_is_expected():
    assert VALID_LOCATION_CLASSES == {"us-onsite", "us-remote", "remote-global", "international", "unknown"}


def test_us_location_hints_present():
    assert "ca" in US_STATES
    assert "new york" in US_CITIES
    assert any("remote us" in s for s in US_KEYWORDS)


def test_international_markers_present():
    assert "london" in INTERNATIONAL_MARKERS
    assert HTTP_TIMEOUT > 0
