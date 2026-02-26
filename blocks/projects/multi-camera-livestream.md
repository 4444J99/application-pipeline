---
title: "Multi-camera livestream production platform"
category: projects
tags: [ai, ci-cd, developer-tools, platform, testing, typescript]
identity_positions: [creative-technologist, independent-engineer]
tracks: [job]
tier: full
review_status: auto-generated
---

# Project: Multi-camera livestream production platform

## One-Line
Multi-camera livestream production platform

## Short (100 words)
Multi-camera livestream production platform. Professional multi-camera 4K live streaming pipeline with Dante audio synchronization. Open documentation. Any budget. $3K to $50K+ | macOS + Apple Silicon | Dante Audio Sync | 4 Tested Profiles | Quick Start | Profiles | Why This Exists Part of ORGAN-III (Ergon).

## Full
**The Problem This Framework Solves:** Every multi-camera streaming guide ends the same way: "...and then figure out audio sync yourself." You have spent thousands on cameras, capture hardware, and a capable Mac. OBS is installed. Dante Controller is open. The hardware is physically connected. Now what? - How do you route Dante audio into OBS without drift? - Why is audio three frames behind video after twenty minutes? - What encoder settings prevent the stream from dying mid-event? - How does a volunteer operator reproduce your exact setup next week? - Where is the single document that ties cameras, audio network, encoding, and streaming into one coherent pipeline? That document does not exist. Until now. ### What Is Missing from Existing Solutions | Problem | Existing Resources | This Framework | |---|---|---| | Hardware selection for a specific budget | Scattered forum posts | 4 tested profiles ($3K to $50K+) with full BOMs | | Dante audio routed into OBS | Fragmented guides across 3 vendors | Complete clock-locked architecture with signal flow diagrams | | Audio-video synchronization over long broadcasts | "Good luck" | Global sample clock via Dante, measured drift <50ms over 1 hour | | Volunteer operator handoff | "Watch this 45-minute video" | 8-phase runbook with decision-tree troubleshooting | | Reproducible streaming setup for academic citation | Nothing | BibTeX-ready, version-locked, config-as-code profiles | | Pre-stream system validation | Manual checklists | Automated health-check scripts with JSON output | ### How This Framework Differs from Products | Capability | ATEM Mini | vMix | OBS Alone | This Framework | |---|---|---|---|---| | Audio synchronization | HDMI embedded only | Windows audio stack | Manual configuration | Dante global clock | | Budget flexibility | Fixed hardware tier | Fixed software license | Unknown starting point | 4 documented profiles | | Operational documentation | Product manual | Tutorial videos | Community wiki fragments | 95% operational coverage | | Volunteer-ready operation | "Watch the video" | "Watch the video" | "Figure it out" | 8-phase runbook | | Reproducible configuration | "Buy same hardware" | "Same version" | No mechanism |

## Links
- GitHub: https://github.com/organvm-iii-ergon/multi-camera--livestream--framework
- Organ: ORGAN-III (Ergon) — Commerce
