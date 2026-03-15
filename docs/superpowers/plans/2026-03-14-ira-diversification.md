# IRA Diversification Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace single-model IRA panel (ICC=0.086) with multi-model, multi-persona architecture producing genuine evaluative disagreement.

**Architecture:** New `generate_ratings.py` orchestrates 4 AI raters (Opus/Sonnet/Haiku/Gemini) with distinct personas. Each rater evaluates 4 subjective dimensions via API calls. `diagnose_ira.py` gains dimension partitioning to compute ICC on subjective dimensions only. Config-driven panel in `system-grading-rubric.yaml`.

**Tech Stack:** Python 3.11+, anthropic SDK (new), google-genai (existing), PyYAML, pytest

**Spec:** `docs/superpowers/specs/2026-03-14-ira-diversification-design.md`

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `strategy/rater-personas.yaml` | CREATE | Persona role + scoring_bias prompts for 4 rater archetypes |
| `strategy/system-grading-rubric.yaml` | MODIFY | Add `ira.panel` config with model/provider/persona/temperature per rater |
| `pyproject.toml` | MODIFY | Add `anthropic` to runtime dependencies |
| `scripts/generate_ratings.py` | CREATE | Multi-model rating session orchestrator |
| `scripts/diagnose_ira.py` | MODIFY | Add `partition_dimensions()`, ground truth reporting |
| `scripts/run.py` | MODIFY | Add `rateall` command |
| `scripts/cli.py` | MODIFY | Add `rate` command |
| `scripts/mcp_server.py` | MODIFY | Add `pipeline_rate` tool |
| `tests/test_generate_ratings.py` | CREATE | 9 tests for rating generation |
| `tests/test_diagnose_ira.py` | MODIFY | 4 new tests for dimension partitioning |
| `CLAUDE.md` | MODIFY | Document generate_ratings.py, rateall command |

---

## Chunk 1: Configuration & Dependencies

### Task 1: Create rater-personas.yaml

**Files:**
- Create: `strategy/rater-personas.yaml`

- [ ] **Step 1: Create the persona config file**

```yaml
# Rater persona prompts for IRA grade norming.
# Each persona defines a role (identity framing) and scoring_bias (variance driver).
# Referenced by rater_id in system-grading-rubric.yaml ira.panel[].persona.

systems-architect:
  role: >-
    You are a systems architect evaluating software quality.
    You prioritize clean abstractions, dependency flow clarity,
    module boundary discipline, and scalability potential.
    You are skeptical of convenience shortcuts that create coupling.
    You weigh architectural purity highly, even at the cost of
    operational simplicity.
  scoring_bias: >-
    When in doubt, penalize tight coupling and reward separation
    of concerns. A system that's hard to reason about modularly
    scores lower even if it "works."

qa-lead:
  role: >-
    You are a QA lead evaluating software quality.
    You prioritize testability, edge case coverage, failure mode
    documentation, validation rigor, and regression safety.
    You are skeptical of code that's hard to test in isolation.
    You weigh defensive programming highly.
  scoring_bias: >-
    When in doubt, penalize untestable designs and reward explicit
    error handling. Systems that rely on happy-path assumptions
    score lower.

pragmatic-operator:
  role: >-
    You are a pragmatic operator who will run this system daily.
    You prioritize onboarding speed, cognitive load reduction,
    command discoverability, and low maintenance burden.
    You are skeptical of over-engineering and complexity that
    doesn't reduce daily toil.
  scoring_bias: >-
    When in doubt, penalize complexity and reward simplicity.
    A system that requires reading 400 lines of CLAUDE.md to
    operate has a documentation problem, not a documentation
    strength.

external-auditor:
  role: >-
    You are an external auditor reviewing this system for the
    first time. You prioritize evidence quality, claim sourcing,
    documentation completeness, and whether stated capabilities
    match observable artifacts.
    You are skeptical of self-reported metrics.
  scoring_bias: >-
    When in doubt, penalize unverifiable claims and reward
    transparent evidence chains. High scores require proof,
    not assertion.
```

- [ ] **Step 2: Commit**

```bash
git add strategy/rater-personas.yaml
git commit -m "feat: add rater persona prompts for IRA diversification"
```

### Task 2: Extend rubric with panel config

**Files:**
- Modify: `strategy/system-grading-rubric.yaml:253-273`

- [ ] **Step 1: Replace the existing `ira` section**

Replace the current `ira:` block (lines 253-273) with:

```yaml
ira:
  min_raters: 3
  max_raters: 7
  panel:
    - rater_id: architect-opus
      model: claude-opus-4-6
      provider: anthropic
      persona: systems-architect
      temperature: 0.7
    - rater_id: qa-sonnet
      model: claude-sonnet-4-6
      provider: anthropic
      persona: qa-lead
      temperature: 0.7
    - rater_id: pragmatist-haiku
      model: claude-haiku-4-5-20251001
      provider: anthropic
      persona: pragmatic-operator
      temperature: 0.8
    - rater_id: auditor-gemini
      model: gemini-2.0-flash
      provider: google
      persona: external-auditor
      temperature: 0.7
  interpretation_bands:
    poor: [-1.0, 0.00]
    slight: [0.00, 0.20]
    fair: [0.21, 0.40]
    moderate: [0.41, 0.60]
    substantial: [0.61, 0.80]
    almost_perfect: [0.81, 1.00]
  consensus:
    method: median
    outlier_iqr_factor: 1.5
    re_rate_threshold: 0.61
```

