---
title: "Personal artistic portfolio site (etceter4.com)"
category: projects
tags: [ai, ci-cd, creative-coding, generative-art, p5js, portfolio, react, testing, three-js, typescript]
identity_positions: [creative-technologist, systems-artist]
tracks: [grant, residency, fellowship, prize]
related_projects: [organvm-system]
tier: full
review_status: auto-generated
---

# Project: Personal artistic portfolio site (etceter4.com)

## One-Line
Personal artistic portfolio site (etceter4.com) — living temple of art, sound, and words

## Short (100 words)
Personal artistic portfolio site (etceter4.com) — living temple of art, sound, and words. git clone https://github.com/organvm-ii-poiesis/a-mavs-olevm.git cd a-mavs-olevm # Install dependencies npm install # Start the development server npm run dev `` Open http://localhost:3000. The temple entrance will appear. ### Available Commands `bash npm run dev # Local server with hot reload (browser-sync, port 3000) npm run lint # ESLint check on core JS files npm run lint:fix # Auto-fix linting issues npm run format # Prettier formatting across all files npm run format:check # Verify formatting compliance npm run test:unit # Vitest unit tests npm run test # Playwright.

## Full
**Technical Overview:** ### Architecture a-mavs-olevm is a **static single-page application** with no build step. JavaScript runs directly in the browser using global scope for cross-file communication. This is a deliberate architectural choice: the site has no framework dependency, no transpilation pipeline, and no runtime that could break independently of the content. ``` +=============================+ | THE PANTHEON | | (Temple Complex) | +=============================+ | | +---------------+------------------------------+-----------------+ | WEST WING | CENTRAL NAOS (Core) | EAST WING | | | | | | Agora | Museum (Preservation) | Akademia | | Discourse | Mausoleum (Honor) | Scholarship | | Manifestos | Labyrinth (Exploration) | Research | | | Choral Chamber (Sound) | CV | | | Atelier (Creation) | | +---------------+------------------------------+-----------------+ | | | SOUTH WING | | Theatron (Theatre) | | Odeion (Music Hall) | | Ergasterion (Workshop) | +==============================+ ``` **Core navigation system:** | File | Responsibility | | `js/page.js` | `Page` class with state management, tier-based navigation, fade transitions | | `js/main.js` | Application entry point, hash-based routing, `handleHashChange()` for browser back/forward | | `index.html` | Single HTML document containing all page sections as visibility-toggled elements | **Navigation tier model:** ``` Tier 1: #landing (Temple Entrance) Tier 2: #menu (Navigation Hub) Tier 3: #sound #vision (Content Sections) #words #info #east-wing #west-wing #south-wing #north-wing Tier 4: #stills #diary (Detail Pages) #video #ogod3d #bibliotheke #pinakotheke #theatron #odeion #ergasterion #khronos ``` ### Technology Stack | Layer | Technology | Purpose | | **Runtime** | Vanilla JavaScript ES6+ | No framework, no build step, global scope by design | | **DOM** | jQuery 3.7+ | DOM manipulation, event handling, AJAX content loading | | **Animation** | Velocity.js 2.0+ | Page transitions (fadeIn/fadeOut with configurable easing) | | **Generative Art** | p5.js | Sketches, particle systems, Perlin noise flow fields | | **3D Rendering** | Three.js 0.160.0 | OGOD 3D visual album, audio-reactive spheres, GLSL shaders | | **Audio Synthesis** | Tone.js 14.8.49 | Programmatic sound generation, audio engine | | **Audio Playback** | Howler.js | Cross-browser audio playback, ambient layers | | **CSS** | Tachyons | Utility-first styling with custom properties for theming | |

## Links
- GitHub: https://github.com/organvm-ii-poiesis/a-mavs-olevm
- Organ: ORGAN-II (Poiesis) — Art
