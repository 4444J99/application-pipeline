"""Tests for agent.py Rule 4 (drafting → staged) enforcement.

Rule 4 requires BOTH:
  - days_left > DRAFTING_STAGED_MIN_DAYS (default 7)
  - score >= _mode_adjusted_threshold(DRAFTING_STAGED_MIN_SCORE) (default 9.0)
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from agent import PipelineAgent


def _make_entry(entry_id="test-entry", status="drafting", score=None, days_ahead=30):
    """Build a minimal pipeline entry dict for Rule 4 testing.

    Args:
        entry_id: Entry identifier.
        status: Pipeline status string.
        score: Value for fit.composite (omit to leave unset).
        days_ahead: Days from today for the deadline date.
    """
    deadline_date = (datetime.now().date() + timedelta(days=days_ahead)).isoformat()
    entry = {
        "id": entry_id,
        "status": status,
        "deadline": {"date": deadline_date, "type": "rolling"},
        "tags": [],
    }
    if score is not None:
        entry["fit"] = {"composite": score}
    return entry


def test_rule4_below_threshold_no_action(monkeypatch):
    """Score 8.0 is below the 9.0 threshold -- no advance action produced."""
    import agent

    monkeypatch.setattr(agent, "can_advance", lambda entry, target: (True, ""))
    monkeypatch.setattr(agent, "_mode_adjusted_threshold", lambda base: base)

    entry = _make_entry(score=8.0, days_ahead=30)
    actions = PipelineAgent(dry_run=True).plan_actions([entry])

    advance_actions = [a for a in actions if a["action"] == "advance" and a.get("to_status") == "staged"]
    assert advance_actions == [], f"Expected no advance to staged, got {advance_actions}"


def test_rule4_at_threshold_advances(monkeypatch):
    """Score exactly 9.0 meets the threshold -- should produce advance to staged."""
    import agent

    monkeypatch.setattr(agent, "can_advance", lambda entry, target: (True, ""))
    monkeypatch.setattr(agent, "_mode_adjusted_threshold", lambda base: base)

    entry = _make_entry(score=9.0, days_ahead=30)
    actions = PipelineAgent(dry_run=True).plan_actions([entry])

    advance_actions = [a for a in actions if a["action"] == "advance" and a.get("to_status") == "staged"]
    assert len(advance_actions) == 1, f"Expected one advance to staged, got {advance_actions}"
    assert advance_actions[0]["entry_id"] == "test-entry"


def test_rule4_missing_score_no_action(monkeypatch):
    """No fit.composite set -- Rule 4 score gate should block advance."""
    import agent

    monkeypatch.setattr(agent, "can_advance", lambda entry, target: (True, ""))
    monkeypatch.setattr(agent, "_mode_adjusted_threshold", lambda base: base)

    entry = _make_entry(score=None, days_ahead=30)
    actions = PipelineAgent(dry_run=True).plan_actions([entry])

    advance_actions = [a for a in actions if a["action"] == "advance" and a.get("to_status") == "staged"]
    assert advance_actions == [], f"Expected no advance to staged, got {advance_actions}"


def test_rule4_insufficient_days_no_action(monkeypatch):
    """Score 9.5 exceeds threshold but only 3 days left (< 7) -- no advance."""
    import agent

    monkeypatch.setattr(agent, "can_advance", lambda entry, target: (True, ""))
    monkeypatch.setattr(agent, "_mode_adjusted_threshold", lambda base: base)

    entry = _make_entry(score=9.5, days_ahead=3)
    actions = PipelineAgent(dry_run=True).plan_actions([entry])

    advance_actions = [a for a in actions if a["action"] == "advance" and a.get("to_status") == "staged"]
    assert advance_actions == [], f"Expected no advance to staged, got {advance_actions}"
