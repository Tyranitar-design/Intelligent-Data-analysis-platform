"""
MCP 工具注册表
==============

工具是有契约的：名称、描述、入参 schema、处理函数。注册表负责分发与校验。

设计约束：

- 工具粒度固定为七个，不增不减。更细会让调用方承担编排责任，
  更粗会让调用方失去控制点和中间反馈。
- 每个工具返回结构化数据（``structuredContent``），同时提供文本形式，
  便于不同能力的调用方取用。
- 工具内部**不重复实现业务逻辑**，只调用 P1~P4 的 service。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional

from mcp.protocol import INVALID_PARAMS, MCPError

logger = logging.getLogger(__name__)

# 工具处理函数签名：(arguments, context) -> dict
ToolHandler = Callable[[dict, "ToolContext"], Awaitable[dict]]


@dataclass
class ToolContext:
    """工具调用的运行时上下文。"""

    principal_id: str = "anonymous"
    session: Any = None
    # 客户端 IP 与 UA，用于审计
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    # 调用链追踪
    request_digest: Optional[str] = None


@dataclass
class ToolSpec:
    """一个工具的完整定义。"""

    name: str
    description: str
    input_schema: dict[str, Any]
    handler: ToolHandler
    # 是否需要鉴权（健康检查类工具可豁免）
    requires_auth: bool = True

    def to_mcp(self) -> dict:
        """转成 MCP ``tools/list`` 的条目格式。"""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }


class ToolRegistry:
    """工具注册表。"""

    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec, *, override: bool = False) -> None:
        if spec.name in self._tools and not override:
            raise ValueError(f"工具已注册: {spec.name}")
        self._tools[spec.name] = spec

    def get(self, name: str) -> Optional[ToolSpec]:
        return self._tools.get(name)

    def names(self) -> list[str]:
        return sorted(self._tools)

    def list_tools(self) -> list[dict]:
        return [self._tools[name].to_mcp() for name in self.names()]

    async def call(
        self, name: str, arguments: dict[str, Any], context: ToolContext
    ) -> dict:
        """调用工具。参数校验失败与业务失败都转成 MCPError。"""
        spec = self._tools.get(name)
        if spec is None:
            raise MCPError(
                INVALID_PARAMS,
                f"未知工具: {name}",
                {"available": self.names()},
            )

        if not isinstance(arguments, dict):
            raise MCPError(INVALID_PARAMS, "arguments 必须是对象")

        self._validate(spec, arguments)

        try:
            return await spec.handler(arguments, context)
        except MCPError:
            raise
        except ValueError as exc:
            # 业务层的参数/状态错误统一转成 INVALID_PARAMS
            raise MCPError(INVALID_PARAMS, str(exc)[:300]) from exc
        except Exception as exc:  # noqa: BLE001 - 工具异常不能穿透协议层
            logger.exception("工具执行失败: %s", name)
            raise MCPError(
                -32603, f"工具执行失败: {type(exc).__name__}", {"detail": str(exc)[:300]}
            ) from exc

    @staticmethod
    def _validate(spec: ToolSpec, arguments: dict[str, Any]) -> None:
        """按 inputSchema 做最小必要校验（required + 类型）。"""
        schema = spec.input_schema or {}
        required = schema.get("required") or []
        missing = [key for key in required if key not in arguments]
        if missing:
            raise MCPError(
                INVALID_PARAMS,
                f"缺少必填参数: {', '.join(missing)}",
                {"required": required},
            )

        properties = schema.get("properties") or {}
        type_map = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "object": dict,
            "array": list,
        }
        for key, value in arguments.items():
            if value is None:
                continue
            declared = properties.get(key, {}).get("type")
            expected = type_map.get(declared)
            if expected is None:
                continue
            # bool 是 int 的子类，单独排除以免 True 被当作 integer 通过
            if isinstance(value, bool) and declared in ("integer", "number"):
                raise MCPError(
                    INVALID_PARAMS, f"参数 {key} 类型应为 {declared}，收到 boolean"
                )
            if not isinstance(value, expected):
                raise MCPError(
                    INVALID_PARAMS,
                    f"参数 {key} 类型应为 {declared}，收到 {type(value).__name__}",
                )


def build_default_registry() -> ToolRegistry:
    """装配七个内置工具。"""
    from mcp.tools import TOOL_SPECS

    registry = ToolRegistry()
    for spec in TOOL_SPECS:
        registry.register(spec)
    return registry
