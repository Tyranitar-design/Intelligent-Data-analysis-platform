# -*- coding: utf-8 -*-
"""任务重入恢复（E3）· 集成测试

覆盖：
- resume 把 failed / running 分片重置为 pending 并重新执行（mock run_job）
- done 分片不被重置
- succeeded / pending job 拒绝（400）
- 不存在 job（404）
- 合规门：blocked 判定 → 403
"""
from __future__ import annotations

import secrets

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from api.core.database import SessionLocal, init_db
from api.main import app
from api.models import (
    CollectJob,
    CollectPlan,
    CollectTask,
    ComplianceVerdict,
)

PREFIX = "resume-test"
TARGET = "https://resume.test/list"


@pytest.fixture(scope="function")
def session():
    init_db()
    db = SessionLocal()
    yield db
    db.rollback()
    plan_ids = select(CollectPlan.id).where(
        CollectPlan.target_url.like("%resume.test%")
    )
    job_ids = select(CollectJob.id).where(CollectJob.plan_id.in_(plan_ids))
    db.execute(delete(CollectTask).where(CollectTask.job_id.in_(job_ids)))
    db.execute(delete(CollectJob).where(CollectJob.plan_id.in_(plan_ids)))
    db.execute(
        delete(CollectPlan).where(CollectPlan.target_url.like("%resume.test%"))
    )
    db.execute(
        delete(ComplianceVerdict).where(
            ComplianceVerdict.target_url.like("%resume.test%")
        )
    )
    db.commit()
    db.close()


def _make_plan(session) -> CollectPlan:
    plan = CollectPlan(target_url=TARGET, status="ready")
    session.add(plan)
    session.commit()
    session.refresh(plan)
    return plan


def _make_job_with_tasks(
    session,
    plan: CollectPlan,
    *,
    job_status: str = "failed",
    task_states: tuple[str, ...] = ("failed", "done"),
) -> tuple[CollectJob, list[CollectTask]]:
    job = CollectJob(
        plan_id=plan.id,
        status=job_status,
        total_tasks=len(task_states),
        dedup_stats={},
    )
    session.add(job)
    session.commit()
    session.refresh(job)

    tasks: list[CollectTask] = []
    for state in task_states:
        task = CollectTask(
            job_id=job.id,
            status=state,
            shard_spec={"kind": "root"},
            cursor={"page": 1, "known_streak": 0},
        )
        session.add(task)
        tasks.append(task)
    session.commit()
    for task in tasks:
        session.refresh(task)
    return job, tasks


def _fake_run_job(monkeypatch, calls: list):
    async def fake_run(self, job_id, **kwargs):
        calls.append(job_id)
        job = self.session.get(CollectJob, job_id)
        job.status = "succeeded"
        self.session.commit()
        return job

    monkeypatch.setattr(
        "collect.scheduler.CollectScheduler.run_job", fake_run
    )


def test_resume_resets_failed_and_reruns(session, monkeypatch):
    plan = _make_plan(session)
    job, tasks = _make_job_with_tasks(session, plan, task_states=("failed", "done"))
    calls: list[int] = []
    _fake_run_job(monkeypatch, calls)

    client = TestClient(app)
    resp = client.post(f"/api/v1/collect/jobs/{job.id}/resume")
    assert resp.status_code == 200
    assert calls == [job.id], "resume 应触发一次 run_job"

    session.expire_all()  # 请求内（另一 session）的修改：使本地缓存失效后重读
    statuses = {
        task.id: task.status
        for task in session.execute(
            select(CollectTask).where(CollectTask.job_id == job.id)
        ).scalars()
    }
    assert statuses[tasks[0].id] == "pending", "failed 分片应被重置为 pending"
    assert statuses[tasks[1].id] == "done", "done 分片不应被重置"

    session.refresh(job)
    assert job.status == "succeeded"


def test_resume_also_recovers_stuck_running(session, monkeypatch):
    """进程中断残留的 running 分片（与 running 状态的 job）也可恢复。"""
    plan = _make_plan(session)
    job, tasks = _make_job_with_tasks(
        session, plan, job_status="running", task_states=("running",)
    )
    calls: list[int] = []
    _fake_run_job(monkeypatch, calls)

    client = TestClient(app)
    resp = client.post(f"/api/v1/collect/jobs/{job.id}/resume")
    assert resp.status_code == 200
    assert calls == [job.id]


def test_resume_rejects_succeeded(session):
    plan = _make_plan(session)
    job, _ = _make_job_with_tasks(
        session, plan, job_status="succeeded", task_states=("done",)
    )
    client = TestClient(app)
    resp = client.post(f"/api/v1/collect/jobs/{job.id}/resume")
    assert resp.status_code == 400
    assert "可重入恢复" in resp.json()["detail"] or "可重试" in resp.json()["detail"]


def test_resume_missing_job_404(session):
    client = TestClient(app)
    resp = client.post("/api/v1/collect/jobs/999999/resume")
    assert resp.status_code == 404


def test_resume_blocked_by_compliance(session):
    plan = _make_plan(session)
    verdict = ComplianceVerdict(
        verdict_uid=f"{PREFIX}-v-{secrets.token_hex(4)}",
        profile_id=None,
        target_url=TARGET,
        decision="blocked",
        dim_access="A4",
        dim_authorization="B4",
        dim_behavior="C1",
        dim_data="D1",
        reasons=["test fixture"],
    )
    session.add(verdict)
    session.commit()
    plan.verdict_uid = verdict.verdict_uid
    session.commit()

    job, _ = _make_job_with_tasks(session, plan, task_states=("failed",))
    client = TestClient(app)
    resp = client.post(f"/api/v1/collect/jobs/{job.id}/resume")
    assert resp.status_code == 403