- [ ] **Step 2: Commit**

```bash
git add strategy/system-grading-rubric.yaml
git commit -m "feat: add IRA panel config with 4 diverse raters"
```

### Task 3: Add anthropic dependency

**Files:**
- Modify: `pyproject.toml:8-14`

- [ ] **Step 1: Add anthropic to dependencies list**

Change the `dependencies` list at line 8-14 from:

```toml
dependencies = [
    "pyyaml",
    "ruamel.yaml",
    "typer",
    "google-genai",
    "mcp",
]
```

to:

```toml
dependencies = [
    "pyyaml",
    "ruamel.yaml",
    "typer",
    "anthropic",
    "google-genai",
    "mcp",
]
```

- [ ] **Step 2: Install the new dependency**

Run: `cd /Users/4jp/Workspace/4444J99/application-pipeline && .venv/bin/pip install -e ".[dev]"`
Expected: `anthropic` installed successfully

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "chore: add anthropic SDK to runtime dependencies"
```

---

## Chunk 2: Core Rating Generation (TDD)

### Task 4: Write test scaffolding for generate_ratings

**Files:**
- Create: `tests/test_generate_ratings.py`

- [ ] **Step 1: Write test file with first 3 tests**

```python
"""Tests for generate_ratings.py — multi-model IRA rating session."""

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from generate_ratings import (
    build_system_prompt,
    call_model,
    load_panel_config,
    load_personas,
    validate_response,
)


class TestPanelConfig:
    def test_panel_config_loads(self):
        """Panel config from rubric has required fields."""
        panel = load_panel_config()
        assert len(panel) >= 4
        for rater in panel:
            assert "rater_id" in rater
            assert "model" in rater
            assert "provider" in rater
            assert "persona" in rater
            assert "temperature" in rater

    def test_persona_prompts_load(self):
        """All personas referenced in panel exist in rater-personas.yaml."""
        panel = load_panel_config()
        personas = load_personas()
        for rater in panel:
            persona_key = rater["persona"]
            assert persona_key in personas, f"Missing persona: {persona_key}"
            assert "role" in personas[persona_key]
            assert "scoring_bias" in personas[persona_key]


class TestResponseValidation:
    def test_response_parsing_valid_json(self):
        """Valid model response parsed into rating schema."""
        response = {
            "architecture": {"score": 8.0, "confidence": "medium", "evidence": "test"},
            "documentation": {"score": 7.5, "confidence": "high", "evidence": "test"},
            "analytics_intelligence": {"score": 8.5, "confidence": "medium", "evidence": "test"},
            "sustainability": {"score": 7.0, "confidence": "medium", "evidence": "test"},
        }
        assert validate_response(response) is True

    def test_response_parsing_malformed(self):
        """Missing dimensions rejected."""
        response = {
            "architecture": {"score": 8.0, "confidence": "medium", "evidence": "test"},
            # Missing 3 dimensions
        }
        assert validate_response(response) is False

    def test_response_out_of_range(self):
        """Score outside 1.0-10.0 rejected."""
        response = {
            "architecture": {"score": 15.0, "confidence": "medium", "evidence": "test"},
            "documentation": {"score": 7.5, "confidence": "high", "evidence": "test"},
            "analytics_intelligence": {"score": 8.5, "confidence": "medium", "evidence": "test"},
            "sustainability": {"score": 7.0, "confidence": "medium", "evidence": "test"},
        }
        assert validate_response(response) is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/4jp/Workspace/4444J99/application-pipeline && .venv/bin/python -m pytest tests/test_generate_ratings.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'generate_ratings'`

### Task 5: Implement generate_ratings.py core

**Files:**
- Create: `scripts/generate_ratings.py`

- [ ] **Step 1: Write the full script**

```python
#!/usr/bin/env python3
"""Multi-model IRA rating session orchestrator.

Generates subjective dimension ratings from a diverse AI panel,
merges with objective ground truth from diagnose.py collectors,
and saves rating JSON files for IRA computation.

Usage:
    python scripts/generate_ratings.py                        # Full session
    python scripts/generate_ratings.py --rater architect-opus  # Single rater
    python scripts/generate_ratings.py --dry-run               # Show prompts only
    python scripts/generate_ratings.py --compute-ira           # Run IRA after
"""

import argparse
import json
import os
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import yaml
from diagnose import (
    COLLECTORS,
    OBJECTIVE_DIMENSIONS,
    PROMPT_GENERATORS,
    SUBJECTIVE_DIMENSIONS,
    compute_composite,
    load_rubric,
)
from pipeline_lib import REPO_ROOT

RATINGS_DIR = REPO_ROOT / "ratings"
PERSONAS_PATH = REPO_ROOT / "strategy" / "rater-personas.yaml"


def load_panel_config() -> list[dict]:
    """Load rater panel config from system-grading-rubric.yaml."""
    rubric = load_rubric()
    return rubric.get("ira", {}).get("panel", [])


def load_personas() -> dict:
    """Load persona prompts from rater-personas.yaml."""
    with open(PERSONAS_PATH) as f:
        return yaml.safe_load(f)


