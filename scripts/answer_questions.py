#!/usr/bin/env python3
"""AI-assisted answer generator for custom portal questions.

Generates prompts that use role context (cover letter, framing) to produce
answers for custom questions that can't be auto-filled. Integrates answers
back into the portal-specific answer YAML files.

Usage:
    python scripts/answer_questions.py --target <id>                # Generate prompt
    python scripts/answer_questions.py --batch --status staged      # Batch prompts
    python scripts/answer_questions.py --target <id> --integrate    # Integrate AI output
    python scripts/answer_questions.py --batch --integrate          # Batch integrate
"""

import argparse
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import (
    REPO_ROOT,
    VARIANTS_DIR,
    load_entries,
    load_entry_by_id,
    strip_markdown,
    PIPELINE_DIR_ACTIVE,
)

CONFIG_PATH = Path(__file__).resolve().parent / ".submit-config.yaml"
WORK_DIR = Path(__file__).resolve().parent / ".alchemize-work"
ASHBY_ANSWERS_DIR = Path(__file__).resolve().parent / ".ashby-answers"
GREENHOUSE_ANSWERS_DIR = Path(__file__).resolve().parent / ".greenhouse-answers"

# Label patterns for matching default_answers from config
DEFAULT_ANSWER_PATTERNS = [
    (re.compile(r"authorized.*work|work.*authorization|legally.*work|eligible.*work", re.I), "work_authorization"),
    (re.compile(r"visa|sponsor", re.I), "visa_sponsorship"),
    (re.compile(r"salary|compensation|pay.*expect", re.I), "salary_expectation"),
    (re.compile(r"start.*date|when.*start|earliest.*start|available.*start", re.I), "start_date"),
    (re.compile(r"how.*hear|how.*find|where.*hear|how.*learn.*about", re.I), "how_did_you_hear"),
    (re.compile(r"relocat", re.I), "willing_to_relocate"),
    (re.compile(r"\bgender\b", re.I), "gender"),
    (re.compile(r"race|ethnic", re.I), "race_ethnicity"),
    (re.compile(r"veteran|military", re.I), "veteran_status"),
    (re.compile(r"disabilit", re.I), "disability_status"),
]


def load_config() -> dict:
    """Load config including default_answers."""
    if not CONFIG_PATH.exists():
        return {}
    return yaml.safe_load(CONFIG_PATH.read_text()) or {}


def get_answers_dir(portal: str) -> Path:
    """Get the answers directory for a given portal type."""
    if portal == "ashby":
        return ASHBY_ANSWERS_DIR
    elif portal == "greenhouse":
        return GREENHOUSE_ANSWERS_DIR
    else:
        return WORK_DIR


def load_answer_template(entry_id: str, portal: str) -> dict | None:
    """Load existing answer template from the portal-specific answers dir."""
    answers_dir = get_answers_dir(portal)
    answer_path = answers_dir / f"{entry_id}.yaml"
    if not answer_path.exists():
        return None
    data = yaml.safe_load(answer_path.read_text())
    return data if isinstance(data, dict) else None


def find_fill_in_fields(answers: dict, raw_text: str) -> list[dict]:
    """Find fields that still have FILL IN placeholders.

    Parses both the answer values and the comments from the raw YAML text
    to provide context about each field.
    """
    fields = []
    # Parse the raw text to get comments (labels, types, options)
    lines = raw_text.split("\n")
    current_comments = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            current_comments.append(stripped.lstrip("# ").strip())
        elif not stripped:
            # Empty line resets comment accumulator
            current_comments = []
        elif ":" in stripped:
            key = stripped.split(":")[0].strip()
            if key in answers:
                val = answers[key]
                if val is None or str(val).strip() == "FILL IN":
                    # Extract label and type from comments
                    label = current_comments[0] if current_comments else key
                    type_info = current_comments[1] if len(current_comments) > 1 else ""
                    fields.append({
                        "key": key,
                        "label": label,
                        "type_info": type_info,
                        "value": val,
                    })
            current_comments = []

    return fields


def resolve_cover_letter(entry: dict) -> str | None:
    """Load cover letter content for context."""
    submission = entry.get("submission", {})
    if not isinstance(submission, dict):
        return None
    variant_ids = submission.get("variant_ids", {})
    if not isinstance(variant_ids, dict):
        return None
    cl_ref = variant_ids.get("cover_letter")
    if not cl_ref:
        return None
    variant_path = VARIANTS_DIR / cl_ref
    if not variant_path.suffix:
        variant_path = variant_path.with_suffix(".md")
    if variant_path.exists():
        raw = variant_path.read_text().strip()
        # Strip frontmatter
        lines = raw.split("\n")
        body_start = 0
        found_separator = False
        for i, line in enumerate(lines):
            if line.strip() == "---":
                if found_separator:
                    body_start = i + 1
                    break
                found_separator = True
        return "\n".join(lines[body_start:]).strip()
    return None


