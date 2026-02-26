#!/usr/bin/env python3
"""Validate pipeline YAML entries against the schema."""

import sys
from pathlib import Path

import yaml

from pipeline_lib import (
    REPO_ROOT, ALL_PIPELINE_DIRS as PIPELINE_DIRS,
    VALID_TRACKS, VALID_STATUSES, VALID_TRANSITIONS,
    detect_portal,
)

REQUIRED_FIELDS = {"id", "name", "track", "status"}
VALID_OUTCOMES = {"accepted", "rejected", "withdrawn", "expired", None}
VALID_DEADLINE_TYPES = {"hard", "rolling", "window", "tba", "fixed"}
VALID_PORTALS = {"submittable", "slideroom", "email", "custom", "web", "greenhouse", "workable", "lever", "ashby", "smartrecruiters"}
VALID_AMOUNT_TYPES = {"lump_sum", "stipend", "salary", "fee", "in_kind", "variable"}
VALID_POSITIONS = {"systems-artist", "creative-technologist", "educator", "community-practitioner", "independent-engineer"}
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
VALID_RECOMMENDATION_STATUSES = {"not_asked", "asked", "confirmed", "submitted", "declined"}
VALID_PORTAL_FIELD_FORMATS = {"text", "textarea", "file_upload", "url", "dropdown", "checkbox"}
VALID_WITHDRAWAL_REASONS = {
    "missed_deadline", "low_fit", "effort_too_high", "duplicate",
    "ineligible", "strategic_shift", "personal", "other",
}
VALID_DEFERRAL_REASONS = {
    "portal_paused", "cycle_not_open", "pending_materials",
    "external_dependency", "strategic_hold",
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
        original_score = fit.get("original_score")
        if original_score is not None and not (1 <= original_score <= 10):
            errors.append(f"Fit original_score out of range: {original_score} (must be 1-10)")
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

    # Portal validation
    target = data.get("target", {})
    if isinstance(target, dict):
        portal = target.get("portal")
        if portal and portal not in VALID_PORTALS:
            errors.append(f"Invalid target.portal: '{portal}' (valid: {VALID_PORTALS})")
        # Warn if portal doesn't match what URL detection finds
        app_url = target.get("application_url", "")
        if app_url and portal:
            detected = detect_portal(app_url)
            if detected and detected != portal:
                errors.append(
                    f"Portal mismatch: target.portal is '{portal}' but URL "
                    f"suggests '{detected}' ({app_url})"
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

    # Recommendations validation
    recommendations = data.get("recommendations")
    if recommendations is not None:
        if not isinstance(recommendations, list):
            errors.append("recommendations must be a list")
        else:
            for i, rec in enumerate(recommendations):
                if not isinstance(rec, dict):
                    errors.append(f"recommendations[{i}] must be a mapping")
                    continue
                rstatus = rec.get("status")
                if rstatus and rstatus not in VALID_RECOMMENDATION_STATUSES:
                    errors.append(
                        f"recommendations[{i}].status '{rstatus}' invalid "
                        f"(valid: {VALID_RECOMMENDATION_STATUSES})"
                    )

    # Portal fields validation
    portal_fields = data.get("portal_fields")
    if portal_fields is not None:
        if not isinstance(portal_fields, dict):
            errors.append("portal_fields must be a mapping")
        else:
            fields = portal_fields.get("fields")
            if fields is not None:
                if not isinstance(fields, list):
                    errors.append("portal_fields.fields must be a list")
                else:
                    for i, field in enumerate(fields):
                        if not isinstance(field, dict):
                            errors.append(f"portal_fields.fields[{i}] must be a mapping")
                            continue
                        fmt = field.get("format")
                        if fmt and fmt not in VALID_PORTAL_FIELD_FORMATS:
                            errors.append(
                                f"portal_fields.fields[{i}].format '{fmt}' invalid "
                                f"(valid: {VALID_PORTAL_FIELD_FORMATS})"
                            )

    # Deferral field validation
    deferral = data.get("deferral")
    status = data.get("status")
    if status == "deferred" and deferral is None:
        errors.append("Status is 'deferred' but no 'deferral' field present (recommended)")
    if deferral is not None:
        if not isinstance(deferral, dict):
            errors.append("deferral must be a mapping")
        else:
            reason = deferral.get("reason")
            if reason and reason not in VALID_DEFERRAL_REASONS:
                errors.append(
                    f"deferral.reason '{reason}' invalid "
                    f"(valid: {VALID_DEFERRAL_REASONS})"
                )
            resume_date = deferral.get("resume_date")
            if resume_date is not None:
                from datetime import datetime
                try:
                    datetime.strptime(str(resume_date), "%Y-%m-%d")
                except ValueError:
                    errors.append(f"Invalid deferral.resume_date format: '{resume_date}' (expected YYYY-MM-DD)")

    # Withdrawal reason validation
    withdrawal = data.get("withdrawal_reason")
    if withdrawal is not None:
        if not isinstance(withdrawal, dict):
            errors.append("withdrawal_reason must be a mapping")
        else:
            reason = withdrawal.get("reason")
            if reason and reason not in VALID_WITHDRAWAL_REASONS:
                errors.append(
                    f"withdrawal_reason.reason '{reason}' invalid "
                    f"(valid: {VALID_WITHDRAWAL_REASONS})"
                )

    return errors


def check_profile_freshness() -> list[str]:
    """Compare profile JSON metric values against metrics-snapshot.md source of truth.

    Returns list of warning strings for stale profiles.
    """
    import json
    import re

    from pipeline_lib import PROFILES_DIR, BLOCKS_DIR

    warnings = []

    # Load source-of-truth metrics from metrics-snapshot.md
    snapshot_path = BLOCKS_DIR / "evidence" / "metrics-snapshot.md"
    if not snapshot_path.exists():
        warnings.append("Cannot check freshness: blocks/evidence/metrics-snapshot.md not found")
        return warnings

    snapshot = snapshot_path.read_text()

    # Extract canonical repo count
    repo_match = re.search(r"Total repositories\s*\|\s*(\d+)", snapshot)
    canonical_repos = int(repo_match.group(1)) if repo_match else None

    if not PROFILES_DIR.exists():
        warnings.append("Cannot check freshness: targets/profiles/ not found")
        return warnings

    stale_count = 0
    for profile_path in sorted(PROFILES_DIR.glob("*.json")):
        if "index" in profile_path.name:
            continue
        text = profile_path.read_text()

        issues = []

        # Check for stale repo count
        if canonical_repos:
            # Match patterns like "101 repositories", "101-repository", "101 repos"
            stale_repos = re.findall(r"\b(\d+)(?:\s+|-)?repositor(?:ies|y)", text)
            for count_str in stale_repos:
                count = int(count_str)
                if count != canonical_repos:
                    issues.append(f"repo count {count} != {canonical_repos}")
                    break

        if issues:
            stale_count += 1
            for issue in issues:
                warnings.append(f"  {profile_path.name}: {issue}")

    if stale_count:
        warnings.insert(0, f"STALE PROFILES — {stale_count} profile(s) with outdated metrics:")
    else:
        warnings.append(f"Profile freshness OK — all profiles match metrics-snapshot.md")

    return warnings


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Validate pipeline YAML entries")
    parser.add_argument("--check-freshness", action="store_true",
                        help="Also check profile JSON freshness against metrics-snapshot.md")
    args = parser.parse_args()

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

    has_errors = False

    if all_errors:
        print(f"VALIDATION FAILED — {len(all_errors)} file(s) with errors:\n")
        for filename, errors in all_errors.items():
            print(f"  {filename}:")
            for error in errors:
                print(f"    - {error}")
        print(f"\n{file_count} files checked, {len(all_errors)} with errors.")
        has_errors = True
    else:
        print(f"OK — {file_count} pipeline entries validated successfully.")

    if args.check_freshness:
        print()
        freshness_warnings = check_profile_freshness()
        for w in freshness_warnings:
            print(w)
        stale = any("STALE" in w for w in freshness_warnings)
        if stale:
            has_errors = True

    if has_errors:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
