#!/usr/bin/env python3
"""Browser automation for submitting job applications via Playwright.

Fills and submits web forms on Greenhouse, Ashby, Workable, and custom portals
using headed Chromium. Pauses before submit by default for human review.

Usage:
    python scripts/browser_submit.py --target <id>                    # Single entry
    python scripts/browser_submit.py --batch                          # All staged jobs
    python scripts/browser_submit.py --batch --portal greenhouse      # Just Greenhouse
    python scripts/browser_submit.py --batch --portal ashby           # Just Ashby
    python scripts/browser_submit.py --target <id> --auto-submit      # Skip review pause
    python scripts/browser_submit.py --target <id> --headless         # Headless mode
    python scripts/browser_submit.py --init-answers --portal ashby    # Generate Ashby answer templates
"""

import argparse
import sys
import time
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import (
    MATERIALS_DIR, PIPELINE_DIR_ACTIVE, VARIANTS_DIR,
    load_entries, load_entry_by_id,
    strip_markdown,
)

# Reuse URL parsers and material resolvers from existing submit modules
from greenhouse_submit import (
    parse_greenhouse_url,
    resolve_cover_letter as gh_resolve_cover_letter,
    resolve_resume as gh_resolve_resume,
    load_answers as gh_load_answers,
    load_config,
)
from ashby_submit import (
    parse_ashby_url,
    resolve_cover_letter as ashby_resolve_cover_letter,
    resolve_resume as ashby_resolve_resume,
    load_answers as ashby_load_answers,
    fetch_form_schema,
    get_custom_fields,
)

# Import record_submission from submit.py
from submit import record_submission

SCRIPTS_DIR = Path(__file__).resolve().parent
ASHBY_ANSWERS_DIR = SCRIPTS_DIR / ".ashby-answers"
GREENHOUSE_ANSWERS_DIR = SCRIPTS_DIR / ".greenhouse-answers"

DELAY_BETWEEN_SUBMISSIONS = 4  # seconds


# ---------------------------------------------------------------------------
# Greenhouse form handler
# ---------------------------------------------------------------------------


def greenhouse_fill(page, entry, config, answers):
    """Fill a Greenhouse hosted application form.

    Navigates to the job page, reveals the form, fills personal info,
    uploads resume, fills cover letter, and answers custom questions.
    """
    entry_id = entry.get("id", "?")
    target = entry.get("target", {})
    app_url = target.get("application_url", "")

    print(f"  Navigating to {app_url}")
    page.goto(app_url, wait_until="networkidle")
    page.wait_for_timeout(2000)

    # Click "Apply" button if present (various label patterns)
    apply_btn = page.locator(
        'a:has-text("Apply for this Job"), button:has-text("Apply for this Job"), '
        'a:has-text("Apply"), button:has-text("Apply")'
    )
    if apply_btn.count() > 0:
        print("  Clicking 'Apply'...")
        apply_btn.first.click()
        page.wait_for_timeout(3000)

    # Wait for the application form to appear
    try:
        page.wait_for_selector("#first_name, form, #application_form", timeout=10000)
    except Exception:
        print("  WARNING: Form did not appear within 10s")

    # --- Personal info ---
    _safe_fill(page, '#first_name', config["first_name"])
    _safe_fill(page, '#last_name', config["last_name"])
    _safe_fill(page, '#email', config["email"])
    phone = config.get("phone", "")
    if phone:
        _safe_fill(page, '#phone', phone)

    # --- Resume upload (by #resume ID) ---
    resume_path = gh_resolve_resume(entry)
    if resume_path:
        print(f"  Uploading resume: {resume_path.name}")
        resume_input = page.locator('#resume, input[type="file"]')
        if resume_input.count() > 0:
            resume_input.first.set_input_files(str(resume_path))
            page.wait_for_timeout(1500)
        else:
            print("  WARNING: No file input found for resume upload")
    else:
        print(f"  WARNING: No resume PDF found for {entry_id}")

    # --- Cover letter ---
    cover_letter_text = gh_resolve_cover_letter(entry)
    if cover_letter_text:
        cl_filled = False
        # Strategy 1: textarea field
        cl_selectors = [
            '#cover_letter_text',
            'textarea[name="cover_letter_text"]',
            'textarea[id*="cover_letter"]',
        ]
        for sel in cl_selectors:
            if page.locator(sel).count() > 0:
                page.locator(sel).first.fill(cover_letter_text)
                cl_filled = True
                print(f"  Filled cover letter textarea ({len(cover_letter_text)} chars)")
                break
        # Strategy 2: file upload — save text as temp .txt and upload
        if not cl_filled:
            cl_input = page.locator('#cover_letter')
            if cl_input.count() > 0:
                import tempfile
                tmp = Path(tempfile.mkdtemp()) / f"{entry_id}-cover-letter.txt"
                tmp.write_text(cover_letter_text)
                cl_input.first.set_input_files(str(tmp))
                cl_filled = True
                print(f"  Uploaded cover letter as file ({len(cover_letter_text)} chars)")
                page.wait_for_timeout(1000)
        if not cl_filled:
            print("  Cover letter: no field found, skipping (fill manually)")

    # --- Custom question answers ---
    if answers:
        print(f"  Filling {len(answers)} custom question answers...")
        for field_name, answer in answers.items():
            _fill_greenhouse_question(page, field_name, str(answer))

    print(f"  Greenhouse form filled for {entry_id}")


