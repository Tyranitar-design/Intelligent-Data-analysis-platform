# -*- coding: utf-8 -*-
"""
Crawl4AI 策略 - 智能爬虫系统 v2.0

基于 crawl4ai 的 AI 友好爬取策略，适用于需要 JavaScript 渲染的页面。
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, List, Optional

from ..models import CrawlIntent, IntentType, ProbeResult, StrategyResult
from .base import BaseStrategy


class Crawl4AIStrategy(BaseStrategy):
    """Crawl4AI 爬取策略

    基于 crawl4ai 的智能爬取。
    适用于:
    - JavaScript 渲染页面
    - SPA 应用
    - 需要等待动态内容加载的页面
    """

    name: str = "crawl4ai"
    priority: int = 80

    def __init__(
        self,
        timeout: int = 60,
        headless: bool = True,
        wait_for_selector: Optional[str] = None,
        js_code: Optional[List[str]] = None,
    ) -> None:
        self.timeout = timeout
        self.headless = headless
        self.wait_for_selector = wait_for_selector
        self.js_code = js_code or []

    async def can_handle(self, probe: ProbeResult) -> bool:
        """判断是否可处理

        适用于:
        - 动态内容页面
        - SPA 应用
        - 需要 JS 渲染的页面
        """
        if probe.is_protected:
            return False
        if probe.detected_intent == IntentType.API_DATA:
            return False
        return True

    async def execute(
        self,
        url: str,
        intent: Optional[CrawlIntent] = None,
        **kwargs: Any,
    ) -> StrategyResult:
        """执行 Crawl4AI 爬取"""
        start_time = time.time()
        intent = intent or CrawlIntent()

        try:
            from crawl4ai import AsyncWebCrawler

            async with AsyncWebCrawler(
                headless=self.headless,
                verbose=False,
            ) as crawler:
                result = await crawler.araw_html(
                    url=url,
                    timeout=self.timeout,
                    js_code=self.js_code if self.js_code else None,
                    wait_for_selector=self.wait_for_selector,
                )

                duration_ms = (time.time() - start_time) * 1000

                if result.success:
                    data: Dict[str, Any] = {
                        "url": url,
                        "html": result.html,
                        "links": result.links or {},
                        "media": result.media or {},
                        "metadata": result.metadata or {},
                    }

                    return StrategyResult(
                        strategy_name=self.name,
                        success=True,
                        data=data,
                        content=result.html,
                        duration_ms=duration_ms,
                        status_code=200,
                        metadata={
                            "extracted_content": result.extracted_content if hasattr(result, "extracted_content") else None,
                        },
                    )
                else:
                    return StrategyResult(
                        strategy_name=self.name,
                        success=False,
                        error=result.error_message or "Unknown error",
                        duration_ms=duration_ms,
                    )

        except ImportError:
            return StrategyResult(
                strategy_name=self.name,
                success=False,
                error="crawl4ai not installed",
                duration_ms=(time.time() - start_time) * 1000,
            )
        except Exception as e:
            return StrategyResult(
                strategy_name=self.name,
                success=False,
                error=f"Crawl4AI error: {str(e)}",
                duration_ms=(time.time() - start_time) * 1000,
            )

    def get_timeout(self) -> int:
        """获取超时时间"""
        return self.timeout

    def get_capabilities(self) -> List[str]:
        """获取策略能力"""
        return [
            "javascript_rendering",
            "spa_support",
            "ai_extraction",
            "screenshot",
            "pdf_generation",
        ]
