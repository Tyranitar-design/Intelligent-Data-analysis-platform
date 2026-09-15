# -*- coding: utf-8 -*-
"""CapSolver 客户端 · 单元测试（mock HTTP）

覆盖四条路径：
- 同步返回（ImageToText 轻任务直接 ready——不轮询）
- 轮询路径（processing → ready）
- 创建失败（errorId）
- 无 key 优雅降级
- token 型任务（Turnstile 的 solution.token 键）
"""
from __future__ import annotations

import asyncio

import httpx

from crawlers.anticrawl.capsolver_client import CapSolverClient


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def test_sync_ready_returns_without_polling(monkeypatch):
    calls = []

    async def fake_post(self, url, json=None, **kwargs):
        calls.append(url)
        if url.endswith("createTask"):
            return FakeResponse(
                {
                    "errorId": 0,
                    "status": "ready",
                    "solution": {"text": "k8m3", "confidence": 0.99},
                }
            )
        return FakeResponse({"errorId": 1, "errorDescription": "should not poll"})

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    client = CapSolverClient(api_key="TEST-KEY")
    result = asyncio.run(client.solve_image(b"\x89PNG-fake"))
    assert result["success"] is True
    assert result["text"] == "k8m3"
    assert len(calls) == 1  # 同步返回——只有 createTask


def test_poll_until_ready(monkeypatch):
    state = {"polls": 0}

    async def fake_post(self, url, json=None, **kwargs):
        if url.endswith("createTask"):
            return FakeResponse({"errorId": 0, "taskId": "t-1"})
        state["polls"] += 1
        if state["polls"] < 2:
            return FakeResponse({"errorId": 0, "status": "processing"})
        return FakeResponse(
            {
                "errorId": 0,
                "status": "ready",
                "solution": {"gRecaptchaResponse": "TOKEN-ABC"},
            }
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    client = CapSolverClient(api_key="TEST-KEY", poll_interval=0.01)
    result = asyncio.run(client.solve_recaptcha_v2("sitekey-x", "https://x.test/"))
    assert result["success"] is True
    assert result["token"] == "TOKEN-ABC"
    assert state["polls"] == 2


def test_create_error(monkeypatch):
    async def fake_post(self, url, json=None, **kwargs):
        return FakeResponse({"errorId": 1, "errorDescription": "ERROR_KEY_DENIED"})

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    client = CapSolverClient(api_key="TEST-KEY")
    result = asyncio.run(client.solve_image(b"x"))
    assert result["success"] is False
    assert "ERROR_KEY_DENIED" in (result["error"] or "")


def test_no_key_graceful():
    client = CapSolverClient(api_key="")
    assert client.available is False
    result = asyncio.run(client.solve_image(b"x"))
    assert result["success"] is False
    assert "CAPSOLVER_API_KEY" in (result["error"] or "")


def test_turnstile_token_solution_key(monkeypatch):
    async def fake_post(self, url, json=None, **kwargs):
        if url.endswith("createTask"):
            return FakeResponse({"errorId": 0, "taskId": "t-2"})
        return FakeResponse(
            {"errorId": 0, "status": "ready", "solution": {"token": "TS-TOKEN"}}
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    client = CapSolverClient(api_key="TEST-KEY", poll_interval=0.01)
    result = asyncio.run(client.solve_turnstile("sk-x", "https://x.test/"))
    assert result["success"] is True
    assert result["token"] == "TS-TOKEN"
