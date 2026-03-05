"""Entry/date/state utility functions extracted from pipeline_lib."""

from __future__ import annotations

from datetime import date, datetime


def parse_date(date_str: str | date | datetime | None) -> date | None:
    """Parse an ISO date string (YYYY-MM-DD) into a date object."""
    if not date_str:
        return None
    if isinstance(date_str, datetime):
        return date_str.date()
    if isinstance(date_str, date):
        return date_str
    try:
        return datetime.strptime(str(date_str), "%Y-%m-%d").date()
    except ValueError:
        return None


def parse_datetime(date_str: str | date | datetime | None) -> datetime | None:
    """Parse an ISO date string into a datetime object."""
    if not date_str:
        return None
    try:
        return datetime.strptime(str(date_str), "%Y-%m-%d")
    except ValueError:
        return None


def format_amount(amount: dict | None) -> str:
    """Format an amount dict for display."""
    if not amount or not isinstance(amount, dict):
        return "—"
    value = amount.get("value", 0)
    currency = amount.get("currency", "USD")
    if value == 0:
        amount_type = amount.get("type", "")
        if amount_type == "in_kind":
            return "In-kind"
        if amount_type == "variable":
            return "Variable"
        return "—"
    if currency == "EUR":
        return f"EUR {value:,}"
    return f"${value:,}"


def get_effort(entry: dict) -> str:
    """Get effort level from submission, defaulting to 'standard'."""
    submission = entry.get("submission", {})
    if isinstance(submission, dict):
        return submission.get("effort_level", "standard") or "standard"
    return "standard"


def get_score(entry: dict) -> float:
    """Get composite fit score."""
    fit = entry.get("fit", {})
    if isinstance(fit, dict):
        raw = fit.get("score", 0)
        if raw is None:
            return 0.0
        return float(raw)
    return 0.0


def get_deadline(entry: dict) -> tuple[date | None, str]:
    """Return (deadline_date, deadline_type)."""
    deadline = entry.get("deadline", {})
    if not isinstance(deadline, dict):
        return None, "unknown"
    return parse_date(deadline.get("date")), deadline.get("type", "unknown")


def days_until(target_date: date) -> int:
    """Days from today until the given date (negative = past)."""
    return (target_date - date.today()).days


def is_actionable(entry: dict) -> bool:
    """Return True if entry is in an actionable status (can be worked on)."""
    status = entry.get("status", "")
    return status in ("research", "qualified", "drafting", "staged")


def is_deferred(entry: dict) -> bool:
    """Return True if entry is deferred (blocked by external factors)."""
    status = entry.get("status", "")
    deferral = entry.get("deferral")
    return status == "deferred" and isinstance(deferral, dict)


def can_advance(entry: dict, target_status: str | None = None) -> tuple[bool, str]:
    """Check if an entry can advance to target status."""
    current_status = entry.get("status", "")
    entry_id = entry.get("id", "unknown")

    if current_status in ("accepted", "rejected", "withdrawn", "expired", "closed"):
        return False, f"{entry_id}: already in terminal status '{current_status}'"

    if is_deferred(entry):
        return False, f"{entry_id}: deferred (blocked by external factor); re-activate before advancing"

    state_order = ["research", "qualified", "drafting", "staged", "submitted"]
    if current_status not in state_order:
        return False, f"{entry_id}: unknown status '{current_status}'"

    if target_status:
        if target_status not in state_order:
            return False, f"{entry_id}: unknown target status '{target_status}'"

        current_idx = state_order.index(current_status)
        target_idx = state_order.index(target_status)
        if target_idx <= current_idx:
            return False, f"{entry_id}: cannot advance backward from '{current_status}' to '{target_status}'"
        return True, f"{entry_id}: can advance {current_status} → {target_status}"

    current_idx = state_order.index(current_status)
    if current_idx < len(state_order) - 1:
        next_status = state_order[current_idx + 1]
        return True, f"{entry_id}: can auto-advance {current_status} → {next_status}"
    return False, f"{entry_id}: already at final actionable status '{current_status}'"
