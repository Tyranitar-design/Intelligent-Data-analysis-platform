# -*- coding: utf-8 -*-
"""站点库统计 API · 集成测试

覆盖：
- `/profiles/stats` 聚合（总数 / 判定分布 / 类型分布 / 过期计数，用 delta 断言）
- 路由顺序：`stats` 不能被 `/profiles/{profile_id}` 吞掉
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from api.core.database import SessionLocal, init_db
from api.main import app
from api.models import SiteProfile

PREFIX = "sites-test"


@pytest.fixture(scope="function")
def session():
    init_db()
    db = SessionLocal()
    yield db
    db.rollback()
    db.execute(delete(SiteProfile).where(SiteProfile.domain.like(f"{PREFIX}%")))
    db.commit()
    db.close()


def _make_profile(
    session,
    domain: str,
    decision: str,
    *,
    site_type: str = "news",
    verified_days_ago: int = 0,
) -> SiteProfile:
    profile = SiteProfile(
        domain=domain,
        url_pattern="/",
        version=1,
        sample_url=f"https://{domain}/",
        site_meta={"type": site_type, "title": "test"},
        compliance={"decision": decision},
        last_verified=datetime.now(timezone.utc)
        - timedelta(days=verified_days_ago),
    )
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return profile


def test_stats_aggregates_with_delta(session):
    client = TestClient(app)
    before = client.get("/api/v1/discover/profiles/stats").json()

    _make_profile(session, f"{PREFIX}-a.test", "proceed", site_type="news")
    _make_profile(
        session, f"{PREFIX}-b.test", "confirm_required", site_type="ecommerce"
    )
    _make_profile(
        session, f"{PREFIX}-c.test", "blocked", verified_days_ago=30
    )

    resp = client.get("/api/v1/discover/profiles/stats")
    assert resp.status_code == 200
    after = resp.json()

    assert after["total"] == before["total"] + 3
    assert after["by_decision"]["proceed"] == before["by_decision"]["proceed"] + 1
    assert (
        after["by_decision"]["confirm_required"]
        == before["by_decision"]["confirm_required"] + 1
    )
    assert after["by_decision"]["blocked"] == before["by_decision"]["blocked"] + 1
    assert after["stale_count"] == before["stale_count"] + 1
    assert after["by_type"].get("news", 0) >= 1
    assert after["by_type"].get("ecommerce", 0) >= 1


def test_stats_route_not_shadowed_by_profile_id(session):
    """`/profiles/stats` 必须命中 stats 端点，而不是被 {profile_id} 解析（422）。"""
    client = TestClient(app)
    resp = client.get("/api/v1/discover/profiles/stats")
    assert resp.status_code == 200
    payload = resp.json()
    assert "total" in payload and "by_decision" in payload
