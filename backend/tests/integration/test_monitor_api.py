# -*- coding: utf-8 -*-
"""运行监视 API · 集成测试

覆盖：
- `/monitor/stats` 契约（service / queue / rate / storage 四段）
- 队列计数随数据变化（delta 断言）
- 限速器域名追踪（acquire 后出现在 stats 中）
"""
from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from api.core.database import SessionLocal, init_db
from api.main import app
from api.models import CollectJob, CollectPlan, CollectSchedule

PREFIX = "monitor-test"
TARGET = "https://monitor.test/list"


@pytest.fixture(scope="function")
def session():
    init_db()
    db = SessionLocal()
    yield db
    db.rollback()
    plan_ids = select(CollectPlan.id).where(CollectPlan.target_url.like("%monitor.test%"))
    db.execute(delete(CollectSchedule).where(CollectSchedule.name.like(f"{PREFIX}%")))
    db.execute(
        delete(CollectJob).where(CollectJob.plan_id.in_(plan_ids))
    )
    db.execute(delete(CollectPlan).where(CollectPlan.target_url.like("%monitor.test%")))
    db.commit()
    db.close()


def test_monitor_stats_contract(session):
    client = TestClient(app)
    resp = client.get("/api/v1/monitor/stats")
    assert resp.status_code == 200
    payload = resp.json()

    assert payload["service"]["version"]
    assert payload["service"]["database"] in ("sqlite", "postgresql")
    assert "pending_jobs" in payload["queue"]
    assert "schedules_enabled" in payload["queue"]
    assert "tracked_domains" in payload["rate"]
    assert "datasets" in payload["storage"]
    assert payload["storage"]["tables"] is not None


def test_monitor_reflects_queue_delta(session):
    client = TestClient(app)
    before = client.get("/api/v1/monitor/stats").json()

    plan = CollectPlan(target_url=TARGET, status="ready")
    session.add(plan)
    session.commit()
    session.refresh(plan)

    session.add(
        CollectJob(
            plan_id=plan.id,
            status="pending",
            total_tasks=1,
            dedup_stats={},
        )
    )
    session.add(
        CollectSchedule(
            name=f"{PREFIX}-daily",
            plan_id=plan.id,
            frequency="daily",
            time_of_day="06:00",
            enabled=True,
        )
    )
    session.commit()

    after = client.get("/api/v1/monitor/stats").json()
    assert after["queue"]["pending_jobs"] == before["queue"]["pending_jobs"] + 1
    assert after["queue"]["total_jobs"] == before["queue"]["total_jobs"] + 1
    assert (
        after["queue"]["schedules_enabled"]
        == before["queue"]["schedules_enabled"] + 1
    )


def test_monitor_rate_tracks_domain(session):
    from collect.ratelimit import get_shared_limiter

    limiter = get_shared_limiter()
    asyncio.run(limiter.acquire("monitor.test"))
    try:
        client = TestClient(app)
        payload = client.get("/api/v1/monitor/stats").json()
        assert "monitor.test" in payload["rate"]["domains"]
        snapshot = payload["rate"]["domains"]["monitor.test"]
        assert snapshot["total_requests"] >= 1
        assert "throttled" in snapshot
    finally:
        limiter.reset("monitor.test")
