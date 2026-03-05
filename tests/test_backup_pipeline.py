"""Tests for scripts/backup_pipeline.py."""

import os
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import backup_pipeline as backup_mod


def test_list_backups_sorts_newest_first(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    names = [
        "pipeline-backup-20250101-000001.tar.gz",
        "pipeline-backup-20250103-000001.tar.gz",
        "pipeline-backup-20250102-000001.tar.gz",
    ]
    for name in names:
        (tmp_path / name).write_text("backup")

    backups = backup_mod.list_backups()
    assert [path.name for path in backups] == sorted(names, reverse=True)


def test_cleanup_old_backups_removes_only_old_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    old_backup = tmp_path / "pipeline-backup-20240101-000000.tar.gz"
    new_backup = tmp_path / "pipeline-backup-20260101-000000.tar.gz"
    old_backup.write_text("old")
    new_backup.write_text("new")

    now = time.time()
    old_time = now - (5 * 24 * 60 * 60)
    os.utime(old_backup, (old_time, old_time))
    os.utime(new_backup, (now, now))

    backup_mod.cleanup_old_backups(keep_days=2)
    assert not old_backup.exists()
    assert new_backup.exists()


def test_restore_pipeline_missing_file_exits(tmp_path, monkeypatch):
    monkeypatch.setattr(backup_mod, "REPO_ROOT", tmp_path)
    with pytest.raises(SystemExit):
        backup_mod.restore_pipeline(str(tmp_path / "missing-backup.tar.gz"))