def try_auto_answer(label: str, config: dict) -> str | None:
    """Try to match a field label against default_answers config patterns."""
    defaults = config.get("default_answers", {})
    if not defaults:
        return None
    for pattern, key in DEFAULT_ANSWER_PATTERNS:
        if pattern.search(label):
            answer = defaults.get(key)
            if answer:
                return str(answer)
    return None


def build_answer_prompt(entry: dict, fill_fields: list[dict], cover_letter: str | None) -> str:
    """Generate a prompt for AI to produce answers for custom questions."""
    entry_id = entry.get("id", "?")
    name = entry.get("name", entry_id)
    org = entry.get("target", {}).get("organization", "")
    framing = entry.get("fit", {}).get("framing", "")

    lines = [
        f"# Custom Question Answers: {name}",
        "",
        f"**Company:** {org}",
        f"**Role:** {name}",
        f"**Identity framing:** {framing}",
        "",
        "## Instructions",
        "",
        "Answer each question below based on the role context and cover letter.",
        "- Keep answers concise and professional",
        "- For text fields, 2-4 sentences unless a longer response is clearly needed",
        "- For select fields, choose from the provided options exactly as written",
        "- Do not fabricate qualifications or experience",
        "- Use first person",
        "",
        "Output each answer with a `### FIELD_KEY` marker, followed by the answer text.",
        "",
        "---",
        "",
    ]

    if cover_letter:
        lines.extend([
            "## Cover Letter (context for answering)",
            "",
            cover_letter,
            "",
            "---",
            "",
        ])

    lines.extend([
        "## Questions to Answer",
        "",
    ])

    for field in fill_fields:
        lines.extend([
            f"### {field['key']}",
            f"**Question:** {field['label']}",
            f"**{field['type_info']}**" if field['type_info'] else "",
            "",
        ])

    return "\n".join(lines)


def generate_prompt_file(entry: dict, config: dict) -> Path | None:
    """Generate answer prompt for an entry. Returns prompt path or None."""
    entry_id = entry.get("id", "?")
    portal = entry.get("target", {}).get("portal", "")

    answers_data = load_answer_template(entry_id, portal)
    if answers_data is None:
        print(f"  {entry_id}: No answer template found. Run --init-answers first.")
        return None

    # Read raw text for comment parsing
    answers_dir = get_answers_dir(portal)
    answer_path = answers_dir / f"{entry_id}.yaml"
    raw_text = answer_path.read_text()

    fill_fields = find_fill_in_fields(answers_data, raw_text)

    # Try auto-answering from defaults first
    auto_answered = 0
    remaining_fields = []
    for field in fill_fields:
        auto_answer = try_auto_answer(field["label"], config)
        if auto_answer:
            answers_data[field["key"]] = auto_answer
            auto_answered += 1
        else:
            remaining_fields.append(field)

    # Write back auto-answers if any were found
    if auto_answered > 0:
        # Rebuild the YAML preserving comments
        updated_text = raw_text
        for field in fill_fields:
            auto_answer = try_auto_answer(field["label"], config)
            if auto_answer:
                # Replace FILL IN with the auto answer for this key
                updated_text = re.sub(
                    rf'^({re.escape(field["key"])}:\s*).*$',
                    rf'\g<1>"{auto_answer}"',
                    updated_text,
                    count=1,
                    flags=re.MULTILINE,
                )
        answer_path.write_text(updated_text)
        print(f"  {entry_id}: Auto-answered {auto_answered} field(s) from defaults")

    if not remaining_fields:
        print(f"  {entry_id}: All fields answered (no prompt needed)")
        return None

    cover_letter = resolve_cover_letter(entry)
    prompt = build_answer_prompt(entry, remaining_fields, cover_letter)

    work_path = WORK_DIR / entry_id
    work_path.mkdir(parents=True, exist_ok=True)
    prompt_file = work_path / "answers-prompt.md"
    prompt_file.write_text(prompt)

    print(f"  {entry_id}: {len(remaining_fields)} field(s) need AI answers → {prompt_file.name}")
    return prompt_file


