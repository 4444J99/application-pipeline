#!/usr/bin/env python3
"""MCP Server for the application pipeline.

Exposes core functions (score, advance, draft, status) as MCP tools,
enabling agentic execution of the pipeline state machine.
"""

from mcp.server.fastmcp import FastMCP
import sys
from pathlib import Path

# Add scripts dir to path so we can import local modules
sys.path.insert(0, str(Path(__file__).resolve().parent))

from score import main as score_main
from advance import main as advance_main
from draft import main as draft_main
from pipeline_status import print_summary, print_upcoming

# Initialize FastMCP server
mcp = FastMCP("application-pipeline")

@mcp.tool()
def pipeline_score(target_id: str, auto_qualify: bool = False) -> str:
    """Score a single entry or all entries in the pipeline."""
    # We intercept stdout to return it as a string
    import io
    from contextlib import redirect_stdout
    
    f = io.StringIO()
    with redirect_stdout(f):
        args = ["--target", target_id]
        if auto_qualify:
            args.append("--auto-qualify")
            
        old_argv = sys.argv
        sys.argv = ["score.py"] + args
        try:
            score_main()
        except SystemExit:
            pass
        finally:
            sys.argv = old_argv
            
    return f.getvalue()

@mcp.tool()
def pipeline_advance(target_id: str, to_status: str = None) -> str:
    """Advance an entry to the next status in the pipeline."""
    import io
    from contextlib import redirect_stdout
    
    f = io.StringIO()
    with redirect_stdout(f):
        args = ["--id", target_id]
        if to_status:
            args.extend(["--to", to_status])
            
        old_argv = sys.argv
        sys.argv = ["advance.py"] + args
        try:
            advance_main()
        except SystemExit:
            pass
        finally:
            sys.argv = old_argv
            
    return f.getvalue()

@mcp.tool()
def pipeline_draft(target_id: str) -> str:
    """Draft application materials from profile content."""
    import io
    from contextlib import redirect_stdout
    
    f = io.StringIO()
    with redirect_stdout(f):
        args = ["--target", target_id]
            
        old_argv = sys.argv
        sys.argv = ["draft.py"] + args
        try:
            draft_main()
        except SystemExit:
            pass
        finally:
            sys.argv = old_argv
            
    return f.getvalue()

@mcp.tool()
def pipeline_status(upcoming_days: int = 7) -> str:
    """Get the full pipeline status overview."""
    import io
    from contextlib import redirect_stdout
    
    f = io.StringIO()
    with redirect_stdout(f):
        from pipeline_lib import load_entries
        entries = load_entries()
        print_summary(entries)
        print_upcoming(entries, upcoming_days)
            
    return f.getvalue()

if __name__ == "__main__":
    # Start the MCP server using stdio transport
    mcp.run()
