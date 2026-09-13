# -*- coding: utf-8 -*-
"""
财联社新闻适配器
===============

功能:
- 财经电报
- 市场快讯
"""
import logging
from typing import Any, Dict

import httpx

from crawlers.adapter_framework import BaseAdapter, AdapterConfig, register_adapter
from crawlers.base import CrawlResult

logger = logging.getLogger(__name__)


class ClsConfig(AdapterConfig):
    name: str = "cls"
    base_url: str = "https://www.cls.cn/api"


@register_adapter("cls", category="news")
class ClsAdapter(BaseAdapter):
    """财联社新闻适配器"""
    
    NAME = "cls"
    DESCRIPTION = "财联社 - 财经电报/市场快讯"
    CATEGORY = "news"
    CONFIG_CLASS = ClsConfig
    
    async def fetch(self, **kwargs) -> CrawlResult:
        """获取财经电报"""
        page = kwargs.get("page", 1)
        per_page = kwargs.get("per_page", 30)
        return await self.fetch_telegraph(page, per_page)
    
    async def fetch_telegraph(self, page: int = 1, per_page: int = 30) -> CrawlResult:
        """获取电报"""
        url = "https://www.cls.cn/api/sw"
        params = {
            "app": "CailianpressWeb",
            "os": "web",
            "sv": "8.4.6",
            "rn": per_page,
            "pg": page,
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            items = data.get("data", {}).get("roll_data", [])
            result_data = []
            for item in items:
                result_data.append({
                    "title": item.get("title", "") or item.get("brief", ""),
                    "content": item.get("content", ""),
                    "published_at": item.get("ctime", ""),
                    "id": item.get("id", ""),
                    "source": "cls",
                })
            
            return CrawlResult(
                success=True,
                data=result_data,
                message=f"获取财联社电报成功",
                source=self.NAME,
                count=len(result_data),
            )
            
        except Exception as e:
            return CrawlResult(
                success=False, data=[], message=f"财联社获取失败: {e}",
                source=self.NAME, error=str(e)
            )
