# Smoke Center Implementation Plan

> Planning-only document for `D:\智能数据分析平台`

## Goal

Add a product-native `Smoke Center / 验收中心` that validates the collection-to-dataset-to-analysis-to-report chain, supports robots-aware public URL testing, and introduces a human-assisted authentication workflow for login/captcha sites.

## Scope

This plan covers:

- OpenSpec-governed product and architecture planning
- backend orchestration design
- frontend control-center design
- phased execution order

This plan does **not** implement the feature yet.

## Phase Plan

### Phase A: Contracts And Data Shapes

- Define scenario registry shapes
- Define smoke run result schema
- Define assisted-auth lifecycle states
- Define failure/status vocabulary:
  - `passed`
  - `failed`
  - `blocked_by_robots`
  - `manual_checkpoint_required`
  - `skipped`

### Phase B: Backend Orchestration

- Create a dedicated `smoke` service package
- Create a dedicated `/api/v1/smoke` router
- Reuse:
  - `crawl`
  - `auth`
  - `dataset_service`
  - `analysis`
  - `reports`
- Avoid duplicating crawl logic inside smoke services

### Phase C: Frontend Smoke Center

- Add a new route and navigation entry
- Build three operator sections:
  - `Local Smoke`
  - `Live Public Smoke`
  - `Live Assisted Smoke`
- Add a structured run result panel
- Emphasize operator clarity over raw debug payloads

### Phase D: First Assisted-Auth Platform

- Use `Bilibili` as the first assisted-auth validation platform
- Validate:
  - login entry
  - human checkpoint
  - session capture
  - session reuse
  - post-auth crawl
  - dataset save
  - analysis
  - report generation

### Phase E: Generalization

- Move from `Bilibili-first` to `platform-extensible`
- Represent future supported platforms through configuration-oriented descriptors instead of platform-specific duplicated flow logic

## First Recommended Implementation Order

1. Backend contracts and result model
2. Smoke router and scenario registry
3. Local smoke execution path
4. Live public smoke execution path
5. Frontend Smoke Center with polling
6. Assisted-auth state machine
7. Bilibili assisted-auth first pass
8. Platform extension framework

## Key Risks

- `crawl.py` is already too large
  - Mitigation: keep Smoke Center in a separate router/service boundary
- assisted-auth is inherently stateful and operator-dependent
  - Mitigation: explicit state machine and manual checkpoint UX
- external URLs are flaky
  - Mitigation: keep `local` smoke as default baseline and classify live runs precisely
- secret leakage risk
  - Mitigation: run history stores evidence summaries, not raw cookies

## Deliverables For Execution Phase

- OpenSpec active change:
  - `smoke-center-assisted-collection`
- implementation plan to be written next against the approved spec
- phased execution using:
  - harness engineering
  - vibe coding
  - expert routing
