# -*- coding: utf-8 -*-
"""验证码自动处理（采集主流程接入点）· 集成测试

用本地"验证码墙"合成页验证端到端处理链（出票为 mock——不消耗真实额度）：
1. reCAPTCHA 墙：mock 出票 → 注入 → 提交 → 页面解锁
2. 图片验证码墙：mock 识别 → 填入 → 提交 → 页面解锁
3. 无验证码页：kind=None 不动作
"""
from __future__ import annotations

import asyncio

from crawlers.anticrawl.captcha_handler import detect_page_captcha, handle_captcha

RECAPTCHA_WALL = """<!doctype html>
<html><body>
  <div class="g-recaptcha" data-sitekey="6Le-wall-test-key"></div>
  <textarea id="g-recaptcha-response" name="g-recaptcha-response"></textarea>
  <button id="verify-btn">Verify</button>
  <div id="result"></div>
  <script>
    document.getElementById('verify-btn').addEventListener('click', () => {
      const v = document.getElementById('g-recaptcha-response').value;
      document.getElementById('result').textContent = v ? 'UNLOCKED' : 'DENIED';
    });
  </script>
</body></html>"""

IMAGE_WALL = """<!doctype html>
<html><body>
  <form id="f">
    <img id="captcha-img" src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7">
    <input type="text" name="code">
    <button type="submit" id="go">Submit</button>
  </form>
  <div id="result"></div>
  <script>
    document.getElementById('go').addEventListener('click', (e) => {
      e.preventDefault();
      const v = document.querySelector('input[name="code"]').value;
      document.getElementById('result').textContent = v ? 'UNLOCKED' : 'DENIED';
    });
  </script>
</body></html>"""

PLAIN_PAGE = "<!doctype html><html><body><p>没有验证码</p></body></html>"


class FakeTokenSolver:
    async def solve_antibot_token(self, kind, sitekey, page_url, **kwargs):
        return {"success": True, "token": "TOKEN-XYZ", "source": "capsolver", "error": None}


class FakeImageSolver:
    async def get_captcha_image(self, page, selector="img"):
        # 走真实实现（元素截图）
        from crawlers.anticrawl.captcha_solver import CaptchaSolver

        return await CaptchaSolver().get_captcha_image(page, selector)

    async def solve_image_captcha(self, image_data):
        return {"success": True, "solution": "k8m3", "source": "ddddocr", "error": None}


def test_handle_recaptcha_wall(tmp_path):
    html = tmp_path / "wall.html"
    html.write_text(RECAPTCHA_WALL, encoding="utf-8")

    async def body():
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.goto(html.as_uri())
            detected = await detect_page_captcha(page)
            result = await handle_captcha(
                page, solver=FakeTokenSolver(), submit_selector="#verify-btn"
            )
            unlocked = await page.locator("#result").inner_text()
            await browser.close()
            return detected, result, unlocked

    detected, result, unlocked = asyncio.run(body())
    assert detected["kind"] == "recaptcha_v2"
    assert detected["sitekey"] == "6Le-wall-test-key"
    assert result["success"] is True, result
    assert unlocked == "UNLOCKED"


def test_handle_image_wall(tmp_path):
    html = tmp_path / "wall.html"
    html.write_text(IMAGE_WALL, encoding="utf-8")

    async def body():
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.goto(html.as_uri())
            result = await handle_captcha(
                page, solver=FakeImageSolver(), submit_selector="#go"
            )
            value = await page.eval_on_selector(
                "input[name='code']", "el => el.value"
            )
            unlocked = await page.locator("#result").inner_text()
            await browser.close()
            return result, value, unlocked

    result, value, unlocked = asyncio.run(body())
    assert result["kind"] == "image"
    assert result["success"] is True, result
    assert value == "k8m3"
    assert unlocked == "UNLOCKED"


def test_no_captcha_page(tmp_path):
    html = tmp_path / "plain.html"
    html.write_text(PLAIN_PAGE, encoding="utf-8")

    async def body():
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.goto(html.as_uri())
            result = await handle_captcha(page)
            await browser.close()
            return result

    result = asyncio.run(body())
    assert result["success"] is False
    assert result["kind"] is None
