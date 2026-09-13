"""
MCP 工具面 · 协议与鉴权测试
===========================

覆盖：协议方法、鉴权（fail-closed）、参数校验、工具分发与错误码。
不访问真实网络——需要外部数据的工具用"不存在的资源"触发业务错误来验证链路。
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.main import app
from mcp.auth import reset_cache
from mcp.protocol import (
    AUTH_REQUIRED,
    INVALID_PARAMS,
    INVALID_TOKEN,
    METHOD_NOT_FOUND,
    RESOURCE_NOT_FOUND,
)

VALID_TOKEN = "test-token-abcdef"
PRINCIPAL = "hermes"


@pytest.fixture()
def client():
    reset_cache()
    yield TestClient(app)
    reset_cache()


def _rpc(client, method, params=None, request_id=1, headers=None):
    return client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {},
        },
        headers=headers or {},
    )


def _auth_header(token=VALID_TOKEN):
    return {"Authorization": f"Bearer {token}"}


# --------------------------------------------------------------------------- #
# 协议方法
# --------------------------------------------------------------------------- #


def test_get_returns_service_overview(client):
    response = client.get("/mcp")
    assert response.status_code == 200

    info = response.json()
    assert info["protocol"] == "json-rpc-2.0-over-http"
    names = [t["name"] for t in info["tools"]]
    assert len(names) == 7
    assert set(names) == {
        "analyze_site",
        "plan_collection",
        "run_collection",
        "job_status",
        "query_dataset",
        "run_analysis",
        "make_report",
    }


def test_initialize_handshake(client):
    response = _rpc(client, "initialize")
    result = response.json()["result"]

    assert result["protocolVersion"]
    assert result["serverInfo"]["name"] == "webinsight-agent"
    assert "tools" in result["capabilities"]


def test_ping(client):
    response = _rpc(client, "ping")
    assert response.json()["result"] == {}


def test_tools_list_schema_shape(client):
    response = _rpc(client, "tools/list")
    tools = response.json()["result"]["tools"]

    assert len(tools) == 7
    for tool in tools:
        assert tool["name"]
        assert tool["description"]
        assert tool["inputSchema"]["type"] == "object"
        assert "properties" in tool["inputSchema"]

    # 每个工具的必填参数必须出现在 properties 里
    for tool in tools:
        required = tool["inputSchema"].get("required") or []
        for key in required:
            assert key in tool["inputSchema"]["properties"], (
                f"{tool['name']} 的必填参数 {key} 未在 properties 中声明"
            )


def test_unknown_method_returns_method_not_found(client):
    response = _rpc(client, "does/not/exist")
    error = response.json()["error"]
    assert error["code"] == METHOD_NOT_FOUND


def test_invalid_payload_returns_parse_error(client):
    response = client.post("/mcp", content="not json at all")
    assert response.json()["error"]["code"] == -32700


def test_notification_returns_202(client):
    response = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
    )
    assert response.status_code == 202


# --------------------------------------------------------------------------- #
# 鉴权
# --------------------------------------------------------------------------- #


def test_call_rejected_when_no_token_configured(client, monkeypatch):
    """fail-closed：未配置 token 时拒绝，而不是放行。"""
    monkeypatch.delenv("MCP_API_KEY", raising=False)
    reset_cache()

    response = _rpc(
        client,
        "tools/call",
        {"name": "query_dataset", "arguments": {"dataset_id": 1}},
    )
    error = response.json()["error"]
    assert error["code"] == AUTH_REQUIRED


def test_call_rejected_without_authorization_header(client, monkeypatch):
    monkeypatch.setenv("MCP_API_KEY", f"{VALID_TOKEN}:{PRINCIPAL}")
    reset_cache()

    response = _rpc(
        client,
        "tools/call",
        {"name": "query_dataset", "arguments": {"dataset_id": 1}},
    )
    assert response.json()["error"]["code"] == AUTH_REQUIRED


def test_call_rejected_with_invalid_token(client, monkeypatch):
    monkeypatch.setenv("MCP_API_KEY", f"{VALID_TOKEN}:{PRINCIPAL}")
    reset_cache()

    response = _rpc(
        client,
        "tools/call",
        {"name": "query_dataset", "arguments": {"dataset_id": 1}},
        headers=_auth_header("wrong-token"),
    )
    assert response.json()["error"]["code"] == INVALID_TOKEN


def test_call_succeeds_with_valid_token(client, monkeypatch):
    """鉴权通过后，业务错误应正确返回（这里用不存在的数据集）。"""
    monkeypatch.setenv("MCP_API_KEY", f"{VALID_TOKEN}:{PRINCIPAL}")
    reset_cache()

    response = _rpc(
        client,
        "tools/call",
        {"name": "query_dataset", "arguments": {"dataset_id": 999999}},
        headers=_auth_header(),
    )
    body = response.json()

    # 不是鉴权错误，而是业务层的"资源不存在"
    assert "error" in body
    assert body["error"]["code"] == RESOURCE_NOT_FOUND


def test_multiple_tokens_map_to_different_principals(client, monkeypatch):
    monkeypatch.setenv("MCP_API_KEY", f"tok_a:hermes,tok_b:local")
    reset_cache()

    for token in ("tok_a", "tok_b"):
        response = _rpc(
            client,
            "tools/call",
            {"name": "query_dataset", "arguments": {"dataset_id": 999999}},
            headers=_auth_header(token),
        )
        # 两个 token 都能通过鉴权（业务错误相同）
        assert response.json()["error"]["code"] == RESOURCE_NOT_FOUND


# --------------------------------------------------------------------------- #
# 参数校验
# --------------------------------------------------------------------------- #


def test_unknown_tool_rejected(client, monkeypatch):
    monkeypatch.setenv("MCP_API_KEY", f"{VALID_TOKEN}:{PRINCIPAL}")
    reset_cache()

    response = _rpc(
        client,
        "tools/call",
        {"name": "no_such_tool", "arguments": {}},
        headers=_auth_header(),
    )
    assert response.json()["error"]["code"] == METHOD_NOT_FOUND


def test_missing_required_argument(client, monkeypatch):
    monkeypatch.setenv("MCP_API_KEY", f"{VALID_TOKEN}:{PRINCIPAL}")
    reset_cache()

    response = _rpc(
        client,
        "tools/call",
        {"name": "query_dataset", "arguments": {}},  # 缺 dataset_id
        headers=_auth_header(),
    )
    error = response.json()["error"]
    assert error["code"] == INVALID_PARAMS
    assert "dataset_id" in error["message"]


def test_wrong_argument_type(client, monkeypatch):
    monkeypatch.setenv("MCP_API_KEY", f"{VALID_TOKEN}:{PRINCIPAL}")
    reset_cache()

    response = _rpc(
        client,
        "tools/call",
        {"name": "query_dataset", "arguments": {"dataset_id": "not-a-number"}},
        headers=_auth_header(),
    )
    error = response.json()["error"]
    assert error["code"] == INVALID_PARAMS
    assert "dataset_id" in error["message"]


def test_boolean_not_accepted_as_integer(client, monkeypatch):
    """bool 是 int 的子类，必须显式排除，否则 True 会被当成 dataset_id=1。"""
    monkeypatch.setenv("MCP_API_KEY", f"{VALID_TOKEN}:{PRINCIPAL}")
    reset_cache()

    response = _rpc(
        client,
        "tools/call",
        {"name": "query_dataset", "arguments": {"dataset_id": True}},
        headers=_auth_header(),
    )
    assert response.json()["error"]["code"] == INVALID_PARAMS


# --------------------------------------------------------------------------- #
# 审计
# --------------------------------------------------------------------------- #


def test_calls_are_audited(client, monkeypatch):
    """工具调用与拒绝都应留痕。"""
    from sqlalchemy import delete, func, select

    from api.core.database import SessionLocal
    from api.models import AuditLog

    monkeypatch.setenv("MCP_API_KEY", f"{VALID_TOKEN}:{PRINCIPAL}")
    reset_cache()

    session = SessionLocal()
    session.execute(delete(AuditLog).where(AuditLog.action.like("mcp.%")))
    session.commit()
    session.close()

    # 一次成功（业务错误但已通过鉴权） + 一次鉴权拒绝
    _rpc(
        client,
        "tools/call",
        {"name": "query_dataset", "arguments": {"dataset_id": 999999}},
        headers=_auth_header(),
    )
    _rpc(
        client,
        "tools/call",
        {"name": "query_dataset", "arguments": {"dataset_id": 999999}},
        headers=_auth_header("bad-token"),
    )

    session = SessionLocal()
    try:
        rows = (
            session.execute(
                select(AuditLog).where(AuditLog.action.like("mcp.%"))
            )
            .scalars()
            .all()
        )
        assert rows, "未写入审计记录"

        results = {r.result for r in rows}
        assert "denied" in results, f"鉴权拒绝未标记为 denied: {results}"
        # 成功通过鉴权的那次记的是业务错误
        assert any(r.request_digest for r in rows), "缺少入参摘要"

        # 敏感入参不应出现在审计详情里
        for row in rows:
            blob = str(row.detail or "")
            assert VALID_TOKEN not in blob
    finally:
        session.execute(delete(AuditLog).where(AuditLog.action.like("mcp.%")))
        session.commit()
        session.close()
