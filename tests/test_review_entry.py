"""Tests for scripts/review_entry.py"""

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from review_entry import _collect_targets, _default_reviewer, mark_reviewed


def test_mark_reviewed_dry_run(tmp_path):
    path = tmp_path / "entry.yaml"
    path.write_text(
        yaml.dump(
            {
                "id": "test-entry",
                "status": "staged",
                "status_meta": {},
            },
            sort_keys=False,
        )
    )

    result = mark_reviewed(path, reviewer="tester", note="ok", dry_run=True)
    assert result["ok"] is True
    assert result["dry_run"] is True
    assert result["status_meta"]["reviewed_by"] == "tester"
    assert result["status_meta"]["approved_by"] == "tester"


def test_mark_reviewed_write(tmp_path):
    path = tmp_path / "entry.yaml"
    path.write_text(
        yaml.dump(
            {
                "id": "test-entry",
                "status": "staged",
            },
            sort_keys=False,
        )
    )

    result = mark_reviewed(path, reviewer="tester", dry_run=False)
    assert result["ok"] is True

    data = yaml.safe_load(path.read_text())
    assert data["status_meta"]["reviewed_by"] == "tester"
    assert data["status_meta"]["approved_by"] == "tester"
    assert "approved_at" in data["status_meta"]
    assert "reviewed_at" in data["status_meta"]
    assert "last_touched" in data


def test_default_reviewer_returns_string():
    result = _default_reviewer()
    assert isinstance(result, str)
    assert len(result) > 0


def test_collect_targets_single_file(monkeypatch):
    sentinel_path = Path("/tmp/fake-entry.yaml")
    monkeypatch.setattr(
        "review_entry.load_entry_by_id",
        lambda entry_id: (sentinel_path, {"id": entry_id}),
    )
    targets = _collect_targets("some-entry", all_staged=False)
    assert targets == [sentinel_path]


def test_collect_targets_raises_without_target_or_all():
    import pytest

    with pytest.raises(ValueError, match="Specify"):
        _collect_targets(None, all_staged=False)
