"""
站点探测 · 结构识别层
=====================

从 HTML 中识别：站点元信息、列表页模式、详情页模式、分页方式、保护状态。

全部基于**页面自身的可见证据**判断，不做任何对抗性绕过；识别到验证码、
付费墙、登录墙时如实记录，交给合规判定层决定后续动作。
"""
from __future__ import annotations

import logging
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import parse_qs, urljoin, urlparse

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# 分页参数的常见命名，按优先级排列
PAGINATION_PARAMS = ("page", "p", "pn", "pagenum", "page_no", "offset", "start", "paged")

# 站点类型关键词 → 类型标签
SITE_TYPE_HINTS: dict[str, tuple[str, ...]] = {
    "news": ("article", "news", "post", "报道", "新闻", "资讯"),
    "ecommerce": ("product", "item", "goods", "shop", "价格", "购买", "加入购物车"),
    "forum": ("thread", "topic", "forum", "bbs", "帖子", "回复", "楼层"),
    "doc": ("docs", "documentation", "manual", "api-reference", "文档", "手册"),
    "academic": ("paper", "journal", "citation", "doi", "论文", "期刊"),
    "government": ("gov", "政务", "公示", "通知公告", "policy"),
    "social": ("profile", "timeline", "feed", "follow", "动态"),
    "blog": ("blog", "archive", "category", "标签", "归档"),
}

PROTECTION_SIGNATURES: tuple[tuple[str, str, bool], ...] = (
    ("captcha", "recaptcha", False),
    ("captcha", "hcaptcha", False),
    ("captcha", "cf-turnstile", False),
    ("captcha", "g-recaptcha", False),
    ("captcha", "验证码", False),
    ("captcha", "人机验证", False),
    ("cloudflare", "cf-browser-verification", False),
    ("cloudflare", "checking your browser", False),
    ("cloudflare", "just a moment", False),
    ("cloudflare", "cf_chl_opt", False),
    ("paywall", "paywall", False),
    ("paywall", "subscribe to continue", False),
    ("paywall", "订阅后继续", False),
    ("paywall", "开通会员", False),
    ("login_wall", "sign in to continue", True),
    ("login_wall", "please log in", True),
    ("login_wall", "请先登录", True),
    ("login_wall", "登录后查看", True),
)


@dataclass
class SiteMeta:
    """站点元信息。"""

    title: str = ""
    description: str = ""
    lang: str = ""
    site_type: str = "other"
    type_evidence: list[str] = field(default_factory=list)
    tech_stack: list[str] = field(default_factory=list)
    canonical: str = ""


@dataclass
class ListPattern:
    """列表页结构。"""

    item_selector: str = ""
    container_selector: str = ""
    item_count: int = 0
    sample_links: list[str] = field(default_factory=list)
    confidence: float = 0.0


@dataclass
class PaginationInfo:
    """分页方式。"""

    mode: str = "none"  # none | param | next_link | cursor | scroll
    param: Optional[str] = None
    sample_next: Optional[str] = None
    evidence: str = ""


@dataclass
class ProtectionInfo:
    """访问保护状态。"""

    kind: str = "none"  # none | captcha | cloudflare | paywall | login_wall | forbidden
    evidence: str = ""
    requires_credentials: bool = False

    @property
    def blocked(self) -> bool:
        return self.kind != "none"


@dataclass
class StructureInfo:
    """结构识别的汇总结果。"""

    meta: SiteMeta = field(default_factory=SiteMeta)
    list_pattern: ListPattern = field(default_factory=ListPattern)
    pagination: PaginationInfo = field(default_factory=PaginationInfo)
    protection: ProtectionInfo = field(default_factory=ProtectionInfo)
    detail_candidate: Optional[str] = None
    headings: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# 站点元信息
# --------------------------------------------------------------------------- #


def extract_site_meta(html: str, url: str, soup: Optional[BeautifulSoup] = None) -> SiteMeta:
    """抽取标题、描述、语言、类型与技术栈指纹。"""
    soup = soup or BeautifulSoup(html, "lxml")
    meta = SiteMeta()

    if soup.title and soup.title.string:
        meta.title = soup.title.string.strip()[:300]

    for name in ("description", "og:description"):
        tag = soup.find("meta", attrs={"name": name}) or soup.find(
            "meta", attrs={"property": name}
        )
        if tag and tag.get("content"):
            meta.description = tag["content"].strip()[:500]
            break

    html_tag = soup.find("html")
    if html_tag and html_tag.get("lang"):
        meta.lang = html_tag["lang"][:20]

    canonical = soup.find("link", rel=lambda v: v and "canonical" in v)
    if canonical and canonical.get("href"):
        meta.canonical = urljoin(url, canonical["href"])

    meta.tech_stack = detect_tech_stack(html, soup)
    meta.site_type, meta.type_evidence = classify_site_type(html, url, soup)
    return meta


