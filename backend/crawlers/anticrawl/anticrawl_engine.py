# -*- coding: utf-8 -*-
"""
反爬策略引擎

功能：
- Cloudflare 绕过
- 验证码处理
- 代理轮换
- 指纹伪装
- 行为模拟
"""
import asyncio
import logging
import random
from typing import Any, Dict, List, Optional

from .fingerprint import FingerprintMasker

logger = logging.getLogger(__name__)

# 尝试导入 Playwright
try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


class AntiCrawlEngine:
    """反爬策略引擎"""

    def __init__(self):
        self.fingerprint = FingerprintMasker()
        self._playwright = None
        self._browser = None
        self._proxies = []

    async def _get_browser(self):
        """获取浏览器实例"""
        if not PLAYWRIGHT_AVAILABLE:
            return None
        if self._browser is None:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(headless=True)
        return self._browser

    async def bypass_cloudflare(self, url: str, timeout: int = 30) -> Dict[str, Any]:
        """
        绕过 Cloudflare

        策略：
        1. 使用指纹伪装
        2. 模拟真实浏览器行为
        3. 等待挑战完成
        """
        if not PLAYWRIGHT_AVAILABLE:
            return {"success": False, "error": "Playwright 未安装"}

        browser = await self._get_browser()
        if not browser:
            return {"success": False, "error": "无法启动浏览器"}

        # 生成指纹
        fp_context = self.fingerprint.get_playwright_context()

        context = await browser.new_context(**fp_context)
        page = await context.new_page()

        try:
            # 应用指纹伪装
            self.fingerprint.apply_all_masks(page)

            # 模拟人类行为：随机延迟
            await asyncio.sleep(random.uniform(1, 3))

            # 访问页面
            response = await page.goto(url, wait_until="networkidle", timeout=timeout * 1000)

            # 检查是否还在挑战页面
            current_url = page.url
            if "challenge" in current_url.lower() or "cf-" in current_url.lower():
                # 等待挑战完成
                await asyncio.sleep(5)
                # 再次检查
                current_url = page.url
                if "challenge" in current_url.lower():
                    return {"success": False, "error": "Cloudflare 挑战未通过"}

            # 获取页面内容
            html = await page.content()
            cookies = await context.cookies()

            return {
                "success": True,
                "html": html,
                "cookies": cookies,
                "url": current_url,
            }

        except Exception as e:
            logger.error(f"绕过 Cloudflare 失败: {e}")
            return {"success": False, "error": str(e)}

        finally:
            await context.close()

    async def solve_captcha(self, image_data: bytes, captcha_type: str = "image") -> Dict[str, Any]:
        """
        验证码识别

        Args:
            image_data: 验证码图片数据
            captcha_type: 验证码类型 (image/slider/click)

        Returns:
            识别结果
        """
        # 这里可以集成第三方打码平台
        # 例如：2captcha、Anti-Captcha 等

        # 简单实现：返回需要人工处理
        return {
            "success": False,
            "error": "验证码识别需要集成第三方服务",
            "captcha_type": captcha_type,
            "image_size": len(image_data),
        }

    async def rotate_proxy(self) -> Optional[str]:
        """代理轮换"""
        if not self._proxies:
            return None
        return random.choice(self._proxies)

    def add_proxies(self, proxies: List[str]):
        """添加代理"""
        self._proxies.extend(proxies)

    async def simulate_human_behavior(self, page):
        """模拟人类行为"""
        # 随机滚动
        for _ in range(random.randint(1, 3)):
            await page.evaluate("window.scrollBy(0, window.innerHeight * 0.3)")
            await asyncio.sleep(random.uniform(0.5, 2))

        # 随机鼠标移动
        await page.mouse.move(
            random.randint(100, 800),
            random.randint(100, 600)
        )

        # 随机点击
        if random.random() > 0.7:
            elements = await page.query_selector_all("a, button")
            if elements:
                element = random.choice(elements)
                await element.hover()
                await asyncio.sleep(random.uniform(0.5, 1.5))

    async def fetch_with_stealth(
        self,
        url: str,
        wait_for: str = None,
        timeout: int = 30,
    ) -> Dict[str, Any]:
        """
        使用隐身模式获取页面

        策略：
        1. 指纹伪装
        2. 行为模拟
        3. 代理轮换
        """
        if not PLAYWRIGHT_AVAILABLE:
            return {"success": False, "error": "Playwright 未安装"}

        browser = await self._get_browser()
        if not browser:
            return {"success": False, "error": "无法启动浏览器"}

        # 生成指纹
        fp_context = self.fingerprint.get_playwright_context()

        # 代理
        proxy = await self.rotate_proxy()
        if proxy:
            fp_context["proxy"] = {"server": proxy}

        context = await browser.new_context(**fp_context)
        page = await context.new_page()

        try:
            # 应用指纹伪装
            self.fingerprint.apply_all_masks(page)

            # 模拟人类行为
            await self.simulate_human_behavior(page)

            # 访问页面
            response = await page.goto(url, wait_until="networkidle", timeout=timeout * 1000)

            # 等待指定元素
            if wait_for:
                await page.wait_for_selector(wait_for, timeout=10000)

            # 再次模拟人类行为
            await self.simulate_human_behavior(page)

            # 获取内容
            html = await page.content()
            cookies = await context.cookies()

            return {
                "success": True,
                "html": html,
                "cookies": cookies,
                "url": page.url,
            }

        except Exception as e:
            logger.error(f"隐身获取失败: {e}")
            return {"success": False, "error": str(e)}

        finally:
            await context.close()

    async def close(self):
        """关闭浏览器"""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
