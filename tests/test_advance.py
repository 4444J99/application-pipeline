"""Tests for scripts/advance.py"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from advance import (
    VALID_TRANSITIONS,
    _log_gate_bypass,
    advance_entry,
    can_advance,
    has_outreach_actions,
    run_advance,
    run_report,
)

# --- can_advance ---


def test_can_advance_valid():
    assert can_advance("qualified", "drafting") is True
    assert can_advance("qualified", "staged") is True
    assert can_advance("drafting", "staged") is True
    assert can_advance("staged", "submitted") is True
    assert can_advance("research", "qualified") is True


def test_can_advance_invalid():
    assert can_advance("research", "submitted") is False
    assert can_advance("qualified", "submitted") is False
    assert can_advance("outcome", "research") is False


def test_can_advance_withdrawn():
    assert can_advance("qualified", "withdrawn") is True
    assert can_advance("drafting", "withdrawn") is True
    assert can_advance("staged", "withdrawn") is True


def test_can_advance_outcome_terminal():
    assert can_advance("outcome", "research") is False
    assert can_advance("outcome", "qualified") is False


def test_can_advance_rollback():
    assert can_advance("drafting", "qualified") is True
    assert can_advance("staged", "drafting") is True


def test_can_advance_from_deferred():
    """Deferred entries can be re-activated to staged, qualified, or drafting."""
    assert can_advance("deferred", "staged") is True
    assert can_advance("deferred", "qualified") is True
    assert can_advance("deferred", "drafting") is True
    assert can_advance("deferred", "withdrawn") is True
    # But not to arbitrary statuses
    assert can_advance("deferred", "submitted") is False


def test_valid_transitions_all_statuses():
    """All statuses in VALID_TRANSITIONS should map to sets."""
    for status, targets in VALID_TRANSITIONS.items():
        assert isinstance(targets, set), f"{status} doesn't map to a set"


# --- advance_entry ---


def _make_temp_yaml(content: str) -> Path:
    """Write content to a temp file and return its path."""
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
    f.write(content)
    f.close()
    return Path(f.name)


SAMPLE_YAML = """id: test-entry
name: Test Entry
track: grant
status: qualified
outcome: null
deadline:
  date: '2026-06-01'
  type: hard
submission:
  effort_level: quick
timeline:
  researched: '2026-01-01'
  qualified: '2026-01-15'
  materials_ready: null
  submitted: null
last_touched: "2026-01-15"
"""


def test_advance_entry_updates_status():
    filepath = _make_temp_yaml(SAMPLE_YAML)
    try:
        result = advance_entry(filepath, "test-entry", "drafting")
        assert result is True
        content = filepath.read_text()
        assert "status: drafting" in content
    finally:
        filepath.unlink()


def test_advance_entry_updates_last_touched():
    from datetime import date
    filepath = _make_temp_yaml(SAMPLE_YAML)
    try:
        advance_entry(filepath, "test-entry", "drafting")
        content = filepath.read_text()
        assert date.today().isoformat() in content
    finally:
        filepath.unlink()


def test_advance_entry_to_staged_sets_timeline():
    filepath = _make_temp_yaml(SAMPLE_YAML)
    try:
        advance_entry(filepath, "test-entry", "staged")
        content = filepath.read_text()
        assert "status: staged" in content
        # materials_ready should be set
        from datetime import date
        assert date.today().isoformat() in content
    finally:
        filepath.unlink()


def test_advance_entry_preserves_other_fields():
    filepath = _make_temp_yaml(SAMPLE_YAML)
    try:
        advance_entry(filepath, "test-entry", "drafting")
        content = filepath.read_text()
        assert "id: test-entry" in content
        assert "name: Test Entry" in content
        assert "track: grant" in content
    finally:
        filepath.unlink()


def test_advance_entry_no_last_touched():
    """Test advancing an entry that has no last_touched field."""
    yaml_no_touch = """id: test-entry