def integrate_answers(entry_id: str, output_text: str, portal: str) -> bool:
    """Parse AI output and update the answer YAML file.

    Expects output to contain sections delimited by ### field_key markers.
    """
    # Parse output into field answers
    section_pattern = re.compile(r'^###\s+(\S+)\s*$', re.MULTILINE)
    parts = section_pattern.split(output_text)
    parsed_answers = {}
    for i in range(1, len(parts) - 1, 2):
        field_key = parts[i].strip()
        answer = parts[i + 1].strip()
        # Clean up the answer — remove **Question:** lines
        answer_lines = []
        for line in answer.split("\n"):
            if line.startswith("**Question:") or line.startswith("**Type:"):
                continue
            answer_lines.append(line)
        parsed_answers[field_key] = "\n".join(answer_lines).strip()

    if not parsed_answers:
        print(f"  Error: No answers found in output for {entry_id}")
        return False

    print(f"  Found {len(parsed_answers)} answer(s): {', '.join(parsed_answers.keys())}")

    # Load existing answer file and update
    answers_dir = get_answers_dir(portal)
    answer_path = answers_dir / f"{entry_id}.yaml"
    if not answer_path.exists():
        print(f"  Error: Answer file not found: {answer_path}")
        return False

    raw_text = answer_path.read_text()

    for key, answer in parsed_answers.items():
        # Handle multiline answers
        if "\n" in answer:
            # Replace the FILL IN value with a block scalar
            yaml_val = f"|\n" + "\n".join(f"  {line}" for line in answer.split("\n"))
            raw_text = re.sub(
                rf'^({re.escape(key)}:\s*).*$',
                rf'\g<1>{yaml_val}',
                raw_text,
                count=1,
                flags=re.MULTILINE,
            )
        else:
            # Single line — quote it
            escaped = answer.replace('"', '\\"')
            raw_text = re.sub(
                rf'^({re.escape(key)}:\s*).*$',
                rf'\g<1>"{escaped}"',
                raw_text,
                count=1,
                flags=re.MULTILINE,
            )

    answer_path.write_text(raw_text)
    print(f"  Updated: {answer_path.name}")
    return True


def find_staged_job_entries(status: str = "staged") -> list[dict]:
    """Find active pipeline entries with job track and given status."""
    entries = load_entries(dirs=[PIPELINE_DIR_ACTIVE], include_filepath=True)
    return [
        e for e in entries
        if e.get("track") == "job"
        and e.get("status") == status
    ]


def main():
    parser = argparse.ArgumentParser(
        description="AI-assisted answer generator for custom portal questions"
    )
    parser.add_argument("--target", help="Target entry ID")
    parser.add_argument("--batch", action="store_true",
                        help="Process all matching entries")
    parser.add_argument("--status", default="staged",
                        help="Filter by status for --batch (default: staged)")
    parser.add_argument("--integrate", action="store_true",
                        help="Integrate AI output back into answer files")
    args = parser.parse_args()

    if not args.target and not args.batch:
        parser.error("Specify --target <id> or --batch")

    config = load_config()

    # Resolve entries
    if args.batch:
        entries = find_staged_job_entries(args.status)
        if not entries:
            print(f"No job entries with status '{args.status}' found.")
            sys.exit(1)
        print(f"Found {len(entries)} job entries with status '{args.status}':\n")
        for e in entries:
            print(f"  - {e.get('id')}: {e.get('name')} [{e.get('target', {}).get('portal', '?')}]")
        print()
    else:
        _, entry = load_entry_by_id(args.target)
        if not entry:
            print(f"Error: No pipeline entry found for '{args.target}'", file=sys.stderr)
            sys.exit(1)
        entries = [entry]

    # --integrate mode
    if args.integrate:
        results = []
        for entry in entries:
            eid = entry.get("id", "?")
            portal = entry.get("target", {}).get("portal", "")
            output_file = WORK_DIR / eid / "answers-output.md"
            if not output_file.exists():
                print(f"  {eid}: No output file at {output_file.name}")
                results.append((eid, False))
                continue
            output_text = output_file.read_text()
            ok = integrate_answers(eid, output_text, portal)
            results.append((eid, ok))
        if len(results) > 1:
            ok_count = sum(1 for _, ok in results if ok)
            print(f"\nIntegrated: {ok_count}/{len(results)}")
        return

    # Default: generate prompts
    results = []
    for entry in entries:
        eid = entry.get("id", "?")
        prompt_file = generate_prompt_file(entry, config)
        results.append((eid, prompt_file is not None))

    prompts_generated = sum(1 for _, ok in results if ok)
    auto_complete = sum(1 for _, ok in results if not ok)
    print(f"\nGenerated {prompts_generated} answer prompt(s).")
    if auto_complete:
        print(f"{auto_complete} entries fully answered (no prompts needed).")
    if prompts_generated:
        print(f"\nNext steps:")
        print(f"  1. Run each prompt through Claude to get answers")
        print(f"  2. Save output to .alchemize-work/<entry-id>/answers-output.md")
        print(f"  3. Run: python scripts/answer_questions.py --batch --integrate")


if __name__ == "__main__":
    main()
