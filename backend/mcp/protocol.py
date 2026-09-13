"""
MCP 协议基础（JSON-RPC 2.0）
============================

自实现而非引入 SDK 的理由：MCP 的传输核心很薄（initialize / tools/list /
tools/call 三个方法），自实现是零新依赖，同时减少了 Lite 形态（Hermes 服务器）
的部署负担与版本兼容风险。

消息格式：

    请求  {"jsonrpc":"2.0","id":1,"method":"tools/call","params":{...}}
    成功  {"jsonrpc":"2.0","id":1,"result":{...}}
    失败  {"jsonrpc":"2.0","id":1,"error":{"code":-32601,"message":"..."}}

被调用方（客户端）看到的只有 ``result`` 或 ``error``——异常不外泄为栈信息，
业务失败一律转成结构化错误，便于调用方判断与重试。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Union

# ---- JSON-RPC 标准错误码 ------------------------------------------------ #
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603

# ---- 本服务的业务错误码（落在 -32000 ~ -32099 区间） ------------------- #
AUTH_REQUIRED = -32001
INVALID_TOKEN = -32002
COMPLIANCE_BLOCKED = -32003
AUTHORIZATION_REQUIRED = -32004
RESOURCE_NOT_FOUND = -32005
RATE_LIMITED = -32006

PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "webinsight-agent"
SERVER_VERSION = "3.0.0"

JsonRpcId = Optional[Union[str, int]]


@dataclass
class MCPError(Exception):
    """可被转成 JSON-RPC error 的业务异常。"""

    code: int
    message: str
    data: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        super().__init__(self.message)

    def to_dict(self) -> dict:
        payload: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.data:
            payload["data"] = self.data
        return payload


@dataclass
class JsonRpcRequest:
    """解析后的 JSON-RPC 请求。"""

    method: str
    params: dict[str, Any] = field(default_factory=dict)
    request_id: JsonRpcId = None
    is_notification: bool = False


def parse_request(payload: Any) -> JsonRpcRequest:
    """把原始 JSON 解析成请求对象。格式非法时抛 :class:`MCPError`。"""
    if not isinstance(payload, dict):
        raise MCPError(INVALID_REQUEST, "请求体必须是 JSON 对象")

    method = payload.get("method")
    if not isinstance(method, str) or not method:
        raise MCPError(INVALID_REQUEST, "缺少 method 字段")

    params = payload.get("params") or {}
    if not isinstance(params, dict):
        raise MCPError(INVALID_PARAMS, "params 必须是对象")

    has_id = "id" in payload and payload["id"] is not None
    return JsonRpcRequest(
        method=method,
        params=params,
        request_id=payload.get("id"),
        is_notification=not has_id,
    )


def success_response(request_id: JsonRpcId, result: Any) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def error_response(request_id: JsonRpcId, error: MCPError) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "error": error.to_dict()}


def tool_result(payload: dict, *, is_error: bool = False) -> dict:
    """构造 ``tools/call`` 的返回值（MCP content 结构）。"""
    import json

    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(payload, ensure_ascii=False, indent=2, default=str),
            }
        ],
        "structuredContent": payload,
        "isError": is_error,
    }


def server_info() -> dict:
    return {
        "protocolVersion": PROTOCOL_VERSION,
        "capabilities": {"tools": {"listChanged": False}},
        "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
    }
