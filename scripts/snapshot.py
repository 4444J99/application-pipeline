#!/usr/bin/env python3
"""Daily pipeline snapshot — captures key metrics for trend tracking.

Saves daily snapshots to signals/daily-snapshots/ for historical comparison.
Supports trend analysis across 7d/30d/90d windows.

Usage:
    python scripts/snapshot.py --report    # Show current snapshot
    python scripts/snapshot.py --save      # Save today's snapshot
    python scripts/snapshot.py --trends    # Show 7d/30d/90d trends
    python scripts/snapshot.py --json      # JSON output
"""

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import (
    ACTIONABLE_STATUSES,
    COMPANY_CAP,
    SIGNALS_DIR,
    get_score,
    load_entries,
    parse_date,
)

SNAPSHOTS_DIR = SIGNALS_DIR / "daily-snapshots"


def capture_snapshot(entries: list[dict] | None = None) -> dict:
    """Capture current pipeline state as a snapshot dict."""
    if entries is None:
        entries = load_entries()

    today = date.today()

    # Status distribution
    status_counts: dict[str, int] = {}
    for e in entries:
        s = e.get("status", "unknown")
        status_counts[s] = status_counts.get(s, 0) + 1

    # Actionable entries
    actionable = [e for e in entries if e.get("status") in ACTIONABLE_STATUSES]

    # Score stats
    scores = [get_score(e) for e in entries if get_score(e) is not None]
    avg_score = sum(scores) / len(scores) if scores else 0.0

    # Stale count (entries untouched for >14 days in actionable statuses)
    stale = 0
    for e in actionable:
        lt = e.get("last_touched")
        if lt:
            d = parse_date(lt)
            if d and (today - d).days >= 14:
                stale += 1

    # Org-cap violations
    org_map: dict[str, int] = {}
    active_statuses = {"research", "qualified", "drafting", "staged", "submitted", "acknowledged", "interview"}
    for e in entries:
        if e.get("status") not in active_statuses:
            continue
        target = e.get("target", {})
        if isinstance(target, dict):
            org = target.get("organization", "")
            if org:
                org_map[org.lower()] = org_map.get(org.lower(), 0) + 1
    org_cap_violations = sum(1 for count in org_map.values() if count > COMPANY_CAP)

    # Track distribution
    track_counts: dict[str, int] = {}
    for e in entries:
        t = e.get("track", "unknown")
        track_counts[t] = track_counts.get(t, 0) + 1

    return {
        "date": str(today),
        "total_entries": len(entries),
        "actionable_count": len(actionable),
        "stale_count": stale,
        "avg_score": round(avg_score, 2),
        "org_cap_violations": org_cap_violations,
        "status_distribution": status_counts,
        "track_distribution": track_counts,
        "scores_above_9": sum(1 for s in scores if s >= 9.0),
    }


def save_snapshot(snapshot: dict) -> Path:
    """Save snapshot to daily-snapshots directory."""
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    path = SNAPSHOTS_DIR / f"{snapshot['date']}.json"
    with open(path, "w") as f:
        json.dump(snapshot, f, indent=2)
    return path


def load_snapshot(date_str: str) -> dict | None:
    """Load a snapshot by date string (YYYY-MM-DD)."""
    path = SNAPSHOTS_DIR / f"{date_str}.json"
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def compute_deltas(current: dict, previous: dict) -> dict:
    """Compute deltas between two snapshots."""
    deltas = {}
    for key in ("total_entries", "actionable_count", "stale_count", "avg_score",
                "org_cap_violations", "scores_above_9"):
        curr = current.get(key, 0)
        prev = previous.get(key, 0)
        deltas[key] = round(curr - prev, 2)
    return deltas


def compute_slope(values: list[float]) -> float:
    """Compute linear regression slope for trend direction.

    Uses simple least-squares: slope = sum((x-xbar)(y-ybar)) / sum((x-xbar)^2)
    """
    n = len(values)
    if n < 2:
        return 0.0
    x_bar = (n - 1) / 2
    y_bar = sum(values) / n
    num = sum((i - x_bar) * (v - y_bar) for i, v in enumerate(values))
    den = sum((i - x_bar) ** 2 for i in range(n))
    return num / den if den != 0 else 0.0


def detect_inflections(snapshots: list[dict], key: str) -> list[str]:
    """Flag metric reversals (direction changes) in a time series."""
    values = [s.get(key, 0) for s in snapshots if key in s]
    if len(values) < 3:
        return []
    inflections = []
    for i in range(1, len(values) - 1):
        prev_dir = values[i] - values[i - 1]
        next_dir = values[i + 1] - values[i]
        if prev_dir > 0 and next_dir < 0:
            inflections.append(f"{key}: peak at index {i} ({values[i]})")
        elif prev_dir < 0 and next_dir > 0:
            inflections.append(f"{key}: trough at index {i} ({values[i]})")
    return inflections


