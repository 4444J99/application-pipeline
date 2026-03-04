#!/usr/bin/env python3
"""Programmatic API layer for pipeline operations.

Provides typed, non-interactive wrappers around core script logic for use by
CLI and MCP surfaces.
"""

from __future__ import annotations

import io
import json
from contextlib import redirect_stdout
from dataclasses import dataclass
from datetime import date
from enum import Enum
from pathlib import Path

import yaml

try:  # Prefer package-style imports when available.
    from .advance import advance_entry as _advance_file_entry
    from .advance import can_advance
    from .compose import compose as compose_document
    from .compose import find_entry as find_compose_entry
    from .draft import assemble_draft, populate_portal_fields
    from .pipeline_lib import (
        DRAFTS_DIR,
        SUBMISSIONS_DIR,
        VALID_STATUSES,
        VALID_TRACKS,
        count_words,
        load_entry_by_id,
        load_profile,
    )
    from .score import (
        ALL_PIPELINE_DIRS_WITH_POOL,
        _load_entries_raw,
        compute_composite,
        compute_dimensions,
        run_auto_qualify,
        update_entry_file,
    )
    from .score import (
        load_entries as load_score_entries,
    )
    from .validate import PIPELINE_DIRS, REQUIRED_FIELDS
    from .validate import validate_entry as validate_file_entry
except ImportError:  # pragma: no cover - script execution fallback
    from advance import advance_entry as _advance_file_entry
    from advance import can_advance
    from compose import compose as compose_document
    from compose import find_entry as find_compose_entry
    from draft import assemble_draft, populate_portal_fields
    from pipeline_lib import (
        DRAFTS_DIR,
        SUBMISSIONS_DIR,
        VALID_STATUSES,
        VALID_TRACKS,
        count_words,
        load_entry_by_id,
        load_profile,
    )
    from score import (
        ALL_PIPELINE_DIRS_WITH_POOL,
        _load_entries_raw,
        compute_composite,
        compute_dimensions,
        run_auto_qualify,
        update_entry_file,
    )
    from score import (
        load_entries as load_score_entries,
    )
    from validate import PIPELINE_DIRS, REQUIRED_FIELDS
    from validate import validate_entry as validate_file_entry


class ResultStatus(Enum):
    """Result status indicators."""

    SUCCESS = "success"
    ERROR = "error"
    DRY_RUN = "dry_run"
    NO_CHANGE = "no_change"


@dataclass
class ScoreResult:
    """Result of scoring an entry or batch."""

    status: ResultStatus
    entry_id: str
    old_score: float | None = None
    new_score: float | None = None
    dimensions: dict[str, int] | None = None
    message: str = ""
    error: str | None = None


@dataclass
class AdvanceResult:
    """Result of advancing an entry."""

    status: ResultStatus
    entry_id: str
    old_status: str | None = None
    new_status: str | None = None
    message: str = ""
    error: str | None = None


@dataclass
class DraftResult:
    """Result of drafting an entry."""

    status: ResultStatus
    entry_id: str
    content: str | None = None
    file_path: str | None = None
    message: str = ""
    error: str | None = None


@dataclass
class ComposeResult:
    """Result of composing an entry."""

    status: ResultStatus
    entry_id: str
    content: str | None = None
    file_path: str | None = None
    word_count: int | None = None
    block_sources: list[str] | None = None
    message: str = ""
    error: str | None = None


@dataclass
class ValidationResult:
    """Result of validating one or more entries."""

    status: ResultStatus
    entry_id: str
    is_valid: bool = False
    errors: list[str] | None = None
    warnings: list[str] | None = None
    message: str = ""
    error: str | None = None

    def __post_init__(self) -> None:
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


_NATURAL_NEXT_STATUS: dict[str, str] = {
    "research": "qualified",
    "qualified": "drafting",
    "drafting": "staged",
    "staged": "submitted",
    "deferred": "qualified",
    "submitted": "acknowledged",
    "acknowledged": "interview",
    "interview": "outcome",
}

API_OPERATION_ERRORS = (
    OSError,
    RuntimeError,
    TypeError,
    ValueError,
    KeyError,
    json.JSONDecodeError,
    yaml.YAMLError,
)


def _natural_next_status(current_status: str) -> str | None:
    """Return the conventional next status for a status, if defined."""

    return _NATURAL_NEXT_STATUS.get(current_status)


