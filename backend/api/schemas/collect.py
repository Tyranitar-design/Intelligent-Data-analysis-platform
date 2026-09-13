"""
采集 · 请求模型
===============
"""
from typing import Optional

from pydantic import BaseModel, Field

from api.schemas.discover import AuthorizationBasis


class PlanRequest(BaseModel):
    """创建采集计划。"""

    url: str = Field(..., description="目标 URL")
    profile_id: Optional[int] = Field(
        default=None, description="复用已有画像；不传则按 url 现场判别"
    )
    requirement: Optional[str] = Field(
        default=None,
        description="自然语言需求，如「采集全部文章标题与发布时间」。为空则按画像推荐全字段",
    )
    declared_authorization: Optional[AuthorizationBasis] = Field(
        default=None, description="授权基础声明"
    )
    max_items: int = Field(default=200, ge=1, le=5000, description="本次采集中条目上限")


class RunRequest(BaseModel):
    """执行采集计划。"""

    plan_id: int
    authorization_token: Optional[str] = Field(
        default=None,
        description="判定为 confirm_required 时，需携带补齐授权后签发的令牌",
    )
    max_items: int = Field(default=200, ge=1, le=5000)


class ItemQuery(BaseModel):
    """条目查询参数。"""

    job_id: Optional[int] = None
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)
