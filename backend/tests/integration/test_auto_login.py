# -*- coding: utf-8 -*-
"""登录态自动化闭环 · 集成测试

覆盖：
1. 表单自动探测（本地合成页）：password 定位 + username 近邻 + submit 按钮
2. 探测变体：无 id（用 name 属性）→ 生成 name 选择器
3. 真实闭环（quotes.toscrape.com/login 练习站）：
   自动登录 → 无错误提示 → Cookie 保存 → **复用回归**（带 Cookie 访问主页含 Logout）

注意：真实站测试会写本地 cookie store，teardown 清理。
"""
from __future__ import annotations

import asyncio

import pytest

from crawlers.auth.form_detector import detect_login_form

LOCAL_PAGE = """<!doctype html>
<html><body>
<form action="/login" method="post">
  <input id="user-field" name="username" type="text" placeholder="Username">
  <input id="pass-field" name="password" type="password">
  <button type="submit">Login</button>
</form>
</body></html>
"""

LOCAL_PAGE_NO_ID = """<!doctype html>
<html><body>
<form action="/login" method="post">
  <input name="email" type="email">
  <input name="pwd" type="password">
  <input type="submit" value="Sign in">
</form>
</body></html>
"""


def _run(body):
    return asyncio.run(body())


def test_detect_form_with_ids(tmp_path):
    html = tmp_path / "login.html"
    html.write_text(LOCAL_PAGE, encoding="utf-8")

    async def body():
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.goto(html.as_uri())
            result = await detect_login_form(page)
            await browser.close()
            return result

    result = _run(body)
    assert result is not None
    assert result["username"] == "#user-field"
    assert result["password"] == "#pass-field"
    assert result["submit"] == "button[type='submit']" or result["submit"] == "button"


def test_detect_form_by_name_attributes(tmp_path):
    html = tmp_path / "login.html"
    html.write_text(LOCAL_PAGE_NO_ID, encoding="utf-8")

    async def body():
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.goto(html.as_uri())
            result = await detect_login_form(page)
            await browser.close()
            return result

    result = _run(body)
    assert result is not None
    assert result["username"] == 'input[name="email"]'
    assert result["password"] == 'input[name="pwd"]'
    assert result["submit"] is not None


def test_detect_form_absent_returns_none(tmp_path):
    html = tmp_path / "plain.html"
    html.write_text("<!doctype html><html><body><p>no form</p></body></html>", encoding="utf-8")

    async def body():
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.goto(html.as_uri())
            result = await detect_login_form(page)
            await browser.close()
            return result

    assert _run(body) is None


# --------------------------------------------------------------------------- #
# 真实闭环（练习站）
# --------------------------------------------------------------------------- #
QUOTES_LOGIN = "https://quotes.toscrape.com/login"
PLATFORM = "quotes-loop-test"


@pytest.fixture()
def cleanup_cookies():
    yield
    from crawlers.auth.cookie_store import CookieStore

    store = CookieStore()
    try:
        store.delete_cookies(PLATFORM)
        store.invalidate_session(PLATFORM)
    except Exception:  # noqa: BLE001
        pass


def test_real_login_and_reuse_loop(cleanup_cookies):
    """自动登录 → Cookie 保存 → 复用回归（登录态页面出现 Logout）。"""
    from crawlers.auth.auth_manager import AuthManager

    async def body():
        manager = AuthManager()
        try:
            # 1) 自动登录（不给选择器——走表单探测路径）
            login = await manager.login_with_playwright(
                platform=PLATFORM,
                username="reviewer",
                password="any-pass-123",
                login_url=QUOTES_LOGIN,
            )
            if not login.get("success"):
                return login, None, None

            # 2) Cookie 已保存
            cookies = manager.cookie_store.get_cookies(PLATFORM)

            # 3) 复用回归：带 Cookie 访问主页，应看到 Logout
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch()
                context = await browser.new_context()
                await context.add_cookies(cookies)
                page = await context.new_page()
                await page.goto("https://quotes.toscrape.com/", wait_until="domcontentloaded", timeout=45000)
                body_text = await page.locator("body").inner_text()
                await browser.close()
            return login, cookies, body_text
        finally:
            await manager.close()

    login, cookies, body_text = _run(body)
    assert login.get("success") is True, login
    assert cookies, "cookie 未保存"
    assert body_text and "Logout" in body_text, "复用回归失败：未出现 Logout"
