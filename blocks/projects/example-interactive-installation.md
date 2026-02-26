---
title: "Reference implementation for sensor-driven interactive art installations with..."
category: projects
tags: [ai, audio, creative-coding, docker, generative-art, osc, react, supercollider, testing, three-js, typescript, websocket]
identity_positions: [community-practitioner, creative-technologist, systems-artist]
tracks: [grant, residency, fellowship]
related_projects: [metasystem-master]
tier: full
review_status: auto-generated
stats:
  languages: [markdown]
  ci: true
  public: true
  promotion_status: CANDIDATE
  relevance: HIGH
---

# Project: Reference implementation for sensor-driven interactive art installations with...

## One-Line
Reference implementation for sensor-driven interactive art installations with depth cameras, LIDAR, and spatial audio

## Short (100 words)
Reference implementation for sensor-driven interactive art installations with depth cameras, LIDAR, and spatial audio. Artistic Purpose | Conceptual Approach | Technical Overview | Installation | Quick Start | Working Examples | Theory Implemented | Portfolio & Exhibition | Related Work | Contributing | License & Author Part of ORGAN-II (Poiesis).

## Full
**Technical Overview:** ### System Architecture ``` ┌─────────────────────────────────────────────────────────────────────┐ │ INSTALLATION HOST │ │ (Linux workstation, GPU) │ ├─────────────────────────────────────────────────────────────────────┤ │ │ │ ┌──────────────┐ ┌──────────────┐ ┌────────────────────┐ │ │ │ Depth Camera │ │ LIDAR │ │ Capacitive Touch │ │ │ │ Azure Kinect │ │ RPLidar A3 │ │ Surface Array │ │ │ │ (USB 3.0) │ │ (USB 2.0) │ │ (SPI/I2C) │ │ │ └──────┬───────┘ └──────┬───────┘ └────────┬───────────┘ │ │ │ │ │ │ │ ┌──────▼─────────────────▼────────────────────▼───────────┐ │ │ │ SENSOR FUSION LAYER │ │ │ │ - Body detection + tracking (multi-sensor) │ │ │ │ - Feature extraction (position, velocity, gesture) │ │ │ │ - Coordinate space unification │ │ │ │ - Sensor health monitoring + failover │ │ │ │ (src/sensors/fusion.ts) │ │ │ └──────────────────────┬──────────────────────────────────┘ │ │ │ │ │ ┌──────────────────────▼──────────────────────────────────┐ │ │ │ RESPONSE ENGINE │ │ │ │ - Zone-based parameter mapping │ │ │ │ - Response curve interpolation │ │ │ │ - Multi-body interaction resolution │ │ │ │ - Failsafe mode management │ │ │ │ - Performance SDK integration (metasystem-master) │ │ │ │ (src/engine/response.ts) │ │ │ └────────┬──────────────────────┬─────────────────────────┘ │ │ │ │ │ │ ┌────────▼────────┐ ┌─────────▼──────────┐ ┌────────────────┐ │ │ │ VISUAL OUTPUT │ │ AUDIO OUTPUT │ │ HAPTIC OUTPUT │ │ │ │ - Projection │ │ - Spatial audio │ │ - Vibration │ │ │ │ - LED arrays │ │ - SuperCollider │ │ - Air jets │ │ │ │ - Screens │ │ - Ambisonics │ │ - Pneumatics │ │ │ │ (Three.js/ │ │ (OSC bridge) │ │ (GPIO/DMX) │ │ │ │ GLSL) │ │ │ │ │ │ │ └─────────────────┘ └────────────────────┘ └────────────────┘ │ │ │ │ ┌─────────────────────────────────────────────────────────────┐ │ │ │ MONITORING DASHBOARD │ │ │ │ - Real-time sensor status (health, latency, frame rate) │ │ │ │ - Visitor count + heatmap │ │ │ │ - System resource usage (CPU, GPU, memory) │ │ │ │ - Remote access for gallery technicians │ │ │ │ (src/dashboard/) │ │ │ └─────────────────────────────────────────────────────────────┘ │ └─────────────────────────────────────────────────────────────────────┘ ``` ### Repository Structure ```

## Links
- GitHub: https://github.com/organvm-ii-poiesis/example-interactive-installation
- Organ: ORGAN-II (Poiesis) — Art
