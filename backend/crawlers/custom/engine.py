# -*- coding: utf-8 -*-
"""
自定义采集引擎
=============
"""
import asyncio
import logging
from datetime import datetime
from typing import Any, Dict

import httpx

from crawlers.base import CrawlResult
from crawlers.robots_checker import RobotsChecker
from .schema import CrawlConfigSchema, SourceType

logger = logging.getLogger(__name__)


class CustomCrawlEngine:
    """用户自定义采集引擎"""
    
    def __init__(self):
        self.robots_checker = RobotsChecker()
    
    async def execute(self, config: CrawlConfigSchema) -> CrawlResult:
        """执行自定义采集任务"""
        start_time = datetime.now()
        logger.info(f"开始自定义采集: {config.name} (类型: {config.source_type})")
        
        try:
            if config.source_type == SourceType.WEB:
                result = await self._crawl_web(config)
            elif config.source_type == SourceType.API:
                result = await self._crawl_api(config)
            elif config.source_type == SourceType.LOCAL:
                result = await self._crawl_local(config)
            else:
                return CrawlResult(
                    success=False, data=[],
                    message=f"不支持的采集类型: {config.source_type}",
                    source=config.name
                )
            
            result.elapsed = (datetime.now() - start_time).total_seconds()
            return result
            
        except Exception as e:
            return CrawlResult(
                success=False, data=[],
                message=f"采集执行失败: {e}",
                source=config.name, error=str(e),
                elapsed=(datetime.now() - start_time).total_seconds(),
            )
    
    async def _crawl_web(self, config: CrawlConfigSchema) -> CrawlResult:
        """网页爬取"""
        web_config = config.web
        
        # robots.txt 检查
        if config.respect_robots:
            report = await self.robots_checker.check(web_config.url)
            if not report.allowed:
                return CrawlResult(
                    success=False, data=[],
                    message=f"robots.txt 不允许爬取: {web_config.url}",
                    source=config.name,
                )
            if report.crawl_delay:
                config.request_delay = max(config.request_delay, report.crawl_delay)
        
        if web_config.use_scrapling:
            return await self._crawl_web_scrapling(config)
        else:
            return await self._crawl_web_httpx(config)
    
    async def _crawl_web_httpx(self, config: CrawlConfigSchema) -> CrawlResult:
        """httpx 网页爬取"""
        web_config = config.web
        try:
            async with httpx.AsyncClient(timeout=config.timeout, follow_redirects=True) as client:
                if web_config.method.upper() == "GET":
                    response = await client.get(web_config.url, headers=web_config.headers or None)
                else:
                    response = await client.post(web_config.url, headers=web_config.headers or None)
                response.raise_for_status()
                html = response.text
            
            return CrawlResult(
                success=True,
                data=[{
                    "url": web_config.url,
                    "html_length": len(html),
                    "html_preview": html[:2000],
                    "crawled_at": datetime.now().isoformat(),
                }],
                message="网页爬取成功",
                source=config.name,
            )
        except Exception as e:
            return CrawlResult(
                success=False, data=[], message=f"网页爬取失败: {e}",
                source=config.name, error=str(e)
            )
    
    async def _crawl_web_scrapling(self, config: CrawlConfigSchema) -> CrawlResult:
        """Scrapling 网页爬取"""
        from crawlers.scrapling_adapter import ScraplingAdapter
        adapter = ScraplingAdapter()
        
        if not adapter.available:
            return CrawlResult(
                success=False, data=[], message="Scrapling 不可用",
                source=config.name,
            )
        
        web_config = config.web
        response = await adapter.fetch_page(url=web_config.url, headers=web_config.headers or None)
        
        if not response:
            return CrawlResult(
                success=False, data=[], message="Scrapling 获取失败",
                source=config.name,
            )
        
        if web_config.container_selector and web_config.item_selectors:
            data = adapter.parse_list(response, web_config.container_selector, web_config.item_selectors)
        elif web_config.selectors:
            data = [adapter.parse_elements(response, web_config.selectors)]
        else:
            text = adapter.get_page_text(response)
            data = [{"text": text, "url": web_config.url}] if text else []
        
        return CrawlResult(
            success=True, data=data, message="Scrapling 爬取成功",
            source=config.name, count=len(data),
        )
    
    async def _crawl_api(self, config: CrawlConfigSchema) -> CrawlResult:
        """API 采集"""
        api_config = config.api
        try:
            headers = dict(api_config.headers)
            if api_config.auth:
                auth_type = api_config.auth.get("type", "")
                if auth_type == "bearer":
                    headers["Authorization"] = f"Bearer {api_config.auth.get('token', '')}"
                elif auth_type == "api_key":
                    key_name = api_config.auth.get("header", "X-API-Key")
                    headers[key_name] = api_config.auth.get("key", "")
            
            async with httpx.AsyncClient(timeout=config.timeout) as client:
                if api_config.method.upper() == "GET":
                    response = await client.get(
                        api_config.endpoint, params=api_config.params, headers=headers,
                    )
                else:
                    response = await client.post(
                        api_config.endpoint, params=api_config.params,
                        json=api_config.body, headers=headers,
                    )
                response.raise_for_status()
                result = response.json()
            
            if api_config.data_path:
                for key in api_config.data_path.split("."):
                    if isinstance(result, dict):
                        result = result.get(key, {})
                    elif isinstance(result, list) and key.isdigit():
                        result = result[int(key)]
            
            all_data = result if isinstance(result, list) else [result]
            
            return CrawlResult(
                success=True, data=all_data, message="API 采集成功",
                source=config.name, count=len(all_data),
            )
        except Exception as e:
            return CrawlResult(
                success=False, data=[], message=f"API 采集失败: {e}",
                source=config.name, error=str(e)
            )
    
    async def _crawl_local(self, config: CrawlConfigSchema) -> CrawlResult:
        """本地文件采集"""
        try:
            from crawlers.utils.file_parser import FileParser
            parser = FileParser()
            result = parser.parse_file(
                file_path=config.local.file_path,
                file_type=config.local.file_type,
                encoding=config.local.encoding,
                delimiter=config.local.delimiter,
                sheet_name=config.local.sheet_name,
                skip_rows=config.local.skip_rows,
            )
            return CrawlResult(
                success=True, data=result.get("preview", []),
                message="文件解析成功", source=config.name,
                count=result.get("row_count", 0),
            )
        except Exception as e:
            return CrawlResult(
                success=False, data=[], message=f"文件解析失败: {e}",
                source=config.name, error=str(e)
            )
    
    async def test_run(self, config: CrawlConfigSchema, max_items: int = 10) -> Dict[str, Any]:
        """测试运行"""
        result = await self.execute(config)
        if result.data and len(result.data) > max_items:
            result.data = result.data[:max_items]
            result.message += f" (预览模式，仅显示前 {max_items} 条)"
        return {
            "success": result.success,
            "message": result.message,
            "count": result.count,
            "elapsed": result.elapsed,
            "preview": result.data,
            "error": result.error,
        }
