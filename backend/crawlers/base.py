# -*- coding: utf-8 -*-
"""
爬虫基类 - 提供统一的爬虫接口和基础功能

增强版 v2：集成反爬策略 + Scrapling + 数据库存储
"""
import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
import httpx
from fake_useragent import UserAgent

# 导入反爬模块
from .utils.anti_crawler import (
    AntiCrawlerEnhancer,
    BrowserFingerprint,
    Proxy,
    get_enhancer,
)

# 导入 Scrapling 适配器
from .scrapling_adapter import ScraplingAdapter, ScraplingConfig

# 导入数据库（延迟导入避免循环依赖）
_db_service = None

def _get_db_service():
    global _db_service
    if _db_service is None:
        try:
            from database.service import DataService
            _db_service = DataService()
        except Exception:
            return None
    return _db_service


@dataclass
class CrawlResult:
    """爬取结果"""
    success: bool
    data: List[Dict]
    message: str
    source: str
    count: int = 0
    elapsed: float = 0.0
    error: Optional[str] = None
    db_record_id: Optional[int] = None

    def __post_init__(self):
        if self.count == 0 and self.data:
            self.count = len(self.data)

    def save_to_db(self, platform: str = None, keyword: str = None, category: str = None) -> Optional[int]:
        """保存结果到数据库"""
        if not self.data:
            return None

        db = _get_db_service()
        if db is None:
            return None

        try:
            result = db.save_crawl_result(
                source=self.source,
                data=self.data,
                category=category,
                keyword=keyword,
                platform=platform or self.source
            )
            self.db_record_id = result.get('record_id')
            return self.db_record_id
        except Exception as e:
            logging.warning(f"保存到数据库失败: {e}")
            return None

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'success': self.success,
            'data': self.data,
            'message': self.message,
            'source': self.source,
            'count': self.count,
            'elapsed': self.elapsed,
            'error': self.error,
            'db_record_id': self.db_record_id
        }


