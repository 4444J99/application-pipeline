#!/usr/bin/env python3
"""Unified Typer CLI for the application pipeline.

This CLI layer uses the pipeline_api module for core operations (score, advance,
draft, compose, validate, enrich, followup, hygiene, submit, triage).

For operations not yet migrated to the API layer, we fall back to
direct script imports with sys.argv manipulation (backward-compatible).
"""

import sys

import typer

try:  # Prefer package-style imports when available.
    from .check_outcomes import main as outcomes_main
    from .pipeline_api import (
        ResultStatus,
        advance_entry,
        compose_entry,
        draft_entry,
        enrich_entry,
        followup_data,
        hygiene_check,
        score_entry,
        submit_entry,
        triage_data,
        validate_entry,
    )
    from .standup import run_standup, run_triage, touch_entry
except ImportError:  # pragma: no cover - script execution fallback
    from check_outcomes import main as outcomes_main
    from pipeline_api import (
        ResultStatus,
        advance_entry,
        compose_entry,
        draft_entry,
        enrich_entry,
        followup_data,
        hygiene_check,
        score_entry,
        submit_entry,
        triage_data,
        validate_entry,
    )
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
        all_entries=all,
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
        if result.error:
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
def campaign(
    days: int = typer.Option(14, help="Look-ahead window in days"),
):
    """Deadline-aware campaign view with urgency tiers."""
    try:
        from campaign import generate_campaign_markdown
        from pipeline_lib import load_entries
    except ImportError:
        from scripts.campaign import generate_campaign_markdown
        from scripts.pipeline_lib import load_entries
    entries = load_entries(include_filepath=True)
    output = generate_campaign_markdown(entries, days)
    typer.echo(output)


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
def hygiene(
    target: str = typer.Argument(None, help="Target ID (optional)"),
):
    """Entry data quality report and gate checks."""
    result = hygiene_check(entry_id=target)

    if result.status == ResultStatus.ERROR:
        typer.echo(f"Error: {result.error}", err=True)
        raise typer.Exit(1)

    typer.echo(f"{result.entry_id}: {result.message}")
    if result.gate_issues:
        for issue in result.gate_issues[:20]:
            typer.echo(f"  - {issue}")
        if len(result.gate_issues) > 20:
            typer.echo(f"  ... and {len(result.gate_issues) - 20} more")


# ============================================================================
# NEW COMMANDS USING EXPANDED API LAYER
# ============================================================================

@app.command()
def followup(
    target: str = typer.Argument(None, help="Target ID (optional)"),
):
    """Today's follow-up actions and overdue items."""
    result = followup_data(entry_id=target)

    if result.status == ResultStatus.ERROR:
        typer.echo(f"Error: {result.error}", err=True)
        raise typer.Exit(1)

    typer.echo(f"{result.entry_id}: {result.message}")
    if result.due_actions:
        for action in result.due_actions:
            typer.echo(f"  [{action.get('tier', '?')}] {action['entry_id']} — {action.get('action', '?')}")


@app.command()
def enrich(
    target: str = typer.Argument(None, help="Target ID (optional)"),
    all: bool = typer.Option(False, "--all", help="Analyze all entries"),
):
    """Show enrichment gaps for entries."""
    if not target and not all:
        typer.echo("Specify target or --all")
        raise typer.Exit(1)

    result = enrich_entry(entry_id=target, all_entries=all)

    if result.status == ResultStatus.ERROR:
        typer.echo(f"Error: {result.error}", err=True)
        raise typer.Exit(1)

    typer.echo(f"{result.entry_id}: {result.message}")
    if result.gaps:
        for gap in result.gaps:
            typer.echo(f"  - {gap}")


@app.command()
def submit(
    target: str = typer.Argument(..., help="Target ID"),
    dry_run: bool = typer.Option(True, "--dry-run/--no-dry-run", help="Preview only"),
):
    """Generate submission checklist for an entry."""
    result = submit_entry(entry_id=target, dry_run=dry_run)

    if result.status == ResultStatus.ERROR:
        typer.echo(f"Error: {result.error}", err=True)
        raise typer.Exit(1)

    typer.echo(f"{result.entry_id}: {result.message}")
    if result.checklist:
        typer.echo(result.checklist)
    if result.issues:
        for issue in result.issues:
            typer.echo(f"  ⚠ {issue}", err=True)


