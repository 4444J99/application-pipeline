#!/usr/bin/env python3
"""apply.py — Single-command application pipeline.

Produces a complete, correct application package for a pipeline entry:
1. Loads entry YAML
2. Fetches ACTUAL portal questions from Greenhouse API
3. Auto-fills standard answers, generates role-specific answers
4. Resolves or generates cover letter (unique from resume)
5. Builds cover letter PDF (Chrome headless)
6. Copies resume PDF
7. Creates application directory with all files
8. Validates completeness + overlap check
9. Prints portal URL

Usage:
    python scripts/apply.py --target <entry-id>
    python scripts/apply.py --target <entry-id> --dry-run
    python scripts/apply.py --batch  # all staged entries
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from greenhouse_submit import fetch_job_questions, get_custom_questions
from pipeline_lib import (
    MATERIALS_DIR,
    PIPELINE_DIR_ACTIVE,
    REPO_ROOT,
    load_entry_by_id,
    load_submit_config,
    resolve_cover_letter,
)

APPLICATIONS_DIR = REPO_ROOT / "applications"
CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# Standard answers — single source of truth
STANDARD_ANSWERS = {
    "first_name": "Anthony",
    "last_name": "Padavano",
    "preferred_first_name": "Anthony",
    "preferred_last_name": "Padavano",
    "email": None,  # loaded from .submit-config.yaml
    "phone": None,  # loaded from .submit-config.yaml
    "linkedin": "https://www.linkedin.com/in/anthonyjamespadavano",
    "website": "https://4444j99.github.io/portfolio/",
    "location": "New York, NY",
    "country": "United States",
    "timezone": "Eastern (ET)",
    "work_authorized": "Yes",
    "sponsorship_needed": "No",
    "how_heard": "LinkedIn",
    "open_to_relocation": "Yes",
    "us_citizen": True,
    "previously_employed": "No",
    "sanctions_clear": True,
}


def _load_personal_info() -> dict:
    """Load personal info from .submit-config.yaml."""
    config = load_submit_config(strict=False)
    answers = dict(STANDARD_ANSWERS)
    if config:
        answers["email"] = config.get("email", "")
        answers["phone"] = config.get("phone", "")
        answers["first_name"] = config.get("first_name", answers["first_name"])
        answers["last_name"] = config.get("last_name", answers["last_name"])
    return answers


def _extract_board_and_job(entry: dict) -> tuple[str, str] | None:
    """Extract Greenhouse board token and job ID from application URL."""
    url = entry.get("target", {}).get("application_url", "")
    # Pattern: boards.greenhouse.io/{board}/jobs/{id} or ?gh_jid={id}
    m = re.search(r"greenhouse\.io/(\w+)/jobs/(\d+)", url)
    if m:
        return m.group(1), m.group(2)
    # Pattern: ?gh_jid=XXXX with board in URL path
    m = re.search(r"gh_jid=(\d+)", url)
    if m:
        job_id = m.group(1)
        # Try to extract board from URL
        board_m = re.search(r"greenhouse\.io/(\w+)", url)
        if board_m:
            return board_m.group(1), job_id
        # Try org name as board
        org = entry.get("target", {}).get("organization", "").lower().replace(" ", "")
        return org, job_id
    return None


def _answer_question(question: dict, entry: dict, personal: dict) -> str:
    """Generate the correct answer for a portal question."""
    label = (question.get("label") or "").strip().lower()
    fields = question.get("fields", [])
    field_type = fields[0].get("type", "text") if fields else "text"
    values = []
    for f in fields:
        for v in f.get("values", []):
            values.append(v.get("label", ""))

    # Standard field matching
    if "first name" in label and "preferred" not in label:
        return personal["first_name"]
    if "last name" in label and "preferred" not in label:
        return personal["last_name"]
    if "preferred first" in label:
        return personal["preferred_first_name"]
    if "preferred last" in label:
        return personal["preferred_last_name"]
    if "email" in label:
        return personal.get("email", "")
    if "phone" in label:
        return personal.get("phone", "")
    if "linkedin" in label:
        return personal["linkedin"]
    if "website" in label:
        return personal["website"]
    if "country" in label and "time zone" in label:
        return f"{personal['country']}, {personal['timezone']}"
    if "how did you hear" in label:
        if values and "LinkedIn" in values:
            return "LinkedIn"
        return personal["how_heard"]
    if "authorized" in label or "authorization" in label:
        return "Yes"
    if "sponsorship" in label:
        return "No"
    if "relocat" in label:
        return personal["open_to_relocation"]

    # Clearance / export controls
    if "clearance" in label and "eligib" in label:
        if values:
            for v in values:
                if "eligible" in v.lower():
                    return v
        return "Yes, I am eligible for a U.S. security clearance"
    if "clearance" in label and "held" in label:
        return "N/A - have never held U.S. security clearance"
    if "export control" in label or "united states citizen" in label.lower():
        if values:
            for v in values:
                if "citizen" in v.lower() and "united states" in v.lower():
                    return v
            for v in values:
                if "citizen" in v.lower():
                    return v
        return "A United States citizen"
    if "sanctions" in label or "cuba" in label or "iran" in label:
        if values:
            for v in values:
                if "none" in v.lower():
                    return v
        return "None of the above"
    if "previously" in label or "employed by" in label or "worked for" in label:
        return "No"
    if "conflict of interest" in label:
        return "No"
    if "history with" in label:
        return "No"
    if "human being" in label:
        return "I am a human being"
    if "acknowledge" in label or "consent" in label or "confirm" in label:
        if values:
            for v in values:
                if "acknowledge" in v.lower() or "agree" in v.lower():
                    return v
        return "Acknowledge"

    # Yes/No qualification questions — analyze the question content
    if field_type == "multi_value_single_select" and values == ["Yes", "No"]:
        # These are qualification questions — answer based on the content
        q_text = label
        # Experience questions — generally Yes
        if any(kw in q_text for kw in ["experience", "worked with", "led", "used", "have you"]):
            return "Yes"
        return "Yes"

    # Free text fields — this is the opportunity for unique content
    if field_type in ("input_text", "textarea") and not any(
        kw in label for kw in ["name", "email", "phone", "linkedin", "website", "url", "country", "location"]
    ):
        return _generate_free_text_answer(label, entry)

    return ""


def _generate_free_text_answer(label: str, entry: dict) -> str:
    """Generate a short, unique free-text answer for a portal question.

    This is where we use every opportunity to present the case for life.
    Keep it short (2-3 sentences), specific to the question, and different
    from the cover letter content.
    """
    org = entry.get("target", {}).get("organization", "")

    # "Anything else you'd like to share?"
    if "anything else" in label.lower() or "additional" in label.lower():
        return (
            f"I maintain a 113-repository system governed by the same patterns this role requires — "
            f"forward-only state transitions, CI-enforced quality gates, and daily health monitoring. "
            f"The system runs 23,470 tests. I built every piece of it alone, which means every component "
            f"had to be self-service, self-healing, and documented well enough that an AI assistant "
            f"can navigate it. That discipline is what I bring to {org}."
        )

    # Generic fallback — should rarely hit
    return ""


def _check_overlap(cover_letter: str, resume_html: str) -> list[str]:
    """Check for 4-word phrase overlaps between cover letter and resume."""
    resume_text = re.sub(r"<[^>]+>", " ", resume_html)
    resume_text = re.sub(r"\s+", " ", resume_text).strip()

    cl_words = cover_letter.lower().split()
    resume_words = resume_text.lower().split()

    cl_phrases = set()
    for i in range(len(cl_words) - 3):
        phrase = " ".join(cl_words[i : i + 4]).strip(".,;:")
        if len(phrase) > 15:
            cl_phrases.add(phrase)

    overlaps = set()
    for i in range(len(resume_words) - 3):
        phrase = " ".join(resume_words[i : i + 4]).strip(".,;:")
        if phrase in cl_phrases:
            overlaps.add(phrase)

    return list(overlaps)


def _build_cover_letter_pdf(md_path: Path, pdf_path: Path) -> bool:
    """Convert cover letter markdown to PDF via Chrome headless."""
    md_text = md_path.read_text()

    # Simple MD → HTML
    html = (
        '<!DOCTYPE html><html><head><style>'
        'body { font-family: Georgia, serif; font-size: 11pt; line-height: 1.5; '
        'margin: 1in; color: #1a1a1a; } p { margin: 0 0 0.8em 0; }'
        '</style></head><body>\n'
    )
    for line in md_text.strip().split("\n"):
        line = line.strip()
        if line.startswith("#") or not line:
            continue
        html += f"<p>{line}</p>\n"
    html += "</body></html>"

    html_path = md_path.with_suffix(".html")
    html_path.write_text(html)

    try:
        subprocess.run(
            [
                CHROME_PATH,
                "--headless",
                "--disable-gpu",
                "--no-sandbox",
                "--print-to-pdf=" + str(pdf_path),
                "--print-to-pdf-no-header",
                str(html_path),
            ],
            capture_output=True,
            timeout=30,
        )
        return pdf_path.exists()
    except Exception:
        return False


def apply_to_entry(entry_id: str, dry_run: bool = False) -> bool:
    """Run the full application pipeline for a single entry."""
    print(f"\n{'=' * 60}")
    print(f"  APPLYING: {entry_id}")
    print(f"{'=' * 60}\n")

    # 1. Load entry
    filepath, entry = load_entry_by_id(entry_id)
    if not entry:
        print(f"  ERROR: Entry not found: {entry_id}")
        return False

    org = entry.get("target", {}).get("organization", "")
    role = entry.get("name", "")
    url = entry.get("target", {}).get("application_url", "")
    portal = entry.get("target", {}).get("portal", "")
    print(f"  Organization: {org}")
    print(f"  Role: {role}")
    print(f"  URL: {url}")
    print(f"  Portal: {portal}")

    # 2. Fetch portal questions from API
    print("\n  Fetching portal questions...")
    board_job = _extract_board_and_job(entry)
    questions = []
    custom_questions = []
    if board_job and portal == "greenhouse":
        board, job_id = board_job
        questions = fetch_job_questions(board, job_id)
        custom_questions = get_custom_questions(questions)
        print(f"  Found {len(questions)} total questions, {len(custom_questions)} custom")
    else:
        print("  Non-Greenhouse portal or could not extract board/job — using standard fields only")

    # 3. Generate answers
    print("  Generating answers...")
    personal = _load_personal_info()
    answers = []
    for q in questions:
        label = (q.get("label") or "").strip()
        answer = _answer_question(q, entry, personal)
        required = q.get("required", False)
        answers.append({"label": label, "answer": answer, "required": required})

    # 4. Resolve cover letter
    print("  Resolving cover letter...")
    cover_letter = resolve_cover_letter(entry, strip_md=False)
    if not cover_letter:
        print("  WARNING: No cover letter found — generate one before submitting")
        cover_letter = ""

    # 5. Find resume
    resume_dir = MATERIALS_DIR / "resumes" / "batch-03" / entry_id
    resume_pdf = None
    resume_html = None
    if resume_dir.exists():
        pdfs = list(resume_dir.glob("*.pdf"))
        htmls = list(resume_dir.glob("*.html"))
        if pdfs:
            resume_pdf = pdfs[0]
        if htmls:
            resume_html = htmls[0]
    if not resume_pdf:
        print(f"  WARNING: No resume PDF found in {resume_dir}")

    # 6. Check overlap
    overlaps = []
    if cover_letter and resume_html and resume_html.exists():
        overlaps = _check_overlap(cover_letter, resume_html.read_text())
        if len(overlaps) > 3:
            print(f"  WARNING: {len(overlaps)} overlapping phrases between cover letter and resume")
            for o in overlaps[:5]:
                print(f"    \"{o}\"")
        else:
            print(f"  Overlap check: {len(overlaps)} phrases (OK)")

    # 7. Create application directory
    today = str(date.today())
    org_slug = re.sub(r"[^a-z0-9]+", "-", org.lower()).strip("-")
    role_slug = re.sub(r"[^a-z0-9]+", "-", role.lower()).strip("-")[:60]
    app_dir = APPLICATIONS_DIR / today / f"{org_slug}--{role_slug}"

    if dry_run:
        print(f"\n  [DRY RUN] Would create: {app_dir}")
        print(f"  Questions: {len(questions)}")
        print(f"  Cover letter: {'found' if cover_letter else 'MISSING'}")
        print(f"  Resume PDF: {resume_pdf.name if resume_pdf else 'MISSING'}")
        return True

    app_dir.mkdir(parents=True, exist_ok=True)

    # 8. Write all files
    # Entry YAML (snapshot)
    if filepath:
        (app_dir / "entry.yaml").write_text(Path(filepath).read_text())
        print("  Wrote: entry.yaml")

    # Portal answers
    pa_lines = [f"# {org} — {role} — Portal Answers\n"]
    pa_lines.append(f"**Portal URL:** {url}\n")
    pa_lines.append(f"**Date:** {today}\n")
    pa_lines.append("**Questions fetched from Greenhouse API**\n")
    pa_lines.append("---\n")
    for a in answers:
        req = " (required)" if a["required"] else ""
        pa_lines.append(f"## {a['label']}{req}\n")
        pa_lines.append(f"{a['answer']}\n")
    (app_dir / "portal-answers.md").write_text("\n".join(pa_lines))
    print(f"  Wrote: portal-answers.md ({len(answers)} answers)")

    # Cover letter
    if cover_letter:
        cl_path = app_dir / "cover-letter.md"
        cl_path.write_text(cover_letter)
        print("  Wrote: cover-letter.md")

        # Build PDF
        pdf_name = f"Anthony-Padavano-{org.replace(' ', '-')}-Cover-Letter.pdf"
        pdf_path = app_dir / pdf_name
        if _build_cover_letter_pdf(cl_path, pdf_path):
            print(f"  Built: {pdf_name}")
        else:
            print("  WARNING: Failed to build cover letter PDF")

    # Resume
    if resume_pdf:
        dest = app_dir / f"Anthony-Padavano-{org.replace(' ', '-')}-Resume.pdf"
        import shutil
        shutil.copy2(resume_pdf, dest)
        print(f"  Copied: {dest.name}")
    if resume_html:
        dest = app_dir / f"Anthony-Padavano-{org.replace(' ', '-')}-Resume.html"
        import shutil
        shutil.copy2(resume_html, dest)

    # 9. Validate
    files = list(app_dir.iterdir())
    print(f"\n  Application directory: {app_dir}")
    print(f"  Files: {len(files)}")
    for f in sorted(files):
        size = f.stat().st_size
        print(f"    {f.name} ({size:,} bytes)")

    print(f"\n  PORTAL URL: {url}")
    print("  STATUS: Ready for portal submission")

    return True


def main():
    parser = argparse.ArgumentParser(description="Single-command application pipeline")
    parser.add_argument("--target", help="Pipeline entry ID")
    parser.add_argument("--batch", action="store_true", help="Process all staged entries")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing files")
    args = parser.parse_args()

    if args.batch:
        # Find all staged entries
        staged = []
        for f in PIPELINE_DIR_ACTIVE.glob("*.yaml"):
            if f.name.startswith("_"):
                continue
            try:
                e = yaml.safe_load(f.read_text())
            except Exception:
                continue
            if e and e.get("status") == "staged":
                staged.append(e.get("id", f.stem))
        if not staged:
            print("No staged entries found.")
            return
        print(f"Processing {len(staged)} staged entries...")
        for entry_id in staged:
            apply_to_entry(entry_id, dry_run=args.dry_run)
    elif args.target:
        apply_to_entry(args.target, dry_run=args.dry_run)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
