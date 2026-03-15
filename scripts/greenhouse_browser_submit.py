#!/usr/bin/env python3
"""Submit Greenhouse applications via browser automation (Playwright).

Handles the React SPA form at job-boards.greenhouse.io which cannot be
submitted via direct HTTP POST (requires JavaScript execution).

Usage:
    python scripts/greenhouse_browser_submit.py --target <entry-id>
    python scripts/greenhouse_browser_submit.py --target <entry-id> --dry-run
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import yaml
from pipeline_lib import PIPELINE_DIR_ACTIVE, REPO_ROOT


def load_config() -> dict:
    config_path = Path(__file__).resolve().parent / ".submit-config.yaml"
    if not config_path.exists():
        print(f"ERROR: {config_path} not found")
        sys.exit(1)
    return yaml.safe_load(config_path.read_text())


def load_entry(entry_id: str) -> dict:
    path = PIPELINE_DIR_ACTIVE / f"{entry_id}.yaml"
    if not path.exists():
        print(f"ERROR: {path} not found")
        sys.exit(1)
    return yaml.safe_load(path.read_text())


def load_answers(entry_id: str) -> dict:
    path = Path(__file__).resolve().parent / ".greenhouse-answers" / f"{entry_id}.yaml"
    if path.exists():
        return yaml.safe_load(path.read_text()) or {}
    return {}


def resolve_resume(entry: dict) -> Path | None:
    materials = entry.get("submission", {}).get("materials_attached", [])
    for m in materials:
        if "batch-03" in m and m.endswith(".pdf"):
            return REPO_ROOT / "materials" / m.replace(".html", ".pdf")
        if "batch-03" in m and m.endswith(".html"):
            pdf = m.replace(".html", ".pdf")
            return REPO_ROOT / "materials" / pdf
    return None


def resolve_cover_letter(entry: dict) -> str:
    variant = entry.get("submission", {}).get("variant_ids", {}).get("cover_letter", "")
    if variant:
        path = REPO_ROOT / "variants" / f"{variant}.md"
        if path.exists():
            return path.read_text().strip()
    return ""


def submit_greenhouse(entry_id: str, dry_run: bool = False):
    from playwright.sync_api import sync_playwright

    entry = load_entry(entry_id)
    config = load_config()
    answers = load_answers(entry_id)

    app_url = entry.get("target", {}).get("application_url", "")
    if not app_url:
        print(f"ERROR: No application_url for {entry_id}")
        return False

    resume_path = resolve_resume(entry)
    cover_letter = resolve_cover_letter(entry)

    print(f"{'[DRY RUN] ' if dry_run else ''}Submitting: {entry.get('name', entry_id)}")
    print(f"  URL: {app_url}")
    print(f"  Resume: {resume_path}")
    print(f"  Cover letter: {len(cover_letter)} chars")
    print(f"  Custom answers: {len(answers)} fields")

    if dry_run:
        print("\n  DRY RUN — would open browser and fill form. Use without --dry-run to submit.")
        return True

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=500)
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
        )
        page = context.new_page()

        print(f"\n  Navigating to {app_url}...")
        page.goto(app_url, wait_until="domcontentloaded", timeout=60000)
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass  # Some sites never reach networkidle — continue after DOM is loaded
        time.sleep(3)

        # Handle custom career pages — check if form fields exist, if not look for Apply button
        has_form = page.locator('input#first_name, input[id*="first_name"], input[name*="first_name"]').count() > 0
        if not has_form:
            print("  No application form found — looking for Apply button...")
            # Look for Apply links/buttons that lead to the Greenhouse form
            apply_selectors = [
                'a:has-text("Apply")',
                'button:has-text("Apply")',
                'a[href*="greenhouse"]',
                'a[href*="grnh"]',
            ]
            for sel in apply_selectors:
                loc = page.locator(sel)
                if loc.count() > 0:
                    href = loc.first.get_attribute("href") or ""
                    text = (loc.first.text_content() or "").strip()
                    if href and ("greenhouse" in href or "grnh" in href or "boards" in href):
                        print(f"  Found Apply link: {text} → {href}")
                        page.goto(href, wait_until="domcontentloaded", timeout=60000)
                        try:
                            page.wait_for_load_state("networkidle", timeout=15000)
                        except Exception:
                            pass
                        time.sleep(3)
                        break
                    elif not href or href == "#":
                        print(f"  Clicking Apply button: {text}")
                        loc.first.click()
                        time.sleep(3)
                        break

        # Scroll to form
        try:
            form = page.locator('form, [data-testid="application-form"], #application-form')
            if form.count() > 0:
                form.first.scroll_into_view_if_needed(timeout=5000)
                time.sleep(1)
        except Exception:
            pass

        page.screenshot(path=f"/tmp/greenhouse-{entry_id}-before.png", full_page=True)
        print(f"  Screenshot: /tmp/greenhouse-{entry_id}-before.png")

        # Dump all form fields for debugging
        all_inputs = page.locator('input, textarea, select').all()
        print(f"  Found {len(all_inputs)} form fields:")
        for inp in all_inputs:
            try:
                tag = inp.evaluate("el => el.tagName")
                name = inp.get_attribute("name") or ""
                itype = inp.get_attribute("type") or ""
                aid = inp.get_attribute("id") or ""
                label = inp.get_attribute("aria-label") or ""
                placeholder = inp.get_attribute("placeholder") or ""
                print(f"    <{tag}> name={name} type={itype} id={aid} label={label} placeholder={placeholder}")
            except Exception:
                pass

        # Fill standard fields — try multiple selector strategies
        field_map = {
            "first_name": config.get("first_name", ""),
            "last_name": config.get("last_name", ""),
            "email": config.get("email", ""),
            "phone": config.get("phone", ""),
        }
        for field_key, value in field_map.items():
            try:
                selectors = [
                    f'input[name*="{field_key}"]',
                    f'input[id*="{field_key}"]',
                    f'input[aria-label*="{field_key.replace("_", " ")}"]',
                    f'input[autocomplete="{field_key.replace("_", "-")}"]',
                ]
                filled = False
                for sel in selectors:
                    loc = page.locator(sel)
                    if loc.count() > 0:
                        loc.first.fill(value)
                        print(f"  Filled: {field_key} (via {sel})")
                        filled = True
                        break
                if not filled:
                    # Try label-based approach
                    label_text = field_key.replace("_", " ").title()
                    label_loc = page.locator(f'label:has-text("{label_text}")')
                    if label_loc.count() > 0:
                        for_id = label_loc.first.get_attribute("for")
                        if for_id:
                            page.locator(f"#{for_id}").fill(value)
                            print(f"  Filled: {field_key} (via label)")
                            filled = True
                if not filled:
                    print(f"  SKIP: Could not find field for {field_key}")
            except Exception as e:
                print(f"  Warning filling {field_key}: {e}")

        # Upload resume
        if resume_path and resume_path.exists():
            try:
                file_inputs = page.locator('input[type="file"]').all()
                if file_inputs:
                    file_inputs[0].set_input_files(str(resume_path))
                    print(f"  Uploaded resume: {resume_path.name}")
                    time.sleep(2)
                else:
                    # Try clicking an upload button
                    upload_btn = page.locator('button:has-text("Attach"), button:has-text("Upload"), button:has-text("Choose")')
                    if upload_btn.count() > 0:
                        with page.expect_file_chooser() as fc_info:
                            upload_btn.first.click()
                        fc = fc_info.value
                        fc.set_files(str(resume_path))
                        print(f"  Uploaded resume via chooser: {resume_path.name}")
                        time.sleep(2)
            except Exception as e:
                print(f"  Warning uploading resume: {e}")

        # Upload cover letter as file (Greenhouse uses file input, not textarea)
        if cover_letter:
            try:
                # Write cover letter to temp .txt file for upload
                cl_path = Path(f"/tmp/{entry_id}-cover-letter.txt")
                cl_path.write_text(cover_letter)

                cl_input = page.locator('input[type="file"][id="cover_letter"], input[type="file"][id*="cover_letter"]')
                if cl_input.count() > 0:
                    cl_input.first.set_input_files(str(cl_path))
                    print(f"  Uploaded cover letter: {cl_path.name} ({len(cover_letter)} chars)")
                    time.sleep(1)
                else:
                    # Fallback: second file input (first is resume)
                    file_inputs = page.locator('input[type="file"]').all()
                    if len(file_inputs) >= 2:
                        file_inputs[1].set_input_files(str(cl_path))
                        print(f"  Uploaded cover letter via 2nd file input ({len(cover_letter)} chars)")
                        time.sleep(1)
                    else:
                        print("  WARNING: Could not find cover letter upload field")
            except Exception as e:
                print(f"  Warning uploading cover letter: {e}")

        # Fill website/LinkedIn fields
        try:
            website = page.locator('#question_11532807007, input[aria-label="Website"]')
            if website.count() > 0:
                website.first.fill("https://4444j99.github.io/portfolio/")
                print("  Filled: website")
        except Exception:
            pass
        try:
            linkedin = page.locator('#question_11532808007, input[aria-label="LinkedIn Profile"]')
            if linkedin.count() > 0:
                linkedin.first.fill("https://www.linkedin.com/in/anthonyjamespadavano")
                print("  Filled: linkedin")
        except Exception:
            pass

        # Fill custom question answers
        for field_id, value in answers.items():
            if field_id.startswith("#") or field_id.startswith("_"):
                continue
            if isinstance(value, list):
                continue  # Skip multi-select for now
            try:
                filled = False
                for sel in [
                    f'input[name*="{field_id}"]',
                    f'textarea[name*="{field_id}"]',
                    f'select[name*="{field_id}"]',
                    f'input[id*="{field_id}"]',
                    f'textarea[id*="{field_id}"]',
                    f'select[id*="{field_id}"]',
                ]:
                    loc = page.locator(sel)
                    if loc.count() > 0:
                        tag = loc.first.evaluate("el => el.tagName.toLowerCase()")
                        if tag == "select":
                            loc.first.select_option(str(value))
                        else:
                            loc.first.fill(str(value).strip())
                        print(f"  Filled: {field_id}")
                        filled = True
                        break
                if not filled:
                    print(f"  SKIP: Could not find {field_id}")
            except Exception as e:
                print(f"  Warning filling {field_id}: {e}")

        # Screenshot after filling
        time.sleep(1)
        page.screenshot(path=f"/tmp/greenhouse-{entry_id}-filled.png", full_page=True)
        print(f"  Screenshot: /tmp/greenhouse-{entry_id}-filled.png")

        # Scroll submit button into view
        submit_btn = page.locator('button[type="submit"], button:has-text("Submit Application"), button:has-text("Submit"), button:has-text("Apply")')
        if submit_btn.count() > 0:
            submit_btn.first.scroll_into_view_if_needed()

        print("\n  ✓ Form filled. Solve the reCAPTCHA and click Submit in the browser.")
        print("  Waiting for confirmation page (up to 5 minutes)...")

        # Wait for the user to solve CAPTCHA and submit
        try:
            page.wait_for_url("**/confirmation**", timeout=300000)
            page.screenshot(path=f"/tmp/greenhouse-{entry_id}-confirmed.png", full_page=True)
            print(f"\n  SUCCESS — Application submitted for {entry.get('name', entry_id)}!")
            print(f"  Confirmation screenshot: /tmp/greenhouse-{entry_id}-confirmed.png")
            browser.close()
            return True
        except Exception:
            current_url = page.url
            content = page.content()
            if "confirmation" in current_url.lower() or "thank" in content.lower():
                print("\n  SUCCESS — Application submitted!")
                browser.close()
                return True
            else:
                print("\n  TIMED OUT — No confirmation detected.")
                print(f"  Current URL: {current_url}")
                page.screenshot(path=f"/tmp/greenhouse-{entry_id}-timeout.png", full_page=True)
                browser.close()
                return False


def main():
    parser = argparse.ArgumentParser(description="Submit Greenhouse applications via browser automation")
    parser.add_argument("--target", required=True, help="Pipeline entry ID")
    parser.add_argument("--dry-run", action="store_true", help="Preview without submitting")
    args = parser.parse_args()

    success = submit_greenhouse(args.target, dry_run=args.dry_run)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
