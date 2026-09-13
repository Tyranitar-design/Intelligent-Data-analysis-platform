"""
站点判别 · 请求模型
===================
"""
from typing import Literal, Optional

from pydantic import BaseModel, Field

AuthorizationBasis = Literal[
    "official",
    "own_credentials",
    "written_authorization",
    "third_party_credentials",
]


class AnalyzeRequest(BaseModel):
    """站点分析请求。"""

    url: str = Field(..., description="目标 URL（可省略协议，默认 https）")
    declared_authorization: Optional[AuthorizationBasis] = Field(
        default=None,
        description=(
            "授权基础声明。official=官方开放；own_credentials=自有凭证；"
            "written_authorization=书面授权；third_party_credentials=来源不明（会被阻断）"
        ),
    )
    force_refresh: bool = Field(
        default=False, description="强制重新探测，忽略已缓存画像"
    )
    sample_details: bool = Field(
        default=True, description="是否抽样详情页以计算字段覆盖率"
    )


class VerdictQuery(BaseModel):
    """判定查询参数。"""

    decision: Optional[Literal["proceed", "confirm_required", "blocked"]] = None
    domain: Optional[str] = None
