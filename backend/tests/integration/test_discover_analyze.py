"""
站点判别链路 · 集成测试
=======================

用 ``httpx.MockTransport`` 模拟站点响应，覆盖完整链路：

    robots.txt → sitemap → 主文档 → 结构识别 → 字段提取 → 四维判定 → 持久化

不访问真实网络，可在任意环境稳定重跑。
"""
from __future__ import annotations

import asyncio
import os

import httpx
import pytest
from sqlalchemy import delete

from api.core.database import SessionLocal
from api.models import ComplianceVerdict, SiteProfile
from discover.fetcher import SiteFetcher, parse_robots
from discover.profile import SiteProfiler, normalize_url_pattern

DEMO_DOMAIN = "demo.webinsight.test"
BASE = f"https://{DEMO_DOMAIN}"

ROBOTS = """User-agent: *
Disallow: /admin/
Crawl-delay: 1
Sitemap: https://demo.webinsight.test/sitemap.xml
"""

SITEMAP = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://demo.webinsight.test/article/1</loc></url>
</urlset>
"""

LIST_HTML = """<!DOCTYPE html>
<html lang="zh-CN"><head>
<meta charset="utf-8">
<title>演示新闻站 - 列表</title>
<meta name="description" content="用于集成测试的演示站点">
<meta name="generator" content="WordPress 6.4">
<script type="application/ld+json">
{"@type":"NewsArticle","headline":"列表页聚合","datePublished":"2026-09-01T10:00:00+08:00"}
</script>
</head><body>
<ul class="news-list">
  <li class="news-item"><a href="/article/1">头条：数据平台上线</a></li>
  <li class="news-item"><a href="/article/2">二条：采集链路打通</a></li>
  <li class="news-item"><a href="/article/3">三条：判别内核完成</a></li>
  <li class="news-item"><a href="/article/4">四条：合规判定生效</a></li>
</ul>
<a href="/news?page=2">下一页</a>
</body></html>
"""

DETAIL_HTML = """<!DOCTYPE html>
<html lang="zh-CN"><head>
<meta charset="utf-8">
<title>头条：数据平台上线</title>
<script type="application/ld+json">
{"@type":"NewsArticle","headline":"头条：数据平台上线",
 "datePublished":"2026-09-10T08:30:00+08:00",
 "author":{"name":"编辑部"}}