def _fill_greenhouse_multi_select(page, field_name, answer):
    """Fill a Greenhouse multi-select checkbox field (name ends with [])."""
    base_name = field_name[:-2]
    checkboxes = page.locator(f'input[name="{field_name}"], input[name="{base_name}[]"]')
    if checkboxes.count() > 0:
        for i in range(checkboxes.count()):
            cb = checkboxes.nth(i)
            label_text = cb.evaluate(
                """el => {
                    const label = el.closest('label') || document.querySelector('label[for="' + el.id + '"]');
                    return label ? label.textContent.trim() : '';
                }"""
            )
            if answer.lower() in label_text.lower():
                if not cb.is_checked():
                    cb.check()
                return


def _fill_greenhouse_question(page, field_name, answer):
    """Fill a single Greenhouse custom question field."""
    if not answer or answer == "FILL IN":
        return

    # Handle multi-select checkboxes first (field_name ends with [])
    if field_name.endswith("[]"):
        _fill_greenhouse_multi_select(page, field_name, answer)
        return

    # Try by ID using attribute selector (safe for any ID format)
    el = page.locator(f'[id="{field_name}"]')
    if el.count() > 0:
        tag = el.first.evaluate("el => el.tagName.toLowerCase()")
        if tag == "select":
            try:
                el.first.select_option(label=answer)
            except Exception:
                try:
                    el.first.select_option(value=answer)
                except Exception:
                    print(f"    WARNING: Could not select '{answer}' for {field_name}")
        elif tag in ("input", "textarea"):
            el.first.fill(answer)
        return

    # Try by name attribute
    el = page.locator(f'[name="{field_name}"]')
    if el.count() > 0:
        tag = el.first.evaluate("el => el.tagName.toLowerCase()")
        if tag == "select":
            try:
                el.first.select_option(label=answer)
            except Exception:
                try:
                    el.first.select_option(value=answer)
                except Exception:
                    pass
        else:
            el.first.fill(answer)
        return
    if field_name.endswith("[]"):
        base_name = field_name[:-2]
        checkboxes = page.locator(f'input[name="{field_name}"], input[name="{base_name}[]"]')
        if checkboxes.count() > 0:
            # Click the checkbox whose label matches
            for i in range(checkboxes.count()):
                cb = checkboxes.nth(i)
                label = cb.evaluate(
                    """el => {
                        const label = el.closest('label') || document.querySelector(`label[for="${el.id}"]`);
                        return label ? label.textContent.trim() : '';
                    }"""
                )
                if answer.lower() in label.lower():
                    if not cb.is_checked():
                        cb.check()
                    return


