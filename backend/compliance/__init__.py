"""
合规判定层
==========

四维矩阵判定的实现。这是"合规必须落成代码"的落点：判定结果结构化输出，
所有采集入口强制过闸，判定记录落库留痕。

维度：

- **A 可访问性**  A1 完全公开 / A2 需凭证 / A3 部分公开 / A4 技术隔离
- **B 授权基础**  B1 官方开放 / B2 用户自有凭证 / B3 用户书面授权 / B4 未声明 / B5 来源不明
- **C 行为合规**  C1-C5（遵守 robots、频率自适应、标识身份、尊重退避、缓存复用）
- **D 数据属性**  D1 公开信息 / D2 公开但受版权保护 / D3 个人数据 / D4 法定禁止

决策三值：``proceed`` / ``confirm_required`` / ``blocked``
"""

from compliance.engine import (
    AccessDimension,
    AlternativeSource,
    AuthorizationDimension,
    BehaviorDimension,
    ComplianceEngine,
    DataDimension,
    Verdict,
    VerdictDecision,
)

__all__ = [
    "AccessDimension",
    "AlternativeSource",
    "AuthorizationDimension",
    "BehaviorDimension",
    "ComplianceEngine",
    "DataDimension",
    "Verdict",
    "VerdictDecision",
]
