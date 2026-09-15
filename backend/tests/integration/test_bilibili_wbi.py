# -*- coding: utf-8 -*-
"""B站 wbi 签名 · 集成测试

1. 离线：算法结构断言（表重排 → 32 位 hex；sign 输出含 wts/w_rid，md5 格式）
2. 实弹：**服务端认可 = 最终验证**——签名后的搜索请求返回 code=0 + 结果
"""
from __future__ import annotations

import asyncio
import re

from crawlers.jsreverse.bilibili_wbi import BilibiliWbi


def test_mixin_key_structure():
    signer = BilibiliWbi()
    key = signer.get_mixin_key(
        "7cd084941338484aae1ad9425b84077c4932caff0ff746eab6f01bf08b70ac45"
    )
    assert len(key) == 32
    assert re.fullmatch(r"[0-9a-f]{32}", key), key


def test_sign_adds_wts_and_wrid():
    signer = BilibiliWbi()
    signer._mixin_key = "0" * 32  # 直接注入（离线）
    signed = signer.sign({"search_type": "video", "keyword": "python"})
    assert "wts" in signed and "w_rid" in signed
    assert re.fullmatch(r"[0-9a-f]{32}", signed["w_rid"])


def test_wbi_search_end_to_end():
    """实弹：wbi 签名 → B站搜索接口（服务端认可即通过）。"""

    async def body():
        import httpx

        signer = BilibiliWbi()
        ok = await signer.prepare()
        assert ok, "wbi keys 获取失败"
        params = signer.sign(
            {"search_type": "video", "keyword": "python", "page": "1"}
        )
        async with httpx.AsyncClient(timeout=25) as client:
            resp = await client.get(
                "https://api.bilibili.com/x/web-interface/search/type",
                params=params,
                headers=signer.request_headers(),
            )
        try:
            payload = resp.json()
        except Exception:  # noqa: BLE001
            payload = {"code": None, "raw": resp.text[:120]}
        return resp.status_code, payload

    status, payload = asyncio.run(body())
    assert status == 200, status
    assert payload.get("code") == 0, f"服务端拒绝: {payload}"
    results = (payload.get("data") or {}).get("result") or []
    assert len(results) > 0, "搜索无结果"
