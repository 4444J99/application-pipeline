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
from datetime import datetime
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_api import (
    ResultStatus,
    advance_entry,
    score_entry,
)
from pipeline_lib import (
    SIGNALS_DIR,
    can_advance,
    get_deadline,
    is_actionable,
    load_entries,
)

# --- Agent rules loader ---

_RULES_PATH = Path(__file__).resolve().parent.parent / "strategy" / "agent-rules.yaml"


def _load_agent_rules() -> dict:
    """Load agent decision rules from YAML, falling back to defaults."""
    if _RULES_PATH.exists():
        try:
            with open(_RULES_PATH) as f:
                data = yaml.safe_load(f) or {}
            return data.get("rules", {})
        except Exception:
            pass
    return {}


_RULES = _load_agent_rules()

# Extract configurable thresholds from rules YAML (with hardcoded fallback)
RESEARCH_QUALIFY_THRESHOLD = _RULES.get("advance_research_to_qualified", {}).get("threshold", 7.0)
QUALIFIED_DRAFTING_THRESHOLD = _RULES.get("advance_qualified_to_drafting", {}).get("threshold", 8.0)
DRAFTING_STAGED_MIN_DAYS = _RULES.get("advance_drafting_to_staged", {}).get("min_days", 7)
STAGED_SUBMIT_MAX_DAYS = _RULES.get("flag_staged_for_submission", {}).get("max_days", 7)


def _rule_enabled(rule_name: str) -> bool:
    """Check if a rule is enabled in config (defaults to True)."""
    return _RULES.get(rule_name, {}).get("enabled", True)


class PipelineAgent:
    """Autonomous agent for pipeline state transitions."""

    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.actions_planned = []
        self.actions_executed = []
        self.errors = []
        self.started_at = datetime.now()

    def plan_actions(self, entries: list[dict]) -> list[dict]:
        """Analyze pipeline state; return planned actions.

        Rules loaded from strategy/agent-rules.yaml:
        1. Research entries: auto-score if no score
        2. Research + score >= threshold: auto-advance to qualified
        3. Qualified + score >= threshold: auto-advance to drafting
        4. Drafting + deadline > min_days: auto-advance to staged
        5. Staged + deadline < max_days: flag for submission
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
            if status == "research" and not score and _rule_enabled("score_unscored_research"):
                actions.append({
                    "entry_id": entry_id,
                    "action": "score",
                    "reason": "research entry lacks score",
                    "severity": "routine",
                })

            # Rule 2: Research + score >= threshold
            elif (status == "research" and score and score >= RESEARCH_QUALIFY_THRESHOLD
                  and _rule_enabled("advance_research_to_qualified")):
                can_adv, reason = can_advance(entry, "qualified")
                if can_adv:
                    actions.append({
                        "entry_id": entry_id,
                        "action": "advance",
                        "to_status": "qualified",
                        "reason": f"research with score {score}",
                        "severity": "routine",
                    })

            # Rule 3: Qualified, score >= threshold
            elif (status == "qualified" and score and score >= QUALIFIED_DRAFTING_THRESHOLD
                  and _rule_enabled("advance_qualified_to_drafting")):
                can_adv, reason = can_advance(entry, "drafting")
                if can_adv:
                    actions.append({
                        "entry_id": entry_id,
                        "action": "advance",
                        "to_status": "drafting",
                        "reason": f"qualified with high score {score}",
                        "severity": "routine",
                    })

            # Rule 4: Drafting, deadline > min_days
            elif status == "drafting" and _rule_enabled("advance_drafting_to_staged"):
                if days_left and days_left > DRAFTING_STAGED_MIN_DAYS:
                    can_adv, reason = can_advance(entry, "staged")
                    if can_adv:
                        actions.append({
                            "entry_id": entry_id,
                            "action": "advance",
                            "to_status": "staged",
                            "reason": f"drafting with {days_left}d until deadline",
                            "severity": "routine",
                        })

            # Rule 5: Staged, deadline < max_days
            elif status == "staged" and _rule_enabled("flag_staged_for_submission"):
                if days_left and days_left < STAGED_SUBMIT_MAX_DAYS:
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

    def write_run_log(self) -> None:
        """Persist run summary for standup visibility and automation audits."""
        log_path = SIGNALS_DIR / "agent-actions.yaml"
        SIGNALS_DIR.mkdir(parents=True, exist_ok=True)

        if log_path.exists():
            try:
                with open(log_path) as f:
                    data = yaml.safe_load(f) or {}
            except Exception:
                data = {}
        else:
            data = {}

        runs = data.get("runs", [])
        if not isinstance(runs, list):
            runs = []

        run_record = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "mode": "execute" if not self.dry_run else "plan",
            "planned": len(self.actions_planned),
            "executed": len(self.actions_executed),
            "errors": len(self.errors),
            "urgent": sum(1 for a in self.actions_planned if a.get("severity") == "urgent"),
            "action_types": sorted({a.get("action", "unknown") for a in self.actions_planned}),
            "duration_seconds": int((datetime.now() - self.started_at).total_seconds()),
        }
        runs.append(run_record)
        data["runs"] = runs[-100:]

        with open(log_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)


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

    agent.write_run_log()


if __name__ == "__main__":
    main()
