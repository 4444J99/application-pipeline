#!/usr/bin/env python3
"""Unified Typer CLI for the application pipeline."""

import typer
import sys
from pathlib import Path

# Ensure the scripts directory is in the path
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Import the main functions from the existing scripts
from standup import run_standup, run_triage, touch_entry
from pipeline_status import print_summary, print_upcoming, load_entries, ALL_PIPELINE_DIRS_WITH_POOL
from score import main as score_main
from advance import main as advance_main
from draft import main as draft_main
from pipeline_status import main as status_main
from compose import main as compose_main
from alchemize import main as alchemize_main
from check_outcomes import main as outcomes_main
from hygiene import main as hygiene_main
from campaign import main as campaign_main
from followup import main as followup_main
from validate import main as validate_main
from outcome_learner import main as learner_main

app = typer.Typer(help="Application Pipeline CLI", no_args_is_help=True)

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
def touch(entry_id: str):
    """Mark an entry as reviewed today (sets last_touched)."""
    touch_entry(entry_id)

@app.command()
def status(
    upcoming: int = typer.Option(30, help="Show deadlines within next N days"),
    all: bool = typer.Option(False, help="Show all entries including rolling"),
    benefits_check: bool = typer.Option(False, help="Show benefits cliff analysis"),
    top: int = typer.Option(None, help="Show top N actionable entries")
):
    """Full pipeline status overview."""
    args = []
    if upcoming != 30:
        args.extend(["--upcoming", str(upcoming)])
    if all:
        args.append("--all")
    if benefits_check:
        args.append("--benefits-check")
    if top:
        args.extend(["--top", str(top)])
        
    old_argv = sys.argv
    sys.argv = ["pipeline_status.py"] + args
    try:
        status_main()
    except SystemExit:
        pass
    finally:
        sys.argv = old_argv

@app.command()
def compose_doc(
    target: str = typer.Argument(..., help="Target ID"),
    output: str = typer.Option(None, "-o", help="Output file"),
    plain: bool = typer.Option(False, help="Output plain text"),
    counts: bool = typer.Option(False, help="Show per-section counts"),
    max_words: int = typer.Option(0, help="Warn if document exceeds N words"),
    word_count: bool = typer.Option(False, help="Report word count only"),
    snapshot: bool = typer.Option(False, help="Save composed output to pipeline/submissions/"),
    profile: bool = typer.Option(False, help="Fall back to profile content"),
    ai_smooth: bool = typer.Option(False, help="Use LLM to smooth the concatenated blocks")
):
    """Compose submission from blocks."""
    args = ["--target", target]
    if output: args.extend(["-o", output])
    if plain: args.append("--plain")
    if counts: args.append("--counts")
    if max_words: args.extend(["--max-words", str(max_words)])
    if word_count: args.append("--word-count")
    if snapshot: args.append("--snapshot")
    if profile: args.append("--profile")
    if ai_smooth: args.append("--ai-smooth")
    
    old_argv = sys.argv
    sys.argv = ["compose.py"] + args
    try:
        compose_main()
    except SystemExit:
        pass
    finally:
        sys.argv = old_argv

@app.command()
def score(
    target: str = typer.Argument(None, help="Target ID to score"),
    all: bool = typer.Option(False, "--all", help="Score all entries"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview only"),
    auto_qualify: bool = typer.Option(False, "--auto-qualify", help="Auto-promote top entries")
):
    """Score entries based on the 8-dimension weighted rubric."""
    args = []
    if all: args.append("--all")
    if dry_run: args.append("--dry-run")
    if auto_qualify: args.append("--auto-qualify")
    if target: args.extend(["--target", target])
    
    old_argv = sys.argv
    sys.argv = ["score.py"] + args
    try:
        score_main()
    except SystemExit:
        pass
    finally:
        sys.argv = old_argv

@app.command()
def advance(
    target: str = typer.Argument(..., help="Target ID"),
    to: str = typer.Option(None, "--to", help="Specific status to advance to"),
    yes: bool = typer.Option(False, "-y", "--yes", help="Skip confirmation")
):
    """Advance an entry to the next status in the state machine."""
    args = ["--id", target]
    if to: args.extend(["--to", to])
    if yes: args.append("--yes")
    
    old_argv = sys.argv
    sys.argv = ["advance.py"] + args
    try:
        advance_main()
    except SystemExit:
        pass
    finally:
        sys.argv = old_argv

@app.command()
def draft(
    target: str = typer.Argument(..., help="Target ID"),
    force: bool = typer.Option(False, "--force", help="Overwrite existing drafts")
):
    """Draft application materials from target profiles."""
    args = ["--target", target]
    if force: args.append("--force")
    
    old_argv = sys.argv
    sys.argv = ["draft.py"] + args
    try:
        draft_main()
    except SystemExit:
        pass
    finally:
        sys.argv = old_argv

@app.command()
def alchemize(
    target: str = typer.Argument(None, help="Target ID"),
    batch: bool = typer.Option(False, help="Process all Greenhouse entries"),
    integrate: bool = typer.Option(False, help="Integrate output.md back into pipeline"),
    submit: bool = typer.Option(False, help="Execute portal submission")
):
    """Full-pipeline orchestrator: intake → research → map → synthesize."""
    args = []
    if target: args.extend(["--target", target])
    if batch: args.append("--batch")
    if integrate: args.append("--integrate")
    if submit: args.append("--submit")
    
    old_argv = sys.argv
    sys.argv = ["alchemize.py"] + args
    try:
        alchemize_main()
    except SystemExit:
        pass
    finally:
        sys.argv = old_argv

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
    if target: args.extend(["--target", target])
    if outcome: args.extend(["--outcome", outcome])
    if record: args.append("--record")
    
    old_argv = sys.argv
    sys.argv = ["check_outcomes.py"] + args
    try:
        outcomes_main()
    except SystemExit:
        pass
    finally:
        sys.argv = old_argv

@app.command()
def learn(save: bool = typer.Option(False, help="Save calibration weights")):
    """Outcome learning engine: calibrate weights from conversion data."""
    args = []
    if save: args.append("--save")
    
    old_argv = sys.argv
    sys.argv = ["outcome_learner.py"] + args
    try:
        learner_main()
    except SystemExit:
        pass
    finally:
        sys.argv = old_argv

@app.command()
def validate():
    """Pipeline YAML schema validation."""
    old_argv = sys.argv
    sys.argv = ["validate.py"]
    try:
        validate_main()
    except SystemExit:
        pass
    finally:
        sys.argv = old_argv

@app.command()
def hygiene(focus: bool = typer.Option(False, "--focus", help="Check company focus Rule of Three")):
    """Entry data quality report and gate checks."""
    args = []
    if focus: args.append("--company-focus")
    
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
