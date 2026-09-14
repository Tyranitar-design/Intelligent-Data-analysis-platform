# -*- coding: utf-8 -*-
"""调度规则 API · 集成测试（全部不触碰真实网络）

覆盖：
- 创建校验（频率参数不合法 → 400）
- CRUD 契约
- 手动触发（mock 采集执行）→ 任务创建 + 规则统计更新
- 到期检测（run_due_once）→ 触发一次后不重复触发
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select

from api.core.database import SessionLocal, init_db
from api.main import app
from api.models import (
    CollectItem,
    CollectJob,
    CollectPlan,
    CollectSchedule,
    CollectTask,
    ComplianceVerdict,
)
from collect import schedule_runner

PREFIX = "sched-test"
TARGET = "https://sched.test/list"


@pytest.fixture(scope="function")
def session():
    init_db()
    db = SessionLocal()
    yield db
    # 清理顺序遵守外键依赖：verdicts → schedules → items → tasks → jobs → plans
    db.rollback()
    db.execute(
        delete(ComplianceVerdict).where(
            ComplianceVerdict.target_url.like("%sched.test%")
        )
    )
    plan_ids = select(CollectPlan.id).where(CollectPlan.target_url.like("%sched.test%"))
    job_ids = select(CollectJob.id).where(CollectJob.plan_id.in_(plan_ids))
    db.execute(delete(CollectSchedule).where(CollectSchedule.name.like(f"{PREFIX}%")))
    db.execute(delete(CollectItem).where(CollectItem.job_id.in_(job_ids)))
    db.execute(delete(CollectTask).where(CollectTask.job_id.in_(job_ids)))
    db.execute(delete(CollectJob).where(CollectJob.plan_id.in_(plan_ids)))
    db.execute(delete(CollectPlan).where(CollectPlan.target_url.like("%sched.test%")))
    db.commit()
    db.close()


@pytest.fixture()
def plan(session) -> CollectPlan:
    row = CollectPlan(
        target_url=TARGET,
        requirement="schedules test",
        status="ready",
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def _fake_run_job(monkeypatch):
    """把采集执行替换成"直接成功"：不联网、只落任务状态。"""

    async def fake_run_job(self, job_id, **kwargs):  # noqa: ANN001
        job = self.session.get(CollectJob, job_id)
        job.status = "succeeded"
        self.session.commit()
        return job

    monkeypatch.setattr(
        "collect.schedule_runner.CollectScheduler.run_job", fake_run_job
    )


def test_create_schedule_validates_frequency(session, plan):
    client = TestClient(app)

    # hourly 缺 interval_hours
    resp = client.post(
        "/api/v1/collect/schedules",
        json={"name": f"{PREFIX} bad1", "plan_id": plan.id, "frequency": "hourly"},
    )
    assert resp.status_code == 400

    # daily 时间非法
    resp = client.post(
        "/api/v1/collect/schedules",
        json={
            "name": f"{PREFIX} bad2",
            "plan_id": plan.id,
            "frequency": "daily",
            "time_of_day": "25:00",
        },
    )
    assert resp.status_code == 400


def test_create_schedule_missing_plan(session):
    client = TestClient(app)
    resp = client.post(
        "/api/v1/collect/schedules",
        json={"name": f"{PREFIX} noplan", "plan_id": 999999, "frequency": "daily",
              "time_of_day": "06:00"},
    )
    assert resp.status_code == 404


def test_schedule_crud_cycle(session, plan):
    client = TestClient(app)

    # 创建（daily 06:00）
    resp = client.post(
        "/api/v1/collect/schedules",
        json={
            "name": f"{PREFIX} daily",
            "plan_id": plan.id,
            "frequency": "daily",
            "time_of_day": "06:00",
        },
    )
    assert resp.status_code == 200
    schedule = resp.json()["schedule"]
    assert schedule["enabled"] is True
    assert schedule["frequency_text"] == "每天 06:00"
    assert schedule["next_run_at"], "启用状态应计算出下一次执行时间"
    schedule_id = schedule["schedule_id"]

    # 列表
    resp = client.get("/api/v1/collect/schedules")
    assert resp.status_code == 200
    ids = [s["schedule_id"] for s in resp.json()["items"]]
    assert schedule_id in ids

    # 暂停 → next_run 清空
    resp = client.patch(
        f"/api/v1/collect/schedules/{schedule_id}", json={"enabled": False}
    )
    assert resp.status_code == 200
    paused = resp.json()["schedule"]
    assert paused["enabled"] is False
    assert paused["next_run_at"] is None

    # 恢复 → next_run 重算
    resp = client.patch(
        f"/api/v1/collect/schedules/{schedule_id}", json={"enabled": True}
    )
    assert resp.status_code == 200
    resumed = resp.json()["schedule"]
    assert resumed["enabled"] is True
    assert resumed["next_run_at"]

    # 删除
    resp = client.delete(f"/api/v1/collect/schedules/{schedule_id}")
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True

    resp = client.get("/api/v1/collect/schedules")
    ids = [s["schedule_id"] for s in resp.json()["items"]]
    assert schedule_id not in ids


def test_manual_run_creates_job_and_updates_stats(session, plan, monkeypatch):
    _fake_run_job(monkeypatch)
    client = TestClient(app)

    resp = client.post(
        "/api/v1/collect/schedules",
        json={
            "name": f"{PREFIX} manual",
            "plan_id": plan.id,
            "frequency": "daily",
            "time_of_day": "06:00",
        },
    )
    schedule_id = resp.json()["schedule"]["schedule_id"]

    resp = client.post(f"/api/v1/collect/schedules/{schedule_id}/run")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["result"]["status"] == "succeeded"
    assert payload["result"]["job_id"]

    after = payload["schedule"]
    assert after["run_count"] == 1
    assert after["last_job_id"] == payload["result"]["job_id"]
    assert after["last_run_at"]
    assert after["next_run_at"]


def test_due_schedule_triggers_once(session, plan, monkeypatch):
    _fake_run_job(monkeypatch)

    past = datetime.now() - timedelta(minutes=5)
    schedule = CollectSchedule(
        name=f"{PREFIX} due",
        plan_id=plan.id,
        frequency="daily",
        time_of_day="06:00",
        enabled=True,
        next_run_at=past,
    )
    session.add(schedule)
    session.commit()
    session.refresh(schedule)

    results = asyncio.run(schedule_runner.run_due_once(session))
    assert len(results) == 1
    assert results[0]["job_id"]
    assert results[0]["status"] == "succeeded"

    session.refresh(schedule)
    assert schedule.run_count == 1
    assert schedule.last_job_id == results[0]["job_id"]
    assert schedule.next_run_at > datetime.now(), "执行后应重算到未来"

    # 第二轮：没有到期规则，不应重复触发
    results2 = asyncio.run(schedule_runner.run_due_once(session))
    assert results2 == []


def test_disabled_schedule_not_due(session, plan):
    past = datetime.now() - timedelta(minutes=5)
    schedule = CollectSchedule(
        name=f"{PREFIX} disabled",
        plan_id=plan.id,
        frequency="daily",
        time_of_day="06:00",
        enabled=False,
        next_run_at=past,
    )
    session.add(schedule)
    session.commit()

    results = asyncio.run(schedule_runner.run_due_once(session))
    assert results == []


# --------------------------------------------------------------------------- #
# 合规门（无人值守路径只放行 proceed）
# --------------------------------------------------------------------------- #


def _make_verdict(session, plan: CollectPlan, decision: str) -> ComplianceVerdict:
    """为计划构造一条判定记录并挂到计划上。"""
    verdict = ComplianceVerdict(
        verdict_uid=f"{PREFIX}-{decision}-{plan.id}",
        profile_id=None,
        target_url=plan.target_url,
        decision=decision,
        dim_access="A1",
        dim_authorization="B4" if decision != "proceed" else "B1",
        dim_behavior="C1",
        dim_data="D1",
        reasons=["test fixture"],
    )
    session.add(verdict)
    session.commit()
    session.refresh(verdict)
    plan.verdict_uid = verdict.verdict_uid
    session.commit()
    return verdict


def test_create_schedule_rejects_confirm_required_plan(session, plan):
    _make_verdict(session, plan, "confirm_required")
    client = TestClient(app)

    resp = client.post(
        "/api/v1/collect/schedules",
        json={
            "name": f"{PREFIX} bad-plan",
            "plan_id": plan.id,
            "frequency": "daily",
            "time_of_day": "06:00",
        },
    )
    assert resp.status_code == 400
    assert "不可用于调度" in resp.json()["detail"]


def test_create_schedule_accepts_proceed_plan(session, plan):
    _make_verdict(session, plan, "proceed")
    client = TestClient(app)

    resp = client.post(
        "/api/v1/collect/schedules",
        json={
            "name": f"{PREFIX} good-plan",
            "plan_id": plan.id,
            "frequency": "daily",
            "time_of_day": "06:00",
        },
    )
    assert resp.status_code == 200


def test_due_schedule_skips_when_compliance_blocks(session, plan):
    """执行门兜底：判定为 blocked 时跳过执行、不建任务、顺延 next_run。"""
    _make_verdict(session, plan, "blocked")

    past = datetime.now() - timedelta(minutes=5)
    schedule = CollectSchedule(
        name=f"{PREFIX} blocked-exec",
        plan_id=plan.id,
        frequency="daily",
        time_of_day="06:00",
        enabled=True,
        next_run_at=past,
    )
    session.add(schedule)
    session.commit()
    session.refresh(schedule)

    results = asyncio.run(schedule_runner.run_due_once(session))
    assert len(results) == 1
    assert results[0]["status"] == "skipped_compliance"
    assert results[0]["job_id"] is None
    assert "blocked_by_compliance" in results[0]["reason"]

    session.refresh(schedule)
    assert schedule.run_count == 1, "跳过也记录一次尝试"
    assert schedule.next_run_at > datetime.now(), "跳过必须顺延，否则调度循环会死转"

    jobs_for_plan = session.execute(
        select(func.count()).select_from(CollectJob).where(CollectJob.plan_id == plan.id)
    ).scalar_one()
    assert jobs_for_plan == 0, "合规阻断时不应创建采集任务"
