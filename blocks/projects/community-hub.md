---
title: "FastAPI flagship portal"
category: projects
tags: [archive, community, docker, education, fastapi, learning, testing, websocket]
identity_positions: [community-practitioner, educator]
tracks: [grant, fellowship]
related_projects: [koinonia-db, organvm-system]
tier: full
review_status: auto-generated
---

# Project: FastAPI flagship portal

## One-Line
FastAPI flagship portal — salon archive, curricula browser, contributor profiles, full-text search, adaptive syllabus...

## Short (100 words)
FastAPI flagship portal — salon archive, curricula browser, contributor profiles, full-text search, adaptive syllabus, Atom feeds, WebSocket live rooms. ORGAN-VI flagship — the community portal for salons, reading groups, adaptive syllabi, and contributor profiles. Live: https://community-hub-8p8t.onrender.com Part of ORGAN-VI (Koinonia).

## Full
**Overview:** community-hub is a FastAPI web application that serves as the public face of ORGAN-VI Koinonia. It provides both HTML pages (Jinja2 templates) and a JSON API for browsing salon archives, reading curricula, taxonomy, community events, contributor profiles, personalized learning paths, full-text search, and Atom syndication feeds. **122 tests** | **CSRF protection** | **Rate limiting** | **WebSocket live rooms** | **Atom 1.0 feeds**

**Architecture:** ``` community-hub/ ├── src/community_hub/ │ ├── app.py # FastAPI app with lifespan, CORS, CSRF, rate limiting │ ├── config.py # Environment-based settings │ ├── csrf.py # Double-submit cookie CSRF middleware │ ├── logging_config.py # Structured logging │ ├── routes/ │ │ ├── api.py # JSON API endpoints │ │ ├── salons.py # Salon HTML routes │ │ ├── curricula.py # Curricula HTML routes │ │ ├── community.py # Events, contributors, stats │ │ ├── search.py # Full-text search (HTML + JSON) │ │ ├── syllabus.py # Learning path generation │ │ ├── feeds.py # Atom 1.0 syndication feeds │ │ └── live.py # WebSocket live salon rooms │ ├── templates/ # Jinja2 templates │ └── static/ # CSS ├── scripts/ │ └── entrypoint.sh # Docker entrypoint (runs Alembic then uvicorn) ├── tests/ # 122 tests ├── Dockerfile ├── render.yaml └── pyproject.toml ``` **Key dependencies:** - **koinonia-db** — shared SQLAlchemy models, Alembic migrations (installed from git) - **FastAPI** — async web framework - **psycopg 3** — PostgreSQL async driver (Neon-compatible) - **Jinja2** — HTML templating - **slowapi** — rate limiting (per-IP) **Security:** - CSRF protection via double-submit cookie on all POST routes - Rate limiting on syllabus generation endpoints (10-20/min) - WebSocket rate limiting (10 msg/sec) and message size limits (4 KB) - HTML escaping on all WebSocket broadcast messages - CORS configurable via `ALLOWED_ORIGINS`

## Links
- GitHub: https://github.com/organvm-vi-koinonia/community-hub
- Organ: ORGAN-VI (Koinonia) — Community
