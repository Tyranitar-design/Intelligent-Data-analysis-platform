# Development Baseline

## Purpose

This document defines the stable phase-1 development baseline for the project.

It answers:
- which files belong in version control
- which files stay local
- which runtime entrypoints are canonical right now
- how legacy OpenSpec documents are preserved without breaking validation

## Versioned Assets

These should stay in the repository:
- source code under `backend/`, `frontend/`, `scripts/`, and `docs/`
- project collaboration assets under `.codex/`
- project instructions in `AGENTS.md`
- OpenSpec assets under `openspec/`
- Docker definitions, especially `docker-compose-v2.yml`
- example environment files such as `backend/.env.example`

## Local-Only Assets

These should stay out of version control:
- secrets and machine-local config in `.env` files
- Python virtual environments
- `node_modules/` and build output
- local databases and cookies stores
- trained model artifacts
- raw crawl output and processed runtime data
- backup folders and local debug artifacts

## Canonical Runtime Entry Points

Until the architecture convergence phase is completed, use these defaults:

- Backend API:
  `backend/api/main.py`
- Frontend package and Vite app:
  `frontend/package.json`
- Docker stack:
  `docker-compose-v2.yml`

Legacy files are preserved for reference, but they are not the preferred baseline:
- `backend/api/main-v2.py`
- `backend/run_api.py`
- `backend/run_api_simple.py`
- `frontend/src/App-v2.tsx`
- `frontend/package-v2.json`
- `docker-compose.yml`

## Verification Note

- Frontend canonical entrypoint has been verified through successful production builds.
- Backend canonical path has been converged to `api.main`, but direct import verification in the current local environment is blocked until all backend dependencies from `requirements-v2.txt` are installed in the active interpreter.
- Docker Compose v2 config is valid when the project name is supplied explicitly, for example `COMPOSE_PROJECT_NAME=idp`.

## Local Development Entry Point

- The preferred local startup entrypoint is now:
  `run-dev.cmd`
- The underlying PowerShell script lives at:
  `scripts/run-dev.ps1`
- This local flow is the current recommended development baseline.
- Docker remains a secondary path for later integration and deployment validation.

## Lightweight Mainline

- The current canonical `api.main` is intentionally lightweight.
- It prioritizes the product-critical path:
  `auth`, `crawl`, `analysis`, `data`, and `reports`.
- Heavy routes such as `ml`, `dl`, and `mining` remain in the codebase but are not mounted by default in the canonical runtime path during this convergence phase.

## OpenSpec Baseline Policy

- Active, validated changes live under `openspec/changes/`
- Historical OpenSpec-style documents that do not match the current delta format are preserved under `openspec/legacy/`
- New work should use `openspec new change <name>` instead of copying an old template folder

## Phase-1 Goal

Phase 1 is complete when:
- `.gitignore` hides local runtime artifacts and secrets
- active OpenSpec changes validate cleanly
- the canonical entrypoints are documented
- legacy change documents are preserved without blocking validation

## Companion Checklist

For a practical include/exclude checklist, see:
- `docs/PHASE1_REPOSITORY_CHECKLIST.md`
