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
VALID_EFFORT_LEVELS = {"quick", "standard", "deep", "complex"}
VALID_DIMENSIONS = {
    "mission_alignment", "evidence_match", "track_record_fit",
    "financial_alignment", "effort_to_value", "strategic_value",
    "deadline_feasibility", "portal_friction",
}
VALID_OUTREACH_TYPES = {
    "pre_submission", "warm_contact", "info_session",
    "post_submission", "follow_up", "reference_request",
}
VALID_OUTREACH_CHANNELS = {"email", "linkedin", "phone", "in_person", "webinar", "other"}
VALID_OUTREACH_STATUSES = {"planned", "done", "waiting"}

# Valid status transitions: each status maps to the set of statuses it can reach
VALID_TRANSITIONS = {
    "research": {"qualified", "withdrawn"},
    "qualified": {"drafting", "staged", "withdrawn"},
    "drafting": {"staged", "qualified", "withdrawn"},
    "staged": {"submitted", "drafting", "withdrawn"},
    "submitted": {"acknowledged", "interview", "outcome", "withdrawn"},
    "acknowledged": {"interview", "outcome", "withdrawn"},
    "interview": {"outcome", "withdrawn"},
    "outcome": set(),  # terminal
}


def _reachable_statuses(from_status: str) -> set[str]:
    """Return all statuses reachable from a given status via valid transitions."""
    reachable = set()
    frontier = [from_status]
    while frontier:
        current = frontier.pop()
        for next_status in VALID_TRANSITIONS.get(current, set()):
            if next_status not in reachable:
                reachable.add(next_status)
                frontier.append(next_status)
    return reachable


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
        # Validate dimensions if present
        dimensions = fit.get("dimensions")
        if dimensions is not None:
            if not isinstance(dimensions, dict):
                errors.append("fit.dimensions must be a mapping")
            else:
                for key, val in dimensions.items():
                    if key not in VALID_DIMENSIONS:
                        errors.append(f"Unknown dimension: '{key}' (valid: {VALID_DIMENSIONS})")
                    if val is not None and not (1 <= val <= 10):
                        errors.append(f"Dimension '{key}' out of range: {val} (must be 1-10)")

    # Effort level validation
    submission = data.get("submission", {})
    if isinstance(submission, dict):
        effort = submission.get("effort_level")
        if effort is not None and effort not in VALID_EFFORT_LEVELS:
            errors.append(f"Invalid effort_level: '{effort}' (valid: {VALID_EFFORT_LEVELS})")

    # Status transition validation
    status = data.get("status")
    if status and status in VALID_TRANSITIONS:
        timeline = data.get("timeline", {})
        if isinstance(timeline, dict):
            # Check that the current status is reachable from the timeline evidence
            # The timeline records when each stage was reached; if a later stage
            # has a date but an earlier required stage doesn't, that's suspicious
            stage_order = ["researched", "qualified", "materials_ready", "submitted",
                           "acknowledged", "interview", "outcome_date"]
            stage_to_status = {
                "researched": "research",
                "qualified": "qualified",
                "materials_ready": "staged",
                "submitted": "submitted",
                "acknowledged": "acknowledged",
                "interview": "interview",
                "outcome_date": "outcome",
            }
            # Find the highest stage with a date set
            highest_dated = None
            for stage_key in stage_order:
                if timeline.get(stage_key):
                    highest_dated = stage_to_status.get(stage_key)
            # If timeline shows a stage that can't reach current status, warn
            if highest_dated and status in VALID_TRANSITIONS:
                # Verify status is consistent: status should match or be reachable
                # from the highest dated stage
                reachable = _reachable_statuses(highest_dated)
                if status not in reachable and status != highest_dated:
                    errors.append(
                        f"Status '{status}' not reachable from timeline "
                        f"(highest dated stage: '{highest_dated}')"
                    )

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

    # last_touched validation
    last_touched = data.get("last_touched")
    if last_touched is not None:
        from datetime import datetime
        try:
            datetime.strptime(str(last_touched), "%Y-%m-%d")
        except ValueError:
            errors.append(f"Invalid last_touched format: '{last_touched}' (expected YYYY-MM-DD)")

    # Outreach validation
    outreach = data.get("outreach")
    if outreach is not None:
        if not isinstance(outreach, list):
            errors.append("outreach must be a list")
        else:
            for i, item in enumerate(outreach):
                if not isinstance(item, dict):
                    errors.append(f"outreach[{i}] must be a mapping")
                    continue
                otype = item.get("type")
                if otype and otype not in VALID_OUTREACH_TYPES:
                    errors.append(f"outreach[{i}].type '{otype}' invalid (valid: {VALID_OUTREACH_TYPES})")
                ochannel = item.get("channel")
                if ochannel and ochannel not in VALID_OUTREACH_CHANNELS:
                    errors.append(f"outreach[{i}].channel '{ochannel}' invalid (valid: {VALID_OUTREACH_CHANNELS})")
                ostatus = item.get("status")
                if ostatus and ostatus not in VALID_OUTREACH_STATUSES:
                    errors.append(f"outreach[{i}].status '{ostatus}' invalid (valid: {VALID_OUTREACH_STATUSES})")

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
