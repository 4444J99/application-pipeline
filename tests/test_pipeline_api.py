"""Tests for scripts/pipeline_api.py helper behavior."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import pipeline_api as api


def test_natural_next_status_known_and_unknown():
    assert api._natural_next_status("research") == "qualified"
    assert api._natural_next_status("unknown-status") is None


def test_validation_result_initializes_empty_lists():
    result = api.ValidationResult(status=api.ResultStatus.SUCCESS, entry_id="x")
    assert result.errors == []
    assert result.warnings == []


def test_score_entry_rejects_mutually_exclusive_flags():
    result = api.score_entry(entry_id=None, auto_qualify=True, all_entries=True)
    assert result.status == api.ResultStatus.ERROR
    assert "mutually exclusive" in (result.error or "")


def test_advance_entry_requires_entry_id():
    result = api.advance_entry(entry_id="")
    assert result.status == api.ResultStatus.ERROR
    assert "entry_id required" in (result.error or "")
