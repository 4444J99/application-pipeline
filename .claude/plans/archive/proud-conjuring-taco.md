# Submit 16 Staged Job Applications

## Context

16 job entries are `staged` with all materials ready (tailored resumes, cover letters, custom question answers). The goal is to submit them with minimal manual UI interaction.

## What's Available (ranked by automation)

### Option 1: Direct API — `greenhouse_submit.py --submit` / `ashby_submit.py --submit`
- **Both scripts already exist** and handle multipart form POST with resume upload + custom answers
- **Auth is optional** — headers only added if API keys are configured (they aren't)
- **Blocker: reCAPTCHA** — Both portals embed invisible reCAPTCHA. The web forms generate a token that the server validates. A raw HTTP POST without a valid reCAPTCHA token will likely be rejected (422 or silent failure).
- **Verdict**: Worth a quick test on one entry. If Greenhouse's Job Board API doesn't enforce reCAPTCHA server-side, this is zero-UI for 6 Greenhouse + 8 Ashby entries.

### Option 2: Chrome MCP — I fill your browser directly
- `mcp__claude-in-chrome__*` tools are available: `navigate`, `form_input`, `find`, `read_page`, `javascript_tool`
- **Currently NOT connected** — extension needs to be active in Chrome
- If connected: I navigate to each form, fill fields via `form_input`, upload files via JS, you handle reCAPTCHA and click submit
- **Verdict**: Best option if you connect the extension. I do the work, you supervise.

### Option 3: Playwright script — `browser_submit.py` (already built)
- Script already exists from previous session — 400 lines, handles Greenhouse/Ashby/Workable/Custom
- You run `python scripts/browser_submit.py --batch`, watch headed Chromium, press Enter after reviewing each form
- **Verdict**: Works but requires running a separate process and monitoring it.

## Portal Breakdown

| Portal | Count | Entries |
|--------|-------|---------|
| Greenhouse | 6 | anthropic-fde, cloudflare, figma, runway-mts, stripe, together-ai |
| Ashby | 8 | cohere, cursor, notion, openai-dx, openai-fde-nyc, perplexity, replit, supabase |
| Workable | 1 | huggingface |
| Custom | 1 | openai-se-evals |

## Recommended Plan: Tiered Approach

### Step 1: Test direct API on one Greenhouse entry
```bash
python scripts/greenhouse_submit.py --target together-ai --submit
```
If this returns 200/201 → API works, batch all 6 Greenhouse entries via API (zero UI).
If it fails (reCAPTCHA/422/403) → move to Step 2.

### Step 2: Test direct API on one Ashby entry
```bash
python scripts/ashby_submit.py --target cohere-applied-ai --submit
```
Same logic — if it works, batch all 8 Ashby. If blocked, move to Step 3.

### Step 3: For any portal where API fails — use browser automation
**Option A (Chrome MCP)**: Connect the Chrome extension, then I fill forms from this conversation using `navigate` → `find` → `form_input` per entry. You review and submit.

**Option B (Playwright)**: Run the existing script:
```bash
python scripts/browser_submit.py --batch --portal greenhouse   # 6 entries
python scripts/browser_submit.py --batch --portal ashby        # 8 entries
python scripts/browser_submit.py --target huggingface-dev-advocate  # Workable
python scripts/browser_submit.py --target openai-se-evals          # Custom/manual
```

### Step 4: Record successful submissions
For API submissions, add `--record` flag or call `record_submission()` after.
For browser submissions, the script calls `record_submission()` automatically.

### Step 5: Verify
```bash
python scripts/pipeline_status.py        # entries moved to submitted/
python scripts/velocity.py --update-signals
pytest tests/ -v                          # no regressions
```

## Key Files

| File | Role |
|------|------|
| `scripts/greenhouse_submit.py` | Greenhouse API submit (already exists) |
| `scripts/ashby_submit.py` | Ashby API submit (already exists) |
| `scripts/browser_submit.py` | Playwright browser automation (already exists) |
| `scripts/submit.py` | `record_submission()` function |
| `scripts/.submit-config.yaml` | Personal info (name, email, phone) |
| `scripts/.greenhouse-answers/*.yaml` | 6 Greenhouse answer files (all exist) |
| `scripts/.ashby-answers/` | Ashby answer templates (empty — API returned 403 for schema fetch; Ashby forms have no custom fields) |
