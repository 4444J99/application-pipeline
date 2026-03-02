"""Tests for scripts/hydrate_followups.py"""

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from hydrate_followups import (
    extract_contact_info,
    generate_schedule,
    get_unhydrated_entries,
    hydrate_entry,
    show_hydration_report,
)

# --- Fixtures ---


def _make_entry(
    entry_id="test-entry-001",
    organization="Test Org",
    portal="greenhouse",
    hiring_contact="",
    recruiter="",
    status="submitted",
    submitted_date=None,
    follow_up=None,
    follow_up_count=0,
    filepath=None,
):
    """Build a minimal pipeline entry dict for hydration tests."""
    target = {
        "organization": organization,
        "portal": portal,
    }
    if hiring_contact:
        target["hiring_contact"] = hiring_contact
    if recruiter:
        target["recruiter"] = recruiter

    timeline = {"researched": "2026-01-01"}
    if submitted_date:
        timeline["submitted"] = submitted_date

    entry = {
        "id": entry_id,
        "status": status,
        "target": target,
        "timeline": timeline,
        "follow_up": follow_up,
        "conversion": {
            "follow_up_count": follow_up_count,
        },
    }
    if filepath:
        entry["_filepath"] = filepath
    return entry


# --- extract_contact_info tests ---


def test_extract_contact_info_full():
    """Entry with all fields returns correct dict."""
    entry = _make_entry(
        organization="Anthropic",
        portal="greenhouse",
        hiring_contact="Jane Doe",
    )
    result = extract_contact_info(entry)
    assert result["organization"] == "Anthropic"
    assert result["contact"] == "Jane Doe"
    assert result["portal"] == "greenhouse"


def test_extract_contact_info_missing():
    """Entry with missing target fields returns empty strings."""
    entry = {"id": "bare-entry", "target": {}}
    result = extract_contact_info(entry)
    assert result["organization"] == ""
    assert result["contact"] == ""
    assert result["portal"] == ""


def test_extract_contact_info_hiring_contact():
    """Uses hiring_contact field when present."""
    entry = _make_entry(hiring_contact="Alice Smith", recruiter="Bob Jones")
    result = extract_contact_info(entry)
    assert result["contact"] == "Alice Smith"


def test_extract_contact_info_recruiter():
    """Falls back to recruiter field when hiring_contact is empty."""
    entry = _make_entry(recruiter="Bob Jones")
    result = extract_contact_info(entry)
    assert result["contact"] == "Bob Jones"


def test_extract_contact_info_no_target():
    """Entry with no target key at all returns empty strings."""
    entry = {"id": "no-target"}
    result = extract_contact_info(entry)
    assert result["organization"] == ""
    assert result["contact"] == ""
    assert result["portal"] == ""


# --- generate_schedule tests ---


def test_generate_schedule_returns_list():
    """generate_schedule returns a list."""
    entry = _make_entry(submitted_date="2026-02-01")
    result = generate_schedule(entry)
    assert isinstance(result, list)


def test_generate_schedule_correct_count():
    """Schedule item count matches PROTOCOL step count."""
    from followup import PROTOCOL

    entry = _make_entry(submitted_date="2026-02-01")
    result = generate_schedule(entry)
    assert len(result) == len(PROTOCOL)


def test_generate_schedule_no_submission_date():
    """Returns empty list for entry with no submission date."""
    entry = _make_entry(submitted_date=None)
    result = generate_schedule(entry)
    assert result == []


def test_generate_schedule_overdue_detection():
    """Old submission date marks all items as overdue."""
    # Submit 60 days ago — all protocol steps should be overdue
    old_date = (date.today() - timedelta(days=60)).isoformat()
    entry = _make_entry(submitted_date=old_date)
    result = generate_schedule(entry)
    assert len(result) > 0
    for item in result:
        assert item["status"] == "overdue", f"{item['type']} should be overdue"


def test_generate_schedule_upcoming_detection():
    """Future submission windows marked as upcoming."""
    # Submit today — protocol steps with day_range starting after day 0
    # should be upcoming (at minimum the later steps)
    today = date.today().isoformat()
    entry = _make_entry(submitted_date=today)
    result = generate_schedule(entry)
    assert len(result) > 0
    # At least the last step (day 14-21) should be upcoming on day 0
    last = result[-1]
    assert last["status"] == "upcoming", f"Last step should be upcoming, got {last['status']}"


def test_generate_schedule_has_required_fields():
    """Each schedule item has all required fields."""
    entry = _make_entry(submitted_date="2026-02-01")
    result = generate_schedule(entry)
    for item in result:
        assert "action" in item
        assert "type" in item
        assert "due_start" in item
        assert "due_end" in item
        assert "status" in item
        assert item["status"] in ("overdue", "pending", "upcoming")


# --- get_unhydrated_entries tests ---


def test_get_unhydrated_entries_returns_list():
    """get_unhydrated_entries returns a list."""
    result = get_unhydrated_entries()
    assert isinstance(result, list)


# --- hydrate_entry tests ---


def test_hydrate_entry_dry_run():
    """Dry run returns summary without modifying files."""
    import tempfile

    # Create a temp YAML file to act as the entry file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        content = (
            "id: test-dry-run\n"
            "status: submitted\n"
            "target:\n"
            "  organization: TestCo\n"
            "  portal: greenhouse\n"
            "timeline:\n"
            f"  submitted: '{(date.today() - timedelta(days=5)).isoformat()}'\n"
            "follow_up: []\n"
            "conversion:\n"
            "  follow_up_count: 0\n"
        )
        f.write(content)
        tmp_path = Path(f.name)

    try:
        entry = _make_entry(
            entry_id="test-dry-run",
            organization="TestCo",
            submitted_date=(date.today() - timedelta(days=5)).isoformat(),
            filepath=tmp_path,
        )
        result = hydrate_entry(entry, dry_run=True)

        assert result is not None
        assert result["id"] == "test-dry-run"
        assert result["organization"] == "TestCo"
        assert result["schedule_items"] > 0

        # Verify file was NOT modified
        after = tmp_path.read_text()
        assert after == content
    finally:
        tmp_path.unlink(missing_ok=True)


def test_hydrate_entry_no_filepath():
    """Entry without filepath returns None."""
    entry = _make_entry(submitted_date="2026-02-01")
    # No _filepath set
    result = hydrate_entry(entry, dry_run=True)
    assert result is None


def test_hydrate_entry_no_submission_date():
    """Entry without submission date returns None."""
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("id: no-date\nstatus: submitted\ntimeline:\n  researched: '2026-01-01'\n")
        tmp_path = Path(f.name)

    try:
        entry = _make_entry(
            entry_id="no-date",
            submitted_date=None,
            filepath=tmp_path,
        )
        result = hydrate_entry(entry, dry_run=True)
        assert result is None
    finally:
        tmp_path.unlink(missing_ok=True)


# --- show_hydration_report tests ---


def test_show_hydration_report_no_entries(capsys):
    """Empty list prints 'all hydrated' message."""
    show_hydration_report([])
    captured = capsys.readouterr()
    assert "hydrated" in captured.out.lower()
    assert "nothing to do" in captured.out.lower()


def test_show_hydration_report_with_entries(capsys):
    """Non-empty list prints report header and entries."""
    entry = _make_entry(
        entry_id="report-entry",
        organization="ReportCo",
        submitted_date=(date.today() - timedelta(days=10)).isoformat(),
    )
    show_hydration_report([entry])
    captured = capsys.readouterr()
    assert "report-entry" in captured.out
    assert "ReportCo" in captured.out
    assert "Hydration Report" in captured.out
