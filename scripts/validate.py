#!/usr/bin/env python3
"""Validate pipeline YAML entries against the schema."""

import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
PIPELINE_DIRS = [
    REPO_ROOT / "pipeline" / "active",
    REPO_ROOT / "pipeline" / "submitted",
    REPO_ROOT / "pipeline" / "closed",
]

REQUIRED_FIELDS = {"id", "name", "track", "status"}
VALID_TRACKS = {"grant", "residency", "job", "fellowship", "writing", "emergency", "prize", "program", "consulting"}
VALID_STATUSES = {"research", "qualified", "drafting", "staged", "submitted", "acknowledged", "interview", "outcome"}
VALID_OUTCOMES = {"accepted", "rejected", "withdrawn", "expired", None}
VALID_DEADLINE_TYPES = {"hard", "rolling", "window", "tba"}
VALID_PORTALS = {"submittable", "slideroom", "email", "custom", "web", "greenhouse", "workable"}
VALID_AMOUNT_TYPES = {"lump_sum", "stipend", "salary", "fee", "in_kind", "variable"}
VALID_POSITIONS = {"systems-artist", "creative-technologist", "educator", "community-practitioner"}


def validate_entry(filepath: Path) -> list[str]:
    """Validate a single pipeline YAML file. Returns list of errors."""
    errors = []

    try:
        with open(filepath) as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        return [f"YAML parse error: {e}"]

    if not isinstance(data, dict):
        return ["File does not contain a YAML mapping"]

    # Required fields
    for field in REQUIRED_FIELDS:
        if field not in data:
            errors.append(f"Missing required field: {field}")

    # ID matches filename
    expected_id = filepath.stem
    if data.get("id") and data["id"] != expected_id:
        errors.append(f"id '{data['id']}' does not match filename '{expected_id}'")

    # Track validation
    track = data.get("track")
    if track and track not in VALID_TRACKS:
        errors.append(f"Invalid track: '{track}' (valid: {VALID_TRACKS})")

    # Status validation
    status = data.get("status")
    if status and status not in VALID_STATUSES:
        errors.append(f"Invalid status: '{status}' (valid: {VALID_STATUSES})")

    # Outcome validation
    outcome = data.get("outcome")
    if outcome not in VALID_OUTCOMES:
        errors.append(f"Invalid outcome: '{outcome}' (valid: {VALID_OUTCOMES})")

    # Deadline type
    deadline = data.get("deadline", {})
    if isinstance(deadline, dict):
        dtype = deadline.get("type")
        if dtype and dtype not in VALID_DEADLINE_TYPES:
            errors.append(f"Invalid deadline.type: '{dtype}'")

    # Amount type
    amount = data.get("amount", {})
    if isinstance(amount, dict):
        atype = amount.get("type")
        if atype and atype not in VALID_AMOUNT_TYPES:
            errors.append(f"Invalid amount.type: '{atype}'")

    # Fit validation
    fit = data.get("fit", {})
    if isinstance(fit, dict):
        score = fit.get("score")
        if score is not None and not (1 <= score <= 10):
            errors.append(f"Fit score out of range: {score} (must be 1-10)")
        position = fit.get("identity_position")
        if position and position not in VALID_POSITIONS:
            errors.append(f"Invalid identity_position: '{position}'")

    # Block path validation
    submission = data.get("submission", {})
    if isinstance(submission, dict):
        blocks = submission.get("blocks_used", {})
        if isinstance(blocks, dict):
            for slot, block_path in blocks.items():
                full_path = REPO_ROOT / "blocks" / block_path
                # Check for .md extension
                if not full_path.suffix:
                    full_path = full_path.with_suffix(".md")
                if not full_path.exists():
                    errors.append(f"Block not found: blocks/{block_path} (slot: {slot})")

    return errors


def main():
    all_errors = {}
    file_count = 0

    for pipeline_dir in PIPELINE_DIRS:
        if not pipeline_dir.exists():
            continue
        for filepath in sorted(pipeline_dir.glob("*.yaml")):
            if filepath.name.startswith("_"):
                continue
            file_count += 1
            errors = validate_entry(filepath)
            if errors:
                all_errors[filepath.name] = errors

    if not file_count:
        print("No pipeline YAML files found.")
        sys.exit(1)

    if all_errors:
        print(f"VALIDATION FAILED — {len(all_errors)} file(s) with errors:\n")
        for filename, errors in all_errors.items():
            print(f"  {filename}:")
            for error in errors:
                print(f"    - {error}")
        print(f"\n{file_count} files checked, {len(all_errors)} with errors.")
        sys.exit(1)
    else:
        print(f"OK — {file_count} pipeline entries validated successfully.")
        sys.exit(0)


if __name__ == "__main__":
    main()
