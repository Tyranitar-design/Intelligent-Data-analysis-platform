"""
采集调度器
==========

从采集计划创建任务、按能力链执行、处理降级、落库去重、汇总统计。

执行契约：

1. 任务执行前必须能取到合规判定（无判定则不执行）
2. 能力链按评分排序，``DEGRADE`` 时自动降级到下一候选
3. ``FAILED`` 是硬失败（如被目标拒绝），不再继续降级
4. 入库前过三级去重，每条数据关联判定留痕
5. 任务状态与游标落库，任务中断后可从游标续跑
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.models import (
    CollectItem,
    CollectJob,
    CollectPlan,
    CollectTask,
    ComplianceVerdict,
    SiteProfile,
)
from collect.capabilities import PageFetcher
from collect.dedup import hamming_distance, make_item_key, simhash64, to_signed64, to_unsigned64
from collect.ratelimit import AdaptiveRateLimiter
from collect.registry import (
    CapabilityRegistry,
    CollectRequest,
    ExecContext,
    ResultStatus,
    build_default_registry,
)
from discover.fetcher import DEFAULT_USER_AGENT, robots_from_profile

logger = logging.getLogger(__name__)

DEFAULT_HAMMING_THRESHOLD = 3
REQUEST_TIMEOUT = 20.0
DEFAULT_MAX_ITEMS = 200


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class TaskOutcome:
    """单个分片的执行结果摘要。"""

    task_id: int
    status: str
    capability: Optional[str] = None
    items_count: int = 0
    degraded: list[str] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "status": self.status,
            "capability": self.capability,
            "items_count": self.items_count,
            "degraded": self.degraded,
            "error": self.error,
        }


class CollectScheduler:
    """采集任务编排器。"""

    def __init__(
        self,
        session: Session,
        registry: Optional[CapabilityRegistry] = None,
        limiter: Optional[AdaptiveRateLimiter] = None,
        hamming_threshold: int = DEFAULT_HAMMING_THRESHOLD,
    ) -> None:
        self.session = session
        self.registry = registry or build_default_registry()
        self.limiter = limiter or AdaptiveRateLimiter()
        self.hamming_threshold = hamming_threshold

    # ------------------------------------------------------------------ #
    # 计划 → 任务
    # ------------------------------------------------------------------ #

    async def create_job(
        self, plan: CollectPlan, *, max_items: int = DEFAULT_MAX_ITEMS
    ) -> CollectJob:
        """为一个计划创建采集任务与初始分片。"""
        job = CollectJob(
            plan_id=plan.id,
            status="pending",
            total_tasks=1,
            dedup_stats={"inserted": 0, "updated": 0, "skipped": 0},
        )
        self.session.add(job)
        self.session.commit()
        self.session.refresh(job)

        task = CollectTask(
            job_id=job.id,
            shard_spec={
                "kind": "root",
                "target": plan.target_url,
                "max_items": max_items,
            },
            cursor={"page": 1, "known_streak": 0},
            status="pending",
        )
        self.session.add(task)
        self.session.commit()

        logger.info("创建采集任务 job=%s plan=%s", job.id, plan.id)
        return job

    # ------------------------------------------------------------------ #
    # 执行
    # ------------------------------------------------------------------ #

    async def run_job(
        self,
        job_id: int,
        *,
        client: Optional[httpx.AsyncClient] = None,
        max_tasks: Optional[int] = None,
    ) -> CollectJob:
        """执行采集任务。可重复调用以从断点续跑。"""
        job = self.session.get(CollectJob, job_id)
        if job is None:
            raise ValueError(f"采集任务不存在: {job_id}")

        plan = self.session.get(CollectPlan, job.plan_id)
        if plan is None:
            raise ValueError(f"采集计划不存在: {job.plan_id}")

        profile = (
            self.session.get(SiteProfile, plan.profile_id) if plan.profile_id else None
        )
        profile_dict = profile.to_dict() if profile else {}
        if not profile_dict:
            profile_dict = {
                "access": {},
                "structure": {},
                "strategy": plan_strategy(plan),
                "sample_url": plan.target_url,
            }

        verdict_row_id = self._resolve_verdict_id(plan)

        owns_client = client is None
        if client is None:
            client = httpx.AsyncClient(
                timeout=REQUEST_TIMEOUT,
                follow_redirects=True,
                headers={
                    "User-Agent": DEFAULT_USER_AGENT,
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                },
            )

        job.status = "running"
        if job.started_at is None:
            job.started_at = _now()
        self.session.commit()

        try:
            robots = robots_from_profile(profile_dict)
            page_fetcher = PageFetcher(
                client, self.limiter, robots_check=robots.can_fetch
            )
            ctx = ExecContext(
                verdict_id=verdict_row_id,
                rate_limiter=self.limiter,
                fetcher=page_fetcher,
                is_known=lambda url: self._item_exists(url),
            )

            request = self._build_request(plan, profile_dict)

            tasks = (
                self.session.execute(
                    select(CollectTask)
                    .where(
                        CollectTask.job_id == job_id,
                        CollectTask.status.in_(("pending", "running")),
                    )
                    .order_by(CollectTask.id)
                )
                .scalars()
                .all()
            )

            outcomes: list[TaskOutcome] = []
            for task in tasks[: max_tasks or len(tasks)]:
                outcomes.append(
                    await self._execute_task(
                        task, profile_dict, request, ctx, verdict_row_id
                    )
                )

            self._finalize(job, outcomes)
            return job
        finally:
            if owns_client:
                await client.aclose()

    # ------------------------------------------------------------------ #

    async def _execute_task(
        self,
        task: CollectTask,
        profile: dict,
        request: CollectRequest,
        ctx: ExecContext,
        verdict_row_id: Optional[int],
    ) -> TaskOutcome:
        """执行单个分片：按能力链依次尝试，直到成功或链耗尽。"""
        task.status = "running"
        self.session.commit()

        preferred = (profile.get("strategy") or {}).get("chain") or []
        chain = self.registry.select_chain(profile, request, preferred=preferred)

        if not chain:
            task.status = "skipped"
            task.last_error = "无可用采集能力（判定阻断或无适配能力）"
            self.session.commit()
            return TaskOutcome(task_id=task.id, status="skipped", error=task.last_error)

        degraded: list[str] = []

        for capability in chain:
            task.attempts += 1
            try:
                result = await capability.execute(profile, request, ctx)
            except Exception as exc:  # noqa: BLE001 - 能力异常应降级而非中断任务
                logger.exception("能力 %s 执行异常", capability.name)
                degraded.append(f"{capability.name}: 异常 {type(exc).__name__}")
                continue

            if result.status is ResultStatus.OK:
                stats = self._store_items(task, result, verdict_row_id)
                # 记录增量命中数：全部命中即"无新增"，统计上要看得出来
                if result.known_hits:
                    stats["known_hits"] = stats.get("known_hits", 0) + result.known_hits
                task.status = "done"
                task.capability_used = capability.name
                task.last_error = None
                self._merge_dedup_stats(task.job_id, stats)
                self.session.commit()
                return TaskOutcome(
                    task_id=task.id,
                    status="done",
                    capability=capability.name,
                    items_count=len(result.items),
                    degraded=degraded,
                )

            if result.status is ResultStatus.FAILED:
                task.status = "failed"
                task.last_error = f"{capability.name}: {result.error}"
                self.session.commit()
                return TaskOutcome(
                    task_id=task.id,
                    status="failed",
                    capability=capability.name,
                    degraded=degraded,
                    error=result.error,
                )

            # DEGRADE：记录原因，继续尝试下一候选
            degraded.append(f"{capability.name}: {result.error}")

        task.status = "failed"
        task.last_error = "能力链全部降级 | " + " ; ".join(degraded[:5])
        self.session.commit()
        return TaskOutcome(
            task_id=task.id,
            status="failed",
            degraded=degraded,
            error=task.last_error,
        )

    # ------------------------------------------------------------------ #
    # 入库
    # ------------------------------------------------------------------ #

    def _store_items(
        self, task: CollectTask, result, verdict_row_id: Optional[int]
    ) -> dict:
        """三级去重后写入条目。"""
        stats = {"inserted": 0, "updated": 0, "skipped": 0, "content_hits": 0}

        for raw in result.items:
            url = (
                raw.get("source_url")
                or raw.get("link")
                or raw.get("url")
                or ""
            ).strip()
            if not url:
                continue

            item_key = make_item_key(url)
            text = raw.get("text") or raw.get("summary") or ""
            payload = raw.get("payload")
            if payload is None:
                # feed 条目没有 payload，用条目自身作为数据
                payload = {
                    k: v
                    for k, v in raw.items()
                    if not k.startswith("_") and k not in ("text", "source_url")
                }
            completeness = float(raw.get("_completeness", 0.0))

            existing = (
                self.session.execute(
                    select(CollectItem).where(CollectItem.item_key == item_key).limit(1)
                )
                .scalars()
                .first()
            )

            new_hash = simhash64(text) if text else 0

            if existing is None:
                self.session.add(
                    CollectItem(
                        job_id=task.job_id,
                        task_id=task.id,
                        verdict_id=verdict_row_id,
                        item_key=item_key,
                        source_url=url[:1000],
                        content_simhash=to_signed64(new_hash) if new_hash else None,
                        payload=payload,
                        completeness=completeness,
                        item_version=1,
                    )
                )
                stats["inserted"] += 1
                continue

            # 第 2 级：内容指纹判定
            if new_hash and existing.content_simhash:
                distance = hamming_distance(
                    new_hash, to_unsigned64(existing.content_simhash)
                )
                if distance <= self.hamming_threshold:
                    existing.last_seen = _now()
                    stats["content_hits"] += 1
                    stats["skipped"] += 1
                    continue

            # 内容发生变化：更新并递增版本
            existing.payload = payload
            existing.completeness = completeness
            existing.item_version = (existing.item_version or 1) + 1
            existing.last_seen = _now()
            if new_hash:
                existing.content_simhash = to_signed64(new_hash)
            if verdict_row_id and existing.verdict_id is None:
                existing.verdict_id = verdict_row_id
            stats["updated"] += 1

        self.session.flush()
        return stats

    def _merge_dedup_stats(self, job_id: int, stats: dict) -> None:
        job = self.session.get(CollectJob, job_id)
        if job is None:
            return
        merged = dict(job.dedup_stats or {})
        for key, value in stats.items():
            merged[key] = merged.get(key, 0) + value
        job.dedup_stats = merged

    # ------------------------------------------------------------------ #
    # 汇总
    # ------------------------------------------------------------------ #

    def _finalize(self, job: CollectJob, outcomes: list[TaskOutcome]) -> None:
        """汇总任务状态、条目数与质量分。"""
        tasks = (
            self.session.execute(
                select(CollectTask).where(CollectTask.job_id == job.id)
            )
            .scalars()
            .all()
        )
        job.total_tasks = len(tasks)
        job.done_tasks = sum(1 for t in tasks if t.status == "done")
        job.items_count = self.session.execute(
            select(func.count())
            .select_from(CollectItem)
            .where(CollectItem.job_id == job.id)
        ).scalar_one()

        job.quality_score = self._compute_quality(job.id)

        error_dist: dict[str, int] = {}
        for task in tasks:
            if task.status == "failed" and task.last_error:
                key = task.last_error.split(":")[0][:60]
                error_dist[key] = error_dist.get(key, 0) + 1
        job.error_dist = error_dist

        if job.done_tasks == job.total_tasks and job.total_tasks > 0:
            job.status = "succeeded"
        elif job.done_tasks > 0:
            job.status = "partial"
        else:
            job.status = "failed"

        job.finished_at = _now()
        self.session.commit()

    def _compute_quality(self, job_id: int) -> float:
        """质量分 = 平均字段完整度 × 有效数据占比。"""
        items = (
            self.session.execute(
                select(CollectItem).where(CollectItem.job_id == job_id)
            )
            .scalars()
            .all()
        )
        if not items:
            return 0.0
        avg_completeness = sum(i.completeness or 0.0 for i in items) / len(items)
        valid = sum(1 for i in items if i.payload)
        valid_ratio = valid / len(items)
        return round(avg_completeness * valid_ratio, 4)

    # ------------------------------------------------------------------ #
    # 辅助
    # ------------------------------------------------------------------ #

    def _build_request(self, plan: CollectPlan, profile: dict) -> CollectRequest:
        shard = (
            self.session.execute(
                select(CollectTask)
                .where(CollectTask.job_id.in_(
                    select(CollectJob.id).where(CollectJob.plan_id == plan.id)
                ))
                .order_by(CollectTask.id.desc())
                .limit(1)
            )
            .scalars()
            .first()
        )
        max_items = DEFAULT_MAX_ITEMS
        if shard and shard.shard_spec:
            max_items = int(shard.shard_spec.get("max_items") or DEFAULT_MAX_ITEMS)

        incremental = plan.incremental_policy or {}
        return CollectRequest(
            target_url=plan.target_url,
            fields=list(plan.field_mapping or []),
            max_items=max_items,
            consecutive_known_limit=int(
                incremental.get("consecutive_limit") or 10
            ),
        )

    def _resolve_verdict_id(self, plan: CollectPlan) -> Optional[int]:
        if not plan.verdict_uid:
            return None
        row = (
            self.session.execute(
                select(ComplianceVerdict)
                .where(ComplianceVerdict.verdict_uid == plan.verdict_uid)
                .limit(1)
            )
            .scalars()
            .first()
        )
        return row.id if row else None

    def _item_exists(self, url: str) -> bool:
        item_key = make_item_key(url)
        found = self.session.execute(
            select(CollectItem.id).where(CollectItem.item_key == item_key).limit(1)
        ).scalar_one_or_none()
        return found is not None


def plan_strategy(plan: CollectPlan) -> dict:
    """从计划里取策略，缺失时给出保守默认。"""
    return {
        "chain": list(plan.strategy_chain or []),
        "rate": dict(plan.rate_policy or {"base_per_second": 1.0}),
        "incremental": dict(plan.incremental_policy or {}),
    }