def archive_existing_ratings() -> None:
    """Move existing rating JSON files to dated archive directory."""
    if not RATINGS_DIR.is_dir():
        return
    date_str = datetime.now(UTC).strftime("%Y-%m-%d")
    archive_dir = RATINGS_DIR / "archive" / date_str
    for f in RATINGS_DIR.glob("*.json"):
        if f.name.startswith("consensus-"):
            continue
        archive_dir.mkdir(parents=True, exist_ok=True)
        shutil.move(str(f), str(archive_dir / f.name))


def build_system_prompt(persona: dict, rubric: dict) -> str:
    """Build system prompt from persona + rubric scoring guides."""
    dims = rubric.get("dimensions", {})
    subjective_dims = {k: v for k, v in dims.items() if k in SUBJECTIVE_DIMENSIONS}

    rubric_context = ""
    for dim_key, dim_cfg in subjective_dims.items():
        rubric_context += f"\n### {dim_cfg.get('label', dim_key)}\n"
        rubric_context += f"{dim_cfg.get('description', '')}\n"
        guide = dim_cfg.get("scoring_guide", {})
        for score_val in sorted(guide.keys()):
            rubric_context += f"  {score_val}: {guide[score_val]}\n"

    dim_keys = list(subjective_dims.keys())
    return (
        f"{persona['role']}\n\n{persona['scoring_bias']}\n\n"
        f"You are rating a software system against this rubric:\n{rubric_context}\n\n"
        f"Respond with ONLY valid JSON. No markdown, no explanation, no code fences.\n"
        f"Return a JSON object with exactly these keys: {dim_keys}\n"
        f"Each value must be an object with: "
        f'"score" (float 1.0-10.0), "confidence" ("high"/"medium"/"low"), '
        f'"evidence" (string), "strengths" (list of strings), "weaknesses" (list of strings).'
    )


def validate_response(response: dict) -> bool:
    """Validate response has all subjective dimensions with valid scores."""
    for dim in SUBJECTIVE_DIMENSIONS:
        if dim not in response:
            return False
        dim_data = response[dim]
        if not isinstance(dim_data, dict):
            return False
        score = dim_data.get("score")
        if score is None:
            return False
        try:
            score_f = float(score)
        except (TypeError, ValueError):
            return False
        if not (1.0 <= score_f <= 10.0):
            return False
    return True


def _call_anthropic(model: str, system_prompt: str, user_prompt: str, temperature: float) -> dict:
    """Call Anthropic API and return parsed JSON."""
    import anthropic

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=model,
        max_tokens=4096,
        temperature=temperature,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return json.loads(response.content[0].text)


def _call_google(model: str, system_prompt: str, user_prompt: str, temperature: float) -> dict:
    """Call Google Gemini API and return parsed JSON."""
    from google import genai
    from google.genai import types

    client = genai.Client()
    response = client.models.generate_content(
        model=model,
        contents=f"{system_prompt}\n\n{user_prompt}",
        config=types.GenerateContentConfig(
            temperature=temperature,
            response_mime_type="application/json",
        ),
    )
    return json.loads(response.text)


def call_model(provider: str, model: str, system_prompt: str, user_prompt: str, temperature: float) -> dict:
    """Dispatch to the appropriate provider's API."""
    if provider == "anthropic":
        return _call_anthropic(model, system_prompt, user_prompt, temperature)
    elif provider == "google":
        return _call_google(model, system_prompt, user_prompt, temperature)
    else:
        raise ValueError(f"Unknown provider: {provider}")


