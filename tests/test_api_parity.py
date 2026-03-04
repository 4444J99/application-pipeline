"""Parity checks between legacy script behavior and pipeline_api wrappers."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from pipeline_api import ResultStatus, score_entry

REPO_ROOT = Path(__file__).resolve().parent.parent


def _sample_entry_id() -> str:
    for rel in ("pipeline/active", "pipeline/submitted", "pipeline/closed", "pipeline/research_pool"):
        pipeline_dir = REPO_ROOT / rel
        for path in sorted(pipeline_dir.glob("*.yaml")):
            if not path.name.startswith("_"):
                return path.stem
    raise AssertionError("No pipeline entries found")


def _parse_score_from_run_output(output: str, entry_id: str) -> float:
    for line in output.splitlines():
        if entry_id not in line:
            continue
        tail = line.split(entry_id, 1)[1].strip()
        if not tail:
            continue
        token = tail.split()[0]  # allow-secret: parser token, not credential material
        return float(token)
    raise AssertionError(f"Could not parse score for {entry_id} from output:\n{output}")


def test_score_api_matches_run_script_dry_run_output():
    entry_id = _sample_entry_id()
    cmd = [sys.executable, str(REPO_ROOT / "scripts" / "run.py"), "score", entry_id, "--dry-run"]
    script = subprocess.run(cmd, capture_output=True, text=True, check=False)
    assert script.returncode == 0, script.stderr

    script_score = _parse_score_from_run_output(script.stdout, entry_id)
    api_result = score_entry(entry_id=entry_id, dry_run=True)

    assert api_result.status == ResultStatus.DRY_RUN
    assert api_result.new_score == script_score
