# -*- coding: utf-8 -*-
"""
动态页面爬取模块 - Phase 4.6.3

针对 JS 渲染页面、SPA、无限滚动、需要交互的页面

技术栈：
- Playwright（浏览器自动化）
- Scrapling StealthyFetcher（反爬绕过）
- crawl4ai（智能提取）

功能：
1. 自动检测页面是否需要动态渲染
2. 等待元素出现
3. 自动滚动加载
4. 点击加载更多
5. 浏览器会话复用
"""
import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .base import CrawlResult

logger = logging.getLogger(__name__)

# 尝试导入 Playwright
try:
    from playwright.async_api import async_playwright, Page, Browser
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright 未安装，动态页面爬取将不可用")

# 尝试导入 Scrapling
try:
    from .scrapling_adapter import ScraplingAdapter
    SCRAPLING_AVAILABLE = True
except ImportError:
    SCRAPLING_AVAILABLE = False

# 尝试导入 crawl4ai
try:
    from crawl4ai import AsyncWebCrawler
    CRAWL4AI_AVAILABLE = True
except ImportError:
    CRAWL4AI_AVAILABLE = False


@dataclass
class DynamicCrawlOptions:
    """动态爬取选项"""
    wait_for: Optional[str] = None          # 等待 CSS 选择器
    wait_time: int = 5                      # 等待时间（秒）
    auto_scroll: bool = False               # 是否自动滚动
    scroll_count: int = 3                   # 滚动次数
    click_selector: Optional[str] = None    # 点击元素选择器
    click_count: int = 1                    # 点击次数
    headless: bool = True                   # 是否无头模式
    viewport: Tuple[int, int] = (1920, 1080)  # 视口大小
    user_agent: Optional[str] = None        # 自定义 UA
    cookies: Optional[List[Dict]] = None    # Cookie
    proxy: Optional[str] = None             # 代理


class DynamicCrawler:
    """动态页面爬取器"""

    def __init__(self):
        self._playwright = None
        self._browser = None
        self._scrapling = None

    @property
    def scrapling(self):
        if self._scrapling is None and SCRAPLING_AVAILABLE:
            self._scrapling = ScraplingAdapter()
        return self._scrapling

    async def _get_browser(self) -> Optional[Any]:
        """获取浏览器实例"""
        if not PLAYWRIGHT_AVAILABLE:
            return None
        if self._browser is None:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(headless=True)
        return self._browser

    async def crawl_dynamic(
        self,
        url: str,
        options: DynamicCrawlOptions = None,
    ) -> CrawlResult:
        """
        动态页面爬取

        Args:
            url: 目标 URL
            options: 动态爬取选项

        Returns:
            CrawlResult
        """
        if options is None:
            options = DynamicCrawlOptions()

        start_time = asyncio.get_event_loop().time()

        try:
            # 优先尝试 Playwright
            if PLAYWRIGHT_AVAILABLE:
                html = await self._crawl_with_playwright(url, options)
                if html:
                    return self._build_result(html, "playwright", start_time)

            # 其次尝试 Scrapling StealthyFetcher
            if self.scrapling and self.scrapling.available:
                html = await self._crawl_with_scrapling(url, options)
                if html:
                    return self._build_result(html, "scrapling", start_time)

            # 最后尝试 crawl4ai
            if CRAWL4AI_AVAILABLE:
                result = await self._crawl_with_crawl4ai(url, options)
                if result:
                    return self._build_result(result, "crawl4ai", start_time)

            return CrawlResult(
                success=False,
                data=[],
                message="动态页面爬取失败：所有策略均不可用",
                source="dynamic_crawler",
                error="No dynamic crawler available",
            )

        except Exception as e:
            logger.error(f"动态爬取异常: {e}")
            return CrawlResult(
                success=False,
                data=[],
                message=f"动态爬取异常: {str(e)}",
                source="dynamic_crawler",
                error=str(e),
            )

    async def _crawl_with_playwright(self, url: str, options: DynamicCrawlOptions) -> Optional[str]:
        """使用 Playwright 爬取动态页面"""
        browser = await self._get_browser()
        if not browser:
            return None

        context = await browser.new_context(
            viewport={"width": options.viewport[0], "height": options.viewport[1]},
            user_agent=options.user_agent,
            proxy={"server": options.proxy} if options.proxy else None,
        )

        if options.cookies:
            await context.add_cookies(options.cookies)

        page = await context.new_page()

        try:
            # 导航到页面
            await page.goto(url, wait_until="networkidle", timeout=30000)

            # 等待指定元素
            if options.wait_for:
                try:
                    await page.wait_for_selector(options.wait_for, timeout=options.wait_time * 1000)
                except Exception:
                    logger.warning(f"等待元素超时: {options.wait_for}")

            # 点击加载更多
            if options.click_selector:
                for _ in range(options.click_count):
                    try:
                        await page.click(options.click_selector)
                        await asyncio.sleep(2)
                    except Exception:
                        break

            # 自动滚动
            if options.auto_scroll:
                for _ in range(options.scroll_count):
                    await page.evaluate("window.scrollBy(0, window.innerHeight)")
                    await asyncio.sleep(1)

            # 获取页面内容
            html = await page.content()
            return html

        except Exception as e:
            logger.warning(f"Playwright 爬取失败: {e}")
            return None
        finally:
            await context.close()

    async def _crawl_with_scrapling(self, url: str, options: DynamicCrawlOptions) -> Optional[str]:
        """使用 Scrapling StealthyFetcher 爬取"""
        if not self.scrapling:
            return None

        try:
            response = await self.scrapling.fetch_stealthy(
                url=url,
                wait_for=options.wait_for,
                auto_scroll=options.auto_scroll,
                headless=options.headless,
            )
            if response:
                return self.scrapling.get_page_html(response)
            return None
        except Exception as e:
            logger.warning(f"Scrapling 动态爬取失败: {e}")
            return None

    async def _crawl_with_crawl4ai(self, url: str, options: DynamicCrawlOptions) -> Optional[Dict[str, Any]]:
        """使用 crawl4ai 爬取"""
        if not CRAWL4AI_AVAILABLE:
            return None

        try:
            async with AsyncWebCrawler() as crawler:
                result = await crawler.arun(url=url)
                return {
                    "markdown": result.markdown,
                    "html": getattr(result, "cleaned_html", None) or getattr(result, "html", ""),
                    "links": getattr(result, "links", []),
                    "media": getattr(result, "media", []),
                    "metadata": getattr(result, "metadata", {}),
                }
        except Exception as e:
            logger.warning(f"crawl4ai 动态爬取失败: {e}")
            return None

    def _build_result(self, content: Any, strategy: str, start_time: float) -> CrawlResult:
        """构建爬取结果"""
        elapsed = asyncio.get_event_loop().time() - start_time

        if isinstance(content, dict):
            # crawl4ai 结果
            return CrawlResult(
                success=True,
                data=[content],
                message=f"动态爬取成功 | 策略: {strategy} | crawl4ai 结果",
                source="dynamic_crawler",
                count=1,
                elapsed=elapsed,
            )
        else:
            # HTML 结果
            return CrawlResult(
                success=True,
                data=[{"html": content, "strategy": strategy}],
                message=f"动态爬取成功 | 策略: {strategy} | HTML 内容",
                source="dynamic_crawler",
                count=1,
                elapsed=elapsed,
            )

    async def close(self):
        """关闭浏览器"""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
