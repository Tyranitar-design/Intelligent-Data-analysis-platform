"""
能力 · 结构化提取（L1 主力）
============================

适用：站点存在可识别的列表结构（重复出现的条目容器）。

流程：抓列表页 → 识别条目 → 逐条抓详情 → 按字段映射提取 → 产出规范化条目。

这是覆盖 60% 站点的主路径。它不需要任何站点特定代码——列表结构由判别层
的 SiteProfile 提供，字段由通用提取规则给出。
"""
from __future__ import annotations

import logging
from typing import Optional

from collect.ratelimit import AdaptiveRateLimiter
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
# 单条详情页正文抽取上限，避免长文把 payload 撑爆
MAX_TEXT_CHARS = 20000


class StructuredExtractor(Capability):
    """列表 → 详情 → 字段提取。"""

    name = "structured_extractor"
    layer = CapabilityLayer.L1
    priority = 7

    def score(self, profile: dict, request: CollectRequest) -> float:
        access = self._access(profile)
        if access.get("protection") in HARD_BLOCK_PROTECTIONS:
            return 0.0

        structure = self._structure(profile)
        item_count = int(structure.get("list_item_count") or 0)
        needs_render = bool(structure.get("needs_render"))

        if item_count >= 3:
            return 0.6 if needs_render else 0.9
        # 列表结构不明确时仍有兜底价值，但优先级低于其他能力
        return 0.25

    def cost_estimate(self, request: CollectRequest) -> CostEstimate:
        # 1 次列表页 + N 次详情页
        pages = min(request.max_items, request.max_pages * 10) + 1
        return CostEstimate(requests=pages, seconds=pages * 0.8, memory_mb=30)

    async def execute(
        self, profile: dict, request: CollectRequest, ctx: ExecContext
    ) -> CollectResult:
        fetcher = getattr(ctx, "fetcher", None)
        if fetcher is None:
            return CollectResult.degrade("缺少取页工具")

        base_rate = self._base_rate(profile)
        list_url = profile.get("sample_url") or request.target_url

        page = await fetcher.get(list_url, base_rate=base_rate)
        if page.blocked:
            return CollectResult.failed(
                f"目标拒绝访问: status={page.status} error={page.error}"
            )
        if not page.ok:
            return CollectResult.degrade(
                f"列表页获取失败: status={page.status} error={page.error}"
            )

        # 用判别层的结构识别器抽取条目链接
        from discover.structure import detect_list_pattern

        pattern = detect_list_pattern(page.text, page.final_url or list_url)
        if pattern.item_count < 1:
            return CollectResult.degrade("未识别到列表条目容器")

        candidate_urls = pattern.sample_links[: request.max_items]
        if not candidate_urls:
            return CollectResult.degrade("列表容器内未找到可用链接")

        ctx.note(f"列表识别：{pattern.item_count} 条，选取 {len(candidate_urls)} 条")

        items: list[dict] = []
        known_hits = 0
        consecutive_known = 0

        for url in candidate_urls:
            if ctx.is_known is not None and ctx.is_known(url):
                known_hits += 1
                consecutive_known += 1
                if consecutive_known >= request.consecutive_known_limit:
                    ctx.note(
                        f"连续 {consecutive_known} 条已见，按增量策略停止翻页"
                    )
                    break
                continue
            consecutive_known = 0

            detail = await fetcher.get(url, base_rate=base_rate)
            if detail.blocked:
                ctx.note(f"详情页被拒绝：{url}")
                continue
            if not detail.ok:
                ctx.note(f"详情页失败 status={detail.status}：{url}")
                continue

            extracted = self._extract(detail.text, detail.final_url or url, request)
            if not extracted:
                continue
            extracted["source_url"] = detail.final_url or url
            items.append(extracted)

            if len(items) >= request.max_items:
                break

        if not items:
            if known_hits > 0:
                # 全部命中去重 = 增量采集的正常结果（无新增），不是失败。
                # 若返回 DEGRADE，调度器会降级到兜底能力并重复采回同一批数据。
                return CollectResult.ok(
                    [],
                    known_hits=known_hits,
                    meta={
                        "list_item_count": pattern.item_count,
                        "capability": self.name,
                        "completeness": 1.0,
                        "all_known": True,
                    },
                )
            return CollectResult.degrade("所有候选详情页均未提取到有效字段")

        completeness = sum(i.get("_completeness", 0.0) for i in items) / len(items)
        return CollectResult.ok(
            items,
            known_hits=known_hits,
            cost=CostEstimate(
                requests=fetcher.request_count,
                seconds=len(items) * 0.8,
                memory_mb=30,
            ),
            meta={
                "list_item_count": pattern.item_count,
                "completeness": round(completeness, 4),
                "capability": self.name,
            },
        )

    # ------------------------------------------------------------------ #

    @staticmethod
    def _base_rate(profile: dict) -> Optional[float]:
        strategy = profile.get("strategy") or {}
        rate = strategy.get("rate") or {}
        value = rate.get("base_per_second")
        try:
            return float(value) if value else None
        except (TypeError, ValueError):
            return None

    def _extract(
        self, html: str, url: str, request: CollectRequest
    ) -> Optional[dict]:
        """从单个详情页提取字段。"""
        from discover.fields import extract_fields_from_page

        specs = extract_fields_from_page(html, url)
        if not specs:
            return None

        wanted = {f.get("name") for f in request.fields} if request.fields else None

        payload: dict = {}
        for spec in specs:
            if wanted and spec.name not in wanted:
                continue
            payload[spec.name] = (
                spec.sample[:MAX_TEXT_CHARS] if isinstance(spec.sample, str) else spec.sample
            )

        if not payload:
            return None

        # 正文单独保留，供内容级去重使用
        body = ""
        content_value = payload.get("content")
        if isinstance(content_value, str):
            body = content_value

        total = len(wanted) if wanted else len(specs)
        completeness = round(len(payload) / max(1, total), 4)

        return {
            "payload": payload,
            "text": body[:MAX_TEXT_CHARS],
            "_completeness": completeness,
        }
