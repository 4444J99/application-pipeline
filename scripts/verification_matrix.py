#!/usr/bin/env python3
"""Module verification matrix checker.

Ensures every top-level script module has an explicit verification route:
1) direct test file (tests/test_<module>.py), or
2) override evidence in strategy/module-verification-overrides.yaml.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
TESTS_DIR = REPO_ROOT / "tests"
DEFAULT_OVERRIDES_PATH = REPO_ROOT / "strategy" / "module-verification-overrides.yaml"
IGNORED_MODULES = {"__init__"}
MCP_SERVER_PATH = REPO_ROOT / "scripts" / "mcp_server.py"
MCP_TEST_PATH = REPO_ROOT / "tests" / "test_mcp_server.py"


@dataclass(frozen=True)
class ModuleStatus:
    module: str
    verification: str
    evidence: list[str]
    note: str


def discover_modules(scripts_dir: Path) -> list[str]:
    """Discover top-level script modules under scripts/."""
    modules: list[str] = []
    for path in sorted(scripts_dir.glob("*.py")):
        stem = path.stem
        if stem in IGNORED_MODULES:
            continue
        if stem.startswith("_"):
            continue
        modules.append(stem)
    return modules


def discover_direct_test_modules(tests_dir: Path) -> set[str]:
    """Return module names that have direct test files (tests/test_<module>.py)."""
    modules: set[str] = set()
    for path in tests_dir.glob("test_*.py"):
        modules.add(path.stem.removeprefix("test_"))
    return modules


def load_overrides(path: Path) -> dict[str, dict]:
    """Load verification overrides YAML as a normalized dict."""
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text()) or {}
    if not isinstance(data, dict):
        return {}
    overrides = data.get("overrides", {})
    if not isinstance(overrides, dict):
        return {}
    result: dict[str, dict] = {}
    for module, cfg in overrides.items():
        if not isinstance(module, str):
            continue
        if not isinstance(cfg, dict):
            cfg = {}
        evidence = cfg.get("evidence", [])
        if isinstance(evidence, str):
            evidence = [evidence]
        if not isinstance(evidence, list):
            evidence = []
        result[module] = {
            "verification": str(cfg.get("verification", "override")),
            "evidence": [str(item) for item in evidence],
            "note": str(cfg.get("note", "")),
        }
    return result


def discover_mcp_tools(server_path: Path) -> list[str]:
    """Discover tool functions decorated with @mcp.tool() in mcp_server.py."""
    if not server_path.exists():
        return []

    tree = ast.parse(server_path.read_text())
    tools: list[str] = []
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            dec = decorator.func if isinstance(decorator, ast.Call) else decorator
            if isinstance(dec, ast.Attribute) and dec.attr == "tool":
                tools.append(node.name)
                break
    return sorted(tools)


def discover_mcp_tested_tools(test_path: Path, tools: list[str]) -> set[str]:
    """Return MCP tool functions that appear in the MCP server test file."""
    if not test_path.exists():
        return set()
    text = test_path.read_text()
    covered = set()
    for tool in tools:
        if re.search(rf"\b{re.escape(tool)}\b", text):
            covered.add(tool)
    return covered


def build_matrix(
    modules: list[str],
    direct_test_modules: set[str],
    overrides: dict[str, dict],
    mcp_tools: list[str] | None = None,
    mcp_tested_tools: set[str] | None = None,
) -> dict:
    """Build module verification matrix report payload."""
    rows: list[ModuleStatus] = []
    missing: list[str] = []

    for module in modules:
        if module in direct_test_modules:
            rows.append(
                ModuleStatus(
                    module=module,
                    verification="direct_test",
                    evidence=[f"tests/test_{module}.py"],
                    note="",
                )
            )
            continue

        override = overrides.get(module)
        if override is not None:
            rows.append(
                ModuleStatus(
                    module=module,
                    verification=override.get("verification", "override"),
                    evidence=override.get("evidence", []),
                    note=override.get("note", ""),
                )
            )
            continue

        missing.append(module)
        rows.append(
            ModuleStatus(
                module=module,
                verification="missing",
                evidence=[],
                note="No direct test file and no override evidence",
            )
        )

    stale_overrides = sorted(set(overrides.keys()) - set(modules))
    mcp_tools = sorted(mcp_tools or [])
    mcp_tested_tools = set(mcp_tested_tools or set())
    mcp_missing_tools = sorted(tool for tool in mcp_tools if tool not in mcp_tested_tools)

    return {
        "total_modules": len(modules),
        "direct_test_count": sum(1 for row in rows if row.verification == "direct_test"),
        "override_count": sum(1 for row in rows if row.verification != "direct_test" and row.verification != "missing"),
        "missing_count": len(missing),
        "missing_modules": sorted(missing),
        "stale_overrides": stale_overrides,
        "mcp_tools_total": len(mcp_tools),
        "mcp_tools_tested": sorted(mcp_tested_tools),
        "mcp_tools_missing": mcp_missing_tools,
        "rows": rows,
    }


def _print_report(report: dict) -> None:
    print("MODULE VERIFICATION MATRIX")
    print("=" * 72)
    print(f"Total modules:  {report['total_modules']}")
    print(f"Direct tests:   {report['direct_test_count']}")
    print(f"Override routes:{report['override_count']}")
    print(f"Missing routes: {report['missing_count']}")
    print()

    override_rows = [row for row in report["rows"] if row.verification not in {"direct_test", "missing"}]
    if override_rows:
        print("Override-verified modules:")
        for row in sorted(override_rows, key=lambda item: item.module):
            evidence = ", ".join(row.evidence) if row.evidence else "(no evidence listed)"
            print(f"  - {row.module}: {row.verification}")
            print(f"    evidence: {evidence}")
            if row.note:
                print(f"    note: {row.note}")
        print()

    missing = report["missing_modules"]
    if missing:
        print("MISSING verification routes:")
        for module in missing:
            print(f"  - {module}")
        print()

    stale_overrides = report["stale_overrides"]
    if stale_overrides:
        print("STALE override entries (module not found in scripts/):")
        for module in stale_overrides:
            print(f"  - {module}")
        print()

    mcp_missing = report["mcp_tools_missing"]
    print(f"MCP tools discovered: {report['mcp_tools_total']}")
    if mcp_missing:
        print("MCP TOOLS MISSING TEST COVERAGE:")
        for tool_name in mcp_missing:
            print(f"  - {tool_name}")
        print()
    else:
        print("MCP tool coverage: complete")


def main() -> None:
    parser = argparse.ArgumentParser(description="Check script module verification coverage")
    parser.add_argument(
        "--overrides",
        default=str(DEFAULT_OVERRIDES_PATH),
        help="Path to overrides YAML (default: strategy/module-verification-overrides.yaml)",
    )
    parser.add_argument("--strict", action="store_true", help="Exit non-zero on missing routes or stale overrides")
    parser.add_argument("--json", action="store_true", help="Emit JSON report instead of human-readable output")
    args = parser.parse_args()

    overrides_path = Path(args.overrides)
    modules = discover_modules(SCRIPTS_DIR)
    direct_test_modules = discover_direct_test_modules(TESTS_DIR)
    overrides = load_overrides(overrides_path)
    mcp_tools = discover_mcp_tools(MCP_SERVER_PATH)
    tested_mcp_tools = discover_mcp_tested_tools(MCP_TEST_PATH, mcp_tools)
    report = build_matrix(
        modules,
        direct_test_modules,
        overrides,
        mcp_tools=mcp_tools,
        mcp_tested_tools=tested_mcp_tools,
    )

    if args.json:
        payload = dict(report)
        payload["rows"] = [asdict(row) for row in report["rows"]]
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        _print_report(report)

    has_failures = bool(report["missing_modules"] or report["stale_overrides"] or report["mcp_tools_missing"])
    if args.strict and has_failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
