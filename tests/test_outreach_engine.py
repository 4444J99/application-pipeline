"""Tests for outreach_engine.py — outreach template generation and tracking."""

import json
import sys
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from outreach_engine import (
    PROTOCOL,
    OutreachAction,
    OutreachResult,
    _log_outreach_actions,
    _save_outreach_templates,
    prepare_outreach,
)


def _make_entry(
    entry_id="test-entry",
    status="submitted",
    portal="greenhouse",
):
    return {
        "id": entry_id,
        "status": status,
        "target": {
            "organization": "Test Org",
            "position": "Engineer",
            "portal": portal,
            "application_url": "https://example.com",
        },
        "submission": {},
    }


class TestProtocol:
    def test_protocol_has_required_keys(self):
        assert "connect" in PROTOCOL
        assert "email" in PROTOCOL
        assert "followup" in PROTOCOL

    def test_protocol_days_ascending(self):
        days = [PROTOCOL[k]["day"] for k in ("connect", "email", "followup")]
        assert days == sorted(days)

    def test_each_has_channel(self):
        for key, val in PROTOCOL.items():
            assert "channel" in val
            assert "day" in val


class TestSaveOutreachTemplates:
    def test_dry_run_returns_zero(self):
        count = _save_outreach_templates("test", {"connect": {}}, dry_run=True)
        assert count == 0

    def test_saves_template_files(self, tmp_path):
        templates = {
            "connect": {"template": "Hi there", "platform": "linkedin"},
            "email": {"template": "Dear hiring manager", "subject": "Interest"},
        }
        with patch("outreach_engine.OUTREACH_DIR", tmp_path):
            count = _save_outreach_templates("entry-1", templates, dry_run=False)
        assert count == 2
        assert (tmp_path / "entry-1" / "connect.md").exists()
        assert (tmp_path / "entry-1" / "email.md").exists()
        content = (tmp_path / "entry-1" / "email.md").read_text()
        assert "Subject:" in content
        assert "Dear hiring manager" in content

    def test_creates_subdirectory(self, tmp_path):
        with patch("outreach_engine.OUTREACH_DIR", tmp_path):
            _save_outreach_templates("new-dir", {"x": {"template": "t"}}, dry_run=False)
        assert (tmp_path / "new-dir").is_dir()


class TestLogOutreachActions:
    def test_dry_run_no_write(self, tmp_path):
        log_path = tmp_path / "outreach-log.yaml"
        with patch("outreach_engine.OUTREACH_LOG_PATH", log_path), \
             patch("outreach_engine.SIGNALS_DIR", tmp_path):
            _log_outreach_actions(
                [OutreachAction("e1", "connect", "linkedin", "Hi", "2026-03-14", "prepared")],
                dry_run=True,
            )
        assert not log_path.exists()

    def test_empty_actions_no_write(self, tmp_path):
        log_path = tmp_path / "outreach-log.yaml"
        with patch("outreach_engine.OUTREACH_LOG_PATH", log_path), \
             patch("outreach_engine.SIGNALS_DIR", tmp_path):
            _log_outreach_actions([], dry_run=False)
        assert not log_path.exists()

    def test_appends_to_log(self, tmp_path):
        log_path = tmp_path / "outreach-log.yaml"
        log_path.write_text(yaml.dump([{"entry_id": "old", "action": "connect"}]))
        with patch("outreach_engine.OUTREACH_LOG_PATH", log_path), \
             patch("outreach_engine.SIGNALS_DIR", tmp_path):
            _log_outreach_actions(
                [OutreachAction("e2", "email", "email", "Hello", "2026-03-14", "prepared")],
                dry_run=False,
            )
        data = yaml.safe_load(log_path.read_text())
        assert len(data) == 2
        assert data[1]["entry_id"] == "e2"

    def test_creates_new_log(self, tmp_path):
        log_path = tmp_path / "outreach-log.yaml"
        with patch("outreach_engine.OUTREACH_LOG_PATH", log_path), \
             patch("outreach_engine.SIGNALS_DIR", tmp_path):
            _log_outreach_actions(
                [OutreachAction("e1", "connect", "linkedin", "Hi", "2026-03-14", "prepared")],
                dry_run=False,
            )
        assert log_path.exists()
        data = yaml.safe_load(log_path.read_text())
        assert len(data) == 1


