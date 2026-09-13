# -*- coding: utf-8 -*-
"""
爬虫服务层 - 统一调用接口 + 分布式采集
"""
import asyncio
from typing import Any, Dict, List, Optional

from .finance.eastmoney import EastMoneyCrawler
from .finance.sina import SinaCrawler
from .news.netease import News36KRCrawler, CLSCrawler
from .ecommerce.crawler import TaobaoCrawler, JDCrawler
from .energy.sgcc import SGCCPowerCrawler
from .energy.csg import CSGPowerCrawler
from .distributed import DistributedCrawler
from .base import CrawlResult


class CrawlService:
    """爬虫服务 - 统一管理所有数据源"""

    def __init__(self):
        self.eastmoney = EastMoneyCrawler()
        self.sina = SinaCrawler()
        self.news_36kr = News36KRCrawler()
        self.news_cls = CLSCrawler()
        self.jd = JDCrawler()
        self.taobao = TaobaoCrawler()
        self.sgcc = SGCCPowerCrawler()
        self.csg = CSGPowerCrawler()

    # ==================== 金融数据 ====================

    async def crawl_stock(self, stock_code: str, days: int = 30, market: str = "sh") -> CrawlResult:
        """爬取单只股票K线"""
        return await self.eastmoney.crawl_stock_kline(stock_code, days, market)

    async def crawl_stocks_batch(self, stocks: List[Dict], days: int = 30) -> CrawlResult:
        """批量爬取多只股票"""
        return await self.eastmoney.crawl_stock_batch(stocks, days)

    async def crawl_index_quotes(self) -> CrawlResult:
        """获取主要指数实时行情"""
        return await self.sina.crawl_index_quotes()

    async def crawl_stock_history(self, symbol: str, days: int = 30) -> CrawlResult:
        """获取股票历史K线 (新浪)"""
        return await self.sina.crawl_stock_history(symbol, days)

    async def crawl_sectors(self, sector_type: str = "industry", limit: int = 20) -> CrawlResult:
        """获取板块行情"""
        return await self.eastmoney.crawl_sectors(sector_type, limit)

    async def crawl_power_stocks(self) -> CrawlResult:
        """获取电力行业股票行情"""
        return await self.sina.crawl_power_stocks()

    # ==================== 新闻数据 ====================

    async def crawl_tech_news(self, per_page: int = 30) -> CrawlResult:
        """爬取36kr科技快讯"""
        return await self.news_36kr.crawl_newsflash(per_page)

    async def crawl_finance_news(self, page: int = 1, per_page: int = 30) -> CrawlResult:
        """爬取财联社电报"""
        return await self.news_cls.crawl_telegraph(page, per_page)

    async def crawl_all_news(self, pages: int = 3) -> CrawlResult:
        """爬取所有新闻源"""
        all_data = []
        for p in range(1, pages + 1):
            r1 = await self.news_36kr.crawl_newsflash(30, p)
            if r1.success:
                all_data.extend(r1.data)
            r2 = await self.news_cls.crawl_telegraph(p, 30)
            if r2.success:
                all_data.extend(r2.data)
        return CrawlResult(
            success=True, data=all_data,
            message=f"爬取 {pages} 页共 {len(all_data)} 条新闻",
            source="multi_news", count=len(all_data)
        )

    # ==================== 电商数据 ====================

    async def crawl_jd(self, keywords: List[str] = None, pages: int = 1) -> CrawlResult:
        """爬取京东"""
        return await self.jd.crawl(keywords, pages)

    async def crawl_taobao(self, keywords: List[str] = None, pages: int = 1) -> CrawlResult:
        """爬取淘宝搜索建议"""
        return await self.taobao.crawl(keywords, pages)

    # ==================== 能源数据 ====================

    async def crawl_power_data(self) -> CrawlResult:
        """获取电力行业数据"""
        return await self.sina.crawl_power_stocks()

    # ==================== 分布式批量采集 ====================

    async def distributed_crawl(self, tasks: List[Dict], concurrency: int = 5) -> Dict:
        """
        分布式批量采集

        Args:
            tasks: 任务列表，如 [
                {"source": "eastmoney", "func": "crawl_stock_kline", "args": ("600519", 30, "sh")},
                {"source": "36kr", "func": "crawl_newsflash", "kwargs": {"per_page": 30}},
            ]
            concurrency: 并发数
        """
        engine = DistributedCrawler(max_concurrency=concurrency)
        engine.register_crawler("eastmoney", self.eastmoney)
        engine.register_crawler("sina", self.sina)
        engine.register_crawler("36kr", self.news_36kr)
        engine.register_crawler("cls", self.news_cls)

        for task in tasks:
            engine.add_task(
                source=task["source"],
                func=task["func"],
                args=tuple(task.get("args", [])),
                kwargs=task.get("kwargs", {}),
            )

        stats = await engine.run(task_count=len(tasks))
        return stats.to_dict()

    # ==================== 历史记录 ====================

    def get_history(self, source: str = None, limit: int = 10) -> List[Dict]:
        """获取爬取历史"""
        from .utils.storage import DataStorage
        storage = DataStorage()
        return storage.get_history(source, limit)


# 全局实例
crawl_service = CrawlService()
