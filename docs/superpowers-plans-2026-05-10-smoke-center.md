# Smoke Center Implementation Plan

> **For future execution:** This document is the staged handoff for implementing the approved OpenSpec change `smoke-center-assisted-collection` in `D:\智能数据分析平台`.

**Goal:** Build a product-native Smoke Center that validates the core chain from collection to dataset to analysis to reports, while supporting robots-aware public URL tests and human-assisted authentication flows.

**Architecture:** The Smoke Center is an orchestration layer over existing product capabilities, not a parallel collection subsystem. Backend work is isolated into a dedicated `smoke` router and service package, while the frontend adds a dedicated control-center page with explicit operator states and structured run results. Assisted authentication is introduced first for Bilibili, but the lifecycle is designed to generalize to additional platforms and custom sites.

**Tech Stack:** FastAPI, SQLAlchemy, existing crawl/auth services, React 18, TypeScript, Zustand/TanStack patterns already present in the app, OpenSpec, harness engineering, vibe coding.

---

## Planned File Structure

### Backend

- Create: `backend/api/routers/smoke.py`
  - Smoke API endpoints for scenarios, runs, and assisted-auth transitions
- Create: `backend/smoke/__init__.py`
  - Public package entry
- Create: `backend/smoke/models.py`
  - Typed internal dataclasses / Pydantic models for scenario config, run state, and run results
- Create: `backend/smoke/scenario_registry.py`
  - Scenario definitions for local, live-public, and live-assisted modes
- Create: `backend/smoke/service.py`
  - Smoke orchestration logic reusing crawl/auth/analysis/report capabilities
- Create: `backend/smoke/state_machine.py`
  - Assisted-auth lifecycle and stage transitions
- Create: `backend/test_smoke_center_planning_baseline.py`
  - Script-style regression checks for initial backend contract

### Frontend

- Create: `frontend/src/api/smoke.ts`
  - Smoke Center API client
- Create: `frontend/src/pages/SmokeCenter.tsx`
  - Dedicated Smoke Center page
- Modify: `frontend/src/App.tsx`
  - Add route
- Modify: `frontend/src/components/layout/Sidebar.tsx`
  - Add navigation entry

### Documentation

- Existing OpenSpec change:
  - `openspec/changes/smoke-center-assisted-collection/`
- Existing planning docs:
  - `docs/2026-05-10-smoke-center-implementation-plan.md`
  - `docs/superpowers-plans-2026-05-10-smoke-center.md`

---

## Phase 1: Backend Contracts

**Objective:** Lock the contract before UI wiring.

- Define canonical run statuses:
  - `passed`
  - `failed`
  - `blocked_by_robots`
  - `manual_checkpoint_required`
  - `skipped`
- Define canonical stages:
  - `scenario_loaded`
  - `robots_check`
  - `probe`
  - `crawl`
  - `waiting_for_human`
  - `session_capture`
  - `session_reuse_check`
  - `dataset_save`
  - `analysis`
  - `report`
  - `completed`
- Define scenario schema:
  - stable `scenario_id`
  - `mode`
  - target requirements
  - auth requirements
  - strategy hints
  - post-processing steps
- Define run result schema:
  - `scenario_id`
  - `status`
  - `stage`
  - `robots`
  - `crawl_strategy`
  - `requires_human`
  - `dataset_saved`
  - `analysis_passed`
  - `report_passed`
  - `artifacts`
  - `notes`
  - `error`

**Verification target:** backend script confirms a scenario list and normalized in-memory result model can be produced without touching the frontend.

---

## Phase 2: Scenario Registry And Non-Auth Runner

**Objective:** Ship the first stable orchestration loop without assisted auth yet.

- Add scenario registry entries for:
  - `local-upload-basic`
  - `live-public-static`
  - `live-public-dynamic-js`
- Reuse existing endpoints/services:
  - `robots-check`
  - `url/probe`
  - `url/crawl`
  - `smart/v2/probe`
  - `smart/v2/crawl`
  - dataset save/list
  - analysis
  - reports
- Ensure public scenarios always check robots first
- Ensure `blocked_by_robots` becomes a first-class terminal result

**Verification target:** run local and live-public scenarios through backend script(s), with explicit evidence for:
- robots status
- chosen strategy
- dataset saved or not
- analysis result
- report result

---

## Phase 3: Frontend Smoke Center

**Objective:** Add the operator-facing control panel with clear UX.

- Add dedicated navigation item and route
- Split UI into:
  - `Local Smoke`
  - `Live Public Smoke`
  - `Live Assisted Smoke`
- Add structured result view showing:
  - scenario
  - current stage
  - status
  - robots result
  - crawl strategy
  - manual checkpoint requirement
  - dataset / analysis / report pass status
  - notes / failure reason
- Prefer summary-first rendering over raw payload dumping

**Verification target:** frontend build passes and the page can render seeded or mocked scenario results before real wiring is completed.

---

## Phase 4: Assisted Auth State Machine

**Objective:** Introduce human collaboration safely and explicitly.

- Build explicit assisted-auth lifecycle:
  - `ready_to_open_login`
  - `waiting_for_human`
  - `session_captured`
  - `session_reuse_check`
  - `crawl_after_auth`
  - `completed`
  - `failed`
- Ensure the operator always knows whether the system is waiting on them or running autonomously
- Never attempt automated captcha bypass
- Record evidence summaries, not raw secret/session material

**Verification target:** backend run model can enter and leave `manual_checkpoint_required` cleanly.

---

## Phase 5: Bilibili First Platform

**Objective:** Validate the first end-to-end assisted-auth scenario.

- Add first assisted scenario:
  - `live-assisted-bilibili`
- Validate:
  - open login
  - operator handoff
  - session capture
  - session reuse check
  - post-auth crawl
  - dataset save
  - analysis
  - report generation

**Verification target:** first successful human-assisted run can be reproduced with a stable operator flow.

---

## Phase 6: Platform Generalization

**Objective:** Avoid a Bilibili-only design.

- Introduce platform descriptor structure for future supported sites
- Support additional assisted-auth platforms by configuration-oriented definitions, not duplicated flows
- Support future custom-site descriptor entry

**Verification target:** a second assisted-auth platform can be added without changing the shared lifecycle logic.

---

## Reliability And Safety Rules

- Smoke Center is an orchestration layer, not a forked crawl subsystem
- Public live runs must check robots before collection
- Captcha and login barriers trigger manual collaboration, not bypass behavior
- Run history stores structured evidence, not raw cookies or secrets
- `crawl.py` should not absorb the new smoke orchestration responsibilities
- New persistence should align with the canonical backend path, not legacy duplicate DB bases

---

## Next Execution Recommendation

When we switch from planning to implementation, the safest first execution slice is:

1. Backend contracts and scenario registry
2. Non-auth local/live-public runner
3. Frontend Smoke Center shell
4. Assisted-auth state machine
5. Bilibili first platform
6. Generalization
