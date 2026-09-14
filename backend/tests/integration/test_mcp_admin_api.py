# -*- coding: utf-8 -*-
"""MCP 接入管理 API · 集成测试

覆盖：
- `/mcp/stats` 契约（统计四段 + 鉴权状态 + 工具数）
- 审计行聚合（构造 `mcp.*` 记录 → delta 断言）
- `/mcp/selftest` 协议自检（initialize 握手返回 server_info）
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from api.core.database import SessionLocal, init_db
from api.main import app
from api.models import AuditLog

PREFIX = "mcp-admin-test"


@pytest.fixture(scope="function")
def session():
    init_db()
    db = SessionLocal()
    yield db
    db.rollback()
    db.execute(delete(AuditLog).where(AuditLog.principal_id.like(f"{PREFIX}%")))
    db.execute(delete(AuditLog).where(AuditLog.action.like(f"{PREFIX}%")))
    db.commit()
    db.close()


def _make_log(session, action: str, *, result: str = "ok") -> AuditLog:
    log = AuditLog(
        principal_id=f"{PREFIX}-agent",
        action=action,
        result=result,
        target_type="mcp_tool",
        target_id=action,
        detail={},
    )
    session.add(log)
    session.commit()
    session.refresh(log)
    return log


def test_mcp_stats_contract(session):
    client = TestClient(app)
    resp = client.get("/api/v1/mcp/stats")
    assert resp.status_code == 200
    payload = resp.json()

    assert payload["protocol"] == "json-rpc-2.0-over-http"
    assert payload["auth_configured"] in (True, False)
    assert payload["tool_count"] >= 7
    assert set(payload["by_result"].keys()) >= {"ok", "denied", "error"}
    assert isinstance(payload["by_tool"], dict)
    assert isinstance(payload["recent"], list)


def test_mcp_stats_aggregates_audit_rows(session):
    client = TestClient(app)
    before = client.get("/api/v1/mcp/stats").json()

    _make_log(session, "mcp.analyze_site", result="ok")
    _make_log(session, "mcp.analyze_site", result="denied")
    _make_log(session, "mcp.query_dataset", result="ok")

    after = client.get("/api/v1/mcp/stats").json()
    assert after["total"] == before["total"] + 3
    assert after["by_tool"].get("analyze_site", 0) >= 2
    assert after["by_tool"].get("query_dataset", 0) >= 1
    assert after["by_result"]["denied"] >= 1
    # recent 倒序：最新在前
    assert after["recent"][0]["action"].startswith("mcp.")


def test_mcp_selftest_initialize(session):
    client = TestClient(app)
    resp = client.post("/api/v1/mcp/selftest")
    assert resp.status_code == 200
    payload = resp.json()

    assert payload["ok"] is True
    assert payload["protocol"] == "json-rpc-2.0-over-http"
    assert payload["server"], "initialize 应返回 server_info"
    assert payload["elapsed_ms"] >= 0
    assert payload["auth_configured"] in (True, False)
