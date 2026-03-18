# Materials Reorganization Plan

## Problems Identified

1. **Cover letter quality issues:**
   - Location wrong ("South Florida" — should be "Staten Island, NYC" or "New York City")
   - Format wrong (markdown headers instead of plain letter text)
   - MCP attributed to OpenAI (it's Anthropic's protocol)
   - Old metrics (94 CI/CD → should be 104)
   - Stripe letter spends a paragraph apologizing for not having blockchain experience

2. **Materials scattered across 4 directories:**
   - `materials/resumes/batch-03/` — 15 dirs (most dead)
   - `variants/cover-letters/` — 100 files (90+ dead)
   - `scripts/.greenhouse-answers/` — 70 files (60+ dead)
   - Pipeline YAML entries reference them by path

3. **Dead materials for non-submitted roles:**
   - 100 cover letters for 9 submissions = 91 dead files
   - 70 answer files for ~10 actual submissions = 60 dead files

## Proposed Structure

```
applications/
  2026-03-15/
    anduril-lead-technical-writer/
      resume.html
      resume.pdf
      cover-letter.md
      answers.yaml (if applicable)
      entry.yaml (copy of pipeline entry at submission time)
  2026-03-17/
    harvey-ai-agents/
      resume.html
      resume.pdf
      cover-letter.md
      entry.yaml
    langchain-enterprise-readiness/
      ...
    openai-fde/
      ...
    stripe-smart-contract/
      ...
    doppler-full-stack/
      ...
    notion-solutions/
      ...
```

Each submission date is a batch. Each company/role is a folder. Everything for that application lives together. Nothing exists that wasn't submitted.

## Cover Letter Template Fixes

1. **Location:** "New York City" (not South Florida)
2. **Format:** Plain text, no markdown headers. "Dear [Company] Hiring Team," ... "Sincerely, Anthony James Padavano"
3. **Metrics:** 113 repos, 104 CI/CD, 23,470 tests, 739K words, 82K files, 22 languages
4. **Never attribute MCP to OpenAI** — it's Anthropic's Model Context Protocol
5. **Never apologize for what you lack** — lead with what you bring

## Research Needed

How many roles per company is optimal? Peer-reviewed sources on:
- Application volume vs response rate
- Multiple applications to same company
- ATS behavior with multiple submissions from same applicant
- Referral multiplier validation
