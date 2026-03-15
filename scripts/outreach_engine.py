#!/usr/bin/env python3
"""Outreach engine: auto-generate and persist outreach materials.

Generates outreach templates for submitted entries, saves them to files,
logs actions to outreach-log.yaml, and sets follow-up dates per protocol.

Usage:
    python scripts/outreach_engine.py                         # Dry-run all submitted
    python scripts/outreach_engine.py --yes                   # Execute outreach prep
    python scripts/outreach_engine.py --target <id>           # Single entry
    python scripts/outreach_engine.py --json                  # Machine-readable output
"""

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from outreach_templates import (
    generate_all_templates,
)
from pipeline_lib import (
    ALL_PIPELINE_DIRS,
    SIGNALS_DIR,
    load_entries,
    load_entry_by_id,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTREACH_DIR = REPO_ROOT / "materials" / "outreach"
OUTREACH_LOG_PATH = SIGNALS_DIR / "outreach-log.yaml"
OUTREACH_HISTORY_PATH = SIGNALS_DIR / "outreach-history.yaml"

# Follow-up protocol timing (days after submission)
PROTOCOL = {
    "connect": {"day": 0, "channel": "linkedin"},
    "email": {"day": 1, "channel": "email"},
    "followup": {"day": 7, "channel": "linkedin"},
}


@dataclass
class OutreachAction:
    """A prepared outreach action."""

    entry_id: str
    action_type: str
    channel: str
    template_text: str
    scheduled_date: str
    status: str  # prepared | sent


@dataclass
class OutreachResult:
    """Result of an outreach preparation."""

    entries_processed: list[str] = field(default_factory=list)
    templates_generated: int = 0
    files_written: int = 0
    followup_dates_set: int = 0
    actions: list[OutreachAction] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _save_outreach_templates(entry_id: str, templates: dict, dry_run: bool = True) -> int:
    """Save outreach templates to materials/outreach/<entry-id>/."""
    if dry_run:
        return 0

    out_dir = OUTREACH_DIR / entry_id
    out_dir.mkdir(parents=True, exist_ok=True)
    count = 0

    for ttype, tmpl in templates.items():
        path = out_dir / f"{ttype}.md"
        content = f"# {ttype.title()} Template\n\n"
        if tmpl.get("subject"):
            content += f"**Subject:** {tmpl['subject']}\n\n"
        if tmpl.get("platform"):
            content += f"**Platform:** {tmpl['platform']}\n"
        if tmpl.get("timing"):
            content += f"**Timing:** {tmpl['timing']}\n"
        content += f"\n---\n\n{tmpl['template']}\n"
        path.write_text(content)
        count += 1

    return count


def _set_followup_dates(entry_id: str, submission_date: date | None = None, dry_run: bool = True) -> int:
    """Set follow-up protocol dates on the entry YAML."""
    if dry_run:
        return 0

    filepath, entry = load_entry_by_id(entry_id)
    if not filepath or not entry:
        return 0

    if submission_date is None:
        timeline = entry.get("timeline") or {}
        sub_str = timeline.get("submitted")
        if sub_str:
            try:
                submission_date = date.fromisoformat(str(sub_str))
            except ValueError:
                submission_date = date.today()
        else:
            submission_date = date.today()

    try:
        from yaml_mutation import YAMLEditor
    except ImportError:
        return 0

    content = Path(filepath).read_text()
    editor = YAMLEditor(content)

    count = 0
    for action_type, proto in PROTOCOL.items():
        target_date = submission_date + timedelta(days=proto["day"])
        editor.set(f"follow_up.protocol.{action_type}_date", target_date.isoformat())
        count += 1

    editor.touch()
    Path(filepath).write_text(editor.dump())
    return count


def _log_outreach_actions(actions: list[OutreachAction], dry_run: bool = True) -> None:
    """Append outreach actions to outreach-log.yaml."""
    if dry_run or not actions:
        return

    SIGNALS_DIR.mkdir(parents=True, exist_ok=True)
    existing = []
    if OUTREACH_LOG_PATH.exists():
        existing = yaml.safe_load(OUTREACH_LOG_PATH.read_text()) or []
    if not isinstance(existing, list):
        existing = []

    for action in actions:
        existing.append({
            "entry_id": action.entry_id,
            "action": action.action_type,
            "channel": action.channel,
            "date": action.scheduled_date,
            "status": action.status,
        })

    OUTREACH_LOG_PATH.write_text(
        yaml.dump(existing, default_flow_style=False, sort_keys=False)
    )


def prepare_outreach(
    entry_ids: list[str] | None = None,
    dry_run: bool = True,
) -> OutreachResult:
    """Generate outreach materials for submitted entries.

    Args:
        entry_ids: Specific entries. None = all recently submitted.
        dry_run: If True, don't write files.
    """
    entries = load_entries(dirs=ALL_PIPELINE_DIRS)
    result = OutreachResult()

    for entry in entries:
        eid = entry.get("id", "")
        if entry_ids and eid not in entry_ids:
            continue
        if entry.get("status") not in ("submitted", "staged"):
            continue

        # Check if outreach already prepared
        outreach_dir = OUTREACH_DIR / eid
        if outreach_dir.exists() and not entry_ids:
            continue  # Skip if already done (unless explicitly targeted)

        try:
            # Generate all template types
            all_templates = generate_all_templates(entry)
            templates = all_templates.get("templates", {})
            result.templates_generated += len(templates)

            # Save template files
            files = _save_outreach_templates(eid, templates, dry_run=dry_run)
            result.files_written += files

            # Set follow-up protocol dates
            dates_set = _set_followup_dates(eid, dry_run=dry_run)
            result.followup_dates_set += dates_set

            # Create action items
            today = date.today()
            for action_type, proto in PROTOCOL.items():
                tmpl = templates.get(action_type, {})
                if tmpl:
                    action = OutreachAction(
                        entry_id=eid,
                        action_type=action_type,
                        channel=proto["channel"],
                        template_text=tmpl.get("template", ""),
                        scheduled_date=(today + timedelta(days=proto["day"])).isoformat(),
                        status="prepared",
                    )
                    result.actions.append(action)

            result.entries_processed.append(eid)
        except Exception as e:
            result.errors.append(f"{eid}: {e}")

    # Log actions
    _log_outreach_actions(result.actions, dry_run=dry_run)

    return result


def _log_outreach_result(result: OutreachResult, log_path: Path | None = None) -> None:
    """Append outreach result to history log."""
    log_path = log_path or OUTREACH_HISTORY_PATH
    entry = {
        "date": str(date.today()),
        "entries_processed": len(result.entries_processed),
        "templates_generated": result.templates_generated,
        "files_written": result.files_written,
        "followup_dates_set": result.followup_dates_set,
        "errors": len(result.errors),
    }
    existing = []
    if log_path.exists():
        existing = yaml.safe_load(log_path.read_text()) or []
    existing.append(entry)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(
        yaml.dump(existing, default_flow_style=False, sort_keys=False)
    )


def main():
    parser = argparse.ArgumentParser(description="Outreach engine: template generation + tracking")
    parser.add_argument("--yes", action="store_true", help="Execute (write files)")
    parser.add_argument("--target", help="Single entry")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    dry_run = not args.yes
    entry_ids = [args.target] if args.target else None

    result = prepare_outreach(entry_ids=entry_ids, dry_run=dry_run)

    if not dry_run:
        _log_outreach_result(result)

    if args.json:
        print(json.dumps(asdict(result), indent=2))
    else:
        mode = "DRY-RUN" if dry_run else "EXECUTED"
        print(f"\n{'=' * 50}")
        print(f"OUTREACH RESULTS ({mode})")
        print(f"{'=' * 50}")
        print(f"Entries processed:   {len(result.entries_processed)}")
        print(f"Templates generated: {result.templates_generated}")
        print(f"Files written:       {result.files_written}")
        print(f"Follow-up dates set: {result.followup_dates_set}")

        if result.actions:
            print("\nScheduled Actions:")
            for a in result.actions:
                print(f"  [{a.scheduled_date}] {a.entry_id}: {a.action_type} via {a.channel}")

        if result.errors:
            print(f"\nErrors ({len(result.errors)}):")
            for e in result.errors:
                print(f"  - {e}")


if __name__ == "__main__":
    main()
