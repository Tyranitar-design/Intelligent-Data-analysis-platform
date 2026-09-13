# -*- coding: utf-8 -*-
"""Assisted-auth state machine and in-memory continuation store."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict
from uuid import uuid4

from crawlers.auth.auth_manager import AuthManager
from crawlers.auth.login_flows import get_login_flow

from .memory_capture import record_smoke_memory_capture
from .scenario_registry import get_scenario


@dataclass
class AssistedAuthSession:
    continuation_token: str
    scenario_id: str
    platform: str
    url: str
    login_url: str
    check_url: str
    created_at: datetime
    expires_at: datetime


_sessions: Dict[str, AssistedAuthSession] = {}
_auth_manager = AuthManager()


def _build_assisted_result(
    *,
    scenario_id: str,
    status: str,
    stage: str,
    assisted_auth_state: str,
    platform: str,
    continuation_token: str | None,
    artifacts: Dict[str, Any],
    notes: list[str] | None = None,
    error: str | None = None,
) -> Dict[str, Any]:
    return {
        "success": True,
        "scenario_id": scenario_id,
        "status": status,
        "stage": stage,
        "requires_human": True,
        "dataset_saved": False,
        "analysis_passed": False,
        "report_passed": False,
        "crawl_strategy": "assisted-auth",
        "robots": {"checked": False},
        "artifacts": artifacts,
        "memory_capture": {},
        "notes": notes or [],
        "error": error,
        "assisted_auth_state": assisted_auth_state,
        "platform": platform,
        "continuation_token": continuation_token,
    }


def _attach_assisted_memory_capture(
    result: Dict[str, Any],
    *,
    scenario_title: str,
    url: str | None,
) -> Dict[str, Any]:
    memory_capture = record_smoke_memory_capture(
        result,
        scenario_id=result["scenario_id"],
        scenario_title=scenario_title,
        mode="live-assisted",
        url=url,
        tags=[result.get("platform") or "assisted-auth", result.get("assisted_auth_state") or ""],
    )
    result["memory_capture"] = memory_capture
    if memory_capture.get("captured"):
        result["notes"] = [*result.get("notes", []), "协同 Smoke 状态已自动写入 Little C 记忆。"]
    elif memory_capture.get("error"):
        result["notes"] = [*result.get("notes", []), f"记忆写入跳过：{memory_capture['error']}"]
    return result


async def start_assisted_auth_scenario(scenario_id: str, url: str) -> Dict[str, Any]:
    scenario = get_scenario(scenario_id)
    if scenario is None or scenario.platform != "bilibili":
        return _attach_assisted_memory_capture(_build_assisted_result(
            scenario_id=scenario_id,
            status="failed",
            stage="scenario_loaded",
            assisted_auth_state="failed",
            platform=scenario.platform if scenario else "unknown",
            continuation_token=None,
            artifacts={},
            error=f"Unsupported assisted scenario: {scenario_id}",
        ), scenario_title="unsupported-assisted-scenario", url=url)

    login_flow = get_login_flow(scenario.platform)
    continuation_token = uuid4().hex
    session = AssistedAuthSession(
        continuation_token=continuation_token,
        scenario_id=scenario_id,
        platform=scenario.platform,
        url=url,
        login_url=login_flow.get("login_url", url),
        check_url=login_flow.get("check_url", url),
        created_at=datetime.now(),
        expires_at=datetime.now() + timedelta(minutes=20),
    )
    _sessions[continuation_token] = session

    return _attach_assisted_memory_capture(_build_assisted_result(
        scenario_id=scenario_id,
        status="manual_checkpoint_required",
        stage="waiting_for_human",
        assisted_auth_state="waiting_for_human",
        platform=session.platform,
        continuation_token=continuation_token,
        artifacts={
            "login_url": session.login_url,
            "check_url": session.check_url,
        },
        notes=[
            "请人工完成登录或验证码，然后再点击继续。",
            "当前第一版采用人机协同，不自动绕过验证码。",
        ],
        error=None,
    ), scenario_title=scenario.title, url=url)


async def continue_assisted_auth_scenario(continuation_token: str) -> Dict[str, Any]:
    session = _sessions.get(continuation_token)
    if session is None:
        return _attach_assisted_memory_capture(_build_assisted_result(
            scenario_id="unknown",
            status="failed",
            stage="session_reuse_check",
            assisted_auth_state="failed",
            platform="unknown",
            continuation_token=None,
            artifacts={},
            error="Invalid continuation token",
        ), scenario_title="assisted-auth-continue", url=None)

    if session.expires_at < datetime.now():
        _sessions.pop(continuation_token, None)
        return _attach_assisted_memory_capture(_build_assisted_result(
            scenario_id=session.scenario_id,
            status="failed",
            stage="session_reuse_check",
            assisted_auth_state="failed",
            platform=session.platform,
            continuation_token=None,
            artifacts={},
            error="Continuation token expired",
        ), scenario_title="Bilibili assisted auth", url=session.url)

    status = await _auth_manager.check_login_status(session.platform, session.check_url)
    is_logged_in = bool(status.get("is_logged_in"))
    _sessions.pop(continuation_token, None)

    if is_logged_in:
        return _attach_assisted_memory_capture(_build_assisted_result(
            scenario_id=session.scenario_id,
            status="completed",
            stage="session_reuse_check",
            assisted_auth_state="session_reuse_check",
            platform=session.platform,
            continuation_token=None,
            artifacts={
                "login_url": session.login_url,
                "check_url": session.check_url,
                "auth_status": status,
            },
            notes=["检测到可复用登录态，下一阶段可继续接入登录态采集。"],
            error=None,
        ), scenario_title="Bilibili assisted auth", url=session.url)

    return _attach_assisted_memory_capture(_build_assisted_result(
        scenario_id=session.scenario_id,
        status="failed",
        stage="session_reuse_check",
        assisted_auth_state="failed",
        platform=session.platform,
        continuation_token=None,
        artifacts={
            "login_url": session.login_url,
            "check_url": session.check_url,
            "auth_status": status,
        },
        notes=["未检测到有效登录态，请重新开始并完成人工登录。"],
        error=status.get("error") or status.get("message") or "Login state not valid",
    ), scenario_title="Bilibili assisted auth", url=session.url)
