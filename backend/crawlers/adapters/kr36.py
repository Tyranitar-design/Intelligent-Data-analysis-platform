# -*- coding: utf-8 -*-
"""
36氪新闻适配器
=============

功能:
- 科技快讯
- 热门文章
"""
import logging
from typing import Any, Dict

import httpx

from crawlers.adapter_framework import BaseAdapter, AdapterConfig, register_adapter
from crawlers.base import CrawlResult

logger = logging.getLogger(__name__)


class Kr36Config(AdapterConfig):
    name: str = "kr36"
    base_url: str = "https://36kr.com/api"


@register_adapter("kr36", category="news")
class Kr36Adapter(BaseAdapter):
    """36氪新闻适配器"""
    
    NAME = "kr36"
    DESCRIPTION = "36氪 - 科技快讯/热门文章"
    CATEGORY = "news"
    CONFIG_CLASS = Kr36Config
    
    async def fetch(self, **kwargs) -> CrawlResult:
        """获取科技快讯"""
        per_page = kwargs.get("per_page", 30)
        return await self.fetch_flash(per_page)
    
    async def fetch_flash(self, per_page: int = 30) -> CrawlResult:
        """获取快讯"""
        url = "https://gateway.36kr.com/api/mis/nav/home/nav/rank/hot"
        params = {"pageSize": per_page}
        
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.post(url, json=params)
                response.raise_for_status()
                data = response.json()
            
            items = data.get("data", {}).get("hotRankList", [])
            result_data = []
            for item in items:
                widget = item.get("widgetContent", {})
                result_data.append({
                    "title": widget.get("title", ""),
                    "summary": widget.get("summary", ""),
                    "published_at": widget.get("publishedAt", ""),
                    "author": widget.get("authorName", ""),
                    "id": widget.get("id", ""),
                    "source": "36kr",
                })
            
            return CrawlResult(
                success=True,
                data=result_data,
                message=f"获取36氪快讯成功",
                source=self.NAME,
                count=len(result_data),
            )
            
        except Exception as e:
            return CrawlResult(
                success=False, data=[], message=f"36氪获取失败: {e}",
                source=self.NAME, error=str(e)
            )
