"""
MCP 接入管理（管理面）
======================

- ``GET  /api/v1/mcp/stats``     调用统计（从审计日志聚合，近 N 天）
- ``POST /api/v1/mcp/selftest``  协议自检（走真实协议层发一次 initialize）

安全约束：本面**不返回也不写入 token 原文**——只报告"鉴权是否已配置"。
token 的生成与轮换仍在环境变量 / .env 中完成。
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.core.database import get_db
from api.models import AuditLog
from mcp.auth import auth_configured
from mcp.server import MCPServer

logger = logging.getLogger(__name__)
router = APIRouter()

_server = MCPServer()


@router.get("/stats", summary="MCP 调用统计")
def mcp_stats(
    days: int = Query(7, ge=1, le=90, description="统计窗口（天）"),
    db: Session = Depends(get_db),
) -> dict:
    """近 N 天的 MCP 调用统计（数据来自审计日志，action 前缀 ``mcp.``）。"""
    rows = (
        db.execute(
            select(AuditLog)
            .where(AuditLog.action.like("mcp.%"))
            .order_by(AuditLog.id.desc())
            .limit(5000)
        )
        .scalars()
        .all()
    )
    # 时间窗口在 Python 侧过滤：SQLite 无时区概念，字符串比较不可靠
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    def _within(row: AuditLog) -> bool:
        if row.ts is None:
            return False
        ts = row.ts if row.ts.tzinfo else row.ts.replace(tzinfo=timezone.utc)
        return ts >= cutoff

    window = [row for row in rows if _within(row)]

    by_result: dict[str, int] = {"ok": 0, "denied": 0, "error": 0}
    by_tool: dict[str, int] = {}
    for row in window:
        by_result[row.result] = by_result.get(row.result, 0) + 1
        tool = row.action[len("mcp."):]
        by_tool[tool] = by_tool.get(tool, 0) + 1

    return {
        "days": days,
        "total": len(window),
        "by_result": by_result,
        "by_tool": dict(sorted(by_tool.items(), key=lambda kv: (-kv[1], kv[0]))),
        "recent": [row.to_dict() for row in window[:10]],
        "auth_configured": auth_configured(),
        "tool_count": len(_server.registry.list_tools()),
        "protocol": "json-rpc-2.0-over-http",
    }


@router.post("/selftest", summary="MCP 协议自检")
async def mcp_selftest() -> dict:
    """走真实协议层发一次 ``initialize``，返回协议版本与耗时。

    不携带凭据也不伪造凭据——``initialize`` 本身是无需鉴权的握手方法，
    鉴权只发生在 ``tools/call``（fail-closed）。
    """
    started = time.perf_counter()
    result = await _server.handle(
        {
            "jsonrpc": "2.0",
            "id": "selftest",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "webinsight-selftest", "version": "1.0"},
            },
        },
        session=None,  # initialize 不需要数据库会话
    )
    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)

    ok = bool(result and "result" in result)
    return {
        "ok": ok,
        "elapsed_ms": elapsed_ms,
        "protocol": "json-rpc-2.0-over-http",
        "server": (result or {}).get("result"),
        "auth_configured": auth_configured(),
    }
