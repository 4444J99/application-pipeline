"""Network proximity scoring extracted from score.py."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from pipeline_lib import parse_date

_NETWORK_DECAY = {
    "response_fresh": 30,
    "response_aging": 90,
    "response_stale": 180,
    "outreach_stale": 60,
}


def _days_since(date_str: str | None) -> int | None:
    """Return days since a date string, or None if unparseable/missing."""
    if not date_str:
        return None
    try:
        parsed = parse_date(str(date_str))
        if parsed:
            return (date.today() - parsed).days
    except Exception:
        pass
    return None


def score_network_proximity(entry: dict, all_entries: list[dict] | None = None) -> int:
    """Score network proximity (1-10) based on relationship signals."""
    score = 1

    network = entry.get("network") or {}
    if isinstance(network, dict):
        strength = network.get("relationship_strength", "cold")
        strength_map = {
            "cold": 1,
            "acquaintance": 4,
            "warm": 7,
            "strong": 9,
            "internal": 10,
        }
        score = max(score, strength_map.get(strength, 1))

    conversion = entry.get("conversion") or {}
    if isinstance(conversion, dict) and conversion.get("channel") == "referral":
        score = max(score, 8)

    follow_ups = entry.get("follow_up") or []
    if isinstance(follow_ups, list):
        for follow_up in follow_ups:
            if not isinstance(follow_up, dict):
                continue
            if follow_up.get("response") not in ("replied", "referred"):
                continue
            follow_date = follow_up.get("date") or follow_up.get("response_date")
            age = _days_since(follow_date)
            if age is None:
                score = max(score, 7)
            elif age <= _NETWORK_DECAY["response_fresh"]:
                score = max(score, 7)
            elif age <= _NETWORK_DECAY["response_aging"]:
                score = max(score, 5)
            elif age <= _NETWORK_DECAY["response_stale"]:
                score = max(score, 3)

    if isinstance(network, dict):
        mutual = network.get("mutual_connections", 0)
        if isinstance(mutual, (int, float)) and mutual >= 5:
            score = max(score, 5)

    outreach = entry.get("outreach") or []
    if isinstance(outreach, list):
        done_count = 0
        for outreach_item in outreach:
            if not isinstance(outreach_item, dict) or outreach_item.get("status") != "done":
                continue
            outreach_date = outreach_item.get("date") or outreach_item.get("completed_date")
            age = _days_since(outreach_date)
            if age is not None and age > _NETWORK_DECAY["outreach_stale"]:
                continue
            done_count += 1
        if done_count >= 2:
            score = max(score, 5)
        elif done_count >= 1:
            score = max(score, 4)

    if all_entries:
        org = (entry.get("target") or {}).get("organization", "")
        if org:
            org_count = sum(
                1
                for candidate in all_entries
                if (candidate.get("target") or {}).get("organization") == org
                and candidate.get("id") != entry.get("id")
            )
            if org_count >= 3:
                score = max(score, 4)
            elif org_count >= 1:
                score = max(score, 3)

    return max(1, min(10, score))


def _log_network_change(entry_id: str, old_network: int, new_network: int, filepath: Path):
    """Log signal-action when network_proximity score changes."""
    if old_network == new_network:
        return
    try:
        from log_signal_action import log_signal_action

        log_signal_action(
            signal_id=f"net-{entry_id}",
            signal_type="network_change",
            description=f"network_proximity {old_network} -> {new_network}",
            action=f"Score updated in {filepath.name}",
            entry_id=entry_id,
        )
    except Exception:
        pass
