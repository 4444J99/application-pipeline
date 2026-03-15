#!/usr/bin/env python3
"""Refresh pipeline metrics from the ORGANVM ecosystem's live state.

Reads system-snapshot.json (preferred) or system-metrics.json from the
corpus repo and updates config/metrics.yaml with current values. Then
optionally runs check_metrics.py --fix to propagate changes into blocks
and resumes.

This is the pipeline's single point of contact with the ecosystem.
All hardcoded values flow through config/metrics.yaml → check_metrics.py.

Usage:
    python scripts/refresh_from_ecosystem.py                # update metrics.yaml
    python scripts/refresh_from_ecosystem.py --propagate    # also fix blocks/resumes
    python scripts/refresh_from_ecosystem.py --dry-run      # show what would change
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_METRICS = REPO_ROOT / "config" / "metrics.yaml"

# Ecosystem data sources (local paths — same machine)
SNAPSHOT_PATH = (
    Path.home() / "Workspace" / "meta-organvm"
    / "organvm-corpvs-testamentvm" / "system-snapshot.json"
)
SYSTEM_METRICS_PATH = (
    Path.home() / "Workspace" / "meta-organvm"
    / "organvm-corpvs-testamentvm" / "system-metrics.json"
)
REGISTRY_PATH = (
    Path.home() / "Workspace" / "meta-organvm"
    / "organvm-corpvs-testamentvm" / "registry-v2.json"
)


def load_json(path: Path) -> dict:
    with path.open() as f:
        return json.load(f)


def build_metrics_from_snapshot(snapshot: dict) -> dict:
    """Extract pipeline-relevant metrics from system-snapshot.json."""
    sys = snapshot.get("system", {})
    variables = snapshot.get("variables", {})
    organs_list = snapshot.get("organs", [])

    # Per-organ repo counts
    organs = {}
    for organ in organs_list:
        key = organ.get("key", "")
        short = key.replace("ORGAN-", "").replace("META-ORGANVM", "Meta")
        organs[short] = organ.get("repo_count", 0)

    return {
        "total_repos": int(variables.get("total_repos", sys.get("total_repos", 0))),
        "active_repos": int(variables.get("active_repos", sys.get("active_repos", 0))),
        "archived_repos": int(variables.get("archived_repos", 0)),
        "organizations": int(variables.get("total_organs", 8)),
        "published_essays": int(variables.get("published_essays", 0)),
        "total_words_k": _to_k(variables.get("total_words_numeric", 0)),
        "automated_tests": int(variables.get("repos_with_tests", 0)),
        "development_sprints": int(variables.get("sprints_completed", 0)),
        "code_files": int(variables.get("code_files", 0)),
        "test_files": int(variables.get("test_files", 0)),
        "ci_workflows": int(variables.get("ci_workflows", 0)),
        "dependency_edges": int(variables.get("dependency_edges", 0)),
        # Organism data (from snapshot.system)
        "density": sys.get("density", 0),
        "entities": sys.get("entities", 0),
        "edges": sys.get("edges", 0),
        "ammoi": sys.get("ammoi", ""),
        "organs": organs,
    }


def build_metrics_from_system_metrics(canonical: dict) -> dict:
    """Fallback: extract from system-metrics.json (less rich)."""
    c = canonical.get("computed", {})
    return {
        "total_repos": c.get("total_repos", 0),
        "active_repos": c.get("active_repos", 0),
        "archived_repos": c.get("archived_repos", 0),
        "organizations": c.get("total_organs", 8),
        "published_essays": c.get("published_essays", 0),
        "total_words_k": _to_k(c.get("total_words_numeric", 0)),
        "automated_tests": c.get("repos_with_tests", 0),
        "development_sprints": c.get("sprints_completed", 0),
        "code_files": c.get("code_files", 0),
        "test_files": c.get("test_files", 0),
        "ci_workflows": c.get("ci_workflows", 0),
        "dependency_edges": c.get("dependency_edges", 0),
        "density": 0,
        "entities": 0,
        "edges": 0,
        "ammoi": "",
        "organs": {},
    }


def _to_k(value: int | str) -> int:
    """Convert raw word count to K+ display value."""
    try:
        n = int(str(value).replace(",", ""))
        return max(1, n // 1000)
    except (ValueError, TypeError):
        return 0


def write_metrics_yaml(metrics: dict, path: Path, dry_run: bool = False) -> str:
    """Write config/metrics.yaml from computed metrics."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines = [
        f"# Application Pipeline: Canonical Metrics Source of Truth",
        f"# Auto-generated from ORGANVM ecosystem — {now}",
        f"# Source: system-snapshot.json → refresh_from_ecosystem.py",
        f"",
        f"system:",
        f"  total_repos: {metrics['total_repos']}",
        f"  active_repos: {metrics['active_repos']}",
        f"  archived_repos: {metrics['archived_repos']}",
        f"  organizations: {metrics['organizations']}",
        f"  published_essays: {metrics['published_essays']}",
        f"  total_words_k: {metrics['total_words_k']}",
        f"  automated_tests: {metrics['automated_tests']}",
        f"  development_sprints: {metrics['development_sprints']}",
        f"  code_files: {metrics['code_files']}",
        f"  test_files: {metrics['test_files']}",
        f"  ci_workflows: {metrics['ci_workflows']}",
        f"  dependency_edges: {metrics['dependency_edges']}",
    ]

    if metrics.get("density"):
        lines.extend([
            f"",
            f"organism:",
            f"  density: {metrics['density']}",
            f"  entities: {metrics['entities']}",
            f"  edges: {metrics['edges']}",
            f"  ammoi: \"{metrics['ammoi']}\"",
        ])

    if metrics.get("organs"):
        lines.extend(["", "organs:"])
        for key, count in sorted(metrics["organs"].items()):
            lines.append(f"  {key}: {count}")

    lines.append("")
    content = "\n".join(lines)

    if dry_run:
        return content

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return content


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Refresh pipeline metrics from ORGANVM ecosystem",
    )
    parser.add_argument(
        "--snapshot", default=str(SNAPSHOT_PATH),
        help="Path to system-snapshot.json",
    )
    parser.add_argument(
        "--metrics", default=str(SYSTEM_METRICS_PATH),
        help="Fallback: path to system-metrics.json",
    )
    parser.add_argument("--dry-run", action="store_true", help="Show changes without writing")
    parser.add_argument("--propagate", action="store_true",
                        help="Run check_metrics.py --fix --yes after updating")
    args = parser.parse_args()

    snapshot_path = Path(args.snapshot)
    metrics_path = Path(args.metrics)
    prefix = "[DRY RUN] " if args.dry_run else ""

    # Load ecosystem data
    if snapshot_path.is_file():
        snapshot = load_json(snapshot_path)
        metrics = build_metrics_from_snapshot(snapshot)
        source = f"system-snapshot.json ({snapshot.get('generated_at', 'unknown')[:19]})"
    elif metrics_path.is_file():
        canonical = load_json(metrics_path)
        metrics = build_metrics_from_system_metrics(canonical)
        source = "system-metrics.json (fallback)"
    else:
        print("ERROR: No ecosystem data source found.", file=sys.stderr)
        print(f"  Checked: {snapshot_path}", file=sys.stderr)
        print(f"  Checked: {metrics_path}", file=sys.stderr)
        return 1

    print(f"{prefix}Source: {source}")
    print(f"{prefix}  total_repos: {metrics['total_repos']}")
    print(f"{prefix}  active_repos: {metrics['active_repos']}")
    print(f"{prefix}  ci_workflows: {metrics['ci_workflows']}")
    print(f"{prefix}  density: {metrics.get('density', 0)}")

    # Write config/metrics.yaml
    content = write_metrics_yaml(metrics, CONFIG_METRICS, dry_run=args.dry_run)
    if args.dry_run:
        print(f"\n{prefix}Would write to {CONFIG_METRICS}:")
        for line in content.splitlines()[:10]:
            print(f"  {line}")
        print("  ...")
    else:
        print(f"{prefix}Written: {CONFIG_METRICS}")

    # Propagate to blocks/resumes
    if args.propagate and not args.dry_run:
        import subprocess
        print(f"\n{prefix}Running check_metrics.py --fix --yes ...")
        result = subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "check_metrics.py"),
             "--fix", "--yes"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        print(result.stdout)
        if result.returncode != 0:
            print(result.stderr, file=sys.stderr)
    elif args.propagate and args.dry_run:
        print(f"\n{prefix}Would run: check_metrics.py --fix --yes")

    return 0


if __name__ == "__main__":
    sys.exit(main())
