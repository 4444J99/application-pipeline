"""Tests for scripts/blind_spot_tracker.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from blind_spot_tracker import (
    compute_progress,
    get_actionable_items,
    get_blind_spots,
    map_spot_to_actions,
)

# --- Fixtures ---

def _make_blind_spots(total=15, completed=3, categories=None, urgent=None):
    """Build a blind_spots dict matching score_blindspots() return shape."""
    if categories is None:
        categories = {
            "Legal & Financial": [
                ("83(b) election filed within 30 days", False, "URGENT: 30-day window", True),
                ("IP assignment agreements signed", False, "", False),
                ("D&O insurance ($125/month)", False, "$125/month early is cheap", False),
                ("Delaware franchise tax: Assumed Par Value method", False, "Can be $400K+", False),
            ],
            "Health & Sustainability": [
                ("Founder burnout awareness (73% prevalence)", True, "Ongoing", False),
                ("Structured breaks scheduled", True, "Calendar non-negotiable time off", False),
                ("Peer support group", False, "YPO, Founder Collective, local groups", False),
                ("Professional support (therapist/coach)", False, "Before crisis, not after", False),
            ],
            "Strategic": [
                ("Warm intro audit (200+ unrealized paths)", False, "Map paths before cold outreach", False),
                ("Documentation as leverage", False, "Public writing generates inbound", False),
                ("Open source strategy", True, "Contributor pipeline doubles as hiring pipeline", False),
                ("Academic partnerships (STTR requires)", False, "Valuable for credibility", False),
                ("Disability grants (least competitive)", False, "Prioritize if applicable", False),
                ("Climate/ESG framing ($62.6B PE market)", False, "Opens additional funding channels", False),
                ("EU AI Act compliance as moat", False, "Compliance creates defensibility", False),
            ],
        }
    if urgent is None:
        urgent = [("Legal & Financial", "83(b) election filed within 30 days", "URGENT: 30-day window")]
    return {
        "categories": categories,
        "total": total,
        "completed": completed,
        "urgent": urgent,
    }


def _make_entries(n=10, submitted=3):
    """Build a minimal list of pipeline entry dicts."""
    entries = []
    for i in range(n):
        status = "submitted" if i < submitted else "drafting"
        entries.append({"id": f"entry-{i}", "status": status})
    return entries


# --- get_blind_spots ---

def test_get_blind_spots_returns_dict():
    result = get_blind_spots()
    assert isinstance(result, dict)


def test_get_blind_spots_has_categories():
    result = get_blind_spots()
    assert "categories" in result


def test_get_blind_spots_has_total():
    result = get_blind_spots()
    assert "total" in result
    assert "completed" in result
    assert isinstance(result["total"], int)
    assert isinstance(result["completed"], int)


def test_get_blind_spots_total_ge_completed():
    """Total should always be >= completed."""
    result = get_blind_spots()
    assert result["total"] >= result["completed"]


# --- compute_progress ---

def test_compute_progress_full():
    """All completed -> 100%."""
    bs = _make_blind_spots(total=10, completed=10)
    progress = compute_progress(bs)
    assert progress["pct"] == 100
    assert progress["completed"] == 10
    assert progress["total"] == 10


def test_compute_progress_empty():
    """0/0 -> 0%."""
    bs = _make_blind_spots(total=0, completed=0)
    progress = compute_progress(bs)
    assert progress["pct"] == 0


def test_compute_progress_partial():
    """3/15 -> 20%."""
    bs = _make_blind_spots(total=15, completed=3)
    progress = compute_progress(bs)
    assert progress["pct"] == 20


def test_compute_progress_bar_format():
    """Bar string contains total and completed count."""
    bs = _make_blind_spots(total=15, completed=3)
    progress = compute_progress(bs)
    bar = progress["bar"]
    assert "3" in bar
    assert "15" in bar
    assert "[" in bar
    assert "]" in bar


def test_compute_progress_bar_full_filled():
    """When 100% complete, bar should be all filled blocks."""
    bs = _make_blind_spots(total=5, completed=5)
    progress = compute_progress(bs)
    # Should contain 10 filled blocks between [ and ]
    assert "\u2588" * 10 in progress["bar"]


# --- map_spot_to_actions ---

def test_map_spot_to_actions_returns_list():
    entries = _make_entries()
    result = map_spot_to_actions("83(b) election filed within 30 days", entries)
    assert isinstance(result, list)
    assert len(result) > 0


def test_map_spot_to_actions_has_required_fields():
    """Each action dict must have spot, action, category, pipeline_relevant."""
    entries = _make_entries()
    result = map_spot_to_actions("Warm intro audit (200+ unrealized paths)", entries)
    for action in result:
        assert "spot" in action
        assert "action" in action
        assert "category" in action
        assert "pipeline_relevant" in action


def test_map_spot_to_actions_legal():
    """Legal spots (83b, IP assignment, D&O) should be flagged as NOT pipeline-relevant."""
    entries = _make_entries()
    for spot_name in [
        "83(b) election filed within 30 days",
        "IP assignment agreements signed",
        "D&O insurance ($125/month)",
    ]:
        result = map_spot_to_actions(spot_name, entries)
        assert len(result) > 0
        for action in result:
            assert action["pipeline_relevant"] is False, f"{spot_name} should not be pipeline-relevant"


def test_map_spot_to_actions_strategic():
    """Strategic spots like warm intro audit and documentation are pipeline-relevant."""
    entries = _make_entries()
    for spot_name in [
        "Warm intro audit (200+ unrealized paths)",
        "Documentation as leverage",
        "Open source strategy",
    ]:
        result = map_spot_to_actions(spot_name, entries)
        assert len(result) > 0
        has_pipeline = any(a["pipeline_relevant"] for a in result)
        assert has_pipeline, f"{spot_name} should have pipeline-relevant action"


def test_map_spot_to_actions_submitted_count():
    """Warm intro audit action should reflect the count of submitted entries."""
    entries = _make_entries(n=20, submitted=7)
    result = map_spot_to_actions("Warm intro audit (200+ unrealized paths)", entries)
    assert any("7" in a["action"] for a in result), "Should include submitted entry count"


def test_map_spot_to_actions_entries_count():
    """Documentation action should reflect total entry count."""
    entries = _make_entries(n=25, submitted=5)
    result = map_spot_to_actions("Documentation as leverage", entries)
    assert any("25" in a["action"] for a in result), "Should include total entry count"


def test_map_spot_to_actions_unknown_spot():
    """Unknown spot names get a generic fallback action."""
    entries = _make_entries()
    result = map_spot_to_actions("Some unknown blind spot XYZ", entries)
    assert len(result) == 1
    assert result[0]["pipeline_relevant"] is False


# --- get_actionable_items ---

def test_get_actionable_items_returns_list():
    bs = _make_blind_spots()
    entries = _make_entries()
    result = get_actionable_items(bs, entries)
    assert isinstance(result, list)


def test_get_actionable_items_excludes_completed():
    """Completed items should not appear in actionable list."""
    bs = _make_blind_spots(
        total=2,
        completed=2,
        categories={
            "Strategic": [
                ("Open source strategy", True, "", False),
                ("Warm intro audit (200+ unrealized paths)", True, "", False),
            ],
        },
        urgent=[],
    )
    entries = _make_entries()
    result = get_actionable_items(bs, entries)
    assert len(result) == 0, "All-complete categories should yield no actionable items"


def test_get_actionable_items_only_pipeline_relevant():
    """Actionable items should only include pipeline-relevant actions."""
    bs = _make_blind_spots()
    entries = _make_entries()
    result = get_actionable_items(bs, entries)
    for item in result:
        assert item["pipeline_relevant"] is True


# --- show_tracker (output test) ---

def test_show_tracker_prints_output(capsys):
    """show_tracker should print a non-empty report to stdout."""
    from blind_spot_tracker import show_tracker

    bs = _make_blind_spots()
    entries = _make_entries()
    show_tracker(bs, entries)
    captured = capsys.readouterr()
    assert "BLIND SPOT TRACKER" in captured.out
    assert "Progress:" in captured.out
    assert len(captured.out) > 100, "Report should have substantial content"


# --- 15/15 achievement tests ---

def test_all_blind_spots_addressed_with_current_profile():
    """With actual startup-profile.yaml, all 15 blind spots should be addressed."""
    result = get_blind_spots()
    assert result["completed"] == result["total"], (
        f"Expected {result['total']}/{result['total']} blind spots addressed, "
        f"got {result['completed']}/{result['total']}"
    )


def test_progress_bar_shows_100_percent():
    """Progress should show 100% when all spots are addressed."""
    result = get_blind_spots()
    progress = compute_progress(result)
    assert progress["pct"] == 100


def test_no_actionable_items_when_all_complete():
    """When all blind spots are addressed, there should be no actionable items."""
    result = get_blind_spots()
    entries = _make_entries()
    actionable = get_actionable_items(result, entries)
    assert len(actionable) == 0, f"Expected 0 actionable items, got {len(actionable)}"