@app.command()
def triage(
    min_score: float = typer.Option(9.0, "--min-score", help="Minimum score threshold"),
    dry_run: bool = typer.Option(True, "--dry-run/--no-dry-run", help="Preview only"),
):
    """Triage staged entries below threshold and org-cap violations."""
    result = triage_data(min_score=min_score, dry_run=dry_run)

    if result.status == ResultStatus.ERROR:
        typer.echo(f"Error: {result.error}", err=True)
        raise typer.Exit(1)

    typer.echo(f"Triage: {result.message}")
    if result.staged_demotions:
        for d in result.staged_demotions:
            typer.echo(f"  demote: {d['id']} (score {d['score']:.1f})")
    if result.org_cap_deferrals:
        for d in result.org_cap_deferrals:
            typer.echo(f"  defer: {d['id']} ({d['org']})")


# ============================================================================
# COMMANDS USING DIRECT SCRIPT IMPORTS (no API wrapper needed)
# ============================================================================

@app.command()
def morning():
    """Morning digest: health + stale + followups + campaign."""
    try:
        from morning import run_morning
    except ImportError:
        from scripts.morning import run_morning
    run_morning(brief=False, save=False)


@app.command()
def deferred():
    """Deferred entries: overdue and upcoming re-activations."""
    try:
        from check_deferred import run_check_deferred
    except ImportError:
        from scripts.check_deferred import run_check_deferred
    run_check_deferred(report_mode=True)


@app.command()
def funnel():
    """Conversion funnel analytics."""
    try:
        from funnel_report import main as funnel_main
    except ImportError:
        from scripts.funnel_report import main as funnel_main
    old_argv = sys.argv
    sys.argv = ["funnel_report.py"]
    try:
        funnel_main()
    except SystemExit:
        pass
    finally:
        sys.argv = old_argv


@app.command()
def snapshot():
    """Pipeline snapshot with counts and trends."""
    try:
        from snapshot import main as snapshot_main
    except ImportError:
        from scripts.snapshot import main as snapshot_main
    old_argv = sys.argv
    sys.argv = ["snapshot.py", "--report"]
    try:
        snapshot_main()
    except SystemExit:
        pass
    finally:
        sys.argv = old_argv


@app.command()
def metrics():
    """Block metric consistency check."""
    try:
        from check_metrics import main as metrics_main
    except ImportError:
        from scripts.check_metrics import main as metrics_main
    old_argv = sys.argv
    sys.argv = ["check_metrics.py"]
    try:
        metrics_main()
    except SystemExit:
        pass
    finally:
        sys.argv = old_argv


@app.command()
def diagnose(
    subjective_only: bool = typer.Option(False, "--subjective-only", help="Generate prompts for AI raters"),
    objective_only: bool = typer.Option(False, "--objective-only", help="Only automated measurements"),
):
    """System diagnostic scorecard."""
    try:
        from diagnose import main as diagnose_main
    except ImportError:
        from scripts.diagnose import main as diagnose_main
    args = ["diagnose.py"]
    if subjective_only:
        args.append("--subjective-only")
    if objective_only:
        args.append("--objective-only")
    old_argv = sys.argv
    sys.argv = args
    try:
        diagnose_main()
    except SystemExit:
        pass
    finally:
        sys.argv = old_argv


@app.command()
def audit(
    claims: bool = typer.Option(False, "--claims", help="Claims provenance only"),
    wiring: bool = typer.Option(False, "--wiring", help="Wiring integrity only"),
    logic: bool = typer.Option(False, "--logic", help="Logical consistency only"),
    external: bool = typer.Option(False, "--external", help="External validation only"),
    as_json: bool = typer.Option(False, "--json", help="Machine-readable JSON output"),
):
    """System integrity audit: claims, wiring, logic, external validation."""
    if external:
        try:
            from audit_system import audit_external
        except ImportError:
            from scripts.audit_system import audit_external
        import json as _json

        result = audit_external()
        if as_json:
            typer.echo(_json.dumps(result, indent=2, default=str))
        elif result.get("status") == "no_cache":
            typer.echo("No validation cache. Run: python scripts/external_validator.py --fetch-only")
        else:
            from external_validator import format_report as ext_format
            typer.echo(ext_format(result))
        return

    try:
        from audit_system import main as audit_main
    except ImportError:
        from scripts.audit_system import main as audit_main
    args = ["audit_system.py"]
    if claims:
        args.append("--claims")
    if wiring:
        args.append("--wiring")
    if logic:
        args.append("--logic")
    if as_json:
        args.append("--json")
    old_argv = sys.argv
    sys.argv = args
    try:
        audit_main()
    except SystemExit:
        pass
    finally:
        sys.argv = old_argv


