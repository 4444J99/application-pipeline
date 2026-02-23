"""Tests for scripts/pipeline_lib.py"""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from pipeline_lib import (
    REPO_ROOT, ALL_PIPELINE_DIRS, BLOCKS_DIR, VARIANTS_DIR,
    VALID_TRACKS, VALID_STATUSES, ACTIONABLE_STATUSES, STATUS_ORDER,
    EFFORT_MINUTES,
    load_entries, load_entry_by_id, parse_date, parse_datetime,
    format_amount, get_effort, get_score, get_deadline, days_until,
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
