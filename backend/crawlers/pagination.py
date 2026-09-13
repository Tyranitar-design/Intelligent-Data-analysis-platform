# -*- coding: utf-8 -*-
"""
分页识别与自动翻页模块 - Phase 4.5

功能：
1. 自动识别常见分页模式
2. URL 模板生成（翻页链接）
3. 分页参数提取
"""
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse


@dataclass
class PaginationPattern:
    """分页模式"""
    pattern_type: str  # "query_param", "path_segment", "offset"
    param_name: str    # 参数名，如 "page", "offset"
    current_page: int
    page_size: int
    total_pages: Optional[int] = None
    total_items: Optional[int] = None
    has_next: bool = True
    next_url: Optional[str] = None


# 常见分页模式正则
PAGINATION_PATTERNS = [
    # ?page=1, ?page=2
    {"type": "query_param", "param": "page", "regex": r"[?&]page=(\d+)"},
    # ?p=1, ?p=2
    {"type": "query_param", "param": "p", "regex": r"[?&]p=(\d+)"},
    # ?offset=0, ?offset=20
    {"type": "query_param", "param": "offset", "regex": r"[?&]offset=(\d+)"},
    # ?start=0, ?start=20
    {"type": "query_param", "param": "start", "regex": r"[?&]start=(\d+)"},
    # ?pn=1, ?pn=2 (百度)
    {"type": "query_param", "param": "pn", "regex": r"[?&]pn=(\d+)"},
    # ?cursor=xxx
    {"type": "query_param", "param": "cursor", "regex": r"[?&]cursor=([^&]+)"},
    # /page/1, /page/2
    {"type": "path_segment", "param": "page", "regex": r"/page/(\d+)"},
    # /p/1, /p/2
    {"type": "path_segment", "param": "p", "regex": r"/p/(\d+)"},
    # /list_1.html, /list_2.html
    {"type": "path_segment", "param": "list", "regex": r"/list_(\d+)\.html?"},
]


def detect_pagination(url: str) -> Optional[PaginationPattern]:
    """
    检测 URL 中的分页模式

    Args:
        url: 页面 URL

    Returns:
        PaginationPattern 或 None
    """
    for pattern in PAGINATION_PATTERNS:
        regex = pattern["regex"]
        match = re.search(regex, url)
        if match:
            current_value = match.group(1)
            try:
                current_page = int(current_value)
            except ValueError:
                # cursor 模式
                return PaginationPattern(
                    pattern_type=pattern["type"],
                    param_name=pattern["param"],
                    current_page=1,
                    page_size=20,
                    has_next=True,
                )

            return PaginationPattern(
                pattern_type=pattern["type"],
                param_name=pattern["param"],
                current_page=current_page,
                page_size=20,  # 默认值
                has_next=True,
            )

    # 没有检测到分页参数，可能是第 1 页
    return PaginationPattern(
        pattern_type="query_param",
        param_name="page",
        current_page=1,
        page_size=20,
        has_next=True,
    )


def generate_page_url(base_url: str, pattern: PaginationPattern, page: int) -> str:
    """
    生成指定页码的 URL

    Args:
        base_url: 基础 URL
        pattern: 分页模式
        page: 目标页码

    Returns:
        翻页后的 URL
    """
    if pattern.pattern_type == "query_param":
        return _set_query_param(base_url, pattern.param_name, page)
    elif pattern.pattern_type == "path_segment":
        return _set_path_segment(base_url, pattern.param_name, page)
    return base_url


def _set_query_param(url: str, param: str, value) -> str:
    """设置 URL 查询参数"""
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    query[param] = [str(value)]
    new_query = urlencode(query, doseq=True)
    return urlunparse(parsed._replace(query=new_query))


def _set_path_segment(url: str, param: str, page: int) -> str:
    """设置 URL 路径中的分页段"""
    # 先尝试替换现有分页
    for pattern in PAGINATION_PATTERNS:
        if pattern["type"] == "path_segment" and pattern["param"] == param:
            regex = pattern["regex"]
            if re.search(regex, url):
                # 替换数字部分
                def replace_page(match):
                    full = match.group(0)
                    num = match.group(1)
                    return full.replace(num, str(page))
                return re.sub(regex, replace_page, url)

    # 没有现有分页，追加到路径
    if url.endswith("/"):
        return f"{url}{param}/{page}"
    return f"{url}/{param}/{page}"


def generate_page_urls(base_url: str, start_page: int = 1, end_page: int = 10) -> List[str]:
    """
    生成一系列翻页 URL

    Args:
        base_url: 第 1 页 URL
        start_page: 起始页码
        end_page: 结束页码

    Returns:
        URL 列表
    """
    pattern = detect_pagination(base_url)
    urls = []

    for page in range(start_page, end_page + 1):
        url = generate_page_url(base_url, pattern, page)
        urls.append(url)

    return urls


def extract_pagination_info(html: str, base_url: str) -> Dict:
    """
    从 HTML 中提取分页信息（总页数、当前页等）

    Args:
        html: 页面 HTML
        base_url: 页面 URL

    Returns:
        分页信息字典
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "lxml")
    info = {
        "current_page": 1,
        "total_pages": None,
        "total_items": None,
        "has_next": False,
        "has_prev": False,
        "next_url": None,
        "prev_url": None,
    }

    # 1. 查找分页导航元素
    pagination_selectors = [
        ".pagination",
        ".page-nav",
        ".pager",
        ".pages",
        "[class*='pagination']",
        "[class*='page-nav']",
        "nav[aria-label*='page']",
    ]

    pagination_elem = None
    for selector in pagination_selectors:
        pagination_elem = soup.select_one(selector)
        if pagination_elem:
            break

    if pagination_elem:
        # 查找当前页
        current = pagination_elem.find("a", class_=re.compile(r"active|current|selected", re.I))
        if current:
            try:
                info["current_page"] = int(current.get_text(strip=True))
            except ValueError:
                pass

        # 查找下一页链接
        next_link = pagination_elem.find("a", text=re.compile(r"下一页|next|›|»", re.I))
        if next_link:
            info["has_next"] = True
            info["next_url"] = next_link.get("href")

        # 查找上一页链接
        prev_link = pagination_elem.find("a", text=re.compile(r"上一页|prev|‹|«", re.I))
        if prev_link:
            info["has_prev"] = True
            info["prev_url"] = prev_link.get("href")

        # 查找总页数
        page_links = pagination_elem.find_all("a")
        page_numbers = []
        for link in page_links:
            text = link.get_text(strip=True)
            try:
                num = int(text)
                if 1 <= num <= 10000:
                    page_numbers.append(num)
            except ValueError:
                pass

        if page_numbers:
            info["total_pages"] = max(page_numbers)

    # 2. 从页面文本中提取总数量
    text = soup.get_text()
    total_patterns = [
        r"共\s*(\d+)\s*条",
        r"共\s*(\d+)\s*页",
        r"total\s*[:：]\s*(\d+)",
        r"(\d+)\s*results?",
        r"(\d+)\s*items?",
    ]
    for pattern in total_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            info["total_items"] = int(match.group(1))
            break

    return info