# ---------------------------------------------------------------------------
# Ashby form handler
# ---------------------------------------------------------------------------


def ashby_fill(page, entry, config, answers):
    """Fill an Ashby hosted application form.

    Ashby forms are React SPAs — need to click "Apply for this Job" first,
    then wait for React to render the form fields. Each field fill uses
    try/except for resilience against React component quirks.
    """
    entry_id = entry.get("id", "?")
    target = entry.get("target", {})
    app_url = target.get("application_url", "")

    print(f"  Navigating to {app_url}")
    page.goto(app_url, wait_until="networkidle")
    page.wait_for_timeout(2000)

    # Click "Apply for this Job" button (required to reveal the form)
    apply_btn = page.locator(
        'button:has-text("Apply for this Job"), a:has-text("Apply for this Job"), '
        'button:has-text("Apply"), a:has-text("Apply")'
    )
    if apply_btn.count() > 0:
        print("  Clicking 'Apply for this Job'...")
        apply_btn.first.click()
        page.wait_for_timeout(3000)

    # Wait for form fields to render (labels, not <form> tag)
    try:
        page.wait_for_selector(
            'label[for="_systemfield_name"], label:has-text("Name")',
            timeout=10000,
        )
    except Exception:
        print("  WARNING: Form fields did not render within 10s")

    # --- Location FIRST (autocomplete triggers React re-render) ---
    location = config.get("location", "")
    if location:
        _fill_location_autocomplete(page, location)
        page.wait_for_timeout(1000)

    # --- Personal info AFTER location (survives re-render) ---
    full_name = f"{config['first_name']} {config['last_name']}"

    _react_fill(page, '_systemfield_name', full_name)
    _react_fill(page, '_systemfield_email', config["email"])

    # Phone — may have a custom ID, try by label
    phone = config.get("phone", "")
    if phone:
        _fill_by_label_safe(page, "Phone", phone)

    # LinkedIn — fill from config if field exists
    linkedin = config.get("linkedin", "")
    if linkedin:
        _fill_by_label_safe(page, "LinkedIn", linkedin)

    page.wait_for_timeout(500)

    # --- Resume upload ---
    resume_path = ashby_resolve_resume(entry)
    if resume_path:
        print(f"  Uploading resume: {resume_path.name}")
        resume_uploaded = False
        try:
            file_inputs = page.locator('input[type="file"]')
            count = file_inputs.count()
            if count > 1:
                # Last file input is typically resume (first is autofill)
                file_inputs.nth(count - 1).set_input_files(str(resume_path))
                resume_uploaded = True
            elif count == 1:
                file_inputs.first.set_input_files(str(resume_path))
                resume_uploaded = True
        except Exception as e:
            print(f"  WARNING: Resume upload error: {e}")
        if resume_uploaded:
            page.wait_for_timeout(1500)
            print(f"  Resume uploaded")
        else:
            print("  WARNING: No file input found for resume upload")
    else:
        print(f"  WARNING: No resume PDF found for {entry_id}")

    # --- Cover letter ---
    cover_letter_text = ashby_resolve_cover_letter(entry)
    if cover_letter_text:
        cl_filled = _fill_by_label_safe(page, "Cover Letter", cover_letter_text)
        if not cl_filled:
            cl_filled = _fill_by_label_safe(page, "Cover letter", cover_letter_text)
        if cl_filled:
            print(f"  Filled cover letter ({len(cover_letter_text)} chars)")

    # --- Custom field answers ---
    if answers:
        print(f"  Filling {len(answers)} custom field answers...")
        for field_path, answer in answers.items():
            _fill_ashby_field(page, field_path, str(answer))

    # Also try to fill any visible custom fields by label matching
    _fill_ashby_custom_by_label(page, config, entry)

    print(f"  Ashby form filled for {entry_id}")


