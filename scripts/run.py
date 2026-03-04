#!/usr/bin/env python3
"""Single-word command dispatcher for the application pipeline.

Maps natural-language command words to script invocations. Designed for
cross-LLM compatibility: any AI that reads this file knows every available
command and can execute the corresponding script.

Usage:
    python scripts/run.py standup
    python scripts/run.py score creative-capital-2027
    python scripts/run.py campaign
    python scripts/run.py --help
"""

import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent

# --- No-argument commands ---
COMMANDS = {
    "standup":     ("standup.py", [],                    "Daily dashboard: stale entries, deadlines, priorities, follow-ups"),
    "campaign":    ("campaign.py", [],                   "Deadline-aware campaign view with urgency tiers"),
    "hygiene":     ("hygiene.py", [],                    "Entry data quality report: URLs, staleness, gates"),
    "followup":    ("followup.py", [],                   "Today's follow-up actions and overdue items"),
    "outcomes":    ("check_outcomes.py", [],             "Entries awaiting response + stale submissions"),
    "funnel":      ("funnel_report.py", [],              "Conversion funnel analytics"),
    "metrics":     ("check_metrics.py", [],              "Metric consistency check across blocks/profiles/strategy"),
    "validate":    ("validate.py", [],                   "Pipeline YAML schema validation"),
    "status":      ("pipeline_status.py", [],            "Full pipeline status overview"),
    "velocity":    ("velocity.py", [],                   "Submission velocity stats"),
    "conversion":  ("conversion_report.py", [],          "Conversion rate report by track/position/score"),
    "scoreall":    ("score.py", ["--all", "--dry-run"],  "Preview all scores"),
    "enrichall":   ("enrich.py", ["--all", "--dry-run"], "Preview all enrichments"),
    "preflight":   ("preflight.py", [],                  "Batch submission readiness"),
    "archive":     ("archive_research.py", ["--report"], "Show archival candidates"),
    "qualify":     ("score.py", ["--auto-qualify"],       "Preview auto-qualification"),
    "email":       ("check_email.py", [],                 "Check email for submission confirmations and responses"),
    "focus":       ("hygiene.py", ["--company-focus"],    "Rule of Three: flag companies with >3 active+submitted job applications"),
    "topjobs":     ("ingest_top_roles.py", [],            "Daily glove-fit fetch: top roles ≥ 9.0 score"),
    "syncmetrics": ("sync_metrics.py", [],               "Check canonical metric consistency across blocks/strategy"),
    "hypotheses":  ("feedback_capture.py", ["--list"],   "List all recorded outcome hypotheses"),
    "analysis":    ("feedback_capture.py", ["--analyze"],"Pattern analysis of outcome hypotheses"),
    "market":      ("market_intel.py", [],               "Market conditions, benchmarks, and grant calendar"),
    "startup":     ("funding_scorer.py", ["--viability"],       "Startup viability score + recommended funding path"),
    "funding":     ("funding_scorer.py", ["--pathway"],         "Non-dilutive funding opportunities by viability"),
    "differentiate": ("funding_scorer.py", ["--differentiation"], "Differentiation rubric score + gap analysis"),
    "blindspots":  ("funding_scorer.py", ["--blindspots"],      "Blind spots checklist with completion status"),
    "sourcejobs":  ("source_jobs.py", ["--fetch", "--dry-run"], "Preview new job postings from ATS APIs"),
    "keywords":    ("distill_keywords.py", [],           "Extract keywords from job postings"),
    "buildblocks": ("generate_project_blocks.py", [],    "Generate blocks from project data"),
    "morning":     ("morning.py", [],                    "Morning digest: health + stale + followups + campaign + funding"),
    "derive":      ("derive_profile.py", [],             "Auto-derive startup profile fields from pipeline data"),
    "learner":     ("outcome_learner.py", [],            "Outcome learning engine: calibration report"),
    "hydrate":     ("hydrate_followups.py", [],          "Batch-hydrate follow-up fields on submitted entries"),
    "triage":      ("smart_triage.py", [],               "Smart triage: decay-scored research entry ranking"),
    "batch":       ("batch_submit.py", [],               "Batch submit staged rolling-deadline entries (dry-run)"),
    "tracker":     ("blind_spot_tracker.py", [],         "Blind spot progress tracker with actionable items"),
    "dashboard":   ("conversion_dashboard.py", [],       "Conversion intelligence dashboard"),
    "freshness":      ("freshness_monitor.py", [],          "Entry freshness report (posting age analysis)"),
    "jobfreshness":   ("standup.py", ["--section", "jobfreshness"], "Job freshness dashboard: hot/warm/stale postings"),
    "expirejobs":     ("freshness_monitor.py", ["--auto-expire-jobs"], "Auto-expire stale job postings (dry-run)"),
    "agent":       ("agent.py", ["--plan"],              "Agent: preview planned autonomous actions"),
    "monitor":     ("monitor_pipeline.py", [],            "Monitor backup + conversion-log freshness"),
    "automation":  ("launchd_manager.py", ["--status"],  "Launchd automation status"),
    "automation-on": ("launchd_manager.py", ["--install", "--kickstart"], "Install and activate launchd agents"),
    "automation-off": ("launchd_manager.py", ["--uninstall"], "Unload and remove launchd agents"),
    "deferred":    ("check_deferred.py", [],              "Deferred entries: overdue and upcoming re-activations"),
    "backup":      ("backup_pipeline.py", ["list"],       "List pipeline backups"),
    "blockroi":    ("block_roi_analysis.py", [],          "Block acceptance rate ROI analysis"),
    "portfolio":   ("portfolio_analysis.py", [],          "Portfolio analysis: blocks, positions, channels, variants"),
    "signals":     ("log_signal_action.py", ["--list"],   "Signal-to-action audit trail"),
    "resumes":     ("upgrade_resumes.py", [],             "Check for stale resume batch references"),
    "hypotheses-v": ("validate_hypotheses.py", [],        "Validate outcome hypotheses vs actuals"),
    "backfill":    ("backfill_dates.py", ["--report"],   "Backfill date_added from timeline.researched"),
    "jobprofiles": ("generate_job_profile.py", ["--batch", "--dry-run"], "Preview missing job profiles for auto-sourced entries"),
    "bridge":      ("portfolio_bridge.py", [],           "Portfolio-pipeline work sample suggestions"),
    "warmintro":   ("warm_intro_audit.py", [],            "Warm intro audit: referral paths and org density"),
    "reachable":   ("score.py", ["--reachable"],           "Reachability analysis: entries that network can unlock"),
    "triagestaged": ("score.py", ["--triage-staged"],      "Triage staged entries: submit-ready / hold / demote"),
    "enrichnetwork": ("enrich.py", ["--network"],          "Hydrate network fields from existing signals"),
    "relationships": ("standup.py", ["--section", "relationships"], "Relationship cultivation dashboard"),
    "cultivate":   ("cultivate.py", ["--candidates"],       "Relationship cultivation candidates"),
    "discover":    ("discover_jobs.py", [],                "Skill-based job discovery across free APIs"),
    "audit":       ("submission_audit.py", [],              "Batch submission readiness diagnostic"),
    "submitall":   ("submit_ready.py", [],                   "Submit all audit-ready entries (dry-run)"),
    "dailyhealth": ("daily_pipeline_health.py", [],          "Composite daily health run: source, score, enrich, campaign, standup, hygiene"),
    "idmaps":      ("generate_id_mappings.py", [],           "Generate ID mapping suggestions from filesystem"),
    "verifyall":   ("verify_all.py", [],                     "Run full verification gates (matrix + lint + validate + tests)"),
    "verifymatrix": ("verification_matrix.py", ["--strict"], "Check module verification coverage matrix"),
}

