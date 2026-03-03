"""Tests for pipeline state query functions."""

import sys
from pathlib import Path

# Ensure scripts dir is in path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from pipeline_lib import can_advance, is_actionable, is_deferred


class TestStateQueries:
    """Test state machine query functions."""

    def test_is_actionable_research(self):
        """Research status is actionable."""
        entry = {"id": "test", "status": "research"}
        assert is_actionable(entry) is True

    def test_is_actionable_qualified(self):
        """Qualified status is actionable."""
        entry = {"id": "test", "status": "qualified"}
        assert is_actionable(entry) is True

    def test_is_actionable_drafting(self):
        """Drafting status is actionable."""
        entry = {"id": "test", "status": "drafting"}
        assert is_actionable(entry) is True

    def test_is_actionable_staged(self):
        """Staged status is actionable."""
        entry = {"id": "test", "status": "staged"}
        assert is_actionable(entry) is True

    def test_is_actionable_submitted(self):
        """Submitted status is not actionable."""
        entry = {"id": "test", "status": "submitted"}
        assert is_actionable(entry) is False

    def test_is_actionable_deferred(self):
        """Deferred status is not actionable."""
        entry = {"id": "test", "status": "deferred"}
        assert is_actionable(entry) is False

    def test_is_deferred_with_deferral(self):
        """Entry with deferred status and deferral dict is deferred."""
        entry = {
            "id": "test",
            "status": "deferred",
            "deferral": {"reason": "portal_closed", "resume_date": "2026-04-01"},
        }
        assert is_deferred(entry) is True

    def test_is_deferred_without_deferral(self):
        """Entry with deferred status but no deferral dict is not deferred."""
        entry = {"id": "test", "status": "deferred"}
        assert is_deferred(entry) is False

    def test_is_deferred_other_status(self):
        """Non-deferred statuses are not deferred."""
        for status in ["research", "qualified", "staged", "submitted"]:
            entry = {"id": "test", "status": status}
            assert is_deferred(entry) is False

    def test_can_advance_forward(self):
        """Forward transitions are allowed."""
        entry = {"id": "test", "status": "research"}
        can, reason = can_advance(entry, "qualified")
        assert can is True
        assert "can advance" in reason.lower()

    def test_can_advance_backward_blocked(self):
        """Backward transitions are blocked."""
        entry = {"id": "test", "status": "qualified"}
        can, reason = can_advance(entry, "research")
        assert can is False
        assert "cannot advance backward" in reason.lower()

    def test_can_advance_auto_next(self):
        """Auto-advance to next status is allowed."""
        entry = {"id": "test", "status": "research"}
        can, reason = can_advance(entry)  # No target_status
        assert can is True
        assert "auto-advance" in reason.lower()
        assert "qualified" in reason

    def test_can_advance_deferred_blocked(self):
        """Deferred entries cannot advance."""
        entry = {
            "id": "test",
            "status": "deferred",
            "deferral": {"reason": "portal_closed"},
        }
        can, reason = can_advance(entry)
        assert can is False
        assert "deferred" in reason.lower()

    def test_can_advance_terminal_blocked(self):
        """Terminal outcomes cannot advance."""
        for terminal in ["accepted", "rejected", "withdrawn", "expired"]:
            entry = {"id": "test", "status": terminal}
            can, reason = can_advance(entry)
            assert can is False
            assert "terminal" in reason.lower()

    def test_can_advance_unknown_status(self):
        """Unknown status returns error."""
        entry = {"id": "test", "status": "invalid_status"}
        can, reason = can_advance(entry)
        assert can is False
        assert "unknown" in reason.lower()

    def test_can_advance_from_final_status(self):
        """Final actionable status cannot auto-advance."""
        entry = {"id": "test", "status": "submitted"}
        can, reason = can_advance(entry)
        assert can is False
        assert "final" in reason.lower() or "cannot" in reason.lower()
