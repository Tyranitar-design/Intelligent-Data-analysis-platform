"""
MCP 鉴权
========

Bearer token 鉴权，每个 token 绑定一个 ``principal_id``（用于审计与数据隔离）。

配置方式（环境变量 ``MCP_API_KEY``）:

    # 单客户端
    MCP_API_KEY=mytoken123

    # 多客户端：token:principal 逗号分隔
    MCP_API_KEY=tok_a:hermes,tok_b:localagent

**fail-closed**：未配置任何 token 时拒绝所有需要鉴权的调用，而不是静默放行。
配置缺失属于部署错误，不应该表现为"谁都能调"。
"""
from __future__ import annotations

import logging
import os
import secrets
from dataclasses import dataclass

from mcp.protocol import AUTH_REQUIRED, INVALID_TOKEN, MCPError

logger = logging.getLogger(__name__)

DEFAULT_PRINCIPAL = "mcp-client"

# 启动时缓存，避免每次调用都读环境变量
_token_cache: dict[str, str] | None = None


@dataclass
class Principal:
    """已认证的调用方。"""

    principal_id: str
    token_hint: str  # 仅保留前 4 位用于日志，不记录完整 token


def _load_tokens() -> dict[str, str]:
    """加载 token → principal 映射。"""
    global _token_cache
    if _token_cache is not None:
        return _token_cache

    raw = (os.getenv("MCP_API_KEY") or "").strip()
    mapping: dict[str, str] = {}

    if raw:
        for entry in raw.split(","):
            entry = entry.strip()
            if not entry:
                continue
            if ":" in entry:
                token, _, principal = entry.partition(":")
                token, principal = token.strip(), principal.strip()
            else:
                token, principal = entry, DEFAULT_PRINCIPAL
            if token:
                mapping[token] = principal or DEFAULT_PRINCIPAL

    _token_cache = mapping
    if not mapping:
        logger.warning(
            "MCP_API_KEY 未配置：所有需鉴权的工具调用都会被拒绝（fail-closed）"
        )
    return mapping


def reset_cache() -> None:
    """清空缓存（配置变更或测试用）。"""
    global _token_cache
    _token_cache = None


def authenticate(authorization: str | None) -> Principal:
    """校验 Authorization 头，返回调用方身份。"""
    tokens = _load_tokens()

    if not tokens:
        raise MCPError(
            AUTH_REQUIRED,
            "服务端未配置 MCP_API_KEY，拒绝调用",
            {"hint": "在 .env 中设置 MCP_API_KEY"},
        )

    if not authorization:
        raise MCPError(
            AUTH_REQUIRED, "缺少 Authorization 头", {"scheme": "Bearer"}
        )

    scheme, _, value = authorization.partition(" ")
    token = value.strip() if scheme.lower() == "bearer" else authorization.strip()

    if not token:
        raise MCPError(AUTH_REQUIRED, "Authorization 头为空")

    # 常量时间比较，避免时序侧信道
    matched: str | None = None
    for candidate, principal in tokens.items():
        if secrets.compare_digest(candidate, token):
            matched = principal
            break

    if matched is None:
        raise MCPError(INVALID_TOKEN, "令牌无效")

    return Principal(principal_id=matched, token_hint=token[:4])


def auth_configured() -> bool:
    return bool(_load_tokens())
