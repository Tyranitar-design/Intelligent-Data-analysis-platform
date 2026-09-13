"""
采集路由
========

- ``POST /api/v1/collect/plan``       创建采集计划（不产生网络请求）
- ``POST /api/v1/collect/run``        执行计划（合规强制点在此拦截）
- ``GET  /api/v1/collect/jobs``       任务列表
- ``GET  /api/v1/collect/jobs/{id}``  任务详情
- ``GET  /api/v1/collect/items``      数据条目查询
- ``GET  /api/v1/collect/registry``   注册的能力清单
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.core.database import get_db
from api.models import (
    CollectItem,
    CollectJob,
    CollectPlan,
    CollectTask,
    ComplianceVerdict,
    SiteProfile,
)
from api.schemas.collect import PlanRequest, RunRequest
from collect.registry import build_default_registry
from collect.scheduler import CollectScheduler
from discover.profile import SiteProfiler

logger = logging.getLogger(__name__)
router = APIRouter()


# --------------------------------------------------------------------------- #
# 计划
# --------------------------------------------------------------------------- #


@router.post("/plan", summary="创建采集计划")
async def create_plan(payload: PlanRequest, db: Session = Depends(get_db)) -> dict:
    """生成采集计划。

    这一步**不产生任何网络请求**——它只是把画像、需求与策略整理成可复核的方案。
    真正的请求发生在 ``/run``。
    """
    profile = None
    if payload.profile_id is not None:
        profile = db.get(SiteProfile, payload.profile_id)
        if profile is None:
            raise HTTPException(status_code=404, detail="画像不存在")

    # 无画像时现场判别一次
    verdict_payload: dict | None = None
    if profile is None:
        profiler = SiteProfiler(db)
        analyzed = await profiler.analyze(
            payload.url, declared_authorization=payload.declared_authorization
        )
        profile = db.get(SiteProfile, analyzed.profile["profile_id"])
        verdict_payload = analyzed.verdict

    profile_dict = profile.to_dict()

    # 判定：优先取本次结果，其次取该画像最近一次留痕
    if verdict_payload is None:
        row = (
            db.execute(
                select(ComplianceVerdict)
                .where(ComplianceVerdict.profile_id == profile.id)
                .order_by(ComplianceVerdict.id.desc())
                .limit(1)
            )
            .scalars()
            .first()
        )
        verdict_payload = row.to_dict() if row else {}

    fields = _select_fields(profile_dict, payload.requirement)
    strategy = profile_dict.get("strategy") or {}
    rate = dict(strategy.get("rate") or {})
    rate.setdefault("base_per_second", 1.0)
    rate.setdefault("min_per_second", 0.1)
    rate.setdefault("max_concurrency_per_domain", 2)

    plan = CollectPlan(
        profile_id=profile.id,
        target_url=payload.url,
        requirement=payload.requirement,
        field_mapping=fields,
        strategy_chain=list(strategy.get("chain") or []),
        rate_policy=rate,
        incremental_policy=dict(strategy.get("incremental") or {}),
        verdict_uid=verdict_payload.get("verdict_id"),
        status="ready",
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)

    return {
        "plan": plan.to_dict(),
        "compliance": verdict_payload,
        "field_count": len(fields),
    }


# --------------------------------------------------------------------------- #
# 执行
# --------------------------------------------------------------------------- #


@router.post("/run", summary="执行采集计划")
async def run_plan(payload: RunRequest, db: Session = Depends(get_db)) -> dict:
    """执行采集计划。

    合规强制点（第二层防线）：判定为 ``blocked`` 直接拒绝；
    ``confirm_required`` 必须携带有效令牌。
    """
    plan = db.get(CollectPlan, payload.plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="采集计划不存在")

    verdict = None
    if plan.verdict_uid:
        verdict = (
            db.execute(
                select(ComplianceVerdict)
                .where(ComplianceVerdict.verdict_uid == plan.verdict_uid)
                .limit(1)
            )
            .scalars()
            .first()
        )

    if verdict is not None:
        if verdict.decision == "blocked":
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "blocked_by_compliance",
                    "message": "该目标处于技术隔离或数据属性受限，不执行采集",
                    "reasons": verdict.reasons or [],
                    "alternatives": verdict.alternatives or [],
                    "coverage_estimate": verdict.coverage_estimate,
                },
            )
        if verdict.decision == "confirm_required":
            if not payload.authorization_token:
                raise HTTPException(
                    status_code=403,
                    detail={
                        "error": "authorization_required",
                        "message": "需先补齐授权声明",
                        "conditions": verdict.conditions or [],
                    },
                )
            if payload.authorization_token != verdict.authorization_token:
                raise HTTPException(
                    status_code=403,
                    detail={"error": "invalid_token", "message": "令牌不匹配"},
                )
            expires = verdict.token_expires_at
            if expires is not None:
                now = datetime.now(timezone.utc)
                exp = (
                    expires
                    if expires.tzinfo
                    else expires.replace(tzinfo=timezone.utc)
                )
                if now > exp:
                    raise HTTPException(
                        status_code=403,
                        detail={"error": "token_expired", "message": "令牌已过期，请重新判别"},
                    )

    scheduler = CollectScheduler(db)
    job = await scheduler.create_job(plan, max_items=payload.max_items)

    try:
        job = await scheduler.run_job(job.id)
    except Exception as exc:  # noqa: BLE001 - 执行失败要回传状态而非 500
        logger.exception("采集执行失败 job=%s", job.id)
        job.status = "failed"
        job.finished_at = datetime.now(timezone.utc)
        job.error_dist = {"execution_error": 1}
        db.commit()
        return {"job": job.to_dict(), "error": str(exc)[:300]}

    return {"job": job.to_dict()}


# --------------------------------------------------------------------------- #
# 查询
# --------------------------------------------------------------------------- #


@router.get("/jobs", summary="采集任务列表")
def list_jobs(
    status: str | None = Query(None),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> dict:
    stmt = select(CollectJob)
    count_stmt = select(func.count()).select_from(CollectJob)
    if status:
        stmt = stmt.where(CollectJob.status == status)
        count_stmt = count_stmt.where(CollectJob.status == status)

    total = db.execute(count_stmt).scalar_one()
    rows = (
        db.execute(
            stmt.order_by(CollectJob.id.desc()).limit(limit).offset(offset)
        )
        .scalars()
        .all()
    )
    return {"total": total, "items": [r.to_dict() for r in rows]}


@router.get("/jobs/{job_id}", summary="采集任务详情")
def get_job(job_id: int, db: Session = Depends(get_db)) -> dict:
    job = db.get(CollectJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="采集任务不存在")

    tasks = (
        db.execute(select(CollectTask).where(CollectTask.job_id == job_id))
        .scalars()
        .all()
    )
    payload = job.to_dict()
    payload["tasks"] = [
        {
            "task_id": t.id,
            "status": t.status,
            "capability": t.capability_used,
            "attempts": t.attempts,
            "last_error": t.last_error,
            "cursor": t.cursor,
        }
        for t in tasks
    ]
    return payload


@router.get("/items", summary="采集数据条目")
def list_items(
    job_id: int | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> dict:
    stmt = select(CollectItem)
    count_stmt = select(func.count()).select_from(CollectItem)
    if job_id is not None:
        stmt = stmt.where(CollectItem.job_id == job_id)
        count_stmt = count_stmt.where(CollectItem.job_id == job_id)

    total = db.execute(count_stmt).scalar_one()
    rows = (
        db.execute(stmt.order_by(CollectItem.id.desc()).limit(limit).offset(offset))
        .scalars()
        .all()
    )
    return {
        "total": total,
        "items": [
            {
                "item_id": r.id,
                "job_id": r.job_id,
                "source_url": r.source_url,
                "verdict_row_id": r.verdict_id,
                "completeness": r.completeness,
                "version": r.item_version,
                "payload": r.payload,
                "first_seen": r.first_seen.isoformat() if r.first_seen else None,
                "last_seen": r.last_seen.isoformat() if r.last_seen else None,
            }
            for r in rows
        ],
    }


@router.get("/registry", summary="已注册的采集能力")
def list_capabilities() -> dict:
    return {"capabilities": build_default_registry().describe()}


# --------------------------------------------------------------------------- #
# 辅助
# --------------------------------------------------------------------------- #


def _select_fields(profile: dict, requirement: str | None) -> list[dict]:
    """按需求筛选字段；需求为空则返回全部高覆盖字段。

    这里做的是关键词匹配——真正的语义筛选留给后续的 LLM 辅助层，
    当前规则版本保证"没有需求时也能给出完整可采字段"。
    """
    fields = list(profile.get("fields") or [])
    if not requirement:
        return [f for f in fields if float(f.get("coverage") or 0) >= 0.4]

    keyword_map = {
        "标题": ("title", "headline", "name"),
        "时间": ("publish_date", "datePublished", "date", "published", "updated"),
        "日期": ("publish_date", "datePublished", "date", "published", "updated"),
        "作者": ("author", "creator"),
        "正文": ("content", "articleBody", "description", "summary"),
        "内容": ("content", "articleBody", "description", "summary"),
        "价格": ("price", "offers"),
        "摘要": ("description", "summary"),
    }

    wanted: set[str] = set()
    for keyword, names in keyword_map.items():
        if keyword in requirement:
            wanted.update(names)

    if not wanted:
        return [f for f in fields if float(f.get("coverage") or 0) >= 0.4]

    return [f for f in fields if f.get("name") in wanted]