def generate_ratings(
    dry_run: bool = False,
    single_rater: str | None = None,
    compute_ira: bool = False,
) -> dict:
    """Run a full multi-model rating session.

    Returns:
        dict with status and list of rater IDs that completed.
    """
    rubric = load_rubric()
    personas = load_personas()
    panel = load_panel_config()

    if not panel:
        return {"status": "error", "error": "No panel config in ira.panel"}

    if single_rater:
        panel = [r for r in panel if r["rater_id"] == single_rater]
        if not panel:
            return {"status": "error", "error": f"Rater '{single_rater}' not in panel"}

    # Check API keys for configured providers
    providers_needed = {r["provider"] for r in panel}
    if "anthropic" in providers_needed and not os.environ.get("ANTHROPIC_API_KEY"):
        return {"status": "error", "error": "Set ANTHROPIC_API_KEY environment variable"}
    if "google" in providers_needed and not os.environ.get("GOOGLE_API_KEY"):
        return {"status": "error", "error": "Set GOOGLE_API_KEY environment variable"}

    # Run objective collectors once
    print("Running objective collectors...", file=sys.stderr)
    objective_scores = {}
    for dim_key, collector in COLLECTORS.items():
        objective_scores[dim_key] = collector()

    # Combine subjective prompts into one evidence package
    evidence_parts = []
    for dim_key, generator in PROMPT_GENERATORS.items():
        evidence_parts.append(f"## {dim_key}\n{generator()}")
    combined_evidence = "\n\n---\n\n".join(evidence_parts)

    if dry_run:
        for rater_cfg in panel:
            persona = personas.get(rater_cfg["persona"], {})
            system_prompt = build_system_prompt(persona, rubric)
            print(f"\n{'=' * 60}")
            print(f"RATER: {rater_cfg['rater_id']} ({rater_cfg['model']})")
            print(f"{'=' * 60}")
            print(f"\nSYSTEM PROMPT:\n{system_prompt[:500]}...")
            print(f"\nEVIDENCE:\n{combined_evidence[:500]}...")
        return {"status": "dry_run", "raters": [r["rater_id"] for r in panel]}

    # Archive existing rating files
    archive_existing_ratings()
    RATINGS_DIR.mkdir(exist_ok=True)

    completed = []
    for rater_cfg in panel:
        rater_id = rater_cfg["rater_id"]
        persona = personas.get(rater_cfg["persona"])
        if not persona:
            print(f"Warning: persona '{rater_cfg['persona']}' missing, skipping {rater_id}", file=sys.stderr)
            continue

        system_prompt = build_system_prompt(persona, rubric)
        print(f"  Rating: {rater_id} ({rater_cfg['model']})...", file=sys.stderr)

        # Call with one retry on failure
        response = None
        for attempt in range(2):
            try:
                response = call_model(
                    provider=rater_cfg["provider"],
                    model=rater_cfg["model"],
                    system_prompt=system_prompt,
                    user_prompt=combined_evidence,
                    temperature=rater_cfg.get("temperature", 0.7),
                )
                break
            except Exception as e:
                if attempt == 0:
                    print(f"  Warning: {rater_id} attempt 1 failed: {e}, retrying...", file=sys.stderr)
                else:
                    print(f"  Warning: {rater_id} retry failed: {e}, skipping", file=sys.stderr)

        if response is None or not validate_response(response):
            if response is not None:
                print(f"  Warning: {rater_id} returned invalid response, skipping", file=sys.stderr)
            continue

        # Merge objective ground truth + subjective ratings
        all_scores = dict(objective_scores)
        for dim_key in SUBJECTIVE_DIMENSIONS:
            if dim_key in response:
                all_scores[dim_key] = response[dim_key]

        rating = {
            "rater_id": rater_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "rubric_version": rubric.get("version", "unknown"),
            "dimensions": all_scores,
            "composite": compute_composite(all_scores, rubric),
        }

        rating_path = RATINGS_DIR / f"{rater_id}.json"
        with open(rating_path, "w") as f:
            json.dump(rating, f, indent=2)

        completed.append(rater_id)
        print(f"  {rater_id}: composite={rating['composite']}", file=sys.stderr)

    # Optionally compute IRA
    if compute_ira and len(completed) >= 2:
        from diagnose_ira import discover_rating_files, generate_json_report, load_ratings

        files = discover_rating_files()
        ratings = load_ratings(files)
        ira = generate_json_report(ratings, show_consensus=True)

        consensus_path = RATINGS_DIR / f"consensus-{datetime.now(UTC).strftime('%Y-%m-%d')}.json"
        with open(consensus_path, "w") as f:
            json.dump(ira, f, indent=2)
        icc_key = "subjective_icc" if "subjective_icc" in ira else "overall_icc"
        print(f"\n  IRA: ICC={ira.get(icc_key, '?')}", file=sys.stderr)

    return {"status": "success", "raters": completed}


