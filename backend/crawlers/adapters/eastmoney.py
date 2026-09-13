# -*- coding: utf-8 -*-
"""
东方财富适配器
=============

功能:
- 股票K线数据
- 板块行情
- 指数行情
"""
import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

import httpx

from crawlers.adapter_framework import (
    BaseAdapter, AdapterConfig, register_adapter,
)
from crawlers.base import CrawlResult

logger = logging.getLogger(__name__)


class EastMoneyConfig(AdapterConfig):
    """东方财富配置"""
    name: str = "eastmoney"
    base_url: str = "https://push2.eastmoney.com"
    kline_url: str = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
    sector_url: str = "https://push2.eastmoney.com/api/qt/clist/get"


@register_adapter("eastmoney", category="finance")
class EastMoneyAdapter(BaseAdapter):
    """东方财富数据适配器"""
    
    NAME = "eastmoney"
    DESCRIPTION = "东方财富 - 股票K线/板块行情/指数行情"
    CATEGORY = "finance"
    CONFIG_CLASS = EastMoneyConfig
    
    def __init__(self, config: EastMoneyConfig = None, **kwargs):
        super().__init__(config, **kwargs)
        self._secid_map = {
            "sh": lambda code: f"1.{code}",
            "sz": lambda code: f"0.{code}",
        }
    
    async def fetch(self, **kwargs) -> CrawlResult:
        """通用获取方法"""
        fetch_type = kwargs.get("type", "stock")
        
        if fetch_type == "stock":
            return await self.fetch_stock_kline(
                stock_code=kwargs.get("stock_code", "600519"),
                days=kwargs.get("days", 30),
                market=kwargs.get("market", "sh"),
            )
        elif fetch_type == "sector":
            return await self.fetch_sectors(
                sector_type=kwargs.get("sector_type", "industry"),
                limit=kwargs.get("limit", 20),
            )
        elif fetch_type == "index":
            return await self.fetch_index_quotes()
        else:
            return CrawlResult(
                success=False, data=[], message=f"未知类型: {fetch_type}", source=self.NAME
            )
    
    async def fetch_stock_kline(
        self, stock_code: str = "600519", days: int = 30, market: str = "sh"
    ) -> CrawlResult:
        """获取股票K线数据"""
        secid = self._secid_map.get(market, lambda c: f"1.{c}")(stock_code)
        
        url = self.config.kline_url
        params = {
            "secid": secid,
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
            "klt": "101",  # 日K
            "fqt": "1",    # 前复权
            "lmt": days,
            "end": "20500101",
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            klines = data.get("data", {}).get("klines", [])
            stock_name = data.get("data", {}).get("name", stock_code)
            
            result_data = []
            for line in klines:
                parts = line.split(",")
                if len(parts) >= 6:
                    result_data.append({
                        "date": parts[0],
                        "open": float(parts[1]),
                        "close": float(parts[2]),
                        "high": float(parts[3]),
                        "low": float(parts[4]),
                        "volume": int(parts[5]),
                        "stock_code": stock_code,
                        "stock_name": stock_name,
                        "market": market,
                    })
            
            return CrawlResult(
                success=True,
                data=result_data,
                message=f"获取 {stock_name}({stock_code}) K线成功",
                source=self.NAME,
                count=len(result_data),
            )
            
        except Exception as e:
            logger.error(f"东方财富K线获取失败: {e}")
            return CrawlResult(
                success=False, data=[], message=f"K线获取失败: {e}",
                source=self.NAME, error=str(e)
            )
    
    async def fetch_sectors(self, sector_type: str = "industry", limit: int = 20) -> CrawlResult:
        """获取板块行情"""
        # 板块类型映射
        fs_map = {
            "industry": "m:90+t:2",
            "concept": "m:90+t:3",
            "area": "m:90+t:1",
        }
        
        url = self.config.sector_url
        params = {
            "pn": 1,
            "pz": limit,
            "po": 1,
            "np": 1,
            "fltt": 2,
            "invt": 2,
            "fid": "f3",
            "fs": fs_map.get(sector_type, "m:90+t:2"),
            "fields": "f2,f3,f4,f12,f14",
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            items = data.get("data", {}).get("diff", [])
            result_data = []
            for item in items:
                result_data.append({
                    "code": item.get("f12", ""),
                    "name": item.get("f14", ""),
                    "change_pct": item.get("f3", 0),
                    "price": item.get("f2", 0),
                    "change": item.get("f4", 0),
                    "type": sector_type,
                })
            
            return CrawlResult(
                success=True,
                data=result_data,
                message=f"获取 {sector_type} 板块行情成功",
                source=self.NAME,
                count=len(result_data),
            )
            
        except Exception as e:
            return CrawlResult(
                success=False, data=[], message=f"板块获取失败: {e}",
                source=self.NAME, error=str(e)
            )
    
    async def fetch_index_quotes(self) -> CrawlResult:
        """获取主要指数行情"""
        indices = [
            {"code": "1.000001", "name": "上证指数"},
            {"code": "0.399001", "name": "深证成指"},
            {"code": "0.399006", "name": "创业板指"},
        ]
        
        result_data = []
        url = "https://push2.eastmoney.com/api/qt/stock/get"
        
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                for idx in indices:
                    params = {
                        "secid": idx["code"],
                        "fields": "f43,f44,f45,f46,f47,f48,f170",
                    }
                    response = await client.get(url, params=params)
                    if response.status_code == 200:
                        d = response.json().get("data", {})
                        result_data.append({
                            "name": idx["name"],
                            "code": idx["code"],
                            "price": d.get("f43", 0) / 100 if d.get("f43") else 0,
                            "change_pct": d.get("f170", 0) / 100 if d.get("f170") else 0,
                        })
            
            return CrawlResult(
                success=True,
                data=result_data,
                message="获取指数行情成功",
                source=self.NAME,
                count=len(result_data),
            )
            
        except Exception as e:
            return CrawlResult(
                success=False, data=[], message=f"指数获取失败: {e}",
                source=self.NAME, error=str(e)
            )