def score_entry(
    entry_id: str | None,
    auto_qualify: bool = False,
    dry_run: bool = True,
    min_score: float = 7.0,
    limit: int = 0,
    verbose: bool = False,
    all_entries: bool = False,
) -> ScoreResult:
    """Score one entry, all entries, or run auto-qualify."""

    try:
        if auto_qualify and all_entries:
            return ScoreResult(
                status=ResultStatus.ERROR,
                entry_id="batch",
                error="auto_qualify and all_entries are mutually exclusive",
            )

        if auto_qualify:
            capture = io.StringIO()
            with redirect_stdout(capture):
                run_auto_qualify(
                    dry_run=dry_run,
                    yes=not dry_run,
                    min_score=min_score,
                    limit=limit,
                )
            output = capture.getvalue().strip()
            summary = output.splitlines()[-1] if output else "auto-qualify complete"
            return ScoreResult(
                status=ResultStatus.DRY_RUN if dry_run else ResultStatus.SUCCESS,
                entry_id="batch",
                message=summary,
            )

        if all_entries:
            entries = load_score_entries(entry_id=None, include_pool=True)
            if not entries:
                return ScoreResult(
                    status=ResultStatus.ERROR,
                    entry_id="batch",
                    error="no entries found",
                )
            all_raw = _load_entries_raw(dirs=ALL_PIPELINE_DIRS_WITH_POOL)
            updated = 0
            for filepath, data in entries:
                dims = compute_dimensions(data, all_raw)
                composite = compute_composite(dims, data.get("track", ""))
                update_entry_file(filepath, dims, composite, dry_run=dry_run)
                updated += 1
            return ScoreResult(
                status=ResultStatus.DRY_RUN if dry_run else ResultStatus.SUCCESS,
                entry_id="batch",
                message=f"scored {updated} entries" + (" (dry-run)" if dry_run else ""),
            )

        if not entry_id:
            return ScoreResult(
                status=ResultStatus.ERROR,
                entry_id="",
                error="entry_id required for single scoring",
            )

        entries = load_score_entries(entry_id=entry_id, include_pool=False)
        if not entries:
            return ScoreResult(
                status=ResultStatus.ERROR,
                entry_id=entry_id,
                error=f"entry '{entry_id}' not found",
            )

        filepath, data = entries[0]
        all_raw = _load_entries_raw(dirs=ALL_PIPELINE_DIRS_WITH_POOL)
        dimensions = compute_dimensions(data, all_raw)
        composite = compute_composite(dimensions, data.get("track", ""))
        old_score, new_score = update_entry_file(filepath, dimensions, composite, dry_run=dry_run)

        delta = ""
        if old_score is not None:
            delta = f" (was {old_score}, delta {new_score - old_score:+.1f})"

        message = f"score={new_score}{delta}" if not verbose else f"score={new_score}, dims={dimensions}"
        return ScoreResult(
            status=ResultStatus.DRY_RUN if dry_run else ResultStatus.SUCCESS,
            entry_id=entry_id,
            old_score=old_score,
            new_score=new_score,
            dimensions=dimensions,
            message=message,
        )
    except API_OPERATION_ERRORS as exc:
        return ScoreResult(
            status=ResultStatus.ERROR,
            entry_id=entry_id or "",
            error=f"{type(exc).__name__}: {exc}",
        )


def advance_entry(
    entry_id: str,
    to_status: str | None = None,
    dry_run: bool = True,
) -> AdvanceResult:
    """Advance an entry to the next status (or specified status)."""

    try:
        if not entry_id:
            return AdvanceResult(
                status=ResultStatus.ERROR,
                entry_id="",
                error="entry_id required",
            )

        filepath, data = load_entry_by_id(entry_id)
        if not filepath or not data:
            return AdvanceResult(
                status=ResultStatus.ERROR,
                entry_id=entry_id,
                error=f"entry '{entry_id}' not found",
            )

        old_status = str(data.get("status", ""))
        if not old_status:
            return AdvanceResult(
                status=ResultStatus.ERROR,
                entry_id=entry_id,
                error="entry missing status",
            )

        target_status = to_status or _natural_next_status(old_status)
        if not target_status:
            return AdvanceResult(
                status=ResultStatus.NO_CHANGE,
                entry_id=entry_id,
                old_status=old_status,
                message=f"no natural next status from '{old_status}'",
            )

        if not can_advance(old_status, target_status):
            return AdvanceResult(
                status=ResultStatus.ERROR,
                entry_id=entry_id,
                old_status=old_status,
                new_status=target_status,
                error=f"invalid transition: {old_status} -> {target_status}",
            )

        if dry_run:
            return AdvanceResult(
                status=ResultStatus.DRY_RUN,
                entry_id=entry_id,
                old_status=old_status,
                new_status=target_status,
                message=f"would advance {old_status} -> {target_status}",
            )

        _advance_file_entry(filepath, entry_id, target_status)
        return AdvanceResult(
            status=ResultStatus.SUCCESS,
            entry_id=entry_id,
            old_status=old_status,
            new_status=target_status,
            message=f"advanced {old_status} -> {target_status}",
        )
    except API_OPERATION_ERRORS as exc:
        return AdvanceResult(
            status=ResultStatus.ERROR,
            entry_id=entry_id,
            error=f"{type(exc).__name__}: {exc}",
        )


