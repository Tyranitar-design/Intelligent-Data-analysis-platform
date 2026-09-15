# -*- coding: utf-8 -*-
"""
登录态管理器

功能：
- 多平台登录管理
- Cookie/Token 自动刷新
- 登录状态检测
- CDP 登录交互
"""
import asyncio
import logging
from typing import Any, Dict, List, Optional

from .cookie_store import CookieStore
from .form_detector import detect_login_form
from .login_flows import get_login_flow, list_supported_platforms

logger = logging.getLogger(__name__)

# 尝试导入 Playwright
try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


class AuthManager:
    """登录态管理器"""

    def __init__(self):
        self.cookie_store = CookieStore()
        self._playwright = None
        self._browser = None

    async def _get_browser(self):
        """获取浏览器实例"""
        if not PLAYWRIGHT_AVAILABLE:
            return None
        if self._browser is None:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(headless=True)
        return self._browser

    async def login_with_playwright(
        self,
        platform: str,
        username: str,
        password: str,
        login_url: str = None,
        username_selector: str = None,
        password_selector: str = None,
        submit_selector: str = None,
        wait_for: str = None,
    ) -> Dict[str, Any]:
        """
        使用 Playwright 自动登录

        支持预置平台配置，也支持自定义参数
        """
        # 获取平台配置
        flow = get_login_flow(platform)

        # 选择器：自定义参数 > 平台预置 > （导航后）自动探测
        login_url = login_url or flow.get("login_url")
        username_selector = username_selector or flow.get("username_selector")
        password_selector = password_selector or flow.get("password_selector")
        submit_selector = submit_selector or flow.get("submit_selector")
        wait_for = wait_for or flow.get("wait_for")

        if not PLAYWRIGHT_AVAILABLE:
            return {"success": False, "error": "Playwright 未安装"}

        browser = await self._get_browser()
        if not browser:
            return {"success": False, "error": "无法启动浏览器"}

        context = await browser.new_context()
        page = await context.new_page()

        try:
            # 导航到登录页
            await page.goto(login_url, wait_until="networkidle", timeout=30000)

            # 选择器缺省时自动探测登录表单（通用化关键）
            if not (username_selector and password_selector):
                detected = await detect_login_form(page) or {}
                username_selector = username_selector or detected.get("username")
                password_selector = password_selector or detected.get("password")
                submit_selector = submit_selector or detected.get("submit")
            if not password_selector or not submit_selector:
                return {"success": False, "error": "无法定位登录表单（password/submit 缺失）"}

            # 填写用户名（部分站点允许空用户名，字段缺失时跳过）
            if username_selector:
                await page.fill(username_selector, username)

            # 填写密码
            await page.fill(password_selector, password)

            # 点击登录
            await page.click(submit_selector)

            # 等待登录完成
            if wait_for:
                await page.wait_for_selector(wait_for, timeout=10000)
            else:
                await asyncio.sleep(2.5)

            # 登录失败检测：可见错误提示 → 不保存 Cookie，直接返回失败
            error_text = await page.evaluate(
                """() => {
                    const els = document.querySelectorAll(
                        '.error, .alert, [class*="error"], [role="alert"]'
                    );
                    for (const el of els) {
                        if (el.offsetParent !== null &&
                            /invalid|incorrect|wrong|失败|错误/i.test(el.textContent || '')) {
                            return (el.textContent || '').trim().slice(0, 120);
                        }
                    }
                    return null;
                }"""
            )
            if error_text:
                logger.warning("登录被拒: %s (%s)", platform, error_text)
                return {"success": False, "error": f"登录被拒: {error_text}"}

            # 获取 Cookie
            cookies = await context.cookies()

            # 保存 Cookie
            self.cookie_store.save_cookies(platform, cookies)

            # 保存会话
            session_data = {
                "login_url": login_url,
                "username": username,
                "cookies": cookies,
            }
            self.cookie_store.save_session(platform, session_data)

            logger.info(f"登录成功: {platform}")

            return {
                "success": True,
                "message": f"登录成功: {platform}",
                "cookies_count": len(cookies),
                "platform": platform,
            }

        except Exception as e:
            logger.error(f"登录失败: {e}")
            return {"success": False, "error": str(e)}

        finally:
            await context.close()

    async def login_with_cookies(
        self,
        platform: str,
        cookies: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        使用 Cookie 登录

        Args:
            platform: 平台名称
            cookies: Cookie 列表

        Returns:
            登录结果
        """
        try:
            self.cookie_store.save_cookies(platform, cookies)
            session_data = {"cookies": cookies}
            self.cookie_store.save_session(platform, session_data)

            logger.info(f"Cookie 登录成功: {platform}")
            return {
                "success": True,
                "message": f"Cookie 登录成功: {platform}",
                "cookies_count": len(cookies),
            }
        except Exception as e:
            logger.error(f"Cookie 登录失败: {e}")
            return {"success": False, "error": str(e)}

    async def check_login_status(self, platform: str, check_url: str = None) -> Dict[str, Any]:
        """
        检测登录状态

        Args:
            platform: 平台名称
            check_url: 用于检测的 URL

        Returns:
            登录状态
        """
        cookies = self.cookie_store.get_cookies(platform)
        if not cookies:
            return {"is_logged_in": False, "message": "无 Cookie"}

        if not check_url:
            return {"is_logged_in": True, "message": "有 Cookie", "cookies_count": len(cookies)}

        # 使用 Cookie 访问检测页面
        if not PLAYWRIGHT_AVAILABLE:
            return {"is_logged_in": True, "message": "有 Cookie（未验证）"}

        browser = await self._get_browser()
        if not browser:
            return {"is_logged_in": True, "message": "有 Cookie（未验证）"}

        context = await browser.new_context()
        page = await context.new_page()

        try:
            # 注入 Cookie
            await context.add_cookies(cookies)

            # 访问检测页面
            response = await page.goto(check_url, wait_until="networkidle", timeout=10000)

            # 检查是否跳转到了登录页
            current_url = page.url
            if "login" in current_url.lower() or "signin" in current_url.lower():
                return {"is_logged_in": False, "message": "Cookie 已过期"}

            return {"is_logged_in": True, "message": "登录状态有效"}

        except Exception as e:
            logger.error(f"检测登录状态失败: {e}")
            return {"is_logged_in": False, "error": str(e)}

        finally:
            await context.close()

    async def get_auth_headers(self, platform: str) -> Dict[str, str]:
        """获取认证头"""
        cookies = self.cookie_store.get_cookies(platform)
        if not cookies:
            return {}

        # 构建 Cookie 字符串
        cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])

        return {
            "Cookie": cookie_str,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }

    async def logout(self, platform: str) -> bool:
        """登出"""
        try:
            self.cookie_store.delete_cookies(platform)
            self.cookie_store.invalidate_session(platform)
            logger.info(f"登出成功: {platform}")
            return True
        except Exception as e:
            logger.error(f"登出失败: {e}")
            return False

    async def list_platforms(self) -> List[str]:
        """列出已登录的平台"""
        return self.cookie_store.list_platforms()

    def list_supported_platforms(self) -> Dict[str, str]:
        """列出支持的平台"""
        return list_supported_platforms()

    async def close(self):
        """关闭浏览器"""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
