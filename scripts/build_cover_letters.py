#!/usr/bin/env python3
"""Build cover letter PDFs from markdown sources.

Converts cover-letter.md files in batch-03/ to styled HTML and PDF,
using the same Chrome headless pipeline as build_resumes.py.

The HTML template matches the resume visual identity (Georgia, centered
header, 1.5pt border) but uses a letter-appropriate layout (larger font,
justified text, no two-column sections).

Usage:
    python scripts/build_cover_letters.py                    # Build all
    python scripts/build_cover_letters.py --target <id>      # Single target
    python scripts/build_cover_letters.py --check            # Check freshness
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RESUMES_DIR = REPO_ROOT / "materials" / "resumes"
TEMPLATE_PATH = RESUMES_DIR / "base" / "cover-letter-template.html"
BATCH_DIR = RESUMES_DIR / "batch-03"

# Identity position → credentials line
CREDENTIALS = {
    "systems-artist": "Systems Artist & Creative Technologist | MFA, Creative Writing | New York City",
    "creative-technologist": "Creative Technologist | MFA, Creative Writing | New York City",
    "independent-engineer": "Software Engineer | Full-Stack Developer (Meta) | New York City",
    "documentation-engineer": "Documentation Engineer | MFA, Creative Writing | New York City",
    "educator": "Educator & Learning Architect | MFA, Creative Writing | New York City",
    "platform-orchestrator": "Platform Engineer | Full-Stack Developer (Meta) | New York City",
    "governance-architect": "Governance & Compliance Architect | New York City",
    "founder-operator": "Founder & Operator | Full-Stack Developer (Meta) | New York City",
    "community-practitioner": "Community Practitioner | MFA, Creative Writing | New York City",
}

DEFAULT_CREDENTIALS = "Software Engineer & Systems Architect | MFA, Creative Writing | New York City"


def find_chrome() -> str:
    """Locate Chrome/Chromium binary."""
    candidates = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "google-chrome",
        "chromium",
    ]
    for c in candidates:
        p = Path(c)
        if p.exists():
            return str(p)
    # Try PATH
    for name in ["google-chrome", "chromium"]:
        try:
            result = subprocess.run(["which", name], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()
        except FileNotFoundError:
            pass
    print("ERROR: Chrome not found", file=sys.stderr)
    sys.exit(1)


def md_to_html_body(md_text: str) -> str:
    """Convert markdown cover letter text to HTML paragraphs.

    Handles: paragraphs, **bold**, *italic*, [links](url), numbered lists,
    ## headings, > blockquotes, --- horizontal rules.
    Does NOT use any external markdown library — pure regex.
    """
    lines = md_text.strip().split("\n")
    paragraphs = []
    current = []

    for line in lines:
        stripped = line.strip()
        if stripped == "":
            if current:
                paragraphs.append(" ".join(current))
                current = []
        else:
            current.append(stripped)
    if current:
        paragraphs.append(" ".join(current))

    html_parts = []
    in_sign_off = False
    for para in paragraphs:
        # Once we hit Sincerely, everything after is sign-off (template handles it)
        if para.startswith("Sincerely,") or para.startswith("Sincerely."):
            in_sign_off = True
            continue
        if in_sign_off:
            continue

        # Skip horizontal rules
        if re.match(r"^-{3,}$", para):
            continue

        # Convert markdown formatting
        text = para

        # Strip heading markers (## Title → Title)
        text = re.sub(r"^#{1,4}\s+", "", text)

        # Strip blockquote markers (> text → text)
        text = re.sub(r"^>\s*", "", text)

        # Links: [text](url) → text
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)

        # Bold: **text**
        text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
        # Italic: *text*
        text = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", text)

        # Numbered list items: keep the number as part of the paragraph
        # (cover letters use numbered lists as structured paragraphs, not HTML <ol>)
        html_parts.append(f"<p>{text}</p>")

    return "\n".join(html_parts)


def detect_identity_position(entry_dir: Path) -> str:
    """Try to detect identity position from the pipeline YAML."""
    entry_id = entry_dir.name
    # Check all pipeline directories
    for subdir in ["active", "submitted", "closed", "research_pool"]:
        yaml_path = REPO_ROOT / "pipeline" / subdir / f"{entry_id}.yaml"
        if yaml_path.exists():
            text = yaml_path.read_text()
            m = re.search(r"identity_position:\s*(.+)", text)
            if m:
                return m.group(1).strip().strip("'\"")
    return "independent-engineer"


def detect_title_line(entry_dir: Path) -> str:
    """Extract the title-line from the matching resume HTML to keep headers identical."""
    resume_html = list(entry_dir.glob("*-resume.html"))
    if resume_html:
        text = resume_html[0].read_text()
        m = re.search(r'class="title-line"[^>]*>([^<]+)<', text)
        if m:
            return m.group(1).strip()
    # Fallback: derive from identity position
    return ""


# Identity position → title-line fallback (matches resume title-line patterns)
TITLE_LINES = {
    "systems-artist": "Systems Artist & Creative Technologist",
    "creative-technologist": "Creative Technologist & Systems Builder",
    "independent-engineer": "Software Engineer & Systems Architect",
    "documentation-engineer": "Documentation Engineer & Systems Architect",
    "educator": "Educator & Learning Architect",
    "platform-orchestrator": "Platform Engineer & Systems Builder",
    "governance-architect": "Governance & Compliance Architect",
    "founder-operator": "Full-Stack Engineer & Systems Builder",
    "community-practitioner": "Community Practitioner & Creative Technologist",
}

DEFAULT_TITLE_LINE = "Software Engineer & Systems Architect"


def build_cover_letter(md_path: Path, chrome: str) -> tuple[bool, int]:
    """Convert a cover-letter.md to HTML and PDF. Returns (success, pages)."""
    entry_dir = md_path.parent
    entry_id = entry_dir.name

    # Read template
    template = TEMPLATE_PATH.read_text()

    # Read markdown
    md_text = md_path.read_text()

    # Convert to HTML body
    body_html = md_to_html_body(md_text)

    # Detect identity position for credentials
    position = detect_identity_position(entry_dir)
    credentials = CREDENTIALS.get(position, DEFAULT_CREDENTIALS)

    # Extract title-line from resume HTML (exact match) or fall back to position
    title_line = detect_title_line(entry_dir)
    if not title_line:
        title_line = TITLE_LINES.get(position, DEFAULT_TITLE_LINE)

    # Splice into template
    html = template.replace("{{BODY}}", body_html)
    html = html.replace("{{CREDENTIALS}}", credentials)
    html = html.replace("{{TITLE_LINE}}", title_line)
    html = html.replace(
        "<title>Anthony James Padavano — Cover Letter</title>",
        f"<title>Anthony James Padavano — Cover Letter — {entry_id}</title>",
    )

    # Write HTML
    html_path = entry_dir / f"{entry_id}-cover-letter.html"
    html_path.write_text(html)

    # Build PDF
    pdf_path = entry_dir / f"{entry_id}-cover-letter.pdf"
    file_url = f"file://{html_path}"
    for headless_flag in ["--headless=new", "--headless"]:
        cmd = [
            chrome,
            headless_flag,
            "--disable-gpu",
            "--no-sandbox",
            "--disable-software-rasterizer",
            "--no-pdf-header-footer",
            f"--print-to-pdf={pdf_path}",
            file_url,
        ]
        if pdf_path.exists():
            pdf_path.unlink()
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0 and pdf_path.exists() and pdf_path.stat().st_size > 0:
                # Count pages
                data = pdf_path.read_bytes()
                pages = len(re.findall(rb"/Type\s*/Page(?!s)", data))
                return True, pages
        except subprocess.TimeoutExpired:
            subprocess.run(["pkill", "-f", f"chrome.*{html_path.name}"], capture_output=True)
            continue
        except FileNotFoundError:
            break

    return False, 0


def main():
    parser = argparse.ArgumentParser(description="Build cover letter PDFs from markdown")
    parser.add_argument("--target", help="Single entry ID to build")
    parser.add_argument("--check", action="store_true", help="Check freshness only")
    args = parser.parse_args()

    # Find all cover-letter.md files
    if args.target:
        target_dir = BATCH_DIR / args.target
        md_files = list(target_dir.glob("cover-letter.md"))
        if not md_files:
            print(f"No cover-letter.md found in {target_dir}")
            sys.exit(1)
    else:
        md_files = sorted(BATCH_DIR.rglob("cover-letter.md"))

    if not md_files:
        print("No cover-letter.md files found in batch-03/.")
        sys.exit(0)

    print(f"Found {len(md_files)} cover letter(s).\n")

    if args.check:
        stale = 0
        for md_path in md_files:
            entry_id = md_path.parent.name
            pdf_path = md_path.parent / f"{entry_id}-cover-letter.pdf"
            if not pdf_path.exists():
                print(f"  MISSING  {entry_id}")
                stale += 1
            elif pdf_path.stat().st_mtime < md_path.stat().st_mtime:
                print(f"  STALE    {entry_id}")
                stale += 1
            else:
                print(f"  OK       {entry_id}")
        if stale:
            print(f"\n{stale} cover letter PDF(s) need rebuilding.")
        else:
            print(f"\nAll {len(md_files)} cover letter PDFs are up to date.")
        sys.exit(1 if stale else 0)

    chrome = find_chrome()
    built = 0
    warnings = 0

    for md_path in md_files:
        entry_id = md_path.parent.name
        print(f"  {entry_id}/cover-letter.md", end=" ... ")
        ok, pages = build_cover_letter(md_path, chrome)
        if ok:
            built += 1
            page_note = f"{pages} page{'s' if pages != 1 else ''}"
            if pages != 1:
                print(f"OK ({page_note}) WARNING: expected 1 page")
                warnings += 1
            else:
                print(f"OK ({page_note})")
        else:
            print("FAILED")

    print(f"\nBuilt {built}/{len(md_files)} cover letter PDFs.")
    if warnings:
        print(f"WARNING: {warnings} cover letter(s) are not exactly 1 page.")


if __name__ == "__main__":
    main()
