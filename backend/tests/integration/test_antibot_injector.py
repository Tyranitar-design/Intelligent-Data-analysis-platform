# -*- coding: utf-8 -*-
"""行为验证码注入器 · 集成测试（本地合成页，Playwright）

覆盖：三类响应字段的写入 + data-sitekey 提取。
"""
from __future__ import annotations

import asyncio

from crawlers.anticrawl.antibot_injector import detect_sitekey, inject_token

PAGE = """<!doctype html>
<html><body>
  <div class="g-recaptcha" data-sitekey="6Le-test-key-AAAA"></div>
  <textarea id="g-recaptcha-response" name="g-recaptcha-response"></textarea>
  <textarea name="h-captcha-response" style="display:none"></textarea>
  <input type="hidden" name="cf-turnstile-response" value="">
</body></html>
"""


def _run(body):
    return asyncio.run(body())


def test_inject_recaptcha(tmp_path):
    html = tmp_path / "inject.html"
    html.write_text(PAGE, encoding="utf-8")

    async def body():
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.goto(html.as_uri())
            ok = await inject_token(page, "recaptcha_v2", "TOKEN-RC")
            value = await page.eval_on_selector(
                "#g-recaptcha-response", "el => el.value"
            )
            await browser.close()
            return ok, value

    ok, value = _run(body)
    assert ok is True
    assert value == "TOKEN-RC"


def test_inject_hcaptcha(tmp_path):
    html = tmp_path / "inject.html"
    html.write_text(PAGE, encoding="utf-8")

    async def body():
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.goto(html.as_uri())
            ok = await inject_token(page, "hcaptcha", "TOKEN-HC")
            value = await page.eval_on_selector(
                "textarea[name='h-captcha-response']", "el => el.value"
            )
            await browser.close()
            return ok, value

    ok, value = _run(body)
    assert ok is True
    assert value == "TOKEN-HC"


def test_inject_turnstile(tmp_path):
    html = tmp_path / "inject.html"
    html.write_text(PAGE, encoding="utf-8")

    async def body():
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.goto(html.as_uri())
            ok = await inject_token(page, "turnstile", "TOKEN-TS")
            value = await page.eval_on_selector(
                "input[name='cf-turnstile-response']", "el => el.value"
            )
            await browser.close()
            return ok, value

    ok, value = _run(body)
    assert ok is True
    assert value == "TOKEN-TS"


def test_detect_sitekey_from_data_attribute(tmp_path):
    html = tmp_path / "inject.html"
    html.write_text(PAGE, encoding="utf-8")

    async def body():
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.goto(html.as_uri())
            key = await detect_sitekey(page, "recaptcha_v2")
            await browser.close()
            return key

    assert _run(body) == "6Le-test-key-AAAA"
