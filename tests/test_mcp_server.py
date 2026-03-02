import pytest
import json
import sys
import os
from pathlib import Path

# Ensure scripts dir is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../scripts')))

from mcp_server import pipeline_score, pipeline_advance, pipeline_draft, pipeline_compose, pipeline_validate


def test_pipeline_score_tool():
    """Verify pipeline_score returns JSON result."""
    result = pipeline_score("test-entry")
    data = json.loads(result)
    assert "status" in data
    assert "entry_id" in data
    assert data["entry_id"] == "test-entry"


def test_pipeline_advance_tool():
    """Verify pipeline_advance returns JSON result."""
    result = pipeline_advance("test-entry", to_status="staged")
    data = json.loads(result)
    assert "status" in data
    assert "entry_id" in data
    assert data["entry_id"] == "test-entry"


def test_pipeline_draft_tool():
    """Verify pipeline_draft returns JSON result."""
    result = pipeline_draft("test-entry")
    data = json.loads(result)
    assert "status" in data
    assert "entry_id" in data
    assert data["entry_id"] == "test-entry"


def test_pipeline_compose_tool():
    """Verify pipeline_compose returns JSON result."""
    result = pipeline_compose("test-entry")
    data = json.loads(result)
    assert "status" in data
    assert "entry_id" in data
    assert data["entry_id"] == "test-entry"


def test_pipeline_validate_tool():
    """Verify pipeline_validate returns JSON result."""
    result = pipeline_validate("test-entry")
    data = json.loads(result)
    assert "status" in data
    assert "entry_id" in data
    assert "is_valid" in data

