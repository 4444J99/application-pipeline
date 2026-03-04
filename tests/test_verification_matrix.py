"""Tests for scripts/verification_matrix.py."""

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from verification_matrix import build_matrix, load_overrides


def test_build_matrix_classifies_direct_override_and_missing():
    modules = ["alpha", "beta", "gamma"]
    direct = {"alpha"}
    overrides = {
        "beta": {
            "verification": "integration_test",
            "evidence": ["tests/test_beta_integration.py"],
            "note": "covered via integration",
        }
    }

    report = build_matrix(modules, direct, overrides)
    by_module = {row.module: row for row in report["rows"]}

    assert by_module["alpha"].verification == "direct_test"
    assert by_module["beta"].verification == "integration_test"
    assert by_module["gamma"].verification == "missing"
    assert report["missing_modules"] == ["gamma"]
    assert report["missing_count"] == 1


def test_build_matrix_detects_stale_overrides():
    report = build_matrix(
        modules=["alpha"],
        direct_test_modules=set(),
        overrides={"old-module": {"verification": "smoke", "evidence": []}},
    )
    assert report["stale_overrides"] == ["old-module"]


def test_build_matrix_reports_missing_mcp_tools():
    report = build_matrix(
        modules=["alpha"],
        direct_test_modules={"alpha"},
        overrides={},
        mcp_tools=["pipeline_score", "pipeline_validate"],
        mcp_tested_tools={"pipeline_score"},
    )
    assert report["mcp_tools_total"] == 2
    assert report["mcp_tools_missing"] == ["pipeline_validate"]


def test_load_overrides_normalizes_shapes(tmp_path):
    path = tmp_path / "overrides.yaml"
    path.write_text(
        yaml.dump(
            {
                "overrides": {
                    "alpha": {
                        "verification": "smoke",
                        "evidence": "python scripts/alpha.py",
                    },
                }
            },
            sort_keys=False,
        )
    )

    overrides = load_overrides(path)
    assert "alpha" in overrides
    assert overrides["alpha"]["verification"] == "smoke"
    assert overrides["alpha"]["evidence"] == ["python scripts/alpha.py"]
