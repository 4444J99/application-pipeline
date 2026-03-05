#!/usr/bin/env python3
"""MCP Server for the application pipeline.

Exposes core functions (score, advance, draft, validate) as MCP tools
using the clean API layer. No sys.argv manipulation or stdout redirection.

Enables agentic execution of the pipeline state machine without tight
coupling to script internals.
"""

import json

from mcp.server.fastmcp import FastMCP

try:  # Prefer package-style imports when available.
    from .pipeline_api import (
        advance_entry,
        compose_entry,
        draft_entry,
        score_entry,
        validate_entry,
    )
except ImportError:  # pragma: no cover - script execution fallback
    from pipeline_api import (
        advance_entry,
        compose_entry,
        draft_entry,
        score_entry,
        validate_entry,
    )

# Initialize FastMCP server
mcp = FastMCP("application-pipeline")


@mcp.tool()
def pipeline_score(
    entry_id: str | None = None,
    auto_qualify: bool = False,
    all_entries: bool = False,
) -> str:
    """Score a single entry or auto-qualify batch.
    
    Args:
        entry_id: Entry ID to score
        auto_qualify: If true, batch-advance research entries >= 7.0
        
    Returns:
        JSON result with status, entry_id, scores, and optional error
    """
    result = score_entry(
        entry_id=entry_id,
        auto_qualify=auto_qualify,
        all_entries=all_entries,
        dry_run=True,
    )
    
    return json.dumps({
        "status": result.status.value,
        "entry_id": result.entry_id,
        "old_score": result.old_score,
        "new_score": result.new_score,
        "message": result.message,
        "error": result.error,
    }, default=str)


@mcp.tool()
def pipeline_advance(target_id: str, to_status: str | None = None) -> str:
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

@mcp.tool()
def pipeline_funnel() -> str:
    """Get conversion funnel analytics as JSON.

    Returns:
        JSON with portal, position, and track conversion stats
    """
    try:
        from conversion_dashboard import generate_dashboard_data
        from pipeline_lib import ALL_PIPELINE_DIRS, load_entries
        entries = load_entries(dirs=ALL_PIPELINE_DIRS, include_filepath=True)
        data = generate_dashboard_data(entries)
        return json.dumps(data, default=str)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


@mcp.tool()
def pipeline_snapshot() -> str:
    """Capture current pipeline snapshot with counts, scores, and violations.

    Returns:
        JSON snapshot of current pipeline state
    """
    try:
        from snapshot import capture_snapshot
        data = capture_snapshot()
        return json.dumps(data, default=str)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


@mcp.tool()
def pipeline_triage(min_score: float = 9.0, dry_run: bool = True) -> str:
    """Triage staged entries below threshold and org-cap violations.

    Args:
        min_score: Minimum score for staged entries (default: 9.0)
        dry_run: If true, preview only (default: true)

    Returns:
        JSON with staged_demotions, org_cap_deferrals, and summary
    """
    try:
        from pipeline_lib import load_entries
        from triage import generate_triage_data
        entries = load_entries()
        data = generate_triage_data(entries, min_score=min_score, dry_run=dry_run)
        return json.dumps(data, default=str)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


@mcp.tool()
def pipeline_crm_dashboard() -> str:
    """Get CRM dashboard data: contacts, orgs, overdue actions.

    Returns:
        JSON with contact stats, org coverage, and overdue items
    """
    try:
        from crm import generate_crm_data, load_contacts
        contacts = load_contacts()
        data = generate_crm_data(contacts)
        return json.dumps(data, default=str)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


@mcp.tool()
def pipeline_campaign(days: int = 14) -> str:
    """Get deadline-aware campaign data with urgency tiers.

    Args:
        days: Look-ahead window in days (default: 14)

    Returns:
        JSON with urgency tiers and entry details
    """
    try:
        from campaign import generate_campaign_data
        from pipeline_lib import load_entries
        entries = load_entries(include_filepath=True)
        data = generate_campaign_data(entries, days)
        return json.dumps(data, default=str)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


if __name__ == "__main__":
    # Start the MCP server using stdio transport
    mcp.run()
