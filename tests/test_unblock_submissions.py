"""Tests for scripts/unblock_submissions.py."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from unblock_submissions import (
    AuditRow,
    _needs_answer_fix,
    _portal_script_name,
    fix_answer_blockers,
    fix_review_gate,
)


def test_needs_answer_fix_only_for_supported_portals():
    row = AuditRow(
        entry={},
        result={"portal": "greenhouse", "results": {"answer_file": False, "answers_complete": True}},
    )
    assert _needs_answer_fix(row) is True

    no_fix = AuditRow(
        entry={},
        result={"portal": "custom", "results": {"answer_file": False, "answers_complete": False}},
    )
    assert _needs_answer_fix(no_fix) is False


def test_portal_script_name_mapping_and_error():
    assert _portal_script_name("greenhouse") == "greenhouse_submit.py"
    assert _portal_script_name("ashby") == "ashby_submit.py"
    with pytest.raises(ValueError):
        _portal_script_name("lever")


def test_fix_review_gate_dry_run_counts_targets(tmp_path, capsys):
    rows = [
        AuditRow(
            entry={"_filepath": str(tmp_path / "entry-1.yaml")},
            result={"id": "entry-1", "status": "staged", "results": {"review_approved": False}},
        ),
        AuditRow(
            entry={"_filepath": str(tmp_path / "entry-2.yaml")},
            result={"id": "entry-2", "status": "qualified", "results": {"review_approved": False}},
        ),
    ]
    fixed, failed = fix_review_gate(rows, reviewer="tester", note="note", apply=False)
    output = capsys.readouterr().out
    assert fixed == 1
    assert failed == 0
    assert "would mark reviewed: entry-1" in output


def test_fix_answer_blockers_dry_run_plans_commands(capsys):
    rows = [
        AuditRow(
            entry={},
            result={
                "id": "entry-1",
                "portal": "greenhouse",
                "results": {"answer_file": False, "answers_complete": False},
            },
        )
    ]
    fixed, failed = fix_answer_blockers(rows, apply=False)
    output = capsys.readouterr().out
    assert fixed == 1
    assert failed == 0
    assert "--init-answers --force" in output
