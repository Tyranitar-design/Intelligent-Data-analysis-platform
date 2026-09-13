# Phase 1 Repository Checklist

## Purpose

This checklist defines what should be treated as part of the stable repository baseline for `D:\智能数据分析平台`.

Use it before any first baseline commit or future cleanup pass.

## Commit Now

These belong in version control as part of the project baseline:

### Collaboration And Process

- `.codex/`
- `AGENTS.md`
- `openspec/`
- `docs/`

### Project Documentation

- `README.md`
- `README-v2.md`
- `DESIGN.md`
- `DESIGN-v2-Enterprise.md`
- `PROJECT_OPTIMIZATION_PLAN.md`
- `AUTH-ANTICRAWL-GUIDE.md`

### Backend Source And Config

- `backend/api/`
- `backend/analysis/`
- `backend/crawlers/`
- `backend/database/`
- `backend/dl/`
- `backend/mining/`
- `backend/ml/`
- `backend/reports/`
- `backend/admin/`
- `backend/requirements.txt`
- `backend/requirements-v2.txt`
- `backend/.env.example`
- `backend/Dockerfile`
- `backend/README_DATABASE.md`
- `backend/alembic.ini`
- stable utility and entrypoint source files

### Frontend Source And Config

- `frontend/src/`
- `frontend/package.json`
- `frontend/package-lock.json`
- `frontend/index.html`
- `frontend/vite.config.ts`
- `frontend/tsconfig*.json`
- `frontend/tailwind.config.*`
- `frontend/postcss.config.*`
- `frontend/Dockerfile`
- `frontend/nginx.conf`

### Infrastructure

- `docker-compose-v2.yml`
- `docker-compose.yml`
- `docker/`
- `scripts/`
- `run-dev.cmd`

## Keep Local Only

These should stay out of version control:

- `.env`
- `backend/.env`
- virtual environments
- `node_modules/`
- `frontend/dist/`
- local databases
- cookies stores
- model artifacts (`.joblib`, `.pt`, `.pth`, `.onnx`)
- raw crawl output
- processed local runtime datasets
- caches, logs, temporary files
- backup directories such as `backend/admin.bak/`

## Preserve As Legacy / Reference

These are useful but not active baseline sources:

- `backend/api/main.py`
- `frontend/src/App.tsx`
- `backend/run_api.py`
- `backend/run_api_simple.py`
- `backend/api/main-v2.py`
- `frontend/src/App-v2.tsx`
- `frontend/package-v2.json`
- historical OpenSpec change folders now stored under `openspec/legacy/changes/`

## Canonical Working Baseline Right Now

- Backend: `backend/api/main.py`
- Frontend: `frontend/package.json`
- Docker: `docker-compose-v2.yml`
- Local dev startup: `run-dev.cmd` -> `scripts/run-dev.ps1`
- Active OpenSpec change set: `openspec/changes/baseline-and-architecture-phase1/`
- Docker project name for local Compose runs: `idp`

## Current Backend Mainline Scope

- Mounted by default in canonical `api.main`:
  `auth`, `crawl`, `analysis`, `data`, `reports`
- Preserved in codebase but not mounted by default during this convergence phase:
  `ml`, `dl`, `mining`

## Verification Status

- Frontend canonical app shell and build path are verified.
- Backend canonical module path has been unified to `api.main`.
- Full backend runtime verification still depends on the active environment having all required dependencies installed.

## Phase 1 Exit Criteria

- `.gitignore` filters local-only artifacts correctly
- active OpenSpec changes validate cleanly
- canonical entrypoints are documented
- legacy materials are preserved but no longer block active workflow
