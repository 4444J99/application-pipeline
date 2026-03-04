#!/usr/bin/env python3
"""Run end-to-end verification gates for the repository.

Default mode runs the same heavy checks expected for release confidence.
Quick mode runs a reduced set for faster local feedback.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PYTHON = sys.executable


@dataclass(frozen=True)
class Check:
    name: str
    command: list[str]


def _resolve_lint_command() -> list[str]:
    """Prefer interpreter-coupled Ruff invocation when available."""
    probe = [PYTHON, "-m", "ruff", "--version"]
    try:
        result = subprocess.run(probe, cwd=REPO_ROOT, capture_output=True, text=True)
    except OSError:
        result = None

    if result is not None and result.returncode == 0:
        return [PYTHON, "-m", "ruff", "check", "scripts/", "tests/"]

    return ["ruff", "check", "scripts/", "tests/"]


def build_checks(quick: bool) -> list[Check]:
    """Return ordered verification checks."""
    checks = [
        Check(
            name="module-verification-matrix",
            command=[PYTHON, str(REPO_ROOT / "scripts" / "verification_matrix.py"), "--strict"],
        ),
        Check(
            name="lint",
            command=_resolve_lint_command(),
        ),
        Check(
            name="pipeline-validation",
            command=[PYTHON, str(REPO_ROOT / "scripts" / "validate.py"), "--check-id-maps", "--check-rubric"],
        ),
    ]

    if quick:
        checks.append(
            Check(
                name="smoke-pytests",
                command=[
                    PYTHON,
                    "-m",
                    "pytest",
                    "-q",
                    "tests/test_pipeline_lib.py",
                    "tests/test_validate.py",
                    "tests/test_run.py",
                    "tests/test_cli.py",
                ],
            )
        )
    else:
        checks.append(
            Check(
                name="full-pytests",
                command=[PYTHON, "-m", "pytest", "tests/", "-q"],
            )
        )

    return checks


def _run_check(check: Check) -> int:
    print(f"\n[RUN] {check.name}")
    print(f"      {' '.join(check.command)}")
    result = subprocess.run(check.command, cwd=REPO_ROOT)
    if result.returncode == 0:
        print(f"[OK ] {check.name}")
    else:
        print(f"[FAIL] {check.name} (exit {result.returncode})")
    return result.returncode


def main() -> None:
    parser = argparse.ArgumentParser(description="Run complete repository verification gates")
    parser.add_argument("--quick", action="store_true", help="Run faster local checks instead of full pytest suite")
    args = parser.parse_args()

    checks = build_checks(quick=args.quick)
    for check in checks:
        exit_code = _run_check(check)
        if exit_code != 0:
            raise SystemExit(exit_code)

    print("\nAll verification gates passed.")


if __name__ == "__main__":
    main()
