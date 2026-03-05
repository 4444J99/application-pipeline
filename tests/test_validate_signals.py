#!/usr/bin/env python3
"""Tests for validate_signals.py — signal YAML schema validation."""

import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))


from validate_signals import (
    AGENT_MODES,
    OUTCOMES,
    SIGNAL_TYPES,
    validate_agent_actions,
    validate_all_signals,
    validate_contacts,
    validate_conversion_log,
    validate_hypotheses,
    validate_referential_integrity,
    validate_signal_actions,
)


@pytest.fixture()
def signals_dir(tmp_path, monkeypatch):
    """Create a temp signals directory and patch SIGNALS_DIR."""
    import validate_signals
    monkeypatch.setattr(validate_signals, "SIGNALS_DIR", tmp_path)
    return tmp_path


def _write_yaml(path, data):
    with open(path, "w") as f:
        yaml.dump(data, f)


def test_signal_actions_valid(signals_dir):
    _write_yaml(signals_dir / "signal-actions.yaml", {
        "actions": [{
            "signal_id": "test-001",
            "signal_type": "hypothesis",
            "description": "Test signal",
            "triggered_action": "advance to drafting",
            "action_date": "2026-03-04",
        }]
    })
    errors = []
    count = validate_signal_actions(errors)
    assert count == 1
    assert errors == []


def test_signal_actions_missing_field(signals_dir):
    _write_yaml(signals_dir / "signal-actions.yaml", {
        "actions": [{"signal_id": "test"}]
    })
    errors = []
    validate_signal_actions(errors)
    assert len(errors) >= 3  # missing description, triggered_action, signal_type, action_date


def test_signal_actions_invalid_type(signals_dir):
    _write_yaml(signals_dir / "signal-actions.yaml", {
        "actions": [{
            "signal_id": "test",
            "signal_type": "invalid_type",
            "description": "Test",
            "triggered_action": "advance",
            "action_date": "2026-03-04",
        }]
    })
    errors = []
    validate_signal_actions(errors)
    assert any("signal_type" in e for e in errors)


def test_conversion_log_valid(signals_dir):
    _write_yaml(signals_dir / "conversion-log.yaml", {
        "entries": [{
            "id": "anthropic-se",
            "submitted": "2026-02-24",
            "track": "job",
            "outcome": None,
        }]
    })
    errors = []
    count = validate_conversion_log(errors)
    assert count == 1
    assert errors == []


def test_conversion_log_invalid_outcome(signals_dir):
    _write_yaml(signals_dir / "conversion-log.yaml", {
        "entries": [{
            "id": "test",
            "submitted": "2026-02-24",
            "track": "job",
            "outcome": "invalid_outcome",
        }]
    })
    errors = []
    validate_conversion_log(errors)
    assert any("outcome" in e for e in errors)


def test_hypotheses_valid(signals_dir):
    _write_yaml(signals_dir / "hypotheses.yaml", {
        "hypotheses": [{
            "entry_id": "anthropic-se",
            "category": "timing",
        }]
    })
    errors = []
    count = validate_hypotheses(errors)
    assert count == 1
    assert errors == []


def test_agent_actions_valid(signals_dir):
    _write_yaml(signals_dir / "agent-actions.yaml", {
        "runs": [{
            "timestamp": "2026-03-03T07:00:00",
            "mode": "execute",
        }]
    })
    errors = []
    count = validate_agent_actions(errors)
    assert count == 1
    assert errors == []


def test_missing_file(signals_dir):
    errors = []
    count = validate_signal_actions(errors)
    assert count == 0
    assert any("missing" in e for e in errors)


def test_validate_all_returns_stats(signals_dir):
    # Create minimal valid files
    _write_yaml(signals_dir / "signal-actions.yaml", {"actions": []})
    _write_yaml(signals_dir / "conversion-log.yaml", {"entries": []})
    _write_yaml(signals_dir / "hypotheses.yaml", {"hypotheses": []})
    _write_yaml(signals_dir / "agent-actions.yaml", {"runs": []})
    errors, stats = validate_all_signals()
    assert isinstance(errors, list)
    assert isinstance(stats, dict)
    assert "signal-actions" in stats


def test_constants_populated():
    assert len(SIGNAL_TYPES) >= 5
    assert None in OUTCOMES
    assert "execute" in AGENT_MODES


# --- Referential integrity tests ---


def test_referential_integrity_valid(signals_dir, tmp_path, monkeypatch):
    """Valid references produce no errors."""
    import validate_signals

    # Create a fake pipeline dir with an entry
    pipeline_dir = tmp_path / "pipeline" / "active"
    pipeline_dir.mkdir(parents=True)
    _write_yaml(pipeline_dir / "test-entry.yaml", {"id": "test-entry", "status": "staged"})
    monkeypatch.setattr(validate_signals, "ALL_PIPELINE_DIRS_WITH_POOL", [pipeline_dir])

    _write_yaml(signals_dir / "conversion-log.yaml", {
        "entries": [{"id": "test-entry", "submitted": "2026-03-01", "track": "job"}]
    })
    _write_yaml(signals_dir / "hypotheses.yaml", {
        "hypotheses": [{"entry_id": "test-entry", "category": "timing"}]
    })
    errors = []
    dangling = validate_referential_integrity(errors)
    assert dangling == 0
    assert errors == []


def test_referential_integrity_dangling(signals_dir, tmp_path, monkeypatch):
    """Dangling references produce errors."""
    import validate_signals

    pipeline_dir = tmp_path / "pipeline" / "active"
    pipeline_dir.mkdir(parents=True)
    monkeypatch.setattr(validate_signals, "ALL_PIPELINE_DIRS_WITH_POOL", [pipeline_dir])

    _write_yaml(signals_dir / "conversion-log.yaml", {
        "entries": [{"id": "nonexistent", "submitted": "2026-03-01", "track": "job"}]
    })
    _write_yaml(signals_dir / "hypotheses.yaml", {
        "hypotheses": [{"id": "also-missing", "category": "timing"}]
    })
    errors = []
    dangling = validate_referential_integrity(errors)
    assert dangling == 2
    assert any("nonexistent" in e for e in errors)
    assert any("also-missing" in e for e in errors)


# --- Contacts validation tests ---


def test_contacts_valid(signals_dir):
    _write_yaml(signals_dir / "contacts.yaml", {
        "contacts": [{
            "name": "Jane Doe",
            "channel": "linkedin",
            "interactions": [{"date": "2026-03-01", "type": "connect", "note": "DM sent"}],
        }]
    })
    errors = []
    count = validate_contacts(errors)
    assert count == 1
    assert errors == []


def test_contacts_invalid_channel(signals_dir):
    _write_yaml(signals_dir / "contacts.yaml", {
        "contacts": [{"name": "Jane", "channel": "fax"}]
    })
    errors = []
    validate_contacts(errors)
    assert any("channel" in e for e in errors)


def test_contacts_missing_name(signals_dir):
    _write_yaml(signals_dir / "contacts.yaml", {
        "contacts": [{"channel": "email"}]
    })
    errors = []
    validate_contacts(errors)
    assert any("name" in e for e in errors)


def test_contacts_optional_missing_file(signals_dir):
    errors = []
    count = validate_contacts(errors)
    assert count == 0
    assert errors == []


def test_contacts_bad_date(signals_dir):
    _write_yaml(signals_dir / "contacts.yaml", {
        "contacts": [{
            "name": "Bob",
            "interactions": [{"date": "not-a-date", "type": "call"}],
        }]
    })
    errors = []
    validate_contacts(errors)
    assert any("not-a-date" in e for e in errors)
