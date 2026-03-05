#!/usr/bin/env python3
"""Diagnostic tool — comprehensive system self-assessment producing a graded scorecard.

Runs objective collectors (automated measurements) and generates subjective
prompts (for AI raters) against the 8-dimension grading rubric.

Usage:
    python scripts/diagnose.py                      # Full report (objective only)
    python scripts/diagnose.py --json               # Structured JSON for IRA
    python scripts/diagnose.py --objective-only      # Only automated measurements
    python scripts/diagnose.py --subjective-only     # Only generate rater prompts
    python scripts/diagnose.py --rater-id opus       # Tag JSON output with rater name
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import yaml
from pipeline_lib import REPO_ROOT

RUBRIC_PATH = REPO_ROOT / "strategy" / "system-grading-rubric.yaml"
SCRIPTS_DIR = REPO_ROOT / "scripts"
TESTS_DIR = REPO_ROOT / "tests"
RATINGS_DIR = REPO_ROOT / "ratings"


def load_rubric() -> dict:
    """Load the system grading rubric."""
    with open(RUBRIC_PATH) as f:
        return yaml.safe_load(f)


def _run_cmd(cmd: list[str], timeout: int = 120) -> tuple[int, str]:
    """Run a command and return (returncode, combined output)."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
            cwd=str(REPO_ROOT),
        )
        output = (result.stdout + "\n" + result.stderr).strip()
        return result.returncode, output
    except subprocess.TimeoutExpired:
        return 1, "Command timed out"
    except FileNotFoundError:
        return 1, f"Command not found: {cmd[0]}"


# ---------------------------------------------------------------------------
# Objective collectors
# ---------------------------------------------------------------------------

def measure_test_coverage() -> dict:
    """Measure test count and verification matrix ratio."""
    # Count tests via pytest --co
    rc, output = _run_cmd([sys.executable, "-m", "pytest", "tests/", "--co", "-q"])
    test_count = 0
    if rc == 0:
        # Last line like "N tests collected"
        for line in output.strip().splitlines():
            m = re.search(r"(\d+)\s+tests?\s+", line)
            if m:
                test_count = int(m.group(1))

    # Verification matrix ratio
    rc2, output2 = _run_cmd([
        sys.executable, str(SCRIPTS_DIR / "verification_matrix.py"), "--strict",
    ])
    matrix_ratio = 0.0
    matrix_detail = ""
    if rc2 == 0:
        matrix_detail = "strict pass"
        matrix_ratio = 1.0
    else:
        # Try to extract ratio from output like "117/121 modules"
        m = re.search(r"(\d+)/(\d+)", output2)
        if m:
            covered, total = int(m.group(1)), int(m.group(2))
            matrix_ratio = covered / total if total > 0 else 0.0
            matrix_detail = f"{covered}/{total} modules"
        else:
            matrix_detail = "could not parse"

    # Score derivation
    if test_count >= 2000 and matrix_ratio >= 1.0:
        score = 10.0
    elif test_count >= 1000 and matrix_ratio >= 0.9:
        score = 7.0 + min(3.0, (test_count - 1000) / 1000 * 1.5 + (matrix_ratio - 0.9) / 0.1 * 1.5)
    elif test_count >= 500 and matrix_ratio >= 0.7:
        score = 5.0 + min(2.0, (test_count - 500) / 500 + (matrix_ratio - 0.7) / 0.2)
    elif test_count >= 100:
        score = 3.0 + min(2.0, (test_count - 100) / 400)
    else:
        score = max(1.0, test_count / 100 * 3.0)

    score = round(min(10.0, score), 1)

    return {
        "score": score,
        "confidence": "high",
        "evidence": f"{test_count} tests; matrix {matrix_detail}",
        "details": {
            "test_count": test_count,
            "matrix_ratio": round(matrix_ratio, 3),
            "matrix_detail": matrix_detail,
        },
    }


