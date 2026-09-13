"""
采集层
======

输入 ``SiteProfile`` + 采集需求 → 按能力评分选链 → 执行 → 产出规范化条目。

模块划分：

- ``registry``       Capability 协议、注册表、评分选链
- ``ratelimit``      按域名的自适应限速
- ``dedup``          三级去重（主键 / SimHash / 语义）
- ``capabilities``   能力实现（feed / sitemap / 结构化提取 / 兜底 / 渲染）
- ``scheduler``      任务编排、分片、断点续传、入库

设计约束（对应合规四维的 C 维）：

- 请求前过 robots 路径级检查，被排除的路径不进入请求
- 频率按域名自适应，遇 429/503 降速并尊重 Retry-After
- 请求标识自身身份与用途
- 每条入库数据关联判定留痕（``CollectItem.verdict_id``）
"""

from collect.registry import (
    Capability,
    CapabilityLayer,
    CapabilityRegistry,
    CollectRequest,
    CollectResult,
    CostEstimate,
    ExecContext,
    ResultStatus,
    build_default_registry,
)

__all__ = [
    "Capability",
    "CapabilityLayer",
    "CapabilityRegistry",
    "CollectRequest",
    "CollectResult",
    "CostEstimate",
    "ExecContext",
    "ResultStatus",
    "build_default_registry",
]
