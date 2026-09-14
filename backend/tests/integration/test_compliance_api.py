# -*- coding: utf-8 -*-
"""合规中心 API · 集成测试

覆盖：
- `/verdicts/stats` 聚合与矩阵（用 delta 断言，不受历史数据影响）
- `PATCH /verdicts/{uid}/authorization` 补齐授权：
  解锁 confirm_required / 拒绝 blocked / 拒绝 proceed / 404 / 枚举校验
- 补齐动作写审计留痕
"""
from __future__ import annotations

import secrets

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from api.core.database import SessionLocal, init_db
from api.main import app
from api.models import AuditLog, ComplianceVerdict

PREFIX = "compliance-test"
TARGET = "https://compliance.test/page"


@pytest.fixture(scope="function")
def session():
    init_db()
    db = SessionLocal()
    yield db
    db.rollback()
    # 清理顺序遵守外键依赖：audit_logs（引用 verdict）→ verdicts
    verdict_ids = select(ComplianceVerdict.id).where(
        ComplianceVerdict.target_url.like("%compliance.test%")
    )
    db.execute(
        delete(AuditLog).where(AuditLog.verdict_id.in_(verdict_ids))
    )
    db.execute(
        delete(ComplianceVerdict).where(
            ComplianceVerdict.target_url.like("%compliance.test%")
        )
    )
    db.commit()
    db.close()


def _make_verdict(
    session,
    decision: str,
    *,
    access: str = "A1",
    authorization: str | None = None,
) -> ComplianceVerdict:
    authorization = authorization or ("B4" if decision != "proceed" else "B1")
    verdict = ComplianceVerdict(
        verdict_uid=f"{PREFIX}-{secrets.token_hex(6)}",
        profile_id=None,
        target_url=TARGET,
        decision=decision,
        dim_access=access,
        dim_authorization=authorization,
        dim_behavior="C1",
        dim_data="D1",
        reasons=["test fixture"],
    )
    session.add(verdict)
    session.commit()
    session.refresh(verdict)
    return verdict


def test_stats_aggregates_and_matrix(session):
    client = TestClient(app)
    before = client.get("/api/v1/discover/verdicts/stats").json()

    _make_verdict(session, "confirm_required", access="A1", authorization="B4")
    _make_verdict(session, "blocked", access="A4", authorization="B4")

    resp = client.get("/api/v1/discover/verdicts/stats")
    assert resp.status_code == 200
    after = resp.json()

    assert after["total"] == before["total"] + 2
    assert (
        after["by_decision"]["confirm_required"]
        == before["by_decision"]["confirm_required"] + 1
    )
    assert after["by_decision"]["blocked"] == before["by_decision"]["blocked"] + 1

    matrix = {(m["access"], m["authorization"]): m["count"] for m in after["matrix"]}
    assert matrix.get(("A4", "B4"), 0) >= 1


def test_confirm_authorization_unlocks_and_audits(session):
    client = TestClient(app)
    verdict = _make_verdict(session, "confirm_required")

    resp = client.patch(
        f"/api/v1/discover/verdicts/{verdict.verdict_uid}/authorization",
        json={"basis": "official", "operator": "yg", "note": "公开演示站点"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["unlocked"] is True

    updated = payload["verdict"]
    assert updated["decision"] == "proceed"
    assert updated["dimensions"]["authorization"] == "B1"
    assert updated["operator"] == "yg"
    assert updated["authorization_basis"] == "official"

    # 审计留痕
    log = (
        session.execute(
            select(AuditLog).where(
                AuditLog.action == "compliance.authorization_confirmed",
                AuditLog.verdict_id == verdict.id,
            )
        )
        .scalars()
        .first()
    )
    assert log is not None
    assert log.principal_id == "yg"
    assert (log.detail or {}).get("basis") == "official"


def test_confirm_rejects_blocked(session):
    client = TestClient(app)
    verdict = _make_verdict(session, "blocked", access="A4")

    resp = client.patch(
        f"/api/v1/discover/verdicts/{verdict.verdict_uid}/authorization",
        json={"basis": "official", "operator": "yg"},
    )
    assert resp.status_code == 400
    assert "不可" in resp.json()["detail"]


def test_confirm_rejects_already_proceed(session):
    client = TestClient(app)
    verdict = _make_verdict(session, "proceed")

    resp = client.patch(
        f"/api/v1/discover/verdicts/{verdict.verdict_uid}/authorization",
        json={"basis": "official", "operator": "yg"},
    )
    assert resp.status_code == 400


def test_confirm_missing_verdict_404(session):
    client = TestClient(app)
    resp = client.patch(
        "/api/v1/discover/verdicts/no-such-verdict-uid/authorization",
        json={"basis": "official", "operator": "yg"},
    )
    assert resp.status_code == 404


def test_confirm_validates_basis_enum(session):
    client = TestClient(app)
    verdict = _make_verdict(session, "confirm_required")

    resp = client.patch(
        f"/api/v1/discover/verdicts/{verdict.verdict_uid}/authorization",
        json={"basis": "third_party_credentials", "operator": "yg"},
    )
    assert resp.status_code == 422
