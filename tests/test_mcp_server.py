import pytest
import sys
import os
from pathlib import Path

# Ensure scripts dir is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../scripts')))

from mcp_server import pipeline_score, pipeline_advance, pipeline_draft, pipeline_status

def test_pipeline_score_tool(mocker):
    """Verify pipeline_score tool intercepts output and calls score_main."""
    mock_main = mocker.patch("mcp_server.score_main")
    def side_effect():
        print("Score output")
    mock_main.side_effect = side_effect
    
    result = pipeline_score("test-target", auto_qualify=True)
    assert "Score output" in result
    mock_main.assert_called_once()

def test_pipeline_advance_tool(mocker):
    """Verify pipeline_advance tool intercepts output and calls advance_main."""
    mock_main = mocker.patch("mcp_server.advance_main")
    def side_effect():
        print("Advance output")
    mock_main.side_effect = side_effect
    
    result = pipeline_advance("test-target", to_status="staged")
    assert "Advance output" in result
    mock_main.assert_called_once()

def test_pipeline_draft_tool(mocker):
    """Verify pipeline_draft tool intercepts output and calls draft_main."""
    mock_main = mocker.patch("mcp_server.draft_main")
    def side_effect():
        print("Draft output")
    mock_main.side_effect = side_effect
    
    result = pipeline_draft("test-target")
    assert "Draft output" in result
    mock_main.assert_called_once()

def test_pipeline_status_tool(mocker):
    """Verify pipeline_status tool calls print_summary and print_upcoming."""
    mock_summary = mocker.patch("mcp_server.print_summary")
    mock_upcoming = mocker.patch("mcp_server.print_upcoming")
    mock_load = mocker.patch("pipeline_lib.load_entries")
    mock_load.return_value = [{"id": "test"}]
    
    pipeline_status(upcoming_days=14)
    mock_summary.assert_called_once_with([{"id": "test"}])
    mock_upcoming.assert_called_once_with([{"id": "test"}], 14)