def main():
    parser = argparse.ArgumentParser(description="Multi-model IRA rating session")
    parser.add_argument("--rater", help="Run single rater only")
    parser.add_argument("--dry-run", action="store_true", help="Show prompts without API calls")
    parser.add_argument("--compute-ira", action="store_true", help="Compute IRA after rating")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    result = generate_ratings(
        dry_run=args.dry_run,
        single_rater=args.rater,
        compute_ira=args.compute_ira,
    )

    if args.json:
        print(json.dumps(result, indent=2))
    elif result["status"] == "error":
        print(f"Error: {result['error']}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the first 5 tests**

Run: `cd /Users/4jp/Workspace/4444J99/application-pipeline && .venv/bin/python -m pytest tests/test_generate_ratings.py -v`
Expected: 5 PASS (panel config, persona load, valid response, malformed, out of range)

- [ ] **Step 3: Commit**

```bash
git add scripts/generate_ratings.py tests/test_generate_ratings.py
git commit -m "feat: add multi-model rating generation with TDD tests"
```

### Task 6: Add API mock tests

**Files:**
- Modify: `tests/test_generate_ratings.py`

- [ ] **Step 1: Add 4 more tests to the test file**

Append to `tests/test_generate_ratings.py`:

```python
class TestAPIIntegration:
    def test_call_anthropic_formats_request(self, monkeypatch):
        """Anthropic API call builds correct message structure."""
        captured = {}

        class FakeContent:
            text = json.dumps({
                "architecture": {"score": 8.0, "confidence": "high", "evidence": "test"},
                "documentation": {"score": 7.0, "confidence": "high", "evidence": "test"},
                "analytics_intelligence": {"score": 8.5, "confidence": "high", "evidence": "test"},
                "sustainability": {"score": 7.5, "confidence": "high", "evidence": "test"},
            })

        class FakeResponse:
            content = [FakeContent()]

        class FakeClient:
            class messages:
                @staticmethod
                def create(**kwargs):
                    captured.update(kwargs)
                    return FakeResponse()

        monkeypatch.setattr("generate_ratings.anthropic", MagicMock())
        import generate_ratings
        monkeypatch.setattr(generate_ratings, "_call_anthropic", lambda m, s, u, t: (
            captured.update({"model": m, "system": s, "user": u, "temperature": t}),
            json.loads(FakeContent.text),
        )[1])

        result = call_model("anthropic", "claude-opus-4-6", "sys", "user", 0.7)
        assert captured["model"] == "claude-opus-4-6"
        assert captured["temperature"] == 0.7
        assert "architecture" in result

    def test_call_google_formats_request(self, monkeypatch):
        """Google API call builds correct message structure."""
        captured = {}

        import generate_ratings
        monkeypatch.setattr(generate_ratings, "_call_google", lambda m, s, u, t: (
            captured.update({"model": m, "temperature": t}),
            {
                "architecture": {"score": 7.5, "confidence": "high", "evidence": "test"},
                "documentation": {"score": 8.0, "confidence": "high", "evidence": "test"},
                "analytics_intelligence": {"score": 7.0, "confidence": "high", "evidence": "test"},
                "sustainability": {"score": 6.5, "confidence": "high", "evidence": "test"},
            },
        )[1])

        result = call_model("google", "gemini-2.0-flash", "sys", "user", 0.7)
        assert captured["model"] == "gemini-2.0-flash"
        assert "architecture" in result


class TestDryRun:
    def test_dry_run_no_api_calls(self, monkeypatch, capsys):
        """--dry-run prints prompts without making any API calls."""
        api_called = {"count": 0}

        import generate_ratings

        def fake_call(*args, **kwargs):
            api_called["count"] += 1
            return {}

        monkeypatch.setattr(generate_ratings, "call_model", fake_call)
        result = generate_ratings.generate_ratings(dry_run=True)

        assert result["status"] == "dry_run"
        assert api_called["count"] == 0
        assert len(result["raters"]) >= 4


class TestAPIKeyCheck:
    def test_missing_api_key_error(self, monkeypatch):
        """Clear error when ANTHROPIC_API_KEY is missing."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

        import generate_ratings
        result = generate_ratings.generate_ratings()

        assert result["status"] == "error"
        assert "API_KEY" in result["error"]
```

- [ ] **Step 2: Run all tests**

Run: `cd /Users/4jp/Workspace/4444J99/application-pipeline && .venv/bin/python -m pytest tests/test_generate_ratings.py -v`
Expected: 9 PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_generate_ratings.py
git commit -m "test: add API mock and dry-run tests for rating generation"
```

### Task 7: Add objective scores sharing test

**Files:**
- Modify: `tests/test_generate_ratings.py`

- [ ] **Step 1: Add the ground truth sharing test**

Append to `tests/test_generate_ratings.py`:

```python
from generate_ratings import RATINGS_DIR, archive_existing_ratings, build_system_prompt
from diagnose import OBJECTIVE_DIMENSIONS, SUBJECTIVE_DIMENSIONS


class TestObjectiveSharing:
    def test_objective_scores_shared(self, tmp_path, monkeypatch):
        """Objective ground truth injected into all rater outputs identically."""
        import generate_ratings

        # Mock ratings dir to tmp
        monkeypatch.setattr(generate_ratings, "RATINGS_DIR", tmp_path / "ratings")

        # Mock collectors to return known values
        fake_objective = {
            "test_coverage": {"score": 10.0, "evidence": "fake"},
            "code_quality": {"score": 9.0, "evidence": "fake"},
            "data_integrity": {"score": 10.0, "evidence": "fake"},
            "operational_maturity": {"score": 8.0, "evidence": "fake"},
            "claim_provenance": {"score": 5.0, "evidence": "fake"},
        }
        monkeypatch.setattr(generate_ratings, "COLLECTORS", {
            k: (lambda v=v: v) for k, v in fake_objective.items()
        })

        # Mock model calls to return valid subjective scores
        call_count = {"n": 0}

        def fake_call(provider, model, sys_prompt, user_prompt, temp):
            call_count["n"] += 1
            return {
                "architecture": {"score": 7.0 + call_count["n"], "confidence": "high", "evidence": "t"},
                "documentation": {"score": 6.0 + call_count["n"], "confidence": "high", "evidence": "t"},
                "analytics_intelligence": {"score": 8.0, "confidence": "high", "evidence": "t"},
                "sustainability": {"score": 7.0, "confidence": "high", "evidence": "t"},
            }

        monkeypatch.setattr(generate_ratings, "call_model", fake_call)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "fake")
        monkeypatch.setenv("GOOGLE_API_KEY", "fake")

        result = generate_ratings.generate_ratings()
        assert result["status"] == "success"

        # Check that all rating files have identical objective scores
        ratings_dir = tmp_path / "ratings"
        rating_files = list(ratings_dir.glob("*.json"))
        assert len(rating_files) >= 2

        import json
        for rf in rating_files:
            data = json.loads(rf.read_text())
            for obj_dim in OBJECTIVE_DIMENSIONS:
                assert data["dimensions"][obj_dim]["score"] == fake_objective[obj_dim]["score"]
```

- [ ] **Step 2: Run full test suite**

Run: `cd /Users/4jp/Workspace/4444J99/application-pipeline && .venv/bin/python -m pytest tests/test_generate_ratings.py -v`
Expected: 10 PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_generate_ratings.py
git commit -m "test: verify objective ground truth shared across all raters"
```

