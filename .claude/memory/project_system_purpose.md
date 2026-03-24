---
name: system_purpose
description: Core purpose of the application pipeline — daily job scanning, skill matching, material generation, application, and outreach
type: project
---

The application pipeline's core mission is a daily automated cycle:
**Scan → Match → Build → Apply → Follow up**

1. Scan jobs from ATS APIs (Greenhouse, Lever, Ashby) and free job boards daily
2. Score/match against the user's skill corpus (blocks, profiles, identity positions)
3. Generate fortified application materials (resumes, cover letters, answers) from the block composition model
4. Apply through portal-specific submitters
5. Reach out via outreach templates and follow-up protocols

**Why:** Everything else in the system (scoring rubric, external validation, calibration, mode switching, citation quality, IRA grade-norming, diagnostics) exists to fortify and ensure the integrity of that core cycle.

**How to apply:** When making architectural decisions, always ask "does this serve the scan→match→build→apply→followup loop?" If it doesn't directly strengthen that cycle, it's secondary.