def measure_code_quality() -> dict:
    """Measure lint errors and type hint presence."""
    rc, output = _run_cmd([
        sys.executable, "-m", "ruff", "check", "scripts/", "tests/",
    ])
    lint_errors = 0
    if rc != 0:
        # Count lines that look like errors (file:line:col: CODE message)
        for line in output.strip().splitlines():
            if re.match(r".+:\d+:\d+:\s+\w+\d+", line):
                lint_errors += 1

    # Count type-hinted functions in scripts/
    hinted = 0
    total_funcs = 0
    for py_file in sorted(SCRIPTS_DIR.glob("*.py")):
        try:
            text = py_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("def "):
                total_funcs += 1
                if "->" in stripped or ": " in stripped.split("(", 1)[-1].split(")", 1)[0] if "(" in stripped else "":
                    hinted += 1

    hint_ratio = hinted / total_funcs if total_funcs > 0 else 0.0

    # Score
    if lint_errors == 0:
        score = 7.0 + min(3.0, hint_ratio * 3.0)
    elif lint_errors <= 10:
        score = 5.0 + min(2.0, (10 - lint_errors) / 10 * 2.0)
    elif lint_errors <= 50:
        score = 3.0 + (50 - lint_errors) / 40 * 2.0
    else:
        score = max(1.0, 3.0 - (lint_errors - 50) / 50)

    score = round(min(10.0, score), 1)

    return {
        "score": score,
        "confidence": "high",
        "evidence": f"{lint_errors} lint errors; {hinted}/{total_funcs} functions type-hinted",
        "details": {
            "lint_errors": lint_errors,
            "type_hinted_functions": hinted,
            "total_functions": total_funcs,
            "hint_ratio": round(hint_ratio, 3),
        },
    }


def measure_data_integrity() -> dict:
    """Measure validation and signal integrity error counts."""
    rc1, output1 = _run_cmd([
        sys.executable, str(SCRIPTS_DIR / "validate.py"),
        "--check-id-maps", "--check-rubric",
    ])
    val_errors = 0
    if rc1 != 0:
        for line in output1.strip().splitlines():
            low = line.lower()
            if "error" in low or "invalid" in low or "missing" in low:
                val_errors += 1

    rc2, output2 = _run_cmd([
        sys.executable, str(SCRIPTS_DIR / "validate_signals.py"), "--strict",
    ])
    sig_errors = 0
    if rc2 != 0:
        for line in output2.strip().splitlines():
            low = line.lower()
            if "error" in low or "invalid" in low or "fail" in low:
                sig_errors += 1

    total_errors = val_errors + sig_errors

    if total_errors == 0:
        score = 10.0
    elif total_errors <= 3:
        score = 7.0 + (3 - total_errors)
    elif total_errors <= 10:
        score = 5.0 + (10 - total_errors) / 7 * 2.0
    elif total_errors <= 30:
        score = 3.0 + (30 - total_errors) / 20 * 2.0
    else:
        score = max(1.0, 3.0 - (total_errors - 30) / 30)

    score = round(min(10.0, score), 1)

    return {
        "score": score,
        "confidence": "high",
        "evidence": f"{val_errors} validation errors; {sig_errors} signal errors",
        "details": {
            "validation_errors": val_errors,
            "signal_errors": sig_errors,
            "total_errors": total_errors,
        },
    }


def measure_operational_maturity() -> dict:
    """Measure launchd agent health, backup recency, and monitoring."""
    # Import launchd_manager for agent status
    try:
        import launchd_manager
        status = launchd_manager.get_agent_status()
        agent_total = status.get("total", 0)
        agent_healthy = status.get("healthy", False)
        agent_loaded = status.get("loaded_count", 0)
    except Exception:
        agent_total = 0
        agent_healthy = False
        agent_loaded = 0

    # Check backup recency
    backup_dir = REPO_ROOT / "backups"
    recent_backup = False
    backup_age_days = -1
    if backup_dir.is_dir():
        backups = sorted(backup_dir.glob("*.tar.gz"), key=lambda p: p.stat().st_mtime, reverse=True)
        if backups:
            import time
            age_seconds = time.time() - backups[0].stat().st_mtime
            backup_age_days = int(age_seconds / 86400)
            recent_backup = backup_age_days <= 7

    # Check notification config
    notify_config = REPO_ROOT / "strategy" / "notifications.yaml"
    has_notify = notify_config.is_file()

    # Score
    points = 0.0
    if agent_total >= 5:
        points += 3.0
    elif agent_total >= 2:
        points += 1.5
    if agent_healthy:
        points += 2.0
    if recent_backup:
        points += 2.0
    elif backup_age_days >= 0:
        points += 1.0
    if has_notify:
        points += 1.5

    score = round(max(1.0, min(10.0, 1.0 + points)), 1)

    return {
        "score": score,
        "confidence": "medium",
        "evidence": (
            f"{agent_loaded}/{agent_total} agents loaded; "
            f"backup {'<7d' if recent_backup else ('stale' if backup_age_days >= 0 else 'none')}; "
            f"notifications {'configured' if has_notify else 'missing'}"
        ),
        "details": {
            "agent_total": agent_total,
            "agent_loaded": agent_loaded,
            "agent_healthy": agent_healthy,
            "backup_age_days": backup_age_days,
            "notifications_configured": has_notify,
        },
    }


