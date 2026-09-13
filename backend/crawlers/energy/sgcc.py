# -*- coding: utf-8 -*-
"""
国家电网爬虫 - 爬取国家电网相关数据

数据来源:
- 电网运行数据 (www.sgcc.com.cn)
- 电力市场数据
- 新能源数据
"""
import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from ..base import BaseCrawler, CrawlResult
from ..utils.parser import DataParser
from ..utils.storage import DataStorage


class SGCCPowerCrawler(BaseCrawler):
    """国家电网数据爬虫"""

    # 国家电网开放数据平台 (如果有)
    # API_BASE = "https://data.sgcc.com.cn/api"

    # 备用数据源: 新浪财经电力板块
    POWER_STOCK_API = "https://hq.sinajs.cn/list={codes}"

    def __init__(self):
        super().__init__("sgcc_power")
        self.storage = DataStorage()
        self.request_delay = 1.0

        # 电力行业股票代码
        self.power_stocks = {
            "sh600900": "长江电力",
            "sh600795": "国电电力",
            "sh600900": "中国核电",
            "sh600905": "三峡能源",
            "sh600026": "华能国际",
            "sh600011": "华能电力",
            "sh600900": "大唐发电",
            "sh600795": "国电电力",
        }

    async def crawl(self, **kwargs) -> CrawlResult:
        """实现抽象方法，默认爬取电力板块数据"""
        return await self.crawl_power_sector()

    async def crawl_power_sector(
        self,
        stock_codes: List[str] = None
    ) -> CrawlResult:
        """
        爬取电力行业股票数据

        Args:
            stock_codes: 股票代码列表，默认使用预设的电力板块

        Returns:
            CrawlResult
        """
        if stock_codes is None:
            stock_codes = list(self.power_stocks.keys())

        codes_str = ",".join(stock_codes)
        url = f"https://hq.sinajs.cn/list={codes_str}"

        headers = {
            "Referer": "https://finance.sina.com.cn/",
            "User-Agent": self.ua.random,
        }

        html = await self.fetch(url, headers=headers)

        if not html:
            return CrawlResult(
                success=False,
                data=[],
                message="请求失败",
                source="sgcc_power"
            )

        # 解析数据
        data_list = []
        for line in html.strip().split("\n"):
            if line.strip():
                parsed = DataParser.parse_sina_data(line)
                if parsed:
                    # 添加股票名称
                    code = line.split('="')[0].split("hq_sinajs_cn_str_")[-1]
                    parsed["stock_code"] = code
                    parsed["stock_name"] = self.power_stocks.get(code, code)
                    data_list.append(parsed)

        # 保存数据
        filepath = self.storage.save(
            source="sgcc",
            data=data_list,
            category="power_sector"
        )

        return CrawlResult(
            success=True,
            data=data_list,
            message=f"成功爬取 {len(data_list)} 只电力股票数据",
            source="sgcc_power",
            count=len(data_list)
        )

    async def get_power_generation_data(self) -> Dict[str, Any]:
        """
        获取电力发电数据 (模拟数据)

        注意: 真实的电网发电数据需要从官方API获取
        这里提供模拟数据用于演示
        """
        import random

        # 模拟电力数据
        data = {
            "timestamp": datetime.now().isoformat(),
            "total_generation": round(random.uniform(1500, 1800), 2),  # 亿千瓦时
            "hydropower": round(random.uniform(200, 400), 2),
            "thermal_power": round(random.uniform(800, 1000), 2),
            "nuclear_power": round(random.uniform(30, 50), 2),
            "wind_power": round(random.uniform(100, 200), 2),
            "solar_power": round(random.uniform(50, 150), 2),
            "peak_load": round(random.uniform(1200, 1500), 2),  # 亿千瓦
            "load_rate": round(random.uniform(0.6, 0.85), 2),
        }

        return data

    async def get_grid_operation_data(self) -> Dict[str, Any]:
        """
        获取电网运行数据 (模拟数据)

        包含: 输电量、线损率、供电可靠性等指标
        """
        import random

        data = {
            "timestamp": datetime.now().isoformat(),
            "transmission_volume": round(random.uniform(300, 500), 2),  # 亿千瓦时
            "line_loss_rate": round(random.uniform(0.04, 0.08), 3),  # 线损率 %
            "power_supply_reliability": round(random.uniform(99.9, 99.99), 2),  # 供电可靠率 %
            "avg_load_rate": round(random.uniform(0.5, 0.7), 2),  # 平均负荷率
            "max_transmission": round(random.uniform(400, 600), 2),  # 最大输送功率 GW
            "grid_frequency": round(random.uniform(49.95, 50.05), 3),  # 频率 Hz
        }

        return data

    def crawl_sync(self, **kwargs) -> CrawlResult:
        """同步版本的爬取方法"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(self.crawl(**kwargs))


# 便捷函数
async def crawl_power_stocks() -> CrawlResult:
    """爬取电力板块股票"""
    crawler = SGCCPowerCrawler()
    return await crawler.crawl_power_sector()


async def get_power_generation() -> Dict[str, Any]:
    """获取发电数据"""
    crawler = SGCCPowerCrawler()
    return await crawler.get_power_generation_data()


async def get_grid_operation() -> Dict[str, Any]:
    """获取电网运行数据"""
    crawler = SGCCPowerCrawler()
    return await crawler.get_grid_operation_data()
