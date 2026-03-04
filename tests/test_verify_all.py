"""Tests for scripts/verify_all.py."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from verify_all import build_checks


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