# ---------------------------------------------------------------------------
# Subjective prompt generators
# ---------------------------------------------------------------------------

def _read_file_excerpt(path: Path, max_lines: int = 80) -> str:
    """Read the first N lines of a file for prompt inclusion."""
    if not path.is_file():
        return f"[File not found: {path.relative_to(REPO_ROOT)}]"
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        excerpt = "\n".join(lines[:max_lines])
        if len(lines) > max_lines:
            excerpt += f"\n... ({len(lines) - max_lines} more lines)"
        return excerpt
    except OSError:
        return f"[Could not read: {path.relative_to(REPO_ROOT)}]"


def _list_scripts() -> list[str]:
    """List all Python scripts in scripts/ directory."""
    return sorted(p.name for p in SCRIPTS_DIR.glob("*.py") if not p.name.startswith("_"))


def generate_architecture_prompt() -> str:
    """Generate a prompt for rating architecture quality."""
    scripts = _list_scripts()
    module_arch = ""
    claude_md = REPO_ROOT / "CLAUDE.md"
    if claude_md.is_file():
        text = claude_md.read_text(encoding="utf-8", errors="replace")
        # Extract Module Architecture and Script Dependency Graph sections
        for section in ["Module Architecture", "Script Dependency Graph"]:
            marker = f"## {section}"
            if marker in text:
                start = text.index(marker)
                end = text.find("\n## ", start + len(marker))
                module_arch += text[start:end if end != -1 else start + 2000] + "\n\n"

    return f"""Rate the ARCHITECTURE of this application pipeline codebase (1-10 scale).

Scoring guide:
- 1: Monolithic scripts; no shared library; circular dependencies
- 3: Some extraction but inconsistent boundaries
- 5: Reasonable module split; some tight coupling
- 7: Clean module boundaries; extracted sub-modules; clear dependency graph
- 10: Exemplary decomposition; each module single-purpose; DAG dependency graph

Evidence to evaluate:

### Scripts directory ({len(scripts)} modules):
{chr(10).join(scripts)}

### Module architecture (from CLAUDE.md):
{module_arch if module_arch else '[Section not found in CLAUDE.md]'}

### pipeline_lib.py excerpt:
{_read_file_excerpt(SCRIPTS_DIR / 'pipeline_lib.py', 40)}

Provide:
1. A score (1-10, one decimal)
2. Key strengths
3. Key weaknesses
4. Your confidence level (high/medium/low)
"""


def generate_documentation_prompt() -> str:
    """Generate a prompt for rating documentation quality."""
    claude_md = REPO_ROOT / "CLAUDE.md"
    docs_files = sorted(p.name for p in (REPO_ROOT / "docs").glob("*")) if (REPO_ROOT / "docs").is_dir() else []

    return f"""Rate the DOCUMENTATION quality of this application pipeline codebase (1-10 scale).

Scoring guide:
- 1: No README; no inline docs; undocumented scripts
- 3: Basic README; some docstrings; missing architecture docs
- 5: Decent CLAUDE.md; docstrings on most scripts
- 7: Comprehensive CLAUDE.md; all scripts have docstrings; architecture documented
- 10: Exemplary CLAUDE.md; full docstrings; handoff doc; SOP library

Evidence to evaluate:

### CLAUDE.md excerpt (first 100 lines):
{_read_file_excerpt(claude_md, 100)}

### docs/ directory contents:
{chr(10).join(docs_files) if docs_files else '[No docs/ directory]'}

### Sample script docstrings:
{_read_file_excerpt(SCRIPTS_DIR / 'standup.py', 15)}
---
{_read_file_excerpt(SCRIPTS_DIR / 'score.py', 15)}
---
{_read_file_excerpt(SCRIPTS_DIR / 'diagnose.py', 15)}

Provide:
1. A score (1-10, one decimal)
2. Key strengths
3. Key weaknesses
4. Your confidence level (high/medium/low)
"""


