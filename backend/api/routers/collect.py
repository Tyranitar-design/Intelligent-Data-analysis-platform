"""
采集路由
========

- ``POST /api/v1/collect/plan``       创建采集计划（不产生网络请求）
- ``POST /api/v1/collect/run``        执行计划（合规强制点在此拦截）
- ``GET  /api/v1/collect/jobs``       任务列表
- ``GET  /api/v1/collect/jobs/{id}``  任务详情
- ``GET  /api/v1/collect/items``      数据条目查询
- ``GET  /api/v1/collect/registry``   注册的能力清单
- ``GET  /api/v1/collect/plans``      采集计划列表
- ``GET  /api/v1/collect/schedules``  调度规则（列表 / 创建 / 更新 / 删除）
- ``POST /api/v1/collect/schedules/{id}/run``  立即执行一次调度
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
    CollectSchedule,
    CollectTask,
    ComplianceVerdict,
    Dataset,
    SiteProfile,
)
from api.schemas.collect import PlanRequest, RunRequest, ScheduleCreate, ScheduleUpdate
from collect.registry import build_default_registry
from collect.schedule_runner import (
    compliance_block_reason,
    compute_next_run,
    execute_schedule,
    load_plan_verdict,
    validate_frequency,
)
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
# 物化
# --------------------------------------------------------------------------- #


@router.post("/jobs/{job_id}/materialize", summary="把采集结果物化成数据集")
def materialize_collect_job(
    job_id: int,
    name: str | None = Query(None, description="数据集名称"),
    apply_pii: bool = Query(True, description="是否执行 PII 字段级最小化（默认开启）"),
    db: Session = Depends(get_db),
) -> dict:
    """把采集任务的条目汇总成可分析的数据集。

    过程：规范化 → PII 最小化 → 落成真实表 → 记录字段级血缘。
    """
    from pipeline.storage import DatasetMaterializer

    materializer = DatasetMaterializer(db)
    try:
        dataset = materializer.materialize_job(
            job_id, name=name, apply_pii=apply_pii
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return dataset.to_dict()


@router.get("/datasets/{dataset_id}/preview", summary="预览数据集内容")
def preview_dataset(
    dataset_id: int,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> dict:
    """按页读取物化后的数据集内容。"""
    from pipeline.storage import DatasetMaterializer

    materializer = DatasetMaterializer(db)
    try:
        return materializer.read_dataset(dataset_id, limit=limit, offset=offset)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/datasets", summary="数据集列表（元数据）")
def list_datasets(
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> dict:
    """列出已物化的数据集元数据（供对比 / 选择场景）。"""
    rows = (
        db.execute(select(Dataset).order_by(Dataset.id.desc()).limit(limit))
        .scalars()
        .all()
    )
    return {
        "items": [
            {
                "dataset_id": row.id,
                "name": row.name,
                "row_count": row.row_count,
                "column_count": row.column_count,
                "created_at": (
                    row.created_at.isoformat() if row.created_at else None
                ),
            }
            for row in rows
        ]
    }


@router.get("/datasets/{dataset_id}/search", summary="检索数据集内容")
def search_dataset(
    dataset_id: int,
    q: str | None = Query(None, description="关键字（LIKE 匹配；为空则全量分页）"),
    field: str | None = Query(None, description="限定字段（需在数据集 schema 内）"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> dict:
    """在物化表上做关键字 / 字段检索。"""
    from pipeline.storage import DatasetMaterializer

    if db.get(Dataset, dataset_id) is None:
        raise HTTPException(status_code=404, detail="数据集不存在")

    materializer = DatasetMaterializer(db)
    try:
        return materializer.search_dataset(
            dataset_id, q=q, field=field, limit=limit, offset=offset
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/datasets/diff", summary="对比两个数据集")
def diff_datasets(
    a: int = Query(..., description="数据集 A 的 ID"),
    b: int = Query(..., description="数据集 B 的 ID"),
    db: Session = Depends(get_db),
) -> dict:
    """对比两个数据集的 schema 与统计差异（适合同一来源的两次采集对比）。"""
    from pipeline.storage import DatasetMaterializer

    materializer = DatasetMaterializer(db)
    try:
        return materializer.diff_datasets(a, b)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


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


# --------------------------------------------------------------------------- #
# 计划查询
# --------------------------------------------------------------------------- #


@router.get("/plans", summary="采集计划列表")
def list_plans(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> dict:
    total = db.execute(select(func.count()).select_from(CollectPlan)).scalar_one()
    rows = (
        db.execute(
            select(CollectPlan)
            .order_by(CollectPlan.id.desc())
            .limit(limit)
            .offset(offset)
        )
        .scalars()
        .all()
    )
    return {"total": total, "items": [r.to_dict() for r in rows]}


# --------------------------------------------------------------------------- #
# 调度规则
# --------------------------------------------------------------------------- #


@router.get("/schedules", summary="调度规则列表")
def list_schedules(db: Session = Depends(get_db)) -> dict:
    now = datetime.now()
    rows = (
        db.execute(select(CollectSchedule).order_by(CollectSchedule.id.desc()))
        .scalars()
        .all()
    )
    return {"items": [r.to_dict(now=now) for r in rows]}


@router.post("/schedules", summary="创建调度规则")
def create_schedule(payload: ScheduleCreate, db: Session = Depends(get_db)) -> dict:
    plan = db.get(CollectPlan, payload.plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="采集计划不存在")

    # 合规预检：无人值守路径只接受可执行（proceed）的计划
    block_reason = compliance_block_reason(load_plan_verdict(db, plan))
    if block_reason:
        raise HTTPException(
            status_code=400,
            detail=f"该计划当前不可用于调度：{block_reason}",
        )

    try:
        validate_frequency(
            payload.frequency,
            interval_hours=payload.interval_hours,
            time_of_day=payload.time_of_day,
            weekday=payload.weekday,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    now = datetime.now()
    schedule = CollectSchedule(
        name=payload.name,
        plan_id=payload.plan_id,
        frequency=payload.frequency,
        interval_hours=payload.interval_hours,
        time_of_day=payload.time_of_day,
        weekday=payload.weekday,
        enabled=payload.enabled,
    )
    if schedule.enabled:
        schedule.next_run_at = compute_next_run(schedule, now=now)

    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return {"schedule": schedule.to_dict(now=now)}


@router.patch("/schedules/{schedule_id}", summary="更新调度规则")
def update_schedule(
    schedule_id: int, payload: ScheduleUpdate, db: Session = Depends(get_db)
) -> dict:
    schedule = db.get(CollectSchedule, schedule_id)
    if schedule is None:
        raise HTTPException(status_code=404, detail="调度规则不存在")

    if payload.name is not None:
        schedule.name = payload.name
    if payload.interval_hours is not None:
        schedule.interval_hours = payload.interval_hours
    if payload.time_of_day is not None:
        schedule.time_of_day = payload.time_of_day
    if payload.weekday is not None:
        schedule.weekday = payload.weekday

    try:
        validate_frequency(
            schedule.frequency,
            interval_hours=schedule.interval_hours,
            time_of_day=schedule.time_of_day,
            weekday=schedule.weekday,
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if payload.enabled is not None:
        schedule.enabled = payload.enabled

    now = datetime.now()
    schedule.next_run_at = (
        compute_next_run(schedule, base=schedule.last_run_at, now=now)
        if schedule.enabled
        else None
    )
    db.commit()
    db.refresh(schedule)
    return {"schedule": schedule.to_dict(now=now)}


@router.delete("/schedules/{schedule_id}", summary="删除调度规则")
def delete_schedule(schedule_id: int, db: Session = Depends(get_db)) -> dict:
    schedule = db.get(CollectSchedule, schedule_id)
    if schedule is None:
        raise HTTPException(status_code=404, detail="调度规则不存在")
    db.delete(schedule)
    db.commit()
    return {"deleted": True, "schedule_id": schedule_id}


@router.post("/schedules/{schedule_id}/run", summary="立即执行一次调度")
async def run_schedule_now(
    schedule_id: int, db: Session = Depends(get_db)
) -> dict:
    """手动触发一条规则：与调度循环共用 ``execute_schedule`` 执行路径。"""
    schedule = db.get(CollectSchedule, schedule_id)
    if schedule is None:
        raise HTTPException(status_code=404, detail="调度规则不存在")

    result = await execute_schedule(db, schedule)
    return {"result": result, "schedule": schedule.to_dict()}