</script>
<meta property="og:title" content="头条：数据平台上线">
</head><body>
<article>
<h1>头条：数据平台上线</h1>
<time datetime="2026-09-10T08:30:00+08:00">2026-09-10</time>
<p>%s</p>
</article>
</body></html>
""" % ("这是一段用于验证正文抽取的示例内容，长度需要超过阈值才能被识别为正文块。" * 5)

CAPTCHA_HTML = """<!DOCTYPE html>
<html><head><title>请验证</title></head>
<body><div class="cf-turnstile" data-sitekey="x"></div>
<p>请完成人机验证后继续访问</p></body></html>
"""


def _handler(request: httpx.Request) -> httpx.Response:
    url = str(request.url)
    routes = {
        f"{BASE}/robots.txt": (ROBOTS, 200, "text/plain"),
        f"{BASE}/sitemap.xml": (SITEMAP, 200, "application/xml"),
        f"{BASE}/news": (LIST_HTML, 200, "text/html"),
        f"{BASE}/article/1": (DETAIL_HTML, 200, "text/html"),
    }
    if url in routes:
        body, status, ctype = routes[url]
        return httpx.Response(status, text=body, headers={"content-type": ctype})
    if "captcha" in url:
        return httpx.Response(200, text=CAPTCHA_HTML, headers={"content-type": "text/html"})
    return httpx.Response(404, text="<html><body>not found</body></html>",
                          headers={"content-type": "text/html"})


@pytest.fixture()
def session():
    db = SessionLocal()
    yield db
    # 清理本次测试产生的记录
    db.execute(delete(ComplianceVerdict).where(ComplianceVerdict.target_url.like(f"%{DEMO_DOMAIN}%")))
    db.execute(delete(SiteProfile).where(SiteProfile.domain == DEMO_DOMAIN))
    db.commit()
    db.close()


def _run(coro):
    return asyncio.run(coro)


# --------------------------------------------------------------------------- #
# 单元：URL 模式归一化
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://a.test/article/12345", "/article/:id"),
        ("https://a.test/news/2026/09/10/slug", "/news/:year/:num/:num/slug"),
        ("https://a.test/user/9f8e7d6c5b4a39281706f5e4d3c2b1a0", "/user/:hash"),
        ("https://a.test/", "/"),
        ("https://a.test/a/b/c", "/a/b/c"),
    ],
)
def test_normalize_url_pattern(url, expected):
    assert normalize_url_pattern(url) == expected


# --------------------------------------------------------------------------- #
# 单元：robots 路径级判定
# --------------------------------------------------------------------------- #


def test_robots_path_level_rules():
    info = parse_robots(ROBOTS)
    assert info.fetched is True
    assert info.can_fetch(f"{BASE}/news") is True
    assert info.can_fetch(f"{BASE}/admin/panel") is False
    assert info.crawl_delay == 1.0
    assert info.sitemaps == [f"{BASE}/sitemap.xml"]


# --------------------------------------------------------------------------- #
# 集成：完整判别链路
# --------------------------------------------------------------------------- #


def test_full_analyze_flow(session):
    async def _go():
        transport = httpx.MockTransport(_handler)
        client = httpx.AsyncClient(transport=transport, follow_redirects=True)
        fetcher = SiteFetcher(client=client)
        profiler = SiteProfiler(session, fetcher=fetcher)
        result = await profiler.analyze(f"{BASE}/news", force_refresh=True)
        await client.aclose()
        return result

    result = _run(_go())

    profile = result.profile
    verdict = result.verdict

    # 画像基本字段
    assert profile["domain"] == DEMO_DOMAIN
    assert profile["url_pattern"] == "/news"
    assert result.cached is False
    # robots + sitemap + 主文档 + 详情样本，至少 3 次请求
    assert result.fetch_count >= 3
    assert profile["site"]["title"].startswith("演示新闻站")
    assert profile["site"]["type"] == "news"
    assert "WordPress 6.4" in profile["site"]["tech_stack"]

    # 结构与分页
    assert profile["structure"]["has_sitemap"] is True
    assert profile["structure"]["list_item_count"] >= 4
    assert profile["structure"]["pagination"]["mode"] in ("param", "next_link")

    # 字段
    names = {f["name"] for f in profile["fields"]}
    assert "title" in names
    assert "publish_date" in names

    # 合规判定：演示站完全公开且提供 sitemap → 走官方开放通道
    assert verdict["decision"] == "proceed"
    assert verdict["dimensions"]["access"] == "A1"
    assert verdict["dimensions"]["authorization"] == "B1"

    # 策略链应包含 sitemap 能力
    assert "sitemap_walker" in profile["strategy"]["chain"]

    # 持久化与留痕
    stored = session.get(SiteProfile, profile["profile_id"])
    assert stored is not None
    assert stored.domain == DEMO_DOMAIN


def test_second_analyze_hits_cache(session):
    async def _go(force: bool):
        transport = httpx.MockTransport(_handler)
        client = httpx.AsyncClient(transport=transport, follow_redirects=True)
        fetcher = SiteFetcher(client=client)
        profiler = SiteProfiler(session, fetcher=fetcher)
        out = await profiler.analyze(f"{BASE}/news", force_refresh=force)
        await client.aclose()
        return out

    first = _run(_go(True))
    assert first.cached is False

    second = _run(_go(False))
    assert second.cached is True
    assert second.profile["profile_id"] == first.profile["profile_id"]


def test_captcha_page_is_blocked(session):
    async def _go():
        transport = httpx.MockTransport(_handler)
        client = httpx.AsyncClient(transport=transport, follow_redirects=True)
        fetcher = SiteFetcher(client=client)
        profiler = SiteProfiler(session, fetcher=fetcher)
        out = await profiler.analyze(f"{BASE}/captcha-protected", force_refresh=True)
        await client.aclose()
        return out

    result = _run(_go())
    verdict = result.verdict

    assert verdict["decision"] == "blocked"
    assert verdict["dimensions"]["access"] == "A4"
    assert len(verdict["alternatives"]) >= 3
    assert verdict["coverage_estimate"] > 0
