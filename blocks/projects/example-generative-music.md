---
title: "Generative music example"
category: projects
tags: [creative-coding, generative-art, music, osc, supercollider, testing, typescript, websocket]
identity_positions: [community-practitioner, creative-technologist, systems-artist]
tracks: [grant, residency, fellowship]
related_projects: [metasystem-master]
tier: full
review_status: auto-generated
stats:
  languages: [typescript]
  ci: true
  public: true
  promotion_status: CANDIDATE
  relevance: HIGH
---

# Project: Generative music example

## One-Line
Generative music example

## Short (100 words)
Generative music example. A reference implementation of audience-controlled generative music synthesis, demonstrating how collective human input can drive real-time algorithmic composition through weighted consensus. This repository is part of ORGAN-II (Poiesis) — the art and creative expression layer of the eight-organ system. It implements a complete audience participation platform where smartphone-wielding listeners collectively shape a live musical performance through four expressive parameters: mood, tempo, intensity, and density. A performer dashboard provides override authority, creating a negotiated creative space between crowd consensus and artistic direction. Part of ORGAN-II (Poiesis).

## Full
**Technical Overview:** The system is a Node.js WebSocket server with two browser-based clients: an audience interface and a performer dashboard. Audio synthesis happens client-side using Tone.js, meaning each audience member hears locally generated sound shaped by the collective state — there is no audio streaming, only parameter streaming. **Server** (`src/server/index.js`): Express + Socket.io server implementing the CAL. Runs a 20Hz state broadcast loop that continuously calculates weighted consensus from all connected audience inputs, applies smoothing interpolation, respects performer overrides, and broadcasts the unified state to all clients. Provides HTTP health and state inspection endpoints. **Audience client** (`src/public/client.js` + `index.html`): Mobile-optimized web interface with four touch-controlled parameter sliders (mood, tempo, intensity, density). Connects via WebSocket, sends parameter changes at up to 20Hz, receives state updates, and drives a Tone.js polyphonic synthesizer. Includes a canvas-based waveform visualizer with mood-responsive coloring and a collective state bar display showing the current consensus values. **Performer dashboard** (`src/public/performer.html`): Desktop-oriented control surface with per-parameter override sliders and toggle switches. Displays live statistics (audience count, latency, inputs per second, session duration) and current consensus values. Performer overrides take priority over audience consensus when activated.

**Architecture:** ``` ┌──────────────────────────────────────────────────────────────────┐ │ Audience (N devices) │ │ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ │ │ │ Phone A │ │ Phone B │ │ Phone C │ │ Phone N │ ... │ │ │ Touch UI │ │ Touch UI │ │ Touch UI │ │ Touch UI │ │ │ │ Tone.js │ │ Tone.js │ │ Tone.js │ │ Tone.js │ │ │ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ │ │ │ │ │ │ │ │ └──────────────┴──────┬───────┴──────────────┘ │ │ WebSocket │ (audience:input) │ │ ▼ │ │ ┌──────────────────────────────────────────────────────┐ │ │ │ CAL Server (Node.js + Socket.io) │ │ │ │ │ │ │ │ ┌─────────────────┐ ┌──────────────────────────┐ │ │ │ │ │ Input Buffer │──▶│ Weighted Consensus │ │ │ │ │ │ (Map per user) │ │ temporal_decay × │ │ │ │ │ └─────────────────┘ │ consensus_proximity │ │ │ │ │ └────────────┬─────────────┘ │ │ │ │ │ │ │ │ │ ┌─────────────────┐ │ │ │ │ │ │ Performer │──▶ Override ──▶│ │ │

## Links
- GitHub: https://github.com/organvm-ii-poiesis/example-generative-music
- Organ: ORGAN-II (Poiesis) — Art
