# Recruiter/Hiring-Manager Filter Research — 2026-03-19

## Key Statistics

| Metric | Value | Source |
|--------|-------|--------|
| Recruiter initial scan time | 11.2 seconds | InterviewPal eye-tracking |
| Metrics boost to top-third ranking | +48% | ResumeWorded 2025 |
| Companies using AI screening | 83% | Source 070 |
| Cover letter callback lift | +53% | ResumeGenius meta-analysis |
| HMs who read cover letters | 94% | Source 095 |
| Referral hire multiplier | 8x | LinkedIn Economic Graph |
| Cold tier-1 pass rate | 2% | Source 025 |
| AI content rejection (generic) | 62% | Source 060 |
| AI content rejection (robotic) | 80% | Source 061 |
| Easy Apply human review rate | 3% | Source 066 |
| FDE posting growth YoY | 1,165% | Bloomberry/Lightcast |
| GitHub review by tech recruiters | 87% | Source 124 |
| Optimal keyword match | 70-80% of JD | ResuTrack 2026 |
| Follow-up offer lift | +68% | Source 110 |

## Implementation: recruiter_filter.py

Built and operational. Checks:
- Stale metrics (canonical values as single source of truth)
- Red flags (passive language, "Independent", "Open to work")
- Formatting (cover letter word count, plain text, phone numbers)
- Auto-fix mode for base resumes

## Priority Additions (from research)

1. Cover letter existence gate (B9) — 53% callback lift
2. Quantified impact bullets ≥3 (W1) — 48% ranking boost
3. Cover letter opener check (W5) — reject "I am writing to..." / "I am excited to apply..."
4. Company-specific reference in cover letter (W4) — 40-53% fewer callbacks without
5. Network proximity ≥5 for tier-1 companies (W12) — cold tier-1 = 2% pass rate
