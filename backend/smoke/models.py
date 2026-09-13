# -*- coding: utf-8 -*-
"""Smoke Center contracts and typed models."""
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


RUN_STATUSES = [
    "passed",
    "failed",
    "blocked_by_robots",
    "manual_checkpoint_required",
    "skipped",
]

RUN_STAGES = [
    "scenario_loaded",
    "robots_check",
    "probe",
    "crawl",
    "waiting_for_human",
    "session_capture",
    "session_reuse_check",
    "dataset_save",
    "analysis",
    "report",
    "completed",
]

ASSISTED_AUTH_STATES = [
    "ready_to_open_login",
    "waiting_for_human",
    "session_captured",
    "session_reuse_check",
    "crawl_after_auth",
    "completed",
    "failed",
]


SmokeMode = Literal["local", "live-public", "live-assisted"]


class SmokeScenarioDefinition(BaseModel):
    """Smoke scenario registry item."""

    scenario_id: str = Field(..., description="Stable scenario identifier")
    title: str = Field(..., description="Operator-visible scenario title")
    description: str = Field(..., description="Scenario summary")
    mode: SmokeMode = Field(..., description="Scenario mode")
    requires_robots_check: bool = Field(..., description="Whether robots.txt check is required")
    requires_auth: bool = Field(..., description="Whether auth/session is required")
    requires_human: bool = Field(..., description="Whether human collaboration is required")
    preferred_strategy: Optional[str] = Field(None, description="Preferred crawl strategy hint")
    platform: Optional[str] = Field(None, description="Target platform for assisted auth scenarios")
    required_inputs: List[str] = Field(default_factory=list, description="Inputs required before running")
    post_steps: List[str] = Field(default_factory=list, description="Planned downstream validation steps")


class SmokeScenarioListResponse(BaseModel):
    """Scenario registry response."""

    success: bool = True
    scenarios: List[SmokeScenarioDefinition]


class SmokeContractsResponse(BaseModel):
    """Backend vocabulary contract response."""

    success: bool = True
    run_statuses: List[str]
    run_stages: List[str]
    assisted_auth_states: List[str]


class SmokeRunRequest(BaseModel):
    """Run request for smoke scenarios."""

    scenario_id: str = Field(..., description="Stable scenario identifier")
    url: Optional[str] = Field(None, description="Target URL for live scenarios")
    dataset_name: Optional[str] = Field(None, description="Dataset name for local smoke")
    dataset_description: str = Field("", description="Dataset description")
    rows: List[Dict[str, Any]] = Field(default_factory=list, description="Local structured rows for local smoke")


class SmokeRunResponse(BaseModel):
    """Normalized smoke run result."""

    success: bool = True
    scenario_id: str
    status: str
    stage: str
    requires_human: bool
    dataset_saved: bool
    analysis_passed: bool
    report_passed: bool
    crawl_strategy: Optional[str] = None
    robots: Dict[str, Any] = Field(default_factory=dict)
    artifacts: Dict[str, Any] = Field(default_factory=dict)
    memory_capture: Dict[str, Any] = Field(default_factory=dict)
    notes: List[str] = Field(default_factory=list)
    error: Optional[str] = None


class AssistedSmokeStartRequest(BaseModel):
    """Start request for assisted-auth scenarios."""

    scenario_id: str = Field(..., description="Assisted scenario identifier")
    url: str = Field(..., description="Target site URL")


class AssistedSmokeContinueRequest(BaseModel):
    """Continue request after manual checkpoint."""

    continuation_token: str = Field(..., description="Continuation token returned by assisted start")


class AssistedSmokeRunResponse(SmokeRunResponse):
    """Extended smoke run response for assisted-auth flows."""

    assisted_auth_state: str
    platform: Optional[str] = None
    continuation_token: Optional[str] = None
