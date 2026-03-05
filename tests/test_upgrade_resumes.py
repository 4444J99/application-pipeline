"""Tests for scripts/upgrade_resumes.py."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from upgrade_resumes import find_stale_resumes, upgrade_entry_file


def test_find_stale_resumes_detects_old_batches():
    entries = [
        {
            "id": "entry-1",
            "_file": "entry-1.yaml",
            "_dir": "active",
            "submission": {
                "materials_attached": ["resumes/batch-01/resume.pdf"],
                "resume_path": "resumes/batch-01/resume.pdf",
            },
        },
        {
            "id": "entry-2",
            "_file": "entry-2.yaml",
            "_dir": "active",
            "submission": {
                "materials_attached": ["resumes/batch-04/resume.pdf"],
                "resume_path": "resumes/batch-04/resume.pdf",
            },
        },
    ]

    stale = find_stale_resumes(entries, target_batch="batch-04")
    assert stale
    assert all(item["entry_id"] == "entry-1" for item in stale)
    assert all(item["new_path"].startswith("resumes/batch-04/") for item in stale)


def test_upgrade_entry_file_replaces_batch_token(tmp_path):
    path = tmp_path / "entry.yaml"
    path.write_text("resume: resumes/batch-01/my-resume.pdf\n")

    changed = upgrade_entry_file(path, "batch-01", "batch-04")
    assert changed is True
    assert "batch-04" in path.read_text()

    unchanged = upgrade_entry_file(path, "batch-99", "batch-04")
    assert unchanged is False