def _fill_by_label(page, label_text, value):
    """Find an input by its label text and fill it. Returns True if filled."""
    # Strategy 1: label with for attribute
    labels = page.locator(f'label:has-text("{label_text}")')
    for i in range(labels.count()):
        label = labels.nth(i)
        # Check if label text is a close match (not just substring)
        actual_text = label.inner_text().strip()
        if label_text.lower() not in actual_text.lower():
            continue
        for_attr = label.get_attribute("for")
        if for_attr:
            # Use attribute selector to handle UUIDs/numeric-start IDs
            target_input = page.locator(f'[id="{for_attr}"]')
            if target_input.count() > 0:
                target_input.first.fill(value)
                return True
        # Strategy 2: input inside the label
        inner_input = label.locator('input, textarea')
        if inner_input.count() > 0:
            inner_input.first.fill(value)
            return True
        # Strategy 3: next sibling input
        parent = label.locator('..')
        sibling_input = parent.locator('input, textarea')
        if sibling_input.count() > 0:
            sibling_input.first.fill(value)
            return True

    # Strategy 4: aria-label
    aria_input = page.locator(f'input[aria-label*="{label_text}" i], textarea[aria-label*="{label_text}" i]')
    if aria_input.count() > 0:
        aria_input.first.fill(value)
        return True

    # Strategy 5: placeholder
    ph_input = page.locator(f'input[placeholder*="{label_text}" i], textarea[placeholder*="{label_text}" i]')
    if ph_input.count() > 0:
        ph_input.first.fill(value)
        return True

    return False


def _fill_ashby_custom_by_label(page, config, entry):
    """Auto-fill common Ashby custom fields by label pattern matching."""
    location = config.get("location", "")
    linkedin = config.get("linkedin", "")

    labels = page.locator('label')
    for i in range(labels.count()):
        label = labels.nth(i)
        text = label.inner_text().strip().lower()
        for_attr = label.get_attribute("for") or ""
        # Skip standard system fields (already filled)
        if for_attr.startswith("_systemfield"):
            continue
        target = page.locator(f'[id="{for_attr}"]') if for_attr else None
        if not target or target.count() == 0:
            continue
        # Auto-fill patterns
        if ("where" in text and "located" in text) or "location" in text:
            if location:
                try:
                    target.first.fill(location)
                except Exception:
                    pass
        elif "linkedin" in text:
            if linkedin:
                try:
                    target.first.fill(linkedin)
                except Exception:
                    pass


def _fill_ashby_field(page, field_path, answer):
    """Fill a single Ashby custom field by its path identifier."""
    if not answer or answer == "FILL IN":
        return

    # Try by name attribute (Ashby sometimes uses path as name)
    el = page.locator(f'[name="{field_path}"]')
    if el.count() > 0:
        tag = el.first.evaluate("el => el.tagName.toLowerCase()")
        if tag == "select":
            try:
                el.first.select_option(label=answer)
            except Exception:
                pass
        else:
            el.first.fill(answer)
        return

    # Try by data-path
    el = page.locator(f'[data-path="{field_path}"]')
    if el.count() > 0:
        inner = el.locator('input, textarea, select')
        if inner.count() > 0:
            tag = inner.first.evaluate("el => el.tagName.toLowerCase()")
            if tag == "select":
                try:
                    inner.first.select_option(label=answer)
                except Exception:
                    pass
            else:
                inner.first.fill(answer)
        return

    # Try by id
    el = page.locator(f'#{field_path}')
    if el.count() > 0:
        el.first.fill(answer)


# ---------------------------------------------------------------------------
# Workable form handler
# ---------------------------------------------------------------------------


def workable_fill(page, entry, config):
    """Navigate to a Workable portal. Manual fallback — just opens the page."""
    app_url = entry.get("target", {}).get("application_url", "")
    entry_id = entry.get("id", "?")

    print(f"  Navigating to {app_url}")
    page.goto(app_url, wait_until="domcontentloaded")
    page.wait_for_timeout(2000)
    print(f"  Workable portal opened for {entry_id}")
    print(f"  NOTE: Workable forms vary — fill manually in the browser")


