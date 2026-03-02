#!/usr/bin/env python3
"""MCP Server for the application pipeline.

Exposes core functions (score, advance, draft, validate) as MCP tools
using the clean API layer. No sys.argv manipulation or stdout redirection.

Enables agentic execution of the pipeline state machine without tight
coupling to script internals.
"""

from mcp.server.fastmcp import FastMCP
import sys
import json
from pathlib import Path

# Add scripts dir to path so we can import local modules
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_api import (
    score_entry,
    advance_entry,
    draft_entry,
    compose_entry,
    validate_entry,
    ResultStatus,
)

# Initialize FastMCP server
mcp = FastMCP("application-pipeline")


@mcp.tool()
def pipeline_score(target_id: str, auto_qualify: bool = False) -> str:
    """Score a single entry or auto-qualify batch.
    
    Args:
        target_id: Entry ID to score
        auto_qualify: If true, batch-advance research entries >= 7.0
        
    Returns:
        JSON result with status, entry_id, scores, and optional error
    """
    result = score_entry(target_id=target_id, auto_qualify=auto_qualify, dry_run=True)
    
    return json.dumps({
        "status": result.status.value,
        "entry_id": result.entry_id,
        "old_score": result.old_score,
        "new_score": result.new_score,
        "message": result.message,
        "error": result.error,
    }, default=str)


@mcp.tool()
def pipeline_advance(target_id: str, to_status: str = None) -> str:
    """Advance an entry to the next status in the pipeline.
    
    Args:
        target_id: Entry ID to advance
        to_status: Target status (optional)
        
    Returns:
        JSON result with status transition and optional error
    """
    result = advance_entry(entry_id=target_id, to_status=to_status, dry_run=True)
    
    return json.dumps({
        "status": result.status.value,
        "entry_id": result.entry_id,
        "old_status": result.old_status,
        "new_status": result.new_status,
        "message": result.message,
        "error": result.error,
    }, default=str)


@mcp.tool()
def pipeline_draft(target_id: str) -> str:
    """Draft application materials from profile content.
    
    Args:
        target_id: Entry ID to draft
        
    Returns:
        JSON result with drafted content and optional file path
    """
    result = draft_entry(entry_id=target_id, dry_run=True)
    
    return json.dumps({
        "status": result.status.value,
        "entry_id": result.entry_id,
        "content": result.content[:500] if result.content else None,  # First 500 chars
        "file_path": result.file_path,
        "message": result.message,
        "error": result.error,
    }, default=str)


@mcp.tool()
def pipeline_compose(target_id: str) -> str:
    """Compose submission from blocks.
    
    Args:
        target_id: Entry ID to compose
        
    Returns:
        JSON result with composed content and metadata
    """
    result = compose_entry(entry_id=target_id, dry_run=True)
    
    return json.dumps({
        "status": result.status.value,
        "entry_id": result.entry_id,
        "content": result.content[:500] if result.content else None,  # First 500 chars
        "word_count": result.word_count,
        "block_sources": result.block_sources,
        "message": result.message,
        "error": result.error,
    }, default=str)


@mcp.tool()
def pipeline_validate(target_id: str = None) -> str:
    """Validate pipeline YAML or specific entry.
    
    Args:
        target_id: Entry ID to validate (optional; validates all if not given)
        
    Returns:
        JSON result with validation status, errors, and warnings
    """
    result = validate_entry(entry_id=target_id)
    
    return json.dumps({
        "status": result.status.value,
        "entry_id": result.entry_id,
        "is_valid": result.is_valid,
        "errors": result.errors,
        "warnings": result.warnings,
        "message": result.message,
    }, default=str)

if __name__ == "__main__":
    # Start the MCP server using stdio transport
    mcp.run()