def detect_tech_stack(html: str, soup: Optional[BeautifulSoup] = None) -> list[str]:
    """基于公开特征识别技术栈（不做任何探测性攻击）。"""
    soup = soup or BeautifulSoup(html, "lxml")
    found: list[str] = []
    lowered = html.lower()

    generator = soup.find("meta", attrs={"name": "generator"})
    if generator and generator.get("content"):
        found.append(generator["content"].strip()[:80])

    signatures = {
        "wordpress": ("wp-content", "wp-includes"),
        "next.js": ("__next_f", "_next/static"),
        "nuxt": ("__nuxt__", "_nuxt/"),
        "react": ("data-reactroot", "react-dom"),
        "vue": ("data-v-", "__vue__"),
        "shopify": ("cdn.shopify.com", "shopify"),
        "drupal": ("drupal.js", "sites/default/files"),
        "jquery": ("jquery.min.js", "jquery-"),
        "bootstrap": ("bootstrap.min.css", "bootstrap.min.js"),
        "tailwind": ("tailwind",),
        "cloudflare": ("cdnjs.cloudflare.com", "__cf_bm"),
    }
    for name, tokens in signatures.items():
        if any(token in lowered for token in tokens):
            found.append(name)

    return sorted(set(found))


def classify_site_type(
    html: str, url: str, soup: Optional[BeautifulSoup] = None
) -> tuple[str, list[str]]:
    """基于证据给站点类型打分。返回 (类型, 证据列表)。"""
    soup = soup or BeautifulSoup(html, "lxml")
    path = urlparse(url).path.lower()
    lowered = html.lower()
    scores: Counter[str] = Counter()
    evidence: list[str] = []

    # 结构化数据是最强证据
    for script in soup.find_all("script", type="application/ld+json"):
        payload = (script.string or "")[:4000].lower()
        for ld_type, site_type in (
            ("article", "news"),
            ("newsarticle", "news"),
            ("blogposting", "blog"),
            ("product", "ecommerce"),
            ("offer", "ecommerce"),
            ("discussionforumposting", "forum"),
            ("scholarlyarticle", "academic"),
            ("techarticle", "doc"),
        ):
            if f'"@type":"{ld_type}"' in payload.replace(" ", "") or (
                f'"@type": "{ld_type}"' in payload
            ):
                scores[site_type] += 3
                evidence.append(f"JSON-LD:{ld_type}")

    # URL 路径证据
    for site_type, tokens in SITE_TYPE_HINTS.items():
        for token in tokens:
            if token in path:
                scores[site_type] += 2
                evidence.append(f"path:{token}")

    # 页面文本证据（弱）
    text_head = lowered[:60000]
    for site_type, tokens in SITE_TYPE_HINTS.items():
        for token in tokens:
            if token in text_head and not token.isascii():
                scores[site_type] += 1
                evidence.append(f"text:{token}")

    if not scores:
        return "other", []
    best, _ = scores.most_common(1)[0]
    return best, evidence[:6]


# --------------------------------------------------------------------------- #
# 列表页结构
# --------------------------------------------------------------------------- #


def detect_list_pattern(
    html: str, base_url: str, soup: Optional[BeautifulSoup] = None
) -> ListPattern:
    """识别列表页：找出重复出现的条目容器。

    做法：统计「标签路径 + class 组合」的重复次数，重复次数最多且内部含链接的
    结构判为列表条目。
    """
    soup = soup or BeautifulSoup(html, "lxml")
    signature_map: dict[str, list] = {}

    for node in soup.find_all(["li", "article", "div", "tr", "section"]):
        classes = node.get("class") or []
        if not classes:
            continue
        # 结构签名：标签 + 排序后的 class（去掉带数字的哈希类）
        stable = sorted(c for c in classes if not re.search(r"\d{3,}", c))
        if not stable:
            continue
        signature = f"{node.name}." + ".".join(stable[:3])
        signature_map.setdefault(signature, []).append(node)

    best_sig = ""
    best_nodes: list = []
    for signature, nodes in signature_map.items():
        if len(nodes) < 3:
            continue
        if len(nodes) > len(best_nodes):
            # 要求条目内部确实带链接，否则可能只是样式块
            linked = [n for n in nodes if n.find("a", href=True)]
            if len(linked) >= 3:
                best_sig = signature
                best_nodes = linked

    pattern = ListPattern()
    if not best_nodes:
        return pattern

    links: list[str] = []
    for node in best_nodes[:20]:
        anchor = node.find("a", href=True)
        if anchor:
            links.append(urljoin(base_url, anchor["href"]))

    pattern.item_selector = best_sig
    pattern.item_count = len(best_nodes)
    pattern.sample_links = links[:10]
    # 条目数越多、链接越完整，置信度越高
    pattern.confidence = min(1.0, len(best_nodes) / 20.0) * (
        0.6 + 0.4 * min(1.0, len(links) / max(1, len(best_nodes)))
    )
    return pattern


