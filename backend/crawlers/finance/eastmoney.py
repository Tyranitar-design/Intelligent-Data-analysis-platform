# -*- coding: utf-8 -*-
"""
金融数据爬虫 - 东方财富 (真实可用)

数据源: push2his.eastmoney.com
- 股票K线 (日/周/月)
- 板块行情
- 涨跌停数据
- 龙虎榜
"""
import asyncio
import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    import httpx
except ImportError:
    httpx = None

from ..base import BaseCrawler, CrawlResult


class EastMoneyCrawler(BaseCrawler):
    """东方财富数据爬虫"""

    # K线 API
    KLINE_URL = "https://push2his.eastmoney.com/api/qt/stock/kline/get"

    # 实时行情 API
    QUOTE_URL = "https://push2.eastmoney.com/api/qt/stock/get"

    # 板块行情 API
    SECTOR_URL = "https://push2.eastmoney.com/api/qt/clist/get"

    def __init__(self):
        super().__init__("eastmoney")
        self.request_delay = 0.5

    async def crawl_stock_kline(
        self,
        stock_code: str,
        days: int = 30,
        market: str = "sh",
        klt: int = 101
    ) -> CrawlResult:
        """
        爬取股票K线数据

        Args:
            stock_code: 股票代码
            days: 历史天数
            market: sh=上证, sz=深证
            klt: 101=日K, 102=周K, 103=月K
        """
        self.logger.info(f"爬取 {market}{stock_code} K线 {days}天")

        secid = f"1.{stock_code}" if market == "sh" else f"0.{stock_code}"
        params = {
            "secid": secid,
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
            "klt": klt,
            "fqt": 1,
            "end": 20500101,
            "lmt": days,
        }

        html = await self.fetch(self.KLINE_URL, params=params)
        if not html:
            return CrawlResult(success=False, data=[], message=f"请求失败 {stock_code}", source="eastmoney")

        data = self._parse_kline(html, stock_code)
        if not data:
            return CrawlResult(success=False, data=[], message=f"解析失败 {stock_code}", source="eastmoney")

        self.logger.info(f"获取 {len(data)} 条K线")
        return CrawlResult(
            success=True, data=data,
            message=f"成功获取 {stock_code} {len(data)} 条K线",
            source="eastmoney", count=len(data)
        )

    async def crawl_stock_batch(
        self,
        stocks: List[Dict],
        days: int = 30
    ) -> CrawlResult:
        """
        批量爬取多只股票

        Args:
            stocks: [{"code": "600519", "name": "贵州茅台", "market": "sh"}, ...]
            days: 历史天数
        """
        all_data = []
        for stock in stocks:
            code = stock.get("code", "")
            name = stock.get("name", code)
            market = stock.get("market", "sh" if code.startswith("6") else "sz")

            result = await self.crawl_stock_kline(code, days, market)
            if result.success:
                for item in result.data:
                    item["name"] = name
                all_data.extend(result.data)
            await asyncio.sleep(self.request_delay)

        return CrawlResult(
            success=True, data=all_data,
            message=f"批量爬取 {len(stocks)} 只股票，共 {len(all_data)} 条K线",
            source="eastmoney", count=len(all_data)
        )

    async def crawl_sectors(
        self,
        sector_type: str = "industry",
        limit: int = 20
    ) -> CrawlResult:
        """
        爬取板块行情

        Args:
            sector_type: industry=行业板块, concept=概念板块, area=地区板块
            limit: 返回数量
        """
        self.logger.info(f"爬取板块行情: {sector_type}")

        fs_map = {
            "industry": "m:90+t:2",
            "concept": "m:90+t:3",
            "area": "m:90+t:1",
        }

        params = {
            "pn": 1,
            "pz": limit,
            "po": 1,
            "np": 1,
            "fltt": 2,
            "invt": 2,
            "fid": "f3",
            "fs": fs_map.get(sector_type, fs_map["industry"]),
            "fields": "f2,f3,f4,f8,f12,f14,f104,f105,f128,f136,f140,f141",
        }

        html = await self.fetch(self.SECTOR_URL, params=params)
        if not html:
            return CrawlResult(success=False, data=[], message="板块请求失败", source="eastmoney_sector")

        try:
            data = json.loads(html.strip())
            diff = data.get("data", {}).get("diff", [])
            sectors = []

            for item in diff:
                sectors.append({
                    "code": item.get("f12", ""),
                    "name": item.get("f14", ""),
                    "price": item.get("f2", 0),
                    "change_pct": item.get("f3", 0),
                    "change_amount": item.get("f4", 0),
                    "turnover_rate": item.get("f8", 0),
                    "leader_stock": item.get("f140", ""),
                    "stock_count": item.get("f136", 0),
                    "rise_count": item.get("f104", 0),
                    "fall_count": item.get("f105", 0),
                })

            return CrawlResult(
                success=True, data=sectors,
                message=f"获取 {sector_type} 板块 {len(sectors)} 个",
                source="eastmoney_sector", count=len(sectors)
            )
        except Exception as e:
            return CrawlResult(success=False, data=[], message=f"板块解析失败: {e}", source="eastmoney_sector")

    async def crawl_stock_list(self, market: str = "sh") -> CrawlResult:
        """
        获取股票列表

        Args:
            market: sh=沪市, sz=深市
        """
        fs = f"m:1+t:2,m:0+t:6,m:0+t:80,m:1+t:23" if market == "sh" else f"m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23"
        params = {
            "pn": 1, "pz": 5000, "po": 1, "np": 1,
            "fltt": 2, "invt": 2, "fid": "f3",
            "fs": fs,
            "fields": "f2,f3,f4,f12,f14",
        }

        html = await self.fetch(self.SECTOR_URL, params=params)
        if not html:
            return CrawlResult(success=False, data=[], message="股票列表请求失败", source="eastmoney_list")

        try:
            data = json.loads(html.strip())
            diff = data.get("data", {}).get("diff", [])
            stocks = [{"code": item.get("f12",""), "name": item.get("f14",""), "price": item.get("f2",0)} for item in diff]
            return CrawlResult(success=True, data=stocks, message=f"获取 {len(stocks)} 只股票", source="eastmoney_list", count=len(stocks))
        except:
            return CrawlResult(success=False, data=[], message="股票列表解析失败", source="eastmoney_list")

    def _parse_kline(self, raw: str, stock_code: str) -> List[Dict]:
        """解析K线数据"""
        try:
            data = json.loads(raw.strip())
            klines = data.get("data", {}).get("klines", [])
            if not klines:
                return []

            records = []
            for kline in klines:
                parts = kline.split(",")
                if len(parts) >= 7:
                    records.append({
                        "symbol": stock_code,
                        "date": parts[0],
                        "open": float(parts[1]),
                        "close": float(parts[2]),
                        "high": float(parts[3]),
                        "low": float(parts[4]),
                        "volume": int(parts[5]),
                        "amount": float(parts[6]),
                        "amplitude": float(parts[7]) if len(parts) > 7 else 0,
                        "change_pct": float(parts[8]) if len(parts) > 8 else 0,
                        "change_amount": float(parts[9]) if len(parts) > 9 else 0,
                        "turnover_rate": float(parts[10]) if len(parts) > 10 else 0,
                    })
            return records
        except Exception:
            return []

    async def crawl(self, **kwargs) -> CrawlResult:
        """实现抽象方法"""
        return await self.crawl_stock_kline(
            kwargs.get("stock_code", "600519"),
            kwargs.get("days", 30),
            kwargs.get("market", "sh")
        )

    def crawl_sync(self, stock_code: str, days: int = 30, market: str = "sh") -> CrawlResult:
        """同步版本"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(self.crawl_stock_kline(stock_code, days, market))
