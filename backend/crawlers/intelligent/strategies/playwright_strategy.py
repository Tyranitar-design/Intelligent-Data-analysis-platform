# -*- coding: utf-8 -*-
"""
Playwright 策略 - 智能爬虫系统 v2.0

基于 Playwright 的全面浏览器自动化策略，适用于复杂动态页面和受保护内容。
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, List, Optional

from ..models import CrawlIntent, IntentType, ProbeResult, StrategyResult
from .base import BaseStrategy


class PlaywrightStrategy(BaseStrategy):
    """Playwright 爬取策略

    基于 Playwright 的浏览器自动化。
    适用于:
    - 受保护页面
    - 需要复杂交互的页面
    - 需要验证码处理的页面
    - 需要认证的页面
    """

    name: str = "playwright"
    priority: int = 70

    def __init__(
        self,
        timeout: int = 60,
        headless: bool = True,
        browser_type: str = "chromium",
        viewport: Optional[Dict[str, int]] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        self.timeout = timeout
        self.headless = headless
        self.browser_type = browser_type
        self.viewport = viewport or {"width": 1920, "height": 1080}
        self.user_agent = user_agent
        self._browser = None
        self._context = None

    async def can_handle(self, probe: ProbeResult) -> bool:
        """判断是否可处理

        可以处理任何类型的页面。
        """
        return True

    async def execute(
        self,
        url: str,
        intent: Optional[CrawlIntent] = None,
        **kwargs: Any,
    ) -> StrategyResult:
        """执行 Playwright 爬取"""
        start_time = time.time()
        intent = intent or CrawlIntent()

        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser_cls = getattr(p, self.browser_type)
                browser = await browser_cls.launch(headless=self.headless)
                context = await browser.new_context(
                    viewport=self.viewport,
                    user_agent=self.user_agent,
                )

                page = await context.new_page()

                if intent.require_auth and intent.cookies:
                    for name, value in intent.cookies.items():
                        await context.add_cookies([{
                            "name": name,
                            "value": value,
                            "domain": self._extract_domain(url),
                            "path": "/",
                        }])

                response = await page.goto(
                    url,
                    timeout=self.timeout * 1000,
                    wait_until="networkidle",
                )

                content = await page.content()

                title = await page.title()

                if intent.pagination:
                    await self._handle_pagination(page)

                await browser.close()

                duration_ms = (time.time() - start_time) * 1000

                data: Dict[str, Any] = {
                    "url": url,
                    "title": title,
                    "html": content,
                    "links": await self._extract_links(page),
                }

                return StrategyResult(
                    strategy_name=self.name,
                    success=True,
                    data=data,
                    content=content,
                    duration_ms=duration_ms,
                    status_code=response.status if response else 200,
                    metadata={"title": title},
                )

        except ImportError:
            return StrategyResult(
                strategy_name=self.name,
                success=False,
                error="playwright not installed",
                duration_ms=(time.time() - start_time) * 1000,
            )
        except Exception as e:
            return StrategyResult(
                strategy_name=self.name,
                success=False,
                error=f"Playwright error: {str(e)}",
                duration_ms=(time.time() - start_time) * 1000,
            )

    async def _extract_links(self, page: Any) -> List[str]:
        """提取页面链接"""
        try:
            links = await page.query_selector_all("a[href]")
            return [
                await link.get_attribute("href")
                for link in links
                if await link.get_attribute("href")
            ]
        except Exception:
            return []

    async def _handle_pagination(self, page: Any) -> None:
        """处理分页"""
        try:
            next_button = await page.query_selector("a.next, button.next, [rel='next']")
            if next_button:
                await next_button.click()
                await page.wait_for_load_state("networkidle")
        except Exception:
            pass

    def _extract_domain(self, url: str) -> str:
        """提取域名"""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.netloc

    def get_timeout(self) -> int:
        """获取超时时间"""
        return self.timeout

    def get_capabilities(self) -> List[str]:
        """获取策略能力"""
        return [
            "full_browser_automation",
            "javascript_rendering",
            "cookie_management",
            "screenshot",
            "pdf_generation",
            "keyboard_input",
            "mouse_interaction",
        ]

    async def close(self) -> None:
        """关闭浏览器"""
        if self._browser:
            await self._browser.close()
            self._browser = None
            self._context = None
