# -*- coding: utf-8 -*-
"""审计点覆盖（v4 §4.9 补全）· 集成测试

覆盖：
- ``dataset.materialize``：物化写审计
- ``export.dataset``：导出写审计
- ``collect.resume``：重入恢复写审计（mock run_job）
- ``collect.run`` 的执行类审计与 resume 同构（此处以 resume 代表）
"""
from __future__ import annotations

import secrets

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from api.core.database import SessionLocal, init_db
from api.main import app
from api.models import (
    AuditLog,
    CollectItem,
    CollectJob,
    CollectPlan,
    CollectTask,
    Dataset,
)
from pipeline.storage import DatasetMaterializer

PREFIX = "auditp-test"
TARGET = "https://auditp.test/list"


@pytest.fixture(scope="function")
def session():
    init_db()
    db = SessionLocal()
    yield db
    db.rollback()
    # 清理顺序：审计 → 数据集（含物理表）→ items → tasks → jobs → plans
    db.execute(
        delete(AuditLog).where(
            AuditLog.principal_id.in_(("web-console", "scheduler"))
        )
    )
    plan_ids = select(CollectPlan.id).where(
        CollectPlan.target_url.like("%auditp.test%")
    )
    job_ids = select(CollectJob.id).where(CollectJob.plan_id.in_(plan_ids))
    materializer = DatasetMaterializer(db)
    # 前缀名 + collect_job_id 双条件（materialize 端点产出的数据集是默认名）
    for row in (
        db.execute(
            select(Dataset).where(
                Dataset.name.like(f"{PREFIX}%")
                | Dataset.collect_job_id.in_(job_ids)
            )
        )
        .scalars()
        .all()
    ):
        materializer.drop_dataset(row.id)
    db.execute(delete(CollectItem).where(CollectItem.job_id.in_(job_ids)))
    db.execute(delete(CollectTask).where(CollectTask.job_id.in_(job_ids)))
    db.execute(delete(CollectJob).where(CollectJob.plan_id.in_(plan_ids)))
    db.execute(
        delete(CollectPlan).where(CollectPlan.target_url.like("%auditp.test%"))
    )
    db.commit()
    db.close()


def _make_job(session, *, job_status: str = "succeeded") -> tuple[CollectPlan, CollectJob]:
    plan = CollectPlan(target_url=TARGET, status="ready")
    session.add(plan)
    session.commit()
    session.refresh(plan)
    job = CollectJob(
        plan_id=plan.id,
        status=job_status,
        total_tasks=1,
        done_tasks=1 if job_status == "succeeded" else 0,
        items_count=1,
        dedup_stats={},
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    return plan, job


def _make_item(session, job: CollectJob) -> CollectItem:
    task = CollectTask(job_id=job.id, status="done", shard_spec={"kind": "root"})
    session.add(task)
    session.commit()
    session.refresh(task)
    item = CollectItem(
        job_id=job.id,
        task_id=task.id,
        item_key=f"{PREFIX}-{secrets.token_hex(6)}",
        source_url=f"{TARGET}/1",
        payload={"title": "审计点测试"},
        completeness=1.0,
    )
    session.add(item)
    session.commit()
    return item


def test_materialize_writes_audit(session):
    _, job = _make_job(session)
    _make_item(session, job)

    client = TestClient(app)
    resp = client.post(f"/api/v1/collect/jobs/{job.id}/materialize")
    assert resp.status_code == 200
    dataset_id = resp.json()["id"]

    session.expire_all()
    log = (
        session.execute(
            select(AuditLog).where(
                AuditLog.action == "dataset.materialize",
                AuditLog.target_id == str(dataset_id),
            )
        )
        .scalars()
        .first()
    )
    assert log is not None, "物化应写审计"
    assert log.principal_id == "web-console"
    assert log.result == "ok"
    assert (log.detail or {}).get("row_count") == 1


def test_export_writes_audit(session):
    materializer = DatasetMaterializer(session)
    dataset = materializer.materialize_records(
        [{"title": "a"}, {"title": "b"}],
        name=f"{PREFIX}-export",
        source_type="test",
        apply_pii=False,
    )

    client = TestClient(app)
    resp = client.get(
        f"/api/v1/analytics/export/{dataset.id}", params={"format": "csv"}
    )
    assert resp.status_code == 200

    session.expire_all()
    log = (
        session.execute(
            select(AuditLog).where(
                AuditLog.action == "export.dataset",
                AuditLog.target_id == str(dataset.id),
            )
        )
        .scalars()
        .first()
    )
    assert log is not None, "导出应写审计"
    assert (log.detail or {}).get("format") == "csv"


def test_resume_writes_audit(session, monkeypatch):
    _, job = _make_job(session, job_status="failed")

    async def fake_run(self, job_id, **kwargs):
        target = self.session.get(CollectJob, job_id)
        target.status = "succeeded"
        self.session.commit()
        return target

    monkeypatch.setattr("collect.scheduler.CollectScheduler.run_job", fake_run)

    client = TestClient(app)
    resp = client.post(f"/api/v1/collect/jobs/{job.id}/resume")
    assert resp.status_code == 200

    session.expire_all()
    log = (
        session.execute(
            select(AuditLog).where(
                AuditLog.action == "collect.resume",
                AuditLog.target_id == str(job.id),
            )
        )
        .scalars()
        .first()
    )
    assert log is not None, "重入恢复应写审计"
    assert log.result == "ok"