@app.command()
def standards(
    level: int = typer.Option(None, "--level", help="Run a single level (1-5)"),
    json_output: bool = typer.Option(False, "--json", help="Machine-readable JSON"),
    run_all: bool = typer.Option(False, "--run-all", help="Run all levels, no cascade stop"),
):
    """Standards Board: 5-level hierarchical validation audit."""
    try:
        from standards import BoardReport, StandardsBoard, format_report
    except ImportError:
        from scripts.standards import BoardReport, StandardsBoard, format_report
    import json as _json

    board = StandardsBoard()
    if level:
        lr = board.check_level(level)
        br = BoardReport(level_reports=[lr])
    else:
        br = board.full_audit(gated=not run_all)

    if json_output:
        typer.echo(_json.dumps(br.to_dict(), indent=2))
    else:
        typer.echo(format_report(br))
    raise typer.Exit(0 if br.passed else 1)


@app.command()
def ingest(
    write: bool = typer.Option(False, "--write", help="Write historical-outcomes.yaml"),
    stats: bool = typer.Option(False, "--stats", help="Summary statistics only"),
    json_output: bool = typer.Option(False, "--json", help="JSON output"),
):
    """Ingest historical application data from CSV exports."""
    try:
        from ingest_historical import main as ingest_main
    except ImportError:
        from scripts.ingest_historical import main as ingest_main
    args = ["ingest_historical.py"]
    if write:
        args.append("--write")
    if stats:
        args.append("--stats")
    if json_output:
        args.append("--json")
    old_argv = sys.argv
    sys.argv = args
    try:
        ingest_main()
    except SystemExit:
        pass
    finally:
        sys.argv = old_argv


@app.command()
def phases(
    velocity: bool = typer.Option(False, "--velocity", help="Monthly velocity only"),
    json_output: bool = typer.Option(False, "--json", help="JSON output"),
):
    """Phase 1 vs Phase 2 application analytics."""
    try:
        from phase_analytics import main as phase_main
    except ImportError:
        from scripts.phase_analytics import main as phase_main
    args = ["phase_analytics.py"]
    if velocity:
        args.append("--velocity")
    if json_output:
        args.append("--json")
    old_argv = sys.argv
    sys.argv = args
    try:
        phase_main()
    except SystemExit:
        pass
    finally:
        sys.argv = old_argv


