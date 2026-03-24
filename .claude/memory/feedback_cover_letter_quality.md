---
name: Cover letter quality — location, format, length, factual errors
description: Cover letter standards: NYC location, markdown source + resume-styled PDF, full 1-page length (550-700 words), no MCP misattribution, no apologizing, current metrics.
type: feedback
---

Cover letter quality rules (updated 2026-03-20):

1. **Location:** New York City. Never "South Florida" or "Miami" — stale data from old resume.

2. **Format (dual output):** Cover letters are authored in **markdown** (`cover-letter.md`) and also built to **resume-styled PDF** via `build_cover_letters.py`. The HTML template matches the resume visual identity (Georgia font, centered header, 1.5pt border). Run `python scripts/run.py coverletters` to build all.

3. **Length:** Must fill a full page — target **550-700 words**, 4-5 substantial paragraphs. Previous 350-450 word target was too short (half a page).

4. **MCP is Anthropic's protocol**, not OpenAI's. Never attribute Anthropic products to other companies.

5. **Never apologize for gaps.** Lead with what you bring, not what you lack.

6. **No commas in role titles** — use "&" or parentheses.

7. **Metrics must be current:** 113 repos, 104 CI/CD, 23,470 tests, 739K words, 82K files, 22 languages, 50 dependency edges.

**Why:** These errors would get applications rejected or signal carelessness.

**How to apply:** Before any cover letter is finalized, verify: correct location, dual format (md + PDF), full page length, no attribution errors, no apologetic framing, current metrics. Build PDFs with `python scripts/build_cover_letters.py`.
