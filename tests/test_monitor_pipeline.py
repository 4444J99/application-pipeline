"""Tests for scripts/monitor_pipeline.py."""

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../scripts")))

from monitor_pipeline import (
    STATUS_CRITICAL,
    STATUS_OK,
    STATUS_WARN,
    compute_exit_code,
    find_latest_backup,
    run_monitor_checks,
)


def _touch_file(path: Path, days_old: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x")
    ts = time.time() - int(days_old * 86400)
    os.utime(path, (ts, ts))


def test_find_latest_backup_across_root_and_backups(tmp_path):
    old_backup = tmp_path / "pipeline-backup-old.tar.gz"
    new_backup = tmp_path / "backups" / "pipeline-backup-new.tar.gz"
    _touch_file(old_backup, days_old=10)
    _touch_file(new_backup, days_old=1)

    latest = find_latest_backup(tmp_path)
    assert latest is not None
    assert latest.name == "pipeline-backup-new.tar.gz"


def test_run_monitor_checks_flags_missing_backup(tmp_path):
    signals = tmp_path / "signals"
    _touch_file(signals / "conversion-log.yaml", days_old=0.1)
    _touch_file(signals / "agent-actions.yaml", days_old=0.1)
    _touch_file(signals / "standup-log.yaml", days_old=0.1)

    results = run_monitor_checks(
        repo_root=tmp_path,
        signals_dir=signals,
        max_backup_age_days=8,
        max_conversion_age_days=2,
        max_agent_log_age_days=4,
        max_standup_age_days=3,
    )
    backup_row = next(r for r in results if r["name"] == "backup")
    assert backup_row["status"] == STATUS_CRITICAL


def test_run_monitor_checks_warns_on_stale_conversion_log(tmp_path):
    signals = tmp_path / "signals"
    _touch_file(tmp_path / "pipeline-backup-1.tar.gz", days_old=1)
    _touch_file(signals / "conversion-log.yaml", days_old=3)
    _touch_file(signals / "agent-actions.yaml", days_old=0.2)
    _touch_file(signals / "standup-log.yaml", days_old=0.2)

    results = run_monitor_checks(
        repo_root=tmp_path,
        signals_dir=signals,
        max_backup_age_days=8,
        max_conversion_age_days=2,
        max_agent_log_age_days=4,
        max_standup_age_days=3,
    )
    conv_row = next(r for r in results if r["name"] == "conversion-log")
    backup_row = next(r for r in results if r["name"] == "backup")
    assert conv_row["status"] == STATUS_WARN
    assert backup_row["status"] == STATUS_OK


def test_compute_exit_code_strict_behavior():
    ok_only = [{"status": STATUS_OK}]
    warn = [{"status": STATUS_WARN}]
    critical = [{"status": STATUS_CRITICAL}]

    assert compute_exit_code(ok_only, strict=True) == 0
    assert compute_exit_code(warn, strict=True) == 1
    assert compute_exit_code(critical, strict=True) == 2
    assert compute_exit_code(critical, strict=False) == 0
