#!/usr/bin/env python3
"""Auto-check and flag deferred entries ready for re-activation.

Deferred entries are those blocked by external factors (portal closed, hiring paused).
This script identifies when they're ready to be re-activated based on resume_date.

Usage:
    python scripts/check_deferred.py                 # List all deferred
    python scripts/check_deferred.py --alert         # Alert if overdue
    python scripts/check_deferred.py --report        # Detailed report
"""

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import load_entries, days_until


def check_deferred_entries(entries: list[dict]) -> dict:
    """Analyze deferred entries; categorize by readiness.
    
    Returns dict with:
    - overdue: entries past resume_date (should re-activate now)
    - upcoming: entries within 7 days of resume_date
    - distant: entries > 7 days away
    - no_date: deferred but no resume_date set (unclear)
    """
    overdue = []
    upcoming = []
    distant = []
    no_date = []
    
    deferred = [e for e in entries if e.get("status") == "deferred"]
    
    for entry in deferred:
        entry_id = entry.get("id", "?")
        deferral = entry.get("deferral", {})
        
        if not isinstance(deferral, dict):
            no_date.append(entry)
            continue
        
        resume_date_str = deferral.get("resume_date")
        if not resume_date_str:
            no_date.append(entry)
            continue
        
        try:
            resume_date = datetime.strptime(resume_date_str, "%Y-%m-%d").date()
            today = datetime.now().date()
            days = (resume_date - today).days
            
            if days < 0:
                overdue.append((entry, abs(days)))
            elif days <= 7:
                upcoming.append((entry, days))
            else:
                distant.append((entry, days))
        except ValueError:
            no_date.append(entry)
    
    return {
        "overdue": overdue,
        "upcoming": upcoming,
        "distant": distant,
        "no_date": no_date,
    }


def format_entry_summary(entry: dict) -> str:
    """Format entry as brief summary."""
    entry_id = entry.get("id", "?")
    name = entry.get("name", entry_id)
    deferral = entry.get("deferral", {})
    reason = deferral.get("reason", "unknown") if isinstance(deferral, dict) else "unknown"
    return f"{name} ({entry_id}) — reason: {reason}"


def run_check_deferred(alert_mode: bool = False, report_mode: bool = False):
    """Run deferred entry check."""
    entries = load_entries()
    results = check_deferred_entries(entries)
    
    overdue, upcoming, distant, no_date = (
        results["overdue"],
        results["upcoming"],
        results["distant"],
        results["no_date"],
    )
    
    print(f"DEFERRED ENTRIES ANALYSIS")
    print("=" * 70)
    
    # OVERDUE (highest priority)
    if overdue:
        print(f"\n🔴 OVERDUE FOR RE-ACTIVATION ({len(overdue)} entries)")
        print("-" * 70)
        for entry, days_ago in sorted(overdue, key=lambda x: x[1], reverse=True):
            print(f"  ⚠️  {format_entry_summary(entry)}")
            print(f"      Resume date was {days_ago} days ago — re-activate now")
            if alert_mode:
                print(f"      [ALERT: {entry.get('id')} overdue]")
    else:
        print(f"\n✓ No overdue entries")
    
    # UPCOMING (next 7 days)
    if upcoming:
        print(f"\n🟡 UPCOMING RE-ACTIVATION ({len(upcoming)} entries, next 7 days)")
        print("-" * 70)
        for entry, days in sorted(upcoming, key=lambda x: x[1]):
            print(f"  ⏱️  {format_entry_summary(entry)}")
            print(f"      Ready to re-activate in {days} day(s)")
    else:
        print(f"\n✓ No entries ready in next 7 days")
    
    # DISTANT (7+ days)
    if report_mode and distant:
        print(f"\n🔵 DISTANT RE-ACTIVATION ({len(distant)} entries, >7 days)")
        print("-" * 70)
        for entry, days in sorted(distant, key=lambda x: x[1])[:10]:  # Top 10
            print(f"  ○ {format_entry_summary(entry)}")
            print(f"     Ready to re-activate in {days} days")
        if len(distant) > 10:
            print(f"  ... and {len(distant) - 10} more")
    
    # NO RESUME_DATE
    if no_date:
        print(f"\n⚠️  INCOMPLETE DEFERRAL ({len(no_date)} entries, no resume_date)")
        print("-" * 70)
        for entry in no_date:
            print(f"  ❓ {format_entry_summary(entry)}")
            print(f"     No resume_date set — clarify when re-activation is possible")
    
    print("\n" + "=" * 70)
    print(f"Summary: {len(overdue)} overdue | {len(upcoming)} upcoming | "
          f"{len(distant)} distant | {len(no_date)} incomplete")
    
    # Return error code if overdue entries exist (for automation)
    if overdue:
        return 1
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Check deferred entries ready for re-activation"
    )
    parser.add_argument(
        "--alert",
        action="store_true",
        help="Alert if overdue entries found; return error code"
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Show full report including distant entries"
    )
    args = parser.parse_args()
    
    exit_code = run_check_deferred(alert_mode=args.alert, report_mode=args.report)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
