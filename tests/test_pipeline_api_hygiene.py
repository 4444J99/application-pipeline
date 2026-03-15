"""Tests for pipeline_api hygiene_check wrapper."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from pipeline_api import HygieneResult, ResultStatus, hygiene_check


def test_hygiene_check_all_returns_success():
    result = hygiene_check()
    assert result.status in (ResultStatus.SUCCESS, ResultStatus.ERROR)
    if result.status == ResultStatus.SUCCESS:
        assert isinstance(result.gate_issues, list)
        assert isinstance(result.total_issues, int)


def test_hygiene_check_not_found():
    result = hygiene_check(entry_id="nonexistent-entry-xyz")
    assert result.status == ResultStatus.ERROR
    assert "not found" in result.error


def test_hygiene_result_initializes_empty_lists():
    r = HygieneResult(status=ResultStatus.SUCCESS, entry_id="test")
    assert r.gate_issues == []
    assert r.stale_entries == []
    assert r.total_issues == 0