# ---------------------------------------------------------------------------
# Manual fallback
# ---------------------------------------------------------------------------


def manual_fallback(page, entry):
    """Open the application URL and pause for manual submission."""
    app_url = entry.get("target", {}).get("application_url", "")
    entry_id = entry.get("id", "?")

    print(f"  Navigating to {app_url}")
    page.goto(app_url, wait_until="domcontentloaded")
    page.wait_for_timeout(2000)
    print(f"  Custom portal opened for {entry_id}")
    print(f"  NOTE: Fill and submit manually in the browser")


# ---------------------------------------------------------------------------
# Ashby --init-answers via browser
# ---------------------------------------------------------------------------


def init_ashby_answers_browser(page, entry, config):
    """Navigate to an Ashby form, extract fields, and generate answer YAML."""
    entry_id = entry.get("id", "?")
    name = entry.get("name", entry_id)
    app_url = entry.get("target", {}).get("application_url", "")

    parsed = parse_ashby_url(app_url)
    if not parsed:
        print(f"  Error: Cannot parse Ashby URL for {entry_id}: {app_url}")
        return False
    company, posting_id = parsed

    answer_path = ASHBY_ANSWERS_DIR / f"{entry_id}.yaml"
    if answer_path.exists():
        print(f"  {entry_id}: Answer file already exists, skipping")
        return False

    # Use API to fetch form schema (faster than browser scraping)
    print(f"  Fetching form schema for {entry_id} ({company}/{posting_id})...")
    fields = fetch_form_schema(posting_id)
    custom_fields = get_custom_fields(fields)

    if not custom_fields:
        print(f"  {entry_id}: No custom fields found")
        return True

    # Build auto-fill answers
    submission = entry.get("submission", {}) or {}
    portfolio_url = submission.get("portfolio_url", "") if isinstance(submission, dict) else ""
    source_map = {
        "portfolio_url": portfolio_url,
        "linkedin": config.get("linkedin", ""),
        "name_pronunciation": config.get("name_pronunciation", ""),
        "pronouns": config.get("pronouns", ""),
        "location": config.get("location", ""),
    }

    from ashby_submit import AUTO_FILL_PATTERNS as ASHBY_AUTO_FILL

    auto_filled = {}
    for field in custom_fields:
        title = field.get("title", "")
        path = field.get("path", "")
        for pattern, source_key in ASHBY_AUTO_FILL:
            if pattern.search(title):
                value = source_map.get(source_key, "")
                if value:
                    auto_filled[path] = value
                break

    # Generate template
    lines = [
        f"# Generated for: {name}",
        f"# Posting: {company}/{posting_id}",
        f"# Edit answers below, then run with --check-answers to validate",
        "",
    ]

    for field in custom_fields:
        title = field.get("title", "?")
        path = field.get("path", "")
        required = field.get("isRequired", False)
        ftype = field.get("type", "unknown")
        type_map = {"String": "text", "LongText": "textarea", "ValueSelect": "select",
                     "MultiValueSelect": "multi-select", "Boolean": "boolean"}
        ftype_label = type_map.get(ftype, ftype)
        select_values = field.get("selectableValues", [])

        comment_parts = [f"# {title}"]
        type_str = f"# Type: {ftype_label}"
        if select_values:
            opts = ", ".join(v.get("label", "?") for v in select_values)
            type_str += f" | Options: {opts}"
        type_str += f" | {'Required' if required else 'Optional'}"
        comment_parts.append(type_str)
        lines.extend(comment_parts)

        if path in auto_filled:
            lines.append(f'{path}: "{auto_filled[path]}"')
        elif ftype_label == "textarea":
            lines.append(f"{path}: |")
            lines.append("  FILL IN")
        else:
            lines.append(f'{path}: "FILL IN"')
        lines.append("")

    ASHBY_ANSWERS_DIR.mkdir(parents=True, exist_ok=True)
    answer_path.write_text("\n".join(lines))

    auto_count = len(auto_filled)
    manual_count = len(custom_fields) - auto_count
    print(f"  {entry_id}: Wrote {answer_path.name}")
    print(f"    {len(custom_fields)} custom fields: {auto_count} auto-filled, {manual_count} need manual answers")
    return True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _safe_fill(page, selector, value):
    """Fill a field if it exists, silently skip if not."""
    el = page.locator(selector)
    if el.count() > 0:
        el.first.fill(value)