class BaseCrawler(ABC):
    """爬虫基类（增强版 v2 — 集成 Scrapling）"""

    def __init__(self, name: str = None, enable_anti_crawler: bool = True, enable_scrapling: bool = False):
        """
        初始化爬虫基类

        Args:
            name: 爬虫名称
            enable_anti_crawler: 是否启用反爬增强
            enable_scrapling: 是否启用 Scrapling（反爬绕过 + 动态渲染）
        """
        self.name = name or self.__class__.__name__
        self.logger = logging.getLogger(self.name)
        self.ua = UserAgent()
        self.request_delay = 1.0  # 请求间隔（秒）
        self.timeout = 30  # 超时（秒）
        self.max_retries = 3  # 最大重试次数

        # 反爬增强
        self.enable_anti_crawler = enable_anti_crawler
        self._anti_crawler = None

        # Scrapling 集成
        self.enable_scrapling = enable_scrapling
        self._scrapling = None

        # 请求统计
        self._request_count = 0
        self._success_count = 0
        self._fail_count = 0
        self._scrapling_fallback_count = 0

    @property
    def anti_crawler(self) -> AntiCrawlerEnhancer:
        """获取反爬增强器（懒加载）"""
        if self._anti_crawler is None:
            self._anti_crawler = get_enhancer()
        return self._anti_crawler

    @property
    def scrapling(self) -> ScraplingAdapter:
        """获取 Scrapling 适配器（懒加载）"""
        if self._scrapling is None and self.enable_scrapling:
            self._scrapling = ScraplingAdapter()
        return self._scrapling

    async def fetch_with_scrapling(
        self,
        url: str,
        selectors: Dict[str, str] = None,
        container_selector: str = None,
        item_selectors: Dict[str, str] = None,
        stealthy: bool = False,
        wait_for: str = None,
        auto_scroll: bool = False,
        headless: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """
        使用 Scrapling 获取并解析页面

        两种模式:
        1. 简单模式 (stealthy=False): 使用 Fetcher，适合普通页面
        2. 隐身模式 (stealthy=True): 使用 StealthyFetcher，适合有反爬保护的页面

        Args:
            url: 目标 URL
            selectors: CSS 选择器映射 {字段名: 选择器}
            container_selector: 列表项容器选择器
            item_selectors: 列表项字段选择器映射
            stealthy: 是否使用隐身模式
            wait_for: 等待的 CSS 选择器
            auto_scroll: 是否自动滚动
            headless: 是否无头模式

        Returns:
            解析结果字典，失败返回 None
        """
        if not self.scrapling or not self.scrapling.available:
            self.logger.warning("Scrapling 不可用，回退到 httpx")
            return None

        try:
            # 获取页面
            if stealthy:
                response = await self.scrapling.fetch_stealthy(
                    url=url,
                    wait_for=wait_for,
                    auto_scroll=auto_scroll,
                    headless=headless,
                )
            else:
                response = await self.scrapling.fetch_page(url=url)

            if not response:
                return None

            # 解析页面
            if container_selector and item_selectors:
                # 列表解析模式
                data = self.scrapling.parse_list(response, container_selector, item_selectors)
                return {"type": "list", "data": data, "count": len(data)}
            elif selectors:
                # 字段解析模式
                data = self.scrapling.parse_elements(response, selectors)
                return {"type": "dict", "data": data}
            else:
                # 返回原始内容
                text = self.scrapling.get_page_text(response)
                html = self.scrapling.get_page_html(response)
                return {"type": "raw", "text": text, "html": html}

        except Exception as e:
            self.logger.error(f"Scrapling 获取失败: {e}")
            return None

    async def fetch_auto(
        self,
        url: str,
        **kwargs,
    ) -> Optional[str]:
        """
        自动选择获取方式

        优先使用 httpx，失败后自动回退到 Scrapling

        Args:
            url: 目标 URL
            **kwargs: 传递给 fetch() 的参数

        Returns:
            响应内容文本
        """
        # 1. 先尝试 httpx
        result = await self.fetch(url, **kwargs)
        if result is not None:
            return result

        # 2. httpx 失败，尝试 Scrapling
        if self.enable_scrapling and self.scrapling and self.scrapling.available:
            self.logger.info(f"httpx 失败，回退到 Scrapling: {url}")
            self._scrapling_fallback_count += 1
            response = await self.scrapling.fetch_page(url=url)
            if response:
                return self.scrapling.get_page_text(response)

        return None

    def _get_headers(self) -> Dict[str, str]:
        """获取随机请求头（基础版）"""
        return {
            "User-Agent": self.ua.random,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }

    def _get_enhanced_headers(self, url: str, referer: str = None) -> Dict[str, str]:
        """获取增强版请求头（反爬增强）"""
        if self.enable_anti_crawler:
            return self.anti_crawler.generate_headers(url, referer)
        return self._get_headers()

    async def fetch(
        self,
        url: str,
        method: str = "GET",
        headers: Dict = None,
        params: Dict = None,
        json_data: Dict = None,
        retry: int = 0,
        use_proxy: bool = False
    ) -> Optional[str]:
        """
        HTTP 请求封装（增强版）

        Args:
            url: 请求URL
            method: 请求方法
            headers: 请求头
            params: URL参数
            json_data: JSON数据
            retry: 当前重试次数
            use_proxy: 是否使用代理

        Returns:
            响应内容文本，失败返回 None
        """
        self._request_count += 1
        domain = urlparse(url).netloc

        # 获取请求头
        if headers is None:
            if self.enable_anti_crawler:
                headers = self._get_enhanced_headers(url)
            else:
                headers = self._get_headers()

        # 反爬：请求前等待
        if self.enable_anti_crawler:
            await self.anti_crawler.wait_before_request(url)

        try:
            # 构建代理配置（httpx 0.27+ 使用 proxy 参数）
            proxy_url = None
            if use_proxy and self.enable_anti_crawler:
                ip_info = await self.anti_crawler.ip_rotation.get_next_ip()
                if ip_info.get("type") == "proxy":
                    proxy_url = ip_info.get("url")
                    self.logger.debug(f"使用代理: {proxy_url}")

            async with httpx.AsyncClient(timeout=self.timeout, proxy=proxy_url) as client:
                if method.upper() == "GET":
                    response = await client.get(url, headers=headers, params=params)
                else:
                    response = await client.post(url, headers=headers, json=json_data)

                response.raise_for_status()

                # 成功统计
                self._success_count += 1
                if self.enable_anti_crawler:
                    await self.anti_crawler.on_request_success(url)

                return response.text

        except httpx.HTTPStatusError as e:
            self._fail_count += 1
            self.logger.warning(f"HTTP错误 {e.response.status_code}: {url}")

            if self.enable_anti_crawler:
                await self.anti_crawler.on_request_failure(url, e.response.status_code)

            if e.response.status_code in [403, 418, 429]:
                # 被封禁，增加延迟后重试
                wait_time = 5 * (retry + 1)
                self.logger.info(f"等待 {wait_time} 秒后重试...")
                await asyncio.sleep(wait_time)
                if retry < self.max_retries:
                    return await self.fetch(url, method, headers, params, json_data, retry + 1, use_proxy)
            return None

        except httpx.RequestError as e:
            self._fail_count += 1
            self.logger.error(f"请求错误: {e}")

            if self.enable_anti_crawler:
                await self.anti_crawler.on_request_failure(url, error=e)

            if retry < self.max_retries:
                await asyncio.sleep(2 ** retry)
                return await self.fetch(url, method, headers, params, json_data, retry + 1, use_proxy)
            return None

        except Exception as e:
            self._fail_count += 1
            self.logger.error(f"未知错误: {e}")
            return None

    def get_stats(self) -> Dict[str, Any]:
        """获取爬虫统计信息"""
        stats = {
            "name": self.name,
            "request_count": self._request_count,
            "success_count": self._success_count,
            "fail_count": self._fail_count,
            "success_rate": self._success_count / max(self._request_count, 1) * 100,
            "scrapling_enabled": self.enable_scrapling,
            "scrapling_fallback_count": self._scrapling_fallback_count,
        }
        if self.enable_anti_crawler and self._anti_crawler:
            stats["anti_crawler"] = self._anti_crawler.get_stats()
        if self.enable_scrapling and self._scrapling:
            stats["scrapling_available"] = self._scrapling.available
        return stats

    async def fetch_with_delay(self, url: str, **kwargs) -> Optional[str]:
        """带请求间隔的获取"""
        await asyncio.sleep(self.request_delay)
        return await self.fetch(url, **kwargs)

    @abstractmethod
    async def crawl(self, **kwargs) -> CrawlResult:
        """执行爬取（子类必须实现）"""
        pass

    async def run(self, **kwargs) -> CrawlResult:
        """运行爬虫的便捷方法"""
        start_time = time.time()
        try:
            result = await self.crawl(**kwargs)
            result.elapsed = time.time() - start_time
            return result
        except Exception as e:
            self.logger.error(f"爬虫执行失败: {e}")
            return CrawlResult(
                success=False,
                data=[],
                message=f"爬虫执行失败: {str(e)}",
                source=self.name,
                elapsed=time.time() - start_time,
                error=str(e)
            )
