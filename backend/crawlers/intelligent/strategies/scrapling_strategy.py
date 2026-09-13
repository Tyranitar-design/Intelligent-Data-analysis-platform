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
        """判断是否可处理

        适用于:
        - HTML 内容
        - 非保护页面
        """
        if not probe.is_html:
            return False
        if probe.is_protected:
            return False
        return True

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
            from scrapling import Autodriver, Phantom

            if self.browser or intent.intent_type == IntentType.DYNAMIC_CONTENT:
                driver = Autodriver()
                page = driver.load(url)
            else:
                page = Phantom.get(url)

            duration_ms = (time.time() - start_time) * 1000

            content = page.html
            title = page.title or ""

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
                status_code=200,
                metadata={
                    "title": title,
                    "extraction_mode": self.extraction_mode,
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
