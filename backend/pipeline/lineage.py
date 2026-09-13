"""
字段级血缘
==========

回答"这个数据集里的 title 字段是从哪来的"：

    dataset.field  ←  collect_item.payload.field
                   ←  extractor_rule（判别层给出的提取规则）
                   ←  site_profile（站点画像）
                   ←  source_url（原始页面）

没有血缘，数据只能"用"不能"信"——出了问题无从回溯是提取规则错了还是
站点改版了还是源数据本身如此。
"""
from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def build_lineage(
    dataset_fields: list[str],
    records: list[dict],
    *,
    profile: Optional[dict] = None,
    source_urls: Optional[list[str]] = None,
) -> list[dict]:
    """构建字段级血缘。

    ``profile`` 提供提取规则（来自判别层的 fields 定义），
    ``records`` 用于统计实际覆盖率。
    """
    profile = profile or {}
    source_urls = source_urls or []
    rule_map = _extract_rule_map(profile)

    total = max(1, len(records))
    lineage: list[dict] = []

    for field in dataset_fields:
        present = sum(1 for r in records if isinstance(r, dict) and r.get(field) not in (None, ""))
        entry: dict[str, Any] = {
            "field": field,
            "item_field": field,
            "extractor_rule": rule_map.get(field, "unknown"),
            "profile_id": profile.get("profile_id"),
            "domain": profile.get("domain"),
            "coverage": round(present / total, 4),
        }
        if source_urls:
            entry["source_sample"] = source_urls[0]
            entry["source_count"] = len(source_urls)
        lineage.append(entry)

    return lineage


def _extract_rule_map(profile: dict) -> dict[str, str]:
    """从画像里取字段 → 提取规则的映射。"""
    mapping: dict[str, str] = {}
    for spec in profile.get("fields") or []:
        if not isinstance(spec, dict):
            continue
        name = spec.get("name")
        if not name:
            continue
        source = spec.get("source") or "unknown"
        path = spec.get("path") or ""
        mapping[name] = f"{source}:{path}" if path else source
    return mapping


def trace_field(lineage: list[dict], field: str) -> Optional[dict]:
    """回溯单个字段的来源。"""
    for entry in lineage:
        if entry.get("field") == field:
            return entry
    return None


def format_lineage(lineage: list[dict]) -> str:
    """把血缘渲染成可读的多行文本，便于写进报告。"""
    if not lineage:
        return "（无血缘记录）"
    lines = []
    for entry in lineage:
        lines.append(
            f"  {entry.get('field'):20s} ← {entry.get('extractor_rule'):28s} "
            f"coverage={entry.get('coverage')}"
        )
    return "\n".join(lines)
