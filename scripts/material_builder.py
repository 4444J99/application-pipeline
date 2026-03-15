#!/usr/bin/env python3
"""Material builder: LLM-powered generation of application materials.

Generates cover letters, answers, and block selections for qualified entries
using google-genai. All outputs are saved as drafts requiring human approval.

Usage:
    python scripts/material_builder.py --target <id>              # Single entry, dry-run
    python scripts/material_builder.py --yes                      # Build all qualified
    python scripts/material_builder.py --target <id> --approve    # Build + approve
    python scripts/material_builder.py --component cover_letter   # Cover letters only
    python scripts/material_builder.py --json                     # Machine-readable
"""

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import (
    ALL_PIPELINE_DIRS,
    SIGNALS_DIR,
    load_block,
    load_entries,
    load_entry_by_id,
    load_profile,
    resolve_cover_letter,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
BLOCKS_DIR = REPO_ROOT / "blocks"
MATERIALS_DIR = REPO_ROOT / "materials"
BUILD_HISTORY_PATH = SIGNALS_DIR / "build-history.yaml"
DRAFTS_DIR = MATERIALS_DIR / "drafts"

# Base resume paths per identity position
RESUME_MAP = {
    "independent-engineer": "resumes/base/independent-engineer-resume.html",
    "systems-artist": "resumes/base/systems-artist-resume.html",
    "educator": "resumes/base/educator-resume.html",
    "creative-technologist": "resumes/base/creative-technologist-resume.html",
    "community-practitioner": "resumes/base/community-practitioner-resume.html",
    "documentation-engineer": "resumes/base/documentation-engineer-resume.html",
    "governance-architect": "resumes/base/governance-architect-resume.html",
    "platform-orchestrator": "resumes/base/platform-orchestrator-resume.html",
    "founder-operator": "resumes/base/founder-operator-resume.html",
}

# Block slot priorities per identity position
BLOCK_SLOTS = {
    "independent-engineer": {
        "identity": "identity/2min",
        "framing": "framings/independent-engineer",
        "evidence": "evidence/engineering-at-scale",
        "methodology": "methodology/ai-conductor",
    },
    "systems-artist": {
        "identity": "identity/2min",
        "framing": "framings/systems-artist",
        "evidence": "evidence/organvm-system",
    },
    "educator": {
        "identity": "identity/2min",
        "framing": "framings/educator",
    },
    "creative-technologist": {
        "identity": "identity/2min",
        "framing": "framings/creative-technologist",
    },
    "community-practitioner": {
        "identity": "identity/2min",
        "framing": "framings/community-practitioner",
    },
    "documentation-engineer": {
        "identity": "identity/2min",
        "framing": "framings/independent-engineer",
        "evidence": "evidence/system-overview",
        "methodology": "methodology/ai-conductor",
    },
    "governance-architect": {
        "identity": "identity/2min",
        "framing": "framings/eu-ai-compliance",
        "evidence": "evidence/system-overview",
    },
    "platform-orchestrator": {
        "identity": "identity/2min",
        "framing": "framings/ai-orchestrator",
        "evidence": "evidence/engineering-at-scale",
        "methodology": "methodology/ai-conductor",
    },
    "founder-operator": {
        "identity": "identity/2min",
        "framing": "framings/disability-founder",
        "evidence": "evidence/system-overview",
    },
}

VARIANTS_DIR = REPO_ROOT / "variants" / "cover-letters"
MODEL_NAME = "gemini-2.5-pro"


@dataclass
class MaterialDraft:
    """A generated material draft."""

    entry_id: str
    component: str
    content: str
    status: str  # draft | approved
    generated_at: str
    model_used: str
    identity_position: str


@dataclass
class BuildResult:
    """Result of a material build operation."""

    entries_processed: list[str] = field(default_factory=list)
    cover_letters_generated: int = 0
    answers_generated: int = 0
    resumes_wired: int = 0
    resumes_tailored: int = 0
    blocks_selected: int = 0
    errors: list[str] = field(default_factory=list)


def _call_llm(system_prompt: str, user_prompt: str) -> str:
    """Call google-genai for text generation."""
    from google import genai

    client = genai.Client()
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=user_prompt,
        config=genai.types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.4,
        ),
    )
    return response.text


