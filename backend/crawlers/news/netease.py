# -*- coding: utf-8 -*-
"""
新闻爬虫 - 36kr + 财联社 (真实可用API)

数据源:
- 36kr.com/api/newsflash - 科技快讯 (JSON API, 无需登录)
- cls.cn/api - 财联社电报
"""
import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..base import BaseCrawler, CrawlResult


class News36KRCrawler(BaseCrawler):
    """36kr 科技新闻爬虫"""

    API_URL = "https://36kr.com/api/newsflash"

    def __init__(self):
        super().__init__("36kr")
        self.request_delay = 1.0

    async def crawl(self, **kwargs) -> CrawlResult:
        """默认爬取最新科技快讯"""
        return await self.crawl_newsflash()

    async def crawl_newsflash(self, per_page: int = 30, page: int = 1) -> CrawlResult:
        """
        爬取36kr快讯

        Args:
            per_page: 每页数量 (max 50)
            page: 页码
        """
        self.logger.info(f"爬取36kr快讯: page={page}, per_page={per_page}")

        params = {"per_page": per_page, "page": page}
        html = await self.fetch(self.API_URL, params=params)

        if not html:
            return CrawlResult(success=False, data=[], message="请求失败", source="36kr")

        try:
            data = json.loads(html.strip())
            items = data.get("data", {}).get("items", [])

            news_list = []
            for item in items:
                news_list.append({
                    "title": item.get("title", ""),
                    "description": item.get("description", ""),
                    "url": f"https://36kr.com/newsflashes/{item.get('id', '')}",
                    "source": "36kr",
                    "category": "科技",
                    "publish_time": item.get("published_at", ""),
                    "created_at": item.get("created_at", ""),
                    "author": item.get("user", {}).get("nickname", ""),
                    "tags": item.get("extraction_tags", []),
                    "counters": item.get("counters", {}),
                })

            return CrawlResult(
                success=True, data=news_list,
                message=f"获取36kr快讯 {len(news_list)} 条",
                source="36kr", count=len(news_list)
            )
        except Exception as e:
            return CrawlResult(success=False, data=[], message=f"解析失败: {e}", source="36kr")

    async def crawl_multi_pages(self, pages: int = 3, per_page: int = 30) -> CrawlResult:
        """爬取多页快讯"""
        all_news = []
        for p in range(1, pages + 1):
            result = await self.crawl_newsflash(per_page, p)
            if result.success:
                all_news.extend(result.data)
            await asyncio.sleep(self.request_delay)

        return CrawlResult(
            success=True, data=all_news,
            message=f"获取36kr快讯 {pages} 页共 {len(all_news)} 条",
            source="36kr", count=len(all_news)
        )


class CLSCrawler(BaseCrawler):
    """财联社电报爬虫"""

    SUBJECT_API = "https://www.cls.cn/api/subject/recommend"

    def __init__(self):
        super().__init__("cls")
        self.request_delay = 1.5

    async def crawl(self, **kwargs) -> CrawlResult:
        """默认爬取推荐专题"""
        return await self.crawl_subjects()

    async def crawl_subjects(self, per_page: int = 30) -> CrawlResult:
        """爬取财联社推荐专题"""
        self.logger.info("爬取财联社电报")

        params = {
            "app": "CailianpressWeb",
            "os": "web",
            "sv": "8.4.6",
        }

        html = await self.fetch(self.SUBJECT_API, params=params)
        if not html:
            return CrawlResult(success=False, data=[], message="请求失败", source="cls")

        try:
            data = json.loads(html.strip())
            # 适配多种可能的返回结构
            items = data.get("data", {}).get("subject_list", [])
            if not items:
                items = data.get("data", {}).get("list", [])
            if not items:
                items = data.get("data", [])

            news_list = []
            for item in items:
                if isinstance(item, dict):
                    news_list.append({
                        "title": item.get("title", item.get("subject_name", "")),
                        "description": item.get("brief", item.get("desc", "")),
                        "url": item.get("url", item.get("share_url", f"https://www.cls.cn/subject/{item.get('id','')}")),
                        "source": "财联社",
                        "category": "财经",
                        "publish_time": item.get("ctime", item.get("updated_at", "")),
                        "image": item.get("image", ""),
                    })

            return CrawlResult(
                success=True, data=news_list,
                message=f"获取财联社 {len(news_list)} 条",
                source="cls", count=len(news_list)
            )
        except Exception as e:
            return CrawlResult(success=False, data=[], message=f"解析失败: {e}", source="cls")

    async def crawl_telegraph(self, page: int = 1, per_page: int = 30) -> CrawlResult:
        """爬取财联社电报快讯"""
        self.logger.info(f"爬取财联社电报: page={page}")

        # 尝试多个 API 端点
        urls_to_try = [
            "https://www.cls.cn/api/telegraph/list",
            "https://www.cls.cn/api/subject/recommend",
        ]

        params_base = {
            "app": "CailianpressWeb",
            "os": "web",
            "sv": "8.4.6",
        }

        for url in urls_to_try:
            params = {**params_base}
            if "telegraph" in url:
                params["page"] = page
                params["rn"] = per_page

            html = await self.fetch(url, params=params)
            if not html:
                continue

            try:
                data = json.loads(html.strip())
                items = data.get("data", {})

                # 适配多种返回结构
                if isinstance(items, dict):
                    items = items.get("roll_data", items.get("items", items.get("subject_list", [])))
                if not items:
                    items = data.get("data", [])

                if not items:
                    continue

                news_list = []
                import re
                for item in items:
                    if isinstance(item, dict):
                        content = item.get("content", item.get("title", item.get("summary", item.get("brief", ""))))
                        content = re.sub(r'<[^>]+>', '', str(content))
                        news_list.append({
                            "title": item.get("title", content[:50] if content else ""),
                            "content": content,
                            "url": item.get("share_url", item.get("url", "")),
                            "source": "财联社",
                            "category": item.get("subject_name", "财经"),
                            "publish_time": item.get("ctime", item.get("created_at", "")),
                            "important": item.get("level", 0),
                        })

                if news_list:
                    return CrawlResult(
                        success=True, data=news_list,
                        message=f"获取财联社 {len(news_list)} 条",
                        source="cls_telegraph", count=len(news_list)
                    )
            except Exception:
                continue

        return CrawlResult(success=False, data=[], message="财联社API全部失败", source="cls")
