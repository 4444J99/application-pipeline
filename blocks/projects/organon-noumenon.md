---
title: "Ontogenetic Morphe"
category: projects
tags: [ai, database, formal-systems, microservices, python, recursive, symbolic, testing]
identity_positions: [independent-engineer, systems-artist]
tracks: [grant, fellowship]
tier: full
review_status: auto-generated
stats:
  languages: [python]
  ci: true
  public: true
  promotion_status: CANDIDATE
  relevance: HIGH
---

# Project: Ontogenetic Morphe

## One-Line
Ontogenetic Morphe — 22-subsystem symbolic processing architecture with recursive 4-phase process loops, async messag...

## Short (100 words)
Ontogenetic Morphe — 22-subsystem symbolic processing architecture with recursive 4-phase process loops, async message bus, and typed symbolic values. Part of ORGAN-I (Theoria).

## Full
**Problem Statement:** Most symbolic processing frameworks treat symbols as inert data: strings with lookup tables, tokens with embeddings, or nodes in static graphs. They lack a model for how symbolic meaning *develops* — how a narrative fragment accrues provenance, how a rule compiles into executable form, how a dream-symbol decays into echo and is eventually archived or transformed into currency. Existing approaches fall into predictable traps: - **Rule engines** (Drools, CLIPS) handle production rules but have no concept of symbolic value, identity, or temporal decay - **Agent frameworks** (LangChain, CrewAI) orchestrate LLM calls but treat the orchestration layer as mere plumbing, not as a domain with its own semantics - **Message brokers** (RabbitMQ, Kafka) provide pub/sub infrastructure but impose no type discipline on the symbolic content flowing through them - **Actor systems** (Akka, Ray) manage concurrency but their actor model does not distinguish between a signal that should attenuate over distance and a message that should persist until consumed Ontogenetic Morphe addresses the gap between these paradigms. It provides a typed symbolic processing architecture where every value carries provenance and lineage, every signal has physical properties (strength, threshold, attenuation), every subsystem follows the same recursive lifecycle, and the whole system communicates through a single async message bus with topic-based routing. The core insight is that symbolic processing is not a pipeline but a *metabolism* — a recursive cycle of intake, processing, evaluation, and integration that mirrors biological ontogenesis. Each subsystem is a specialized organ within a larger body, and the body's coherence emerges from the message bus, not from a central controller.

**Core Concepts:** ### The Four-Phase Process Loop Every computation in the system follows a single abstract protocol defined by `ProcessLoop[InputT, OutputT, ContextT]`: ``` INTAKE → PROCESS → EVALUATE → INTEGRATE ↑ │ └────────────────────┘ (feedback: should_continue) ``` The `evaluate` phase returns a boolean `should_continue` flag, creating a natural recursion: a subsystem keeps cycling until its own evaluation criteria are satisfied. This is not an arbitrary design choice — it models the recursive self-modification that characterizes living systems. A rule compiler does not simply compile; it compiles, evaluates the result, and recompiles if the

## Links
- GitHub: https://github.com/organvm-i-theoria/organon-noumenon--ontogenetic-morphe
- Organ: ORGAN-I (Theoria) — Theory
