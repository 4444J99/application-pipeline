# Plan: Fix Autonomous Submission Pipeline

## Context

The pipeline has 35 active job entries (23 Greenhouse, 12 Ashby) that can theoretically be submitted via API from the terminal — no browser needed. However, submissions are failing because:

1. `resolve_resume()` only finds `.pdf` files in `materials_attached`, but most entries only reference `.html` sources
2. `lever_submit.py` has a syntax bug (orphaned `return None` on line 115)
3. There's no email submission script for the 25 "custom" portal entries (grants/residencies)
4. No unified batch dry-run to diagnose all blockers at once

## Changes

### 1. Fix `resolve_resume()` to auto-discover PDFs (pipeline_lib.py:716-728)

**Problem:** `materials_attached` lists `.html` files, but `resolve_resume()` only returns `.pdf`. The PDFs exist on disk in the same directory but aren't referenced.

**Fix:** If no PDF is found in `materials_attached`, look for a sibling `.pdf` next to any `.html` resume reference in the list. This is a 5-line fallback — no schema changes needed.

```python
# After the existing loop, add fallback:
for m in materials:
    mat_path = MATERIALS_DIR / m
    if mat_path.suffix.lower() == ".html":
        pdf_sibling = mat_path.with_suffix(".pdf")
        if pdf_sibling.exists():
            return pdf_sibling
return None
```

### 2. Fix `lever_submit.py` syntax bug (line 115)

**Problem:** Orphaned `return None` on line 115, sitting between a comment and the next section header. Leftover from a deleted function.

**Fix:** Delete lines 113-115 (the comment + stray return). The imports are already handled at the top of the file.

### 3. Build `email_submit.py` — email-based submission for grants/residencies

**New file:** `scripts/email_submit.py`

Follows the exact same CLI pattern as `greenhouse_submit.py`:
- `--target <id>` / `--batch` for scope
- Default dry-run with preview, `--submit` to actually send
- `--record` to update pipeline YAML after sending
- Uses `smtplib.SMTP_SSL` with Gmail App Password from `.submit-config.yaml`

**Config addition to `.submit-config.yaml`:**
```yaml
smtp:
  server: smtp.gmail.com
  port: 465
  email: padavano.anthony@gmail.com
  app_password: "..."  # Gmail App Password (not account password)
```

**Email composition:**
- Subject from entry YAML field `submission.email_subject` (or auto-generate from entry name)
- Body from `resolve_cover_letter(entry)` (or `submission.email_body` override)
- Attachments: resume PDF via `resolve_resume(entry)`, plus any other files in `materials_attached`
- Recipient from `target.application_url` if it's a `mailto:` link, or `target.email`

**Scope:** Only processes entries with `portal: custom` or `portal: email` that have a target email address.

### 4. Build `submission_audit.py` — batch readiness diagnostic

**New file:** `scripts/submission_audit.py`

Single command that checks every active entry with an API-submittable portal and reports:

| Check | What it verifies |
|-------|-----------------|
| Portal parsed | URL matches Greenhouse/Ashby/Lever/email pattern |
| Resume PDF exists | `resolve_resume()` returns a path |
| Cover letter exists | `resolve_cover_letter()` returns content |
| Status submittable | Not already submitted/acknowledged/interview/outcome |
| Answer file exists | For Greenhouse: `.greenhouse-answers/<id>.yaml` present |
| Answer validation | Required custom questions all answered |

Output: grouped by portal, with pass/fail for each check, and a summary of how many are submission-ready.

**Quick command:** `python scripts/run.py audit`

### 5. Wire `audit` into `run.py`

Add `audit` to the quick command table, mapping to `submission_audit.py`.

## Files Modified

| File | Change |
|------|--------|
| `scripts/pipeline_lib.py` | Fix `resolve_resume()` PDF fallback (lines 716-728) |
| `scripts/lever_submit.py` | Delete orphaned `return None` (lines 113-115) |
| `scripts/email_submit.py` | **New** — email submission script |
| `scripts/submission_audit.py` | **New** — batch readiness diagnostic |
| `scripts/run.py` | Add `audit` quick command |

## Verification

1. `python -c "import sys; sys.path.insert(0,'scripts'); from lever_submit import main; print('OK')"` — no syntax error
2. `python scripts/submission_audit.py` — run audit, verify output shows pass/fail for each entry
3. `python scripts/greenhouse_submit.py --target anthropic-software-engineer-agent-sdk-claude-code` — dry-run should now find the PDF
4. `python scripts/email_submit.py --batch` — dry-run preview of all email-submittable entries
5. `pytest tests/ -v -x` — existing tests still pass
