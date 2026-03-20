---
title: "I Built a Career Pipeline with 3,266 Tests"
published: false
tags: [career, python, systemdesign, productivity]
series: "Building in Public"
---

3,266 tests. 148 scripts. 123 CLI commands. One YAML file per job application.

This is how I job search now — and it's the most useful thing I've ever built.

## The Problem

Job searching is controlled chaos. You have a spreadsheet that lies to you. A Gmail thread with 47 tabs open. A resume you haven't updated since 2023. A LinkedIn message you meant to follow up on two weeks ago. A cover letter you copy-pasted and forgot to change the company name.

I spent four days in early 2026 submitting 60 cold applications. I got zero interviews.

That's when I stopped and built a system instead.

## The Solution

I built an application pipeline in Python — a CLI-first, YAML-driven, test-covered infrastructure for managing every stage of a job search as a structured conversion funnel.

Here's what it does:

- **148 scripts** (organized into 123 named CLI commands via `run.py`)
- **One YAML file per application** — company, role, deadline, score, materials attached, outreach log, state
- **A state machine** that enforces forward-only transitions: `research → qualified → drafting → staged → submitted → acknowledged → interview → outcome`
- **A 9-dimension scoring rubric** that must reach a minimum threshold before an entry can advance
- **A network graph** (168 nodes, 171 edges, 57 organizations) with BFS/DFS path-finding to find warm paths into target companies
- **A daily standup command** that surfaces stale entries, upcoming deadlines, follow-up actions, and campaign priorities
- **A conversion funnel** with analytics by channel, portal, position type, and score range
- **3,266 tests** — pytest, CI/CD gate on every push to main

The system tracks 209 outreach actions, 173 contacts in a built-in CRM, and a pipeline health score currently sitting at 8.2/10.

## The Architecture

### State Machine

Every application lives in a YAML file in `pipeline/active/`. The `advance.py` script enforces forward-only progression. You cannot skip from `drafting` to `submitted`. You cannot advance to `submitted` without at least one logged outreach action — a LinkedIn connection, an email, a referral ask.

This is intentional. Warm paths are not optional. The referral multiplier from market research is 8x hire rate compared to cold applications. That constraint is baked into the system.

### Scoring System (9 Dimensions)

Before anything enters the active pipeline as `qualified`, it gets scored across nine dimensions:

1. Technical fit
2. Identity alignment
3. Strategic value
4. Network proximity
5. Evidence match (TF-IDF against job description keywords)
6. Deadline urgency
7. Portal friction
8. Compensation range
9. Cultural alignment

The minimum threshold to advance: 7.0. Entries below that stay in `research_pool/` — a separate directory that holds hundreds of auto-sourced entries without polluting the active working set.

### Network Graph (Granovetter Weak-Ties Theory)

The `network_graph.py` module implements a weighted graph of professional relationships using BFS and DFS path-finding. Every edge has a tie strength (1-10). Scoring uses hop-decay — each additional degree of separation reduces the proximity score by a configurable decay factor, implementing Granovetter's weak-ties theory: loose connections are often more valuable than strong ones because they bridge otherwise disconnected networks.

When I score an application, the `score_network.py` module queries this graph for the shortest path to the target organization and feeds the result into the `network_proximity` dimension. 57 organizations are currently in the graph, spanning direct connections to third-degree paths.

### Recruiter Filter

Before any submission, `submit.py` runs a pre-flight check that validates:

- All metrics in the cover letter and resume match canonical values in `check_metrics.py`
- No stale materials attached (materials must be within freshness threshold)
- At least one outreach action logged for this entry
- The cover letter is present and non-empty
- The tailored resume exists in the current batch directory

This is the recruiter filter. Nothing submits until it passes.

## What I Learned

### Precision Beats Volume

60 cold applications in four days gave me zero interviews. That was the data. The system now enforces a maximum of 1-2 applications per week, with a minimum of one outreach action before submission. Slower, warmer, higher signal.

### The System Is the Portfolio

The pipeline has 3,266 tests. Most production applications I've worked on don't have 3,266 tests. The architecture itself — state machines, dependency injection, modular CLI design, inter-rater agreement for quality scoring, external API validation against BLS salary data — is a demonstration of how I think about systems.

When a hiring manager asks "show me something you've built," this is what I show them.

### Documentation Is the Product

I spent seven years teaching 2,000+ students across composition, creative writing, and technical communication. The MFA in Creative Writing and the decade of documentation work aren't a detour from software — they're the discipline.

The blocks system at the core of this pipeline mirrors how I taught writing: modular, reusable units at four depth tiers (60-second, 2-minute, 5-minute, cathedral). Every application is a composition problem. Every block is a paragraph pattern.

Documentation architecture is not a career pivot. It's the same skill at a different resolution.

### Granovetter Was Right

The network graph has returned more value than any job board. 13 LinkedIn connection requests accepted out of 169 sent (8.7%) in a 36-hour window. Every accepted connection is a node in the graph. Every second-degree path to a target company raises the network proximity score and reduces the activation energy for a warm introduction. The math works. Build the graph.

## The Numbers

What the pipeline actually tracks right now:

- **209 outreach actions** logged (LinkedIn connects, DMs, email introductions, referral asks)
- **173 contacts** in the built-in CRM with tie-strength ratings
- **13 acceptances in 36 hours** from 169 connection requests (8.7% acceptance rate)
- **8.2/10 health score** (composite across 9 system-quality dimensions)
- **3,266 tests** in pytest with CI/CD gate on every push

The pipeline runs five LaunchAgents on my local machine: daily deferred-entry check at 6:00 AM, pipeline monitor at 6:30 AM, weekly backup at 2:00 AM Sunday, biweekly agent run Monday/Thursday, weekly brief Sunday evening.

## Try It

The portfolio and full case study live at [anthonypadavano.com/portfolio](https://anthonypadavano.com/portfolio). The pipeline architecture is the first case study in a series on building institutional-scale systems as a solo practitioner.

Source on GitHub: [github.com/4444j99](https://github.com/4444j99)

---

If you've built anything like this — or tried to — I'd be curious what you automated first. For me it was the standup report. Turned out knowing what was stale every morning was more valuable than the submission itself.
