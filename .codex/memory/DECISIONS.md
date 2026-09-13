# Decisions

## Active Decisions

1. The project uses OpenSpec as the preferred structure for substantial change work.
2. Codex-specific OpenSpec skills have been initialized in `.codex/skills/`.
3. Project memory is stored in `.codex/memory/` so Little C can reload context quickly.
4. Python-first remains the default for backend, analytics, ML, and scraping tasks.
5. The current canonical backend entrypoint is `backend/api/main.py`.
6. The current canonical frontend entrypoint is `frontend/package.json`.
7. The current canonical Docker entrypoint is `docker-compose-v2.yml`.
8. Historical OpenSpec-style changes are preserved under `openspec/legacy/changes/`, while only current-format changes stay active.
9. The current priority is a lightweight canonical API mainline for the product-critical path: auth, crawl, analysis, data, and reports first; heavier ML/DL/mining runtime convergence can follow as a separate step.