name: Test Entry
track: grant
status: qualified
"""
    filepath = _make_temp_yaml(yaml_no_touch)
    try:
        advance_entry(filepath, "test-entry", "drafting")
        content = filepath.read_text()
        assert "status: drafting" in content
        assert "last_touched:" in content
    finally:
        filepath.unlink()


# --- deferred re-activation ---


DEFERRED_YAML = """id: deferred-entry
name: Deferred Entry
track: grant
status: deferred
deferral:
  reason: portal_paused
  resume_date: '2026-04-01'
  note: Portal under maintenance
last_touched: "2026-01-15"
"""


def test_advance_deferred_to_staged():
    """Deferred entries can be advanced to staged."""
    filepath = _make_temp_yaml(DEFERRED_YAML)
    try:
        result = advance_entry(filepath, "deferred-entry", "staged")
        assert result is True
        content = filepath.read_text()
        assert "status: staged" in content
    finally:
        filepath.unlink()


def test_advance_deferred_to_qualified():
    """Deferred entries can be advanced to qualified."""
    filepath = _make_temp_yaml(DEFERRED_YAML)
    try:
        result = advance_entry(filepath, "deferred-entry", "qualified")
        assert result is True
        content = filepath.read_text()
        assert "status: qualified" in content
    finally:
        filepath.unlink()


def test_run_advance_excludes_deferred_from_normal_batch():
    """Deferred entries should not be picked up by default batch operations
    targeting actionable statuses (e.g. --to staged without --status deferred).

    The gate allows deferred entries through, but can_advance must also pass,
    and deferred is not in ACTIONABLE_STATUSES so the status_filter logic
    handles exclusion correctly.
    """
    # Deferred → staged is valid per VALID_TRANSITIONS
    assert can_advance("deferred", "staged") is True
    # But deferred is NOT in ACTIONABLE_STATUSES, meaning it won't match
    # a default --status filter for qualified/drafting batch runs
    from pipeline_lib import ACTIONABLE_STATUSES
    assert "deferred" not in ACTIONABLE_STATUSES


# --- has_outreach_actions ---


def test_has_outreach_actions_empty():
    """Entry with no follow_up or outreach returns False."""
    entry = {"id": "test", "follow_up": [], "outreach": []}
    assert has_outreach_actions(entry) is False


def test_has_outreach_actions_missing_keys():
    """Entry missing follow_up and outreach keys returns False."""
    entry = {"id": "test"}
    assert has_outreach_actions(entry) is False


def test_has_outreach_actions_none_values():
    """Entry with None follow_up/outreach returns False."""
    entry = {"id": "test", "follow_up": None, "outreach": None}
    assert has_outreach_actions(entry) is False


def test_has_outreach_actions_with_follow_up():
    """Entry with follow_up actions returns True."""
    entry = {
        "id": "test",
        "follow_up": [{"date": "2026-03-01", "channel": "linkedin"}],
        "outreach": [],
    }
    assert has_outreach_actions(entry) is True


def test_has_outreach_actions_with_outreach():
    """Entry with outreach actions returns True."""
    entry = {
        "id": "test",
        "follow_up": [],
        "outreach": [{"date": "2026-03-01", "contact": "Alice"}],
    }
    assert has_outreach_actions(entry) is True


def test_has_outreach_actions_with_both():
    """Entry with both follow_up and outreach returns True."""
    entry = {
        "id": "test",
        "follow_up": [{"date": "2026-03-01"}],
        "outreach": [{"date": "2026-03-01"}],
    }
    assert has_outreach_actions(entry) is True


# --- run_report ---


def _make_report_entry(
    entry_id, name, status, score=7.0, effort="standard",
    deadline_date=None, deadline_type="rolling", has_profile_name=None,
):
    """Build an entry dict suitable for run_report testing."""
    entry = {
        "id": entry_id,
        "name": name,
        "status": status,
        "fit": {"score": score},
        "submission": {"effort_level": effort},
        "deadline": {"date": deadline_date, "type": deadline_type},
    }
    return entry


def test_run_report_ready_sorted_by_score(capsys, monkeypatch):
    """Ready entries are printed sorted by score descending."""
    entries = [
        _make_report_entry("low-score", "Low Score Entry", "qualified", score=6.0),
        _make_report_entry("high-score", "High Score Entry", "qualified", score=9.5),
        _make_report_entry("mid-score", "Mid Score Entry", "qualified", score=7.5),
    ]

    # Mock load_profile to return a profile for all entries (no blockers)
    monkeypatch.setattr("advance.load_profile", lambda target_id: {"name": target_id})

    run_report(entries)

    output = capsys.readouterr().out
    assert "READY TO ADVANCE (3)" in output
    # High score should appear before mid, which appears before low
    high_pos = output.index("High Score Entry")
    mid_pos = output.index("Mid Score Entry")
    low_pos = output.index("Low Score Entry")
    assert high_pos < mid_pos < low_pos


def test_run_report_blocked_no_profile(capsys, monkeypatch):
    """Entries without a profile are classified as blocked."""
    entries = [
        _make_report_entry("no-profile-entry", "No Profile Entry", "qualified", score=8.0),
    ]

    # Mock load_profile to return None (no profile found)
    monkeypatch.setattr("advance.load_profile", lambda target_id: None)

    run_report(entries)

    output = capsys.readouterr().out
    assert "BLOCKED (1)" in output
    assert "No Profile Entry" in output
    assert "no profile" in output


def test_run_report_blocked_expired_deadline(capsys, monkeypatch):
    """Entries with expired deadlines are classified as blocked."""
    entries = [
        _make_report_entry(
            "expired-entry", "Expired Entry", "qualified",
            score=8.0, deadline_date="2020-01-01", deadline_type="hard",
        ),
    ]

    # Has a profile, but deadline is expired
    monkeypatch.setattr("advance.load_profile", lambda target_id: {"name": target_id})

    run_report(entries)

    output = capsys.readouterr().out
    assert "BLOCKED" in output
    assert "expired deadline" in output


def test_run_report_non_actionable_skipped(capsys, monkeypatch):
    """Entries with non-actionable statuses (submitted, outcome) are skipped."""
    entries = [
        _make_report_entry("submitted-entry", "Submitted Entry", "submitted"),
        _make_report_entry("outcome-entry", "Outcome Entry", "outcome"),
    ]

    monkeypatch.setattr("advance.load_profile", lambda target_id: {"name": target_id})

    run_report(entries)

    output = capsys.readouterr().out
    assert "No actionable entries to advance." in output


def test_run_report_summary_counts(capsys, monkeypatch):
    """Summary line shows correct ready and blocked counts."""
    entries = [
        _make_report_entry("ready-1", "Ready One", "qualified", score=8.0),
        _make_report_entry("blocked-1", "Blocked One", "qualified", score=7.0),
    ]

    # First entry has profile, second does not
    def mock_load_profile(target_id):
        if target_id == "ready-1":
            return {"name": "ready-1"}
        return None

    monkeypatch.setattr("advance.load_profile", mock_load_profile)

    run_report(entries)

    output = capsys.readouterr().out
    assert "Summary: 1 ready, 1 blocked, 2 total actionable" in output


# --- run_advance ---


def _write_pipeline_yaml(tmp_path, entry_id, status="qualified", effort="quick",
                         follow_up=None, outreach=None, org=None):
    """Write a pipeline YAML file in tmp_path and return its path."""
    lines = [
        f"id: {entry_id}",
        f"name: {entry_id.replace('-', ' ').title()}",
        "track: job",
        f"status: {status}",
        "outcome: null",
        "deadline:",
        "  date: '2026-12-01'",
        "  type: hard",
        "fit:",
        "  score: 8.0",
        "submission:",
        f"  effort_level: {effort}",
        "timeline:",
        "  researched: '2026-01-01'",
        "  qualified: '2026-01-15'",
        "  materials_ready: null",
        "  submitted: null",
        'last_touched: "2026-01-15"',
    ]
    if org:
        lines.insert(4, "target:")
        lines.insert(5, f"  organization: {org}")
    if follow_up is not None:
        if follow_up:
            lines.append("follow_up:")
            for item in follow_up:
                lines.append(f"  - date: '{item}'")
        else:
            lines.append("follow_up: []")
    if outreach is not None:
        if outreach:
            lines.append("outreach:")
            for item in outreach:
                lines.append(f"  - date: '{item}'")
        else:
            lines.append("outreach: []")

    content = "\n".join(lines) + "\n"
    filepath = tmp_path / f"{entry_id}.yaml"
    filepath.write_text(content)
    return filepath


def _make_loaded_entry(filepath):
    """Parse a pipeline YAML file into an entry dict with _filepath metadata."""
    import yaml
    data = yaml.safe_load(filepath.read_text())
    data["_filepath"] = filepath
    data["_dir"] = filepath.parent.name
    data["_file"] = filepath.name
    return data


def test_run_advance_dry_run_no_file_modification(tmp_path, monkeypatch, capsys):
    """Dry run mode prints candidates but does not modify files."""
    filepath = _write_pipeline_yaml(tmp_path, "dry-run-test", status="qualified")
    original_content = filepath.read_text()

    entry = _make_loaded_entry(filepath)

    monkeypatch.setattr("advance.load_entries", lambda include_filepath=False: [entry])

    run_advance(
        target_status="drafting",
        effort_filter=None,
        status_filter=None,
        entry_id=None,
        dry_run=True,
        auto_yes=True,
    )

    # File should be unchanged
    assert filepath.read_text() == original_content

    output = capsys.readouterr().out
    assert "DRY RUN" in output
    assert "1 entries would be advanced" in output


def test_run_advance_outreach_gate_blocks_submitted(tmp_path, monkeypatch, capsys):
    """Entries without outreach actions are blocked from advancing to submitted."""
    filepath = _write_pipeline_yaml(
        tmp_path, "no-outreach", status="staged",
        follow_up=[], outreach=[],
    )
    original_content = filepath.read_text()

    entry = _make_loaded_entry(filepath)

    monkeypatch.setattr("advance.load_entries", lambda include_filepath=False: [entry])

    run_advance(
        target_status="submitted",
        effort_filter=None,
        status_filter=None,
        entry_id=None,
        dry_run=False,
        auto_yes=True,
        force=False,
    )

    # File should be unchanged — blocked by outreach gate
    assert filepath.read_text() == original_content

    output = capsys.readouterr().out
    assert "BLOCKED" in output
    assert "No outreach actions recorded" in output


def test_run_advance_force_bypasses_outreach_gate(tmp_path, monkeypatch, capsys):
    """Force flag bypasses the outreach gate for advancing to submitted."""
    filepath = _write_pipeline_yaml(
        tmp_path, "force-test", status="staged",
        follow_up=[], outreach=[],
    )

    entry = _make_loaded_entry(filepath)

    monkeypatch.setattr("advance.load_entries", lambda include_filepath=False: [entry])
    # Mock log_action to avoid writing to signal-actions.yaml
    monkeypatch.setattr("advance.advance_entry", lambda fp, eid, ts, reason=None: _mock_advance(fp, ts))

    run_advance(
        target_status="submitted",
        effort_filter=None,
        status_filter=None,
        entry_id=None,
        dry_run=False,
        auto_yes=True,
        force=True,
    )

    output = capsys.readouterr().out
    # Should not be blocked — force bypasses the gate
    assert "BLOCKED" not in output
    assert "Advanced 1 entries" in output


def _mock_advance(filepath, target_status):
    """Minimal mock for advance_entry that updates status without signal logging."""
    content = filepath.read_text()
    import re
    content = re.sub(r"status: \S+", f"status: {target_status}", content)
    filepath.write_text(content)
    return True


def test_run_advance_filters_by_effort(tmp_path, monkeypatch, capsys):
    """Effort filter only includes entries matching the specified effort level."""
    fp_quick = _write_pipeline_yaml(tmp_path, "quick-entry", status="qualified", effort="quick")
    fp_deep = _write_pipeline_yaml(tmp_path, "deep-entry", status="qualified", effort="deep")

    entries = [_make_loaded_entry(fp_quick), _make_loaded_entry(fp_deep)]

    monkeypatch.setattr("advance.load_entries", lambda include_filepath=False: entries)

    run_advance(
        target_status="drafting",
        effort_filter="quick",
        status_filter=None,
        entry_id=None,
        dry_run=True,
        auto_yes=True,
    )

    output = capsys.readouterr().out
    assert "Quick Entry" in output
    assert "Deep Entry" not in output
    assert "1 entries would be advanced" in output


def test_run_advance_filters_by_entry_id(tmp_path, monkeypatch, capsys):
    """Entry ID filter selects only the matching entry."""
    fp_a = _write_pipeline_yaml(tmp_path, "entry-a", status="qualified")
    fp_b = _write_pipeline_yaml(tmp_path, "entry-b", status="qualified")

    entries = [_make_loaded_entry(fp_a), _make_loaded_entry(fp_b)]

    monkeypatch.setattr("advance.load_entries", lambda include_filepath=False: entries)

    run_advance(
        target_status="drafting",
        effort_filter=None,
        status_filter=None,
        entry_id="entry-a",
        dry_run=True,
        auto_yes=True,
    )

    output = capsys.readouterr().out
    assert "Entry A" in output
    assert "Entry B" not in output


def test_run_advance_no_candidates_prints_message(tmp_path, monkeypatch, capsys):
    """When no entries match filters, a clear message is printed."""
    monkeypatch.setattr("advance.load_entries", lambda include_filepath=False: [])

    run_advance(
        target_status="drafting",
        effort_filter=None,
        status_filter=None,
        entry_id=None,
        dry_run=True,
        auto_yes=True,
    )

    output = capsys.readouterr().out
    assert "No entries match" in output


# --- strict mode ---


def test_run_advance_strict_blocks_without_outreach(tmp_path, monkeypatch, capsys):
    """Strict mode blocks submitted advancement even if --skip-outreach-gate is not used."""
    filepath = _write_pipeline_yaml(
        tmp_path, "strict-test", status="staged",
        follow_up=[], outreach=[],
    )
    original_content = filepath.read_text()
    entry = _make_loaded_entry(filepath)

    monkeypatch.setattr("advance.load_entries", lambda include_filepath=False: [entry])

    run_advance(
        target_status="submitted",
        effort_filter=None,
        status_filter=None,
        entry_id=None,
        dry_run=False,
        auto_yes=True,
        force=False,
        strict=True,
    )

    assert filepath.read_text() == original_content
    output = capsys.readouterr().out
    assert "strict mode" in output
    assert "BLOCKED" in output


def test_run_advance_strict_allows_with_outreach(tmp_path, monkeypatch, capsys):
    """Strict mode allows submitted advancement when outreach actions exist."""
    filepath = _write_pipeline_yaml(
        tmp_path, "strict-ok", status="staged",
        follow_up=["2026-03-01"], outreach=[],
    )
    entry = _make_loaded_entry(filepath)

    monkeypatch.setattr("advance.load_entries", lambda include_filepath=False: [entry])
    monkeypatch.setattr("advance.advance_entry", lambda fp, eid, ts, reason=None: _mock_advance(fp, ts))

    run_advance(
        target_status="submitted",
        effort_filter=None,
        status_filter=None,
        entry_id=None,
        dry_run=False,
        auto_yes=True,
        force=False,
        strict=True,
    )

    output = capsys.readouterr().out
    assert "BLOCKED" not in output
    assert "Advanced 1 entries" in output


# --- gate bypass logging ---


def test_log_gate_bypass_best_effort(monkeypatch):
    """Gate bypass logging is best-effort and does not raise."""
    # Should not raise even when log_signal_action is not importable
    _log_gate_bypass("test-entry", "outreach")
