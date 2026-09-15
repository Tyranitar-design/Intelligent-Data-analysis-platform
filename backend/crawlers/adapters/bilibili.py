# -*- coding: utf-8 -*-
"""B站适配器（公开接口 + wbi 签名）

功能:
- 热门视频（公开接口，无需签名）
- 视频详情（公开接口）
- 搜索（wbi 签名）

合规说明：使用 B站公开 API（学习 / 研究用途）；网页路径采集另受 robots.txt 约束
（见平台 discover/compliance 合规链）。
"""
import logging
import re
import time
from typing import Any, Dict

import httpx

from crawlers.adapter_framework import BaseAdapter, AdapterConfig, register_adapter
from crawlers.base import CrawlResult
from crawlers.jsreverse.bilibili_wbi import BilibiliWbi

logger = logging.getLogger(__name__)

TAG_RE = re.compile(r"<[^>]+>")


class BilibiliConfig(AdapterConfig):
    name: str = "bilibili"
    base_url: str = "https://api.bilibili.com"


@register_adapter("bilibili", category="video")
class BilibiliAdapter(BaseAdapter):
    """B站数据适配器（热门 / 详情 / 搜索）。"""

    NAME = "bilibili"
    DESCRIPTION = "B站 - 热门视频/视频详情/搜索（wbi 签名）"
    CATEGORY = "video"
    CONFIG_CLASS = BilibiliConfig

    def __init__(self, config: BilibiliConfig = None, **kwargs):
        super().__init__(config, **kwargs)
        self._wbi = BilibiliWbi()

    async def fetch(self, **kwargs) -> CrawlResult:
        fetch_type = kwargs.get("type", "popular")
        if fetch_type == "popular":
            return await self.fetch_popular(
                page=kwargs.get("page", 1), page_size=kwargs.get("page_size", 20)
            )
        if fetch_type == "video":
            return await self.fetch_video(bvid=kwargs.get("bvid", ""))
        if fetch_type == "search":
            return await self.fetch_search(
                keyword=kwargs.get("keyword", ""), page=kwargs.get("page", 1)
            )
        return CrawlResult(
            success=False,
            data=[],
            message=f"不支持的采集类型: {fetch_type}",
            source=self.NAME,
            error=f"unsupported type: {fetch_type}",
        )

    # ------------------------------------------------------------------ #
    # 热门（公开）
    # ------------------------------------------------------------------ #
    async def fetch_popular(self, page: int = 1, page_size: int = 20) -> CrawlResult:
        started = time.time()
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                resp = await client.get(
                    "https://api.bilibili.com/x/web-interface/popular",
                    params={"pn": page, "ps": page_size},
                    headers=self._wbi.request_headers(),
                )
                payload = resp.json()
            items = (payload.get("data") or {}).get("list") or []
            data = [self._normalize_video(item) for item in items]
            return CrawlResult(
                success=True,
                data=data,
                message="热门视频采集成功",
                source=self.NAME,
                count=len(data),
                elapsed=time.time() - started,
            )
        except Exception as exc:  # noqa: BLE001
            return self._error(f"热门视频采集失败: {exc}", started)

    # ------------------------------------------------------------------ #
    # 视频详情（公开）
    # ------------------------------------------------------------------ #
    async def fetch_video(self, bvid: str) -> CrawlResult:
        started = time.time()
        if not bvid:
            return self._error("缺少 bvid", started)
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                resp = await client.get(
                    "https://api.bilibili.com/x/web-interface/view",
                    params={"bvid": bvid},
                    headers=self._wbi.request_headers(),
                )
                payload = resp.json()
            if payload.get("code") != 0:
                return self._error(f"接口返回错误: {payload.get('message')}", started)
            data = [self._normalize_video(payload.get("data") or {})]
            return CrawlResult(
                success=True,
                data=data,
                message="视频详情采集成功",
                source=self.NAME,
                count=1,
                elapsed=time.time() - started,
            )
        except Exception as exc:  # noqa: BLE001
            return self._error(f"视频详情采集失败: {exc}", started)

    # ------------------------------------------------------------------ #
    # 搜索（wbi 签名）
    # ------------------------------------------------------------------ #
    async def fetch_search(self, keyword: str, page: int = 1) -> CrawlResult:
        started = time.time()
        if not keyword:
            return self._error("缺少 keyword", started)
        try:
            ready = await self._wbi.prepare()
            if not ready:
                return self._error("wbi keys 获取失败", started)
            params = self._wbi.sign(
                {"search_type": "video", "keyword": keyword, "page": str(page)}
            )
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                resp = await client.get(
                    "https://api.bilibili.com/x/web-interface/search/type",
                    params=params,
                    headers=self._wbi.request_headers(),
                )
                payload = resp.json()
            if payload.get("code") != 0:
                return self._error(f"接口返回错误: {payload.get('message')}", started)
            items = (payload.get("data") or {}).get("result") or []
            data = [self._normalize_search(item) for item in items]
            return CrawlResult(
                success=True,
                data=data,
                message="搜索采集成功（wbi 签名）",
                source=self.NAME,
                count=len(data),
                elapsed=time.time() - started,
            )
        except Exception as exc:  # noqa: BLE001
            return self._error(f"搜索采集失败: {exc}", started)

    # ------------------------------------------------------------------ #
    # 工具
    # ------------------------------------------------------------------ #
    @staticmethod
    def _normalize_video(item: Dict[str, Any]) -> Dict[str, Any]:
        stat = item.get("stat") or {}
        owner = item.get("owner") or {}
        bvid = item.get("bvid", "")
        return {
            "bvid": bvid,
            "title": TAG_RE.sub("", item.get("title", "") or ""),
            "author": owner.get("name", "") or item.get("author", ""),
            "play": stat.get("view", item.get("play", 0)),
            "danmaku": stat.get("danmaku", item.get("video_review", 0)),
            "url": f"https://www.bilibili.com/video/{bvid}" if bvid else "",
            "source": "bilibili",
        }

    @staticmethod
    def _normalize_search(item: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "bvid": item.get("bvid", ""),
            "title": TAG_RE.sub("", item.get("title", "") or ""),
            "author": item.get("author", ""),
            "play": item.get("play", 0),
            "danmaku": item.get("video_review", 0),
            "duration": item.get("duration", ""),
            "url": item.get("arcurl", ""),
            "source": "bilibili",
        }

    def _error(self, message: str, started: float) -> CrawlResult:
        logger.warning("%s", message)
        return CrawlResult(
            success=False,
            data=[],
            message=message,
            source=self.NAME,
            elapsed=time.time() - started,
            error=message,
        )
