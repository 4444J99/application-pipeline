#!/usr/bin/env python3
"""Scheduler health audit for launchd automation.

Checks each pipeline launchd plist for:
1) installed in ~/Library/LaunchAgents
2) currently loaded in launchd
3) recently executed (based on log file freshness)

Usage:
    python scripts/scheduler_health.py
    python scripts/scheduler_health.py --strict
    python scripts/scheduler_health.py --json
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import plistlib
import subprocess
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LAUNCHD_DIR = REPO_ROOT / "launchd"
USER_LAUNCH_AGENTS = Path.home() / "Library" / "LaunchAgents"


@dataclass(frozen=True)
class SchedulerJobHealth:
    label: str
    plist: str
    installed: bool
    loaded: bool | None
    expected_interval_hours: float
    max_allowed_age_hours: float
    log_path: str | None
    log_exists: bool
    log_age_hours: float | None
    recent_run: bool


def _plist_paths() -> list[Path]:
    return sorted(LAUNCHD_DIR.glob("com.4jp.pipeline.*.plist"))


def _load_plist(path: Path) -> dict:
    with open(path, "rb") as f:
        data = plistlib.load(f)
    return data if isinstance(data, dict) else {}


def _expected_interval_hours(start_interval: object) -> float:
    """Estimate expected run cadence from StartCalendarInterval."""
    if isinstance(start_interval, dict):
        return 168.0 if "Weekday" in start_interval else 24.0

    if isinstance(start_interval, list) and start_interval:
        weekdays = [item.get("Weekday") for item in start_interval if isinstance(item, dict) and "Weekday" in item]
        if weekdays:
            # Approximate weekly cadence by number of weekday slots.
            return max(24.0, 168.0 / max(1, len(weekdays)))
        return max(1.0, 24.0 / len(start_interval))

    # Fallback for unusual schedules.
    return 24.0


def _launchctl_loaded(label: str) -> bool | None:
    """Return launchd loaded state. None when platform doesn't support launchctl."""
    if platform.system() != "Darwin":
        return None
    cmd = ["launchctl", "print", f"gui/{os.getuid()}/{label}"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode == 0


def _resolve_log_path(plist_data: dict) -> Path | None:
    raw = plist_data.get("StandardOutPath") or plist_data.get("StandardErrorPath")
    if not raw or not isinstance(raw, str):
        return None
    return Path(raw)


def collect_scheduler_health(max_age_multiplier: float = 2.0) -> list[SchedulerJobHealth]:
    jobs: list[SchedulerJobHealth] = []
    now = datetime.now(UTC)

    for plist_path in _plist_paths():
        plist_data = _load_plist(plist_path)
        label = str(plist_data.get("Label", plist_path.stem))
        installed = (USER_LAUNCH_AGENTS / plist_path.name).exists()
        loaded = _launchctl_loaded(label)
        interval_hours = _expected_interval_hours(plist_data.get("StartCalendarInterval"))
        max_allowed_age_hours = max(24.0, interval_hours * max_age_multiplier)

        log_path = _resolve_log_path(plist_data)
        log_exists = bool(log_path and log_path.exists())
        log_age_hours: float | None = None
        if log_exists and log_path:
            age_seconds = now.timestamp() - log_path.stat().st_mtime
            log_age_hours = max(0.0, age_seconds / 3600.0)
        recent_run = bool(log_age_hours is not None and log_age_hours <= max_allowed_age_hours)

        jobs.append(
            SchedulerJobHealth(
                label=label,
                plist=str(plist_path.name),
                installed=installed,
                loaded=loaded,
                expected_interval_hours=round(interval_hours, 1),
                max_allowed_age_hours=round(max_allowed_age_hours, 1),
                log_path=str(log_path) if log_path else None,
                log_exists=log_exists,
                log_age_hours=round(log_age_hours, 1) if log_age_hours is not None else None,
                recent_run=recent_run,
            )
        )

    return jobs


def _print_report(jobs: list[SchedulerJobHealth]) -> None:
    print("SCHEDULER HEALTH")
    print("=" * 90)
    if platform.system() != "Darwin":
        print("Platform is not macOS; launchd checks are not applicable.")
        print()

    if not jobs:
        print("No launchd plists found.")
        return

    print(
        f"{'Label':38s} {'Installed':10s} {'Loaded':8s} {'Recent':8s} {'Log Age(h)':10s} {'Max Age(h)':10s}"
    )
    print("-" * 90)
    for job in jobs:
        loaded = "n/a" if job.loaded is None else ("yes" if job.loaded else "no")
        age = "-" if job.log_age_hours is None else f"{job.log_age_hours:.1f}"
        print(
            f"{job.label[:38]:38s} "
            f"{'yes' if job.installed else 'no':10s} "
            f"{loaded:8s} "
            f"{'yes' if job.recent_run else 'no':8s} "
            f"{age:10s} "
            f"{job.max_allowed_age_hours:10.1f}"
        )

    failures = [
        job for job in jobs
        if not job.installed or (job.loaded is False) or not job.recent_run
    ]
    print("-" * 90)
    print(f"Jobs: {len(jobs)} | Healthy: {len(jobs) - len(failures)} | Unhealthy: {len(failures)}")


def evaluate_scheduler_health(jobs: list[SchedulerJobHealth]) -> bool:
    """Return True when all jobs are healthy (Darwin-only strict criteria)."""
    if platform.system() != "Darwin":
        return True
    return all(
        job.installed and job.loaded is True and job.recent_run
        for job in jobs
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Launchd scheduler health audit")
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when unhealthy")
    parser.add_argument(
        "--max-age-multiplier",
        type=float,
        default=2.0,
        help="Allowed log age multiplier vs schedule interval (default: 2.0)",
    )
    args = parser.parse_args()

    jobs = collect_scheduler_health(max_age_multiplier=args.max_age_multiplier)

    if args.json:
        payload = {
            "platform": platform.system(),
            "healthy": evaluate_scheduler_health(jobs),
            "jobs": [asdict(job) for job in jobs],
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        _print_report(jobs)

    if args.strict and not evaluate_scheduler_health(jobs):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
