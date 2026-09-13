"""
站点探测 · 字段发现层
=====================

从页面中提取结构化数据，并推断「这个站点能采到哪些字段」。

提取优先级（确定性从高到低）：

    JSON-LD  →  microdata  →  OpenGraph  →  meta  →  语义化 DOM  →  通用容器猜测

多页样本合并时计算字段覆盖率：某字段在 N 个样本中命中 M 次，覆盖率 = M/N。
覆盖率是调用方判断"这个字段值不值得采"的依据。
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

MAX_SAMPLES = 5

# 常见字段的候选定位规则，按优先级排列： (来源, 定位表达式)
TITLE_RULES: tuple[tuple[str, str], ...] = (
    ("json-ld", "$.headline"),
    ("opengraph", "meta[property='og:title']"),
    ("meta", "meta[name='twitter:title']"),
    ("css", "h1"),
    ("css", "title"),
)

DATE_RULES: tuple[tuple[str, str], ...] = (
    ("json-ld", "$.datePublished"),
    ("meta", "meta[property='article:published_time']"),
    ("meta", "meta[name='pubdate']"),
    ("css", "time[datetime]"),
    ("css", "time"),
)

AUTHOR_RULES: tuple[tuple[str, str], ...] = (
    ("json-ld", "$.author.name"),
    ("meta", "meta[name='author']"),
    ("css", "[rel='author']"),
    ("css", ".author"),
    ("css", ".byline"),
)

CONTENT_RULES: tuple[tuple[str, str], ...] = (
    ("css", "article"),
    ("css", "main"),
    ("css", "[role='main']"),
    ("css", ".article-content"),
    ("css", ".post-content"),
    ("css", ".content"),
    ("css", "#content"),
)

PRICE_RULES: tuple[tuple[str, str], ...] = (
    ("json-ld", "$.offers.price"),
    ("meta", "meta[property='product:price:amount']"),
    ("css", "[itemprop='price']"),
    ("css", ".price"),
    ("css", ".product-price"),
)


@dataclass
class FieldSpec:
    """一个可采字段的描述。"""

    name: str
    path: str
    source: str
    type: str = "text"
    sample: Any = None
    coverage: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class StructuredPayload:
    """从页面提取到的一块结构化数据。"""

    kind: str  # json-ld | microdata | opengraph
    data: dict

    def to_dict(self) -> dict:
        return {"kind": self.kind, "data": self.data}


# --------------------------------------------------------------------------- #
# 结构化数据提取
# --------------------------------------------------------------------------- #


def extract_json_ld(soup: BeautifulSoup) -> list[StructuredPayload]:
    """提取 JSON-LD 块。解析失败的块跳过并记录。"""
    out: list[StructuredPayload] = []
    for script in soup.find_all("script", type="application/ld+json"):
        raw = script.string or script.get_text() or ""
        raw = raw.strip()
        if not raw:
            continue
        try:
            parsed = json.loads(raw)
        except (json.JSONDecodeError, ValueError) as exc:
            logger.debug("JSON-LD 解析失败: %s", str(exc)[:80])
            continue

        # 可能是数组，或 {"@graph": [...]}
        items: list[Any] = []
        if isinstance(parsed, list):
            items = parsed
        elif isinstance(parsed, dict):
            graph = parsed.get("@graph")
            items = graph if isinstance(graph, list) else [parsed]

        for item in items:
            if isinstance(item, dict):
                out.append(StructuredPayload(kind="json-ld", data=item))
    return out


def extract_opengraph(soup: BeautifulSoup) -> Optional[StructuredPayload]:
    """提取 OpenGraph / Twitter Card 元数据。"""
    data: dict[str, str] = {}
    for tag in soup.find_all("meta"):
        prop = tag.get("property") or tag.get("name") or ""
        content = tag.get("content")
        if not content:
            continue
        if prop.startswith("og:") or prop.startswith("twitter:"):
            data[prop] = content.strip()[:600]
    return StructuredPayload(kind="opengraph", data=data) if data else None


def extract_microdata(soup: BeautifulSoup) -> list[StructuredPayload]:
    """从 itemprop 标记中提取基础 microdata。"""
    out: list[StructuredPayload] = []
    items = soup.find_all(attrs={"itemscope": True})
    for item in items[:5]:
        props: dict[str, str] = {}
        for prop in item.find_all(attrs={"itemprop": True}):
            key = prop.get("itemprop")
            value = prop.get("content") or prop.get("datetime") or prop.get_text(strip=True)
            if key and value and key not in props:
                props[key] = value[:400]
        if props:
            props["@type"] = item.get("itemtype", "unknown")
            out.append(StructuredPayload(kind="microdata", data=props))
    return out


def extract_all_structured(html: str) -> list[StructuredPayload]:
    """按优先级返回页面上所有结构化数据块。"""
    soup = BeautifulSoup(html, "lxml")
    payloads: list[StructuredPayload] = []
    payloads.extend(extract_json_ld(soup))
    og = extract_opengraph(soup)
    if og:
        payloads.append(og)
    payloads.extend(extract_microdata(soup))
    return payloads


# --------------------------------------------------------------------------- #
# 字段定位
# --------------------------------------------------------------------------- #


def _from_jsonld(payloads: list[StructuredPayload], path: str) -> Any:
    """按 $.a.b 形式的路径在 JSON-LD 中取值。"""
    if not path.startswith("$."):
        return None
    keys = path[2:].split(".")
    for payload in payloads:
        if payload.kind != "json-ld":
            continue
        node: Any = payload.data
        for key in keys:
            if isinstance(node, dict) and key in node:
                node = node[key]
            elif isinstance(node, list) and node and isinstance(node[0], dict):
                node = node[0].get(key)
            else:
                node = None
                break
        if node not in (None, "", [], {}):
            if isinstance(node, dict):
                return node.get("name") or node.get("@id") or str(node)[:200]
            return node
    return None


def _from_selector(soup: BeautifulSoup, selector: str, base_url: str) -> Any:
    """用 CSS 选择器或 meta 规则取值。"""
    if selector.startswith("meta["):
        match = re.search(r"\[(?:property|name)='([^']+)'\]", selector)
        if not match:
            return None
        key = match.group(1)
        tag = soup.find("meta", attrs={"property": key}) or soup.find(
            "meta", attrs={"name": key}
        )
        return (tag.get("content") or "").strip()[:600] if tag and tag.get("content") else None

    try:
        node = soup.select_one(selector)
    except Exception:  # noqa: BLE001 - 非法选择器不应中断探测
        return None
    if node is None:
        return None

    if node.name == "time" and node.get("datetime"):
        return node["datetime"].strip()
    if node.name == "a" and node.get("href"):
        return urljoin(base_url, node["href"])
    text = node.get_text(" ", strip=True)
    return text[:2000] if text else None


def _infer_type(value: Any) -> str:
    if value is None:
        return "text"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, (int, float)):
        return "float" if isinstance(value, float) else "int"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "json"

    text = str(value).strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}([T ]\d{2}:\d{2}(:\d{2})?)?.*", text):
        return "datetime"
    if re.fullmatch(r"-?\d+", text):
        return "int"
    if re.fullmatch(r"-?\d+\.\d+", text):
        return "float"
    if re.fullmatch(r"https?://\S+", text):
        return "url"
    return "text"


def _resolve_rule(
    rule: tuple[str, str],
    payloads: list[StructuredPayload],
    soup: BeautifulSoup,
    base_url: str,
) -> Any:
    source, expr = rule
    if source == "json-ld":
        return _from_jsonld(payloads, expr)
    if source in ("opengraph", "meta"):
        return _from_selector(soup, expr, base_url)
    if source == "css":
        return _from_selector(soup, expr, base_url)
    return None


def extract_fields_from_page(html: str, url: str) -> list[FieldSpec]:
    """从单个页面提取常见字段。

    返回仅包含**命中**的字段；未命中的字段不进入结果，
    覆盖率在多样本合并时计算。
    """
    soup = BeautifulSoup(html, "lxml")
    payloads = extract_all_structured(html)
    found: list[FieldSpec] = []

    groups: tuple[tuple[str, tuple[tuple[str, str], ...]], ...] = (
        ("title", TITLE_RULES),
        ("publish_date", DATE_RULES),
        ("author", AUTHOR_RULES),
        ("content", CONTENT_RULES),
        ("price", PRICE_RULES),
    )

    for name, rules in groups:
        for rule in rules:
            value = _resolve_rule(rule, payloads, soup, url)
            if value in (None, "", [], {}):
                continue
            text = str(value)
            # 过滤明显无意义的值
            if name == "content" and len(text) < 80:
                continue
            found.append(
                FieldSpec(
                    name=name,
                    path=f"{rule[0]}:{rule[1]}",
                    source=rule[0],
                    type=_infer_type(value),
                    sample=text[:300],
                    coverage=1.0,
                )
            )
            break  # 每个字段取优先级最高的一条

    # 附加：JSON-LD 中其余可用的标量字段
    for payload in payloads:
        if payload.kind != "json-ld":
            continue
        for key, value in list(payload.data.items())[:12]:
            if key.startswith("@") or isinstance(value, (dict, list)):
                continue
            if any(f.name == key for f in found):
                continue
            text = str(value)
            if not text or len(text) > 400:
                continue
            found.append(
                FieldSpec(
                    name=key,
                    path=f"json-ld:$.{key}",
                    source="json-ld",
                    type=_infer_type(value),
                    sample=text[:300],
                    coverage=1.0,
                )
            )

    return found


def merge_field_coverage(
    per_page_fields: list[list[FieldSpec]],
) -> list[FieldSpec]:
    """合并多页样本的字段，计算覆盖率并按覆盖率降序返回。"""
    if not per_page_fields:
        return []

    total = len(per_page_fields)
    merged: dict[str, FieldSpec] = {}
    hits: dict[str, int] = {}

    for fields in per_page_fields:
        seen = set()
        for spec in fields:
            key = spec.name
            if key in seen:
                continue
            seen.add(key)
            hits[key] = hits.get(key, 0) + 1
            existing = merged.get(key)
            # 优先保留来源确定性更高、样本更长的记录
            if existing is None or _source_rank(spec.source) < _source_rank(
                existing.source
            ):
                merged[key] = spec

    result: list[FieldSpec] = []
    for key, spec in merged.items():
        spec.coverage = round(hits[key] / total, 4)
        result.append(spec)

    result.sort(key=lambda s: (-s.coverage, s.name))
    return result


def _source_rank(source: str) -> int:
    return {
        "json-ld": 0,
        "microdata": 1,
        "opengraph": 2,
        "meta": 3,
        "css": 4,
    }.get(source, 9)