def generate_analytics_prompt() -> str:
    """Generate a prompt for rating analytics and intelligence."""
    analytics_scripts = [
        "funnel_report.py", "score.py", "snapshot.py",
        "rejection_learner.py", "org_intelligence.py", "block_outcomes.py",
    ]
    excerpts = []
    for name in analytics_scripts:
        p = SCRIPTS_DIR / name
        if p.is_file():
            excerpts.append(f"### {name}:\n{_read_file_excerpt(p, 20)}")

    return f"""Rate the ANALYTICS & INTELLIGENCE capability of this pipeline (1-10 scale).

Scoring guide:
- 1: No analytics; manual tracking; no scoring model
- 3: Basic counts; simple scoring
- 5: Funnel report exists; scoring model with some dimensions
- 7: Full funnel + conversion analytics; 9-dimension scoring; snapshot trends
- 10: Comprehensive analytics suite; scoring with auto-derive; trend regression; block-outcome correlation; org intelligence

Evidence to evaluate:

{chr(10).join(excerpts)}

Provide:
1. A score (1-10, one decimal)
2. Key strengths
3. Key weaknesses
4. Your confidence level (high/medium/low)
"""


def generate_sustainability_prompt() -> str:
    """Generate a prompt for rating sustainability / bus factor."""
    docs_files = sorted(p.name for p in (REPO_ROOT / "docs").glob("*")) if (REPO_ROOT / "docs").is_dir() else []
    launchd_files = sorted(p.name for p in (REPO_ROOT / "launchd").glob("*")) if (REPO_ROOT / "launchd").is_dir() else []

    return f"""Rate the SUSTAINABILITY of this pipeline for a single-operator context (1-10 scale).

Scoring guide:
- 1: Fully manual; no docs; impossible to hand off
- 3: Some automation; sparse docs; significant tribal knowledge
- 5: Moderate automation; CLAUDE.md helps; still needs original operator context
- 7: Good automation; clear docs; another operator could run daily workflow
- 10: Autonomous daily ops; comprehensive docs + SOPs; any AI/human can onboard from CLAUDE.md alone

Evidence to evaluate:

### Automation (launchd agents):
{chr(10).join(launchd_files) if launchd_files else '[No launchd/ directory]'}

### Documentation:
{chr(10).join(docs_files) if docs_files else '[No docs/ directory]'}

### Quick commands excerpt (run.py):
{_read_file_excerpt(SCRIPTS_DIR / 'run.py', 50)}

### CLAUDE.md session sequences and commands:
(See CLAUDE.md for full command table — {len(_list_scripts())} scripts available)

Provide:
1. A score (1-10, one decimal)
2. Key strengths
3. Key weaknesses
4. Your confidence level (high/medium/low)
"""


# ---------------------------------------------------------------------------
# Composite scoring
# ---------------------------------------------------------------------------

OBJECTIVE_DIMENSIONS = ["test_coverage", "code_quality", "data_integrity", "operational_maturity"]
SUBJECTIVE_DIMENSIONS = ["architecture", "documentation", "analytics_intelligence", "sustainability"]

COLLECTORS = {
    "test_coverage": measure_test_coverage,
    "code_quality": measure_code_quality,
    "data_integrity": measure_data_integrity,
    "operational_maturity": measure_operational_maturity,
}

PROMPT_GENERATORS = {
    "architecture": generate_architecture_prompt,
    "documentation": generate_documentation_prompt,
    "analytics_intelligence": generate_analytics_prompt,
    "sustainability": generate_sustainability_prompt,
}


def compute_diagnostic_score(
    scores: dict[str, dict],
    rubric: dict,
) -> float:
    """Compute weighted composite score from dimension scores."""
    dimensions = rubric.get("dimensions", {})
    total = 0.0
    weight_sum = 0.0
    for dim_key, dim_cfg in dimensions.items():
        weight = dim_cfg.get("weight", 0.0)
        if dim_key in scores and scores[dim_key].get("score") is not None:
            total += weight * scores[dim_key]["score"]
            weight_sum += weight
    if weight_sum == 0:
        return 0.0
    return round(total / weight_sum * weight_sum / weight_sum * (total / weight_sum), 1)