def _react_fill(page, element_id, value):
    """Fill a React controlled input by ID using native event dispatch.

    React controlled components may ignore Playwright's .fill() because
    they manage state internally. This function uses JS to set the value
    and dispatch React-compatible events.
    """
    el = page.locator(f'[id="{element_id}"]')
    if el.count() == 0:
        return False
    try:
        # Use Playwright's fill (dispatches input/change events)
        el.first.fill(value)
        page.wait_for_timeout(100)
        # Also dispatch events via JS as backup for React 18+
        page.evaluate("""({id, val}) => {
            const el = document.getElementById(id);
            if (!el) return;
            const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                window.HTMLInputElement.prototype, 'value'
            ).set;
            nativeInputValueSetter.call(el, val);
            el.dispatchEvent(new Event('input', {bubbles: true}));
            el.dispatchEvent(new Event('change', {bubbles: true}));
        }""", {"id": element_id, "val": value})
        page.wait_for_timeout(100)
        return True
    except Exception:
        return False


def _fill_by_label_safe(page, label_text, value):
    """Wrapper around _fill_by_label that catches exceptions."""
    try:
        return _fill_by_label(page, label_text, value)
    except Exception:
        return False


def _fill_location_autocomplete(page, location):
    """Handle Ashby's location autocomplete field.

    Ashby's location field is a custom React autocomplete — the <input>
    has no type attribute and no ID. Identified by 'input:not([type])' or
    placeholder='Start typing...'. We type the location to trigger the
    autocomplete dropdown, then select the best match.
    """
    try:
        # Primary: input with no type attribute (Ashby's location autocomplete)
        loc_input = page.locator('input:not([type])')
        if loc_input.count() == 0:
            # Fallback: find via label DOM traversal
            loc_input = page.locator('input[placeholder="Start typing..."]')
        if loc_input.count() == 0:
            print("  NOTE: Location autocomplete input not found")
            return

        loc_input.first.click(timeout=5000)
        page.wait_for_timeout(300)
        loc_input.first.fill("")
        page.wait_for_timeout(200)
        # Type to trigger autocomplete dropdown
        loc_input.first.press_sequentially(location, delay=60)
        page.wait_for_timeout(2000)

        # Look for autocomplete dropdown options
        options = page.locator('[role="option"], [role="listbox"] li, [class*="option"]:visible')
        if options.count() > 0:
            # Click the best matching option
            city = location.lower().split(",")[0].strip()
            for i in range(min(options.count(), 10)):
                text = options.nth(i).inner_text().strip()
                if city in text.lower():
                    options.nth(i).click()
                    page.wait_for_timeout(500)
                    return
            # No exact match, click first option
            options.first.click()
            page.wait_for_timeout(500)
        else:
            # No dropdown — try Tab to accept typed value
            loc_input.first.press("Tab")
            page.wait_for_timeout(300)
    except Exception as e:
        print(f"  NOTE: Location field may need manual entry ({e})")


def find_staged_job_entries(portal_filter=None):
    """Find all staged job entries, optionally filtered by portal type."""
    entries = load_entries(dirs=[PIPELINE_DIR_ACTIVE], include_filepath=True)
    results = []
    for e in entries:
        if e.get("status") != "staged":
            continue
        if e.get("track") != "job":
            continue
        if portal_filter:
            portal = e.get("target", {}).get("portal", "")
            if portal != portal_filter:
                continue
        results.append(e)
    return results


def resolve_portal(entry):
    """Get the portal type for an entry."""
    return entry.get("target", {}).get("portal", "custom")