def _resolve_profile(entry_id: str) -> dict | None:
    """Resolve profile by entry id using canonical loader and target_id fallback."""

    profile = load_profile(entry_id)
    if profile:
        return profile

    profiles_dir = Path(__file__).resolve().parent.parent / "targets" / "profiles"
    if not profiles_dir.exists():
        return None

    for profile_path in profiles_dir.glob("*.json"):
        try:
            pdata = json.loads(profile_path.read_text())
        except json.JSONDecodeError:
            continue
        if pdata.get("target_id") == entry_id:
            return pdata
    return None


def draft_entry(
    entry_id: str,
    profile: bool = False,
    length: str = "medium",
    populate: bool = False,
    dry_run: bool = True,
) -> DraftResult:
    """Draft application materials from profile or blocks."""

    try:
        if not entry_id:
            return DraftResult(
                status=ResultStatus.ERROR,
                entry_id="",
                error="entry_id required",
            )

        filepath, entry = load_entry_by_id(entry_id)
        if not entry:
            return DraftResult(
                status=ResultStatus.ERROR,
                entry_id=entry_id,
                error=f"entry '{entry_id}' not found",
            )

        # Draft assembly is profile-driven; always resolve profile when available.
        profile_data = _resolve_profile(entry_id)
        document, warnings = assemble_draft(entry, profile_data, length)

        file_path = None
        if not dry_run:
            DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
            output_path = DRAFTS_DIR / f"{entry_id}.md"
            output_path.write_text(document)
            file_path = str(output_path)

            if populate and profile_data and filepath:
                populate_portal_fields(filepath, entry, profile_data)

        warning_msg = f" ({len(warnings)} warnings)" if warnings else ""
        return DraftResult(
            status=ResultStatus.DRY_RUN if dry_run else ResultStatus.SUCCESS,
            entry_id=entry_id,
            content=document,
            file_path=file_path,
            message=f"draft generated{warning_msg}",
        )
    except API_OPERATION_ERRORS as exc:
        return DraftResult(
            status=ResultStatus.ERROR,
            entry_id=entry_id,
            error=f"{type(exc).__name__}: {exc}",
        )


def compose_entry(
    entry_id: str,
    snapshot: bool = False,
    counts: bool = False,
    profile: bool = False,
    dry_run: bool = True,
) -> ComposeResult:
    """Compose submission from blocks and materials."""

    try:
        if not entry_id:
            return ComposeResult(
                status=ResultStatus.ERROR,
                entry_id="",
                error="entry_id required",
            )

        entry = find_compose_entry(entry_id)
        if not entry:
            return ComposeResult(
                status=ResultStatus.ERROR,
                entry_id=entry_id,
                error=f"entry '{entry_id}' not found",
            )

        profile_data = _resolve_profile(entry_id) if profile else None
        content = compose_document(entry, profile_data, ai_smooth=False)
        word_count = count_words(content)

        file_path = None
        if snapshot and not dry_run:
            SUBMISSIONS_DIR.mkdir(parents=True, exist_ok=True)
            snapshot_name = f"{entry_id}-{date.today().isoformat()}.md"
            snapshot_path = SUBMISSIONS_DIR / snapshot_name
            snapshot_path.write_text(content)
            file_path = str(snapshot_path)

        submission = entry.get("submission", {}) if isinstance(entry.get("submission"), dict) else {}
        block_sources = []
        blocks_used = submission.get("blocks_used")
        if isinstance(blocks_used, dict):
            block_sources = [str(v) for v in blocks_used.values()]

        message = f"composed {word_count} words"
        if counts:
            message += f" (counts requested: {word_count}w)"

        return ComposeResult(
            status=ResultStatus.DRY_RUN if dry_run else ResultStatus.SUCCESS,
            entry_id=entry_id,
            content=content,
            file_path=file_path,
            word_count=word_count,
            block_sources=block_sources,
            message=message,
        )
    except API_OPERATION_ERRORS as exc:
        return ComposeResult(
            status=ResultStatus.ERROR,
            entry_id=entry_id,
            error=f"{type(exc).__name__}: {exc}",
        )


