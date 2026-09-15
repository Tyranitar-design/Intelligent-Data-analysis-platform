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
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from api.core.config import settings
from api.core.database import get_db
from api.models import (
    AuditLog,
    CollectItem,
    CollectJob,
    CollectSchedule,
    ComplianceVerdict,
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


@router.get(
    "/metrics", summary="Prometheus 指标导出", response_class=PlainTextResponse
)
def prometheus_metrics(db: Session = Depends(get_db)) -> str:
    """Prometheus 文本格式指标（零依赖实现）。

    指标命名遵循 ``webinsight_*`` 前缀；所有值为 gauge（当前快照）。
    可直接接入 Prometheus scrape，或用于人工诊断。
    """
    from collect.ratelimit import get_shared_limiter

    lines: list[str] = []

    def add(name: str, help_text: str, rows: list[tuple[str | None, float]]) -> None:
        lines.append(f"# HELP {name} {help_text}")
        lines.append(f"# TYPE {name} gauge")
        for labels, value in rows:
            if labels:
                lines.append(f"{name}{{{labels}}} {value}")
            else:
                lines.append(f"{name} {value}")

    # ---- 采集任务 ----
    job_rows = db.execute(
        select(CollectJob.status, func.count()).group_by(CollectJob.status)
    ).all()
    add(
        "webinsight_jobs",
        "collect jobs by status",
        [(f'status="{status}"', float(count)) for status, count in job_rows]
        or [("", 0.0)],
    )

    # ---- 调度 ----
    schedules_total = db.execute(
        select(func.count()).select_from(CollectSchedule)
    ).scalar_one()
    schedules_enabled = db.execute(
        select(func.count())
        .select_from(CollectSchedule)
        .where(CollectSchedule.enabled.is_(True))
    ).scalar_one()
    add(
        "webinsight_schedules",
        "schedules by state",
        [
            ('state="enabled"', float(schedules_enabled)),
            ('state="total"', float(schedules_total)),
        ],
    )

    # ---- 限速（进程级共享限速器） ----
    rate_stats = get_shared_limiter().stats()
    add(
        "webinsight_rate_current_per_second",
        "current adaptive rate per domain",
        [
            (f'domain="{domain}"', float(snap.get("current_per_second", 0.0)))
            for domain, snap in rate_stats.items()
        ]
        or [("", 0.0)],
    )
    add(
        "webinsight_rate_throttle_events",
        "throttle events per domain",
        [
            (f'domain="{domain}"', float(snap.get("throttle_events", 0)))
            for domain, snap in rate_stats.items()
        ]
        or [("", 0.0)],
    )

    # ---- 存储 ----
    db_size: int | None = None
    table_count: int | None = None
    try:
        if settings.DATABASE_URL.startswith("sqlite"):
            from database.models import resolve_default_db_path

            db_path = Path(resolve_default_db_path())
            if db_path.exists():
                db_size = db_path.stat().st_size
            table_count = db.execute(
                text("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            ).scalar_one()
    except Exception:  # noqa: BLE001 - 指标接口不应因统计失败而 500
        logger.exception("存储指标统计失败")
    add("webinsight_storage_bytes", "main database file size", [("", float(db_size or 0))])
    add("webinsight_storage_tables", "table count", [("", float(table_count or 0))])

    # ---- 资产 ----
    add(
        "webinsight_datasets",
        "materialized datasets",
        [("", float(db.execute(select(func.count()).select_from(Dataset)).scalar_one()))],
    )
    add(
        "webinsight_items",
        "collect items",
        [("", float(db.execute(select(func.count()).select_from(CollectItem)).scalar_one()))],
    )
    add(
        "webinsight_profiles",
        "site profiles",
        [("", float(db.execute(select(func.count()).select_from(SiteProfile)).scalar_one()))],
    )
    add(
        "webinsight_audit_logs",
        "audit log entries",
        [("", float(db.execute(select(func.count()).select_from(AuditLog)).scalar_one()))],
    )

    # ---- 合规判定 ----
    verdict_rows = db.execute(
        select(ComplianceVerdict.decision, func.count()).group_by(
            ComplianceVerdict.decision
        )
    ).all()
    add(
        "webinsight_verdicts",
        "compliance verdicts by decision",
        [(f'decision="{decision}"', float(count)) for decision, count in verdict_rows]
        or [("", 0.0)],
    )

    return "\n".join(lines) + "\n"


@router.get("/retention", summary="数据保留报告")
def retention_report(db: Session = Depends(get_db)) -> dict:
    """各数据资产的存量与时间范围（只读报告，不做删除）。

    用途：决定清理策略前先看清"有什么、多老、增长多快"。
    """
    def summarize(model, ts_column) -> dict:
        count = db.execute(select(func.count()).select_from(model)).scalar_one()
        oldest = db.execute(select(func.min(ts_column))).scalar_one()
        newest = db.execute(select(func.max(ts_column))).scalar_one()
        return {
            "count": count,
            "oldest": oldest.isoformat() if oldest else None,
            "newest": newest.isoformat() if newest else None,
        }

    tables = {
        "collect_items": summarize(CollectItem, CollectItem.first_seen),
        "datasets": summarize(Dataset, Dataset.created_at),
        "audit_logs": summarize(AuditLog, AuditLog.ts),
        "compliance_verdicts": summarize(
            ComplianceVerdict, ComplianceVerdict.created_at
        ),
    }
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tables": tables,
        "total_rows": sum(entry["count"] for entry in tables.values()),
    }
