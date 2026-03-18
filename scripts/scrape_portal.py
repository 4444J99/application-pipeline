#!/usr/bin/env python3
"""Scrape application portal form fields and generate answer templates.

Navigates to the application URL, extracts form labels and field types,
and writes a portal-answers.md template to the applications/ directory.

Usage:
    python scripts/scrape_portal.py --target <entry-id>
    python scripts/scrape_portal.py --target <entry-id> --output answers.md
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import PIPELINE_DIR_ACTIVE


def scrape_form_fields(url: str) -> list[dict]:
    """Navigate to a URL and extract all form field labels and types.

    Returns list of {label, field_id, field_type, required} dicts.
    """
    from playwright.sync_api import sync_playwright

    fields = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        time.sleep(5)

        # Click Apply button if present
        apply = page.locator('button:has-text("Apply"), a:has-text("Apply")')
        if apply.count() > 0:
            try:
                apply.first.click()
                time.sleep(3)
            except Exception:
                pass

        # Extract labels and their associated fields
        labels = page.locator("label").all()
        for label in labels:
            try:
                text = (label.text_content() or "").strip()
                if not text or len(text) < 3:
                    continue

                for_id = label.get_attribute("for") or ""

                # Skip EEOC/demographic fields
                if any(s in for_id.lower() for s in ["eeoc", "gender", "race", "veteran", "disability"]):
                    continue
                if any(s in text.lower() for s in ["gender", "race", "veteran", "disability", "hispanic"]):
                    continue

                # Find the associated input
                field_type = "text"
                required = False
                if for_id:
                    inp = page.locator(f"#{for_id}")
                    if inp.count() > 0:
                        tag = inp.first.evaluate("el => el.tagName.toLowerCase()")
                        field_type = tag
                        if tag == "input":
                            field_type = inp.first.get_attribute("type") or "text"
                        required = inp.first.get_attribute("required") is not None

                # Skip system fields we auto-fill
                if text.lower() in ("name", "email", "resume"):
                    continue

                fields.append({
                    "label": text,
                    "field_id": for_id,
                    "field_type": field_type,
                    "required": required,
                })
            except Exception:
                continue

        browser.close()

    return fields


def generate_answer_template(entry: dict, fields: list[dict]) -> str:
    """Generate a markdown answer template from scraped fields."""
    org = entry.get("target", {}).get("organization", "Unknown")
    name = entry.get("name", "Unknown Role")

    lines = [f"# {org} — {name} — Portal Answers", ""]

    for field in fields:
        req = " (required)" if field["required"] else ""
        lines.append(f"## {field['label']}{req}")
        if field["field_type"] == "textarea":
            lines.append("")
            lines.append("[Your answer here — 2-4 sentences]")
        else:
            lines.append("")
            lines.append("[Answer]")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Scrape portal form fields and generate answer template")
    parser.add_argument("--target", required=True, help="Pipeline entry ID")
    parser.add_argument("--output", "-o", help="Output file (default: applications dir)")
    args = parser.parse_args()

    # Load entry
    filepath = PIPELINE_DIR_ACTIVE / f"{args.target}.yaml"
    if not filepath.exists():
        print(f"ERROR: {filepath} not found")
        sys.exit(1)

    entry = yaml.safe_load(filepath.read_text())
    url = entry.get("target", {}).get("application_url", "")
    if not url:
        print(f"ERROR: No application_url for {args.target}")
        sys.exit(1)

    print(f"Scraping: {url}")
    fields = scrape_form_fields(url)

    if not fields:
        print("No custom form fields found.")
        sys.exit(0)

    print(f"Found {len(fields)} custom fields:")
    for f in fields:
        req = "*" if f["required"] else " "
        print(f"  [{req}] {f['label'][:60]} ({f['field_type']})")

    template = generate_answer_template(entry, fields)

    if args.output:
        output_path = Path(args.output)
    else:
        output_path = filepath.parent / f"{args.target}-portal-answers.md"

    output_path.write_text(template)
    print(f"\nTemplate written to: {output_path}")


if __name__ == "__main__":
    sys.exit(main() or 0)