def wait_for_review(page, entry_id):
    """Pause execution and wait for user to review the form in the browser."""
    print()
    print(f"  >>> REVIEW: {entry_id}")
    print(f"  >>> The form is filled. Review it in the browser.")
    print(f"  >>> Press Enter here to submit, or type 'skip' to skip this entry.")
    print()
    try:
        response = input("  >>> ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\n  Aborted.")
        return "abort"
    if response == "skip":
        return "skip"
    return "submit"


def click_submit(page, portal):
    """Attempt to click the submit button on the form."""
    submit_selectors = [
        'button[type="submit"]',
        'input[type="submit"]',
        'button:has-text("Submit")',
        'button:has-text("Submit Application")',
        'button:has-text("Submit application")',
        'button:has-text("Apply")',
        'button:has-text("Send Application")',
    ]
    for sel in submit_selectors:
        btn = page.locator(sel)
        if btn.count() > 0 and btn.first.is_visible():
            print(f"  Clicking submit button...")
            btn.first.click()
            return True
    print("  WARNING: Could not find submit button — submit manually in the browser")
    return False


def wait_for_confirmation(page, timeout=10000):
    """Wait for a submission confirmation signal."""
    # Look for common success indicators
    success_selectors = [
        'text="Thank you"',
        'text="Application submitted"',
        'text="application has been submitted"',
        'text="application has been received"',
        'text="successfully submitted"',
        'text="We have received your application"',
        'text="Success"',
        '[class*="success"]',
        '[class*="confirmation"]',
    ]
    for sel in success_selectors:
        try:
            page.wait_for_selector(sel, timeout=timeout)
            return True
        except Exception:
            continue
    return False


# ---------------------------------------------------------------------------
# Main processing
# ---------------------------------------------------------------------------


def process_entry_browser(page, entry, config, auto_submit=False):
    """Process a single entry: fill form, review, submit, record.

    Returns: "submitted", "skipped", "failed", or "aborted"
    """
    entry_id = entry.get("id", "?")
    name = entry.get("name", entry_id)
    portal = resolve_portal(entry)
    filepath = entry.get("_filepath")

    print(f"\n{'=' * 60}")
    print(f"PROCESSING: {name}")
    print(f"  Portal: {portal} | ID: {entry_id}")
    print(f"{'=' * 60}")

    # Load answers based on portal type
    answers = {}
    if portal == "greenhouse":
        answers = gh_load_answers(entry_id) or {}
    elif portal == "ashby":
        answers = ashby_load_answers(entry_id) or {}

    # Dispatch to portal handler
    try:
        if portal == "greenhouse":
            greenhouse_fill(page, entry, config, answers)
        elif portal == "ashby":
            ashby_fill(page, entry, config, answers)
        elif portal == "workable":
            workable_fill(page, entry, config)
        else:
            manual_fallback(page, entry)
    except Exception as e:
        print(f"  ERROR filling form: {e}")
        print(f"  The browser is still open — fill manually if needed.")
        # Don't return failed yet, let user still review

    # Review step
    if not auto_submit:
        action = wait_for_review(page, entry_id)
        if action == "abort":
            return "aborted"
        if action == "skip":
            print(f"  Skipped: {entry_id}")
            return "skipped"

    # Submit
    submitted = click_submit(page, portal)
    if submitted:
        page.wait_for_timeout(3000)
        confirmed = wait_for_confirmation(page, timeout=8000)
        if confirmed:
            print(f"  Submission confirmed for {entry_id}")
        else:
            print(f"  No confirmation detected — check the browser to verify")

    # Record submission
    if filepath and Path(filepath).exists():
        try:
            record_submission(Path(filepath), entry)
            print(f"  Recorded submission for {entry_id}")
        except Exception as e:
            print(f"  WARNING: Could not record submission: {e}")
            print(f"  Run manually: python scripts/submit.py --target {entry_id} --record")
    else:
        print(f"  WARNING: No filepath for entry — record manually")
        print(f"  Run: python scripts/submit.py --target {entry_id} --record")

    return "submitted"


