# -*- coding: utf-8 -*-
"""JS 逆向实战实验室 · 集成测试

1. 离线：AST 函数发现 + 依赖链提取 + execjs 复现 == Python 参照实现
2. 端到端：仿真站 → 逆向链自动签名 → 200；错签 403；过期 ts 403（防重放）
"""
from __future__ import annotations

import asyncio
import re
import time

import httpx

from crawlers.jsreverse.jsrev_lab import (
    SIGN_JS,
    expected_sign,
    reversed_signed_fetch,
    start_lab_server,
)


def test_extract_and_reproduce_signature():
    """AST 发现 + 依赖链提取 + execjs 复现 == Python 参照实现。"""
    from crawlers.jsreverse.js_reverse_engine import JSReverseEngine

    engine = JSReverseEngine()
    ast = engine.parse_ast(SIGN_JS)
    funcs = sorted(f["name"] for f in engine.find_functions(ast or {}))
    assert "sign" in funcs and "_0xa1" in funcs and "buildQuery" in funcs

    dep_var = re.search(r"var\s+_0xn\s*=\s*.*?;", SIGN_JS)
    assert dep_var is not None
    combined = (
        dep_var.group(0)
        + "\n"
        + engine.extract_function_code(SIGN_JS, "_0xa1")
        + "\n"
        + engine.extract_function_code(SIGN_JS, "sign")
    )
    value = engine.execute_js(combined, "sign", ["user42", 1700000000])
    assert value == expected_sign("user42", 1700000000)


def test_lab_end_to_end():
    server, base = start_lab_server()
    try:
        result = asyncio.run(reversed_signed_fetch(base, "user7"))
        assert result["status"] == 200, result
        assert result["body"]["ok"] is True
        assert result["sign"] == result["expected"]

        # 对照组：错签 → 403
        bad = httpx.get(
            f"{base}/api/data",
            params={"uid": "user7", "ts": int(time.time()), "sign": "deadbeef"},
            timeout=10,
        )
        assert bad.status_code == 403
        assert bad.json()["error"] == "bad sign"

        # 对照组：过期时间戳 → 403（防重放）
        stale_ts = int(time.time()) - 3600
        expired = httpx.get(
            f"{base}/api/data",
            params={
                "uid": "user7",
                "ts": stale_ts,
                "sign": expected_sign("user7", stale_ts),
            },
            timeout=10,
        )
        assert expired.status_code == 403
        assert expired.json()["error"] == "ts expired"
    finally:
        server.shutdown()
