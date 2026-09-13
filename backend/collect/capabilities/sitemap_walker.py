"""
能力 · Sitemap 遍历（L1）
=========================

Sitemap 是站点主动公开的 URL 清单，语义明确、无需猜测列表结构。

支持 ``<urlset>`` 与 ``<sitemapindex>``（索引会展开一层，避免递归过深）。
拿到 URL 清单后按字段规则逐页提取，与结构化提取共用同一套抽取逻辑。
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

# 索引展开上限，防止超大型 sitemap 把探测拖垮
MAX_SITEMAPS_PER_INDEX = 5


def parse_sitemap(xml_text: str) -> tuple[list[str], list[str]]:
    """解析 sitemap。

    返回 ``(页面 URL 列表, 子 sitemap 列表)``。

    标准结构是 ``<urlset><url><loc>…</loc></url></urlset>``——``<loc>`` 位于
    ``<url>`` 之下而非根的直接子节点，因此必须递归查找。也兼容 ``<loc>``
    直接挂在根下的非标准写法。
    """
    if not xml_text or not xml_text.strip():
        return [], []

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        logger.debug("sitemap 解析失败: %s", str(exc)[:80])
        return [], []

    root_name = root.tag.rsplit("}", 1)[-1].lower()
    is_index = root_name == "sitemapindex"

    urls: list[str] = []
    children: list[str] = []

    for node in root.iter():
        if node is root:
            continue
        if node.tag.rsplit("}", 1)[-1].lower() != "loc":
            continue
        value = (node.text or "").strip()
        if not value:
            continue
        (children if is_index else urls).append(value)

    return urls, children


class SitemapWalker(Capability):
    """Sitemap 遍历采集。"""

    name = "sitemap_walker"
    layer = CapabilityLayer.L1
    priority = 8

    def score(self, profile: dict, request: CollectRequest) -> float:
        access = self._access(profile)
        if access.get("protection") in HARD_BLOCK_PROTECTIONS:
            return 0.0
        if access.get("sitemaps"):
            structure = self._structure(profile)
            # 没有明确指出列表结构时，sitemap 是最好的入口
            return 0.85 if not structure.get("list_item_count") else 0.7
        return 0.0

    def cost_estimate(self, request: CollectRequest) -> CostEstimate:
        pages = request.max_items + 2
        return CostEstimate(requests=pages, seconds=pages * 0.8, memory_mb=35)

    async def execute(
        self, profile: dict, request: CollectRequest, ctx: ExecContext
    ) -> CollectResult:
        fetcher = getattr(ctx, "fetcher", None)
        if fetcher is None:
            return CollectResult.degrade("缺少取页工具")

        sitemaps = (self._access(profile).get("sitemaps")) or []
        if not sitemaps:
            return CollectResult.degrade("画像中未发现 sitemap")

        base_rate = self._base_rate(profile)
        page_urls: list[str] = []

        for sitemap_url in sitemaps[:2]:
            page = await fetcher.get(sitemap_url, base_rate=base_rate)
            if not page.ok:
                ctx.note(f"sitemap 获取失败 status={page.status}：{sitemap_url}")
                continue

            urls, children = parse_sitemap(page.text)

            # 索引文件：展开一层子 sitemap
            for child in children[:MAX_SITEMAPS_PER_INDEX]:
                child_page = await fetcher.get(child, base_rate=base_rate)
                if child_page.ok:
                    child_urls, _ = parse_sitemap(child_page.text)
                    urls.extend(child_urls)

            page_urls.extend(urls[: request.max_items])
            if len(page_urls) >= request.max_items:
                break

        if not page_urls:
            return CollectResult.degrade("sitemap 未产出可用 URL")

        ctx.note(f"sitemap 产出 {len(page_urls)} 个 URL")
        return await self._extract_pages(
            fetcher, page_urls[: request.max_items], request, ctx, base_rate
        )

    # ------------------------------------------------------------------ #

    async def _extract_pages(
        self,
        fetcher,
        urls: list[str],
        request: CollectRequest,
        ctx: ExecContext,
        base_rate: Optional[float],
    ) -> CollectResult:
        """逐页提取字段。与结构化提取共用抽取规则。"""
        from discover.fields import extract_fields_from_page

        items: list[dict] = []
        known_hits = 0
        consecutive_known = 0
        wanted = {f.get("name") for f in request.fields} if request.fields else None

        for url in urls:
            if ctx.is_known is not None and ctx.is_known(url):
                known_hits += 1
                consecutive_known += 1
                if consecutive_known >= request.consecutive_known_limit:
                    break
                continue
            consecutive_known = 0

            page = await fetcher.get(url, base_rate=base_rate)
            if not page.ok:
                continue

            specs = extract_fields_from_page(page.text, page.final_url or url)
            payload = {
                s.name: (s.sample[:20000] if isinstance(s.sample, str) else s.sample)
                for s in specs
                if not wanted or s.name in wanted
            }
            if not payload:
                continue

            items.append(
                {
                    "payload": payload,
                    "text": payload.get("content", "") or "",
                    "source_url": page.final_url or url,
                    "_completeness": round(
                        len(payload) / max(1, len(wanted) if wanted else len(specs)), 4
                    ),
                }
            )
            if len(items) >= request.max_items:
                break

        if not items:
            if known_hits > 0:
                # 与结构化提取同理：全部命中属于增量的正常结果，不应降级
                return CollectResult.ok(
                    [],
                    known_hits=known_hits,
                    meta={
                        "capability": self.name,
                        "completeness": 1.0,
                        "all_known": True,
                    },
                )
            return CollectResult.degrade("sitemap 页面均未提取到字段")

        completeness = sum(i.get("_completeness", 0.0) for i in items) / len(items)
        return CollectResult.ok(
            items,
            known_hits=known_hits,
            cost=CostEstimate(
                requests=fetcher.request_count,
                seconds=len(items) * 0.8,
                memory_mb=35,
            ),
            meta={
                "capability": self.name,
                "completeness": round(completeness, 4),
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
