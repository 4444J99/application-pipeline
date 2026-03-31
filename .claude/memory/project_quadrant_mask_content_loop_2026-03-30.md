---
name: Quadrant-Mask-Content Loop — applications as content feedstock
description: Every application generates research that becomes public content. Four audience quadrants map to four in-midst-my-life masks. The pipeline markets the product through its own operation.
type: project
---

## The Principle

Every application submitted is three things simultaneously:
1. A submission to a specific opportunity
2. A research project generating domain intelligence
3. Raw material for public-facing content that markets the product

The four audience quadrants map to four identity masks from in-midst-my-life:

| Quadrant | Mask | Voice | Content Register |
|----------|------|-------|-----------------|
| Q1 Individual Applicant | **Narrator** | Peer, fellow seeker, sharing the practice | Testament posts, "here's what I learned" |
| Q2 Individual Employer | **Strategist** | Authority, showing what hiring is missing | Employer-facing LinkedIn, "stop reading resumes" |
| Q3 Institutional Seeker | **Architect** | Builder, showing the system's blueprints | Technical articles, architecture deep-dives |
| Q4 Institutional Hirer | **Integrator** | Infrastructure partner, showing enterprise value | Case studies, integration docs, white papers |

## The Feedback Loop

```
APPLICATION → RESEARCH → CONTENT → DISTRIBUTION → AUDIENCE → REVENUE
     ↑                                                           |
     └───────────── next application informed by audience data ──┘
```

Each application produces:
- Company/role analysis (→ becomes industry content)
- Cover letter narrative (→ becomes Testament post raw material)
- Contact research (→ becomes networking content)
- Scoring data (→ becomes methodology content)
- Quality gate results (→ becomes "how we built this" content)

## Implementation

The LinkedIn content engine (`scripts/linkedin_composer.py`) should accept `--from-application <entry-id>` to extract content themes from a submitted application. The Testament audit enforces quality. The mask determines the voice.

**Why:** Content produced from real applications has authenticity that manufactured content lacks. The reader can feel the difference between "here's a thought experiment about hiring" and "here's what I learned applying to Temporal's AI SDK team." The specificity IS the credibility.

**How to apply:** After every batch of applications, extract 2-3 content themes. Draft Testament posts from the research. Audit. Publish. The pipeline IS the content engine's feedstock.
