"""
站点探测 · 获取层
=================

负责探测流程中的网络获取：robots.txt、Sitemap、RSS/Atom 订阅源、主文档。

设计约束（对应合规四维的 C 维）：

- 所有请求标识自身身份与用途（C3）
- 遵守 robots.txt 的**路径级**约束：被 Disallow 的路径不抓，未被约束的路径正常抓；
  见到 Disallow 就整站放弃是判定错误，会损失绝大部分可采面
- 尊重 429 / 503 与 Retry-After（C4）
- 不绕过任何技术措施：出现验证码、付费墙、鉴权、WAF 挑战时如实记录并交由判定层处理
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx

logger = logging.getLogger(__name__)

# 标识自身身份，便于站点运营方识别与联系（行为合规 C3）
DEFAULT_USER_AGENT = (
    "WebInsightAgent/3.0 (+site-analysis; contact: platform-operator)"
)

DEFAULT_TIMEOUT = 15.0
MAX_BODY_BYTES = 5 * 1024 * 1024  # 单页上限 5MB，超出截断


@dataclass
class FetchResult:
    """一次 HTTP 获取的结果。"""

    url: str
    status: int = 0
    headers: dict[str, str] = field(default_factory=dict)
    text: str = ""
    final_url: str = ""
    elapsed_ms: int = 0
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.error is None and 200 <= self.status < 300

    @property
    def content_type(self) -> str:
        return self.headers.get("content-type", "").lower()

    @property
    def retry_after(self) -> Optional[float]:
        raw = self.headers.get("retry-after")
        if not raw:
            return None
        try:
            return float(raw)
        except ValueError:
            return None


@dataclass
class RobotsInfo:
    """robots.txt 的解析结果（路径级）。"""

    fetched: bool = False
    raw: str = ""
    sitemaps: list[str] = field(default_factory=list)
    crawl_delay: Optional[float] = None
    # 针对我方 UA 生效的规则，按出现顺序保留用于最长匹配
    disallow: list[str] = field(default_factory=list)
    allow: list[str] = field(default_factory=list)
    parse_error: Optional[str] = None

    def can_fetch(self, url: str, user_agent: str = DEFAULT_USER_AGENT) -> bool:
        """按最长匹配判定某个 URL 路径是否允许抓取。

        robots.txt 的语义是"最长匹配优先"，而不是"Disallow 一票否决"。
        未匹配任何规则时默认允许。
        """
        if not self.fetched:
            # 未取到 robots.txt（404/超时）视为无约束
            return True

        path = urlparse(url).path or "/"
        best_len = -1
        verdict = True

        for pattern in self.disallow:
            if _path_match(path, pattern) and len(pattern) >= best_len:
                best_len = len(pattern)
                verdict = False
        for pattern in self.allow:
            if _path_match(path, pattern) and len(pattern) > best_len:
                best_len = len(pattern)
                verdict = True
        return verdict


def _path_match(path: str, pattern: str) -> bool:
    """robots 路径匹配：支持 * 通配与 $ 结尾锚定。"""
    if not pattern:
        return False
    anchor_end = pattern.endswith("$")
    if anchor_end:
        pattern = pattern[:-1]
    if "*" in pattern:
        prefix, _, suffix = pattern.partition("*")
        return path.startswith(prefix) and (
            path.endswith(suffix) if suffix else True
        )
    if anchor_end:
        return path == pattern
    return path.startswith(pattern)


def _truncate(text: str, limit: int = MAX_BODY_BYTES) -> str:
    """按字节上限截断，避免超大页面拖垮探测。"""
    if len(text) <= limit:
        return text
    return text[:limit]


class SiteFetcher:
    """探测用的轻量 HTTP 客户端。

    与采集层的区别：这里只做探测所需的最小请求，低频、可缓存、带身份标识。
    """

    def __init__(
        self,
        user_agent: str = DEFAULT_USER_AGENT,
        timeout: float = DEFAULT_TIMEOUT,
        client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self.user_agent = user_agent
        self.timeout = timeout
        self._client = client
        self._owns_client = client is None
        self.request_count = 0

    def _headers(self) -> dict[str, str]:
        return {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml,"
            "application/json;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }

    async def __aenter__(self) -> "SiteFetcher":
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
                headers=self._headers(),
            )
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    async def get(self, url: str) -> FetchResult:
        """获取单个 URL。任何异常都转成 FetchResult，不向上抛。"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
                headers=self._headers(),
            )
            self._owns_client = True

        loop = asyncio.get_running_loop()
        started = loop.time()
        self.request_count += 1

        try:
            resp = await self._client.get(url)
        except httpx.HTTPError as exc:
            return FetchResult(
                url=url,
                error=f"{type(exc).__name__}: {exc}",
                elapsed_ms=int((loop.time() - started) * 1000),
            )

        elapsed = int((loop.time() - started) * 1000)
        headers = {k.lower(): v for k, v in resp.headers.items()}
        text = resp.text if _is_textual(headers.get("content-type", "")) else ""

        return FetchResult(
            url=url,
            status=resp.status_code,
            headers=headers,
            text=_truncate(text),
            final_url=str(resp.url),
            elapsed_ms=elapsed,
        )

    async def fetch_robots(self, base_url: str) -> RobotsInfo:
        """获取并解析 robots.txt。"""
        robots_url = urljoin(base_url, "/robots.txt")
        result = await self.get(robots_url)

        if not result.ok or not result.text.strip():
            logger.info("robots.txt 不可用 (%s): status=%s", robots_url, result.status)
            return RobotsInfo(fetched=False)

        info = parse_robots(result.text, base_url=base_url)
        info.fetched = True
        return info

    async def discover_sitemaps(self, base_url: str, robots: RobotsInfo) -> list[str]:
        """发现 sitemap 入口：优先 robots 声明，其次常规路径。"""
        candidates: list[str] = list(robots.sitemaps)

        if not candidates:
            for path in ("/sitemap.xml", "/sitemap_index.xml", "/sitemap.xml.gz"):
                candidates.append(urljoin(base_url, path))

        found: list[str] = []
        for url in candidates[:3]:  # 探测阶段最多试 3 个
            result = await self.get(url)
            if result.ok and ("<urlset" in result.text or "<sitemapindex" in result.text):
                found.append(result.final_url or url)
        return found

    async def discover_feeds(self, html: str, base_url: str) -> list[dict]:
        """从页面 <link rel="alternate"> 中发现 RSS / Atom 订阅源。"""
        feeds: list[dict] = []
        try:
            from bs4 import BeautifulSoup
        except ImportError:  # pragma: no cover - 依赖缺失时静默跳过
            return feeds

        soup = BeautifulSoup(html, "lxml")
        for link in soup.find_all("link", rel=lambda v: v and "alternate" in v):
            type_ = (link.get("type") or "").lower()
            if "rss" in type_ or "atom" in type_ or "xml" in type_:
                href = link.get("href")
                if href:
                    feeds.append(
                        {
                            "url": urljoin(base_url, href),
                            "type": "atom" if "atom" in type_ else "rss",
                            "title": link.get("title") or "",
                        }
                    )
        return feeds


