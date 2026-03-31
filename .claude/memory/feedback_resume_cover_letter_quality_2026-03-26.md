---
name: Resume and cover letter quality — COMPLETE rules (original + amendments)
description: ALL rules for resume and cover letter production. Original rules from 2026-03-20 PLUS amendments from 2026-03-26. Rules are ADDITIVE — new rules never replace old ones.
type: feedback
---

**PRINCIPLE: Rules are ADDITIVE. New rules AMEND, never overwrite. Every rule ever established remains in force unless explicitly revoked by the user.**

## ORIGINAL RULES (from feedback_cover_letter_quality.md, 2026-03-20)

### Cover Letter Standards
1. **Location:** New York City. Never "South Florida" or "Miami."
2. **Format (dual output):** Cover letters authored in markdown (`cover-letter.md`) AND built to resume-styled PDF via `build_cover_letters.py`. The HTML template matches the resume visual identity.
3. **Length:** Must fill a full page — **550-700 words**, 4-5 substantial paragraphs. 300-400 words is HALF A PAGE and unacceptable.
4. **MCP is Anthropic's protocol**, not OpenAI's.
5. **Never apologize for gaps.** Lead with what you bring.
6. **No commas in role titles** — use "&" or parentheses.
7. **Metrics must be current:** 113 repos, 104 CI/CD, 23,470 tests, 739K words, 82K files, 50 dependency edges (from CANONICAL dict in recruiter_filter.py).

### Resume Standards (from feedback_base_not_output.md)
8. **Fix BASE templates, never patch outputs.** When a structural change is needed, modify the 9 base templates in `materials/resumes/base/`. The tailoring system propagates changes on the next `tailor_resume.py` run. NEVER touch batch-NN files for systemic fixes.
9. **Resume must fill exactly 1 page** — 95-98% fill. Not half, not overflowing.
10. **4 experience entries minimum:** ORGANVM (2020–Present), Instructor (2015–Present), Digital Marketing Manager (2023–2024), Multimedia Specialist (2011–2020). These show 18 years of career breadth.
11. **Vertical stacked layout** for experience entries — full-width bullets. NEVER columnar/grid layout. Columns create dead space and make entries look thin.

## AMENDMENTS (2026-03-26)

### A1. "Independent Engineer" is DEAD — use ORGANVM
The title "Independent Engineer" must NEVER appear on any resume or cover letter. ORGANVM is the employer name. "Software Engineer & [role-specific title]" at ORGANVM.

### A2. Cover letter visual parity with resume
Same header (name centered, contact info, border), same font family (Georgia), same page dimensions. Built via `build_cover_letters.py` which has the matching template. The `apply.py` bare `<p>` wrapper is NOT acceptable — use the proper template at `materials/resumes/base/cover-letter-template.html`.

### A3. Project diversity — rotate per role
Include 15-20 projects in the tailor prompt organized by domain. Select 5 most relevant per role. The default 5 (ORGANVM System, agentic-titan, agent--claude-smith, Application Pipeline, Portfolio) are FALLBACK only. Domain-specific rotation:
- DevRel: essays, portfolio, teaching tools
- AI/ML: agentic-titan, IRA facility, multi-model evaluation
- Platform: CI/CD infrastructure, LaunchAgents, registry governance
- Arts: generative art, Metasystem Master, p5.js
- Financial Services: governance, audit trails, state machine

## AMENDMENTS (2026-03-28)

### A4. Cover letter template is the single source of truth
**`materials/resumes/base/cover-letter-template.html`** is the ONE template for all cover letters. Both `apply.py` and `build_cover_letters.py` consume it. Template placeholders: `{{BODY}}`, `{{TITLE_LINE}}`, `{{CREDENTIALS}}`. Never use `{{LETTER_BODY}}` or `{{NAME}}` — those are dead placeholders.

### A5. Cover letter rendering specifications
- **Font:** Georgia serif, 9.5pt body, line-height 1.42 (fits 550-700 words on 1 page)
- **Header:** Name (16pt italic) + title-line (9.5pt uppercase, letter-spacing 2pt) + contact (8pt). Must match resume header structure.
- **Title-line:** Pulled from batch-03 resume HTML if available, else derived from identity position via `TITLE_LINES` dict.
- **Sign-off:** "Sincerely," + bold name + credentials line (from identity position via `CREDENTIALS` dict). Template handles this — never include sign-off in markdown body.
- **Paragraph spacing:** 9pt margin-bottom, justified text, auto-hyphens.
- **Page fill:** Flexbox column layout with `min-height: 10.1in`, letter-body `flex: 1`.
- **Contact format:** `New York City | 561-602-7300 | padavano.anthony@gmail.com` (pipes, not dots).

### A6. Chrome headless PDF build rules
- **Always use absolute file:// URLs.** `file_url = f"file://{html_path.resolve()}"`. Relative paths cause ERR_INVALID_URL.
- **Always use `--no-pdf-header-footer`** flag (NOT `--print-to-pdf-no-header` which is deprecated).
- **Try `--headless=new` first**, fall back to `--headless` for older Chrome versions.
- **Verify page count after build.** Cover letters must be exactly 1 page. 2+ pages means font/spacing needs tightening.

### A7. Identity position flows into cover letter
`apply.py` reads `fit.identity_position` (or `submission.identity_position`) from the entry YAML and uses it to populate:
1. Title-line in header (if no resume HTML match found)
2. Credentials line in sign-off
3. Both keyed from the same `TITLE_LINES` / `CREDENTIALS` dicts that `build_cover_letters.py` uses

### A8. Markdown body filtering
When converting cover-letter.md → HTML body:
- Skip lines starting with: "Anthony Padavano", "Anthony James Padavano", "New York, NY", "New York City", "padavano.anthony@gmail.com"
- Stop at "Sincerely," (template handles sign-off)
- Blank-line-separated paragraphs (join continuation lines within paragraphs)
- Convert `**bold**` → `<strong>`, `*italic*` → `<em>`, strip markdown links

## ENFORCEMENT

All rules must be checked AUTOMATICALLY by `apply.py` before declaring READY:
- [ ] Cover letter word count >= 550 (RED FLAG if < 500)
- [ ] No "Independent Engineer" in any generated file
- [ ] Cover letter built via base template (not bare HTML or inline styles)
- [ ] Cover letter has title-line matching identity position
- [ ] Cover letter has sign-off with credentials
- [ ] Resume has >= 4 experience entries
- [ ] Resume is exactly 1 page
- [ ] Cover letter is exactly 1 page (verified by PDF page count)
- [ ] PDF has no browser headers/footers (--no-pdf-header-footer)
- [ ] Projects are not the same 5 defaults (check against a blocklist)
- [ ] Metrics match CANONICAL dict
- [ ] Employer is ORGANVM, not "Independent" or "Self-Employed"
- [ ] Experience entries are vertical/stacked, not columnar
