"""
能力 · RSS / Atom 订阅（L1）
============================

站点主动公开的结构化通道，是优先级最高的采集路径：
无需解析 DOM、无需渲染、字段由发布方保证语义。

覆盖 RSS 2.0 与 Atom 两种格式，解析用标准库 ``xml.etree``，不引入额外依赖。
"""
from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from typing import Optional

from collect.registry import (
    Capability,
    CapabilityLayer,
    CollectRequest,
    CollectResult,
    CostEstimate,
    ExecContext,
)

logger = logging.getLogger(__name__)

HARD_BLOCK_PROTECTIONS = frozenset({"captcha", "cloudflare", "paywall", "forbidden"})

_ATOM_NS = "{http://www.w3.org/2005/Atom}"


def _localname(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _find_text(node: ET.Element, *names: str) -> str:
    """按标签名（忽略命名空间）查找首个非空文本。"""
    wanted = {n.lower() for n in names}
    for child in node:
        if _localname(child.tag) in wanted:
            if child.text and child.text.strip():
                return child.text.strip()
            # Atom 的 link 用属性承载地址
            href = child.get("href")
            if href:
                return href.strip()
    return ""


def parse_feed(xml_text: str, feed_url: str = "") -> list[dict]:
    """解析 RSS 2.0 / Atom 文档，返回规范化条目列表。

    每条包含 ``title`` / ``link`` / ``published`` / ``summary`` 四个基础字段，
    这些是两种格式共同具备的语义。
    """
    if not xml_text or not xml_text.strip():
        return []

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        logger.debug("feed 解析失败 %s: %s", feed_url, str(exc)[:80])
        return []

    entries: list[ET.Element] = []
    root_name = _localname(root.tag)

    if root_name == "feed":  # Atom
        entries = [c for c in root if _localname(c.tag) == "entry"]
    else:  # RSS 2.0 / RDF
        for child in root:
            if _localname(child.tag) == "channel":
                entries = [c for c in child if _localname(c.tag) == "item"]
                break
        if not entries:
            entries = [c for c in root if _localname(c.tag) == "item"]

    items: list[dict] = []
    for entry in entries:
        title = _find_text(entry, "title")
        link = _find_text(entry, "link", "id", "guid")
        published = _find_text(entry, "pubDate", "published", "updated", "date")
        summary = _find_text(entry, "description", "summary", "content")

        if not link and not title:
            continue

        items.append(
            {
                "title": title,
                "link": link,
                "published": published,
                "summary": summary[:2000] if summary else "",
            }
        )

        if len(items) >= 500:
            break

    return items


class FeedReader(Capability):
    """RSS / Atom 采集。"""

    name = "feed_reader"
    layer = CapabilityLayer.L1
    priority = 9

    def score(self, profile: dict, request: CollectRequest) -> float:
        access = self._access(profile)
        if access.get("protection") in HARD_BLOCK_PROTECTIONS:
            return 0.0
        if access.get("feeds"):
            return 0.95
        return 0.0

    def cost_estimate(self, request: CollectRequest) -> CostEstimate:
        feeds = max(1, min(request.max_pages, 3))
        return CostEstimate(requests=feeds, seconds=feeds * 0.5, memory_mb=15)

    async def execute(
        self, profile: dict, request: CollectRequest, ctx: ExecContext
    ) -> CollectResult:
        fetcher = getattr(ctx, "fetcher", None)
        if fetcher is None:
            return CollectResult.degrade("缺少取页工具")

        feeds = (self._access(profile).get("feeds")) or []
        if not feeds:
            return CollectResult.degrade("画像中未发现订阅源")

        base_rate = self._base_rate(profile)
        all_items: list[dict] = []
        used_feeds: list[str] = []

        for feed_url in feeds[: request.max_pages]:
            page = await fetcher.get(feed_url, base_rate=base_rate)
            if not page.ok:
                ctx.note(f"订阅源获取失败 status={page.status}：{feed_url}")
                continue

            entries = parse_feed(page.text, feed_url)
            if not entries:
                ctx.note(f"订阅源无可解析条目：{feed_url}")
                continue

            used_feeds.append(feed_url)
            for entry in entries:
                entry["_source_feed"] = feed_url
                all_items.append(entry)

            if len(all_items) >= request.max_items:
                break

        if not all_items:
            return CollectResult.degrade("所有订阅源均未产出条目")

        trimmed = all_items[: request.max_items]
        return CollectResult.ok(
            trimmed,
            cost=CostEstimate(
                requests=fetcher.request_count,
                seconds=len(used_feeds) * 0.5,
                memory_mb=15,
            ),
            meta={
                "feeds_used": used_feeds,
                "capability": self.name,
                "completeness": 1.0 if trimmed else 0.0,
            },
        )

    @staticmethod
    def _base_rate(profile: dict) -> Optional[float]:
        rate = (profile.get("strategy") or {}).get("rate") or {}
        value = rate.get("base_per_second")
        try:
            return float(value) if value else None
        except (TypeError, ValueError):
            return None
