"""Tests for apply_engine.py — readiness checking and ATS submission."""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from apply_engine import (
    ApplyResult,
    ReadinessCheck,
    _log_apply_result,
    apply_ready_entries,
    check_readiness,
)


def _make_entry(
    entry_id="test-entry",
    status="staged",
    portal="greenhouse",
    blocks_used=None,
    cover_letter=None,
    resume=None,
    outreach_log=None,
):
    """Build a minimal pipeline entry dict for testing."""
    entry = {
        "id": entry_id,
        "status": status,
        "target": {"portal": portal, "application_url": "https://example.com"},
        "submission": {},
    }
    if blocks_used is not None:
        entry["submission"]["blocks_used"] = blocks_used
    if cover_letter:
        entry["submission"]["variant_ids"] = [cover_letter]
    if resume:
        entry["submission"]["materials_attached"] = [resume]
    if outreach_log is not None:
        entry["follow_up"] = {"actions_log": outreach_log}
    return entry


class TestCheckReadiness:
    def test_fully_ready_entry(self, tmp_path):
        """Entry with all materials is ready."""
        entry = _make_entry(
            blocks_used=["identity/2min"],
            outreach_log=[{"date": "2026-03-10", "channel": "linkedin"}],
        )
        with patch("apply_engine.resolve_cover_letter", return_value="cover.md"), \
             patch("apply_engine.resolve_resume", return_value="resume.pdf"):
            result = check_readiness(entry)
        assert result.is_ready
        assert result.missing == []
        assert result.has_cover_letter
        assert result.has_resume
        assert result.has_blocks

    def test_missing_cover_letter(self):
        entry = _make_entry(
            blocks_used=["identity/2min"],
            outreach_log=[{"date": "2026-03-10"}],
        )
        with patch("apply_engine.resolve_cover_letter", return_value=None), \
             patch("apply_engine.resolve_resume", return_value="resume.pdf"):
            result = check_readiness(entry)
        assert not result.is_ready
        assert "cover_letter" in result.missing

    def test_missing_resume(self):
        entry = _make_entry(
            blocks_used=["identity/2min"],
            outreach_log=[{"date": "2026-03-10"}],
        )
        with patch("apply_engine.resolve_cover_letter", return_value="cover.md"), \
             patch("apply_engine.resolve_resume", return_value=None):
            result = check_readiness(entry)
        assert not result.is_ready
        assert "resume" in result.missing

    def test_missing_blocks(self):
        entry = _make_entry(
            outreach_log=[{"date": "2026-03-10"}],
        )
        with patch("apply_engine.resolve_cover_letter", return_value="cover.md"), \
             patch("apply_engine.resolve_resume", return_value="resume.pdf"):
            result = check_readiness(entry)
        assert not result.is_ready
        assert "blocks_used" in result.missing

    def test_missing_portal(self):
        entry = _make_entry(
            portal="",
            blocks_used=["identity/2min"],
            outreach_log=[{"date": "2026-03-10"}],
        )
        with patch("apply_engine.resolve_cover_letter", return_value="cover.md"), \
             patch("apply_engine.resolve_resume", return_value="resume.pdf"):
            result = check_readiness(entry)
        assert not result.is_ready
        assert "portal type" in result.missing

    def test_missing_outreach(self):
        """Entries without outreach actions are not ready."""
        entry = _make_entry(blocks_used=["identity/2min"])
        with patch("apply_engine.resolve_cover_letter", return_value="cover.md"), \
             patch("apply_engine.resolve_resume", return_value="resume.pdf"):
            result = check_readiness(entry)
        assert not result.is_ready
        assert any("outreach" in m for m in result.missing)

    def test_portal_propagated(self):
        entry = _make_entry(portal="lever")
        with patch("apply_engine.resolve_cover_letter", return_value=None), \
             patch("apply_engine.resolve_resume", return_value=None):
            result = check_readiness(entry)
        assert result.portal == "lever"

    def test_no_custom_questions_is_ready(self):
        """Entry with no portal answer file is assumed ready (no custom questions)."""
        entry = _make_entry(
            blocks_used=["identity/2min"],
            outreach_log=[{"date": "2026-03-10"}],
        )
        with patch("apply_engine.resolve_cover_letter", return_value="cover.md"), \
             patch("apply_engine.resolve_resume", return_value="resume.pdf"):
            result = check_readiness(entry)
        assert result.has_answers