def compute_composite(scores: dict[str, dict], rubric: dict) -> float:
    """Compute weighted composite — simpler correct version."""
    dims = rubric.get("dimensions", {})
    total = 0.0
    for dim_key, dim_cfg in dims.items():
        w = dim_cfg.get("weight", 0.0)
        if dim_key in scores and scores[dim_key].get("score") is not None:
            total += w * scores[dim_key]["score"]
    return round(total, 1)


# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------

def format_human_report(scores: dict[str, dict], rubric: dict) -> str:
    """Format a human-readable scorecard."""
    dims = rubric.get("dimensions", {})
    lines = [
        "=" * 65,
        "  APPLICATION PIPELINE — DIAGNOSTIC SCORECARD",
        "=" * 65,
        "",
        f"  {'Dimension':<25s} {'Score':>6s}  {'Weight':>6s}  {'Weighted':>8s}  Evidence",
        "  " + "-" * 60,
    ]

    composite = 0.0
    for dim_key in dims:
        cfg = dims[dim_key]
        label = cfg.get("label", dim_key)
        weight = cfg.get("weight", 0.0)
        if dim_key in scores:
            s = scores[dim_key]
            sc = s.get("score", 0.0)
            if sc is None:
                sc = 0.0
            weighted = round(weight * sc, 2)
            composite += weighted
            ev = s.get("evidence", "")
            if len(ev) > 35:
                ev = ev[:32] + "..."
            lines.append(f"  {label:<25s} {sc:>6.1f}  {weight:>6.2f}  {weighted:>8.2f}  {ev}")
        else:
            lines.append(f"  {label:<25s}   {'—':>4s}  {weight:>6.2f}  {'—':>8s}  (not rated)")

    lines.append("  " + "-" * 60)
    lines.append(f"  {'COMPOSITE':<25s} {composite:>6.1f}  {'1.00':>6s}")
    lines.append("")

    # Subjective prompts not yet rated
    unrated = [k for k in SUBJECTIVE_DIMENSIONS if k not in scores]
    if unrated:
        lines.append(f"  Unrated subjective dimensions: {', '.join(unrated)}")
        lines.append("  Run with --subjective-only to generate prompts for AI raters.")
    lines.append("")
    return "\n".join(lines)


def format_json_output(
    scores: dict[str, dict],
    rubric: dict,
    rater_id: str = "local-objective",
) -> dict:
    """Format structured JSON for IRA consumption."""
    composite = compute_composite(scores, rubric)
    return {
        "rater_id": rater_id,
        "timestamp": datetime.now(UTC).isoformat(),
        "rubric_version": rubric.get("version", "unknown"),
        "dimensions": scores,
        "composite": composite,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Diagnostic tool — system self-assessment scorecard",
    )
    parser.add_argument("--json", action="store_true", help="Output structured JSON for IRA")
    parser.add_argument("--objective-only", action="store_true", help="Only run automated measurements")
    parser.add_argument("--subjective-only", action="store_true", help="Only generate rater prompts")
    parser.add_argument("--rater-id", default="local-objective", help="Rater ID for JSON output")
    args = parser.parse_args()

    rubric = load_rubric()
    scores: dict[str, dict] = {}

    if args.subjective_only:
        # Generate prompts for AI raters
        print("=" * 65)
        print("  SUBJECTIVE RATING PROMPTS")
        print("=" * 65)
        for dim_key, generator in PROMPT_GENERATORS.items():
            label = rubric["dimensions"][dim_key].get("label", dim_key)
            print(f"\n{'─' * 65}")
            print(f"  DIMENSION: {label} (weight: {rubric['dimensions'][dim_key]['weight']})")
            print(f"{'─' * 65}\n")
            print(generator())
        return

    # Run objective collectors
    if not args.subjective_only:
        for dim_key, collector in COLLECTORS.items():
            scores[dim_key] = collector()

    if args.json:
        output = format_json_output(scores, rubric, rater_id=args.rater_id)
        RATINGS_DIR.mkdir(exist_ok=True)
        print(json.dumps(output, indent=2))
    else:
        print(format_human_report(scores, rubric))


if __name__ == "__main__":
    main()
