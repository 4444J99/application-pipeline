#!/usr/bin/env python3
"""Build PDF resumes from HTML sources using headless Chrome.

Finds all *-resume.html files in materials/resumes/ and converts each
to PDF via headless Chrome with no margins and no header/footer.

Usage:
    python scripts/build_resumes.py
    python scripts/build_resumes.py --check   # Verify PDFs are up to date

If headless Chrome hangs (common on macOS Tahoe beta), open each HTML
file in Chrome manually and use Print → Save as PDF with no margins.
"""

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RESUMES_DIR = REPO_ROOT / "materials" / "resumes"

# Chrome paths to try (macOS)
CHROME_PATHS = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary",
]


def find_chrome() -> str | None:
    """Find a working Chrome/Chromium binary."""
    for path in CHROME_PATHS:
        if Path(path).exists():
            return path
    # Try PATH
    try:
        result = subprocess.run(
            ["which", "google-chrome"], capture_output=True, text=True
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except FileNotFoundError:
        pass
    return None


def build_pdf(chrome: str, html_path: Path, pdf_path: Path) -> bool:
    """Convert an HTML file to PDF using headless Chrome."""
    file_url = f"file://{html_path}"
    # Try --headless=new first (Chrome 112+), fall back to --headless
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
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30
            )
            if pdf_path.exists() and pdf_path.stat().st_size > 0:
                return True
        except subprocess.TimeoutExpired:
            # Kill any orphaned Chrome processes from the timeout
            subprocess.run(
                ["pkill", "-f", f"chrome.*{html_path.name}"],
                capture_output=True,
            )
            continue
        except FileNotFoundError:
            break

    print(f"  ERROR: Chrome PDF generation failed", file=sys.stderr)
    return False


def run_check() -> int:
    """Check that all HTML resumes have corresponding up-to-date PDFs."""
    html_files = sorted(RESUMES_DIR.glob("*-resume.html"))
    if not html_files:
        print("No resume HTML files found.")
        return 1

    stale = 0
    for html_path in html_files:
        pdf_path = html_path.with_suffix(".pdf")
        name = html_path.name
        if not pdf_path.exists():
            print(f"  MISSING  {name} -> {pdf_path.name}")
            stale += 1
        elif pdf_path.stat().st_mtime < html_path.stat().st_mtime:
            print(f"  STALE    {name} -> {pdf_path.name}")
            stale += 1
        else:
            print(f"  OK       {name} -> {pdf_path.name}")

    if stale:
        print(f"\n{stale} PDF(s) need rebuilding. Run: python scripts/build_resumes.py")
        print("Or open each HTML in Chrome and Print -> Save as PDF (no margins, no header/footer)")
        return 1
    print(f"\nAll {len(html_files)} PDFs are up to date.")
    return 0


def run_list():
    """List all resume HTML files and their PDF status."""
    html_files = sorted(RESUMES_DIR.glob("*-resume.html"))
    if not html_files:
        print("No resume HTML files found.")
        return

    print(f"Resume HTML files in {RESUMES_DIR}:\n")
    for html_path in html_files:
        pdf_path = html_path.with_suffix(".pdf")
        status = "PDF exists" if pdf_path.exists() else "NO PDF"
        print(f"  {html_path.name}  [{status}]")


def main():
    parser = argparse.ArgumentParser(
        description="Build PDF resumes from HTML sources using headless Chrome"
    )
    parser.add_argument(
        "--check", action="store_true",
        help="Check that PDFs are up to date (don't build)"
    )
    parser.add_argument(
        "--list", action="store_true",
        help="List all resume HTML files"
    )
    args = parser.parse_args()

    if args.list:
        run_list()
        return

    if args.check:
        sys.exit(run_check())

    chrome = find_chrome()
    if not chrome:
        print(
            "ERROR: Chrome/Chromium not found.\n"
            "Install Google Chrome, or open each HTML file manually and\n"
            "use Print -> Save as PDF (no margins, no header/footer).",
            file=sys.stderr,
        )
        run_list()
        sys.exit(1)

    print(f"Using: {chrome}")

    html_files = sorted(RESUMES_DIR.glob("*-resume.html"))
    if not html_files:
        print("No resume HTML files found in materials/resumes/")
        sys.exit(1)

    print(f"Found {len(html_files)} HTML resume(s)\n")

    success = 0
    failed = 0
    for html_path in html_files:
        pdf_path = html_path.with_suffix(".pdf")
        print(f"  {html_path.name} -> {pdf_path.name} ...", end=" ")
        if build_pdf(chrome, html_path, pdf_path):
            size_kb = pdf_path.stat().st_size / 1024
            print(f"OK ({size_kb:.0f} KB)")
            success += 1
        else:
            print("FAILED")
            failed += 1

    print(f"\nBuilt {success}/{success + failed} PDFs.")
    if failed:
        print("\nFor failed PDFs: open the HTML in Chrome and use Print -> Save as PDF")
        print("  Settings: no margins, no header/footer, save to materials/resumes/")
        sys.exit(1)


if __name__ == "__main__":
    main()
