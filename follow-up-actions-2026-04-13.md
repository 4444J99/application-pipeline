# Work Tasks Derived from Inbox Review — 2026-04-13

**Window:** 2026-03-25 through 2026-04-13
**Sources:** Mail.app INBOX (53 messages) + Gmail MCP threads (60 threads, 4/3-4/13)
**Total unique threads reviewed:** ~100

---

## CRITICAL — Immediate Action Required

### 1. Deposition Prep Sessions (Legal)
- **Source:** Micah Longo <mlongo@longofirm.com> — 4/8 schedule + 3/30 HIPAA update
- **What:** Remaining deposition prep sessions: **4/13 (today @ 12 PM)**, **4/14 @ 12 PM**, **4/16 @ 12 PM**. First session (4/9) completed via phone at 1 PM. Final "dress rehearsal" will be via Zoom.
- **Action:** Attend today's session. Review HIPAA update sent 3/30. Prepare for 4/14 and 4/16 sessions.
- **Status:** IN PROGRESS

### 2. Exposed OpenAI API Key in Docker Hub (Security)
- **Source:** Gabriel <polem4rch@gmail.com> — 4/11
- **What:** Security researcher found OpenAI API key exposed in public Docker image `cetaceang/openai-king`. Claims it's your key.
- **Action:** Verify if this is your key. If yes: rotate immediately via OpenAI dashboard. Remove or update the Docker image. Reply to Gabriel acknowledging.
- **Urgency:** HIGH — key may be actively exploited

### 3. Student Loan Default Warning (Finance)
- **Source:** Nelnet <nelnetnoreply@nelnet.studentaid.gov> — 4/11
- **What:** Account EXXXXX3852 at risk of default. "You still have time to avoid default."
- **Action:** Contact Nelnet or explore IDR/deferment options. This is time-sensitive — default has lasting credit consequences.
- **Urgency:** HIGH

---

## FINANCE — Action Needed

### 4. Cash App $50 Request — Richard Gonzalez
- **Source:** cash@square.com — 4/5 (received), 4/6 and 4/12 reminders
- **What:** $50 request from Richard Gonzalez. Request expires ~4/19.
- **Action:** Pay or decline before expiry.
- **Status:** NEEDS DECISION

### 5. Santander Overdraft
- **Source:** Santander_Bank@alerts.santander.us — 4/10
- **What:** Account *******1657 overdrawn -$1.04 (1 returned item).
- **Action:** Deposit to clear negative balance. Check for overdraft fees.
- **Status:** NEEDS ACTION

### 6. January/Zip Pay Collection — $175.50
- **Source:** notices@january.com — 4/3, 4/9, 4/12 (recurring)
- **What:** January (collector for Zip Co US) pursuing $175.50 for Zip Pay in 4 balance.
- **Action:** Pay, dispute, or negotiate payment plan. These notices are escalating.
- **Status:** NEEDS RESOLUTION

### 7. Healthcare.gov Tax Return Reminder
- **Source:** Marketplace@healthcare.gov — 4/8
- **What:** Must file tax return if Marketplace premium assistance was received.
- **Action:** File 2025 tax return if not already done. Marketplace subsidy reconciliation required.
- **Status:** NEEDS ACTION

### 8. Monthly Statements Available
- **Source:** Alliant CU (4/2), Robinhood (4/2)
- **What:** March statements ready for review.
- **Action:** Review both. Check Alliant for any unusual activity; note Robinhood positions for tax planning.
- **Status:** FYI / REVIEW

### 9. PayPal / Honey Rewards Program Changes
- **Source:** honey@my.joinhoney.com — 4/2
- **What:** Amendments to PayPal Rewards Program Agreement.
- **Action:** Review if using Honey cashback. May affect reward structure.
- **Status:** LOW PRIORITY

---

## PIPELINE — Jobs & Applications

### 10. Cloudflare Rejection — Models Engineer, Developer Relations
- **Source:** no-reply@cloudflare.com — 4/2
- **What:** Application update (rejection) for Models Engineer, Developer Relations.
- **Action:** Record outcome in pipeline. Run `python scripts/check_outcomes.py` or `python scripts/check_email.py --record --yes` to update YAML.
- **Status:** NEEDS RECORDING