@app.command()
def rate(
    rater: str = typer.Option(None, "--rater", help="Single rater ID"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show prompts only"),
    compute_ira: bool = typer.Option(False, "--compute-ira", help="Compute IRA after"),
):
    """Run multi-model IRA rating session."""
    from generate_ratings import generate_ratings

    result = generate_ratings(
        dry_run=dry_run,
        single_rater=rater,
        compute_ira=compute_ira,
    )

    if result["status"] == "error":
        typer.echo(f"Error: {result['error']}", err=True)
        raise typer.Exit(1)

    typer.echo(f"Status: {result['status']}")
    if result.get("raters"):
        typer.echo(f"Raters: {', '.join(result['raters'])}")


@app.command()
def mode(
    set_mode: str = typer.Option(None, "--set", help="Switch mode: precision, volume, hybrid"),
    compare: bool = typer.Option(False, "--compare", help="Compare all modes"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview mode switch"),
    json_output: bool = typer.Option(False, "--json", help="JSON output"),
):
    """Show or switch pipeline mode (precision/volume/hybrid)."""
    try:
        from pipeline_mode import compare_modes, format_report, get_active_thresholds, get_current_mode
        from pipeline_mode import set_mode as do_set_mode
    except ImportError:
        from scripts.pipeline_mode import compare_modes, format_report, get_active_thresholds, get_current_mode
        from scripts.pipeline_mode import set_mode as do_set_mode
    import json as _json  # noqa: I001

    if set_mode:
        result = do_set_mode(set_mode, dry_run=dry_run)
    elif compare:
        result = compare_modes()
    else:
        m = get_current_mode()
        t = get_active_thresholds()
        result = {"mode": m, "thresholds": t}

    if json_output:
        typer.echo(_json.dumps(result, indent=2, default=str))
    else:
        typer.echo(format_report(result))


@app.command()
def outreach(
    target: str = typer.Argument(..., help="Entry ID"),
    template_type: str = typer.Option(None, "--type", help="connect, email, or followup"),
    json_output: bool = typer.Option(False, "--json", help="JSON output"),
):
    """Generate outreach templates for an entry."""
    try:
        from outreach_templates import (
            _find_entry,
            _identity_position,
            _org_name,
            _role_title,
            _track,
            format_report,
            generate_all_templates,
            generate_cold_email,
            generate_connect_note,
            generate_followup,
        )
    except ImportError:
        from scripts.outreach_templates import (
            _find_entry,
            _identity_position,
            _org_name,
            _role_title,
            _track,
            format_report,
            generate_all_templates,
            generate_cold_email,
            generate_connect_note,
            generate_followup,
        )
    import json as _json  # noqa: I001

    entry = _find_entry(target)
    if not entry:
        typer.echo(f"Entry not found: {target}", err=True)
        raise typer.Exit(1)

    if template_type == "connect":
        result = generate_connect_note(entry)
    elif template_type == "email":
        result = generate_cold_email(entry)
    elif template_type == "followup":
        result = generate_followup(entry)
    else:
        result = generate_all_templates(entry)

    if json_output:
        typer.echo(_json.dumps(result, indent=2, default=str))
    else:
        if "templates" not in result:
            result = {"entry_id": entry.get("id"), "org": _org_name(entry), "role": _role_title(entry), "track": _track(entry), "identity_position": _identity_position(entry), "templates": {result["type"]: result}}
        typer.echo(format_report(result))


# ============================================================================
# DAILY PIPELINE CYCLE (SCAN → MATCH → BUILD)
# ============================================================================

@app.command()
def scan(
    sources: str = typer.Option("all", help="Source group: ats, free, all"),
    max_entries: int = typer.Option(100, "--max", help="Max new entries to create"),
    yes: bool = typer.Option(False, "-y", "--yes", help="Execute (default is dry-run)"),
    json_output: bool = typer.Option(False, "--json", help="JSON output"),
):
    """Unified job scan: all 8 APIs, dedup, pre-score."""
    import dataclasses
    import json as _json

    try:
        from scan_orchestrator import scan_all
    except ImportError:
        from scripts.scan_orchestrator import scan_all

    result = scan_all(dry_run=not yes, sources=sources, max_entries=max_entries)
    if json_output:
        typer.echo(_json.dumps(dataclasses.asdict(result), indent=2, default=str))
    else:
        typer.echo(f"Scan complete: {result.total_qualified} qualified from {result.total_fetched} fetched")
        typer.echo(f"  Sources: {', '.join(result.sources_queried)}")
        typer.echo(f"  Duplicates skipped: {result.duplicates_skipped}")
        if result.errors:
            for e in result.errors:
                typer.echo(f"  Error: {e}", err=True)


@app.command()
def match(
    target: str = typer.Argument(None, help="Score a single entry ID"),
    top_n: int = typer.Option(10, "--top", help="Number of top matches to show"),
    json_output: bool = typer.Option(False, "--json", help="JSON output"),
):
    """Auto-score unscored entries, rank top matches."""
    import dataclasses
    import json as _json

    try:
        from match_engine import match_and_rank
    except ImportError:
        from scripts.match_engine import match_and_rank

    result = match_and_rank(target_id=target, top_n=top_n)
    if json_output:
        typer.echo(_json.dumps(dataclasses.asdict(result), indent=2, default=str))
    else:
        typer.echo(f"Match: scored {result.entries_scored}, qualified {result.qualified}")
        typer.echo(f"  Threshold: {result.threshold_used}")
        if result.top_matches:
            typer.echo("  Top matches:")
            for m in result.top_matches:
                typer.echo(f"    {m.composite_score:.1f}  {m.entry_id} ({m.organization})")


@app.command()
def build(
    target: str = typer.Argument(None, help="Build for a single entry ID"),
    yes: bool = typer.Option(False, "-y", "--yes", help="Execute (default is dry-run)"),
    json_output: bool = typer.Option(False, "--json", help="JSON output"),
):
    """LLM-powered material generation (cover letters, blocks, resumes)."""
    import dataclasses
    import json as _json

    try:
        from material_builder import build_materials
    except ImportError:
        from scripts.material_builder import build_materials

    result = build_materials(target_id=target, dry_run=not yes)
    if json_output:
        typer.echo(_json.dumps(dataclasses.asdict(result), indent=2, default=str))
    else:
        typer.echo(f"Build: {result.entries_processed} entries processed")
        typer.echo(f"  Cover letters: {result.cover_letters_generated}")
        typer.echo(f"  Resumes wired: {result.resumes_wired}")
        typer.echo(f"  Blocks selected: {result.blocks_selected}")
        if result.errors:
            for e in result.errors:
                typer.echo(f"  Error: {e}", err=True)


@app.command()
def apply(
    target: str = typer.Argument(None, help="Check/submit a single entry"),
    yes: bool = typer.Option(False, "-y", "--yes", help="Execute submissions"),
    json_output: bool = typer.Option(False, "--json", help="JSON output"),
):
    """Readiness check + ATS submission for staged entries."""
    import dataclasses
    import json as _json

    try:
        from apply_engine import apply_ready_entries
    except ImportError:
        from scripts.apply_engine import apply_ready_entries

    entry_ids = [target] if target else None
    result = apply_ready_entries(entry_ids=entry_ids, dry_run=not yes)
    if json_output:
        typer.echo(_json.dumps(dataclasses.asdict(result), indent=2, default=str))
    else:
        typer.echo(f"Apply: checked {len(result.checked)}, submitted {len(result.submitted)}")
        for check in result.checked:
            status = "READY" if check.is_ready else "NOT READY"
            typer.echo(f"  {check.entry_id} [{check.portal}]: {status}")
            for m in check.missing:
                typer.echo(f"    - {m}")
        if result.errors:
            for e in result.errors:
                typer.echo(f"  Error: {e}", err=True)


@app.command(name="outreach-prep")
def outreach_prep(
    target: str = typer.Argument(None, help="Single entry ID"),
    yes: bool = typer.Option(False, "-y", "--yes", help="Execute (write files)"),
    json_output: bool = typer.Option(False, "--json", help="JSON output"),
):
    """Generate outreach templates + set follow-up protocol dates."""
    import dataclasses
    import json as _json

    try:
        from outreach_engine import prepare_outreach
    except ImportError:
        from scripts.outreach_engine import prepare_outreach

    entry_ids = [target] if target else None
    result = prepare_outreach(entry_ids=entry_ids, dry_run=not yes)
    if json_output:
        typer.echo(_json.dumps(dataclasses.asdict(result), indent=2, default=str))
    else:
        typer.echo(f"Outreach: {len(result.entries_processed)} entries, {result.templates_generated} templates")
        for a in result.actions:
            typer.echo(f"  [{a.scheduled_date}] {a.entry_id}: {a.action_type} via {a.channel}")
        if result.errors:
            for e in result.errors:
                typer.echo(f"  Error: {e}", err=True)


@app.command()
def cycle(
    phase: list[str] = typer.Option(None, "--phase", help="Run specific phase(s): scan, match, build"),
    yes: bool = typer.Option(False, "-y", "--yes", help="Execute (default is dry-run)"),
    json_output: bool = typer.Option(False, "--json", help="JSON output"),
):
    """Daily pipeline cycle: Scan → Match → Build."""
    import json as _json

    try:
        from daily_pipeline_orchestrator import run_daily_cycle
    except ImportError:
        from scripts.daily_pipeline_orchestrator import run_daily_cycle

    phases = phase if phase else None
    result = run_daily_cycle(dry_run=not yes, phases=phases)
    if json_output:
        typer.echo(_json.dumps(result, indent=2, default=str))
    else:
        typer.echo("Daily Cycle Results:")
        for p in ("scan", "match", "build", "apply", "outreach"):
            if p in result:
                typer.echo(f"  {p}: {result[p].get('status', 'done')}")
        if "auto_advance" in result:
            aa = result["auto_advance"]
            if aa.get("advanced"):
                typer.echo(f"  auto-advance: {len(aa['advanced'])} entries")
        if "followup_actions_logged" in result:
            typer.echo(f"  followup: {result['followup_actions_logged']} actions logged")


@app.command()
def preflight(
    json_output: bool = typer.Option(False, "--json", help="JSON output"),
):
    """Check system readiness for autonomous pipeline operation."""
    import json as _json

    try:
        from daily_pipeline_orchestrator import preflight_check
    except ImportError:
        from scripts.daily_pipeline_orchestrator import preflight_check

    check = preflight_check()
    if json_output:
        typer.echo(_json.dumps(check, indent=2))
    else:
        status = "READY" if check["ready"] else "NOT READY"
        typer.echo(f"Preflight: {status}")
        typer.echo(f"Entries: {check['entries_found']}")
        if check["issues"]:
            for issue in check["issues"]:
                typer.echo(f"  - {issue}")
    raise typer.Exit(0 if check["ready"] else 1)


if __name__ == "__main__":
    app()