class TestPrepareOutreach:
    def test_filters_non_submitted(self):
        entries = [_make_entry(status="qualified")]
        with patch("outreach_engine.load_entries", return_value=entries):
            result = prepare_outreach(dry_run=True)
        assert len(result.entries_processed) == 0

    def test_processes_submitted_entries(self):
        entries = [_make_entry(entry_id="e1")]
        templates = {
            "templates": {
                "connect": {"template": "Hi"},
                "email": {"template": "Hello"},
            }
        }
        with patch("outreach_engine.load_entries", return_value=entries), \
             patch("outreach_engine.generate_all_templates", return_value=templates):
            result = prepare_outreach(dry_run=True)
        assert "e1" in result.entries_processed
        assert result.templates_generated == 2

    def test_processes_staged_entries(self):
        entries = [_make_entry(entry_id="e1", status="staged")]
        templates = {"templates": {"connect": {"template": "Hi"}}}
        with patch("outreach_engine.load_entries", return_value=entries), \
             patch("outreach_engine.generate_all_templates", return_value=templates):
            result = prepare_outreach(dry_run=True)
        assert "e1" in result.entries_processed

    def test_filters_by_entry_ids(self):
        entries = [
            _make_entry(entry_id="a"),
            _make_entry(entry_id="b"),
        ]
        templates = {"templates": {"connect": {"template": "Hi"}}}
        with patch("outreach_engine.load_entries", return_value=entries), \
             patch("outreach_engine.generate_all_templates", return_value=templates):
            result = prepare_outreach(entry_ids=["a"], dry_run=True)
        assert "a" in result.entries_processed
        assert "b" not in result.entries_processed

    def test_skips_existing_outreach(self, tmp_path):
        """Entries with existing outreach dir are skipped (unless explicitly targeted)."""
        entries = [_make_entry(entry_id="e1")]
        outreach_dir = tmp_path / "e1"
        outreach_dir.mkdir()
        with patch("outreach_engine.load_entries", return_value=entries), \
             patch("outreach_engine.OUTREACH_DIR", tmp_path):
            result = prepare_outreach(dry_run=True)
        assert len(result.entries_processed) == 0

    def test_explicit_target_overrides_skip(self, tmp_path):
        """Explicitly targeted entries are processed even if outreach exists."""
        entries = [_make_entry(entry_id="e1")]
        outreach_dir = tmp_path / "e1"
        outreach_dir.mkdir()
        templates = {"templates": {"connect": {"template": "Hi"}}}
        with patch("outreach_engine.load_entries", return_value=entries), \
             patch("outreach_engine.OUTREACH_DIR", tmp_path), \
             patch("outreach_engine.generate_all_templates", return_value=templates):
            result = prepare_outreach(entry_ids=["e1"], dry_run=True)
        assert "e1" in result.entries_processed

    def test_creates_action_items(self):
        entries = [_make_entry(entry_id="e1")]
        templates = {
            "templates": {
                "connect": {"template": "Hi"},
                "email": {"template": "Hello", "subject": "Greetings"},
            }
        }
        with patch("outreach_engine.load_entries", return_value=entries), \
             patch("outreach_engine.generate_all_templates", return_value=templates):
            result = prepare_outreach(dry_run=True)
        assert len(result.actions) == 2
        channels = {a.channel for a in result.actions}
        assert "linkedin" in channels
        assert "email" in channels

    def test_error_handling(self):
        entries = [_make_entry(entry_id="bad")]
        with patch("outreach_engine.load_entries", return_value=entries), \
             patch("outreach_engine.generate_all_templates", side_effect=Exception("fail")):
            result = prepare_outreach(dry_run=True)
        assert len(result.errors) == 1
        assert "bad" in result.errors[0]


class TestDataclasses:
    def test_outreach_action_fields(self):
        a = OutreachAction("e1", "connect", "linkedin", "Hi", "2026-03-14", "prepared")
        assert a.entry_id == "e1"
        assert a.status == "prepared"

    def test_outreach_result_defaults(self):
        r = OutreachResult()
        assert r.entries_processed == []
        assert r.templates_generated == 0
        assert r.files_written == 0
        assert r.followup_dates_set == 0

    def test_result_json_serializable(self):
        r = OutreachResult(entries_processed=["a"], templates_generated=3)
        serialized = json.dumps(asdict(r), default=str)
        assert "a" in serialized
        assert "3" in serialized
