---
name: Validate every generated artifact before shipping
description: Post-generation validation gates prevent truncated resumes, wrong auto-fill, dead URLs, and broken links from reaching the user. Never ship AI-generated content without validation.
type: feedback
---

Every AI-generated artifact must pass validation BEFORE being presented to the user or written to disk.

**Why:** The 2026-03-28 session found that EVERY tailored resume had truncated sentences, EVERY portal answer had wrong auto-fills, EVERY outreach DM had broken profile links, and EVERY application URL was unchecked. The pipeline had zero post-generation validation. The user's trust eroded because defects kept shipping.

**How to apply:**
1. **Resumes:** Run `validate_sentence_completeness()` after `integrate_tailored_sections()` — flag truncation patterns (conjunctions/prepositions ending sentences)
2. **Portal answers:** After writing portal-answers.md, scan for blank required fields — print BLOCKER warning
3. **Auto-fill:** Never blanket-return "Yes" for unknown Yes/No questions. Positive qualifications → "Yes", negative → "No", unknown → "" (blank for human review)
4. **Application URLs:** HEAD request to `target.application_url` — warn if 404 (role may be closed)
5. **Cover letters:** Verify 1-page PDF after build. Check title-line and sign-off populated.
6. **Outreach contacts:** Check contacts.yaml interactions before listing as "fresh". Verify LinkedIn URLs resolve.
7. **Chrome PDFs:** Always absolute `file://` URLs + `--no-pdf-header-footer` + `--headless=new`

**The principle:** If the system generates it, the system validates it. Don't ship and hope.
