"""Tests for scripts/scheduler_health.py."""

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import scheduler_health as sched_mod


def test_expected_interval_hours_daily_and_weekly():
    assert sched_mod._expected_interval_hours({"Hour": 6, "Minute": 0}) == 24.0
    assert sched_mod._expected_interval_hours({"Hour": 2, "Minute": 0, "Weekday": 0}) == 168.0


def test_expected_interval_hours_list_weekdays():
    interval = [{"Hour": 7, "Weekday": 1}, {"Hour": 7, "Weekday": 4}]
    assert sched_mod._expected_interval_hours(interval) == 84.0


def test_evaluate_scheduler_health_non_darwin(monkeypatch):
    monkeypatch.setattr(sched_mod.platform, "system", lambda: "Linux")
    jobs = [
        sched_mod.SchedulerJobHealth(
            label="x",
            plist="x.plist",
            installed=False,
            loaded=None,
            expected_interval_hours=24.0,
            max_allowed_age_hours=48.0,
            log_path=None,
            log_exists=False,
            log_age_hours=None,
            recent_run=False,
        )
    ]
    assert sched_mod.evaluate_scheduler_health(jobs) is True


def test_collect_scheduler_health_recent_run(tmp_path, monkeypatch):
    plist = tmp_path / "com.4jp.pipeline.test.plist"
    plist.write_text("plist")
    log = tmp_path / "pipeline-test.log"
    log.write_text("ok")
    os.utime(log, (time.time(), time.time()))

    agents = tmp_path / "LaunchAgents"
    agents.mkdir()
    (agents / plist.name).write_text("installed")

    monkeypatch.setattr(sched_mod, "USER_LAUNCH_AGENTS", agents)
    monkeypatch.setattr(sched_mod, "_plist_paths", lambda: [plist])
    monkeypatch.setattr(
        sched_mod,
        "_load_plist",
        lambda _path: {
            "Label": "com.4jp.pipeline.test",
            "StartCalendarInterval": {"Hour": 6, "Minute": 0},
            "StandardOutPath": str(log),
        },
    )
    monkeypatch.setattr(sched_mod, "_launchctl_loaded", lambda _label: True)

    jobs = sched_mod.collect_scheduler_health()
    assert len(jobs) == 1
    assert jobs[0].installed is True
    assert jobs[0].loaded is True
    assert jobs[0].recent_run is True


def test_collect_scheduler_health_flags_stale_log(tmp_path, monkeypatch):
    plist = tmp_path / "com.4jp.pipeline.stale.plist"
    plist.write_text("plist")
    log = tmp_path / "pipeline-stale.log"
    log.write_text("old")
    old = time.time() - (200 * 3600)
    os.utime(log, (old, old))

    agents = tmp_path / "LaunchAgents"
    agents.mkdir()
    (agents / plist.name).write_text("installed")

    monkeypatch.setattr(sched_mod, "USER_LAUNCH_AGENTS", agents)
    monkeypatch.setattr(sched_mod, "_plist_paths", lambda: [plist])
    monkeypatch.setattr(
        sched_mod,
        "_load_plist",
        lambda _path: {
            "Label": "com.4jp.pipeline.stale",
            "StartCalendarInterval": {"Hour": 6, "Minute": 0},
            "StandardOutPath": str(log),
        },
    )
    monkeypatch.setattr(sched_mod, "_launchctl_loaded", lambda _label: True)

    jobs = sched_mod.collect_scheduler_health()
    assert jobs[0].recent_run is False
