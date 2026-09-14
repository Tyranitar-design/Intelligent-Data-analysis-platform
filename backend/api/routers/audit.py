"""
审计路由
========

- ``GET /api/v1/audit/logs``  审计日志检索（过滤 + 分页）

审计日志**不提供删除**：需要清理时走保留策略（按时间归档），而不是逐条删
——可删的审计等于没有审计。
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.core.database import get_db
from api.models import AuditLog

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/logs", summary="审计日志检索")
def list_audit_logs(
    action: Optional[str] = Query(None, description="按操作名过滤（前缀匹配，如 collect.）"),
    principal: Optional[str] = Query(None, description="按操作者标识过滤"),
    result: Optional[str] = Query(None, description="按结果过滤：ok / denied / error"),
    verdict_id: Optional[int] = Query(None, description="按关联判定行 ID 过滤"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> dict:
    """检索审计留痕（按时间倒序）。

    入参只存摘要哈希（见 ``mcp.audit``）——本接口同样不回传敏感原文。
    """
    stmt = select(AuditLog)
    count_stmt = select(func.count()).select_from(AuditLog)

    if action:
        pattern = f"{action}%"
        stmt = stmt.where(AuditLog.action.like(pattern))
        count_stmt = count_stmt.where(AuditLog.action.like(pattern))
    if principal:
        stmt = stmt.where(AuditLog.principal_id == principal)
        count_stmt = count_stmt.where(AuditLog.principal_id == principal)
    if result:
        stmt = stmt.where(AuditLog.result == result)
        count_stmt = count_stmt.where(AuditLog.result == result)
    if verdict_id is not None:
        stmt = stmt.where(AuditLog.verdict_id == verdict_id)
        count_stmt = count_stmt.where(AuditLog.verdict_id == verdict_id)

    total = db.execute(count_stmt).scalar_one()
    rows = (
        db.execute(stmt.order_by(AuditLog.id.desc()).limit(limit).offset(offset))
        .scalars()
        .all()
    )

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [r.to_dict() for r in rows],
    }
