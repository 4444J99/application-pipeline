#!/usr/bin/env python3
"""Autonomous pipeline agent: reads state, decides actions, executes.

The agent loops through the pipeline state machine, making decisions based on
rules (e.g., "score >= 7 AND deadline < 7 days → submit"). This enables
unattended batch processing while maintaining human decision-making authority.

Usage:
    python scripts/agent.py --plan                  # Show planned actions (dry-run)
    python scripts/agent.py --execute --yes         # Execute autonomously
    python scripts/agent.py --target <id> --yes     # Single entry
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import (
    load_entries,
    get_deadline,
    is_actionable,
    can_advance,
    update_yaml_field,
)
from pipeline_api import (
    score_entry,
    advance_entry,
    ResultStatus,
)


class PipelineAgent:
    """Autonomous agent for pipeline state transitions."""
    
    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.actions_planned = []
        self.actions_executed = []
        self.errors = []
    
    def plan_actions(self, entries: list[dict]) -> list[dict]:
        """Analyze pipeline state; return planned actions.
        
        Rules:
        1. Research entries: auto-score if no score
        2. Research + score >= 7: auto-advance to qualified
        3. Qualified: auto-advance if score >= 8
        4. Drafting: auto-advance if deadline > 7 days away
        5. Staged + deadline < 7: flag for submission
        """
        actions = []
        
        for entry in entries:
            if not is_actionable(entry):
                continue
            
            entry_id = entry.get("id", "?")
            status = entry.get("status", "?")
            score = entry.get("fit", {}).get("composite") if isinstance(entry.get("fit"), dict) else None
            deadline_date, deadline_type = get_deadline(entry)
            days_left = (deadline_date - datetime.now().date()).days if deadline_date else None
            
            # Rule 1: Research entries without scores
            if status == "research" and not score:
                actions.append({
                    "entry_id": entry_id,
                    "action": "score",
                    "reason": "research entry lacks score",
                    "severity": "routine",
                })
            
            # Rule 2: Research + score >= 7
            elif status == "research" and score and score >= 7.0:
                can, reason = can_advance(entry, "qualified")
                if can:
                    actions.append({
                        "entry_id": entry_id,
                        "action": "advance",
                        "to_status": "qualified",
                        "reason": f"research with score {score}",
                        "severity": "routine",
                    })
            
            # Rule 3: Qualified, score >= 8
            elif status == "qualified" and score and score >= 8.0:
                can, reason = can_advance(entry, "drafting")
                if can:
                    actions.append({
                        "entry_id": entry_id,
                        "action": "advance",
                        "to_status": "drafting",
                        "reason": f"qualified with high score {score}",
                        "severity": "routine",
                    })
            
            # Rule 4: Drafting, deadline > 7 days
            elif status == "drafting":
                if days_left and days_left > 7:
                    can, reason = can_advance(entry, "staged")
                    if can:
                        actions.append({
                            "entry_id": entry_id,
                            "action": "advance",
                            "to_status": "staged",
                            "reason": f"drafting with {days_left}d until deadline",
                            "severity": "routine",
                        })
            
            # Rule 5: Staged, deadline < 7 days
            elif status == "staged":
                if days_left and days_left < 7:
                    actions.append({
                        "entry_id": entry_id,
                        "action": "flag_for_submission",
                        "reason": f"staged with {days_left}d until deadline",
                        "severity": "urgent",
                    })
        
        return actions
    
    def execute_actions(self, actions: list[dict]) -> None:
        """Execute planned actions."""
        for action in actions:
            entry_id = action["entry_id"]
            action_type = action["action"]
            
            try:
                if action_type == "score":
                    result = score_entry(entry_id=entry_id, dry_run=self.dry_run)
                    if result.status in (ResultStatus.SUCCESS, ResultStatus.DRY_RUN):
                        self.actions_executed.append(action)
                    else:
                        self.errors.append((entry_id, f"score failed: {result.error}"))
                
                elif action_type == "advance":
                    target_status = action.get("to_status")
                    result = advance_entry(
                        entry_id=entry_id,
                        to_status=target_status,
                        dry_run=self.dry_run,
                    )
                    if result.status in (ResultStatus.SUCCESS, ResultStatus.DRY_RUN):
                        self.actions_executed.append(action)
                    else:
                        self.errors.append((entry_id, f"advance failed: {result.error}"))
                
                elif action_type == "flag_for_submission":
                    # Don't auto-submit; just flag
                    self.actions_executed.append(action)
            
            except Exception as e:
                self.errors.append((entry_id, str(e)))
    
    def report(self) -> str:
        """Generate agent report."""
        lines = []
        lines.append("=" * 70)
        lines.append(f"PIPELINE AGENT REPORT ({datetime.now().isoformat()})")
        lines.append(f"Mode: {'DRY-RUN' if self.dry_run else 'EXECUTE'}")
        lines.append("=" * 70)
        
        lines.append(f"\n📋 PLANNED ACTIONS: {len(self.actions_planned)}")
        for action in self.actions_planned:
            severity_marker = "🔴" if action["severity"] == "urgent" else "🟡"
            lines.append(f"  {severity_marker} {action['entry_id']}: {action['action']} "
                        f"({action['reason']})")
        
        lines.append(f"\n✅ EXECUTED ACTIONS: {len(self.actions_executed)}")
        for action in self.actions_executed:
            lines.append(f"  ✓ {action['entry_id']}: {action['action']}")
        
        if self.errors:
            lines.append(f"\n❌ ERRORS: {len(self.errors)}")
            for entry_id, error in self.errors:
                lines.append(f"  ✗ {entry_id}: {error}")
        
        lines.append("\n" + "=" * 70)
        return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Autonomous pipeline agent")
    parser.add_argument(
        "--plan",
        action="store_true",
        help="Show planned actions (dry-run)"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute autonomous actions"
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip confirmation for execute"
    )
    parser.add_argument(
        "--target",
        help="Single entry ID (optional; all if not given)"
    )
    args = parser.parse_args()
    
    if not (args.plan or args.execute):
        parser.print_help()
        sys.exit(1)
    
    entries = load_entries()
    if args.target:
        entries = [e for e in entries if e.get("id") == args.target]
        if not entries:
            print(f"Entry not found: {args.target}", file=sys.stderr)
            sys.exit(1)
    
    agent = PipelineAgent(dry_run=not args.execute)
    
    # Plan actions
    agent.actions_planned = agent.plan_actions(entries)
    
    # Show plan
    print(agent.report())
    
    # Execute if requested
    if args.execute:
        if not args.yes:
            response = input("\nExecute planned actions? (yes/no): ")
            if response.lower() != "yes":
                print("Cancelled")
                sys.exit(0)
        
        agent.execute_actions(agent.actions_planned)
        print("\n" + agent.report())


if __name__ == "__main__":
    main()
