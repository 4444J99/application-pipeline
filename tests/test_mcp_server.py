import json
import os
import sys
from pathlib import Path

# Ensure scripts dir is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../scripts')))

from mcp_server import pipeline_advance, pipeline_compose, pipeline_draft, pipeline_score, pipeline_validate

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
    repo_root = Path(__file__).resolve().parent.parent
    for rel in ("pipeline/active", "pipeline/submitted", "pipeline/closed", "pipeline/research_pool"):
        pipeline_dir = repo_root / rel
        for path in sorted(pipeline_dir.glob("*.yaml")):
            if not path.name.startswith("_"):
                return path.stem
    raise AssertionError("No pipeline entries found")


def _first_advanceable_entry() -> tuple[str, str]:
    import yaml

    repo_root = Path(__file__).resolve().parent.parent
    for rel in ("pipeline/active", "pipeline/submitted", "pipeline/closed", "pipeline/research_pool"):
        pipeline_dir = repo_root / rel
        for path in sorted(pipeline_dir.glob("*.yaml")):
            if path.name.startswith("_"):
                continue
            data = yaml.safe_load(path.read_text()) or {}
            status = data.get("status")
            target = _NEXT_STATUS.get(status)
            if target:
                return path.stem, target
    raise AssertionError("No advanceable entry found")


def test_pipeline_score_tool():
    """Verify pipeline_score returns JSON result."""
    entry_id = _first_entry_id()
    result = pipeline_score(entry_id)
    data = json.loads(result)
    assert "status" in data
    assert "entry_id" in data
    assert data["entry_id"] == entry_id
    assert data["status"] in {"dry_run", "success"}


def test_pipeline_advance_tool():
    """Verify pipeline_advance returns JSON result."""
    entry_id, target = _first_advanceable_entry()
    result = pipeline_advance(entry_id, to_status=target)
    data = json.loads(result)
    assert "status" in data
    assert "entry_id" in data
    assert data["entry_id"] == entry_id


def test_pipeline_draft_tool():
    """Verify pipeline_draft returns JSON result."""
    entry_id = _first_entry_id()
    result = pipeline_draft(entry_id)
    data = json.loads(result)
    assert "status" in data
    assert "entry_id" in data
    assert data["entry_id"] == entry_id


def test_pipeline_compose_tool():
    """Verify pipeline_compose returns JSON result."""
    entry_id = _first_entry_id()
    result = pipeline_compose(entry_id)
    data = json.loads(result)
    assert "status" in data
    assert "entry_id" in data
    assert data["entry_id"] == entry_id


def test_pipeline_validate_tool():
    """Verify pipeline_validate returns JSON result."""
    entry_id = _first_entry_id()
    result = pipeline_validate(entry_id)
    data = json.loads(result)
    assert "status" in data
    assert "entry_id" in data
    assert "is_valid" in data


def test_pipeline_score_all_tool():
    """Verify batch scoring mode returns a batch result."""
    result = pipeline_score(all_entries=True)
    data = json.loads(result)
    assert data["entry_id"] == "batch"
    assert data["status"] in {"dry_run", "success"}
