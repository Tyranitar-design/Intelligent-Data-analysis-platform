# -*- coding: utf-8 -*-
"""审计检索 API · 集成测试

覆盖：
- 列表契约（倒序、字段、detail 透传）
- action 前缀过滤 / result 过滤 / principal 过滤
- 分页
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from api.core.database import SessionLocal, init_db
from api.main import app
from api.models import AuditLog

PREFIX = "audit-test"


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


def _make_log(
    session,
    action: str,
    *,
    result: str = "ok",
    principal: str | None = None,
) -> AuditLog:
    log = AuditLog(
        principal_id=principal or f"{PREFIX}-agent",
        action=action,
        result=result,
        target_type="test",
        target_id="42",
        detail={"k": "v"},
    )
    session.add(log)
    session.commit()
    session.refresh(log)
    return log


def test_list_logs_contract(session):
    client = TestClient(app)
    before = client.get("/api/v1/audit/logs").json()
    log = _make_log(session, f"{PREFIX}.action_a")

    resp = client.get("/api/v1/audit/logs", params={"limit": 10})
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["total"] == before["total"] + 1
    assert payload["items"][0]["id"] == log.id  # 倒序：最新在前
    assert payload["items"][0]["action"] == f"{PREFIX}.action_a"
    assert payload["items"][0]["detail"] == {"k": "v"}


def test_filter_by_action_prefix(session):
    client = TestClient(app)
    _make_log(session, f"{PREFIX}.alpha")
    _make_log(session, f"{PREFIX}.alpha.sub")
    _make_log(session, f"{PREFIX}.beta")

    resp = client.get("/api/v1/audit/logs", params={"action": f"{PREFIX}.alpha"})
    items = resp.json()["items"]
    assert len(items) == 2
    assert all(i["action"].startswith(f"{PREFIX}.alpha") for i in items)


def test_filter_by_result_and_principal(session):
    client = TestClient(app)
    _make_log(session, f"{PREFIX}.denied1", result="denied", principal=f"{PREFIX}-bad")
    _make_log(session, f"{PREFIX}.ok1", result="ok", principal=f"{PREFIX}-good")

    resp = client.get(
        "/api/v1/audit/logs",
        params={"result": "denied", "principal": f"{PREFIX}-bad"},
    )
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["result"] == "denied"
    assert items[0]["principal_id"] == f"{PREFIX}-bad"


def test_pagination(session):
    client = TestClient(app)
    for index in range(3):
        _make_log(session, f"{PREFIX}.page{index}")

    first = client.get(
        "/api/v1/audit/logs",
        params={"limit": 2, "offset": 0, "action": PREFIX},
    ).json()
    assert first["total"] >= 3
    assert len(first["items"]) == 2

    second = client.get(
        "/api/v1/audit/logs",
        params={"limit": 2, "offset": 2, "action": PREFIX},
    ).json()
    assert len(second["items"]) >= 1

    # 两页不重叠
    first_ids = {item["id"] for item in first["items"]}
    second_ids = {item["id"] for item in second["items"]}
    assert not (first_ids & second_ids)