---

## Chunk 3: ICC Partition Fix (TDD)

### Task 8: Write failing tests for dimension partitioning

**Files:**
- Modify: `tests/test_diagnose_ira.py`

- [ ] **Step 1: Add 4 new tests at the end of the file**

Append to `tests/test_diagnose_ira.py`:

```python
class TestDimensionPartitioning:
    """Tests for objective/subjective dimension separation in IRA."""

    def test_partition_dimensions_by_type(self):
        """Objective/subjective split matches diagnose.py constants."""
        from diagnose import OBJECTIVE_DIMENSIONS, SUBJECTIVE_DIMENSIONS
        from diagnose_ira import partition_dimensions

        rubric_path = Path(__file__).resolve().parent.parent / "strategy" / "system-grading-rubric.yaml"
        import yaml
        with open(rubric_path) as f:
            rubric = yaml.safe_load(f)

        # Build fake ratings with all dimensions
        fake_scores = {d: [8.0, 7.0, 9.0] for d in list(OBJECTIVE_DIMENSIONS) + list(SUBJECTIVE_DIMENSIONS)}
        ground_truth, rated = partition_dimensions(fake_scores, rubric)

        assert set(ground_truth.keys()) == set(OBJECTIVE_DIMENSIONS)
        assert set(rated.keys()) == set(SUBJECTIVE_DIMENSIONS)

    def test_icc_subjective_only(self):
        """ICC computation excludes objective dimensions when rubric available."""
        from diagnose_ira import partition_dimensions

        rubric_path = Path(__file__).resolve().parent.parent / "strategy" / "system-grading-rubric.yaml"
        import yaml
        with open(rubric_path) as f:
            rubric = yaml.safe_load(f)

        scores = {
            # Objective — identical (SD=0)
            "test_coverage": [10.0, 10.0, 10.0],
            "code_quality": [9.4, 9.4, 9.4],
            "data_integrity": [10.0, 10.0, 10.0],
            "operational_maturity": [9.5, 9.5, 9.5],
            "claim_provenance": [5.6, 5.6, 5.6],
            # Subjective — real variance
            "architecture": [8.5, 7.0, 6.5],
            "documentation": [8.0, 7.5, 9.0],
            "analytics_intelligence": [9.0, 7.5, 8.0],
            "sustainability": [7.0, 6.0, 8.0],
        }

        ground_truth, rated = partition_dimensions(scores, rubric)

        # All objective dims should be in ground_truth
        assert "test_coverage" in ground_truth
        assert "test_coverage" not in rated

        # ICC on rated only should show real variance
        icc = compute_icc([rated[d] for d in sorted(rated.keys())])
        assert icc > 0.0  # Not degenerate

    def test_ground_truth_in_json_output(self):
        """JSON report contains ground_truth key with objective scores."""
        rubric_path = Path(__file__).resolve().parent.parent / "strategy" / "system-grading-rubric.yaml"
        import yaml
        with open(rubric_path) as f:
            rubric = yaml.safe_load(f)

        ratings = [
            {
                "rater_id": f"rater-{i}",
                "dimensions": {
                    "test_coverage": {"score": 10.0},
                    "code_quality": {"score": 9.4},
                    "data_integrity": {"score": 10.0},
                    "operational_maturity": {"score": 9.5},
                    "claim_provenance": {"score": 5.6},
                    "architecture": {"score": 7.0 + i},
                    "documentation": {"score": 8.0 + i * 0.5},
                    "analytics_intelligence": {"score": 8.0},
                    "sustainability": {"score": 7.0 + i},
                },
            }
            for i in range(3)
        ]

        result = generate_json_report(ratings, show_consensus=True)
        assert "ground_truth" in result
        assert "test_coverage" in result["ground_truth"]
        assert "subjective_icc" in result

    def test_backward_compat_no_rubric(self, monkeypatch):
        """All dimensions go through ICC when no rubric file found."""
        from diagnose_ira import partition_dimensions

        scores = {
            "test_coverage": [10.0, 10.0, 10.0],
            "architecture": [8.0, 7.0, 9.0],
        }

        ground_truth, rated = partition_dimensions(scores, rubric=None)

        # Without rubric, everything goes to rated
        assert len(ground_truth) == 0
        assert "test_coverage" in rated
        assert "architecture" in rated
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/4jp/Workspace/4444J99/application-pipeline && .venv/bin/python -m pytest tests/test_diagnose_ira.py::TestDimensionPartitioning -v`
Expected: FAIL — `ImportError: cannot import name 'partition_dimensions'`

### Task 9: Implement partition_dimensions in diagnose_ira.py

**Files:**
- Modify: `scripts/diagnose_ira.py:327-334` (after `discover_rating_files`)

- [ ] **Step 1: Add partition_dimensions function**

Insert after line 333 (end of `discover_rating_files`) in `scripts/diagnose_ira.py`:

