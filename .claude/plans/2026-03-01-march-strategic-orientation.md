# Job Market Landscape: March 2026 Strategic Orientation

*Plan date: 2026-03-01*

## Context

60 submissions were fired in a burst Feb 24–27. Pipeline is now in "wait + follow up" mode. One rejection received (cohere-applied-ai, resume screen, 3-day turnaround). 961 entries in research pool. 37 active entries across 5 tracks. The purpose of this plan is to orient strategy based on current market conditions and pipeline signals.

---

## Market Reality: March 2026

### Overall Climate
- **Stabilizing, not recovering.** ~51K tech layoffs YTD but dramatically lower than 2025's 245K. Hiring rate ~29%.
- **Cold applications are effectively dead** at competitive targets (AI labs, elite creative orgs). Quality of signal per application matters far more than throughput now.
- **Volume hiring is not happening.** Each hire is selective and deliberate.

### By Track

| Track | Market Signal | Conversion Timeline |
|-------|--------------|-------------------|
| **Platform/Infra Engineer** | Strongest immediate demand. Data center + AI workload expansion. Go, Kubernetes, Terraform hot. | 4–8 weeks |
| **AI/ML Labs** | Anthropic has ~44 open roles. Requires 6–12 month relationship runway for competitive conversion. Cold app success rate low. | 3–6 months w/ relationship |
| **Creative Technologist** | Thin as a job market. Robust as funded residency/grant ecosystem. Creative Capital opens TODAY (April 2 deadline). | Grant cycles: 3–6 months |
| **Academic/Educator** | Fall 2026 hiring windows closed. Focus shifts to visiting artist / guest lecture positions built now for 2027 applications. | 2027 cycle |
| **Systems Artist** | LACMA Art+Tech Lab (up to $50K, 2-year) closes April 22. Prize cycles (Prix Ars Electronica, STARTS Prize) remain active. | Prize cycles: varies |

### What Hiring Managers / Grant Panels Want in 2026
1. **Proof > claims.** Portfolio proves; resume claims. GitHub/public artifacts reviewed immediately.
2. **Numbers lead everything.** "103 repos, 2,349 tests" — storefront metrics beat prose.
3. **AI-conductor methodology is a positive signal.** Human directs + AI generates volume + human judgment visible = exactly what labs and panels are rewarding.
4. **AI-generated content (undifferentiated) is a disqualifying negative signal.** 53% of hiring managers cite it as top red flag.
5. **Relationships before applications.** The effective application window at Anthropic, Creative Capital, Knight Fellowship is 6–12 months prior.

---

## Current Pipeline State

| Metric | Value |
|--------|-------|
| Total submitted | 60 (all Feb 24–27, 1–4 days old) |
| Active: staged | 14 |
| Active: drafting | 7 |
| Active: qualified | 8 |
| Active: deferred | 3 |
| Research pool | 961 entries |
| Interviews | 0 |
| Positive outcomes | 0 |
| Rejections | 1 (cohere-applied-ai, resume screen) |

**Too early for conversion signal.** 48 entries awaiting response, oldest submission 3 days old.

### Immediate Deadline Pressure (Priority Order)

| Deadline | Entry | Status | Action Needed |
|----------|-------|--------|---------------|
| **April 2** | creative-capital-2027 | staged | Application opened March 2. 32 days. HIGHEST PRIORITY. |
| **March 16** (deferred) | pen-america | deferred | Monitor — resume March 1 per deferral |
| **March 18** | google-creative-fellowship | drafting | Complete draft now |
| **April 1** | fire-island-residency, headlands-center, nlnet-commons | drafting | 31 days |
| **April 22** | lacma-art-tech | staged | 52 days — top art+tech grant ($50K, 2yr) |

---

## Recommended Strategy for March 2026

### This Week (March 1–7)

1. **Code red: Creative Capital.** Portal opened March 2. April 2 deadline. This is the single highest-leverage grant cycle open right now. `compose --target creative-capital-2027` and begin drafting.
2. **Follow-up activation.** 38 LinkedIn connection actions due in Day 1–3 window. Run `python scripts/followup.py` daily. This is now the primary conversion lever — not new submissions.
3. **Complete google-creative-fellowship draft.** March 18 deadline is 17 days away.

### This Month (March)

4. **Complete fire-island, headlands, nlnet drafts** before April 1.
5. **Monitor Anthropic research pool.** 20+ entries parked there. Begin relationship-building actions (comment on public work, engage on social/GitHub) rather than cold applications. Target: submit 1–2 Anthropic roles in May–June after 3–4 months of visible presence.
6. **Platform/infra track is the fastest-converting.** Cohere, Elastic, MongoDB, and Notion (staged) should be submitted if not already. These convert in 4–8 weeks on skill signal alone.
7. **Draft LACMA Art+Tech** — April 22 deadline. Up to $50K over 2 years. Strong systems-artist framing fit.

### Structural Observations

- **Independent-engineer is the volume workhorse** (42/78 entries, 100% submit rate) — market supports this but conversion is competitive. Differentiation comes from public artifact signal, not more applications.
- **Systems-artist / creative-technologist** tracks depend on grant cycles, not job boards. These require calendar-driven attention (Creative Capital, LACMA, Prix Ars, STARTS Prize).
- **Community-practitioner** track has 50% submit rate — lowest of all positions. Consider whether deferred entries (pen-america, stimpunks) are worth the continued effort vs. letting them expire.
- **No academic submissions yet** — consistent with market reality (cycle closed). No action needed until fall 2026.

### Compensation Benchmarks (For Offer Evaluation)

| Track | Reasonable Target |
|-------|-----------------|
| Platform/Infra Eng (Elastic, Cohere, MongoDB tier) | $150K–$225K TC |
| AI lab (Anthropic, if conversion happens) | $400K–$630K TC |
| Creative Capital Award | Multi-year project grant |
| LACMA Art+Tech Lab | Up to $50K / 2 years |
| Mozilla Fellowship (if opens) | $100K total ($75K stipend + $25K project) |

---

## Verification / Next Actions

```bash
# 1. Daily follow-up dashboard
python scripts/followup.py

# 2. Check urgent deadlines (use plan section — deadlines section unavailable)
python scripts/standup.py --section plan

# 3. Begin Creative Capital draft
python scripts/compose.py --target creative-capital-2027

# 4. Complete google-creative-fellowship draft
python scripts/compose.py --target google-creative-fellowship

# 5. Campaign view for next 30 days
python scripts/campaign.py --days 30
```

---

## Key Sources (External Research)

- [2026 Tech Market Outlook — Refactor Talent](https://refactortalent.com/2026-tech-job-market-outlook/)
- [Breaking Into AI 2026 — DataExec](https://dataexec.io/p/breaking-into-ai-in-2026-what-anthropic-openai-and-meta-actually-hire-for)
- [Creative Capital 2026 Open Call](https://creative-capital.org/creative-capital-award/award-application/)
- [LACMA Art+Tech Lab Grants](https://www.lacma.org/art/lab/grants)
- [Hiring Trends 2026 — TechHR Series](https://techrseries.com/artificial-intelligence/hiring-trends-report-2026-study-finds-ai-is-accelerating-the-decline-of-the-resume-as-employers-demand-more-authentic-signals-of-talent/)
