"""
MCP 工具面
==========

把平台能力以 MCP 工具形式暴露给外部调用方（Hermes 等 24 小时在线的代理）。

模块划分：

- ``protocol``  JSON-RPC 2.0 消息类型与错误码
- ``registry``  工具注册表与选链校验
- ``auth``      Bearer 鉴权（fail-closed）
- ``audit``     审计写入（入参只存摘要哈希）
- ``tools``     七个工具的实现
- ``server``    协议处理器

关于自实现：MCP SDK 未引入，协议核心（initialize / tools/list / tools/call）
很薄，自实现是零新依赖，也减少了 Lite 形态（Hermes 服务器）的部署负担。

注意：本包名 ``mcp`` 与官方 SDK 同名。当前环境未安装官方 SDK，
若将来需要引入，需先给本包改名或做命名空间隔离。
"""

from mcp.protocol import MCPError, server_info, tool_result
from mcp.registry import ToolContext, ToolRegistry, build_default_registry
from mcp.server import MCPServer

__all__ = [
    "MCPError",
    "MCPServer",
    "ToolContext",
    "ToolRegistry",
    "build_default_registry",
    "server_info",
    "tool_result",
]
