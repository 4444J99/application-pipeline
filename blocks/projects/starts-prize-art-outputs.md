---
title: "ORGANVM Tier 1 Art Outputs (S+T+ARTS Prize)"
category: projects
tags: [performance, generative-art, supercollider, queer, audience-participation, creative-coding, installation]
identity_positions: [systems-artist, creative-technologist]
tracks: [prize]
related_projects: [omni-dromenon-engine, krypto-velamen, generative-music]
tier: full
---

# Art Outputs: ORGANVM Tier 1 Projects

The ORGANVM system produces four distinct art projects, each representing a different mode of art-technology convergence.

## Omni-Dromenon Engine: Consensus as Creative Medium

A real-time audience-participatory performance system where the audience becomes co-author. Audience members control continuous parameters — mood, tempo, intensity, texture — via mobile devices. These inputs aggregate through a three-axis weighted consensus algorithm: spatial proximity (closer audience members have more influence), temporal recency (recent inputs decay older ones), and cluster agreement (aligned inputs amplify each other). Performers retain graduated override authority — absolute, blend, or lock — preserving artistic agency within collective input.

The innovation is treating consensus itself as a creative medium. The negotiation between audience desire, algorithmic aggregation, and performer judgment produces emergent aesthetic outcomes that no single participant controls. Five genre presets — ballet, electronic music, opera, installation, theatre — encode different philosophies about the audience-performer relationship.

Built as a TypeScript monorepo: Express/Socket.io core, React interfaces, OSC bridge to SuperCollider/Max/MSP. Designed for 1,000+ concurrent participants at <2ms latency.

## Alchemical Synthesizer (Brahma Meta-Rack): Parasitic-Symbiotic Synthesis

A modular synthesis organism modeled on the Trimurti cycle — Brahma (genesis), Vishnu (sustenance), Shiva (dissolution). 66 SuperCollider files implement 10 synthesis engines spanning subtractive, additive, FM, granular, spectral, and physical modeling. The 7-stage signal path processes sound from genesis through transformation to dissolution and rebirth.

Generative systems — Lorenz attractors, Markov chains, cellular automata — drive emergent behavior. The organism model means the synthesizer has states analogous to metabolism, growth, and decay. Pure Data processes and spatializes. The p5.js Visual Cortex renders the organism's internal state in real time — not abstract visualization but a window into the synthesizer's living processes.

Three ports of OSC communication bind SuperCollider, Pure Data, and the web interface into a co-evolving feedback loop. The sound shapes the visual; the visual state feeds back into synthesis parameters.

## MET4MORFOSES: Ovid as Immersive Web Experience

An MFA thesis project that transforms Ovid's *Metamorphoses* into an 8-mode web experience: 3D node map (React Three Fiber), faux social media feed, scrolling literary experience, AI oracle, generative audio (GlitchSynth), and spatial navigation. The content pipeline ingests PDFs of the original text and critical apparatus, then distributes them across interaction modes.

Each mode offers a different relationship to the same source material — navigating the mythic network spatially, encountering fragments as social media posts, listening to generated soundscapes, or consulting an AI trained on the text. The metamorphosis isn't just the subject; it's the form. The work itself shape-shifts depending on how you enter it.

## KRYPTO-VELAMEN: Queer Literary Archive as Living System

A distributed queer literary archive built on the principle that concealment is a compositional engine, not biographical background. The project studies how queer writers from Rimbaud (1871) to Porpentine (2010s) encode desire through what it calls "Double-Channel Text" — surface story and substrate story running simultaneously.

A 9-variable encoding schema formalizes concealment strategies into calibratable parameters: Rimbaud Drift (sensory overload as camouflage), Wilde Mask (performative surface protecting interior truth), Burroughs Control (structural disruption as encoding), Lorde Voice (direct naming as political act), Arenas Scream (baroque excess as resistance to erasure), and Acker Piracy (appropriation to inscribe queer presence).

The platform architecture — 8 microservices, Neo4j knowledge graph (106 entities, 118 relations), AI agent swarm — centers community safety through pseudonym management and risk-calibrated privacy. The archive is designed to grow: an evolving, non-linear documentation of queer interiority that refuses narrative closure or moral framing.
