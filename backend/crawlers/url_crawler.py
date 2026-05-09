# -*- coding: utf-8 -*-
"""
URL 自由爬取模块 - Phase 4.5

核心功能：
1. 自动探测 URL 类型（API / 静态网页 / 动态网页 / 反爬网页）
2. 智能选择爬取策略（httpx / Scrapling / crawl4ai）
3. 智能解析结构化数据（表格 / 列表 / 卡片）
4. 数据质量校验与清洗

爬取策略优先级：
- API (JSON) → httpx 直接请求
- 静态 HTML → Scrapling Fetcher
- 反爬页面 → Scrapling StealthyFetcher
- SPA/动态 → crawl4ai 智能提取
"""
import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse, urljoin

import httpx
from bs4 import BeautifulSoup

from .base import BaseCrawler, CrawlResult
from .scrapling_adapter import ScraplingAdapter
from .auth.auth_manager import AuthManager

logger = logging.getLogger(__name__)

# 尝试导入 crawl4ai
try:
    from crawl4ai import AsyncWebCrawler
    CRAWL4AI_AVAILABLE = True
except ImportError:
    CRAWL4AI_AVAILABLE = False
    logger.warning("crawl4ai 未安装，SPA/动态页面爬取将不可用")


@dataclass
class URLProbeResult:
    """URL 探测结果"""
    url: str
    content_type: str = ""
    status_code: int = 0
    is_api: bool = False
    is_static_html: bool = False
    is_dynamic: bool = False  # SPA / 大量 JS
    is_protected: bool = False  # Cloudflare / 反爬
    requires_login: bool = False
    charset: str = "utf-8"
    content_length: int = 0
    error: Optional[str] = None


@dataclass
class ParsedData:
    """解析后的数据"""
    data_type: str  # "table", "list", "cards", "article", "api_response"
    data: List[Dict[str, Any]]
    columns: List[str] = field(default_factory=list)
    total_count: int = 0
    preview: Dict[str, Any] = field(default_factory=dict)


