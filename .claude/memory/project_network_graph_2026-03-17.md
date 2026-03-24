---
name: Network Graph & LinkedIn Outreach Session
description: Built network_graph.py (Granovetter weak-ties, BFS path-finding), 39 LinkedIn contacts across 14 companies, wired into scoring pipeline
type: project
---

Major session 2026-03-17: LinkedIn outreach + network graph implementation.

**Why:** Cold applications have 0.66% hire rate. Referrals are 7-15x more effective. The pipeline needed a network graph to model connections, find paths to target companies, and feed network_proximity scoring.

**How to apply:** Network graph is now a first-class pipeline subsystem. Use `netpath <org>` to find paths, `netscore <id>` for entry scores, `--sync-contacts` to keep contacts.yaml in sync.

## What was built

- `scripts/network_graph.py` — BFS/DFS path-finding, hop-decay scoring, tie-strength tracking
- `signals/network.yaml` — 42 nodes, 41 edges across 17 orgs
- `tests/test_network_graph.py` — 28 tests
- Theory: Granovetter (1973), Rajkumar et al. (2022 Science), referral decay model
- Hop scoring: 1-hop=8, 2-hop=6, 3-hop=4, cold=1, with strength/redundancy/density modifiers

## Integration points

- `score_network.py` → `_score_from_graph()` queries graph, combined via `max(entry_score, graph_score)`
- `validate_signals.py` → `validate_outreach_log()` + `validate_network()` added
- `followup.py` → fixed to search `ALL_PIPELINE_DIRS` (active+submitted+closed)
- `contacts.yaml` → synced from 2 to 41 contacts via `--sync-contacts`
- `run.py` → 5 new commands: network, netmap, netorgs, netpath, netscore
- `CLAUDE.md` → updated: script deps, 121 commands, config files, session sequences

## LinkedIn outreach batch

- 14 companies, 39 contacts, all sent 2026-03-17
- Strategy: multi-connect Tier 1 (2-3 per company), single Tier 2/3
- Premium trial active: unlimited personalized notes, 300-char limit, InMail
- Craig Dennis (Cloudflare DevRel) accepted + DM sent — only warm lead
- Exceptions: Bersabel Tadesse (left Figma), Elliot Plant (dead URL)

## Profile fortification (pending)

- 16 contact profiles researched — patterns documented
- Recommended headline: `Documentation Engineer & Systems Architect | 739K words | 113 repos | 100+ courses`
- Closest comp: Jamie Kosoy (Stripe) — creative coder who teaches with BFA
- User profile review blocked — need Chrome extension or paste of LinkedIn sections
