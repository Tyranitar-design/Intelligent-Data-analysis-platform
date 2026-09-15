# -*- coding: utf-8 -*-
"""TLS 指纹伪装 · 集成测试（curl_cffi 增强，多源调研验证项）

1. curl_cffi(impersonate=chrome) 的 JA3 与裸 httpx 不同（TLS 层反检测证据）
2. HttpxStrategy 直采走 curl_cffi 并标注 transport（metadata.tls）
"""
from __future__ import annotations

import asyncio

import httpx


def test_curl_cffi_ja3_differs_from_httpx():
    """JA3 对比：curl_cffi 浏览器指纹 ≠ 裸 httpx 指纹。"""
    bare = httpx.get("https://tls.browserleaks.com/json", timeout=25)
    ja3_bare = (bare.json() or {}).get("ja3_hash")

    from curl_cffi import requests as cffi_requests

    resp = cffi_requests.get(
        "https://tls.browserleaks.com/json", impersonate="chrome", timeout=25
    )
    ja3_cffi = (resp.json() or {}).get("ja3_hash")

    assert ja3_bare, "裸 httpx JA3 获取失败"
    assert ja3_cffi, "curl_cffi JA3 获取失败"
    assert ja3_bare != ja3_cffi, f"JA3 相同（{ja3_bare}）——伪装未生效"


def test_strategy_uses_curl_cffi_transport():
    """策略直采使用 curl_cffi 并在 metadata 标注 transport。"""
    from crawlers.intelligent.strategies.httpx_strategy import HttpxStrategy

    async def body():
        strategy = HttpxStrategy()
        try:
            result = await strategy.execute("https://example.com/")
        finally:
            await strategy.close()
        return result

    result = asyncio.run(body())
    assert result.success is True, result
    assert str(result.metadata.get("tls", "")).startswith("curl_cffi"), result.metadata
