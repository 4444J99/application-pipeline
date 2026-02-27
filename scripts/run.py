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
}

# --- Parameterized commands (word + target ID) ---
PARAM_COMMANDS = {
    "score":    ("score.py", ["--target"],               "Score a single entry"),
    "enrich":   ("enrich.py", ["--target", None, "--all", "--yes"], "Wire materials/blocks/variants"),
    "advance":  ("advance.py", ["--id"],                 "Advance entry to next status"),
    "compose":  ("compose.py", ["--target"],             "Compose submission from blocks"),
    "draft":    ("draft.py", ["--target"],               "Draft from profile content"),
    "submit":   ("submit.py", ["--target"],              "Generate portal-ready checklist"),
    "check":    ("submit.py", ["--check"],               "Pre-submit validation"),
    "record":   ("submit.py", ["--target", None, "--record"], "Record completed submission"),
    "gate":     ("hygiene.py", ["--gate"],               "Track-specific readiness gate"),
    "contacts": ("research_contacts.py", ["--target"],   "Research hiring contacts"),
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
    print("  Morning:  standup → followup → outcomes → campaign")
    print("  Submit:   campaign → check <id> → submit <id> → record <id>")
    print("  Research: hygiene → scoreall → qualify → enrichall")
    print("  Analyze:  funnel → conversion → velocity → metrics")
    print()
    print("Usage: python scripts/run.py <command> [target-id]")


def run_command(cmd: str, target: str | None = None):
    """Execute a command."""
    # Check standalone commands first (unless a target is provided)
    if cmd in COMMANDS and target is None:
        script, args, _ = COMMANDS[cmd]
        full_args = [sys.executable, str(SCRIPTS_DIR / script)] + args
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
        full_args = [sys.executable, str(SCRIPTS_DIR / script)] + args
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
    target = sys.argv[2] if len(sys.argv) > 2 else None

    run_command(cmd, target)


if __name__ == "__main__":
    main()
