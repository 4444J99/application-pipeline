# Attack Order — All Actionable Items — 2026-04-13

**Sources merged:** INBOX review (27 items) + All Mail GitHub review (500 emails, 17 repos, 11 other streams)
**Total unique actionable items:** 72
**Noise dismissed:** ~430 threads (newsletters, marketing, transactional receipts, entertainment)

---

## TIER 0 — TODAY (time-locked obligations)

| # | Item | Domain | Action | Deadline |
|---|------|--------|--------|----------|
| 0.1 | Deposition prep — Micah Longo | Legal | Attend today's 12 PM session (or check if already done). Prep for 4/14 + 4/16 | **Today** |
| 0.2 | Reply to Becka McKay (FAU) | Outreach | She asked "Where are you? What resources do you need?" — respond while warm | **Today** |

---

## TIER 1 — WITHIN 24 HOURS (security + legal + financial severity)

| # | Item | Domain | Status |
|---|------|--------|--------|
| 1.1 | Exposed OpenAI API key — Docker Hub | Security | **INVESTIGATED** — Docker image is `cetaceang` (not yours). Awaiting browser verification of OpenAI dashboard. |
| 1.2 | `.github` Sentinel CRITICAL PRs | Security/Code | **CLEAR** — All 8 PRs already merged (Dec 2025 – Jan 2026). |
| 1.3 | `petasum-super-petasum` Sentinel CRITICALs | Security/Code | **CLEAR** — 4 PRs closed. Workflow uses safe `env:` pattern. Low risk. |
| 1.4 | GitHub third-party OAuth app added | Security | **INVESTIGATED** — Account looks clean. Awaiting browser verification. |
| 1.5 | Security Alert: Secrets in code | Security | **CHECKING** — Agent investigating issue #109 status. |
| 1.6 | AJP Media Arts LLC — State filing | Legal/Business | **PARKED** — External billing/legal. Noted, not blocking. |
| 1.7 | AJP Media Arts LLC — Compliance filing | Legal/Business | **PARKED** — External billing/legal. Noted, not blocking. |
| 1.8 | Nelnet student loan — default prevention | Finance | **PARKED** — External financial. Noted, not blocking. |

---

## TIER 2 — THIS WEEK (deadlines, pipeline hygiene, financial cleanup)

| # | Item | Domain | Action | Deadline |
|---|------|--------|--------|----------|
| 2.1 | Deposition prep sessions | Legal | 4/14 @ 12 PM, 4/16 @ 12 PM. Review HIPAA update from 3/30. Final dress rehearsal via Zoom. | 4/14, 4/16 |
| 2.2 | LinkedIn Premium renewal decision | Subscription | **PARKED** — External billing. Decision by 4/17. | **4/17** |
| 2.3 | Cash App $50 — Richard Gonzalez | Finance | **PARKED** — External financial. | ~4/19 |
| 2.4 | January/Zip Pay $175.50 collection | Finance | **PARKED** — External financial. | This week |
| 2.5 | Santander overdraft -$1.04 | Finance | **PARKED** — External financial. | This week |
| 2.6 | Healthcare.gov tax return | Finance/Gov | **PARKED** — External. | ASAP |
| 2.7 | Record pipeline outcomes | Pipeline | **DONE** — Grafana (rejected), Awesome Foundation (rejected), Webflow (acknowledged). | ~~This week~~ |
| 2.8 | MCP prompt injection (IRF-SYS-062) | Security | **CHECKING** — Agent investigating issue #156 status. | This week |

---

## TIER 3 — THIS WEEK (development — high-value work)

### ORGANVM Infrastructure

