---
name: Resume and cover letter quality — identity, format, and project diversity
description: Three recurring failures that must be caught automatically. Independent Engineer is DEAD. Cover letters must match resume formatting. Projects must rotate — never the same 5 repos.
type: feedback
---

Three failures identified 2026-03-26 that keep recurring. These are NOT suggestions — they are hard rules.

## 1. "Independent Engineer" is DEAD — use ORGANVM

The title "Independent Engineer" must NEVER appear on any resume or cover letter. The role attribution is to ORGANVM — the system's name, the studio's name. "Independent Engineer" makes the user look unemployed. ORGANVM makes them look like they run something.

**Why:** User said "makes me look like a goddamn clown." The identity reframe happened 2026-03-15 (see project_identity_reframe_2026-03-15.md). Documentation Engineer was identified as the lead position. The system has 9 identity positions — "Independent Engineer" is one of them but it should NEVER be the default. ORGANVM is the employer name, not "Independent" or "Self-Employed."

**How to apply:**
- `tailor_resume.py`: the experience section must say "ORGANVM" as the employer, not "Independent Engineer"
- `apply.py`: validate that no generated material contains "Independent Engineer" as a title or role
- Resume EXPERIENCE section: "Software Engineer & [role-specific title]" at ORGANVM, not "Independent Engineer"
- Add as a recruiter_filter.py RED FLAG check

## 2. Cover letter format must match resume format

Cover letters must have the SAME header/footer styling as the resume — same font, same layout, same visual identity. Currently the cover letter HTML template is a bare `<p>` wrapper while the resume has a proper styled template. They look like they came from two different people.

**Why:** User said "the cover letter doesn't follow the same format as the resume, it has garbage on the header and footer." A hiring manager receives both PDFs — they must look like one package.

**How to apply:**
- `build_cover_letters.py` or the HTML generation in `apply.py`: use the same CSS template as `build_resumes.py`
- Header: Name, location, contact info — same layout as resume
- No "Dear Hiring Team" garbage formatting — clean, professional, matching
- Audit: if resume PDF exists, cover letter PDF must use the same template

## 3. Project diversity — rotate, don't repeat the same 5

The resume keeps showcasing the same 5 projects (ORGANVM Eight-Organ System, agentic-titan, agent--claude-smith, Application Pipeline, Portfolio). There are 113+ repositories. The resume should highlight projects RELEVANT to the specific role, not the same generic 5.

**Why:** User said "are there not some more options to showcase what ORGANVM does other than the same goddamn 5 repos." The system has repos covering: generative art, modular synthesis, recursive engines, data pipelines, governance frameworks, community platforms, editorial systems, CLI tools, MCP servers, and more.

**How to apply:**
- `tailor_resume.py`: when generating resume prompts, include a LARGER menu of projects (15-20) organized by domain relevance, not just the default 5
- For DevRel roles: showcase essays, portfolio, teaching tools
- For AI/ML roles: showcase agentic-titan, IRA facility, multi-model evaluation
- For Platform roles: showcase CI/CD infrastructure, LaunchAgents, registry governance
- For Arts roles: showcase generative art repos, Metasystem Master, p5.js work
- For Financial Services: showcase governance, audit trails, state machine
- The default 5 are FALLBACK, not the primary selection
