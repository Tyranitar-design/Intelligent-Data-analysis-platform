"""
能力 · 通用 HTTP 抓取（L1 兜底）
================================

当其他能力都无法定位结构化通道时的兜底路径：抓目标页本身并按通用规则
抽取字段，产出单条记录。

评分刻意压低（0.4 基线），让它排在 sitemap / feed / 结构化提取之后——
兜底能力不应该抢主路径的活。
"""
from __future__ import annotations

import logging
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
MAX_TEXT_CHARS = 20000


class HttpFetcher(Capability):
    """单页抓取 + 通用字段抽取。"""

    name = "http_fetcher"
    layer = CapabilityLayer.L1
    priority = 3

    def score(self, profile: dict, request: CollectRequest) -> float:
        access = self._access(profile)
        if access.get("protection") in HARD_BLOCK_PROTECTIONS:
            return 0.0

        structure = self._structure(profile)
        score = 0.4
        if structure.get("needs_render"):
            score -= 0.25
        if access.get("feeds") or access.get("sitemaps"):
            score -= 0.1
        return max(0.0, score)

    def cost_estimate(self, request: CollectRequest) -> CostEstimate:
        return CostEstimate(requests=1, seconds=1.0, memory_mb=20)

    async def execute(
        self, profile: dict, request: CollectRequest, ctx: ExecContext
    ) -> CollectResult:
        fetcher = getattr(ctx, "fetcher", None)
        if fetcher is None:
            return CollectResult.degrade("缺少取页工具")

        base_rate = self._base_rate(profile)
        url = request.target_url or profile.get("sample_url")
        if not url:
            return CollectResult.degrade("未提供目标 URL")

        page = await fetcher.get(url, base_rate=base_rate)
        if page.blocked:
            return CollectResult.failed(
                f"目标拒绝访问: status={page.status} error={page.error}"
            )
        if not page.ok:
            return CollectResult.degrade(
                f"页面获取失败: status={page.status} error={page.error}"
            )

        from discover.fields import extract_fields_from_page

        specs = extract_fields_from_page(page.text, page.final_url or url)
        wanted = {f.get("name") for f in request.fields} if request.fields else None

        payload = {
            s.name: (s.sample[:MAX_TEXT_CHARS] if isinstance(s.sample, str) else s.sample)
            for s in specs
            if not wanted or s.name in wanted
        }
        if not payload:
            return CollectResult.degrade("通用规则未提取到字段")

        completeness = round(
            len(payload) / max(1, len(wanted) if wanted else len(specs)), 4
        )
        return CollectResult.ok(
            [
                {
                    "payload": payload,
                    "text": payload.get("content", "") or "",
                    "source_url": page.final_url or url,
                    "_completeness": completeness,
                }
            ],
            cost=CostEstimate(requests=1, seconds=1.0, memory_mb=20),
            meta={"capability": self.name, "completeness": completeness},
        )

    @staticmethod
    def _base_rate(profile: dict) -> Optional[float]:
        rate = (profile.get("strategy") or {}).get("rate") or {}
        value = rate.get("base_per_second")
        try:
            return float(value) if value else None
        except (TypeError, ValueError):
            return None
