"""
定时调度运行器
==============

在采集编排器（``collect.scheduler.CollectScheduler``）之上加一层"定时器"：

- ``compute_next_run``   纯函数：结构化频率 → 下一次执行时间（零依赖）
- ``due_schedules``      找出到期的规则
- ``execute_schedule``   执行一条规则：创建任务 + 运行 + 更新规则状态
- ``run_due_once``       执行一轮（检查 + 触发）
- ``schedule_loop``      常驻循环（由应用 lifespan 启动）

设计约束：

1. 时间口径统一用**本机时间**（naive datetime），与调度模型一致。
2. 重复执行不会造成重复数据 —— 三级去重已兜底；失败的周期照常顺延，
   不堆叠补跑（积压时只顺延到下一个未来时刻）。
3. 循环周期由 ``SCHEDULE_TICK_SECONDS`` 控制，测试环境可缩短。
4. 循环只属于长驻进程（uvicorn）；pytest 的 TestClient 不触发 lifespan，
   因此测试不会意外启动循环（需要测 tick 时直接调 ``run_due_once``）。
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Callable, Iterable, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from api.models import CollectPlan, CollectSchedule, ComplianceVerdict
from collect.scheduler import CollectScheduler
from mcp.audit import record as record_audit

logger = logging.getLogger(__name__)

_HOURLY_CATCHUP_LIMIT = 1000  # 积压顺延的迭代上限（防御异常输入）


# --------------------------------------------------------------------------- #
# 纯函数：频率校验与下一次执行时间
# --------------------------------------------------------------------------- #


def _parse_hhmm(value) -> tuple[int, int]:
    """解析 "HH:MM"。非法输入抛 ``ValueError``。"""
    if not isinstance(value, str) or ":" not in value:
        raise ValueError(f"time_of_day 需要 HH:MM 格式，收到: {value!r}")
    hour_text, minute_text = value.strip().split(":", 1)
    hour, minute = int(hour_text), int(minute_text)
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(f"time_of_day 超出范围: {value!r}")
    return hour, minute


def validate_frequency(
    frequency: str,
    *,
    interval_hours=None,
    time_of_day=None,
    weekday=None,
) -> None:
    """校验频率参数组合；不合法抛 ``ValueError``（API 层转 400）。"""
    if frequency == "hourly":
        if interval_hours is None or not (1 <= int(interval_hours) <= 24):
            raise ValueError("hourly 频率需要 interval_hours 在 1-24 之间")
    elif frequency == "daily":
        _parse_hhmm(time_of_day)
    elif frequency == "weekly":
        _parse_hhmm(time_of_day)
        if weekday is None or not (0 <= int(weekday) <= 6):
            raise ValueError("weekly 频率需要 weekday 在 0-6 之间（0=周一）")
    else:
        raise ValueError(f"不支持的频率: {frequency!r}（可选 hourly / daily / weekly）")


def _get(schedule, key):
    if isinstance(schedule, dict):
        return schedule.get(key)
    return getattr(schedule, key, None)


def compute_next_run(
    schedule,
    *,
    base: Optional[datetime] = None,
    now: Optional[datetime] = None,
) -> datetime:
    """计算下一次执行时间（本机时间）。

    ``schedule`` 支持 ORM 对象或 dict（读取 frequency / interval_hours /
    time_of_day / weekday 字段）。``base`` 为计时基准（通常传"上次运行
    时间"）；不传则由 ``now`` 起算。
    """
    now = now or datetime.now()
    frequency = _get(schedule, "frequency")

    if frequency == "hourly":
        interval = int(_get(schedule, "interval_hours") or 1)
        interval = max(1, min(24, interval))
        cursor = (base or now) + timedelta(hours=interval)
        for _ in range(_HOURLY_CATCHUP_LIMIT):  # 积压时只顺延到未来，不补跑
            if cursor > now:
                break
            cursor += timedelta(hours=interval)
        return cursor

    if frequency == "daily":
        hour, minute = _parse_hhmm(_get(schedule, "time_of_day"))
        candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if candidate <= now:
            candidate += timedelta(days=1)
        return candidate

    if frequency == "weekly":
        hour, minute = _parse_hhmm(_get(schedule, "time_of_day"))
        weekday = int(_get(schedule, "weekday") if _get(schedule, "weekday") is not None else 0)
        weekday = max(0, min(6, weekday))
        days_ahead = (weekday - now.weekday()) % 7
        candidate = (now + timedelta(days=days_ahead)).replace(
            hour=hour, minute=minute, second=0, microsecond=0
        )
        if candidate <= now:
            candidate += timedelta(days=7)
        return candidate

    raise ValueError(f"不支持的频率: {frequency!r}")


# --------------------------------------------------------------------------- #
# 到期筛选与执行
# --------------------------------------------------------------------------- #


def due_schedules(db: Session, *, now: Optional[datetime] = None) -> list[CollectSchedule]:
    """返回当前到期的规则（启用且有 next_run_at 且已到点）。"""
    now = now or datetime.now()
    rows = (
        db.execute(
            select(CollectSchedule)
            .where(
                CollectSchedule.enabled.is_(True),
                CollectSchedule.next_run_at.is_not(None),
                CollectSchedule.next_run_at <= now,
            )
            .order_by(CollectSchedule.next_run_at)
        )
        .scalars()
        .all()
    )
    return list(rows)


def load_plan_verdict(db: Session, plan: CollectPlan):
    """取计划关联的判定记录；无 verdict_uid 时返回 None。"""
    if not plan.verdict_uid:
        return None
    return (
        db.execute(
            select(ComplianceVerdict)
            .where(ComplianceVerdict.verdict_uid == plan.verdict_uid)
            .limit(1)
        )
        .scalars()
        .first()
    )


def compliance_block_reason(verdict) -> Optional[str]:
    """无人值守路径的合规门。

    返回拒绝原因字符串；``None`` 表示放行。

    - ``blocked``：硬边界（技术措施 / 凭证来源 / 数据属性），不执行；
    - ``confirm_required``：无人值守没有"补齐授权"的人工环节，
      跳过等待人工处理（与"受限层挂起等声明"的授权确认流程一致）；
    - ``proceed`` / 无判定记录：放行（与 ``/run`` 端点对无判定的既有行为一致）。
    """
    if verdict is None:
        return None
    if verdict.decision == "blocked":
        reasons = list(verdict.reasons or [])
        return "blocked_by_compliance" + (f": {reasons[0]}" if reasons else "")
    if verdict.decision == "confirm_required":
        return (
            "authorization_required: 该目标等待授权确认，"
            "需补齐授权声明后重建计划再启用调度"
        )
    return None


async def execute_schedule(
    db: Session,
    schedule: CollectSchedule,
    *,
    now: Optional[datetime] = None,
) -> dict:
    """执行一条规则：合规门 → 创建任务 → 运行 → 更新规则状态。

    合规门与 ``/run`` 端点同源：**无人值守路径只放行 ``proceed`` 的计划**。
    失败不抛出：采集链路内部已有降级与错误落库；这里只负责把结果
    反映到规则统计（run_count / fail_count / last_job_id）。
    """
    now = now or datetime.now()

    plan = db.get(CollectPlan, schedule.plan_id)
    if plan is None:
        schedule.enabled = False
        schedule.next_run_at = None
        db.commit()
        logger.warning("调度规则 %s 的计划 %s 不存在，已自动停用", schedule.id, schedule.plan_id)
        return {"schedule_id": schedule.id, "status": "plan_missing", "job_id": None}

    # 合规门：跳过也要顺延 next_run（否则调度循环会每轮重试）
    block_reason = compliance_block_reason(load_plan_verdict(db, plan))
    if block_reason:
        schedule.last_run_at = now
        schedule.run_count = (schedule.run_count or 0) + 1
        schedule.next_run_at = compute_next_run(schedule, base=now, now=now)
        db.commit()
        record_audit(
            db,
            principal_id="scheduler",
            action="collect.schedule_run",
            result="denied",
            target_type="collect_schedule",
            target_id=str(schedule.id),
            detail={"reason": block_reason},
        )
        logger.warning("调度跳过（合规）：schedule=%s reason=%s", schedule.id, block_reason)
        return {
            "schedule_id": schedule.id,
            "status": "skipped_compliance",
            "job_id": None,
            "reason": block_reason,
        }

    scheduler = CollectScheduler(db)
    job = await scheduler.create_job(plan)
    run_status = job.status

    try:
        job = await scheduler.run_job(job.id)
        run_status = job.status
    except Exception:  # noqa: BLE001 - 执行异常不能拖垮循环
        logger.exception("调度执行异常 schedule=%s job=%s", schedule.id, job.id)
        run_status = "failed"

    schedule.last_run_at = now
    schedule.last_job_id = job.id
    schedule.run_count = (schedule.run_count or 0) + 1
    if run_status == "failed":
        schedule.fail_count = (schedule.fail_count or 0) + 1
    schedule.next_run_at = compute_next_run(schedule, base=now, now=now)
    db.commit()

    record_audit(
        db,
        principal_id="scheduler",
        action="collect.schedule_run",
        result="ok" if run_status != "failed" else "error",
        target_type="collect_schedule",
        target_id=str(schedule.id),
        detail={"job_id": job.id, "status": run_status},
    )

    logger.info(
        "调度执行完成 schedule=%s job=%s status=%s next=%s",
        schedule.id, job.id, run_status, schedule.next_run_at,
    )
    return {"schedule_id": schedule.id, "status": run_status, "job_id": job.id}


async def run_due_once(
    db: Session, *, now: Optional[datetime] = None
) -> list[dict]:
    """执行一轮：检查到期规则并逐条触发。返回各条的执行结果摘要。"""
    results: list[dict] = []
    for schedule in due_schedules(db, now=now):
        results.append(await execute_schedule(db, schedule, now=now))
    return results


# --------------------------------------------------------------------------- #
# 常驻循环
# --------------------------------------------------------------------------- #


async def schedule_loop(
    db_factory: Callable,
    interval_seconds: float = 15.0,
) -> None:
    """常驻调度循环。

    ``db_factory`` 返回数据库会话上下文管理器（如
    ``api.core.database.get_db_session``）。循环异常自愈：单轮失败只记日志，
    不影响后续轮次。
    """
    logger.info("调度循环启动，检查间隔 %.1fs", interval_seconds)
    while True:
        try:
            with db_factory() as db:
                results = await run_due_once(db)
                if results:
                    logger.info("调度循环执行 %d 条规则", len(results))
        except Exception:  # noqa: BLE001 - 循环必须自愈
            logger.exception("调度循环单轮异常")
        await asyncio.sleep(interval_seconds)
