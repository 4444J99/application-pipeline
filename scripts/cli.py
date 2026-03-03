#!/usr/bin/env python3
"""Unified Typer CLI for the application pipeline.

This CLI layer uses the pipeline_api module for all core operations.
No sys.argv manipulation or stdout redirection—clean function calls only.

For operations not yet migrated to the API layer, we fall back to
direct script imports (backward-compatible).
"""

import sys
from pathlib import Path

import typer

# Ensure the scripts directory is in the path
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Import clean API layer (new way)
from campaign import main as campaign_main
from check_outcomes import main as outcomes_main
from hygiene import main as hygiene_main
from pipeline_api import (
    ResultStatus,
    advance_entry,
    compose_entry,
    draft_entry,
    score_entry,
    validate_entry,
)

# Import functions not yet migrated to API layer (backward-compatible)
from standup import run_standup, run_triage, touch_entry

app = typer.Typer(help="Application Pipeline CLI", no_args_is_help=True)


# ============================================================================
# COMMANDS USING CLEAN API LAYER
# ============================================================================

@app.command()
def score(
    target: str = typer.Argument(None, help="Target ID to score"),
    all: bool = typer.Option(False, "--all", help="Score all entries"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview only"),
    auto_qualify: bool = typer.Option(False, "--auto-qualify", help="Auto-promote top entries"),
    min_score: float = typer.Option(7.0, "--min-score", help="Min score for auto-qualify"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Show dimension breakdowns"),
):
    """Score entries based on the 8-dimension weighted rubric."""
    if not target and not all and not auto_qualify:
        typer.echo("Specify --target, --all, or --auto-qualify")
        raise typer.Exit(1)
    
    result = score_entry(
        entry_id=target,
        auto_qualify=auto_qualify,
        dry_run=dry_run,
        min_score=min_score,
        verbose=verbose,
    )
    
    if result.status == ResultStatus.ERROR:
        typer.echo(f"Error: {result.error}", err=True)
        raise typer.Exit(1)
    
    typer.echo(f"{result.entry_id}: {result.message}")
    if result.new_score:
        typer.echo(f"  Score: {result.new_score}")


@app.command()
def advance(
    target: str = typer.Argument(..., help="Target ID"),
    to: str = typer.Option(None, "--to", help="Specific status to advance to"),
    yes: bool = typer.Option(False, "-y", "--yes", help="Skip confirmation"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview only"),
):
    """Advance an entry to the next status in the state machine."""
    result = advance_entry(
        entry_id=target,
        to_status=to,
        dry_run=dry_run,
    )
    
    if result.status == ResultStatus.ERROR:
        typer.echo(f"Error: {result.error}", err=True)
        raise typer.Exit(1)
    
    typer.echo(f"{result.entry_id}: {result.message}")
    if result.new_status:
        typer.echo(f"  {result.old_status} → {result.new_status}")


@app.command()
def draft(
    target: str = typer.Argument(..., help="Target ID"),
    force: bool = typer.Option(False, "--force", help="Overwrite existing drafts"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview only"),
):
    """Draft application materials from target profiles."""
    result = draft_entry(
        entry_id=target,
        dry_run=dry_run,
    )
    
    if result.status == ResultStatus.ERROR:
        typer.echo(f"Error: {result.error}", err=True)
        raise typer.Exit(1)
    
    typer.echo(f"{result.entry_id}: {result.message}")
    if result.file_path:
        typer.echo(f"  Output: {result.file_path}")


@app.command()
def compose(
    target: str = typer.Argument(..., help="Target ID"),
    snapshot: bool = typer.Option(False, help="Save to pipeline/submissions/"),
    profile: bool = typer.Option(False, help="Fall back to profile content"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview only"),
):
    """Compose submission from blocks."""
    result = compose_entry(
        entry_id=target,
        snapshot=snapshot,
        profile=profile,
        dry_run=dry_run,
    )
    
    if result.status == ResultStatus.ERROR:
        typer.echo(f"Error: {result.error}", err=True)
        raise typer.Exit(1)
    
    typer.echo(f"{result.entry_id}: {result.message}")
    if result.word_count:
        typer.echo(f"  Words: {result.word_count}")
    if result.file_path:
        typer.echo(f"  Output: {result.file_path}")


@app.command()
def validate(target: str = typer.Argument(None, help="Target ID (optional)")):
    """Validate pipeline YAML schema."""
    result = validate_entry(entry_id=target)
    
    if result.status == ResultStatus.ERROR:
        typer.echo(f"Error: {result.error}", err=True)
        for err in result.errors:
            typer.echo(f"  - {err}", err=True)
        raise typer.Exit(1)
    
    typer.echo(f"{result.entry_id}: validation passed")
    if result.warnings:
        for warn in result.warnings:
            typer.echo(f"  ⚠️  {warn}")


# ============================================================================
# COMMANDS STILL USING SCRIPT MAIN() FUNCTIONS (BACKWARD-COMPATIBLE)
# ============================================================================

@app.command()
def standup(
    hours: float = typer.Option(3.0, help="Available hours for today's session"),
    section: str = typer.Option(None, help="Run a single section only"),
    log: bool = typer.Option(False, help="Append session record to standup-log.yaml"),
    jobs: bool = typer.Option(False, help="Show job pipeline status only"),
    opportunities: bool = typer.Option(False, help="Show opportunity pipeline only"),
    triage: bool = typer.Option(False, help="Enter interactive triage mode")
):
    """Daily dashboard: stale entries, deadlines, priorities, follow-ups."""
    if triage:
        run_triage()
        return
        
    track_filter = None
    if jobs:
        track_filter = "jobs"
    elif opportunities:
        track_filter = "opportunities"
    
    run_standup(hours, section, log, track_filter=track_filter)


@app.command()
def touch(entry_id: str = typer.Argument(..., help="Entry ID to mark as reviewed")):
    """Mark an entry as reviewed today (sets last_touched)."""
    touch_entry(entry_id)


@app.command()
def campaign():
    """Deadline-aware campaign view with urgency tiers."""
    old_argv = sys.argv
    sys.argv = ["campaign.py"]
    try:
        campaign_main()
    except SystemExit:
        pass
    finally:
        sys.argv = old_argv


@app.command()
def outcomes(
    target: str = typer.Option(None, "--target", help="Target ID"),
    outcome: str = typer.Option(None, "--outcome", help="Outcome result"),
    record: bool = typer.Option(False, "--record", help="Record an outcome")
):
    """Entries awaiting response + record outcomes."""
    args = []
    if target:
        args.extend(["--target", target])
    if outcome:
        args.extend(["--outcome", outcome])
    if record:
        args.append("--record")
    
    old_argv = sys.argv
    sys.argv = ["check_outcomes.py"] + args
    try:
        outcomes_main()
    except SystemExit:
        pass
    finally:
        sys.argv = old_argv


@app.command()
def hygiene(focus: bool = typer.Option(False, "--focus", help="Check company focus Rule of Three")):
    """Entry data quality report and gate checks."""
    args = []
    if focus:
        args.append("--company-focus")
    
    old_argv = sys.argv
    sys.argv = ["hygiene.py"] + args
    try:
        hygiene_main()
    except SystemExit:
        pass
    finally:
        sys.argv = old_argv


if __name__ == "__main__":
    app()