| # | Item | Repo | Action |
|---|------|------|--------|
| 3.1 | `.github` Bolt optimization PRs | organvm-i-theoria/.github | Batch-review ~12 Bolt PRs (regex, crawler, link validation). Merge viable ones. |
| 3.2 | `.github` Palette dashboard PRs | organvm-i-theoria/.github | Batch-review ~10 Palette PRs (legends, empty states, emojis, categories). Pick best, close duplicates. |
| 3.3 | `.github` workflow fixes | organvm-i-theoria/.github | PRs #185-#206: pip cache removal, SHA pinning, Python execution, sed delimiter. Mostly mechanical — batch merge. |
| 3.4 | Axiom reconciliation (IRF-SYS-088) | corpvs-testamentvm | SEED.md A1-A9 vs SPEC AX-000-001..009. Foundational — blocks downstream work. Issue #311. |
| 3.5 | Primitive set reconciliation (IRF-SYS-089) | corpvs-testamentvm | Four competing formulations need resolution. Issue #312. |
| 3.6 | Registration vacuum (IRF-SYS-090) | corpvs-testamentvm | 10+ repos on disk not in registry-v2.json. Birth pre-req. Issue #313. |
| 3.7 | UMFAS birth (IRF-SYS-087) | corpvs-testamentvm | Create the space. Implement from axioms, not derivatives. Issues #310, #305. |

### Sovereign Systems (Client Work)

| # | Item | Repo | Action |
|---|------|------|--------|
| 3.8 | Node architecture lock (alpha.4) | sovereign-systems | Finalize 13 vs 14 nodes + order. Issue #13. Blocks all beta work. |
| 3.9 | Content genome merge (beta.11) | sovereign-systems | Reduce 1,821 atoms → ~1,000 build-ready groups. Issue #24. |
| 3.10 | CLAUDE.md system variable refresh (omega.4) | sovereign-systems | Issue #35. Quick win — unblocks agent work in this repo. |
| 3.11 | Source-bundle naming normalization (omega.3) | sovereign-systems | 127 files with spaces/special chars. Issue #34. |

### Engine & Orchestration

| # | Item | Repo | Action |
|---|------|------|--------|
| 3.12 | SPEC-024 Phases 3-7 | organvm-engine | CLI projection, heartbeat daemon, MCP + dashboard. Issues #77-81. |
| 3.13 | Threshold topology verification | orchestration-start-here | Omega scorecard impact, testament events, concordance IDs. Issues #151-154. |
| 3.14 | Derivation/axiom governance convergence | system-system--system | 11 derivations + 8 axioms need governance loci. Issues #7, #8. |

---

## TIER 4 — NEXT 7 DAYS (pipeline triage + outreach + code maintenance)

### Pipeline — Job Triage

| # | Item | Action |
|---|------|--------|
| 4.1 | Score new job listings | Run `score.py` on: Thrive Mobile (AI Product Innovation), Reejig (AI Workflow Builder), Capgemini (Generative AI Engineer), ResponsiveAds (Product Mgmt Lead), Sudowrite (hiring). Apply only if >= 7.0. |
| 4.2 | GitHub Enterprise billing follow-up | Ticket 4130573 closed. Complete feedback survey. Decide next billing action per discussion. |

### Outreach

| # | Item | Action |
|---|------|--------|
| 4.3 | Evaluate SWARMs / Thomas King | Read full email (4/2). Assess alignment with ORGANVM. Respond or archive. |
| 4.4 | Alex @ tribecode.ai — anthropic-sdk-python PR | Review context. Respond if relevant collaboration. |

### Dependency Updates (batch)

| # | Item | Repos |
|---|------|-------|
| 4.5 | Dependabot PR batch | stakeholder-portal: next, vite, langsmith, drizzle-orm. portfolio: basic-ftp, defu, vite, minor-patch group. narratological-lenses: vite. the-actual-news: next. |
| 4.6 | public-record-data-scrapper issues | CI feedback, package-lock size, review comments. Issues #35, #47, #73, #75, #83, #85, #111. |
| 4.7 | Domus LaunchAgent ExecTimeout audit | Issue #25 in domus-semper-palingenesis. Audit all plists for missing ExecTimeout. |

### Sovereign Systems — Beta Backlog