def _validate_inline_entry(entry_dict: dict) -> tuple[list[str], list[str]]:
    """Validate inline entry dict using core structural checks."""

    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(entry_dict, dict):
        return ["entry_dict must be a mapping"], warnings

    missing = sorted(REQUIRED_FIELDS - set(entry_dict.keys()))
    for field in missing:
        errors.append(f"Missing required field: {field}")

    track = entry_dict.get("track")
    if track and track not in VALID_TRACKS:
        errors.append(f"Invalid track: '{track}'")

    status = entry_dict.get("status")
    if status and status not in VALID_STATUSES:
        errors.append(f"Invalid status: '{status}'")

    return errors, warnings


def validate_entry(
    entry_id: str | None = None,
    entry_dict: dict | None = None,
) -> ValidationResult:
    """Validate a single entry, an inline entry dict, or the full pipeline."""

    try:
        if entry_dict is not None:
            errors, warnings = _validate_inline_entry(entry_dict)
            is_valid = len(errors) == 0
            return ValidationResult(
                status=ResultStatus.SUCCESS if is_valid else ResultStatus.ERROR,
                entry_id=str(entry_dict.get("id", "inline")),
                is_valid=is_valid,
                errors=errors,
                warnings=warnings,
                message="validation passed" if is_valid else "validation failed",
                error="; ".join(errors) if errors else None,
            )

        if entry_id:
            filepath, _ = load_entry_by_id(entry_id)
            if not filepath:
                return ValidationResult(
                    status=ResultStatus.ERROR,
                    entry_id=entry_id,
                    is_valid=False,
                    errors=[f"entry '{entry_id}' not found"],
                    message="validation failed",
                    error=f"entry '{entry_id}' not found",
                )
            warnings: list[str] = []
            errors = validate_file_entry(filepath, warnings=warnings)
            is_valid = len(errors) == 0
            return ValidationResult(
                status=ResultStatus.SUCCESS if is_valid else ResultStatus.ERROR,
                entry_id=entry_id,
                is_valid=is_valid,
                errors=errors,
                warnings=warnings,
                message="validation passed" if is_valid else "validation failed",
                error="; ".join(errors) if errors else None,
            )

        # Full pipeline validation
        all_errors: list[str] = []
        all_warnings: list[str] = []
        file_count = 0

        for pipeline_dir in PIPELINE_DIRS:
            if not pipeline_dir.exists():
                continue
            for filepath in sorted(pipeline_dir.glob("*.yaml")):
                if filepath.name.startswith("_"):
                    continue
                file_count += 1
                warnings: list[str] = []
                errors = validate_file_entry(filepath, warnings=warnings)
                all_warnings.extend([f"{filepath.name}: {w}" for w in warnings])
                all_errors.extend([f"{filepath.name}: {e}" for e in errors])

        if file_count == 0:
            return ValidationResult(
                status=ResultStatus.ERROR,
                entry_id="all",
                is_valid=False,
                errors=["No pipeline YAML files found"],
                message="validation failed",
                error="No pipeline YAML files found",
            )

        is_valid = len(all_errors) == 0
        return ValidationResult(
            status=ResultStatus.SUCCESS if is_valid else ResultStatus.ERROR,
            entry_id="all",
            is_valid=is_valid,
            errors=all_errors,
            warnings=all_warnings,
            message=f"validated {file_count} entries",
            error="; ".join(all_errors[:3]) if all_errors else None,
        )
    except API_OPERATION_ERRORS as exc:
        return ValidationResult(
            status=ResultStatus.ERROR,
            entry_id=entry_id or "all",
            is_valid=False,
            errors=[f"{type(exc).__name__}: {exc}"],
            message="validation failed",
            error=f"{type(exc).__name__}: {exc}",
        )


__all__ = [
    "ResultStatus",
    "ScoreResult",
    "AdvanceResult",
    "DraftResult",
    "ComposeResult",
    "ValidationResult",
    "score_entry",
    "advance_entry",
    "draft_entry",
    "compose_entry",
    "validate_entry",
]
