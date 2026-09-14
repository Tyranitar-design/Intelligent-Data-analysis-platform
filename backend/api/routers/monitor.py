"""
运行监视路由
============

- ``GET /api/v1/monitor/stats``  服务 / 队列 / 限速 / 存储 聚合快照

聚合口径：
- 队列：采集任务状态分布 + 调度规则启停；
- 限速：进程级共享限速器的各域名实时节奏（见 ``collect.ratelimit``）；
- 存储：主库文件大小与核心资产计数。
"""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from api.core.config import settings
from api.core.database import get_db
from api.models import (
    CollectItem,
    CollectJob,
    CollectSchedule,
    Dataset,
    SiteProfile,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/stats", summary="运行监视快照")
def monitor_stats(db: Session = Depends(get_db)) -> dict:
    """服务 / 队列 / 限速 / 存储 的聚合快照。"""
    from collect.ratelimit import get_shared_limiter

    # ---- 服务 ----
    service = {
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "database": (
            "sqlite"
            if settings.DATABASE_URL.startswith("sqlite")
            else "postgresql"
        ),
    }

    # ---- 队列 ----
    job_counts = {
        status: count
        for status, count in db.execute(
            select(CollectJob.status, func.count()).group_by(CollectJob.status)
        ).all()
    }
    schedules_total = db.execute(
        select(func.count()).select_from(CollectSchedule)
    ).scalar_one()
    schedules_enabled = db.execute(
        select(func.count())
        .select_from(CollectSchedule)
        .where(CollectSchedule.enabled.is_(True))
    ).scalar_one()
    queue = {
        "pending_jobs": job_counts.get("pending", 0),
        "running_jobs": job_counts.get("running", 0),
        "total_jobs": sum(job_counts.values()),
        "job_status": job_counts,
        "schedules_total": schedules_total,
        "schedules_enabled": schedules_enabled,
    }

    # ---- 限速 ----
    limiter = get_shared_limiter()
    rate_stats = limiter.stats()
    rate = {
        "tracked_domains": len(rate_stats),
        "throttled_domains": [
            domain for domain, snap in rate_stats.items() if snap.get("throttled")
        ],
        "domains": rate_stats,
    }

    # ---- 存储 ----
    storage = {
        "datasets": db.execute(select(func.count()).select_from(Dataset)).scalar_one(),
        "items": db.execute(select(func.count()).select_from(CollectItem)).scalar_one(),
        "profiles": db.execute(
            select(func.count()).select_from(SiteProfile)
        ).scalar_one(),
        "tables": None,
        "db_file": None,
        "db_bytes": None,
    }
    try:
        if settings.DATABASE_URL.startswith("sqlite"):
            storage["tables"] = db.execute(
                text("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            ).scalar_one()
            from database.models import resolve_default_db_path

            db_path = Path(resolve_default_db_path())
            if db_path.exists():
                storage["db_file"] = db_path.name
                storage["db_bytes"] = db_path.stat().st_size
    except Exception:  # noqa: BLE001 - 观测接口不应因统计失败而 500
        logger.exception("存储统计失败")

    return {
        "service": service,
        "queue": queue,
        "rate": rate,
        "storage": storage,
    }
