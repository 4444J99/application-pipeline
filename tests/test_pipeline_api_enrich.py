"""Tests for pipeline_api enrich_entry wrapper."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from pipeline_api import EnrichResult, ResultStatus, enrich_entry


def test_enrich_entry_requires_id_or_all():
    result = enrich_entry(entry_id=None, all_entries=False)
    assert result.status == ResultStatus.ERROR
    assert "required" in result.error


def test_enrich_entry_not_found():
    result = enrich_entry(entry_id="nonexistent-entry-id-xyz")
    assert result.status == ResultStatus.ERROR
    assert "not found" in result.error


def test_enrich_entry_all_returns_batch():
    result = enrich_entry(all_entries=True)
    assert result.status == ResultStatus.SUCCESS
    assert result.entry_id == "batch"
    assert isinstance(result.gaps, list)
    assert "gaps" in result.message or "entries" in result.message


def test_enrich_result_dataclass_fields():
    r = EnrichResult(status=ResultStatus.SUCCESS, entry_id="test", gaps=["materials"])
    assert r.gaps == ["materials"]
    assert r.error is None
