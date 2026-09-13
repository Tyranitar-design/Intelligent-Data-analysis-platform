# -*- coding: utf-8 -*-
"""
HTTPX 策略 - 智能爬虫系统 v2.0

适用于 API 请求和静态页面的轻量级爬取策略。
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, List, Optional

import httpx

from ..models import CrawlIntent, IntentType, ProbeResult, StrategyResult
from .base import BaseStrategy


class HttpxStrategy(BaseStrategy):
    """HTTPX 爬取策略

    适用于:
    - API 数据请求
    - 静态 HTML 页面
    - 轻量级数据获取
    """

    name: str = "httpx"
    priority: int = 100

    def __init__(
        self,
        timeout: int = 30,
        follow_redirects: bool = True,
        max_redirects: int = 10,
    ) -> None:
        self.timeout = timeout
        self.follow_redirects = follow_redirects
        self.max_redirects = max_redirects
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """获取或创建 HTTP 客户端"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                follow_redirects=self.follow_redirects,
                max_redirects=self.max_redirects,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                },
            )
        return self._client

    async def can_handle(self, probe: ProbeResult) -> bool:
        """判断是否可处理

        适用于:
        - JSON API
        - 静态 HTML
        - 非保护页面
        """
        if probe.requires_auth:
            return False
        if probe.is_protected:
            return False
        if probe.detected_intent == IntentType.DYNAMIC_CONTENT:
            return False
        return True

    async def execute(
        self,
        url: str,
        intent: Optional[CrawlIntent] = None,
        **kwargs: Any,
    ) -> StrategyResult:
        """执行 HTTP 请求"""
        start_time = time.time()
        intent = intent or CrawlIntent()
        headers = intent.headers.copy() if intent.headers else {}
        cookies = intent.cookies.copy() if intent.cookies else {}

        try:
            client = await self._get_client()

            response = await client.get(
                url,
                headers=headers,
                cookies=cookies,
                timeout=self.timeout,
            )

            duration_ms = (time.time() - start_time) * 1000

            if response.status_code == 200:
                content_type = response.headers.get("content-type", "")

                if "application/json" in content_type:
                    data = response.json()
                    return StrategyResult(
                        strategy_name=self.name,
                        success=True,
                        data=data,
                        content=response.text,
                        duration_ms=duration_ms,
                        status_code=response.status_code,
                        metadata={"content_type": content_type},
                    )
                else:
                    return StrategyResult(
                        strategy_name=self.name,
                        success=True,
                        content=response.text,
                        duration_ms=duration_ms,
                        status_code=response.status_code,
                        metadata={"content_type": content_type},
                    )
            else:
                return StrategyResult(
                    strategy_name=self.name,
                    success=False,
                    error=f"HTTP {response.status_code}",
                    duration_ms=duration_ms,
                    status_code=response.status_code,
                )

        except asyncio.TimeoutError:
            return StrategyResult(
                strategy_name=self.name,
                success=False,
                error="Request timeout",
                duration_ms=(time.time() - start_time) * 1000,
            )
        except httpx.RequestError as e:
            return StrategyResult(
                strategy_name=self.name,
                success=False,
                error=f"Request error: {str(e)}",
                duration_ms=(time.time() - start_time) * 1000,
            )
        except Exception as e:
            return StrategyResult(
                strategy_name=self.name,
                success=False,
                error=f"Unexpected error: {str(e)}",
                duration_ms=(time.time() - start_time) * 1000,
            )

    def get_timeout(self) -> int:
        """获取超时时间"""
        return self.timeout

    def get_capabilities(self) -> List[str]:
        """获取策略能力"""
        return [
            "api_requests",
            "static_html",
            "json_parsing",
            "cookie_management",
            "redirect_handling",
        ]

    async def close(self) -> None:
        """关闭客户端"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
