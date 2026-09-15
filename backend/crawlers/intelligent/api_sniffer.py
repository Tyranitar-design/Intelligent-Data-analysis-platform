# -*- coding: utf-8 -*-
"""API 嗅探器：Playwright 网络监听 → JSON 接口提取 → 直连取数

调研依据（多源交叉）：XHR/API 直连相比 DOM 解析——更快、更稳（接口变更频率低于
CSS 选择器）、资源效率高（免渲染）。来源：dataprixa「Best Practices for Handling
Dynamic Content」、context.dev《Web Scraping in Python 2026》、zenrows 等。

用法::

    sniffer = ApiSniffer()
    sniffer.attach(page)          # 页面加载前挂载
    await page.goto(url)
    best = sniffer.best_api()     # 最佳 JSON 接口
    rows = await sniffer.fetch_via_api(best, page=url)   # 直连取数（免浏览器）
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

ITEM_KEYS = ("items", "data", "list", "results", "rows", "records")
INNER_KEYS = ("items", "list", "results", "rows", "records")


class ApiSniffer:
    """收集页面 XHR/fetch JSON 接口，并支持直连取数。"""

    def __init__(self, max_capture: int = 60):
        self.max_capture = max_capture
        self.captured: List[Dict[str, Any]] = []
        self._tasks: List[asyncio.Task] = []

    # ------------------------------------------------------------------ #
    # 挂载与捕获
    # ------------------------------------------------------------------ #
    def attach(self, page) -> None:
        """挂载响应监听（页面加载前调用）。"""

        def handler(response):
            task = asyncio.ensure_future(self._on_response(response))
            self._tasks.append(task)

        page.on("response", handler)

    async def drain(self, timeout: float = 1.0) -> None:
        """等待进行中的捕获任务完成（页面 networkidle 后调用更稳）。"""
        if self._tasks:
            await asyncio.wait(self._tasks, timeout=timeout)

    async def _on_response(self, response) -> None:
        try:
            request = response.request
            if request.resource_type not in ("xhr", "fetch"):
                return
            if len(self.captured) >= self.max_capture:
                return
            headers = response.headers or {}
            content_type = (headers.get("content-type") or "").lower()
            if "json" not in content_type:
                return
            try:
                body = await response.json()
            except Exception:  # noqa: BLE001
                return
            item_count = self._count_items(body)
            preview = None
            try:
                preview = json.dumps(body, ensure_ascii=False)[:300]
            except Exception:  # noqa: BLE001
                pass
            self.captured.append(
                {
                    "url": response.url,
                    "method": request.method,
                    "status": response.status,
                    "content_type": content_type,
                    "item_count": item_count,
                    "body_preview": preview,
                    "body": body if item_count and item_count <= 5000 else None,
                }
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("响应嗅探忽略: %s", exc)

    # ------------------------------------------------------------------ #
    # 启发式：条数统计与最佳候选
    # ------------------------------------------------------------------ #
    @staticmethod
    def _count_items(body: Any) -> int:
        if isinstance(body, list):
            return len(body)
        if isinstance(body, dict):
            for key in ITEM_KEYS:
                value = body.get(key)
                if isinstance(value, list):
                    return len(value)
                if isinstance(value, dict):
                    for inner_key in INNER_KEYS:
                        inner = value.get(inner_key)
                        if isinstance(inner, list):
                            return len(inner)
        return 0

    def best_api(self) -> Optional[Dict[str, Any]]:
        """选最佳接口：item_count 优先；URL 含 api / 方法 GET 加分。"""
        if not self.captured:
            return None

        def score(item: Dict[str, Any]) -> int:
            value = int(item.get("item_count") or 0)
            url = item.get("url") or ""
            if "/api" in url or "api." in url:
                value += 100
            if item.get("method") == "GET":
                value += 10
            return value

        return max(self.captured, key=score)

    # ------------------------------------------------------------------ #
    # 直连取数
    # ------------------------------------------------------------------ #
    async def fetch_via_api(
        self,
        api: Dict[str, Any],
        page: Optional[str] = None,
        limit: int = 500,
    ) -> Optional[List[Dict[str, Any]]]:
        """直连 API 取数（免浏览器）。返回记录列表；无法解析时 None。

        Args:
            api: ``best_api()`` 返回的接口描述
            page: 页面 URL（作为 Referer 提升通过率）
            limit: 最大记录数
        """
        import httpx

        try:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept": "application/json, text/plain, */*",
            }
            if page:
                headers["Referer"] = page
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                resp = await client.get(api["url"], headers=headers)
                body = resp.json()
        except Exception as exc:  # noqa: BLE001
            logger.warning("API 直连失败: %s", exc)
            return None
        return self._extract_records(body)[:limit]

    @staticmethod
    def _extract_records(body: Any) -> List[Dict[str, Any]]:
        if isinstance(body, list):
            return [row for row in body if isinstance(row, dict)]
        if isinstance(body, dict):
            for key in ITEM_KEYS:
                value = body.get(key)
                if isinstance(value, list):
                    return [row for row in value if isinstance(row, dict)]
                if isinstance(value, dict):
                    for inner_key in INNER_KEYS:
                        inner = value.get(inner_key)
                        if isinstance(inner, list):
                            return [row for row in inner if isinstance(row, dict)]
        return []
