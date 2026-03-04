# Plan: Fix Over-Trimmed Resumes + Add Content Length Template

## Context

8 batch-03 resumes were trimmed to fit 1 page but the trimming was too aggressive — content fills only ~75% of the page, leaving ~25% blank space at the bottom. The `build_resumes.py --check` reports "1 page" (technically correct) but the resumes look sparse compared to properly-filled ones.

**Root cause:** The trimming agent both removed a project entry AND shortened all descriptions. Should have done one or the other.

**Evidence:** Good resume (`temporal-technical-writer`) = ~11.2KB HTML. Trimmed resumes = ~9.9KB. Base template = ~10.7KB. The trimmed ones lost ~1.3KB of content.

## Part 1: Fix the 8 Over-Trimmed Resumes

### Target Density (Gold Standard: `temporal-technical-writer`)

| Section | Target Length |
|---------|-------------|
| Profile | 5-6 lines (~350-450 chars visible text) |
| Projects | 5 entries, each 2-3 line descriptions |
| Experience bullets | Each wraps to 2 lines |
| Total HTML | ~10.5-11.2KB |
| Page fill | ~95-98% |

### Files to Fix

All in `materials/resumes/batch-03/<id>/<id>-resume.html`:

1. `temporal-staff-developer-advocate-platform-engineering`
2. `temporal-staff-developer-advocate-developer-enablement`
3. `stripe-developer-experience-engineer-privy`
4. `resend-dx-engineer-technical-writer`
5. `gitlab-staff-backend-engineer-developer-experience-ruby`
6. `anthropic-developer-community-lead-emea`
7. `mongodb-senior-technical-writer`
8. `temporal-staff-developer-advocate-emea`

### Fix per file

1. **Restore 5th project** — add back the removed project (Application Pipeline or Classroom RPG Aetheria) with a 2-3 line description
2. **Expand profile** — add back the "Specialist in..." and "Focused on..." sentences (~2 more lines)
3. **Expand project descriptions** — restore second sentence per project to reach 2-3 lines each
4. **Expand experience bullets** — ensure each wraps to 2 lines with restored detail

### Build + Verify

```bash
# Delete old PDFs
rm -f materials/resumes/batch-03/{temporal-staff-developer-advocate-platform-engineering,temporal-staff-developer-advocate-developer-enablement,stripe-developer-experience-engineer-privy,resend-dx-engineer-technical-writer,gitlab-staff-backend-engineer-developer-experience-ruby,anthropic-developer-community-lead-emea,mongodb-senior-technical-writer,temporal-staff-developer-advocate-emea}/*.pdf

# Rebuild
python scripts/build_resumes.py

# Check
python scripts/build_resumes.py --check 2>&1 | grep batch-03
```

Visually verify 2-3 PDFs fill the page.

## Part 2: Add Content Length Guidelines to `tailor_resume.py`

### Change Location

`scripts/tailor_resume.py` → `build_tailoring_prompt()` function (line 171)

### What to Add

Add explicit content length targets to the prompt instructions (lines 187-195). These will be read by the AI when generating tailored sections:

```python
"## Content Length Targets (CRITICAL — resume must fill exactly 1 page)",
"",
"The final resume MUST fill 95-98% of a single 8.5x11 page at 8.4pt Georgia.",
"Content that is too short looks sparse; too long overflows to 2 pages.",
"",
"- **TITLE_LINE**: 4-8 words (e.g. 'STAFF DEVELOPER ADVOCATE (PLATFORM ENGINEERING)')",
"- **PROFILE**: One paragraph, 5-6 lines (~350-450 characters). Include: role framing, key metrics (103 repos, 2349+ tests, 94 CI/CD), methodology note, credentials, identity.",
"- **SKILLS**: 20-25 skills, single line wrapping to 2-3 lines",
"- **PROJECTS**: Exactly 5 project entries. Each entry: bold title line + 2-3 line description (~150-200 chars). Total section ~800-1000 chars.",
"- **EXPERIENCE**: 4 entries. First entry (Independent Engineer): 4 bullets, each wrapping to 2 lines (~120-150 chars each). Other 3 entries: 1 bullet each wrapping to 2 lines.",
"",
"If in doubt, write MORE rather than less — it's easier to trim a 2-page resume to 1 than to fill a sparse page.",
```

### Files Modified

| File | Change |
|------|--------|
| 8 HTML files in `materials/resumes/batch-03/` | Restore content density |
| `scripts/tailor_resume.py` | Add content length targets to prompt (lines ~187-195) |

## Verification

1. All 8 PDFs show "OK (1 page)" via `build_resumes.py --check`
2. Visual check of 2-3 rebuilt PDFs confirms ~95%+ page fill
3. `ruff check scripts/tailor_resume.py` passes
4. Run `python scripts/tailor_resume.py --target temporal-technical-writer` (dry-run prompt generation) to confirm new guidelines appear in the prompt output