def load_recent_snapshots(days: int = 90) -> list[dict]:
    """Load snapshots from the last N days."""
    if not SNAPSHOTS_DIR.exists():
        return []
    today = date.today()
    snapshots = []
    for d in range(days):
        ds = str(today - timedelta(days=d))
        snap = load_snapshot(ds)
        if snap:
            snapshots.append(snap)
    return list(reversed(snapshots))  # oldest first


def compute_trends(snapshots: list[dict]) -> dict:
    """Compute trend data from a list of snapshots."""
    if not snapshots:
        return {"error": "No snapshots available"}

    current = snapshots[-1]
    trends = {"current": current, "windows": {}}

    for window_name, window_days in [("7d", 7), ("30d", 30), ("90d", 90)]:
        window = [s for s in snapshots if s.get("date", "") >= str(date.today() - timedelta(days=window_days))]
        if len(window) < 2:
            trends["windows"][window_name] = {"available": False, "snapshots": len(window)}
            continue
        trends["windows"][window_name] = {
            "available": True,
            "snapshots": len(window),
            "deltas": compute_deltas(window[-1], window[0]),
            "slope_actionable": round(compute_slope([s.get("actionable_count", 0) for s in window]), 3),
            "slope_score": round(compute_slope([s.get("avg_score", 0) for s in window]), 3),
            "inflections": detect_inflections(window, "actionable_count")
                         + detect_inflections(window, "avg_score"),
        }
    return trends


def format_snapshot(snapshot: dict) -> str:
    """Format a snapshot for human display."""
    lines = ["Pipeline Snapshot", "=" * 50]
    lines.append(f"  Date:               {snapshot['date']}")
    lines.append(f"  Total entries:      {snapshot['total_entries']}")
    lines.append(f"  Actionable:         {snapshot['actionable_count']}")
    lines.append(f"  Stale (>14d):       {snapshot['stale_count']}")
    lines.append(f"  Avg score:          {snapshot['avg_score']:.2f}")
    lines.append(f"  Scores >= 9.0:      {snapshot['scores_above_9']}")
    lines.append(f"  Org-cap violations: {snapshot['org_cap_violations']}")
    lines.append("\n  Status distribution:")
    for status, count in sorted(snapshot.get("status_distribution", {}).items()):
        lines.append(f"    {status:<20s} {count}")
    return "\n".join(lines)


def format_trends(trends: dict) -> str:
    """Format trend data for human display."""
    if "error" in trends:
        return f"Trends: {trends['error']}"
    lines = ["Pipeline Trends", "=" * 50]
    for window_name, data in trends.get("windows", {}).items():
        if not data.get("available"):
            lines.append(f"\n  {window_name}: insufficient data ({data.get('snapshots', 0)} snapshots)")
            continue
        lines.append(f"\n  {window_name} ({data['snapshots']} snapshots):")
        deltas = data.get("deltas", {})
        for key, val in deltas.items():
            sign = "+" if val > 0 else ""
            lines.append(f"    {key:<25s} {sign}{val}")
        lines.append(f"    slope(actionable):    {data.get('slope_actionable', 0):.3f}")
        lines.append(f"    slope(avg_score):     {data.get('slope_score', 0):.3f}")
        inflections = data.get("inflections", [])
        if inflections:
            lines.append("    inflections:")
            for inf in inflections:
                lines.append(f"      - {inf}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Daily pipeline snapshot and trend tracking")
    parser.add_argument("--report", action="store_true", help="Show current snapshot")
    parser.add_argument("--save", action="store_true", help="Save today's snapshot")
    parser.add_argument("--trends", action="store_true", help="Show trends (7d/30d/90d)")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    if not any([args.report, args.save, args.trends, args.json]):
        args.report = True

    entries = load_entries()
    snapshot = capture_snapshot(entries)

    if args.save:
        path = save_snapshot(snapshot)
        print(f"Snapshot saved to {path}")

    if args.json:
        if args.trends:
            snapshots = load_recent_snapshots()
            payload = compute_trends(snapshots)
        else:
            payload = snapshot
        print(json.dumps(payload, indent=2, default=str))
        return

    if args.trends:
        snapshots = load_recent_snapshots()
        print(format_trends(compute_trends(snapshots)))
    elif args.report:
        print(format_snapshot(snapshot))


if __name__ == "__main__":
    main()
