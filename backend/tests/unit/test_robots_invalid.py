# -*- coding: utf-8 -*-
"""RobotsChecker 伪装内容检测 · 单元测试（mock HTTP）

背景：京东将 robots.txt 请求伪装重定向到首页 HTML——静默"默认允许"会掩盖风险；
修复后应标记 source="invalid" + 强警告（保守默认仍允许，但要求人工确认）。
"""
from __future__ import annotations

import asyncio

import httpx

from crawlers.robots_checker import RobotsChecker


class FakeHtmlResponse:
    status_code = 200
    text = "<!DOCTYPE html><html><head><title>Home</title></head><body>x</body></html>"


class FakeTxtResponse:
    status_code = 200
    text = "User-agent: *\nDisallow: /private/\n"


class Fake404:
    status_code = 404
    text = "not found"


def test_html_masquerade_marks_invalid(monkeypatch):
    async def fake_get(self, url, **kwargs):
        return FakeHtmlResponse()

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    checker = RobotsChecker()
    report = asyncio.run(checker.check("https://www.jd.com/"))
    assert report.source == "invalid", report.to_dict()
    assert report.allowed is True  # 保守默认
    assert any("伪装" in w or "非文本" in w for w in report.warnings), report.warnings


def test_valid_robots_still_works(monkeypatch):
    async def fake_get(self, url, **kwargs):
        return FakeTxtResponse()

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    checker = RobotsChecker()
    report = asyncio.run(checker.check("https://example.com/private/data"))
    assert report.source == "robots.txt"
    assert report.allowed is False


def test_missing_robots_stays_default(monkeypatch):
    async def fake_get(self, url, **kwargs):
        return Fake404()

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    checker = RobotsChecker()
    report = asyncio.run(checker.check("https://example.com/"))
    assert report.source == "default"
    assert report.allowed is True
