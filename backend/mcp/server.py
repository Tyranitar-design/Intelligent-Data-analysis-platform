"""
MCP Server
==========

JSON-RPC over HTTP 的协议处理器。

支持的方法：

| 方法 | 作用 |
|---|---|
| ``initialize``                | 握手，返回协议版本与能力 |
| ``notifications/initialized`` | 客户端就绪通知（无响应） |
| ``ping``                      | 健康检查 |
| ``tools/list``                | 工具清单 |
| ``tools/call``                | 调用工具 |

处理器的职责边界很清楚：协议解析、鉴权、审计、错误归一化。
工具本身做什么，由 :mod:`mcp.tools` 决定。
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from sqlalchemy.orm import Session

from mcp import audit
from mcp.auth import authenticate
from mcp.protocol import (
    AUTH_REQUIRED,
    AUTHORIZATION_REQUIRED,
    COMPLIANCE_BLOCKED,
    INTERNAL_ERROR,
    INVALID_PARAMS,
    INVALID_TOKEN,
    METHOD_NOT_FOUND,
    MCPError,
    error_response,
    parse_request,
    server_info,
    success_response,
    tool_result,
)
from mcp.registry import ToolContext, ToolRegistry, build_default_registry

logger = logging.getLogger(__name__)

# 这些错误码代表"被拒绝"，审计里要区分于普通错误
DENIED_CODES = frozenset(
    {AUTH_REQUIRED, INVALID_TOKEN, COMPLIANCE_BLOCKED, AUTHORIZATION_REQUIRED}
)


class MCPServer:
    """MCP 协议处理器。"""

    def __init__(self, registry: Optional[ToolRegistry] = None) -> None:
        self.registry = registry or build_default_registry()

    async def handle(
        self,
        payload: Any,
        *,
        session: Session,
        authorization: Optional[str] = None,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Optional[dict]:
        """处理一条 JSON-RPC 消息。

        通知类消息返回 ``None``（HTTP 层应回 202）。
        """
        try:
            request = parse_request(payload)
        except MCPError as exc:
            return error_response(None, exc)

        request_id = request.request_id

        if request.is_notification:
            logger.debug("收到通知: %s", request.method)
            return None

        try:
            if request.method == "initialize":
                return success_response(request_id, server_info())

            if request.method == "ping":
                return success_response(request_id, {})

            if request.method == "tools/list":
                return success_response(
                    request_id, {"tools": self.registry.list_tools()}
                )

            if request.method == "tools/call":
                result = await self._call_tool(
                    request, session, authorization, client_ip, user_agent
                )
                return success_response(request_id, result)

            raise MCPError(
                METHOD_NOT_FOUND,
                f"未知方法: {request.method}",
                {"supported": ["initialize", "ping", "tools/list", "tools/call"]},
            )

        except MCPError as exc:
            return error_response(request_id, exc)
        except Exception as exc:  # noqa: BLE001 - 协议层必须兜住所有异常
            logger.exception("MCP 处理异常 method=%s", request.method)
            return error_response(
                request_id,
                MCPError(INTERNAL_ERROR, "服务端内部错误", {"detail": str(exc)[:200]}),
            )

    # ------------------------------------------------------------------ #

    async def _call_tool(
        self,
        request,
        session: Session,
        authorization: Optional[str],
        client_ip: Optional[str],
        user_agent: Optional[str],
    ) -> dict:
        params = request.params or {}
        name = params.get("name")
        arguments = params.get("arguments") or {}

        if not name or not isinstance(name, str):
            raise MCPError(INVALID_PARAMS, "tools/call 缺少 name 参数")

        spec = self.registry.get(name)
        if spec is None:
            raise MCPError(
                METHOD_NOT_FOUND,
                f"未知工具: {name}",
                {"available": self.registry.names()},
            )

        principal_id = "anonymous"
        if spec.requires_auth:
            try:
                principal = authenticate(authorization)
                principal_id = principal.principal_id
            except MCPError as exc:
                # 鉴权失败同样要留痕——安全审计的重点正是失败尝试
                audit.record(
                    session,
                    principal_id="anonymous",
                    action=f"mcp.{name}",
                    result="denied",
                    target_type="tool",
                    target_id=name,
                    detail={"code": exc.code, "message": exc.message, "stage": "auth"},
                    request_digest=audit.digest_payload(arguments),
                    client_ip=client_ip,
                    user_agent=user_agent,
                )
                raise

        context = ToolContext(
            principal_id=principal_id,
            session=session,
            client_ip=client_ip,
            user_agent=user_agent,
            request_digest=audit.digest_payload(arguments),
        )

        try:
            result = await self.registry.call(name, arguments, context)
        except MCPError as exc:
            audit.record(
                session,
                principal_id=principal_id,
                action=f"mcp.{name}",
                result="denied" if exc.code in DENIED_CODES else "error",
                target_type="tool",
                target_id=name,
                detail={"code": exc.code, "message": exc.message},
                request_digest=context.request_digest,
                client_ip=client_ip,
                user_agent=user_agent,
            )
            raise

        audit.record(
            session,
            principal_id=principal_id,
            action=f"mcp.{name}",
            result="ok",
            target_type="tool",
            target_id=name,
            detail=_summarize_result(name, result),
            request_digest=context.request_digest,
            client_ip=client_ip,
            user_agent=user_agent,
        )
        return tool_result(result)


def _summarize_result(tool_name: str, result: dict) -> dict:
    """把工具结果压成审计用得上的少量结构化字段。

    审计不该把整个结果集抄一遍——只留能回答"这次调用改变了什么"的信息。
    """
    if not isinstance(result, dict):
        return {}

    summary: dict[str, Any] = {}
    if "profile" in result and isinstance(result["profile"], dict):
        summary["profile_id"] = result["profile"].get("profile_id")
        summary["domain"] = result["profile"].get("domain")
        summary["confidence"] = result["profile"].get("confidence")
    if "plan" in result and isinstance(result["plan"], dict):
        summary["plan_id"] = result["plan"].get("plan_id")
    if "job" in result and isinstance(result["job"], dict):
        job = result["job"]
        summary["job_id"] = job.get("job_id")
        summary["job_status"] = job.get("status")
        summary["items_count"] = job.get("items_count")
    if "dataset_id" in result:
        summary["dataset_id"] = result.get("dataset_id")
    if "analysis_type" in result:
        summary["analysis_type"] = result.get("analysis_type")
    if "decision" in result:
        summary["decision"] = result.get("decision")
    if "compliance" in result and isinstance(result["compliance"], dict):
        summary["decision"] = result["compliance"].get("decision")
    return summary
