"""Tests for scripts/review_entry.py"""

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from review_entry import mark_reviewed


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
    assert "reviewed_at" in data["status_meta"]
    assert "last_touched" in data