class URLCrawler(BaseCrawler):
    """
    URL 自由爬取器

    使用方式：
        crawler = URLCrawler()
        result = await crawler.crawl_url("https://example.com")
    """

    def __init__(self, enable_crawl4ai: bool = True):
        super().__init__(name="URLCrawler", enable_anti_crawler=True, enable_scrapling=True)
        self.enable_crawl4ai = enable_crawl4ai and CRAWL4AI_AVAILABLE
        self._crawl4ai = None
        self.auth_manager = AuthManager()  # 登录态管理器

    @property
    def crawl4ai(self):
        """获取 crawl4ai 实例（懒加载）"""
        if self._crawl4ai is None and self.enable_crawl4ai:
            self._crawl4ai = AsyncWebCrawler()
        return self._crawl4ai

    # ==================== 1. URL 探测 ====================

    async def probe_url(self, url: str, timeout: int = 10) -> URLProbeResult:
        """
        探测 URL 类型和特征

        通过 HEAD 请求快速判断：
        - Content-Type → API vs 网页
        - 状态码 → 是否被保护
        - 响应头 → 是否有反爬特征
        """
        result = URLProbeResult(url=url)

        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                # HEAD 请求
                try:
                    head_resp = await client.head(url, headers=self._get_headers())
                    result.status_code = head_resp.status_code
                    result.content_type = head_resp.headers.get("content-type", "").lower()
                    result.charset = self._extract_charset(head_resp.headers.get("content-type", ""))
                    result.content_length = int(head_resp.headers.get("content-length", 0))
                except Exception:
                    # HEAD 不支持，降级到 GET
                    pass

                # 如果 HEAD 失败或需要更多信息，用 GET 获取前 4KB
                if result.status_code == 0 or result.status_code >= 400:
                    get_resp = await client.get(
                        url,
                        headers=self._get_headers(),
                        timeout=timeout,
                    )
                    result.status_code = get_resp.status_code
                    if not result.content_type:
                        result.content_type = get_resp.headers.get("content-type", "").lower()

                    # 检查反爬特征
                    body_preview = get_resp.text[:4096]
                    result.is_protected = self._detect_protection(body_preview, result.status_code)

        except httpx.HTTPStatusError as e:
            result.status_code = e.response.status_code
            result.is_protected = result.status_code in [403, 418, 429, 503]
            result.error = f"HTTP {result.status_code}"
        except Exception as e:
            result.error = str(e)
            result.is_protected = True  # 未知错误，假设需要高级爬取

        # 判断类型
        result.is_api = self._is_api_response(result.content_type)
        result.is_static_html = self._is_static_html(result.content_type)

        return result

    def _extract_charset(self, content_type: str) -> str:
        """从 Content-Type 提取编码"""
        match = re.search(r"charset=([\w-]+)", content_type, re.IGNORECASE)
        return match.group(1) if match else "utf-8"

    def _is_api_response(self, content_type: str) -> bool:
        """判断是否为 API 响应"""
        api_types = [
            "application/json",
            "application/xml",
            "text/xml",
            "application/javascript",
        ]
        return any(t in content_type for t in api_types)

    def _is_static_html(self, content_type: str) -> bool:
        """判断是否为静态 HTML"""
        return "text/html" in content_type

    def _detect_protection(self, body: str, status_code: int) -> bool:
        """检测是否有反爬保护"""
        if status_code in [403, 418, 429, 503]:
            return True

        protection_signals = [
            "cloudflare",
            "cf-browser-verification",
            "turnstile",
            "captcha",
            "access denied",
            "blocked",
            "challenge",
            "ddos-guard",
            "incapsula",
        ]
        body_lower = body.lower()
        return any(signal in body_lower for signal in protection_signals)

    # ==================== 2. 智能爬取 ====================

    async def crawl_url(
        self,
        url: str,
        selectors: Dict[str, str] = None,
        container_selector: str = None,
        item_selectors: Dict[str, str] = None,
        force_strategy: str = None,
        wait_for: str = None,
        auto_scroll: bool = False,
        timeout: int = 30,
        auth_platform: str = None,  # 登录平台 (如: zhihu, weibo)
        use_auth: bool = False,     # 是否使用登录态
    ) -> CrawlResult:
        """
        智能爬取 URL

        Args:
            url: 目标 URL
            selectors: CSS 选择器 {字段名: 选择器}
            container_selector: 列表容器选择器
            item_selectors: 列表项字段选择器
            force_strategy: 强制使用策略 ("api"/"static"/"stealthy"/"crawl4ai")
            wait_for: 等待渲染的选择器
            auto_scroll: 是否自动滚动
            timeout: 超时时间

        Returns:
            CrawlResult
        """
        start_time = asyncio.get_event_loop().time()
        logger.info(f"开始爬取: {url}")

        try:
            # Step 1: 探测 URL
            if not force_strategy:
                probe = await self.probe_url(url)
                if probe.error and not probe.is_protected:
                    return CrawlResult(
                        success=False,
                        data=[],
                        message=f"URL 探测失败: {probe.error}",
                        source="url_crawler",
                        error=probe.error,
                    )
                strategy = self._choose_strategy(probe)
            else:
                strategy = force_strategy
                probe = None

            logger.info(f"使用策略: {strategy}")

            # Step 2: 执行爬取
            raw_content = None
            content_type = "html"

            # 准备认证信息
            auth_headers = {}
            auth_cookies = None
            if use_auth and auth_platform:
                auth_headers = await self.auth_manager.get_auth_headers(auth_platform)
                auth_cookies = self.auth_manager.cookie_store.get_cookies(auth_platform)
                logger.info(f"使用登录态: {auth_platform}, cookies={len(auth_cookies) if auth_cookies else 0}")

            if strategy == "api":
                raw_content, content_type = await self._fetch_api(url, timeout, auth_headers)
            elif strategy == "static":
                raw_content, content_type = await self._fetch_static(url, timeout, auth_headers)
            elif strategy == "stealthy":
                raw_content = await self._fetch_stealthy(url, wait_for, auto_scroll, timeout, auth_cookies)
            elif strategy == "crawl4ai":
                raw_content = await self._fetch_crawl4ai(url, timeout, auth_cookies)
            else:
                # 自动回退
                raw_content = await self._fetch_auto_fallback(url, timeout, auth_headers)

            if raw_content is None:
                return CrawlResult(
                    success=False,
                    data=[],
                    message="爬取失败: 无法获取内容",
                    source="url_crawler",
                    error="Empty response",
                )

            # Step 3: 智能解析
            parsed = self._parse_content(raw_content, content_type, selectors, container_selector, item_selectors)

            # Step 4: 数据质量校验
            quality_report = self._check_data_quality(parsed)

            elapsed = asyncio.get_event_loop().time() - start_time

            return CrawlResult(
                success=True,
                data=parsed.data,
                message=f"爬取成功 | 策略: {strategy} | 类型: {parsed.data_type} | 数量: {parsed.total_count} | 质量: {quality_report['score']:.0%}",
                source="url_crawler",
                count=parsed.total_count,
                elapsed=elapsed,
            )

        except Exception as e:
            elapsed = asyncio.get_event_loop().time() - start_time
            logger.error(f"爬取异常: {e}")
            return CrawlResult(
                success=False,
                data=[],
                message=f"爬取异常: {str(e)}",
                source="url_crawler",
                elapsed=elapsed,
                error=str(e),
            )

    def _choose_strategy(self, probe: URLProbeResult) -> str:
        """根据探测结果选择爬取策略"""
        if probe.is_api:
            return "api"
        if probe.is_protected:
            if self.enable_crawl4ai and CRAWL4AI_AVAILABLE:
                return "crawl4ai"
            return "stealthy"
        if probe.is_static_html:
            return "static"
        # 默认尝试静态，失败会自动回退
        return "static"

    # ==================== 3. 各策略实现 ====================

    async def _fetch_api(self, url: str, timeout: int, auth_headers: Dict[str, str] = None) -> Tuple[Optional[Any], str]:
        """API 模式：直接请求 JSON/XML"""
        try:
            headers = self._get_enhanced_headers(url)
            if auth_headers:
                headers.update(auth_headers)
            
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                resp = await client.get(url, headers=headers)
                resp.raise_for_status()
                content_type = resp.headers.get("content-type", "").lower()

                if "json" in content_type:
                    return resp.json(), "json"
                elif "xml" in content_type:
                    return resp.text, "xml"
                else:
                    return resp.text, "text"
        except Exception as e:
            logger.warning(f"API 请求失败: {e}")
            return None, "error"

    async def _fetch_static(self, url: str, timeout: int, auth_headers: Dict[str, str] = None) -> Tuple[Optional[str], str]:
        """静态页面模式：httpx + BeautifulSoup"""
        try:
            headers = self._get_enhanced_headers(url)
            if auth_headers:
                headers.update(auth_headers)
            
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                resp = await client.get(url, headers=headers)
                resp.raise_for_status()
                return resp.text, "html"
        except Exception as e:
            logger.warning(f"静态请求失败: {e}")
            return None, "error"

    async def _fetch_stealthy(self, url: str, wait_for: str, auto_scroll: bool, timeout: int, auth_cookies: List[Dict] = None) -> Optional[str]:
        """隐身模式：Scrapling StealthyFetcher"""
        if not self.scrapling or not self.scrapling.available:
            logger.warning("Scrapling 不可用，跳过隐身模式")
            return None

        try:
            response = await self.scrapling.fetch_stealthy(
                url=url,
                wait_for=wait_for,
                auto_scroll=auto_scroll,
                headless=True,
                cookies=auth_cookies,
            )
            if response:
                return self.scrapling.get_page_html(response)
            return None
        except Exception as e:
            logger.warning(f"隐身模式失败: {e}")
            return None

    async def _fetch_crawl4ai(self, url: str, timeout: int, auth_cookies: List[Dict] = None) -> Optional[Dict[str, Any]]:
        """crawl4ai 模式：智能提取正文"""
        if not self.enable_crawl4ai or not CRAWL4AI_AVAILABLE:
            return None

        try:
            # 如果有认证 Cookie，先创建带 Cookie 的浏览器上下文
            if auth_cookies:
                from playwright.async_api import async_playwright
                async with async_playwright() as p:
                    browser = await p.chromium.launch(headless=True)
                    context = await browser.new_context()
                    await context.add_cookies(auth_cookies)
                    page = await context.new_page()
                    await page.goto(url, wait_until="networkidle", timeout=timeout*1000)
                    html = await page.content()
                    await browser.close()
                    return {
                        "html": html,
                        "markdown": "",
                        "links": [],
                        "media": [],
                        "metadata": {},
                    }
            else:
                async with AsyncWebCrawler() as crawler:
                    result = await crawler.arun(url=url)
                    return {
                        "markdown": result.markdown,
                        "html": getattr(result, "cleaned_html", None) or getattr(result, "html", ""),
                        "links": getattr(result, "links", []),
                        "media": getattr(result, "media", []),
                        "metadata": getattr(result, "metadata", {}),
                    }
        except Exception as e:
            logger.warning(f"crawl4ai 失败: {e}")
            return None

    async def _fetch_auto_fallback(self, url: str, timeout: int, auth_headers: Dict[str, str] = None) -> Optional[Any]:
        """自动回退策略"""
        # 1. 尝试 httpx
        content, ct = await self._fetch_static(url, timeout, auth_headers)
        if content:
            return content

        # 2. 尝试 Scrapling
        if self.scrapling and self.scrapling.available:
            content = await self._fetch_stealthy(url, None, False, timeout)
            if content:
                return content

        # 3. 尝试 crawl4ai
        if self.enable_crawl4ai:
            content = await self._fetch_crawl4ai(url, timeout)
            if content:
                return content

        return None

    # ==================== 4. 智能解析 ====================

    def _parse_content(
        self,
        raw_content: Any,
        content_type: str,
        selectors: Dict[str, str] = None,
        container_selector: str = None,
        item_selectors: Dict[str, str] = None,
    ) -> ParsedData:
        """
        智能解析内容

        优先级：
        1. 用户指定选择器 → 按选择器解析
        2. JSON 响应 → 直接提取
        3. HTML 页面 → 自动识别表格/列表/卡片
        4. crawl4ai 结果 → Markdown 解析
        """
        # 情况 1: crawl4ai 结果
        if isinstance(raw_content, dict) and "markdown" in raw_content:
            return self._parse_crawl4ai_result(raw_content)

        # 情况 2: JSON 响应
        if content_type == "json" or isinstance(raw_content, dict):
            return self._parse_json(raw_content)

        # 情况 3: HTML 页面
        if content_type == "html" or isinstance(raw_content, str):
            # 用户指定选择器
            if selectors or (container_selector and item_selectors):
                return self._parse_with_selectors(
                    raw_content, selectors, container_selector, item_selectors
                )
            # 自动识别
            return self._auto_parse_html(raw_content)

        # 情况 4: XML
        if content_type == "xml":
            return self._parse_xml(raw_content)

        # 默认：作为文本
        return ParsedData(
            data_type="text",
            data=[{"content": str(raw_content)[:5000]}],
            columns=["content"],
            total_count=1,
        )

    def _parse_json(self, data: Any) -> ParsedData:
        """解析 JSON 数据"""
        if isinstance(data, dict):
            # 尝试找到列表字段
            list_field = self._find_list_field(data)
            if list_field:
                items = data[list_field]
                if isinstance(items, list) and len(items) > 0:
                    columns = list(items[0].keys()) if isinstance(items[0], dict) else ["value"]
                    return ParsedData(
                        data_type="api_response",
                        data=items,
                        columns=columns,
                        total_count=len(items),
                    )
            # 单条记录
            return ParsedData(
                data_type="api_response",
                data=[data],
                columns=list(data.keys()),
                total_count=1,
            )
        elif isinstance(data, list):
            if len(data) > 0 and isinstance(data[0], dict):
                return ParsedData(
                    data_type="api_response",
                    data=data,
                    columns=list(data[0].keys()),
                    total_count=len(data),
                )
            return ParsedData(
                data_type="api_response",
                data=[{"value": item} for item in data],
                columns=["value"],
                total_count=len(data),
            )
        return ParsedData(data_type="api_response", data=[{"value": data}], columns=["value"], total_count=1)

    def _find_list_field(self, data: Dict) -> Optional[str]:
        """在 JSON 中找到最可能是数据列表的字段"""
        candidates = []
        for key, value in data.items():
            if isinstance(value, list) and len(value) > 0:
                # 优先选择名字像列表的字段
                score = len(value)
                if any(word in key.lower() for word in ["list", "data", "items", "result", "records", "rows"]):
                    score += 100
                candidates.append((key, score))

        if candidates:
            candidates.sort(key=lambda x: x[1], reverse=True)
            return candidates[0][0]
        return None

    def _parse_with_selectors(
        self,
        html: str,
        selectors: Dict[str, str] = None,
        container_selector: str = None,
        item_selectors: Dict[str, str] = None,
    ) -> ParsedData:
        """使用 CSS 选择器解析 HTML"""
        soup = BeautifulSoup(html, "lxml")

        if container_selector and item_selectors:
            # 列表模式
            containers = soup.select(container_selector)
            data = []
            for container in containers:
                item = {}
                for field, selector in item_selectors.items():
                    elem = container.select_one(selector)
                    item[field] = self._extract_text(elem) if elem else ""
                data.append(item)

            return ParsedData(
                data_type="list",
                data=data,
                columns=list(item_selectors.keys()),
                total_count=len(data),
            )

        elif selectors:
            # 字段模式
            data = {}
            for field, selector in selectors.items():
                elems = soup.select(selector)
                if len(elems) == 1:
                    data[field] = self._extract_text(elems[0])
                else:
                    data[field] = [self._extract_text(e) for e in elems]

            return ParsedData(
                data_type="dict",
                data=[data],
                columns=list(selectors.keys()),
                total_count=1,
            )

        return self._auto_parse_html(html)

    def _auto_parse_html(self, html: str) -> ParsedData:
        """自动解析 HTML，识别表格/列表/卡片"""
        soup = BeautifulSoup(html, "lxml")

        # 1. 优先找表格
        tables = soup.find_all("table")
        if tables:
            best_table = self._find_best_table(tables)
            if best_table:
                return self._parse_table(best_table)

        # 2. 找列表 (ul/ol > li)
        lists = soup.find_all(["ul", "ol"])
        for lst in lists:
            items = lst.find_all("li", recursive=False)
            if len(items) >= 3:
                return self._parse_list(items)

        # 3. 找卡片 (article/div with structured content)
        cards = soup.find_all(["article", "div"], class_=re.compile(r"card|item|post|product", re.I))
        if len(cards) >= 3:
            return self._parse_cards(cards)

        # 4. 提取文章正文
        article = self._extract_article(soup)
        if article:
            return ParsedData(
                data_type="article",
                data=[article],
                columns=["title", "content", "author", "date"],
                total_count=1,
            )

        # 5. 兜底：提取所有文本段落
        paragraphs = soup.find_all("p")
        texts = [p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 20]
        if texts:
            return ParsedData(
                data_type="text",
                data=[{"paragraph": t} for t in texts[:50]],
                columns=["paragraph"],
                total_count=len(texts),
            )

        # 最终兜底
        text = soup.get_text(separator="\n", strip=True)
        return ParsedData(
            data_type="text",
            data=[{"content": text[:5000]}],
            columns=["content"],
            total_count=1,
        )

    def _find_best_table(self, tables: List) -> Any:
        """找到最佳表格（数据最多的）"""
        best = None
        best_score = 0
        for table in tables:
            rows = table.find_all("tr")
            if len(rows) >= 2:
                score = len(rows)
                # 优先选择有 thead 的表格
                if table.find("thead"):
                    score += 10
                # 优先选择数据行多的
                data_rows = len([r for r in rows if r.find(["td"])])
                score += data_rows
                if score > best_score:
                    best_score = score
                    best = table
        return best

    def _parse_table(self, table) -> ParsedData:
        """解析 HTML 表格"""
        # 提取表头
        headers = []
        thead = table.find("thead")
        if thead:
            header_row = thead.find("tr")
            if header_row:
                headers = [th.get_text(strip=True) for th in header_row.find_all(["th", "td"])]

        if not headers:
            first_row = table.find("tr")
            if first_row:
                headers = [th.get_text(strip=True) for th in first_row.find_all(["th", "td"])]

        # 提取数据行
        rows = []
        tbody = table.find("tbody") or table
        for tr in tbody.find_all("tr"):
            cells = tr.find_all(["td", "th"])
            if len(cells) == 0:
                continue
            # 跳过表头行
            if tr.find("th") and not tr.find("td"):
                continue

            row = {}
            for i, cell in enumerate(cells):
                key = headers[i] if i < len(headers) else f"col_{i}"
                row[key] = self._extract_text(cell)
            rows.append(row)

        return ParsedData(
            data_type="table",
            data=rows,
            columns=headers or [f"col_{i}" for i in range(len(rows[0]) if rows else 0)],
            total_count=len(rows),
        )

    def _parse_list(self, items: List) -> ParsedData:
        """解析列表项"""
        data = []
        for item in items:
            text = item.get_text(separator=" ", strip=True)
            # 尝试提取链接
            links = item.find_all("a")
            link = links[0].get("href") if links else ""
            data.append({
                "text": text,
                "link": link,
            })

        return ParsedData(
            data_type="list",
            data=data,
            columns=["text", "link"],
            total_count=len(data),
        )

    def _parse_cards(self, cards: List) -> ParsedData:
        """解析卡片"""
        data = []
        for card in cards:
            item = {}
            # 尝试提取标题
            title = card.find(["h1", "h2", "h3", "h4", "h5", "h6", ".title", "[class*='title']"])
            item["title"] = title.get_text(strip=True) if title else ""
            # 尝试提取描述
            desc = card.find("p") or card.find(class_=re.compile(r"desc|summary|content", re.I))
            item["description"] = desc.get_text(strip=True) if desc else ""
            # 尝试提取链接
            link = card.find("a")
            item["link"] = link.get("href") if link else ""
            # 尝试提取图片
            img = card.find("img")
            item["image"] = img.get("src") if img else ""

            data.append(item)

        return ParsedData(
            data_type="cards",
            data=data,
            columns=["title", "description", "link", "image"],
            total_count=len(data),
        )

    def _extract_article(self, soup: BeautifulSoup) -> Optional[Dict]:
        """提取文章正文"""
        # 常见文章容器
        article_selectors = [
            "article",
            "[class*='article']",
            "[class*='post-content']",
            "[class*='entry-content']",
            "[class*='content-body']",
            "#content",
            ".content",
        ]

        article_elem = None
        for selector in article_selectors:
            article_elem = soup.select_one(selector)
            if article_elem:
                break

        if not article_elem:
            return None

        # 提取标题
        title = soup.find("h1") or soup.find("title")
        title_text = title.get_text(strip=True) if title else ""

        # 提取正文
        paragraphs = article_elem.find_all("p")
        content = "\n\n".join(p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 10)

        # 提取作者
        author = soup.find(class_=re.compile(r"author", re.I))
        author_text = author.get_text(strip=True) if author else ""

        # 提取日期
        date = soup.find("time") or soup.find(class_=re.compile(r"date|time", re.I))
        date_text = date.get_text(strip=True) if date else ""

        if len(content) < 100:
            return None

        return {
            "title": title_text,
            "content": content,
            "author": author_text,
            "date": date_text,
        }

    def _parse_crawl4ai_result(self, result: Dict) -> ParsedData:
        """解析 crawl4ai 结果"""
        markdown = result.get("markdown", "")
        # 尝试从 markdown 提取表格
        tables = self._extract_markdown_tables(markdown)
        if tables:
            return ParsedData(
                data_type="table",
                data=tables["data"],
                columns=tables["headers"],
                total_count=len(tables["data"]),
            )

        # 返回文章格式
        return ParsedData(
            data_type="article",
            data=[{
                "title": result.get("metadata", {}).get("title", ""),
                "content": markdown,
                "url": result.get("metadata", {}).get("url", ""),
            }],
            columns=["title", "content", "url"],
            total_count=1,
        )

    def _extract_markdown_tables(self, markdown: str) -> Optional[Dict]:
        """从 Markdown 提取表格"""
        lines = markdown.split("\n")
        tables = []
        current_table = []

        for line in lines:
            if "|" in line:
                current_table.append(line)
            else:
                if len(current_table) >= 3:
                    tables.append(current_table)
                current_table = []

        if len(current_table) >= 3:
            tables.append(current_table)

        if not tables:
            return None

        # 取最大的表格
        best = max(tables, key=len)
        headers = [h.strip() for h in best[0].split("|") if h.strip()]
        data = []
        for row in best[2:]:  # 跳过表头和分隔线
            cells = [c.strip() for c in row.split("|") if c.strip() or c == ""]
            if len(cells) >= len(headers):
                row_dict = {}
                for i, h in enumerate(headers):
                    row_dict[h] = cells[i] if i < len(cells) else ""
                data.append(row_dict)

        return {"headers": headers, "data": data}

    def _parse_xml(self, xml_str: str) -> ParsedData:
        """解析 XML"""
        soup = BeautifulSoup(xml_str, "xml")
        # 提取所有子元素
        root = soup.find()
        if root:
            items = []
            for child in root.find_all(recursive=False):
                item = {}
                for sub in child.find_all(recursive=False):
                    item[sub.name] = sub.get_text(strip=True)
                if item:
                    items.append(item)

            if items:
                columns = list(items[0].keys())
                return ParsedData(
                    data_type="xml",
                    data=items,
                    columns=columns,
                    total_count=len(items),
                )

        return ParsedData(
            data_type="xml",
            data=[{"content": xml_str[:5000]}],
            columns=["content"],
            total_count=1,
        )

    def _extract_text(self, elem) -> str:
        """提取元素文本"""
        if elem is None:
            return ""
        # 优先获取文本内容
        text = elem.get_text(separator=" ", strip=True)
        if text:
            return text
        # 获取属性
        for attr in ["title", "alt", "value", "data-value"]:
            val = elem.get(attr)
            if val:
                return val
        return ""

    # ==================== 5. 数据质量校验 ====================

    def _check_data_quality(self, parsed: ParsedData) -> Dict[str, Any]:
        """
        检查数据质量

        评分维度：
        - 完整性：非空字段比例
        - 一致性：数据类型一致性
        - 丰富度：字段数量
        """
        if not parsed.data:
            return {"score": 0.0, "issues": ["无数据"]}

        issues = []
        total_cells = 0
        filled_cells = 0

        for row in parsed.data:
            for key, value in row.items():
                total_cells += 1
                if value is not None and str(value).strip():
                    filled_cells += 1

        completeness = filled_cells / max(total_cells, 1)

        # 检查是否有足够的数据
        if parsed.total_count < 1:
            issues.append("数据量为空")
        elif parsed.total_count < 3 and parsed.data_type in ["table", "list", "cards"]:
            issues.append("数据量较少")

        # 检查字段丰富度
        if len(parsed.columns) < 2 and parsed.total_count > 1:
            issues.append("字段较少")

        # 综合评分
        score = completeness
        if parsed.total_count >= 10:
            score = min(1.0, score + 0.1)
        if len(parsed.columns) >= 3:
            score = min(1.0, score + 0.1)

        return {
            "score": score,
            "completeness": completeness,
            "total_cells": total_cells,
            "filled_cells": filled_cells,
            "issues": issues,
        }

    # ==================== 6. 批量爬取 ====================

    async def crawl_urls(
        self,
        urls: List[str],
        concurrency: int = 3,
        **kwargs,
    ) -> List[CrawlResult]:
        """批量爬取多个 URL"""
        semaphore = asyncio.Semaphore(concurrency)

        async def _crawl_one(url: str) -> CrawlResult:
            async with semaphore:
                return await self.crawl_url(url, **kwargs)

        tasks = [_crawl_one(url) for url in urls]
        return await asyncio.gather(*tasks)

    # ==================== 7. 兼容基类接口 ====================

    async def crawl(self, **kwargs) -> CrawlResult:
        """兼容 BaseCrawler 接口"""
        url = kwargs.get("url")
        if not url:
            return CrawlResult(
                success=False,
                data=[],
                message="缺少 URL 参数",
                source="url_crawler",
                error="Missing url parameter",
            )
        return await self.crawl_url(url, **kwargs)
