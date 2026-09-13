# Hot Memory

This file is the project hot-start memory. Read it first, then dive into the deeper memory files if needed.

## Project Snapshot

- data collection
- anti-crawl aware scraping
- analytics and EDA
- ML and DL workflows
- data visualization

## Active Decisions

- The project uses OpenSpec as the preferred structure for substantial change work.
- Codex-specific OpenSpec skills have been initialized in `.codex/skills/`.
- Project memory is stored in `.codex/memory/` so Little C can reload context quickly.
- Python-first remains the default for backend, analytics, ML, and scraping tasks.
- The current canonical backend entrypoint is `backend/api/main.py`.
- The current canonical frontend entrypoint is `frontend/package.json`.

## Known Issues

- Existing `openspec/changes/*` entries currently fail validation under the latest OpenSpec delta rules.
- Likely cause: legacy change documents do not yet use the required delta headers and scenario blocks.
- If OpenSpec workflows are used for new changes, prefer creating fresh compliant changes instead of extending the old invalid ones until migration is complete.

## Recent Work

- Initialized OpenSpec for Codex in this project.
- Confirmed OpenSpec project-local skills were generated under `.codex/skills/`.
- Added Little C project memory pack design for long-term collaboration.
- Observed that legacy OpenSpec change files need migration to current delta format.
- Expanded `.gitignore` to cover local runtime outputs, secrets, models, and caches.
- Added `docs/DEVELOPMENT_BASELINE.md` and `docs/PHASE1_REPOSITORY_CHECKLIST.md`.

## Recent Captures

- 2026-05-15 | Smoke Center | local-upload-basic | passed | 本地数据主链验收 -> passed @ completed
- 2026-05-15 | Smoke Center | local-upload-basic | passed | 本地数据主链验收 -> passed @ completed

## Retrieval Hints

- .codex/skills/
- .codex/memory/
- backend/api/main.py
- frontend/package.json
- docker-compose-v2.yml
- openspec/legacy/changes/
- openspec/changes/*
- .gitignore
- docs/DEVELOPMENT_BASELINE.md
- docs/PHASE1_REPOSITORY_CHECKLIST.md
- baseline-and-architecture-phase1
- openspec validate --changes --json --no-interactive
- Project
- Memory
- Summary
- This

## Read Next

1. `README-v2.md`
2. `.codex/memory/PROJECT_MEMORY.md`
3. `.codex/memory/DECISIONS.md`
4. `.codex/memory/KNOWN_ISSUES.md`
5. `.codex/memory/WORKLOG.md`
