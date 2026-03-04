#!/usr/bin/env python3
"""Module verification matrix checker.

Ensures every top-level script module has an explicit verification route:
1) direct test file (tests/test_<module>.py), or
2) override evidence in strategy/module-verification-overrides.yaml.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
TESTS_DIR = REPO_ROOT / "tests"
DEFAULT_OVERRIDES_PATH = REPO_ROOT / "strategy" / "module-verification-overrides.yaml"
IGNORED_MODULES = {"__init__"}


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


def build_matrix(modules: list[str], direct_test_modules: set[str], overrides: dict[str, dict]) -> dict:
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

    return {
        "total_modules": len(modules),
        "direct_test_count": sum(1 for row in rows if row.verification == "direct_test"),
        "override_count": sum(1 for row in rows if row.verification != "direct_test" and row.verification != "missing"),
        "missing_count": len(missing),
        "missing_modules": sorted(missing),
        "stale_overrides": stale_overrides,
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
    report = build_matrix(modules, direct_test_modules, overrides)

    if args.json:
        payload = dict(report)
        payload["rows"] = [asdict(row) for row in report["rows"]]
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        _print_report(report)

    has_failures = bool(report["missing_modules"] or report["stale_overrides"])
    if args.strict and has_failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