class TestApplyReadyEntries:
    def test_dry_run_skips_submission(self):
        entries = [_make_entry(entry_id="e1", blocks_used=["a"], outreach_log=[{"d": 1}])]
        with patch("apply_engine.load_entries", return_value=entries), \
             patch("apply_engine.resolve_cover_letter", return_value="c.md"), \
             patch("apply_engine.resolve_resume", return_value="r.pdf"):
            result = apply_ready_entries(dry_run=True)
        assert len(result.checked) == 1
        assert len(result.submitted) == 0
        assert "e1" in result.skipped

    def test_filters_non_staged(self):
        entries = [_make_entry(entry_id="e1", status="qualified")]
        with patch("apply_engine.load_entries", return_value=entries):
            result = apply_ready_entries(dry_run=True)
        assert len(result.checked) == 0

    def test_filters_by_entry_ids(self):
        entries = [
            _make_entry(entry_id="a"),
            _make_entry(entry_id="b"),
        ]
        with patch("apply_engine.load_entries", return_value=entries), \
             patch("apply_engine.resolve_cover_letter", return_value=None), \
             patch("apply_engine.resolve_resume", return_value=None):
            result = apply_ready_entries(entry_ids=["a"], dry_run=True)
        assert len(result.checked) == 1
        assert result.checked[0].entry_id == "a"

    def test_not_ready_goes_to_skipped(self):
        entries = [_make_entry(entry_id="e1")]  # No blocks or outreach
        with patch("apply_engine.load_entries", return_value=entries), \
             patch("apply_engine.resolve_cover_letter", return_value=None), \
             patch("apply_engine.resolve_resume", return_value=None):
            result = apply_ready_entries(dry_run=True)
        assert "e1" in result.skipped

    def test_submission_on_execute(self):
        """When dry_run=False, ready entries go through _submit_entry."""
        entries = [_make_entry(entry_id="e1", blocks_used=["a"], outreach_log=[{"d": 1}])]
        with patch("apply_engine.load_entries", return_value=entries), \
             patch("apply_engine.resolve_cover_letter", return_value="c.md"), \
             patch("apply_engine.resolve_resume", return_value="r.pdf"), \
             patch("apply_engine._submit_entry", return_value=(True, "ok")) as mock_sub:
            result = apply_ready_entries(dry_run=False)
        assert "e1" in result.submitted
        mock_sub.assert_called_once()

    def test_submission_error_recorded(self):
        entries = [_make_entry(entry_id="e1", blocks_used=["a"], outreach_log=[{"d": 1}])]
        with patch("apply_engine.load_entries", return_value=entries), \
             patch("apply_engine.resolve_cover_letter", return_value="c.md"), \
             patch("apply_engine.resolve_resume", return_value="r.pdf"), \
             patch("apply_engine._submit_entry", return_value=(False, "API error")):
            result = apply_ready_entries(dry_run=False)
        assert len(result.errors) == 1
        assert "e1" in result.errors[0]


class TestLogApplyResult:
    def test_creates_log_file(self, tmp_path):
        log_path = tmp_path / "apply-history.yaml"
        result = ApplyResult(
            checked=[],
            submitted=["a"],
            skipped=["b"],
            errors=[],
        )
        _log_apply_result(result, log_path=log_path)
        assert log_path.exists()
        data = yaml.safe_load(log_path.read_text())
        assert len(data) == 1
        assert data[0]["submitted"] == 1

    def test_appends_to_existing_log(self, tmp_path):
        log_path = tmp_path / "apply-history.yaml"
        log_path.write_text(yaml.dump([{"date": "2026-03-13", "submitted": 2}]))
        result = ApplyResult(submitted=["c"])
        _log_apply_result(result, log_path=log_path)
        data = yaml.safe_load(log_path.read_text())
        assert len(data) == 2


class TestDataclasses:
    def test_readiness_check_serializable(self):
        check = ReadinessCheck(
            entry_id="test", is_ready=True, portal="greenhouse",
        )
        import dataclasses
        d = dataclasses.asdict(check)
        serialized = json.dumps(d)
        assert "test" in serialized

    def test_apply_result_defaults(self):
        result = ApplyResult()
        assert result.checked == []
        assert result.submitted == []
        assert result.skipped == []
        assert result.errors == []

    def test_apply_result_serializable(self):
        result = ApplyResult(submitted=["a", "b"])
        import dataclasses
        serialized = json.dumps(dataclasses.asdict(result), default=str)
        assert "a" in serialized
