---
title: "Classroom RPG: Aetheria"
category: projects
tags: [education, gamification, teaching, curriculum, learning-platform, react, typescript, ai, pedagogy, classroom, assessment, game-design]
identity_positions: [educator, independent-engineer, creative-technologist]
tracks: [job, grant, fellowship]
related_projects: [organvm-system]
tier: full
---

# Project: Classroom RPG — Aetheria

## One-Line
Classroom gamification platform (React 19, TypeScript, Vite) with AI-powered feedback, 4 theme systems, and quest-based learning progression.

## Short (~100 words)
Aetheria is a classroom gamification platform that transforms course assignments into quests within themed realms. Built with React 19, TypeScript, Vite, and Tailwind CSS v4, it uses LLM-powered features (via GitHub Spark) for AI-generated study guides and assignment feedback. The platform includes 4 switchable theme systems (Fantasy, Cyberpunk, Medieval, Modern) with localized terminology, a Knowledge Crystal system for remediation on failed quests, and a sandbox mode for demos. The architecture demonstrates education-specific product engineering: turning pedagogical concepts (mastery-based progression, scaffolded feedback, formative assessment) into composable software components.

## Full
Aetheria bridges 11 years of classroom teaching experience with production-grade frontend engineering. The platform implements pedagogical principles as software architecture:

- **Quest state machine**: Assignments progress through locked → available → in-progress → submitted → graded states, mirroring mastery-based progression where students must demonstrate competence before advancing
- **Knowledge Crystal system**: Failed quests generate remediation artifacts — targeted review materials that address specific gaps, implementing the pedagogical concept of formative assessment as a game mechanic
- **4 theme systems**: Fantasy, Cyberpunk, Medieval, and Modern themes with localized terminology (e.g. "quest" vs "mission" vs "task"), demonstrating that the same learning structure can be presented in multiple cultural frames
- **AI-powered feedback**: LLM integration for generating study guides and providing scaffolded assignment feedback, extending the AI-conductor methodology into educational contexts
- **XP/leveling progression**: Experience points and leveling tied to learning outcomes, not just completion — the reward structure reinforces the pedagogical goals
- **Sandbox mode**: Demo environment for showcasing the platform without student data, designed for conference presentations and grant applications

The project traveled the full Theory → Art → Commerce pipeline (ORGAN-I → II → III) and is documented in a published post-mortem essay that honestly examines what succeeded and what didn't — demonstrating the process-as-product methodology applied to educational technology.

## Links
- GitHub: https://github.com/4444J99/classroom-rpg-aetheria
- Post-mortem: Referenced in public process essays
