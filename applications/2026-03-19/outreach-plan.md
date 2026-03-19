# Outreach Plan — March 19, 2026

2 applications submitted. Connect with hiring contacts within 1-3 days.

---

### [ ] 1. Coinbase — Senior SWE, Data Platform — Remote USA
- **Status:** Submitted March 19 (Day 0)
- **Portal:** https://www.coinbase.com/careers/positions/7728790?gh_jid=7728790
- **Note:** 2nd Coinbase application (1st was Money Movement & Risk on Mar 18). Research says max 2 if genuinely different roles — Data Platform vs Money Movement qualifies.
- **Contacts:**
  - ★ **Jianlong Zhong** — [linkedin.com/in/jay-zhong](https://www.linkedin.com/in/jay-zhong/) (Leading Data Teams @ Coinbase — Sr Engineering Leader, Data Platform & Infra)
  - **Vivek Maurya** — [linkedin.com/in/vivek-maurya-3475691](https://www.linkedin.com/in/vivek-maurya-3475691/) (Building AI-driven data platform @ Coinbase)
  - **Amar Nath** — [linkedin.com/in/amar1611](https://www.linkedin.com/in/amar1611/) (Coinbase, hiring for Data Platform)
- **Connection message:**
  > Hi [Name] — I built a data platform from scratch: registry-v2.json (2,240 lines, single source of truth for 113 repos), JSON Schema validation in CI, automated lineage tracking across 50 dependency edges. Applied for Senior SWE, Data Platform. Would love to connect.
- **If accepted — DM:**
  > Thanks for connecting. The registry I maintain is essentially a hand-built data catalog — 113 repos declared via seed.yaml contracts, aggregated into a single source of truth, with JSON Schema validation and automated lineage enforcement. The same architectural patterns that make my system queryable are what Coinbase applies to data platform infrastructure. Happy to walk through it.
  >
  > Portfolio: https://4444j99.github.io/portfolio/
- **Log:** `python scripts/followup.py --log coinbase-senior-software-engineer-data-platform --channel linkedin --contact "[Name]" --note "Connection request sent"`

---

### [ ] 2. Temporal — Senior SWE, Open Source Server — Remote US
- **Status:** Submitted March 19 (Day 0)
- **Portal:** https://job-boards.greenhouse.io/temporaltechnologies/jobs/4290103007
- **WARM PATH:** Mason Egger and Cecil Phillip (Temporal DevRel) both accepted LinkedIn connections and received DMs. This is the warmest application in the pipeline.
- **Contacts (already connected):**
  - ★ **Mason Egger** — [Temporal DevRel] · ✅ Connected + DM sent
  - **Cecil Phillip** — [Temporal DevRel] · ✅ Connected + DM sent
- **New contacts to add:**
  - **Search:** "Engineering Manager Temporal" on LinkedIn
  - **Search:** "Senior Software Engineer Temporal open source" on LinkedIn
- **Connection message:**
  > Hi [Name] — I built a promotion state machine governing 113 repos with forward-only transitions, 50 dependency edges, zero violations. Applied for Senior SWE on the OSS Server team. Mason Egger and Cecil Phillip connected me — the architecture maps directly to Temporal's workflow model.
- **If accepted — DM:**
  > Thanks for connecting. My system's promotion state machine — LOCAL → CANDIDATE → PUBLIC → GRADUATED with forward-only transitions, CI-enforced validation, and compensating actions on failure — is structurally identical to a Temporal workflow. I built it by hand because I didn't have Temporal. Now I want to work on the infrastructure that would have solved it correctly.
  >
  > Portfolio: https://4444j99.github.io/portfolio/
  > GitHub: https://github.com/meta-organvm
- **Log:** `python scripts/followup.py --log temporal-senior-software-engineer-open-source-server --channel linkedin --contact "[Name]" --note "Connection request sent"`

---

## Rules

1. **Temporal is priority** — warm path via Mason + Cecil. Ask them: "Who on the OSS Server team should I talk to?"
2. **Coinbase is 2nd application** — different team, different role. Don't mention the Money Movement application.
3. **LinkedIn throttle active** — at ~150-175 weekly cap. Only connect with high-value targets this week.
4. **Log every action.**
