# -*- coding: utf-8 -*-
"""
免费公开 API 适配器
=================

数据源: public-apis (https://github.com/public-apis/public-apis)
所有接口均为免费、无需认证的公开 API

覆盖:
- 天气数据 (OpenWeatherMap 免费)
- 汇率数据 (ExchangeRate API 免费)
- 新闻数据 (GNews 免费)
- 科研数据 (Wikipedia API)
- 随机数据 (各种免费 API)
"""
import logging
from typing import Any, Dict

import httpx

from crawlers.adapter_framework import BaseAdapter, AdapterConfig, register_adapter
from crawlers.base import CrawlResult

logger = logging.getLogger(__name__)


class PublicAPIConfig(AdapterConfig):
    """公开 API 配置"""
    name: str = "public_api"
    base_url: str = ""  # 不同 API 有不同 base_url
    timeout: int = 15


# ==================== 天气 API ====================

@register_adapter("openweather", category="weather")
class OpenWeatherAdapter(BaseAdapter):
    """OpenWeatherMap 免费天气 API"""
    
    NAME = "openweather"
    DESCRIPTION = "OpenWeatherMap - 全球天气数据（免费版）"
    CATEGORY = "weather"
    CONFIG_CLASS = PublicAPIConfig
    
    async def fetch(self, **kwargs) -> CrawlResult:
        """获取天气数据"""
        city = kwargs.get("city", "Beijing")
        api_key = kwargs.get("api_key", "")
        
        if not api_key:
            # 尝试使用免费端点
            return await self._fetch_free_weather(city)
        
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {"q": city, "appid": api_key, "units": "metric", "lang": "zh_cn"}
        
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            return CrawlResult(
                success=True,
                data=[{
                    "city": data.get("name"),
                    "temp": data.get("main", {}).get("temp"),
                    "humidity": data.get("main", {}).get("humidity"),
                    "description": data.get("weather", [{}])[0].get("description", ""),
                    "wind_speed": data.get("wind", {}).get("speed"),
                    "source": "openweathermap",
                }],
                message=f"天气获取成功: {city}",
                source=self.NAME,
            )
        except Exception as e:
            return CrawlResult(
                success=False, data=[],
                message=f"天气获取失败: {e}",
                source=self.NAME, error=str(e),
            )
    
    async def _fetch_free_weather(self, city: str) -> CrawlResult:
        """使用 wttr.in 免费天气（无需 API Key）"""
        url = f"https://wttr.in/{city}"
        params = {"format": "j1"}
        
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            current = data.get("current_condition", [{}])[0]
            return CrawlResult(
                success=True,
                data=[{
                    "city": city,
                    "temp_C": current.get("temp_C"),
                    "humidity": current.get("humidity"),
                    "description": current.get("weatherDesc", [{}])[0].get("value", ""),
                    "wind_speed_kmph": current.get("windspeedKmph"),
                    "feels_like_C": current.get("FeelsLikeC"),
                    "source": "wttr.in",
                }],
                message=f"天气获取成功: {city} (wttr.in)",
                source=self.NAME,
            )
        except Exception as e:
            return CrawlResult(
                success=False, data=[],
                message=f"天气获取失败: {e}",
                source=self.NAME, error=str(e),
            )


# ==================== 汇率 API ====================

@register_adapter("exchangerate", category="finance")
class ExchangeRateAdapter(BaseAdapter):
    """汇率数据 API（免费）"""
    
    NAME = "exchangerate"
    DESCRIPTION = "ExchangeRate - 实时汇率数据（免费）"
    CATEGORY = "finance"
    CONFIG_CLASS = PublicAPIConfig
    
    async def fetch(self, **kwargs) -> CrawlResult:
        """获取汇率数据"""
        base = kwargs.get("base", "USD")
        url = f"https://api.exchangerate-api.com/v4/latest/{base}"
        
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
            
            rates = data.get("rates", {})
            # 只返回主要货币
            major_currencies = ["USD", "EUR", "GBP", "JPY", "CNY", "KRW", "HKD", "SGD", "AUD", "CAD"]
            result_data = [{
                "base": base,
                "date": data.get("date"),
                "rates": {k: v for k, v in rates.items() if k in major_currencies},
            }]
            
            return CrawlResult(
                success=True,
                data=result_data,
                message=f"汇率获取成功 (base={base})",
                source=self.NAME,
            )
        except Exception as e:
            return CrawlResult(
                success=False, data=[],
                message=f"汇率获取失败: {e}",
                source=self.NAME, error=str(e),
            )


# ==================== Wikipedia API ====================

@register_adapter("wikipedia", category="research")
class WikipediaAdapter(BaseAdapter):
    """Wikipedia 搜索 API（免费）"""
    
    NAME = "wikipedia"
    DESCRIPTION = "Wikipedia - 百科搜索/摘要（免费）"
    CATEGORY = "research"
    CONFIG_CLASS = PublicAPIConfig
    
    async def fetch(self, **kwargs) -> CrawlResult:
        """搜索 Wikipedia"""
        keyword = kwargs.get("keyword", "")
        language = kwargs.get("language", "zh")  # zh/en
        limit = kwargs.get("limit", 10)
        
        url = f"https://{language}.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "list": "search",
            "srsearch": keyword,
            "srlimit": limit,
            "format": "json",
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            search_results = data.get("query", {}).get("search", [])
            result_data = [{
                "title": item.get("title"),
                "snippet": item.get("snippet", "").replace("<span class=\"searchmatch\">", "").replace("</span>", ""),
                "page_id": item.get("pageid"),
                "url": f"https://{language}.wikipedia.org/wiki/{item.get('title', '').replace(' ', '_')}",
            } for item in search_results]
            
            return CrawlResult(
                success=True,
                data=result_data,
                message=f"Wikipedia 搜索 '{keyword}' 成功",
                source=self.NAME,
                count=len(result_data),
            )
        except Exception as e:
            return CrawlResult(
                success=False, data=[],
                message=f"Wikipedia 搜索失败: {e}",
                source=self.NAME, error=str(e),
            )
