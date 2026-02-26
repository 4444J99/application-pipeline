---
title: "Omni-Dromenon Engine"
category: projects
tags: [performance, audience-participation, generative-art, creative-coding, websocket, typescript, supercollider, osc]
identity_positions: [systems-artist, creative-technologist]
tracks: [grant, residency, fellowship, prize]
related_projects: [generative-music, organvm-system]
tier: full
---

# Project: Omni-Dromenon Engine

## One-Line
Real-time audience-participatory performance engine with weighted consensus and performer override authority.

## Short (100 words)
Omni-Dromenon is an open-source performance engine where audience members control continuous parameters — mood, tempo, intensity, texture — via phones. Inputs aggregate through three-axis weighted consensus: spatial proximity, temporal recency, and cluster agreement. Performers retain graduated override (absolute, blend, lock). Genre presets for ballet, electronic music, opera, installation, and theatre encode aesthetic priorities about what matters most in each form's audience-performer relationship. TypeScript pnpm monorepo with Express/Socket.io core, React performer and audience interfaces, OSC bridge to SuperCollider/Max/MSP, four working examples, and Docker infrastructure. Designed for 1,000+ concurrent audience members at <2ms P95 latency.

## Full
The engine consists of five packages:

- **Core Engine** — Express + Socket.io server with two WebSocket namespaces (/audience, /performer). Implements three-axis weighted consensus algorithm, parameter bus with 16 event types, outlier rejection via z-score filtering, exponential smoothing, and OSC bridge.
- **Performance SDK** — React 18 component library: audience sliders, voting panel, performer dashboard with live parameters, override panel (absolute/blend/lock modes), performer status.
- **Audio Synthesis Bridge** — OSC gateway to SuperCollider/Max/MSP + WebAudio API for browser-native synthesis. Parameter mapping from consensus values to synthesis controls.
- **Client SDK** — Lightweight WebSocket client for third-party integration.
- **Orchestrate** — Python multi-AI orchestration CLI with gated pipeline.

Four working examples: generative music (SuperCollider via OSC), generative visual (WebGL shaders), choreographic interface (pose detection + movement mapping), theatre dialogue (branching narrative engine).

Five genre presets: Electronic Music (temporal 0.5), Ballet (spatial 0.5), Opera (consensus 0.5), Installation (spatial 0.7), Theatre (balanced 0.4/0.3/0.3).

Infrastructure: Docker Compose, Redis, ChromaDB, Nginx, GCP/Terraform. 200+ docs files including manifestos, deployment playbooks, festival rider, collaboration agreements.

## Links
- Repository: https://github.com/organvm-ii-poiesis/metasystem-master
- Portfolio: https://4444j99.github.io/portfolio/
- System Hub: https://github.com/meta-organvm
