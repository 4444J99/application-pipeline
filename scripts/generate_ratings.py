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
