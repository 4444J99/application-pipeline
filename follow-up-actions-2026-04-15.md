# Follow-Up Actions from Inbox Review — 2026-04-15

**Window:** 2026-04-09 through 2026-04-15
**Sources:** Mail.app INBOX (~50 messages) + All Mail (~250 messages)
**Prior session:** 2026-04-13/14 (covered 3/25-4/13, 72 tasks, 58 resolved)

---

## SESSION OUTCOMES

### Completed
- Webhook secret rotated: `radix-recursiva-solve-coagula-redi` hook 558013866 (GH-9951654-7992-a1)
- k6 PR #5770 handoff envelope generated for Jules (TODO #2764 cleanup)
- Memory parity restored: 3 files synced to chezmoi source (domus commit `560f628`)
- Pipeline entries closed: Snorkel AI (rejected), Twilio Developer Evangelist (rejected)

### Rejections Logged
| Company | Role | Date | Source |
|---------|------|------|--------|
| Snorkel AI | Staff Applied AI Engineer - Pre-Sales | 2026-04-14 | Greenhouse |
| Twilio | Developer Evangelist | 2026-04-14 | Twilio Careers |
| Grafana Labs | (role unspecified) | 2026-04-09 | Ryan McKellips email (logged in 4/14 session) |

---

## SECURITY — External Action Required

### 1. Rotate OpenAI API Key (CRITICAL)
- **Source:** polem4rch@gmail.com (responsible disclosure, 2026-04-10)
- **What:** Key exposed in public Docker image `cetaceang/openai-king` (92MB, 507 pulls, live since Aug 2025)
- **Action:** Rotate at platform.openai.com. Audit usage logs. Report image to Docker Hub.
- **Status:** OPEN — requires browser login

### 2. GCP Billing Overdue
- **Source:** CloudPlatform-noreply@google.com (2026-04-15)
- **What:** Account `016B52-CC5865-3BDA82` has unpaid balance. May be deactivated.
- **Action:** Pay at console.cloud.google.com/billing
- **Status:** OPEN — requires browser login

### 3. Webhook Receiver Update
- **What:** Webhook secret rotated for hook 558013866 but receiving endpoint (`github-bot-production.appspot.com`) needs new secret to verify signatures.
- **New value:** Stored in conversation output — save to 1Password immediately <!-- allow-secret -->
- **Action:** Store in 1Password as "GitHub Webhook - radix-recursiva", update App Engine endpoint config.
- **Status:** OPEN — requires 1Password + App Engine access

### 4. Semgrep Integration Webhook
- **What:** Hook 578404008 (ivviiviivvi--Semgrep-Code--011226) cannot be rotated via user API.
- **Action:** Check via GitHub Settings → Applications → Semgrep, or contact Semgrep.
- **Status:** OPEN — requires GitHub App settings

---

## FINANCIAL — External Action Required

### 5. Tax Filing (DEADLINE: TODAY 2026-04-15)
- **Source:** Healthcare.gov (2026-04-08)
- **What:** Must file 2025 return and reconcile Form 1095-A (ACA premium tax credits)
- **Action:** File via IRS Free File or VITA

### 6. LegalZoom FL Annual Report (DEADLINE: 2026-04-16)
- **Source:** LegalZoom (2026-04-10)
- **What:** AJP Media Arts LLC Florida Annual Report — submit info to LegalZoom by Apr 16, state deadline May 1
- **Action:** LegalZoom Compliance Center — pre-filled, ~5 min

### 7. Santander Overdraft (FEE RISK: 2026-04-16)
- **Source:** Santander (2026-04-10/11)
- **What:** Account overdrawn by $1.04. 5-day sustained overdraft fee ($15) triggers if not resolved.
- **Action:** Deposit/transfer via Santander app

### 8-12. Carried from 4/14 (unchanged)
- **Nelnet default** — call 888-486-4722, request forbearance
- **January/Zip Pay** — $175.50, contact@january.com, PIN ZGEPZC
- **Cash App** — $50 from Richard Gonzalez, expires ~Apr 19
- **GoDaddy met4vers.io** — expired Mar 29, renewal or let expire
- **LinkedIn Premium** — cancel by Apr 18 to avoid auto-charge

---

## PEOPLE — Pending

### 13. Noah Beddome (LinkedIn)
- **What:** Security leader replied "I'd love to chat" to InMail
- **Action:** Reply with scheduling options
- **Status:** OPEN

### 14. Becka McKay (FAU)
- **What:** Thread complete on user's side (replied Apr 14 9:55am). Awaiting her response.
- **Action:** Follow up no earlier than Apr 17 if no reply.
- **Status:** WAITING

---

## JOB SIGNALS (No Action — Monitor)

- Anthropic: Technical Enablement Lead (Claude Code), Solutions Architect (Applied AI)
- Sudowrite: Hiring full-time, freelance, gigs
- Figma: Solutions Consultant
- Runway: Creative Workflow Architect

---

## IRF CARRY-FORWARD (Not Yet Updated in IRF)

| Item | IRF Action Needed |
|------|-------------------|
| IRF-OSS-042 update | k6 PR #5770 APPROVED by mstoykov. TODO cleanup dispatched to Jules. Status: approved → pending cleanup → merge |
| NEW: security — webhook exposure | GitHub disclosed webhook secret leak (GH-9951654-7992-a1). Hook 558013866 rotated. Hook 578404008 (Semgrep) pending. |
| NEW: security — OpenAI key in Docker | `cetaceang/openai-king` exposes live API key. Rotation required. |
| NEW: security — GCP billing overdue | Account `016B52-CC5865-3BDA82`. Deactivation risk. |
| IRF-SYS-011 update | GoDaddy `met4vers.io` cancellation notice received (expired Mar 29, grace period). |