### 11. Grafana Labs — Full Cycle Complete
- **Source:** Grafana notifications (3/31, 4/1) + Ryan McKellips rejection (4/9)
- **What:** Recruiter screen was scheduled (4/1 for Mon 4/6 10:30 AM), interview occurred, then formal rejection on 4/9: "we've decided to not move forward."
- **Action:** Record outcome. Log rejection signal (screened — post-interview). Note: GitHub ticket 4130573 feedback survey also arrived from GitHub Support (separate item).
- **Status:** NEEDS RECORDING

### 12. Webflow — Application Acknowledged
- **Source:** no-reply@webflow.com — 3/30
- **What:** "Thanks for your interest in Webflow, Anthony James"
- **Action:** Record acknowledgment in pipeline if not already tracked.
- **Status:** NEEDS REVIEW

### 13. Awesome Foundation NYC — Grant Not Selected
- **Source:** info@awesomenyc.org — 4/9
- **What:** March 2026 grant awarded to another applicant. "You were not selected as this month's grantee."
- **Action:** Record outcome. Consider reapplying to a future cycle.
- **Status:** NEEDS RECORDING

### 14. Job Listings to Evaluate
- **Source:** LinkedIn jobs-listings, recruiter emails
- **What:** New postings spotted in inbox:
  - Thrive Mobile — Manager, AI Product Innovation (LinkedIn, 4/1 + 4/10)
  - Reejig — AI Workflow Builder (LinkedIn, 4/8)
  - Capgemini — Generative AI Engineer (LinkedIn, 4/4)
  - ResponsiveAds — Ad Format & Template Product Management Lead (4/4)
  - Sudowrite — hiring (Full-time, Freelance, Gigs) (4/9)
- **Action:** Score against rubric via `python scripts/score.py`. Check if any exceed 7.0 threshold.
- **Status:** NEEDS TRIAGE

### 15. GitHub Enterprise Billing Ticket Closed
- **Source:** developer@githubsupport.com — 4/8 (update), 4/9 (feedback survey)
- **What:** Support ticket 4130573 (billing review & plan assessment) resolved and closed.
- **Action:** Complete feedback survey if desired. Evaluate next steps per billing discussion.
- **Status:** FYI / CLOSED

---

## OUTREACH & NETWORK

### 16. Becka McKay (FAU) — Replied, Needs Follow-up
- **Source:** Sent: padavano.anthony@gmail.com (4/13), Reply: rmckay3@fau.edu (4/13)
- **What:** You reached out to Becka McKay (Professor, FAU) requesting guidance. She replied same day: "Where are you? What kind of resources are you most in need of?"
- **Action:** Reply with specific resource needs and current situation. She's responsive — maintain momentum.
- **Urgency:** RESPOND TODAY

### 17. Thomas King / SWARMs — Evaluate Outreach
- **Source:** thomas@contourdefinemilestone.com — 4/2
- **What:** "SWARMs <> 4444J99!" — appears to be a collaboration inquiry or cold outreach related to multi-agent systems.
- **Action:** Read full email. Evaluate if aligned with ORGANVM / studio goals. Respond or archive.
- **Status:** NEEDS REVIEW

### 18. Alex @ tribecode.ai — anthropic-sdk-python PR
- **Source:** a@tribecode.ai — 3/27
- **What:** Discussion about an anthropic-sdk-python pull request.
- **Action:** Review the PR context. Respond if collaboration is relevant.
- **Status:** NEEDS REVIEW

---

## SUBSCRIPTIONS — Review & Manage

### 19. LinkedIn Premium Renewal — April 18
- **Source:** billing-noreply@linkedin.com — 4/11
- **What:** Premium subscription renewing 4/18. Reminder of benefits.
- **Action:** Decide: continue (useful for job pipeline + InMail) or cancel before 4/18.
- **Urgency:** DECISION BY 4/17

