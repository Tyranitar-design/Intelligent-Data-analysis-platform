"""
能力层共享工具
==============

把"取一页"这件事收敛到一处：限速、并发闸门、robots 检查、退避反馈、
错误归一化。各能力不再各自实现请求逻辑——这是 P0 单一定义原则的延续。

合规章制在此处生效：robots 不允许的路径直接拒绝，不进入请求。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Optional
from urllib.parse import urlparse

import httpx

from collect.ratelimit import AdaptiveRateLimiter

logger = logging.getLogger(__name__)

DEFAULT_USER_AGENT = (
    "WebInsightAgent/3.0 (+data-collection; contact: platform-operator)"
)
MAX_BODY_BYTES = 5 * 1024 * 1024


@dataclass
class PageResult:
    """一次取页的结果。"""

    url: str
    status: int = 0
    text: str = ""
    headers: dict[str, str] = field(default_factory=dict)
    final_url: str = ""
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.error is None and 200 <= self.status < 300

    @property
    def blocked(self) -> bool:
        """是否被 robots 或目标站点拒绝。"""
        return self.status in (401, 403, 451) or (
            self.error is not None and self.error.startswith("robots_disallowed")
        )


def _retry_after(headers: dict[str, str]) -> Optional[float]:
    raw = headers.get("retry-after")
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


class PageFetcher:
    """带限速、并发闸门与 robots 检查的取页工具。"""

    def __init__(
        self,
        client: httpx.AsyncClient,
        limiter: AdaptiveRateLimiter,
        robots_check: Optional[Callable[[str], bool]] = None,
        user_agent: str = DEFAULT_USER_AGENT,
    ) -> None:
        self.client = client
        self.limiter = limiter
        self.robots_check = robots_check
        self.user_agent = user_agent
        self.request_count = 0
        self.blocked_count = 0

    async def get(self, url: str, base_rate: Optional[float] = None) -> PageResult:
        """取一页。任何异常都归一成 PageResult，不向上抛。"""
        if self.robots_check is not None and not self.robots_check(url):
            self.blocked_count += 1
            return PageResult(url=url, error="robots_disallowed: 该路径被 robots 排除")

        domain = urlparse(url).netloc
        await self.limiter.acquire(domain, base_rate)
        semaphore = await self.limiter.concurrency_slot(domain)

        async with semaphore:
            try:
                response = await self.client.get(url)
            except httpx.HTTPError as exc:
                return PageResult(url=url, error=f"{type(exc).__name__}: {exc}"[:200])

        self.request_count += 1
        headers = {k.lower(): v for k, v in response.headers.items()}
        self.limiter.on_response(
            domain, response.status_code, _retry_after(headers)
        )

        content_type = headers.get("content-type", "")
        textual = (
            not content_type
            or any(
                token in content_type
                for token in ("text/", "json", "xml", "html", "javascript")
            )
        )
        text = response.text if textual else ""
        if len(text) > MAX_BODY_BYTES:
            text = text[:MAX_BODY_BYTES]

        return PageResult(
            url=url,
            status=response.status_code,
            text=text,
            headers=headers,
            final_url=str(response.url),
        )

    async def get_many(
        self,
        urls: list[str],
        base_rate: Optional[float] = None,
        limit: Optional[int] = None,
    ) -> list[PageResult]:
        """顺序取多页（顺序而非并发，避免对目标站点形成突发压力）。"""
        results: list[PageResult] = []
        for url in urls[: limit or len(urls)]:
            results.append(await self.get(url, base_rate=base_rate))
        return results


def text_length(html: str) -> int:
    """粗略统计可见文本长度，用于质量评估。"""
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        return len(soup.get_text(strip=True))
    except Exception:  # noqa: BLE001
        return len(html)


def looks_like_js_shell(html: str) -> bool:
    """判断页面是否只是一个等待 JS 填充的空壳。"""
    return text_length(html) < 400 and html.count("<script") >= 5


def safe_json(obj: Any) -> Any:
    """把不可 JSON 序列化的值降级为字符串。"""
    import json

    try:
        json.dumps(obj)
        return obj
    except (TypeError, ValueError):
        return str(obj)[:500]
