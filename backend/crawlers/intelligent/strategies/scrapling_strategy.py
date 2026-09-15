# -*- coding: utf-8 -*-
"""
Scrapling 策略 - 智能爬虫系统 v2.0

基于 scrapling 的高性能 HTML 解析策略，适用于静态和动态页面。
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, List, Optional

from ..models import CrawlIntent, IntentType, ProbeResult, StrategyResult
from .base import BaseStrategy


class ScraplingStrategy(BaseStrategy):
    """Scrapling 爬取策略

    基于 парсинг 框架的高性能解析。
    适用于:
    - 静态 HTML 解析
    - 动态内容提取
    - 结构化数据抽取
    """

    name: str = "scrapling"
    priority: int = 90

    def __init__(
        self,
        timeout: int = 30,
        browser: bool = False,
        extraction_mode: str = "fast",
    ) -> None:
        self.timeout = timeout
        self.browser = browser
        self.extraction_mode = extraction_mode

    async def can_handle(self, probe: ProbeResult) -> bool:
        """判断是否可处理。

        HTML 页面均可处理：普通页面走 Fetcher；
        保护页 / 挑战特征自动升级 StealthyFetcher（patchright 反检测浏览器）。
        """
        return bool(probe.is_html)

    async def execute(
        self,
        url: str,
        intent: Optional[CrawlIntent] = None,
        **kwargs: Any,
        ) -> StrategyResult:
        """执行 Scrapling 解析"""
        start_time = time.time()
        intent = intent or CrawlIntent()

        try:
            from scrapling.fetchers import Fetcher, StealthyFetcher

            dynamic = self.browser or intent.intent_type == IntentType.DYNAMIC_CONTENT
            used_stealth = dynamic
            if dynamic:
                # 动态内容 / 浏览器模式 → StealthyFetcher（patchright 反检测）
                page = await asyncio.to_thread(
                    StealthyFetcher.fetch, url, headless=True
                )
            else:
                page = await asyncio.to_thread(Fetcher.get, url)
                # 挑战特征（CF / 403 / 验证页）→ 自动升级 StealthyFetcher
                if self._looks_challenged(page):
                    page = await asyncio.to_thread(
                        StealthyFetcher.fetch, url, headless=True
                    )
                    used_stealth = True

            duration_ms = (time.time() - start_time) * 1000

            content = str(getattr(page, "html_content", "") or "")
            title = getattr(page, "title", "") or ""
            status = int(getattr(page, "status", 200) or 200)

            data: Dict[str, Any] = {
                "url": url,
                "title": title,
                "html": content,
                "links": page.links if hasattr(page, "links") else [],
            }

            if intent.pagination:
                data["pagination"] = True

            return StrategyResult(
                strategy_name=self.name,
                success=True,
                data=data,
                content=content,
                duration_ms=duration_ms,
                status_code=status,
                metadata={
                    "title": title,
                    "extraction_mode": self.extraction_mode,
                    "stealth": used_stealth,
                },
            )

        except ImportError:
            return StrategyResult(
                strategy_name=self.name,
                success=False,
                error="scrapling not installed",
                duration_ms=(time.time() - start_time) * 1000,
            )
        except Exception as e:
            return StrategyResult(
                strategy_name=self.name,
                success=False,
                error=f"Scrapling error: {str(e)}",
                duration_ms=(time.time() - start_time) * 1000,
            )

    @staticmethod
    def _looks_challenged(page) -> bool:
        """检测反爬挑战特征（状态码 / 挑战页标记），命中则升级 StealthyFetcher。"""
        status = int(getattr(page, "status", 200) or 200)
        if status in (403, 429, 503):
            return True
        content = str(getattr(page, "html_content", "") or "")
        markers = (
            "cf-challenge",
            "Just a moment",
            "Checking your browser",
            "challenge-platform",
            "Attention Required",
        )
        return any(marker in content for marker in markers)

    def get_timeout(self) -> int:
        """获取超时时间"""
        return self.timeout

    def get_capabilities(self) -> List[str]:
        """获取策略能力"""
        return [
            "html_parsing",
            "css_selectors",
            "json_extraction",
            "dynamic_content",
            "link_extraction",
        ]
