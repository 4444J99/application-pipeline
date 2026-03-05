#!/usr/bin/env python3
"""Tests for notify.py — notification dispatcher."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from notify import (
    VALID_EVENTS,
    dispatch_event,
    dispatch_webhook,
    load_config,
    show_config,
)


class TestLoadConfig:
    def test_loads_existing_config(self, tmp_path, monkeypatch):
        import notify
        config_path = tmp_path / "notifications.yaml"
        config_path.write_text(yaml.dump({
            "webhooks": ["https://example.com/hook"],
            "email": {"smtp_host": "smtp.test.com", "sender": "test@test.com"},
            "subscriptions": {"weekly_brief": ["webhook"]},
        }))
        monkeypatch.setattr(notify, "CONFIG_PATH", config_path)
        config = load_config()
        assert config["webhooks"] == ["https://example.com/hook"]
        assert config["subscriptions"]["weekly_brief"] == ["webhook"]

    def test_missing_config_returns_defaults(self, tmp_path, monkeypatch):
        import notify
        monkeypatch.setattr(notify, "CONFIG_PATH", tmp_path / "nonexistent.yaml")
        config = load_config()
        assert config["webhooks"] == []
        assert config["subscriptions"] == {}


class TestDispatchWebhook:
    def test_successful_webhook(self):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch("notify.urllib.request.urlopen", return_value=mock_resp):
            ok, msg = dispatch_webhook({"test": True}, "https://example.com/hook")
        assert ok is True
        assert "200" in msg

    def test_failed_webhook(self):
        import urllib.error
        with patch("notify.urllib.request.urlopen", side_effect=urllib.error.URLError("Connection refused")):
            ok, msg = dispatch_webhook({"test": True}, "https://example.com/hook")
        assert ok is False
        assert "failed" in msg.lower()


class TestDispatchEvent:
    def test_unknown_event(self):
        results = dispatch_event("unknown_event", {})
        assert results[0]["success"] is False
        assert "Unknown" in results[0]["message"]

    def test_no_channels_configured(self, tmp_path, monkeypatch):
        import notify
        config_path = tmp_path / "notifications.yaml"
        config_path.write_text(yaml.dump({
            "webhooks": [],
            "email": {},
            "subscriptions": {"weekly_brief": []},
        }))
        monkeypatch.setattr(notify, "CONFIG_PATH", config_path)
        monkeypatch.setattr(notify, "NOTIFICATION_LOG", tmp_path / "notification-log.yaml")
        results = dispatch_event("weekly_brief", {"summary": "test"})
        assert results[0]["channel"] == "file"
        assert results[0]["success"] is True

    def test_webhook_channel_dispatched(self, tmp_path, monkeypatch):
        import notify
        config_path = tmp_path / "notifications.yaml"
        config_path.write_text(yaml.dump({
            "webhooks": ["https://example.com/hook"],
            "email": {},
            "subscriptions": {"weekly_brief": ["webhook"]},
        }))
        monkeypatch.setattr(notify, "CONFIG_PATH", config_path)

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch("notify.urllib.request.urlopen", return_value=mock_resp):
            results = dispatch_event("weekly_brief", {"summary": "test brief"})
        assert len(results) == 1
        assert results[0]["channel"] == "webhook"
        assert results[0]["success"] is True


class TestValidEvents:
    def test_expected_events_present(self):
        assert "weekly_brief" in VALID_EVENTS
        assert "agent_action" in VALID_EVENTS
        assert "deadline_alert" in VALID_EVENTS
        assert "outcome_received" in VALID_EVENTS
        assert "triage_report" in VALID_EVENTS


class TestShowConfig:
    def test_runs_without_error(self, tmp_path, monkeypatch, capsys):
        import notify
        config_path = tmp_path / "notifications.yaml"
        config_path.write_text(yaml.dump({"webhooks": [], "email": {}, "subscriptions": {}}))
        monkeypatch.setattr(notify, "CONFIG_PATH", config_path)
        show_config()
        output = capsys.readouterr().out
        assert "Notification Configuration" in output
