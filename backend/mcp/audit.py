"""
MCP 审计
========

每次工具调用都写审计。入参**只存摘要哈希**，不存原文——
``authorization_token`` 这类敏感值绝不应该出现在日志或审计表里。
"""
from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Optional

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# 入参中不应落库的敏感键（即使哈希也不该原样保留）
SENSITIVE_KEYS = frozenset(
    {"authorization_token", "token", "password", "api_key", "secret", "cookie"}
)


def digest_payload(arguments: dict[str, Any]) -> str:
    """计算入参摘要。敏感键先脱敏再哈希。"""
    if not isinstance(arguments, dict):
        return ""

    sanitized = {
        key: ("<redacted>" if key.lower() in SENSITIVE_KEYS else value)
        for key, value in arguments.items()
    }
    try:
        blob = json.dumps(sanitized, sort_keys=True, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        blob = str(sorted(sanitized.keys()))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:32]


def record(
    session: Session,
    *,
    principal_id: str,
    action: str,
    result: str = "ok",
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    detail: Optional[dict] = None,
    request_digest: Optional[str] = None,
    client_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
    verdict_row_id: Optional[int] = None,
) -> None:
    """写一条审计记录。

    审计失败不应中断业务——记日志即可，但不能让主流程挂掉。
    """
    try:
        from api.models import AuditLog

        session.add(
            AuditLog(
                principal_id=principal_id[:100] if principal_id else None,
                action=action[:80],
                target_type=target_type[:40] if target_type else None,
                target_id=str(target_id)[:80] if target_id is not None else None,
                verdict_id=verdict_row_id,
                request_digest=request_digest,
                result=result[:20],
                detail=detail or {},
                ip=client_ip[:60] if client_ip else None,
                user_agent=user_agent[:300] if user_agent else None,
            )
        )
        session.commit()
    except Exception as exc:  # noqa: BLE001 - 审计失败不阻断业务
        logger.warning("写审计日志失败: %s", str(exc)[:160])
        try:
            session.rollback()
        except Exception:  # noqa: BLE001
            pass
