# Application Pipeline Memory

## User
- [Engineering timeline](user_engineering_timeline.md) — 15 years (2011–present), not 6. First website with unnamedplay-r/etceter4.

## User Preferences
- When listing pipeline entries (batch lists, top entries, etc.), **always include the application URL** from `target.application_url`
- Resume batches go to `materials/resumes/batch-NN/`; current batch is `batch-03`
- PDF build via `python scripts/build_resumes.py` (headless Chrome); all resumes must be exactly 1 page
- Wire resumes to pipeline YAML via `python scripts/tailor_resume.py --target <id> --wire`

## Market Intelligence System (added 2026-03-01)
- `strategy/market-intelligence-2026.json` — master data artifact; 112 sources; review by 2026-06-01
- `strategy/market-research-corpus.md` — annotated bibliography (126 sources across 7 categories)
- `scripts/market_intel.py` — CLI; flags: `--track`, `--calendar`, `--salary`, `--skills`, `--channels`, `--sources`, `--staleness`
- Quick command: `python scripts/run.py market`
- `standup.py --section market` — shows conditions + hot skills + upcoming grant deadlines
- `score.py` loads portal friction scores + strategic base from JSON at runtime (via `get_portal_scores()` / `get_strategic_base()`)
- `followup.py` loads PROTOCOL timing from JSON via `load_protocol_from_market_intel()`
- `standup.py` loads stale thresholds from JSON via `_get_stale_threshold()`
- All scripts fallback to hardcoded defaults if JSON missing — no breaking changes

## Key 2026 Market Data Points (Precision-Over-Volume Era)
- Tech layoffs YTD: 51,330 (856/day); cold app viability: LOW
- Referral multiplier: 8x; tailored cover letter: +53% callback; follow-up: +68% offers
- **Precision mode**: max 1-2 apps/week, min score 7.0 (recalibrated 2026-03-15 from 9.0), network_proximity >= 5 preferred
- Daily split: 2hr research, 2hr relationships, 1hr application work
- Max 10 active entries; max 1 per org (COMPANY_CAP=1)
- AI content rejection: 62% (generic), 80% (robotic)
- Hot skills: go (+41%), kubernetes, terraform, platform-engineering, mcp, agentic-workflows
- **Active deadlines (verified 2026-03-31)**: ZKM Rauschenberg 2026-04-12 (reactivated to drafting), LACMA Art+Tech rolling (drafting). Creative Capital CLOSED. NLnet ARCHIVED (0/89 past winners had governance tools). Headlands + Google Fellowship EXPIRED. Sovereign Tech Fellowship was phantom — no pipeline entry ever existed. Track via `python scripts/run.py market --calendar`
- Scoring threshold crisis RESOLVED 2026-03-15: 9.0→7.0. See [freshness gate memory](project_freshness_gate_2026-03-15.md).

## Block Metrics Hygiene (updated 2026-04-02)
- Canonical values: 113 repos, 739K words, 48 essays, 23,470 tests (system-wide), ~3,423 tests (pipeline-specific, per S46 handoff), 33 sprints
- Pipeline now has 171 scripts and 182 test files (was "160+" and "100" in CLAUDE.md — verify before next CLAUDE.md edit)
- `python scripts/check_metrics.py` validates 168 files; run before any submission batch
- Common false positives to watch: per-organ test counts ("1,254 automated tests" for ORGAN-I),
  subset repo refs ("70 repositories" when meaning "70 of 103"), document paths ("10-repository-standards"),
  table cell values with "Meta" prefix
- Fix pattern: reword to use "of N" subset notation or replace "automated tests" with "test cases"
- `blocks/identity/5min.md` — core identity block; watch test_count (canonical 2,349)
- `blocks/framings/software-engineer-at-organvm.md` — jobs framing; watch total_repos phrase form