def pick_detail_candidate(pattern: ListPattern) -> Optional[str]:
    """从列表样本中挑一条最像详情页的链接。"""
    if not pattern.sample_links:
        return None
    # 跳过明显的导航/分类链接
    noise = ("category", "tag", "author", "login", "register", "javascript:", "#")
    for link in pattern.sample_links:
        lowered = link.lower()
        if any(token in lowered for token in noise):
            continue
        if len(urlparse(link).path.strip("/").split("/")) >= 1:
            return link
    return pattern.sample_links[0]


# --------------------------------------------------------------------------- #
# 分页
# --------------------------------------------------------------------------- #


def detect_pagination(
    html: str, base_url: str, soup: Optional[BeautifulSoup] = None
) -> PaginationInfo:
    """识别分页方式：URL 参数 / rel=next / 游标 / 滚动加载。"""
    soup = soup or BeautifulSoup(html, "lxml")

    # 1. <link rel="next"> 或 <a rel="next">
    rel_next = soup.find("link", rel=lambda v: v and "next" in v) or soup.find(
        "a", rel=lambda v: v and "next" in v
    )
    if rel_next and rel_next.get("href"):
        return PaginationInfo(
            mode="next_link",
            sample_next=urljoin(base_url, rel_next["href"]),
            evidence="rel=next",
        )

    # 2. 分页参数：检查页面内链接是否带 page 类参数
    for anchor in soup.find_all("a", href=True)[:400]:
        href = anchor["href"]
        if not href or href.startswith(("javascript:", "#")):
            continue
        query = parse_qs(urlparse(urljoin(base_url, href)).query)
        for param in PAGINATION_PARAMS:
            if param in query:
                return PaginationInfo(
                    mode="param",
                    param=param,
                    sample_next=urljoin(base_url, href),
                    evidence=f"query param '{param}'",
                )

    # 3. 文本锚点："下一页" / "next" / ">"
    for anchor in soup.find_all("a", href=True):
        text = (anchor.get_text() or "").strip().lower()
        if text in ("下一页", "下页", "next", "next page", "»", ">"):
            return PaginationInfo(
                mode="next_link",
                sample_next=urljoin(base_url, anchor["href"]),
                evidence=f"anchor text '{text}'",
            )

    # 4. 滚动加载 / 游标线索（弱证据）
    lowered = html.lower()
    if any(token in lowered for token in ("infinite-scroll", "无限滚动", "load more", "加载更多")):
        return PaginationInfo(mode="scroll", evidence="infinite scroll marker")

    return PaginationInfo(mode="none")


# --------------------------------------------------------------------------- #
# 保护状态
# --------------------------------------------------------------------------- #


def detect_protection(
    html: str,
    status: int = 200,
    headers: Optional[dict[str, str]] = None,
) -> ProtectionInfo:
    """判定页面是否处于访问保护之下。

    识别到保护时如实标记，不做任何绕过尝试。
    """
    headers = {k.lower(): v for k, v in (headers or {}).items()}

    if status in (401, 407):
        return ProtectionInfo(
            kind="login_wall",
            evidence=f"HTTP {status}",
            requires_credentials=True,
        )
    if status == 403:
        server = headers.get("server", "")
        kind = "cloudflare" if "cloudflare" in server.lower() else "forbidden"
        return ProtectionInfo(kind=kind, evidence=f"HTTP 403 (server={server or 'n/a'})")

    if "www-authenticate" in headers:
        return ProtectionInfo(
            kind="login_wall",
            evidence="WWW-Authenticate header",
            requires_credentials=True,
        )

    lowered = html.lower()
    # Cloudflare 挑战页通常极短且带特定标记，优先级高于普通关键词
    for kind, token, needs_cred in PROTECTION_SIGNATURES:
        if token in lowered:
            # 采样命中可能来自第三方脚本（如页脚引用了 recaptcha），
            # 因此对 captcha 类要求页面规模较小或在表单内
            if kind == "captcha" and len(html) > 200_000:
                continue
            return ProtectionInfo(
                kind=kind,
                evidence=f"marker '{token}'",
                requires_credentials=needs_cred,
            )

    return ProtectionInfo()


# --------------------------------------------------------------------------- #
# 汇总
# --------------------------------------------------------------------------- #


def analyze_structure(
    html: str,
    url: str,
    status: int = 200,
    headers: Optional[dict[str, str]] = None,
) -> StructureInfo:
    """一次性完成结构识别的全部步骤。"""
    soup = BeautifulSoup(html, "lxml")
    info = StructureInfo()
    info.meta = extract_site_meta(html, url, soup)
    info.protection = detect_protection(html, status, headers)

    if info.protection.blocked:
        # 处于保护状态时不再做结构推断，避免对挑战页做无意义分析
        return info

    info.list_pattern = detect_list_pattern(html, url, soup)
    info.pagination = detect_pagination(html, url, soup)
    info.detail_candidate = pick_detail_candidate(info.list_pattern)

    headings = [
        h.get_text(strip=True)[:120]
        for h in soup.find_all(["h1", "h2"])[:8]
        if h.get_text(strip=True)
    ]
    info.headings = headings
    return info
