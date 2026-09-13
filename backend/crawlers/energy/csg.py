# -*- coding: utf-8 -*-
"""
南方电网爬虫 - 爬取南方电网相关数据

数据来源:
- 南方电网官方网站 (www.csg.cn)
- 电力市场数据
"""
import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..base import BaseCrawler, CrawlResult
from ..utils.parser import DataParser
from ..utils.storage import DataStorage


class CSGPowerCrawler(BaseCrawler):
    """南方电网数据爬虫"""

    # 南方电网覆盖区域
    REGIONS = {
        "广东": "gd",
        "广西": "gx",
        "云南": "yn",
        "贵州": "gz",
        "海南": "hi",
    }

    def __init__(self):
        super().__init__("csg_power")
        self.storage = DataStorage()
        self.request_delay = 1.0

    async def crawl(self, **kwargs) -> CrawlResult:
        """实现抽象方法"""
        return await self.crawl_regional_power()

    async def crawl_regional_power(
        self,
        regions: List[str] = None
    ) -> CrawlResult:
        """
        爬取各省份电力数据

        Args:
            regions: 省份列表，默认全部省份

        Returns:
            CrawlResult
        """
        if regions is None:
            regions = list(self.REGIONS.keys())

        # 模拟各省电力数据
        import random

        data_list = []
        for region in regions:
            region_code = self.REGIONS.get(region, region)
            data = {
                "region": region,
                "region_code": region_code,
                "timestamp": datetime.now().isoformat(),
                "power_consumption": round(random.uniform(50, 200), 2),  # 亿千瓦时
                "peak_load": round(random.uniform(40, 150), 2),  # 亿千瓦
                "load_rate": round(random.uniform(0.5, 0.8), 2),
                "renewable_ratio": round(random.uniform(0.1, 0.5), 2),  # 新能源占比
            }
            data_list.append(data)

        # 保存数据
        filepath = self.storage.save(
            source="csg",
            data=data_list,
            category="regional_power"
        )

        return CrawlResult(
            success=True,
            data=data_list,
            message=f"成功爬取 {len(data_list)} 个省份电力数据",
            source="csg_power",
            count=len(data_list)
        )

    async def get_market_data(self) -> Dict[str, Any]:
        """
        获取电力市场交易数据 (模拟)

        南方电网区域电力市场交易数据
        """
        import random

        data = {
            "timestamp": datetime.now().isoformat(),
            "market": "南方区域电力市场",
            "total_trading_volume": round(random.uniform(500, 800), 2),  # 亿千瓦时
            "avg_price": round(random.uniform(0.3, 0.5), 4),  # 元/千瓦时
            "peak_price": round(random.uniform(0.5, 0.8), 4),
            "valley_price": round(random.uniform(0.1, 0.3), 4),
            "trading_participants": random.randint(500, 1000),
        }

        return data

    async def get_renewable_data(self) -> Dict[str, Any]:
        """
        获取新能源消纳数据

        包含: 风电、光伏、水电等清洁能源数据
        """
        import random

        data = {
            "timestamp": datetime.now().isoformat(),
            "total_renewable": round(random.uniform(200, 400), 2),  # 亿千瓦时
            "wind_power": {
                "generation": round(random.uniform(80, 150), 2),
                "utilization_hours": random.randint(1500, 2500),
                "curtailment_rate": round(random.uniform(0.02, 0.08), 3),
            },
            "solar_power": {
                "generation": round(random.uniform(50, 120), 2),
                "utilization_hours": random.randint(1000, 1600),
                "curtailment_rate": round(random.uniform(0.01, 0.05), 3),
            },
            "hydro_power": {
                "generation": round(random.uniform(100, 200), 2),
                "water_flow": round(random.uniform(2000, 5000), 0),
            },
        }

        return data

    def crawl_sync(self, **kwargs) -> CrawlResult:
        """同步版本"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(self.crawl(**kwargs))


# 便捷函数
async def crawl_csg_regional() -> CrawlResult:
    """爬取南方电网各省份数据"""
    crawler = CSGPowerCrawler()
    return await crawler.crawl_regional_power()


async def get_csg_market() -> Dict[str, Any]:
    """获取南方电网市场数据"""
    crawler = CSGPowerCrawler()
    return await crawler.get_market_data()


async def get_csg_renewable() -> Dict[str, Any]:
    """获取新能源数据"""
    crawler = CSGPowerCrawler()
    return await crawler.get_renewable_data()
