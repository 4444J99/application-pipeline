---
title: "Verifiable news ledger platform"
category: projects
tags: [ai, ci-cd, database, developer-tools, docker, microservices, platform, testing, typescript]
identity_positions: [creative-technologist, independent-engineer]
tracks: [job]
tier: full
review_status: auto-generated
stats:
  languages: [typescript]
  ci: true
  public: true
  promotion_status: CANDIDATE
  relevance: HIGH
---

# Project: Verifiable news ledger platform

## One-Line
Verifiable news ledger platform — news as a public service

## Short (100 words)
Verifiable news ledger platform — news as a public service. Part of ORGAN-III (Ergon).

## Full
**Technical Architecture:** The platform is a TypeScript monorepo managed with pnpm workspaces, organized into five backend microservices, a Next.js frontend application, and a shared contracts layer. ``` ┌──────────────────────────────────────────────────────────────┐ │ User Surfaces │ │ ┌──────────┐ ┌──────────────┐ ┌─────────────────┐ │ │ │ Reader │ │ Verifier │ │ Publisher │ │ │ │ (Web) │ │ (Web) │ │ (Web) │ │ │ └────┬──────┘ └──────┬───────┘ └───────┬──────────┘ │ │ │ │ │ │ └───────┼──────────────────┼────────────────────┼───────────────┘ │ │ │ ▼ ▼ ▼ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ │ Gateway │ │ Verify │ │ Story │ │ BFF :8080 │ │ :8084 │ │ :8081 │ └──────┬───────┘ └──────┬───────┘ └──────┬───────┘ │ │ │ ├──────────────────┼───────────────────┤ │ │ │ ▼ ▼ ▼ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ │ Claim │ │ Evidence │ │ PostgreSQL │ │ :8082 │ │ :8083 │ │ :5432 │ └──────────────┘ └──────────────┘ └──────────────┘ ``` ### Services | Service | Port | Responsibility | |---------|------|----------------| | **Gateway** | 8080 | Public-facing BFF (Backend for Frontend). Serves the feed, individual story bundles, and the publish endpoint. Implements the full publish gate algorithm in a single transactional SQL query. | | **Story** | 8081 | Story CRUD operations — create, update, version management. Handles the draft/review/published state machine. | | **Claim** | 8082 | Claim extraction from narrative text. Interfaces with the model gateway for automated claim identification. | | **Evidence** | 8083 | Evidence object registration. Computes content hashes, validates provenance metadata, and stores content-addressed objects. | | **Verify** | 8084 | Verification task management. Generates review tasks for evidence gaps, collects structured verdicts from reviewers. | ### Frontend Application The `apps/public-web/` directory contains a Next.js application providing three user-facing surfaces: - **Reader** (`/`) — Story feed ranked by quality signals, not engagement. Each story page displays the narrative with an expandable verification spine panel showing claims, evidence, and correction history. - **Verifier** (`/verify`) — Claim review queues, evidence gap alerts, and structured review submission forms. - **Story Detail** (`/story/[story_id]`) — Full story bundle display with claims, evidence edges, and corrections timeline. ### Event-Driven Pipeline State changes flow through a PostgreSQL-backed event outbox pattern: 1. **Ingest** — Evidence objects registered with content

## Links
- GitHub: https://github.com/organvm-iii-ergon/the-actual-news
- Organ: ORGAN-III (Ergon) — Commerce