```python
def partition_dimensions(
    scores_per_dim: dict[str, list[float]],
    rubric: dict | None = None,
) -> tuple[dict[str, list[float]], dict[str, list[float]]]:
    """Split dimensions into ground truth (objective) and rated (subjective).

    Uses diagnose.py's OBJECTIVE_DIMENSIONS/SUBJECTIVE_DIMENSIONS as the
    authoritative classification. Falls back to putting all dims in rated
    if rubric is None or diagnose constants are unavailable.

    Returns:
        (ground_truth, rated) — each a dict of {dim: [scores]}
    """
    if rubric is None:
        return {}, dict(scores_per_dim)

    try:
        from diagnose import OBJECTIVE_DIMENSIONS
    except ImportError:
        return {}, dict(scores_per_dim)

    ground_truth = {}
    rated = {}
    for dim, scores in scores_per_dim.items():
        if dim in OBJECTIVE_DIMENSIONS:
            ground_truth[dim] = scores
        else:
            rated[dim] = scores

    return ground_truth, rated
```

- [ ] **Step 2: Modify `generate_json_report` to use partitioning**

In `scripts/diagnose_ira.py`, modify the `generate_json_report` function (around line 480) to partition dimensions and report ground truth separately. Replace the function body:

Find this block near the start of `generate_json_report` (line ~480-538):

```python
def generate_json_report(ratings: list[dict], show_consensus: bool = False) -> dict:
    """Generate machine-readable IRA report."""
    rater_ids, scores_per_dim = extract_dimension_scores(ratings)
    n_raters = len(ratings)
    all_dims = sorted(scores_per_dim.keys())
    complete_dims = [d for d in all_dims if len(scores_per_dim[d]) == n_raters]

    overall_icc = 0.0
    categorical_agreement: dict | None = None
    if complete_dims and n_raters >= 2:
        matrix = [scores_per_dim[d] for d in complete_dims]
        overall_icc = compute_icc(matrix)
```

Replace with:

```python
def generate_json_report(ratings: list[dict], show_consensus: bool = False) -> dict:
    """Generate machine-readable IRA report."""
    rater_ids, scores_per_dim = extract_dimension_scores(ratings)
    n_raters = len(ratings)
    all_dims = sorted(scores_per_dim.keys())
    complete_dims = [d for d in all_dims if len(scores_per_dim[d]) == n_raters]

    # Try to partition into ground truth vs rated
    try:
        rubric = load_rubric_for_partition()
    except Exception:
        rubric = None

    ground_truth, rated_dims = partition_dimensions(scores_per_dim, rubric)
    has_partition = len(ground_truth) > 0

    # Compute ICC on rated dimensions only (if partitioned), else all
    icc_dims = [d for d in sorted(rated_dims.keys()) if len(rated_dims[d]) == n_raters] if has_partition else complete_dims
    icc_source = rated_dims if has_partition else scores_per_dim

    overall_icc = 0.0
    categorical_agreement: dict | None = None
    if icc_dims and n_raters >= 2:
        matrix = [icc_source[d] for d in icc_dims]
        overall_icc = compute_icc(matrix)
```

- [ ] **Step 3: Add ground_truth and subjective_icc to JSON output**

In the same `generate_json_report` function, find the `result = {` block near the end and replace it:

Replace:

```python
    result = {
        "n_raters": n_raters,
        "rater_ids": rater_ids,
        "overall_icc": round(overall_icc, 3),
        "overall_interpretation": interpret_agreement(overall_icc),
        "dimensions": per_dim,
    }
    if categorical_agreement:
        result["categorical_agreement"] = categorical_agreement
```

With:

```python
    result = {
        "n_raters": n_raters,
        "rater_ids": rater_ids,
        "overall_icc": round(overall_icc, 3),
        "overall_interpretation": interpret_agreement(overall_icc),
        "dimensions": per_dim,
    }
    if has_partition:
        result["subjective_icc"] = round(overall_icc, 3)
        result["subjective_interpretation"] = interpret_agreement(overall_icc)
        result["ground_truth"] = {
            dim: {"score": scores[0] if scores else None}
            for dim, scores in ground_truth.items()
        }
    if categorical_agreement:
        result["categorical_agreement"] = categorical_agreement
```

- [ ] **Step 4: Add `load_rubric_for_partition` helper**

Add this function near the top of `diagnose_ira.py` (after `load_rubric_bands`, around line 56):

```python
def load_rubric_for_partition() -> dict | None:
    """Load rubric YAML for dimension partitioning. Returns None on failure."""
    rubric_path = REPO_ROOT / "strategy" / "system-grading-rubric.yaml"
    if not rubric_path.is_file():
        return None
    try:
        import yaml
        with open(rubric_path) as f:
            return yaml.safe_load(f)
    except Exception:
        return None
```

- [ ] **Step 5: Run partition tests**

Run: `cd /Users/4jp/Workspace/4444J99/application-pipeline && .venv/bin/python -m pytest tests/test_diagnose_ira.py::TestDimensionPartitioning -v`
Expected: 4 PASS

- [ ] **Step 6: Run full diagnose_ira test suite to check backward compat**

Run: `cd /Users/4jp/Workspace/4444J99/application-pipeline && .venv/bin/python -m pytest tests/test_diagnose_ira.py -v`
Expected: All existing tests PASS + 4 new PASS

- [ ] **Step 7: Commit**

```bash
git add scripts/diagnose_ira.py tests/test_diagnose_ira.py
git commit -m "feat: partition IRA dimensions into ground truth and rated"
```

---

## Chunk 4: Integration Wiring

### Task 10: Wire into run.py

**Files:**
- Modify: `scripts/run.py:104-111` (Diagnostics section)

