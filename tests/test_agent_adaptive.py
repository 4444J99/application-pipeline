"""Adaptive threshold and channel allocator tests for scripts/agent.py."""

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import agent
from agent import PipelineAgent, compute_channel_allocator


def _entry(entry_id: str, track: str, score: float, outcome: str | None = None, status: str = "research") -> dict:
    return {
        "id": entry_id,
        "track": track,
        "status": status,
        "fit": {"composite": score},
        "outcome": outcome,
        "deadline": {"date": (date.today() + timedelta(days=30)).isoformat(), "type": "hard"},
    }


def test_compute_channel_allocator_prefers_higher_conversion_tracks():
    entries = []
    entries.extend(_entry(f"job-{i}", "job", 9.0, outcome="accepted" if i < 1 else "rejected") for i in range(5))
    entries.extend(_entry(f"grant-{i}", "grant", 9.0, outcome="accepted" if i < 4 else "rejected") for i in range(5))
    entries.extend(_entry(f"fell-{i}", "fellowship", 9.0, outcome="rejected") for i in range(5))

    alloc = compute_channel_allocator(entries, min_samples=3)
    assert alloc["grant"] > alloc["job"]
    assert alloc["job"] > alloc["fellowship"]


def test_plan_actions_applies_channel_allocator_bias(monkeypatch):
    monkeypatch.setattr(agent, "can_advance", lambda entry, target: (True, ""))
    monkeypatch.setattr(agent, "_mode_adjusted_threshold", lambda base: base)
    monkeypatch.setattr(
        agent,
        "compute_feedback_adjustment",
        lambda months=3: {"delta": 0.0, "conversion_rate": 0.1, "hypothesis_accuracy": 50.0, "resolved_hypotheses": 20},
    )
    monkeypatch.setattr(
        agent,
        "compute_channel_allocator",
        lambda entries, min_samples=3: {"grant": 1.2, "job": 0.8, "fellowship": 1.0},
    )

    grant_entry = _entry("grant-entry", "grant", 8.95, status="research")
    job_entry = _entry("job-entry", "job", 8.95, status="research")
    actions = PipelineAgent(dry_run=True).plan_actions([grant_entry, job_entry])
    targets = {a["entry_id"] for a in actions if a["action"] == "advance"}
    assert "grant-entry" in targets
    assert "job-entry" not in targets


def test_plan_actions_applies_feedback_delta(monkeypatch):
    monkeypatch.setattr(agent, "can_advance", lambda entry, target: (True, ""))
    monkeypatch.setattr(agent, "_mode_adjusted_threshold", lambda base: base)
    monkeypatch.setattr(
        agent,
        "compute_feedback_adjustment",
        lambda months=3: {"delta": 0.3, "conversion_rate": 0.05, "hypothesis_accuracy": 40.0, "resolved_hypotheses": 20},
    )
    monkeypatch.setattr(
        agent,
        "compute_channel_allocator",
        lambda entries, min_samples=3: {"grant": 1.0, "job": 1.0, "fellowship": 1.0},
    )

    entry = _entry("tight-entry", "job", 9.1, status="research")
    actions = PipelineAgent(dry_run=True).plan_actions([entry])
    assert [a for a in actions if a["action"] == "advance"] == []
