#!/usr/bin/env python3
"""Pipeline monitoring checks for backup and signal freshness.

Designed for scheduled automation (launchd) and manual spot checks.
"""

import argparse
import time
from pathlib import Path

from pipeline_lib import REPO_ROOT, SIGNALS_DIR

STATUS_OK = "OK"
STATUS_WARN = "WARN"
STATUS_CRITICAL = "CRITICAL"


def _age_days(path: Path, now_ts: float | None = None) -> float:
    """Return file age in days."""
    now_ts = now_ts if now_ts is not None else time.time()
    return (now_ts - path.stat().st_mtime) / 86400.0


def find_latest_backup(repo_root: Path) -> Path | None:
    """Find latest backup in repo root or backups/ directory."""
    candidates = list(repo_root.glob("pipeline-backup-*.tar.gz"))
    backup_dir = repo_root / "backups"
    if backup_dir.exists():
        candidates.extend(backup_dir.glob("pipeline-backup-*.tar.gz"))
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def run_monitor_checks(
    repo_root: Path,
    signals_dir: Path,
    max_backup_age_days: int,
    max_conversion_age_days: int,
    max_agent_log_age_days: int,
    max_standup_age_days: int,
    now_ts: float | None = None,
) -> list[dict]:
    """Run pipeline monitoring checks."""
    results: list[dict] = []

    latest_backup = find_latest_backup(repo_root)
    if not latest_backup:
        results.append(
            {
                "name": "backup",
                "status": STATUS_CRITICAL,
                "detail": "no pipeline backups found",
                "action": "run `python scripts/backup_pipeline.py create`",
            }
        )
    else:
        age = _age_days(latest_backup, now_ts=now_ts)
        if age > max_backup_age_days:
            status = STATUS_CRITICAL
            action = "run backup now and verify weekly launchd job"
        else:
            status = STATUS_OK
            action = ""
        results.append(
            {
                "name": "backup",
                "status": status,
                "detail": f"{latest_backup.name} ({age:.1f}d old)",
                "action": action,
            }
        )

    def _check_signal(
        filename: str,
        name: str,
        max_age_days: int,
        missing_status: str = STATUS_WARN,
        stale_status: str = STATUS_WARN,
    ) -> None:
        path = signals_dir / filename
        if not path.exists():
            results.append(
                {
                    "name": name,
                    "status": missing_status,
                    "detail": "missing",
                    "action": f"create/update {filename}",
                }
            )
            return

        age = _age_days(path, now_ts=now_ts)
        if age > max_age_days:
            status = stale_status
            action = f"refresh {filename} (>{max_age_days}d old)"
        else:
            status = STATUS_OK
            action = ""

        results.append(
            {
                "name": name,
                "status": status,
                "detail": f"{filename} ({age:.1f}d old)",
                "action": action,
            }
        )

    _check_signal(
        filename="conversion-log.yaml",
        name="conversion-log",
        max_age_days=max_conversion_age_days,
        missing_status=STATUS_WARN,
        stale_status=STATUS_WARN,
    )
    _check_signal(
        filename="agent-actions.yaml",
        name="agent-actions",
        max_age_days=max_agent_log_age_days,
        missing_status=STATUS_WARN,
        stale_status=STATUS_WARN,
    )
    _check_signal(
        filename="standup-log.yaml",
        name="standup-log",
        max_age_days=max_standup_age_days,
        missing_status=STATUS_WARN,
        stale_status=STATUS_WARN,
    )

    return results


def compute_exit_code(results: list[dict], strict: bool) -> int:
    """Compute CLI exit code based on result severities."""
    if not strict:
        return 0

    statuses = {r.get("status") for r in results}
    if STATUS_CRITICAL in statuses:
        return 2
    if STATUS_WARN in statuses:
        return 1
    return 0


def print_report(results: list[dict]) -> None:
    """Print monitor output."""
    status_icon = {
        STATUS_OK: "OK",
        STATUS_WARN: "!!",
        STATUS_CRITICAL: "!!",
    }

    print("PIPELINE MONITOR")
    print("=" * 70)
    for row in results:
        status = row["status"]
        icon = status_icon.get(status, "?")
        print(f"{icon:>2} {row['name']:<16} {status:<8} {row['detail']}")
        if row.get("action"):
            print(f"   action: {row['action']}")

    counts = {
        STATUS_OK: sum(1 for r in results if r["status"] == STATUS_OK),
        STATUS_WARN: sum(1 for r in results if r["status"] == STATUS_WARN),
        STATUS_CRITICAL: sum(1 for r in results if r["status"] == STATUS_CRITICAL),
    }
    print("-" * 70)
    print(
        f"Summary: {counts[STATUS_OK]} ok | "
        f"{counts[STATUS_WARN]} warnings | "
        f"{counts[STATUS_CRITICAL]} critical"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Monitor pipeline automation health")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero on warnings/critical checks")
    parser.add_argument("--max-backup-age-days", type=int, default=8)
    parser.add_argument("--max-conversion-age-days", type=int, default=2)
    parser.add_argument("--max-agent-log-age-days", type=int, default=4)
    parser.add_argument("--max-standup-age-days", type=int, default=3)
    args = parser.parse_args()

    results = run_monitor_checks(
        repo_root=REPO_ROOT,
        signals_dir=SIGNALS_DIR,
        max_backup_age_days=args.max_backup_age_days,
        max_conversion_age_days=args.max_conversion_age_days,
        max_agent_log_age_days=args.max_agent_log_age_days,
        max_standup_age_days=args.max_standup_age_days,
    )
    print_report(results)
    raise SystemExit(compute_exit_code(results, strict=args.strict))


if __name__ == "__main__":
    main()