## Follow-up System State (snapshots — run `standup --section followup` for current)
- 30 overdue follow-up actions across 24 submitted entries (snapshot: 2026-03-30 morning digest)
- 12 new contacts logged 2026-03-28 (verified, with LinkedIn URLs, role-aligned)
- 114 contacts in contacts.yaml (3,329 lines), 316 outreach-log entries (verified 2026-04-02)
- Protocol: connect Day 1-3, DM Day 7, final follow-up Day 14
- Network: 182 nodes, 182 edges, 153 dormant, 0 very_strong — wide but paper-thin (snapshot: 2026-03-28)
- **Pipeline state (2026-04-02):** 60 active, 22 submitted, 1,694 research_pool, 300 closed

## Job Entry Patterns (updated 2026-03-01)
- Auto-sourced job entries often get `resumes/independent-engineer-resume.html` as a dangling reference
  when `tailor_resume.py --wire` appends batch-03 resume without removing old reference
- Fix: remove dangling line from YAML `submission.materials_attached` list
- Cohere Applied AI (Korea/Singapore) batch-03 resumes built 2026-03-01 (1-page, agentic-workflows focus)

## Feedback
- [Additive design](feedback_additive_design.md) — Each prompt adds complexity; never simplify or replace prior layers
- [Data hygiene](feedback_data_hygiene.md) — Dynamic data (recomputable) vs observation data (system's diary). Never delete observations.
- [Cover letter quality](feedback_cover_letter_quality.md) — SUPERSEDED by unified rules below. Kept for historical reference only.
- [Unified resume/CL rules](feedback_resume_cover_letter_quality_2026-03-26.md) — 550-700 words, ORGANVM employer, vertical layout, triple layer, all rules consolidated
- [Fix bases not outputs](feedback_base_not_output.md) — Modify base templates, never patch historical batch-NN outputs
- [Outreach: new contacts only](feedback_outreach_new_contacts.md) — Never recycle already-contacted people into outreach plans. Research fresh contacts per submission.
- [Never defer to human](feedback_never_defer_to_human.md) — The human is the conductor. Never ask them to run CLI commands, set passwords, or do mechanical work the system can do programmatically.
- [No skips, no N/A](feedback_no_skips_no_na.md) — Every index check produces DONE or VACUUM. "Skip" and "N/A" are forbidden — they are vacuums disguised as decisions. Water constantly flowing.
- [Log tool fixes](feedback_log_tool_fixes.md) — When fixing bugs or building tools, log what changed. Don't silently fix things.
- [Building for others fortifies](feedback_building_for_others.md) — Solving their problems > solves ours higher. Every venture hardens the studio. Explore every path.
- [IRA model limits](feedback_ira_model_limits.md) — Never send full CLAUDE.md to Haiku. Sonnet minimum, or break evidence into chunks.
- [Never list commands](feedback_never_defer_commands.md) — Never present commands for the user to run. Run them all automatically.
- [Rules are ADDITIVE](feedback_rules_are_additive.md) — New rules amend, never overwrite. All existing rules remain in force unless explicitly revoked.
- [Gemini collaboration](feedback_gemini_collaboration.md) — Net negative for this repo. No persistent memory = violates unseen rules. Stateless tasks only.
- [Validate before shipping](feedback_validate_before_shipping.md) — Every generated artifact needs post-generation validation. Never ship and hope.
- [Loops are physics](feedback_loops_are_physics.md) — 10 loops are the universal execution model, not pipeline-specific. Energy in → transform → output → feedback. PUBLISH (2%) is the critical underinvestment. Every system, repo, venture maps to this.
- [Multi-agent post-mortem](feedback_multi_agent_postmortem_2026-03-30.md) — First parallel run: Codex 9, Gemini 7, OpenCode 6. Prompt precision prevents drift. Compile check in every edit prompt. Constrain test scope. Pre-scan file manifests. Model selection matters for Scouts.
- [Memory parity](feedback_memory_parity.md) — `(local):(remote)={1:1}`. All persistent state must exist both locally and on remote. If physical dies, soul persists. Verify on every session close.
- [Memory reconciliation](feedback_memory_reconciliation.md) — Memory is hypothesis, not fact. Load → identify claims → verify against reality → present delta. Never recite stale state.
- [Session handoff protocol](feedback_session_handoff_protocol.md) — Every non-trivial session must write a handoff file (`.claude/plans/{date}-session-handoff-{id}.md`). Not a summary — a context injection. Contains: what happened, user state, decisions, artifacts, hanging actions, what next session must know. Separate from avalanche (task chain).

## Project Memories
- [System Purpose](project_system_purpose.md) — Core mission: Scan → Match → Build → Apply → Follow up. Everything else is armor plating.
- [Colossal Triage 2026-03-13](project_triage_2026-03-13.md) — Major pipeline triage, scoring threshold crisis, health 5.2→7.2
- [Freshness Gate & Scoring Recalibration 2026-03-15](project_freshness_gate_2026-03-15.md) — Auto 72h flush, threshold 9.0→7.0
- [Session 2026-03-15](project_session_2026-03-15.md) — Corpus fingerprint, browser submit, 142/142 test coverage, evaluation-to-growth
- [Ecosystem Integration 2026-03-15](project_ecosystem_integration_2026-03-15.md) — Snapshot, 9 positions, auto-classify, engagement data, stakeholder portal
- [Identity Reframe 2026-03-15](project_identity_reframe_2026-03-15.md) — 80K files, 70% docs, documentation-engineer is the lead position not independent-engineer
- [Portfolio Blockers](project_portfolio_blockers.md) — Security audit blocks Plausible deploy (RESOLVED — Plausible now working)
- [Network Graph & Outreach 2026-03-17](project_network_graph_2026-03-17.md) — network_graph.py, 39 LinkedIn contacts, Granovetter scoring, wired into score_network.py
- [Session 2026-03-17/18](project_session_2026-03-17.md) — 7 applications, 52 outreach, 5 features automated, materials reorg, identity reframe
- [Open Source Testament 2026-03-19](project_open_source_testament_2026-03-19.md) — `context[current-work] > relevant[open-source]`, 42 target repos across 5 organs, AdenHQ/Hive first contribution in progress
- [Session Arc 2026-03-18/20](project_session_2026-03-18-20.md) — 43 commits, 169 outreach, intake pipeline fix (902 hidden gems), OSS testament, daily automation, 149/149 verification
- [Tony Carbone / Alt Funding Group](project_tony_carbone_altfunding_2026-03.md) — Inbound consulting lead, 40-min call, 5 workstreams (MCA + Flyland.com healthcare SaaS), awaiting follow-up
- [Consulting Pivot 2026-03-23](project_consulting_pivot_2026-03-23.md) — Tony (client) + Scott Lefler (build+sell partner) converging same week. Jobs = weakest link. Scrapper repo is bridge.
- [Session Arc 2026-03-21/23](project_session_2026-03-21-23.md) — 7 PRs across 7 OSS repos, 30 outreach, 8 contribution workspaces, Hive fusion architecture, Matthew Diakonov reciprocal
- [Outreach Data Gap 2026-03-24](project_outreach_data_gap_2026-03-24.md) — RESOLVED. log_dm.py + reconcile_outreach.py now operational.
- [Three-Pillar Strategy 2026-03-24](project_three_pillar_strategy_2026-03-24.md) — Jobs (runway) + Grants (validation) + Consulting (bridge to studio). Pipeline 90% optimized for jobs, needs rebalancing. Studio dream = Pixar/ILM built on ORGANVM.
- [Weekly Rhythm & Creation-First 2026-03-24](project_weekly_rhythm_2026-03-24.md) — Creation is the constant, pillars orbit it. Mon=jobs, Tue=grants, Wed=consulting, Thu/Fri=deep build. Daily artifact posting. Jobs ONLY on Monday.
- [Dustin Dipaulo Ventures 2026-03-24](project_dustin_dipaulo_ventures_2026-03-24.md) — 3 ventures: music DSP alternative, AI audit consulting, neurodivergent fashion. Peer co-creator.
- [Maddie Ventures 2026-03-24](project_maddie_ventures_2026-03-24.md) — 3 ventures: non-profit housing, water funnel (her domain, asked for help), atemporal atlas (Zelda-style layered maps). Awaiting her transcripts/voice notes.
- [Pillar 3 Full Network 2026-03-24](project_pillar3_full_network_2026-03-24.md) — 6 partners, 12+ ventures. Tony (fintech), Scott (design), Dustin (UI/UX), Maddie (water/housing), Rob (fitness/chess/HokageChess), Jessica (18K heartbreak audience + behavioral blockchain repo exists).
- [Session Arc 2026-03-25](project_session_2026-03-25.md) — 20+ commits, diagnostic 3.5→8.3, rubric refactor, apply.py built, 5 apps with API questions, repo reorg Phase 1.
- [Session Arc 2026-03-26/27](project_session_2026-03-26-27.md) — Materials Protocol (12 articles), repo reorg Phase 2, Gemini tested (net neg), 10 apps total, 12/12 compliance.
- [Session Arc 2026-03-28](project_session_2026-03-28.md) — CL template unified, resume CSS tuned, 5 quality gates added, 4 apps submitted, 12 verified contacts, Cursor deferred.
- [Triptych Architecture 2026-03-30](project_triptych_architecture_2026-03-30.md) — Aerarium (grants) + Pipeline (jobs) + Consulting = three faces, shared infra, distinct process. SOP-INST-001 applies to all three.
- [Quadrant-Mask-Content Loop 2026-03-30](project_quadrant_mask_content_loop_2026-03-30.md) — Every application = research = content feedstock. Q1→Narrator, Q2→Strategist, Q3→Architect, Q4→Integrator. Pipeline markets itself through its own operation.
- [Funder-Fit Lessons 2026-03-30](project_funder_fit_lessons_2026-03-30.md) — CC + NLnet both deferred. Gate works. 89 NLnet projects analyzed: 0 governance tools. Reframe Cvrsvs as seed.yaml spec or DAG validator or GH Action. Past Winners Analysis is a HARD GATE in Phase 1.
- [Session 2026-03-31](project_session_2026-03-31.md) — CLAUDE.md compression 43.7k→27.6k chars (37%), merged Commands/Quick Commands/CLI, restructured Script Dependency Graph, all behavioral rules preserved
- [Session S44 Audit 2026-03-31](project_session_2026-03-31-s44.md) — Hall-monitor audit: 4 violations found (5 memory files unsynced, IRF-DOM collision 019-022, orphaned script, formatting). All fixed.
- [Session S45 2026-03-31](project_session_2026-03-31-s45.md) — CRITICAL: freshness fix (99% false positive rate), triage 99→12, 3 apps built, health 7.0→9.0, Sovereign Tech phantom purged
- [First Interview — Grafana 2026-04-01](project_first_interview_grafana_2026-04-01.md) — Pipeline's first positive conversion. Staff AI Engineer, People Technology | NASA | Remote. Applied outside pipeline 2026-03-26, 5-day response, screen Mon 2026-04-06 10:30 AM EDT. Quicklog gap RESOLVED.
- [Session S46 2026-04-01](project_session_2026-04-01-s46.md) — quicklog.py built+wired, 5 IRF items (067+069 DONE), Grafana interview processing, 10-index propagation, scorecard 3.0→4.7
- [Session S54 2026-04-03](project_session_2026-04-03-s54.md) — Full triage recovery: health 8.2→9.2, 6 entries deferred, 7 follow-up closures, followup.py format bug fixed, memory parity restored (6 files), Grafana prep refreshed

## References
- [OpenClaw Gateway Setup](reference_openclaw_setup_2026-03-31.md) — OpenClaw v2026.3.28 at ~/.openclaw/, Ollama gateway port 18789, llama3.2:3b primary, no cloud auth