# --- Parameterized commands (word + target ID) ---
PARAM_COMMANDS = {
    "score":    ("score.py", ["--target"],               "Score a single entry"),
    "enrich":   ("enrich.py", ["--id", None, "--all"], "Wire materials/blocks/variants"),
    "advance":  ("advance.py", ["--id"],                 "Advance entry to next status"),
    "compose":  ("compose.py", ["--target"],             "Compose submission from blocks"),
    "draft":    ("draft.py", ["--target"],               "Draft from profile content"),
    "submit":   ("submit.py", ["--target"],              "Generate portal-ready checklist"),
    "check":    ("submit.py", ["--check"],               "Pre-submit validation"),
    "record":   ("submit.py", ["--target", None, "--record"], "Record completed submission"),
    "gate":     ("hygiene.py", ["--gate"],               "Track-specific readiness gate"),
    "contacts":   ("research_contacts.py", ["--target"],  "Research hiring contacts"),
    "hypothesis": ("feedback_capture.py", ["--entry"],   "Capture outcome hypothesis for an entry"),
    "alchemize":  ("alchemize.py", ["--target"],         "End-to-end Greenhouse orchestrator (research → synthesis)"),
    "answers":    ("answer_questions.py", ["--target"],  "Generate AI-assisted answers for portal questions"),
    "tailor":     ("tailor_resume.py", ["--target"],     "Tailor resume for a specific entry"),
    "samples":    ("portfolio_bridge.py", ["--target"],  "Suggest work samples for an entry"),
    "jobprofile": ("generate_job_profile.py", ["--target"], "Generate minimal profile for auto-sourced job entry"),
    "discover":   ("discover_jobs.py", ["--position"],     "Discover jobs for a specific identity position"),
    "review":     ("review_entry.py", ["--target"],        "Mark an entry reviewed for submission governance"),
    "cultivate":  ("cultivate.py", ["--plan"],              "Generate cultivation plan for an entry"),
}


