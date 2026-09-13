# -*- coding: utf-8 -*-
"""
爬虫模块 - 智能数据分析平台

支持多源数据采集（全部真实API）：
- 金融数据：东方财富（股票K线、板块行情）、新浪财经（实时行情、历史K线、指数）
- 新闻资讯：36kr（科技快讯）、财联社（电报）
- 电商数据：京东（模拟+API）、淘宝（搜索建议）
- 电网数据：电力行业股行情（新浪）
- 分布式采集：DistributedCrawler 并发引擎
"""

from .base import BaseCrawler, CrawlResult
from .finance.eastmoney import EastMoneyCrawler
from .finance.sina import SinaCrawler
from .news.netease import News36KRCrawler, CLSCrawler
from .ecommerce.crawler import TaobaoCrawler, JDCrawler
from .energy.sgcc import SGCCPowerCrawler
from .energy.csg import CSGPowerCrawler
from .distributed import DistributedCrawler, crawl_all_stocks, crawl_all_news

__all__ = [
    "BaseCrawler",
    "CrawlResult",
    # 分布式引擎
    "DistributedCrawler",
    "crawl_all_stocks",
    "crawl_all_news",
    # 金融
    "EastMoneyCrawler",
    "SinaCrawler",
    # 新闻
    "News36KRCrawler",
    "CLSCrawler",
    # 电商
    "TaobaoCrawler",
    "JDCrawler",
    # 能源
    "SGCCPowerCrawler",
    "CSGPowerCrawler",
]
