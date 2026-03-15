"""Tests for scripts/verify_all.py."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from verify_all import _resolve_lint_command, build_checks


def test_build_checks_full_mode_includes_full_pytests():
    checks = build_checks(quick=False)
    names = [check.name for check in checks]

    assert "module-verification-matrix" in names
    assert "lint" in names
    assert "pipeline-validation" in names
    assert "full-pytests" in names
    assert "smoke-pytests" not in names


def test_build_checks_quick_mode_includes_smoke_pytests():
    checks = build_checks(quick=True)
    names = [check.name for check in checks]

    assert "module-verification-matrix" in names
    assert "lint" in names
    assert "pipeline-validation" in names
    assert "smoke-pytests" in names
    assert "full-pytests" not in names


def test_resolve_lint_command_returns_list():
    result = _resolve_lint_command()
    assert isinstance(result, list)
    assert len(result) >= 3
    assert "check" in result


def test_build_checks_names_are_unique():
    for quick in (True, False):
        checks = build_checks(quick=quick)
        names = [c.name for c in checks]
        assert len(names) == len(set(names)), f"duplicate check names in quick={quick}"


def test_build_checks_returns_at_least_three():
    for quick in (True, False):
        checks = build_checks(quick=quick)
        assert len(checks) >= 3, f"expected >=3 checks, got {len(checks)} in quick={quick}"