def fetch_posting_text(entry: dict) -> str:
    """Fetch the full job posting description from the ATS API.

    Supports Greenhouse, Lever, and Ashby portals. Falls back to
    entry notes/title if the API call fails.
    """
    import json as _json
    import urllib.error
    import urllib.request

    portal = entry.get("target", {}).get("portal", "")
    app_url = entry.get("target", {}).get("application_url", "")
    fallback = entry.get("notes", "") or entry.get("target", {}).get("title", "")

    try:
        if portal == "greenhouse":
            from greenhouse_submit import parse_greenhouse_url
            parsed = parse_greenhouse_url(app_url, entry.get("target", {}).get("url", ""))
            if parsed:
                board, job_id = parsed
                url = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs/{job_id}"
                req = urllib.request.Request(url, headers={"Accept": "application/json"})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = _json.loads(resp.read().decode())
                content = data.get("content", "")
                title = data.get("title", "")
                # Strip HTML tags for clean text
                import re
                clean = re.sub(r"<[^>]+>", " ", content)
                clean = re.sub(r"\s+", " ", clean).strip()
                return f"{title}\n\n{clean}" if clean else fallback

        elif portal == "lever":
            from lever_submit import parse_lever_url
            parsed = parse_lever_url(app_url)
            if parsed:
                company, posting_id, is_eu = parsed
                region = "eu." if is_eu else ""
                url = f"https://api.{region}lever.co/v0/postings/{company}/{posting_id}"
                req = urllib.request.Request(url, headers={"Accept": "application/json"})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = _json.loads(resp.read().decode())
                desc = data.get("descriptionPlain", "") or data.get("description", "")
                title = data.get("text", "")
                return f"{title}\n\n{desc}" if desc else fallback

        elif portal == "ashby":
            from ashby_submit import parse_ashby_url
            parsed = parse_ashby_url(app_url)
            if parsed:
                company, posting_id = parsed
                url = "https://api.ashbyhq.com/posting-api/posting-info"
                body = _json.dumps({"postingId": posting_id}).encode()
                req = urllib.request.Request(url, data=body, method="POST",
                                            headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = _json.loads(resp.read().decode())
                info = data.get("info", {})
                desc = info.get("descriptionPlain", "") or info.get("descriptionHtml", "")
                title = info.get("title", "")
                import re
                clean = re.sub(r"<[^>]+>", " ", desc)
                clean = re.sub(r"\s+", " ", clean).strip()
                return f"{title}\n\n{clean}" if clean else fallback

    except Exception:
        pass

    return fallback


def _wire_cover_letter(entry_id: str, content: str, dry_run: bool = True) -> Path | None:
    """Save cover letter to variants/ and return the path."""
    if dry_run:
        return None
    VARIANTS_DIR.mkdir(parents=True, exist_ok=True)
    path = VARIANTS_DIR / f"{entry_id}.md"
    path.write_text(content)
    return path


def _wire_entry_materials(
    entry_id: str,
    cover_letter_path: str | None = None,
    blocks_used: dict | None = None,
    resume_path: str | None = None,
    dry_run: bool = True,
) -> bool:
    """Write material references into the pipeline entry YAML.

    Updates submission.variant_ids.cover_letter, submission.blocks_used,
    and submission.materials_attached with the generated material paths.
    """
    if dry_run:
        return True

    filepath, entry = load_entry_by_id(entry_id)
    if not filepath or not entry:
        return False

    try:
        from yaml_mutation import YAMLEditor
    except ImportError:
        return False

    content = Path(filepath).read_text()
    editor = YAMLEditor(content)

    if cover_letter_path:
        editor.set("submission.variant_ids.cover_letter", cover_letter_path)

    if blocks_used:
        for slot, block_path in blocks_used.items():
            editor.set(f"submission.blocks_used.{slot}", block_path)

    if resume_path:
        # Add to materials_attached if not already present
        existing = entry.get("submission", {}).get("materials_attached", []) or []
        if resume_path not in existing:
            existing.append(resume_path)
            editor.set("submission.materials_attached", existing)

    editor.touch()
    Path(filepath).write_text(editor.dump())
    return True


def generate_answers(entry: dict, posting_text: str) -> dict[str, str]:
    """Generate answers for custom portal questions using LLM.

    Returns dict of {field_key: answer_text}.
    """
    portal = entry.get("target", {}).get("portal", "")
    entry_id = entry.get("id", "")

    try:
        from answer_questions import (
            find_fill_in_fields,
            load_answer_template,
            load_config,
            try_auto_answer,
        )
    except ImportError:
        return {}

    config = load_config()
    answers_data = load_answer_template(entry_id, portal)
    if answers_data is None:
        return {}

    # Get the raw YAML for comment parsing
    from answer_questions import get_answers_dir
    answer_path = get_answers_dir(portal) / f"{entry_id}.yaml"
    if not answer_path.exists():
        return {}

    raw_text = answer_path.read_text()
    fill_fields = find_fill_in_fields(answers_data, raw_text)

    # Try auto-answer first
    remaining = []
    auto_answers = {}
    for f in fill_fields:
        auto = try_auto_answer(f["label"], config)
        if auto:
            auto_answers[f["key"]] = auto
        else:
            remaining.append(f)

    if not remaining:
        return auto_answers

    # Build LLM prompt for remaining fields
    org = entry.get("target", {}).get("organization", "")
    title = entry.get("target", {}).get("title", "")
    position = entry.get("identity_position", "independent-engineer")

    system_prompt = (
        f"Answer custom application questions for {title} at {org}. "
        f"Identity position: {position}. "
        "Use ONLY facts from the provided context. Do NOT fabricate experience. "
        "Keep answers concise (2-4 sentences for text, exact match for select fields)."
    )

    questions_text = "\n".join(
        f"- {f['label']} [{f['type_info']}] (key: {f['key']})"
        for f in remaining
    )
    user_prompt = (
        f"JOB POSTING:\n{posting_text}\n\n"
        f"QUESTIONS:\n{questions_text}\n\n"
        "For each question, output:\n### FIELD_KEY\nanswer text\n"
    )

    try:
        output = _call_llm(system_prompt, user_prompt)
    except Exception:
        return auto_answers

    # Parse LLM output into field answers
    import re
    section_pattern = re.compile(r'^###\s+(\S+)\s*$', re.MULTILINE)
    parts = section_pattern.split(output)
    for i in range(1, len(parts) - 1, 2):
        key = parts[i].strip()
        answer = parts[i + 1].strip()
        # Remove metadata lines
        lines = [l for l in answer.split("\n")
                 if not l.startswith("**Question:") and not l.startswith("**Type:")]
        auto_answers[key] = "\n".join(lines).strip()

    return auto_answers


def select_blocks_for_entry(entry: dict) -> dict[str, str]:
    """Select best blocks for an entry based on identity position."""
    position = entry.get("identity_position", "independent-engineer")
    slots = BLOCK_SLOTS.get(position, BLOCK_SLOTS["independent-engineer"])

    selected = {}
    if not BLOCKS_DIR.exists():
        return selected

    for slot, block_path in slots.items():
        content = load_block(block_path)
        if content:
            selected[slot] = block_path
    return selected


def _template_cover_letter(
    entry: dict,
    block_contents: list[str],
    job_posting: str,
) -> str:
    """Generate a cover letter from blocks using templates (no LLM required).

    Composes a structured cover letter from identity blocks and profile content.
    This is the fallback when no LLM is available, ensuring the pipeline can
    operate autonomously without API keys.
    """
    org = entry.get("target", {}).get("organization", "the organization")
    title = entry.get("target", {}).get("title", "the role")
    entry_id = entry.get("id", "")
    position = entry.get("identity_position", "independent-engineer")

    # Try loading profile for artist statement / bio
    profile = load_profile(entry_id) if entry_id else None
    artist_stmt = ""
    if profile:
        stmts = profile.get("artist_statements", {})
        artist_stmt = stmts.get("short", stmts.get("medium", ""))

    # Extract key evidence from blocks (first 3 sentences from each)
    evidence_paras = []
    for bc in block_contents[:3]:
        sentences = [s.strip() for s in bc.replace("\n", " ").split(".") if s.strip()]
        top = ". ".join(sentences[:3]) + "." if sentences else ""
        if top:
            evidence_paras.append(top)

    # Compose letter
    sections = [f"Dear Hiring Team at {org},"]

    # Opening: who I am + why this role
    if artist_stmt:
        sections.append(
            f"I am writing to express my interest in the {title} position. "
            f"{artist_stmt}"
        )
    else:
        sections.append(
            f"I am writing to express my interest in the {title} position at {org}. "
            f"My background in {position.replace('-', ' ')} aligns directly with "
            f"the requirements of this role."
        )

    # Evidence paragraphs from blocks
    for para in evidence_paras:
        sections.append(para)

    # Closing
    sections.append(
        "I would welcome the opportunity to discuss how my experience "
        f"can contribute to {org}'s mission. Thank you for your consideration."
    )
    sections.append("Sincerely,\nAnthony James Padavano")

    return "\n\n".join(sections)


def generate_cover_letter(
    entry: dict,
    block_contents: list[str],
    job_posting: str,
) -> str:
    """Generate a cover letter from blocks + job posting context.

    Tries LLM first (google-genai), falls back to template-based generation
    for autonomous operation without API keys.
    """
    position = entry.get("identity_position", "independent-engineer")
    org = entry.get("target", {}).get("organization", "the organization")
    title = entry.get("target", {}).get("title", "the role")

    system_prompt = (
        f"You are writing a cover letter for a {title} position at {org}. "
        f"Your identity position is: '{position}'. "
        "Use ONLY the facts, metrics, and evidence from the provided blocks. "
        "Do NOT fabricate any experience, metrics, or evidence. "
        "Lead with numbers and concrete achievements. "
        "One sentence, one claim — maintain scannability. "
        "Target length: 350-450 words. "
        "Output the cover letter directly without preamble."
    )

    blocks_text = "\n\n---\n\n".join(block_contents)
    user_prompt = (
        f"JOB POSTING:\n{job_posting}\n\n"
        f"EVIDENCE BLOCKS:\n{blocks_text}\n\n"
        "Write a cover letter for this role using only the evidence above."
    )

    try:
        return _call_llm(system_prompt, user_prompt)
    except ImportError:
        # No google-genai — use template fallback
        return _template_cover_letter(entry, block_contents, job_posting)
    except Exception:
        # LLM error — use template fallback
        return _template_cover_letter(entry, block_contents, job_posting)


def tailor_resume(entry: dict, cover_letter: str, posting_text: str, dry_run: bool = True) -> str | None:
    """Generate a role-tailored resume for an entry (full autonomous cycle).

    1. Extract sections from the base HTML template
    2. Build a tailoring prompt with cover letter + job posting
    3. Send to LLM (or return base resume path if no LLM)
    4. Integrate LLM output into HTML template
    5. Convert HTML → PDF via headless Chrome
    6. Wire the resume into the pipeline entry YAML

    Returns the resume reference path (relative to repo root) or None.
    """
    entry_id = entry.get("id", "")
    position = entry.get("identity_position", "independent-engineer")

    if dry_run or not entry_id:
        return None

    try:
        from tailor_resume import (
            build_tailoring_prompt,
            extract_sections,
            integrate_tailored_sections,
            load_base_template,
            wire_resume_to_entry,
        )
    except ImportError:
        return None

    # Step 1: Load base template and extract sections
    template_html = load_base_template(position)
    sections = extract_sections(template_html)
    if not sections:
        return None

    # Step 2: Build tailoring prompt
    prompt = build_tailoring_prompt(entry, sections, cover_letter)

    # Step 3: Send to LLM
    system_prompt = (
        "You are a resume tailoring expert. Rewrite the resume sections to match "
        "the target role. Preserve all factual claims. Reorder and re-emphasize "
        "to front-load relevance. Keep the same HTML structure. "
        "Output each section with a ### SECTION_NAME marker."
    )
    try:
        llm_output = _call_llm(system_prompt, prompt)
    except Exception:
        # No LLM available — can't tailor, use base resume
        return None

    # Step 4: Integrate into HTML template
    html_path = integrate_tailored_sections(entry_id, llm_output, position)
    if not html_path:
        return None

    # Step 5: Convert HTML → PDF
    try:
        from build_resumes import build_pdf, find_chrome
        chrome = find_chrome()
        if chrome:
            pdf_path = html_path.with_suffix(".pdf")
            build_pdf(chrome, html_path, pdf_path)
    except ImportError:
        pass  # PDF build is optional; HTML is still usable

    # Step 6: Wire into pipeline YAML
    wire_resume_to_entry(entry_id)

    # Return the reference path
    from pipeline_lib import CURRENT_BATCH
    return f"resumes/{CURRENT_BATCH}/{entry_id}/{entry_id}-resume.html"


def wire_resume(identity_position: str, entry_id: str = "") -> str:
    """Select the best resume path, preferring tailored batch resumes.

    Resolution order:
    1. Batch-03 tailored resume (entry-specific PDF or HTML)
    2. Base identity-position resume (generic)
    """
    # Check for tailored batch-03 resume first
    if entry_id:
        batch_dir = MATERIALS_DIR / "resumes" / "batch-03" / entry_id
        if batch_dir.exists():
            for f in batch_dir.iterdir():
                if f.suffix.lower() == ".pdf":
                    return str(f.relative_to(MATERIALS_DIR.parent))
            for f in batch_dir.iterdir():
                if f.suffix.lower() == ".html":
                    return str(f.relative_to(MATERIALS_DIR.parent))

    return RESUME_MAP.get(identity_position, RESUME_MAP["independent-engineer"])


def _load_buildable_entries(entry_ids: list[str] | None = None) -> list[dict]:
    """Load qualified entries that need materials built."""
    entries = load_entries(dirs=ALL_PIPELINE_DIRS)
    buildable = []
    for e in entries:
        if entry_ids and e.get("id") not in entry_ids:
            continue
        if e.get("status") not in ("qualified", "drafting"):
            continue
        submission = e.get("submission") or {}
        has_cover = bool(resolve_cover_letter(e))
        has_blocks = bool(submission.get("blocks_used"))
        if not has_cover or not has_blocks:
            buildable.append(e)
    return buildable


def _save_draft(draft: MaterialDraft, dry_run: bool = True) -> Path | None:
    """Save a material draft to the drafts directory."""
    if dry_run:
        return None
    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{draft.entry_id}--{draft.component}.md"
    path = DRAFTS_DIR / filename
    header = (
        f"---\n"
        f"entry_id: {draft.entry_id}\n"
        f"component: {draft.component}\n"
        f"status: {draft.status}\n"
        f"generated_at: {draft.generated_at}\n"
        f"model_used: {draft.model_used}\n"
        f"identity_position: {draft.identity_position}\n"
        f"---\n\n"
    )
    path.write_text(header + draft.content)
    return path


def build_materials(
    entry_ids: list[str] | None = None,
    components: list[str] | None = None,
    dry_run: bool = True,
    approve: bool = False,
) -> BuildResult:
    """Generate application materials for qualified entries.

    Args:
        entry_ids: Specific entries. None = all qualified missing materials.
        components: Components to build. None = all.
                    Options: cover_letter, answers, resume, blocks.
        dry_run: If True, don't write files.
        approve: If True, mark materials as approved (not draft).
    """
    if components is None:
        components = ["cover_letter", "blocks", "resume", "answers"]

    entries = _load_buildable_entries(entry_ids)
    result = BuildResult()

    for entry in entries:
        entry_id = entry.get("id", "")
        position = entry.get("identity_position", "independent-engineer")
        now = datetime.now().isoformat()
        status = "approved" if approve else "draft"

        try:
            # Fetch full job posting for LLM context
            posting_text = fetch_posting_text(entry)

            # Block selection
            selected_blocks = {}
            if "blocks" in components:
                selected_blocks = select_blocks_for_entry(entry)
                if selected_blocks:
                    result.blocks_selected += len(selected_blocks)

            # Cover letter — generated per-job from blocks + profile
            generated_letter = ""
            cover_letter_variant_path = None
            if "cover_letter" in components:
                block_contents = []
                for block_path in selected_blocks.values():
                    content = load_block(block_path)
                    if content:
                        block_contents.append(content)

                if block_contents:
                    generated_letter = generate_cover_letter(entry, block_contents, posting_text)
                    draft = MaterialDraft(
                        entry_id=entry_id,
                        component="cover_letter",
                        content=generated_letter,
                        status=status,
                        generated_at=now,
                        model_used=MODEL_NAME,
                        identity_position=position,
                    )
                    _save_draft(draft, dry_run=dry_run)
                    cl_path = _wire_cover_letter(entry_id, generated_letter, dry_run=dry_run)
                    if cl_path:
                        cover_letter_variant_path = str(cl_path.relative_to(REPO_ROOT))
                    result.cover_letters_generated += 1

            # Answer generation
            if "answers" in components:
                answers = generate_answers(entry, posting_text)
                if answers:
                    result.answers_generated += len(answers)
                    # Write answers back to portal answer file
                    if not dry_run:
                        try:
                            from answer_questions import integrate_answers
                            portal = entry.get("target", {}).get("portal", "")
                            formatted = "\n".join(
                                f"### {k}\n{v}" for k, v in answers.items()
                            )
                            integrate_answers(entry_id, formatted, portal)
                        except Exception:
                            pass

            # Resume — tailored per-job when LLM available, best-available fallback
            resume_ref = None
            if "resume" in components:
                tailored = tailor_resume(entry, generated_letter, posting_text, dry_run=dry_run)
                if tailored:
                    resume_ref = tailored
                    result.resumes_tailored += 1
                else:
                    resume_ref = wire_resume(position, entry_id=entry_id)
                result.resumes_wired += 1

            # Wire all materials into entry YAML
            if not dry_run and (cover_letter_variant_path or selected_blocks or resume_ref):
                _wire_entry_materials(
                    entry_id,
                    cover_letter_path=cover_letter_variant_path,
                    blocks_used=selected_blocks,
                    resume_path=resume_ref,
                    dry_run=False,
                )

            result.entries_processed.append(entry_id)
        except Exception as e:
            result.errors.append(f"{entry_id}: {e}")

    return result


def _log_build_result(result: BuildResult, log_path: Path | None = None) -> None:
    """Append build result to history log."""
    log_path = log_path or BUILD_HISTORY_PATH
    entry = {
        "date": str(date.today()),
        "entries_processed": len(result.entries_processed),
        "cover_letters": result.cover_letters_generated,
        "answers": result.answers_generated,
        "resumes_wired": result.resumes_wired,
        "resumes_tailored": result.resumes_tailored,
        "blocks_selected": result.blocks_selected,
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
    parser = argparse.ArgumentParser(
        description="Material builder: LLM-powered generation"
    )
    parser.add_argument("--target", help="Build for single entry")
    parser.add_argument("--yes", action="store_true", help="Execute (write files)")
    parser.add_argument("--approve", action="store_true", help="Mark as approved")
    parser.add_argument(
        "--component",
        help="Component: cover_letter, answers, resume, blocks",
    )
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    dry_run = not args.yes
    entry_ids = [args.target] if args.target else None
    components = [args.component] if args.component else None

    result = build_materials(
        entry_ids=entry_ids,
        components=components,
        dry_run=dry_run,
        approve=args.approve,
    )

    if not dry_run:
        _log_build_result(result)

    if args.json:
        print(json.dumps(asdict(result), indent=2))
    else:
        mode = "DRY-RUN" if dry_run else "EXECUTED"
        print(f"\n{'=' * 50}")
        print(f"BUILD RESULTS ({mode})")
        print(f"{'=' * 50}")
        print(f"Entries processed:     {len(result.entries_processed)}")
        print(f"Cover letters:         {result.cover_letters_generated}")
        print(f"Answers generated:     {result.answers_generated}")
        print(f"Resumes tailored:      {result.resumes_tailored}")
        print(f"Resumes wired:         {result.resumes_wired}")
        print(f"Blocks selected:       {result.blocks_selected}")
        if result.errors:
            print(f"\nErrors ({len(result.errors)}):")
            for err in result.errors:
                print(f"  - {err}")
        if result.entries_processed:
            print("\nProcessed:")
            for eid in result.entries_processed:
                print(f"  - {eid}")


if __name__ == "__main__":
    main()
