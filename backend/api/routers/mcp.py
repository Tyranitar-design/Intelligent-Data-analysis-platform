"""
MCP 端点
========

- ``POST /mcp``  JSON-RPC 2.0 入口
- ``GET  /mcp``  服务概览（人工检查服务与工具是否就绪）

协议错误一律以 HTTP 200 + JSON-RPC error 返回——这是 JSON-RPC 的标准做法，
调用方据 ``error.code`` 判断，而不是据 HTTP 状态码。
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, Response
from sqlalchemy.orm import Session

from api.core.database import get_db
from mcp.auth import auth_configured
from mcp.protocol import PARSE_ERROR
from mcp.server import MCPServer

logger = logging.getLogger(__name__)
router = APIRouter()

_server = MCPServer()


@router.post("", summary="MCP JSON-RPC 入口")
async def mcp_endpoint(request: Request, db: Session = Depends(get_db)):
    """MCP 协议入口。body 为单条 JSON-RPC 请求。"""
    try:
        payload = await request.json()
    except Exception:  # noqa: BLE001 - 解析失败要返回标准错误码
        return JSONResponse(
            {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": PARSE_ERROR, "message": "请求体不是合法 JSON"},
            }
        )

    result = await _server.handle(
        payload,
        session=db,
        authorization=request.headers.get("authorization"),
        client_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    # 通知类消息无响应
    if result is None:
        return Response(status_code=202)

    return JSONResponse(result)


@router.get("/", include_in_schema=False)
@router.get("", summary="MCP 服务概览")
async def mcp_info() -> dict:
    """返回协议信息、鉴权状态与工具清单，便于人工确认服务就绪。"""
    return {
        "protocol": "json-rpc-2.0-over-http",
        "auth_configured": auth_configured(),
        "tool_count": len(_server.registry.list_tools()),
        "tools": _server.registry.list_tools(),
        "usage": (
            "POST 本路径，body 形如 "
            '{"jsonrpc":"2.0","id":1,"method":"tools/call",'
            '"params":{"name":"analyze_site","arguments":{"url":"..."}}}'
        ),
    }