def main():
    parser = argparse.ArgumentParser(
        description="Browser automation for submitting job applications"
    )
    parser.add_argument("--target", help="Target entry ID")
    parser.add_argument("--batch", action="store_true",
                        help="Process all staged job entries")
    parser.add_argument("--portal", choices=["greenhouse", "ashby", "workable", "custom"],
                        help="Filter by portal type (with --batch)")
    parser.add_argument("--auto-submit", action="store_true",
                        help="Skip review pause before submit")
    parser.add_argument("--headless", action="store_true",
                        help="Run in headless mode (default: headed)")
    parser.add_argument("--init-answers", action="store_true",
                        help="Generate Ashby answer templates via API")
    args = parser.parse_args()

    if not args.target and not args.batch:
        parser.error("Specify --target <id> or --batch")

    config = load_config()

    # Resolve entries
    if args.batch:
        entries = find_staged_job_entries(portal_filter=args.portal)
        if not entries:
            portal_note = f" with portal={args.portal}" if args.portal else ""
            print(f"No staged job entries found{portal_note}.")
            sys.exit(1)
    else:
        filepath, entry = load_entry_by_id(args.target)
        if not entry:
            print(f"Error: No pipeline entry found for '{args.target}'", file=sys.stderr)
            sys.exit(1)
        entry["_filepath"] = filepath
        entries = [entry]

    # --init-answers mode (Ashby only, uses API not browser)
    if args.init_answers:
        ashby_entries = [e for e in entries if e.get("target", {}).get("portal") == "ashby"]
        if not ashby_entries:
            print("No Ashby entries found for --init-answers.")
            sys.exit(1)
        print(f"Generating Ashby answer templates for {len(ashby_entries)} entry(ies)...\n")
        results = []
        for entry in ashby_entries:
            ok = init_ashby_answers_browser(None, entry, config)
            results.append((entry.get("id"), ok))
        generated = sum(1 for _, ok in results if ok)
        print(f"\nSummary: {generated}/{len(results)} generated")
        return

    # Launch Playwright browser
    from playwright.sync_api import sync_playwright

    print(f"\nLaunching browser ({'headless' if args.headless else 'headed'})...")
    print(f"Entries to process: {len(entries)}")
    for e in entries:
        portal = resolve_portal(e)
        print(f"  - {e.get('id')} ({portal})")
    print()

    with sync_playwright() as p:
        # Use persistent context for cookie/reCAPTCHA trust accumulation
        user_data_dir = SCRIPTS_DIR / ".browser-profile"
        user_data_dir.mkdir(exist_ok=True)

        browser = p.chromium.launch_persistent_context(
            str(user_data_dir),
            headless=args.headless,
            viewport={"width": 1280, "height": 900},
            locale="en-US",
        )

        page = browser.new_page()
        results = []

        for i, entry in enumerate(entries):
            result = process_entry_browser(
                page, entry, config, auto_submit=args.auto_submit,
            )
            results.append((entry.get("id"), result))

            if result == "aborted":
                print("\nAborted by user.")
                break

            # Delay between submissions
            if i < len(entries) - 1 and result == "submitted":
                print(f"\n  Waiting {DELAY_BETWEEN_SUBMISSIONS}s before next entry...")
                time.sleep(DELAY_BETWEEN_SUBMISSIONS)

        browser.close()

    # Summary
    print(f"\n{'=' * 60}")
    print("BATCH SUMMARY:")
    print(f"{'=' * 60}")
    submitted = 0
    skipped = 0
    failed = 0
    for eid, result in results:
        icon = {"submitted": "+", "skipped": "-", "failed": "!", "aborted": "X"}.get(result, "?")
        print(f"  [{icon}] {eid}: {result}")
        if result == "submitted":
            submitted += 1
        elif result == "skipped":
            skipped += 1
        elif result == "failed":
            failed += 1

    print(f"\n  {submitted} submitted, {skipped} skipped, {failed} failed")


if __name__ == "__main__":
    main()
