# -*- coding: utf-8 -*-
"""B站适配器 · 集成测试（实弹：公开接口 + wbi 签名搜索）

1. 适配器注册检查
2. 热门视频实弹（公开接口）
3. 搜索实弹（wbi 签名——服务端认可）
"""
from __future__ import annotations

import asyncio

from crawlers.adapters.bilibili import BilibiliAdapter


def test_adapter_registered():
    from crawlers.adapter_framework import AdapterRegistry

    names = list(AdapterRegistry._adapters.keys()) if hasattr(AdapterRegistry, "_adapters") else []
    assert "bilibili" in names, names


def test_popular_fetch():
    async def body():
        adapter = BilibiliAdapter()
        return await adapter.fetch(type="popular", page_size=5)

    result = asyncio.run(body())
    assert result.success is True, result.error
    assert result.count >= 3, result.count
    first = result.data[0]
    assert first["bvid"] and first["title"] and first["url"]
    assert first["url"].startswith("https://www.bilibili.com/video/")
    assert first["source"] == "bilibili"


def test_search_fetch_with_wbi():
    async def body():
        adapter = BilibiliAdapter()
        return await adapter.fetch(type="search", keyword="python", page=1)

    result = asyncio.run(body())
    assert result.success is True, result.error
    assert result.count > 0, "搜索无结果"
    first = result.data[0]
    assert first["title"], first
    # 搜索标题应已清洗 HTML 高亮标签
    assert "<em" not in first["title"]