| # | Item | Issue |
|---|------|-------|
| 4.8 | Editorial triage of 104 FLAGGED atoms | beta.12 / Issue #25 |
| 4.9 | Semantic clustering — 1,153 SIGNAL atoms | beta.15 / Issue #28 |
| 4.10 | Hydration Node phased plan | beta.10 / Issue #23 |
| 4.11 | EWG API for Hydration Node ZIP lookup | beta.16 / Issue #29 |
| 4.12 | Downloadable product pipeline | beta.18 / Issue #31 |
| 4.13 | Astrology/human design integration layer | beta.17 / Issue #30 |

---

## TIER 5 — BACKLOG (low priority / FYI / optional)

| # | Item | Action |
|---|------|--------|
| 5.1 | Subscription decisions | Verizon YouTube Premium pricing, Fly.io support (expired), Spectrum (trial ended), Instacart+ (monitor usage) |
| 5.2 | Monthly statement review | Alliant CU March statement, Robinhood Q1 statement |
| 5.3 | PayPal/Honey rewards changes | Review if using cashback features |
| 5.4 | Banking/Plaid connections verify | 3/30 cluster: Santander PIN + Apple Pay + multiple Plaid connections. Confirm intentional. |
| 5.5 | Optional events | GitGuardian secrets webinar, Google Next digital streaming, IBO IBEN webinar (April) |
| 5.6 | Governance issues | Ceremony-as-specification (#317), 15 ideal forms (#316), organ boundary audit (#315), governance predicates (#304, #303) |
| 5.7 | a-mavs-olevm Stripe tip jar | Issue #74 — Stripe Payment Link for omega #9/#10 |
| 5.8 | Sovereign Systems remaining beta | Revenue agreement (alpha.3), custom domains (alpha.1), quiz routing (beta.4), spiral interaction (beta.3), subscription model (beta.2) |
| 5.9 | Open-source PRs | temporalio/sdk-python docs PR #1385, openai/openai-agents-python fix PR #2802, grafana/k6 metrics comment PR #5770 |

---

## Execution Strategy

### Today (4/13) — 4 items
```
0.1 Deposition prep (if not done)
0.2 Reply to Becka McKay
1.1 Rotate exposed API key
1.4 Verify GitHub OAuth app
```

### Tomorrow (4/14) — 8 items
```
0.1 Deposition prep @ 12 PM
1.2 Batch-merge .github Sentinel CRITICALs
1.3 Batch-merge petasum Sentinel CRITICALs
1.5 Audit secrets alert
1.6 AJP Media Arts state filing
1.7 AJP Media Arts compliance filing
1.8 Contact Nelnet re: default prevention
2.7 Record pipeline outcomes (batch command)
```

### Tues-Wed (4/15-16) — financial + pipeline + code
```
2.1 Deposition prep @ 12 PM (4/16)
2.2 LinkedIn Premium decision
2.3 Cash App decision
2.4 Zip Pay resolution
2.5 Santander overdraft
2.6 Tax return filing
2.8 MCP prompt injection mitigation
3.1-3.3 .github PR batch (Bolt + Palette + workflow fixes)
```

### Thu-Fri (4/17-18) — ORGANVM core + sovereign systems
```
3.4-3.7 corpvs-testamentvm: axiom/primitive/registry/UMFAS
3.8-3.11 sovereign-systems: node lock + genome + CLAUDE.md + naming
3.12-3.14 engine + orchestration + system-system governance
```

### Weekend/Next Week — triage + maintenance
```
TIER 4: pipeline job scoring, outreach evaluation, dependency batch, beta backlog
TIER 5: subscriptions, statements, optional events, governance backlog
```

---

## Metrics

| Category | Count | Tiers |
|----------|-------|-------|
| Security (code + credentials) | 10 | 1-2 |
| Legal / Business filings | 4 | 0-2 |
| Finance | 6 | 1-2 |
| Pipeline (career) | 8 | 2, 4 |
| ORGANVM infrastructure | 7 | 3 |
| Sovereign Systems (client) | 10 | 3-4 |
| Outreach / Network | 4 | 0, 4 |
| Subscriptions / Admin | 8 | 2, 5 |
| Code maintenance (deps, CI) | 8 | 4 |
| Governance / Theory | 7 | 5 |
| **Total actionable** | **72** | |
