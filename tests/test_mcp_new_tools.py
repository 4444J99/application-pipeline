"""Tests for newly added MCP server tools."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from mcp_server import (
    mcp,
    pipeline_enrich,
    pipeline_followup,
    pipeline_hygiene,
    pipeline_phase_analytics,
    pipeline_rate,
    pipeline_standards,
)


def test_mcp_tool_count_is_sixteen():
    tools = mcp._tool_manager._tools
    assert len(tools) >= 16


def test_pipeline_followup_returns_json():
    result = pipeline_followup()
    data = json.loads(result)
    assert "status" in data
    assert "entry_id" in data


def test_pipeline_enrich_requires_args():
    result = pipeline_enrich()
    data = json.loads(result)
    assert data["status"] == "error"
    assert "required" in data["error"]


def test_pipeline_hygiene_returns_json():
    result = pipeline_hygiene()
    data = json.loads(result)
    assert "status" in data
    assert "total_issues" in data


def test_pipeline_standards_returns_json():
    result = pipeline_standards()
    data = json.loads(result)
    assert "passed" in data
    assert "level_reports" in data


def test_pipeline_phase_analytics_returns_json():
    result = pipeline_phase_analytics()
    data = json.loads(result)
    assert "phase_1" in data
    assert "phase_2" in data


def test_pipeline_rate_dry_run():
    """Verify pipeline_rate returns JSON in dry_run mode."""
    result = pipeline_rate(dry_run=True)
    data = json.loads(result)
    assert data["status"] == "dry_run"
    assert "raters" in data
    assert len(data["raters"]) >= 4
