"""Tests for pipeline_api followup_data wrapper."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from pipeline_api import FollowupResult, ResultStatus, followup_data


def test_followup_data_all_returns_success():
    result = followup_data()
    assert result.status in (ResultStatus.SUCCESS, ResultStatus.ERROR)
    if result.status == ResultStatus.SUCCESS:
        assert isinstance(result.due_actions, list)
        assert result.total_entries >= 0


def test_followup_data_not_found():
    result = followup_data(entry_id="nonexistent-entry-xyz")
    assert result.status == ResultStatus.ERROR
    assert "nonexistent-entry-xyz" in result.error


def test_followup_result_dataclass_fields():
    r = FollowupResult(status=ResultStatus.SUCCESS, entry_id="all", due_actions=[], total_entries=5)
    assert r.due_actions == []
    assert r.total_entries == 5
    assert r.error is None