### 20. Verizon YouTube Premium Pricing Change
- **Source:** no-reply@customer.verizon.com — 4/10
- **What:** YouTube Premium perk pricing being updated.
- **Action:** Review new pricing. Decide if Verizon perk is still worthwhile.
- **Status:** LOW PRIORITY

### 21. Fly.io Standard Support Expired
- **Source:** team@news.fly.io — 4/4 (3-day warning), 4/7 (expired)
- **What:** 30-day Standard email support trial ended.
- **Action:** Evaluate if paid support is needed for any deployed services. If no active Fly.io workloads, ignore.
- **Status:** FYI

### 22. Spectrum Free Trial Ended
- **Source:** spectrum@exchange.spectrum.com — 4/1
- **What:** Trial expired. Offer available through 5/8.
- **Action:** Decide if Spectrum service is needed.
- **Status:** LOW PRIORITY

### 23. Instacart+ Membership Confirmed
- **Source:** no-reply@instacart.com — 4/3
- **What:** Paid membership started.
- **Action:** FYI. Monitor if being used enough to justify cost.
- **Status:** FYI

---

## SECURITY & DEVTOOLS

### 24. Banking & Plaid Connections (3/30)
- **Source:** Santander, Plaid, Flowery NY — 3/30 (cluster of 10+ messages)
- **What:** Card PIN change, Apple Pay setup, multiple Plaid bank connections to Dutchie, and Flowery NY verification codes.
- **Action:** Verify all these connections were intentionally initiated by you. If not, secure accounts immediately.
- **Status:** VERIFY

### 25. GitGuardian Secrets Webinar
- **Source:** dwayne.mcdaniel@gitguardian.com — 4/1
- **What:** Live webinar: "The State of Secrets Sprawl 2026" expert panel.
- **Action:** Register if interested. Relevant to Docker Hub key exposure (item #2) and overall security posture.
- **Status:** OPTIONAL

### 26. Google Next Digital Access
- **Source:** nextsupport@google.com — 4/10
- **What:** Digital version available to stream select sessions live.
- **Action:** Register for streaming if interested in Google Cloud content.
- **Status:** OPTIONAL

### 27. GitHub Copilot Quota Refreshed
- **Source:** no-reply@github.com — 3/29
- **What:** Monthly request quota reset.
- **Action:** None required. FYI.
- **Status:** FYI

---

## NOISE — No Action Required

Newsletters archived (no action): Built In (x2), Socket Weekly (x2), CodeRabbit (x2), OpenAI Dev News, Termius, GitKraken (x2), Trunk, Vercel, Ghost (x2), GitBook, Google Cloud (x2), Audible Genius, Airtable, Udemy (x2), Cluing 2.0

Marketing/promo archived: Sniffies (x3+), Columbus Circle (x2), DSW VIP, Timberland, Holman Honda, Letterboxd (x2+), Ableton, Netflix, Patreon AAMON HAWK, GrowHealthy FL, Dutchie (transactional noise)

Entertainment: Radiohead/WASTE HQ (x2), Louis C.K. Netflix/Hollywood Bowl

Social: LinkedIn impressions (x2)

---

## Summary by Priority

| Priority | Count | Key Items |
|----------|-------|-----------|
| **CRITICAL** | 3 | Deposition prep (today+), API key exposure, student loan default |
| **FINANCE** | 6 | Cash App, overdraft, Zip collection, tax return, statements, PayPal |
| **PIPELINE** | 6 | Cloudflare rejection, Grafana rejection, Webflow ack, Awesome NYC, job listings, GitHub billing |
| **OUTREACH** | 3 | Becka McKay reply, SWARMs inquiry, tribecode PR |
| **SUBSCRIPTIONS** | 5 | LinkedIn renewal (4/18), Verizon, Fly.io, Spectrum, Instacart+ |
| **SECURITY** | 4 | Plaid connections verify, GitGuardian webinar, Google Next, GitHub quota |
| **NOISE** | ~50 | Newsletters, marketing, entertainment |

**Total actionable items: 27**
**Noise dismissed: ~50 threads**
