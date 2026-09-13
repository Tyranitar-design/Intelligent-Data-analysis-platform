# -*- coding: utf-8 -*-
"""Smoke Center contracts router."""
from fastapi import APIRouter

from smoke.models import (
    ASSISTED_AUTH_STATES,
    AssistedSmokeContinueRequest,
    AssistedSmokeRunResponse,
    AssistedSmokeStartRequest,
    RUN_STAGES,
    RUN_STATUSES,
    SmokeContractsResponse,
    SmokeRunRequest,
    SmokeRunResponse,
    SmokeScenarioListResponse,
)
from smoke.assisted_auth import continue_assisted_auth_scenario, start_assisted_auth_scenario
from smoke.scenario_registry import list_scenarios
from smoke.service import execute_non_auth_smoke_run

router = APIRouter()


@router.get("/scenarios", response_model=SmokeScenarioListResponse)
async def get_smoke_scenarios():
    """Return registered smoke scenarios."""
    return SmokeScenarioListResponse(scenarios=list_scenarios())


@router.get("/contracts", response_model=SmokeContractsResponse)
async def get_smoke_contracts():
    """Return backend smoke contracts and vocabularies."""
    return SmokeContractsResponse(
        run_statuses=RUN_STATUSES,
        run_stages=RUN_STAGES,
        assisted_auth_states=ASSISTED_AUTH_STATES,
    )


@router.post("/run", response_model=SmokeRunResponse)
async def run_smoke_scenario(request: SmokeRunRequest):
    """Execute first-phase non-auth smoke scenarios."""
    result = await execute_non_auth_smoke_run(request)
    return SmokeRunResponse(**result)


@router.post("/assisted/start", response_model=AssistedSmokeRunResponse)
async def start_assisted_smoke(request: AssistedSmokeStartRequest):
    """Start a Bilibili-first human-assisted smoke flow."""
    result = await start_assisted_auth_scenario(
        scenario_id=request.scenario_id,
        url=request.url,
    )
    return AssistedSmokeRunResponse(**result)


@router.post("/assisted/continue", response_model=AssistedSmokeRunResponse)
async def continue_assisted_smoke(request: AssistedSmokeContinueRequest):
    """Continue a human-assisted smoke flow after manual login/captcha handling."""
    result = await continue_assisted_auth_scenario(request.continuation_token)
    return AssistedSmokeRunResponse(**result)