def _is_textual(content_type: str) -> bool:
    if not content_type:
        return True
    return any(
        token in content_type
        for token in ("text/", "json", "xml", "javascript", "html")
    )


def robots_from_profile(profile: dict) -> "RobotsInfo":
    """从已落库的站点画像重建 robots 规则。

    采集阶段复用判别阶段的探测结果，避免为每个任务重复请求 robots.txt。
    """
    access = profile.get("access") or {}
    return RobotsInfo(
        fetched=bool(access.get("robots_fetched")),
        disallow=list(access.get("robots_disallow") or []),
        allow=list(access.get("robots_allow") or []),
        crawl_delay=access.get("crawl_delay"),
        sitemaps=list(access.get("sitemaps") or []),
    )


def parse_robots(text: str, base_url: str = "") -> RobotsInfo:
    """解析 robots.txt 为路径级规则。

    只提取针对 `*` 或我方 UA 的规则；其余 UA 段忽略。

    同时用标准库 RobotFileParser 做一次交叉校验，仅用于记录 crawl_delay
    与 sitemap（标准库对 * 通配支持有限，故主判定用本函数的规则列表）。
    """
    info = RobotsInfo(raw=text[:8000])
    if not text.strip():
        # 内容为空等同于"无 robots 约束"，保持 fetched=False
        return info

    applies = False
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip().lower()
        value = value.strip()

        if key == "user-agent":
            applies = value == "*" or "webinsight" in value.lower()
            continue
        if not applies:
            continue

        if key == "disallow":
            if value:
                info.disallow.append(value)
        elif key == "allow":
            if value:
                info.allow.append(value)
        elif key == "crawl-delay":
            try:
                info.crawl_delay = float(value)
            except ValueError:
                pass
        elif key == "sitemap":
            info.sitemaps.append(value)

    if base_url:
        try:
            parser = RobotFileParser()
            parser.parse(text.splitlines())
            delay = parser.crawl_delay(DEFAULT_USER_AGENT.split("/")[0])
            if delay and info.crawl_delay is None:
                info.crawl_delay = float(delay)
        except Exception as exc:  # noqa: BLE001 - 交叉校验失败不影响主流程
            info.parse_error = str(exc)[:200]

    # 解析成功即视为已获取，规则列表生效
    info.fetched = True
    return info
