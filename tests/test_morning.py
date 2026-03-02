"""Tests for scripts/morning.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from morning import (
    capture_output,
    compute_top_action,
    format_digest,
)

# --- capture_output ---


def test_capture_output_captures_print():
    """capture_output captures printed text."""
    def my_fn():
        print("hello world")
        return 42

    result, text = capture_output(my_fn)
    assert result == 42
    assert "hello world" in text


def test_capture_output_with_args():
    """capture_output passes args and kwargs correctly."""
    def my_fn(x, y=10):
        print(f"{x}+{y}")
        return x + y

    result, text = capture_output(my_fn, 5, y=20)
    assert result == 25
    assert "5+20" in text


def test_capture_output_empty_print():
    """capture_output handles functions that print nothing."""
    def silent():
        return "quiet"

    result, text = capture_output(silent)
    assert result == "quiet"
    assert text == ""


# --- compute_top_action ---


def test_top_action_critical_deadline():
    """Critical campaign items take highest priority."""
    health = {"actionable": 5, "total": 50}
    stale = {"expired": 0, "at_risk": 0, "stagnant": 0}
    campaign = "CRITICAL:\n  [8.5] Big Grant  3d  staged\nURGENT:\n  (none)"
    followup = "No actions due."
    action = compute_top_action(health, stale, campaign, followup)
    assert "CRITICAL DEADLINE" in action


def test_top_action_overdue_followup():
    """Overdue follow-ups take second priority."""
    health = {"actionable": 5, "total": 50}
    stale = {"expired": 0, "at_risk": 0, "stagnant": 0}
    campaign = "CRITICAL:\n  (none)\nURGENT:\n  (none)"
    followup = "OVERDUE (3):\n     !!! Acme Inc — Senior Dev\n"
    action = compute_top_action(health, stale, campaign, followup)
    assert "OVERDUE FOLLOW-UP" in action


def test_top_action_expired():
    """Expired entries take priority when no critical/overdue."""
    health = {"actionable": 5, "total": 50}
    stale = {"expired": 2, "at_risk": 0, "stagnant": 0}
    campaign = "CRITICAL:\n  (none)"
    followup = ""
    action = compute_top_action(health, stale, campaign, followup)
    assert "ARCHIVE" in action
    assert "2" in action


def test_top_action_at_risk():
    """At-risk entries flagged when no expired."""
    health = {"actionable": 5, "total": 50}
    stale = {"expired": 0, "at_risk": 3, "stagnant": 0}
    campaign = "CRITICAL:\n  (none)"
    followup = ""
    action = compute_top_action(health, stale, campaign, followup)
    assert "ADVANCE" in action
    assert "3" in action


def test_top_action_stagnant():
    """Stagnant entries flagged when no higher priority."""
    health = {"actionable": 5, "total": 50}
    stale = {"expired": 0, "at_risk": 0, "stagnant": 7}
    campaign = "CRITICAL:\n  (none)"
    followup = ""
    action = compute_top_action(health, stale, campaign, followup)
    assert "REVIEW" in action
    assert "7" in action


def test_top_action_default_pipeline():
    """Default action is to work pipeline when no alerts."""
    health = {"actionable": 10, "total": 50}
    stale = {"expired": 0, "at_risk": 0, "stagnant": 0}
    campaign = "CRITICAL:\n  (none)"
    followup = ""
    action = compute_top_action(health, stale, campaign, followup)
    assert "10 actionable" in action


def test_top_action_empty_pipeline():
    """Clean pipeline suggests sourcing."""
    health = {"actionable": 0, "total": 0}
    stale = {"expired": 0, "at_risk": 0, "stagnant": 0}
    campaign = "CRITICAL:\n  (none)"
    followup = ""
    action = compute_top_action(health, stale, campaign, followup)
    assert "source" in action.lower()


# --- format_digest ---


def test_format_digest_has_header():
    """Digest includes MORNING DIGEST header."""
    digest = format_digest(
        {"total": 10, "actionable": 5, "submitted": 2, "days_since_last_submission": 3},
        "", {"expired": 0, "at_risk": 0, "stagnant": 0}, "",
        "", "", "", "Do something",
    )
    assert "MORNING DIGEST" in digest


def test_format_digest_includes_top_action():
    """Top action appears prominently in digest."""
    digest = format_digest(
        {"total": 10, "actionable": 5, "submitted": 2, "days_since_last_submission": 3},
        "", {"expired": 0, "at_risk": 0, "stagnant": 0}, "",
        "", "", "", "CRITICAL: Submit grant today",
    )
    assert "CRITICAL: Submit grant today" in digest


def test_format_digest_includes_pipeline_stats():
    """Digest shows pipeline counts."""
    digest = format_digest(
        {"total": 100, "actionable": 42, "submitted": 15, "days_since_last_submission": 1},
        "", {"expired": 0, "at_risk": 0, "stagnant": 0}, "",
        "", "", "", "Work pipeline",
    )
    assert "100 total" in digest
    assert "42 actionable" in digest
    assert "15 submitted" in digest


def test_format_digest_shows_alerts():
    """Digest shows alert counts when present."""
    digest = format_digest(
        {"total": 50, "actionable": 20, "submitted": 5, "days_since_last_submission": 2},
        "", {"expired": 1, "at_risk": 2, "stagnant": 3}, "",
        "", "", "", "Fix alerts",
    )
    assert "1 expired" in digest
    assert "2 at-risk" in digest
    assert "3 stagnant" in digest


def test_format_digest_no_alerts_section_when_clean():
    """No alerts section when all staleness counts are zero."""
    digest = format_digest(
        {"total": 50, "actionable": 20, "submitted": 5, "days_since_last_submission": 2},
        "", {"expired": 0, "at_risk": 0, "stagnant": 0}, "",
        "", "", "", "Work pipeline",
    )
    assert "expired" not in digest.lower()
    assert "at-risk" not in digest.lower()
