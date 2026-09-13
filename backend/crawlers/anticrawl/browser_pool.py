# -*- coding: utf-8 -*-
"""
浏览器池

功能：
- 管理多个浏览器实例
- 指纹轮换
- 会话隔离
"""
import asyncio
import logging
from typing import Any, Dict, List, Optional

from .fingerprint import FingerprintMasker

logger = logging.getLogger(__name__)

# 尝试导入 Playwright
try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


class BrowserPool:
    """浏览器池"""

    def __init__(self, max_browsers: int = 3):
        self.max_browsers = max_browsers
        self.fingerprint = FingerprintMasker()
        self._playwright = None
        self._browsers: List[Browser] = []
        self._contexts: List[BrowserContext] = []
        self._current_index = 0

    async def _get_playwright(self):
        """获取 Playwright 实例"""
        if not PLAYWRIGHT_AVAILABLE:
            return None
        if self._playwright is None:
            self._playwright = await async_playwright().start()
        return self._playwright

    async def create_browser(self) -> Optional[Browser]:
        """创建浏览器实例"""
        if not PLAYWRIGHT_AVAILABLE:
            return None

        playwright = await self._get_playwright()
        if not playwright:
            return None

        try:
            browser = await playwright.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-accelerated-2d-canvas",
                    "--disable-gpu",
                    "--window-size=1920,1080",
                ]
            )
            self._browsers.append(browser)
            return browser
        except Exception as e:
            logger.error(f"创建浏览器失败: {e}")
            return None

    async def create_context(self, browser: Browser = None, cookies: List[Dict] = None) -> Optional[BrowserContext]:
        """创建浏览器上下文"""
        if not browser:
            browser = await self.create_browser()
        if not browser:
            return None

        # 生成新指纹
        fp_context = self.fingerprint.get_playwright_context()

        try:
            context = await browser.new_context(**fp_context)

            # 注入 Cookie
            if cookies:
                await context.add_cookies(cookies)

            self._contexts.append(context)
            return context
        except Exception as e:
            logger.error(f"创建上下文失败: {e}")
            return None

    async def get_page(self, cookies: List[Dict] = None) -> Optional[Page]:
        """获取页面"""
        context = await self.create_context(cookies=cookies)
        if not context:
            return None

        try:
            page = await context.new_page()
            # 应用指纹伪装
            self.fingerprint.apply_all_masks(page)
            return page
        except Exception as e:
            logger.error(f"创建页面失败: {e}")
            return None

    async def rotate_browser(self) -> Optional[Browser]:
        """轮换浏览器"""
        if not self._browsers:
            return await self.create_browser()

        self._current_index = (self._current_index + 1) % len(self._browsers)
        return self._browsers[self._current_index]

    async def close_all(self):
        """关闭所有浏览器"""
        for context in self._contexts:
            try:
                await context.close()
            except:
                pass
        self._contexts.clear()

        for browser in self._browsers:
            try:
                await browser.close()
            except:
                pass
        self._browsers.clear()

        if self._playwright:
            try:
                await self._playwright.stop()
            except:
                pass
            self._playwright = None
