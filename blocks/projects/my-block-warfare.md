---
title: "TurfSynth AR"
category: projects
tags: [ai, api, ci-cd, database, developer-tools, game-design, nlp, platform, react, testing, typescript, websocket]
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

# Project: TurfSynth AR

## One-Line
TurfSynth AR — location-based game with environmental synthesis and procedural creature generation

## Short (100 words)
TurfSynth AR — location-based game with environmental synthesis and procedural creature generation. A location-based augmented reality game where your real-world neighborhood procedurally generates the game around you. TurfSynth AR merges open-world turf dynamics with creature collection and environmental synthesis. Instead of overlaying static content onto the real world the way existing location-based games do, TurfSynth extracts compact "Place Fingerprints" from camera, microphone, and sensor data, then uses those fingerprints to procedurally generate creatures, soundscapes, visuals, and mission flavor that are unique to every block.

## Full
**Product Overview:** ### The Problem Location-based games today overlay static, artist-authored content on top of the real world. Every player who visits the same spot sees the same gym, the same spawn, the same assets. The world itself contributes nothing to the experience. Environmental context -- color, sound, geometry, motion, time of day -- is completely ignored. ### The Approach TurfSynth AR introduces **environmental synthesis**: the player's actual surroundings become the creative engine. On-device pipelines extract a compact "Place Fingerprint" (a privacy-preserving feature vector under 400 bytes) from camera frames, ambient audio, motion sensors, and GPS locality. That fingerprint drives procedural generation of collectible creatures ("Synthlings"), ambient soundscapes, visual themes, and mission parameters. No raw camera or audio data ever leaves the device. The game layer on top of this synthesis engine is a **turf-control system** where neighborhoods are divided into H3 hexagonal cells grouped into districts. Players form crews, earn influence through exploration and combat, deploy outposts, and execute asynchronous raids to contest territory. Influence decays over time, so holding turf requires continuous play rather than a one-time capture. ### The Outcome A location-based game where every block sounds and looks like itself, every player's creature collection reflects the places they have actually visited, and neighborhood pride becomes a literal game mechanic. The result is a system where the real world and the game world are coupled at a level of specificity that no existing title achieves. ### Player Fantasy You are a "Mapper" who samples reality to produce a personalized, stylized underworld layer: graffiti sigils, neon signage, ambient beats, faction banners, procedural creatures, and mission set dressing -- all generated from your surroundings without requiring artists to hand-author every block of every city. ---

**Technical Architecture:** ### System Topology ``` ┌─────────────────────────────────────────────────────────────────┐ │ Unity Client │ │ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ │ │ │ AR Session │ │ Fingerprint │ │ Turf │ │ │ │ Manager │ │ Capture │ │ Display │ │ │ └──────────────┘ └──────────────┘ └──────────────┘ │ └───────────────────────────┬─────────────────────────────────────┘ │ REST API (shared/api-types.ts) ┌───────────────────────────┴─────────────────────────────────────┐ │ Node.js Backend (Fastify 5) │ │ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ │ │ │ Geofencing │ │ Fingerprint │

## Links
- GitHub: https://github.com/organvm-iii-ergon/my-block-warfare
- Organ: ORGAN-III (Ergon) — Commerce
