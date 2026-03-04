"""Integration tests for pipeline_api module with real repository fixtures."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

# Ensure scripts dir is in path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from pipeline_api import (
    ResultStatus,
    advance_entry,
    compose_entry,
    draft_entry,
    score_entry,
    validate_entry,
)
from pipeline_lib import VALID_TRANSITIONS

REPO_ROOT = Path(__file__).resolve().parent.parent
PIPELINE_DIRS = [
    REPO_ROOT / "pipeline" / "active",
    REPO_ROOT / "pipeline" / "submitted",
    REPO_ROOT / "pipeline" / "closed",
    REPO_ROOT / "pipeline" / "research_pool",
]
_NEXT_STATUS = {
    "research": "qualified",
    "qualified": "drafting",
    "drafting": "staged",
    "staged": "submitted",
    "deferred": "qualified",
    "submitted": "acknowledged",
    "acknowledged": "interview",
    "interview": "outcome",
}


def _first_entry_id() -> str:
    for pipeline_dir in PIPELINE_DIRS:
        for path in sorted(pipeline_dir.glob("*.yaml")):
            if path.name.startswith("_"):
                continue
            return path.stem
    raise AssertionError("No pipeline entries found for integration tests")


def _first_advanceable_entry() -> tuple[str, str]:
    for pipeline_dir in PIPELINE_DIRS:
        for path in sorted(pipeline_dir.glob("*.yaml")):
            if path.name.startswith("_"):
                continue
            data = yaml.safe_load(path.read_text()) or {}
            status = data.get("status")
            target = _NEXT_STATUS.get(status)
            if target and target in VALID_TRANSITIONS.get(status, set()):
                return path.stem, target
    raise AssertionError("No advanceable entry found for integration tests")


def test_score_entry_requires_parameters():
    result = score_entry(entry_id=None, auto_qualify=False, all_entries=False)
    assert result.status == ResultStatus.ERROR
    assert "required" in (result.error or "").lower()


def test_score_entry_dry_run_single():
    entry_id = _first_entry_id()
    result = score_entry(entry_id=entry_id, dry_run=True)
    assert result.status == ResultStatus.DRY_RUN
    assert result.entry_id == entry_id
    assert isinstance(result.new_score, float)
    assert isinstance(result.dimensions, dict)


def test_score_entry_dry_run_all_entries():
    result = score_entry(entry_id=None, all_entries=True, dry_run=True)
    assert result.status == ResultStatus.DRY_RUN
    assert result.entry_id == "batch"
    assert "scored" in result.message.lower()


def test_advance_requires_entry_id():
    result = advance_entry(entry_id=None)
    assert result.status == ResultStatus.ERROR
    assert "entry_id required" in (result.error or "").lower()


def test_advance_dry_run_real_transition():
    entry_id, target = _first_advanceable_entry()
    result = advance_entry(entry_id=entry_id, to_status=target, dry_run=True)
    assert result.status == ResultStatus.DRY_RUN
    assert result.entry_id == entry_id
    assert result.new_status == target


def test_draft_requires_entry_id():
    result = draft_entry(entry_id=None)
    assert result.status == ResultStatus.ERROR
    assert "entry_id required" in (result.error or "").lower()


def test_draft_dry_run_content():
    entry_id = _first_entry_id()
    result = draft_entry(entry_id=entry_id, dry_run=True)
    assert result.status == ResultStatus.DRY_RUN
    assert result.entry_id == entry_id
    assert isinstance(result.content, str)
    assert len(result.content) > 0


def test_compose_requires_entry_id():
    result = compose_entry(entry_id=None)
    assert result.status == ResultStatus.ERROR
    assert "entry_id required" in (result.error or "").lower()


def test_compose_dry_run_content():
    entry_id = _first_entry_id()
    result = compose_entry(entry_id=entry_id, dry_run=True)
    assert result.status == ResultStatus.DRY_RUN
    assert result.entry_id == entry_id
    assert isinstance(result.content, str)
    assert isinstance(result.word_count, int)
    assert result.word_count > 0


def test_validate_all_entries_success():
    result = validate_entry()
    assert result.entry_id == "all"
    assert isinstance(result.errors, list)
    assert isinstance(result.warnings, list)
    assert result.status == ResultStatus.SUCCESS
    assert result.is_valid is True


def test_validate_dict_input():
    entry_dict = {
        "id": "test-entry",
        "name": "Test Entry",
        "track": "job",
        "status": "research",
    }
    result = validate_entry(entry_dict=entry_dict)
    assert result.status == ResultStatus.SUCCESS
    assert result.is_valid is True

