---
title: "Omni-Dromenon Engine"
category: projects
tags: [ai, api, audio, blockchain, creative-coding, database, docker, generative-art, orchestration, osc, performance, python, react, supercollider, testing, typescript, websocket]
identity_positions: [community-practitioner, creative-technologist, systems-artist]
tracks: [grant, residency, fellowship, prize]
related_projects: [organvm-system, recursive-engine]
tier: full
review_status: auto-generated
---

# Project: Omni-Dromenon Engine

## One-Line
Omni-Dromenon Engine — canonical monorepo for ORGAN-II.

## Short (100 words)
Omni-Dromenon Engine — canonical monorepo for ORGAN-II. Real-time performance system consolidating 12 repos: core-engine, performance-sdk, client-sdk, audio-synthesis-bridge, orchestrate CLI, 4 examples, extensive docs. Artistic Purpose | Conceptual Approach | System Architecture | Package Reference | Installation | Quick Start | Working Examples | API Reference | Configuration Deep Dive | Theory Implemented | Portfolio & Exhibition | Cross-References | Contributing | License & Author Part of ORGAN-II (Poiesis).

## Full
**System Architecture:** ### Three-Layer Design ``` ┌─────────────────────────────────────────────────────────────────┐ │ NGINX REVERSE PROXY │ │ (infra/nginx/nginx.conf) │ ├──────────────────────┬──────────────────────────────────────────┤ │ │ │ │ ┌───────────────────▼──────────────────┐ │ │ │ CORE ENGINE (Port 3000) │ │ │ │ packages/core-engine/ │ │ │ │ │ │ │ │ ┌──────────┐ ┌──────────────────┐ │ ┌───────────────┐ │ │ │ │ Express │ │ Socket.io │ │ │ Redis 7 │ │ │ │ │ REST API │ │ /audience ns │ │◄──│ Session State │ │ │ │ │ │ │ /performer ns │ │ │ (Port 6379) │ │ │ │ └────┬─────┘ └──────┬───────────┘ │ └───────────────┘ │ │ │ │ │ │ │ │ │ ┌────▼───────────────▼───────────┐ │ ┌───────────────┐ │ │ │ │ PARAMETER BUS │ │ │ ChromaDB │ │ │ │ │ Event-driven pub/sub │ │ │ Vector Store │ │ │ │ │ (src/bus/parameter-bus.ts) │ │◄──│ Long-term │ │ │ │ └────────────┬───────────────────┘ │ │ Memory │ │ │ │ │ │ │ (Port 8000) │ │ │ │ ┌────────────▼───────────────────┐ │ └───────────────┘ │ │ │ │ CONSENSUS AGGREGATOR │ │ │ │ │ │ Weighted voting + smoothing │ │ │ │ │ │ Cluster analysis + outliers │ │ │ │ │ │ (src/consensus/*.ts) │ │ │ │ │ └────────────┬───────────────────┘ │ │ │ │ │ │ │ │ │ ┌────────────▼───────────────────┐ │ │ │ │ │ OSC BRIDGE │ │ │ │ │ │ SuperCollider / Max/MSP │ │ │ │ │ │ (src/osc/osc-bridge.ts) │ │ │ │ │ └────────────────────────────────┘ │ │ │ └───────────────────────────────────────┘ │ │ │ │ ┌───────────────────────────────────────┐ │ │ │ PERFORMANCE SDK (Port 3001) │ │ │ │ packages/performance-sdk/ │ │ │ │ │ │ │ │ React 18 + Vite + Socket.io-client │ │ │ │ ┌──────────────┐ ┌────────────────┐ │ │ │ │ │ Audience UI │ │ Performer │ │ │ │ │ │ Sliders, │ │ Dashboard, │ │ │ │ │ │ Voting Panel │ │ Override Panel │ │ │ │ │ └──────────────┘ └────────────────┘ │ │ │ └───────────────────────────────────────┘ │ │ │ │ ┌───────────────────────────────────────┐ │ │ │ AUDIO SYNTHESIS BRIDGE │ │ │ │ packages/audio-synthesis-bridge/ │ │ │ │ │ │ │ │ OSC Server + WebAudio

## Links
- GitHub: https://github.com/organvm-ii-poiesis/metasystem-master
- Organ: ORGAN-II (Poiesis) — Art
