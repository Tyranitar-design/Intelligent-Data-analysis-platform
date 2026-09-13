"""
采集能力注册表
==============

所有采集能力实现统一的 ``Capability`` 协议，调度器按**适配度评分**选链，
执行失败自动降级到下一候选。加新能力 = 注册一个类，不改调度核心。

这是上一代做不出通用能力的根因所在：能力选择靠 if-else 意图分支，
加一个能力就要改核心调度代码，于是所有精力都花在堆站点适配器上。

能力分层与目标覆盖：

    L1 通用    HTTP 抓取 / 结构化提取 / RSS / Sitemap       覆盖 60% 站点零适配
    L2 策略    渲染 / 分页遍历 / API 调用                    覆盖 30%
    L3 适配    站点特定逻辑（私有 API、特殊登录）            覆盖 10%
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class CapabilityLayer(StrEnum):
    """能力分层。"""

    L1 = "L1"
    L2 = "L2"
    L3 = "L3"


class ResultStatus(StrEnum):
    """能力执行结果的三种去向。"""

    OK = "ok"            # 成功，产出可用的条目
    DEGRADE = "degrade"  # 本能力不适用或失败，请调度器尝试下一候选
    FAILED = "failed"    # 硬失败（如被合规阻断），不应继续降级


@dataclass
class CollectRequest:
    """一次采集请求。"""

    target_url: str
    # 要采集的字段 [{name, path, source, type}]
    fields: list[dict] = field(default_factory=list)
    # 最多处理多少页 / 多少个条目
    max_pages: int = 10
    max_items: int = 500
    # 增量模式：命中已见条目的连续次数达到阈值即停止翻页
    consecutive_known_limit: int = 10
    # 补充参数（能力自定义）
    options: dict[str, Any] = field(default_factory=dict)


@dataclass
class CostEstimate:
    """成本预估，用于调度决策。"""

    requests: int = 1
    seconds: float = 1.0
    memory_mb: float = 10.0

    @property
    def weight(self) -> float:
        """归一化的成本权重，越小越便宜。"""
        return (
            min(1.0, self.requests / 100.0) * 0.5
            + min(1.0, self.seconds / 60.0) * 0.3
            + min(1.0, self.memory_mb / 512.0) * 0.2
        )


@dataclass
class CollectResult:
    """能力执行结果。"""

    status: ResultStatus
    items: list[dict] = field(default_factory=list)
    next_cursor: Optional[dict] = None
    error: Optional[str] = None
    cost: CostEstimate = field(default_factory=CostEstimate)
    # 命中的已见条目数（增量判定用）
    known_hits: int = 0
    # 能力自定义的观测信息
    meta: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def ok(cls, items: list[dict], **kwargs: Any) -> "CollectResult":
        return cls(status=ResultStatus.OK, items=items, **kwargs)

    @classmethod
    def degrade(cls, reason: str, **kwargs: Any) -> "CollectResult":
        return cls(status=ResultStatus.DEGRADE, error=reason, **kwargs)

    @classmethod
    def failed(cls, reason: str, **kwargs: Any) -> "CollectResult":
        return cls(status=ResultStatus.FAILED, error=reason, **kwargs)


@dataclass
class ExecContext:
    """能力执行上下文。"""

    # 合规判定留痕 ID：每条产出的数据都要能追溯到它
    verdict_id: Optional[int] = None
    # 取页工具（带限速、并发闸门与 robots 检查）
    fetcher: Any = None
    # 限速器（按 domain 自适应）
    rate_limiter: Any = None
    # 去重查询接口
    dedup: Any = None
    # 已见条目判定回调：给定 item_key 返回是否已采过
    is_known: Any = None
    # 结构化日志
    trace: list[str] = field(default_factory=list)

    def note(self, message: str) -> None:
        self.trace.append(message)
        logger.debug("[collect] %s", message)


class Capability(ABC):
    """采集能力基类。"""

    name: str = "base"
    layer: CapabilityLayer = CapabilityLayer.L1
    # 同一评分下优先级更高者先试（0-10）
    priority: int = 0

    @abstractmethod
    def score(self, profile: dict, request: CollectRequest) -> float:
        """返回 0.0-1.0 的适配度；返回 0 表示不适用。"""

    @abstractmethod
    async def execute(
        self, profile: dict, request: CollectRequest, ctx: ExecContext
    ) -> CollectResult:
        """执行采集。"""

    def cost_estimate(self, request: CollectRequest) -> CostEstimate:
        """默认成本预估，子类可覆写。"""
        return CostEstimate()

    # -- 便捷访问 ---------------------------------------------------- #

    @staticmethod
    def _access(profile: dict) -> dict:
        return profile.get("access") or {}

    @staticmethod
    def _structure(profile: dict) -> dict:
        return profile.get("structure") or {}

    @staticmethod
    def _fields(profile: dict) -> list[dict]:
        return profile.get("fields") or []


class CapabilityRegistry:
    """能力注册表与选链器。"""

    def __init__(self) -> None:
        self._capabilities: dict[str, Capability] = {}

    def register(self, capability: Capability, *, override: bool = False) -> None:
        """注册能力。同名默认不覆盖，避免插件互相踩踏。"""
        if capability.name in self._capabilities and not override:
            raise ValueError(f"能力已注册: {capability.name}")
        self._capabilities[capability.name] = capability
        logger.debug("注册采集能力: %s (%s)", capability.name, capability.layer)

    def unregister(self, name: str) -> None:
        self._capabilities.pop(name, None)

    def get(self, name: str) -> Optional[Capability]:
        return self._capabilities.get(name)

    def names(self) -> list[str]:
        return sorted(self._capabilities)

    def by_layer(self, layer: CapabilityLayer) -> list[Capability]:
        return [c for c in self._capabilities.values() if c.layer == layer]

    def select_chain(
        self,
        profile: dict,
        request: CollectRequest,
        *,
        preferred: Optional[list[str]] = None,
    ) -> list[Capability]:
        """按适配度选出候选链，失败时依次降级。

        ``preferred`` 给出期望的能力名顺序（来自画像的 strategy.chain），
        命中的能力获得加权，但不排斥其他候选——画像可能过时。
        """
        preferred = preferred or []
        scored: list[tuple[float, Capability]] = []

        for capability in self._capabilities.values():
            try:
                raw = capability.score(profile, request)
            except Exception as exc:  # noqa: BLE001 - 单个能力的评分异常不该影响选链
                logger.warning("能力 %s 评分失败: %s", capability.name, exc)
                continue

            if raw <= 0:
                continue

            weight = raw * (1.0 + capability.priority * 0.1)
            if capability.name in preferred:
                # 画像推荐加权，但不至于压过明显更合适的能力
                weight *= 1.35
            scored.append((weight, capability))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [capability for _, capability in scored]

    def describe(self) -> list[dict]:
        """输出注册表概览，供 /capabilities 端点展示。"""
        return [
            {
                "name": c.name,
                "layer": str(c.layer),
                "priority": c.priority,
            }
            for c in sorted(
                self._capabilities.values(), key=lambda x: (str(x.layer), -x.priority)
            )
        ]


def build_default_registry() -> CapabilityRegistry:
    """构建含全部内置能力的注册表。

    能力实现在 :mod:`collect.capabilities` 中，这里集中装配，避免循环导入。
    """
    from collect.capabilities import (
        BrowserRenderer,
        FeedReader,
        HttpFetcher,
        SitemapWalker,
        StructuredExtractor,
    )

    registry = CapabilityRegistry()
    registry.register(HttpFetcher())
    registry.register(StructuredExtractor())
    registry.register(FeedReader())
    registry.register(SitemapWalker())
    registry.register(BrowserRenderer())
    return registry
