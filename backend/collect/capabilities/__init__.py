"""
采集能力层
==========

每个能力实现 :class:`collect.registry.Capability` 协议：

- ``score(profile, request)``     适配度评分（0 表示不适用）
- ``execute(profile, request, ctx)`` 执行并返回 :class:`CollectResult`
- ``cost_estimate(request)``      成本预估，供调度决策

能力清单与分层：

    L1 通用
      feed_reader          RSS / Atom（最高优先，官方结构化通道）
      sitemap_walker       Sitemap 遍历
      structured_extractor 列表 → 详情 → 字段提取（主力）
      http_fetcher         单页兜底
    L2 策略
      browser_renderer     公开页面渲染（运行时缺失时自动降级）
"""

from collect.capabilities._common import PageFetcher, PageResult
from collect.capabilities.browser_renderer import BrowserRenderer, playwright_available
from collect.capabilities.feed_reader import FeedReader, parse_feed
from collect.capabilities.http_fetcher import HttpFetcher
from collect.capabilities.sitemap_walker import SitemapWalker, parse_sitemap
from collect.capabilities.structured_extractor import StructuredExtractor

__all__ = [
    "PageFetcher",
    "PageResult",
    "BrowserRenderer",
    "FeedReader",
    "HttpFetcher",
    "SitemapWalker",
    "StructuredExtractor",
    "parse_feed",
    "parse_sitemap",
    "playwright_available",
]