def show_help():
    """Print all available commands."""
    print("Application Pipeline — Single-Word Commands")
    print("=" * 55)
    print()
    print("STANDALONE COMMANDS:")
    for cmd, (script, _, desc) in sorted(COMMANDS.items()):
        print(f"  {cmd:<14s} {desc}")
    print()
    print("PARAMETERIZED COMMANDS (word + entry ID):")
    for cmd, (script, _, desc) in sorted(PARAM_COMMANDS.items()):
        print(f"  {cmd:<14s} {desc}")
    print()
    print("SESSION SEQUENCES:")
    print("  Morning:  morning (or: standup → followup → outcomes → campaign)")
    print("  Submit:   campaign → check <id> → submit <id> → record <id>")
    print("  Batch:    triage → batch → hydrate → freshness")
    print("  Research: hygiene → scoreall → qualify → enrichall")
    print("  Analyze:  funnel → conversion → velocity → dashboard → blockroi")
    print("  Strategy: startup → funding → differentiate → tracker")
    print("  Agent:    agent → deferred → signals → hypotheses-v")
    print("  Health:   monitor → freshness → resumes → backup → portfolio")
    print()
    print("Usage: python scripts/run.py <command> [args...]")


def run_command(
    cmd: str,
    target: str | None = None,
    extra_args: list[str] | None = None,
):
    """Execute a command."""
    extra_args = extra_args or []

    # Check standalone commands first (unless a target is provided)
    if cmd in COMMANDS and target is None:
        script, args, _ = COMMANDS[cmd]
        full_args = [sys.executable, str(SCRIPTS_DIR / script)] + args + extra_args
    elif cmd in PARAM_COMMANDS and target is not None:
        script, arg_template, _ = PARAM_COMMANDS[cmd]
        # Build args: replace None placeholders with the target
        args = []
        for a in arg_template:
            if a is None:
                args.append(target)
            else:
                args.append(a)
        # If target wasn't inserted via None placeholder, append after the flag
        if target not in args:
            args.append(target)
        full_args = [sys.executable, str(SCRIPTS_DIR / script)] + args + extra_args
    elif cmd in PARAM_COMMANDS and target is None:
        _, _, desc = PARAM_COMMANDS[cmd]
        print(f"Error: '{cmd}' requires a target ID.", file=sys.stderr)
        print(f"Usage: python scripts/run.py {cmd} <entry-id>", file=sys.stderr)
        sys.exit(1)
    else:
        print(f"Unknown command: '{cmd}'", file=sys.stderr)
        print("Run 'python scripts/run.py --help' for available commands.", file=sys.stderr)
        sys.exit(1)

    result = subprocess.run(full_args)
    sys.exit(result.returncode)


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("--help", "-h", "help"):
        show_help()
        sys.exit(0)

    cmd = sys.argv[1].lower()
    rest = sys.argv[2:]

    target = None
    extra_args = rest

    # If a command supports parameterized mode and the first arg is positional,
    # treat it as target ID and pass remaining args through.
    if cmd in PARAM_COMMANDS and rest and not rest[0].startswith("-"):
        target = rest[0]
        extra_args = rest[1:]

    # For standalone-only commands, all trailing args are passthrough flags/args.
    if cmd in COMMANDS and cmd not in PARAM_COMMANDS:
        target = None
        extra_args = rest

    run_command(cmd, target, extra_args)


if __name__ == "__main__":
    main()