- [ ] **Step 1: Add rateall command**

In `scripts/run.py`, find the Diagnostics section (line ~104) and add after the `"ira"` entry:

```python
    "rateall":     ("generate_ratings.py", ["--compute-ira"], "Multi-model rating session with IRA computation"),
```

- [ ] **Step 2: Commit**

```bash
git add scripts/run.py
git commit -m "feat: add rateall quick command"
```

### Task 11: Wire into cli.py

**Files:**
- Modify: `scripts/cli.py`

- [ ] **Step 1: Add rate command**

Add this command after the existing commands in `cli.py` (in the "NEW COMMANDS" section, after line ~309):

```python
@app.command()
def rate(
    rater: str = typer.Option(None, "--rater", help="Single rater ID"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show prompts only"),
    compute_ira: bool = typer.Option(False, "--compute-ira", help="Compute IRA after"),
):
    """Run multi-model IRA rating session."""
    from generate_ratings import generate_ratings

    result = generate_ratings(
        dry_run=dry_run,
        single_rater=rater,
        compute_ira=compute_ira,
    )

    if result["status"] == "error":
        typer.echo(f"Error: {result['error']}", err=True)
        raise typer.Exit(1)

    typer.echo(f"Status: {result['status']}")
    if result.get("raters"):
        typer.echo(f"Raters: {', '.join(result['raters'])}")
```

- [ ] **Step 2: Commit**

```bash
git add scripts/cli.py
git commit -m "feat: add rate CLI command for multi-model IRA"
```

### Task 12: Wire into mcp_server.py

**Files:**
- Modify: `scripts/mcp_server.py`

- [ ] **Step 1: Add pipeline_rate tool**

Add this tool at the end of the file (before `if __name__` or at the bottom):

```python
@mcp.tool()
def pipeline_rate(
    rater_id: str | None = None,
    dry_run: bool = True,
    compute_ira: bool = False,
) -> str:
    """Run multi-model IRA rating session.

    Args:
        rater_id: Single rater to run (optional; runs all if not given)
        dry_run: If true, show prompts without calling APIs
        compute_ira: If true, compute IRA after rating

    Returns:
        JSON with status and list of completed raters
    """
    try:
        from generate_ratings import generate_ratings

        result = generate_ratings(
            dry_run=dry_run,
            single_rater=rater_id,
            compute_ira=compute_ira,
        )
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})
```

- [ ] **Step 2: Commit**

```bash
git add scripts/mcp_server.py
git commit -m "feat: add pipeline_rate MCP tool"
```

### Task 13: Update CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Add to Script Dependency Graph section**

Find the "Script Dependency Graph" section and add:

```
- **`generate_ratings.py`** imports from `diagnose.py` — uses COLLECTORS, PROMPT_GENERATORS, OBJECTIVE_DIMENSIONS, SUBJECTIVE_DIMENSIONS for multi-model IRA rating. Calls Anthropic and Google APIs.
```

- [ ] **Step 2: Add to Quick Commands table**

Find the Quick Commands table and add to the Diagnostics section:

```
| `rateall` | Multi-model IRA rating session with diverse AI panel |
```

- [ ] **Step 3: Add to Commands section**

Find the Diagnostics & grade norming section and add:

```bash
python scripts/generate_ratings.py                        # Full multi-model rating session
python scripts/generate_ratings.py --rater architect-opus  # Single rater only
python scripts/generate_ratings.py --dry-run               # Show prompts without API calls
python scripts/generate_ratings.py --compute-ira           # Run IRA after rating
```

- [ ] **Step 4: Add to Configuration Files table**

Add:

```
| `strategy/rater-personas.yaml` | Persona prompts for multi-model IRA raters (loaded by `generate_ratings.py`) |
```

- [ ] **Step 5: Add to Session sequences**

Update the Diagnostic session sequence:

```
- Diagnostic: `diagnose` → `rateall` → `ira`
```

- [ ] **Step 6: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: document generate_ratings.py, rateall command, rater personas"
```

### Task 14: Lint and full test suite

- [ ] **Step 1: Run ruff**

Run: `cd /Users/4jp/Workspace/4444J99/application-pipeline && .venv/bin/ruff check scripts/generate_ratings.py tests/test_generate_ratings.py`
Expected: No errors. If errors, run `.venv/bin/ruff check --fix` and re-check.

- [ ] **Step 2: Run verification matrix**

Run: `cd /Users/4jp/Workspace/4444J99/application-pipeline && .venv/bin/python scripts/verification_matrix.py --strict`
Expected: PASS (generate_ratings.py should have test_generate_ratings.py mapped)

- [ ] **Step 3: Run full test suite**

Run: `cd /Users/4jp/Workspace/4444J99/application-pipeline && .venv/bin/python -m pytest tests/ -v --tb=short 2>&1 | tail -30`
Expected: All tests PASS including new ones

- [ ] **Step 4: Dry-run smoke test**

Run: `cd /Users/4jp/Workspace/4444J99/application-pipeline && .venv/bin/python scripts/generate_ratings.py --dry-run`
Expected: Prints 4 rater prompts without API calls

- [ ] **Step 5: Final commit if any lint fixes**

```bash
git add -u
git commit -m "chore: lint fixes and verification matrix update"
```
