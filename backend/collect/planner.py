"""
采集计划构建与合规校验
======================

从路由层抽出的业务逻辑：REST 端点与 MCP 工具共用同一套实现，
避免"两个入口各自实现一遍"这种最典型的重复。

合规校验在此处集中，是三层防线中的第一层最外层——
任何创建计划或执行采集的入口都会经过它。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from api.models import CollectPlan, ComplianceVerdict, SiteProfile

logger = logging.getLogger(__name__)

# 需求关键词 → 字段名候选
KEYWORD_FIELD_MAP: dict[str, tuple[str, ...]] = {
    "标题": ("title", "headline", "name"),
    "题目": ("title", "headline", "name"),
    "时间": ("publish_date", "datePublished", "date", "published", "updated"),
    "日期": ("publish_date", "datePublished", "date", "published", "updated"),
    "作者": ("author", "creator"),
    "正文": ("content", "articleBody", "description", "summary"),
    "内容": ("content", "articleBody", "description", "summary"),
    "摘要": ("description", "summary"),
    "价格": ("price", "offers"),
    "评论": ("commentCount", "comments"),
}

DEFAULT_COVERAGE_FLOOR = 0.4


@dataclass
class ComplianceDenied(Exception):
    """合规校验未通过。调用方据此转成自己的错误格式。"""

    kind: str  # blocked | authorization_required | invalid_token | token_expired
    message: str
    reasons: list[str] = field(default_factory=list)
    conditions: list[str] = field(default_factory=list)
    alternatives: list[dict] = field(default_factory=list)
    coverage_estimate: float = 0.0

    def __post_init__(self) -> None:
        super().__init__(self.message)

    def to_dict(self) -> dict:
        return {
            "error": self.kind,
            "message": self.message,
            "reasons": self.reasons,
            "conditions": self.conditions,
            "alternatives": self.alternatives,
            "coverage_estimate": self.coverage_estimate,
        }


def resolve_verdict(
    session: Session, verdict_uid: Optional[str]
) -> Optional[ComplianceVerdict]:
    """按对外 ID 取判定记录。"""
    if not verdict_uid:
        return None
    return (
        session.execute(
            select(ComplianceVerdict)
            .where(ComplianceVerdict.verdict_uid == verdict_uid)
            .limit(1)
        )
        .scalars()
        .first()
    )


def check_verdict(
    verdict: Optional[ComplianceVerdict], authorization_token: Optional[str] = None
) -> None:
    """合规闸门。不通过时抛 :class:`ComplianceDenied`。

    - ``blocked``                → 直接拒绝，附替代源
    - ``confirm_required``       → 需要令牌；令牌错误或过期同样拒绝
    - ``proceed`` / 无判定记录   → 放行
    """
    if verdict is None:
        return

    if verdict.decision == "blocked":
        raise ComplianceDenied(
            kind="blocked",
            message="该目标处于技术隔离或数据属性受限，不执行采集",
            reasons=list(verdict.reasons or []),
            alternatives=list(verdict.alternatives or []),
            coverage_estimate=float(verdict.coverage_estimate or 0.0),
        )

    if verdict.decision != "confirm_required":
        return

    if not authorization_token:
        raise ComplianceDenied(
            kind="authorization_required",
            message="需先补齐授权声明",
            conditions=list(verdict.conditions or []),
        )

    if authorization_token != verdict.authorization_token:
        raise ComplianceDenied(
            kind="invalid_token", message="授权令牌不匹配"
        )

    expires = verdict.token_expires_at
    if expires is not None:
        now = datetime.now(timezone.utc)
        exp = expires if expires.tzinfo else expires.replace(tzinfo=timezone.utc)
        if now > exp:
            raise ComplianceDenied(
                kind="token_expired", message="授权令牌已过期，请重新判别站点"
            )


def select_fields(profile: dict, requirement: Optional[str]) -> list[dict]:
    """按需求筛选可采字段。

    需求为空时返回覆盖率达标的全字段；需求存在时按关键词匹配。
    真正的语义筛选留给后续的 LLM 辅助层，当前规则保证"没有需求也能给出完整方案"。
    """
    fields = list(profile.get("fields") or [])
    if not requirement:
        return [
            f for f in fields if float(f.get("coverage") or 0) >= DEFAULT_COVERAGE_FLOOR
        ]

    wanted: set[str] = set()
    for keyword, names in KEYWORD_FIELD_MAP.items():
        if keyword in requirement:
            wanted.update(names)

    if not wanted:
        return [
            f for f in fields if float(f.get("coverage") or 0) >= DEFAULT_COVERAGE_FLOOR
        ]

    return [f for f in fields if f.get("name") in wanted]


async def build_plan(
    session: Session,
    *,
    url: str,
    profile_id: Optional[int] = None,
    requirement: Optional[str] = None,
    declared_authorization: Optional[str] = None,
) -> tuple[CollectPlan, dict]:
    """构建采集计划。

    不产生网络请求（除 ``profile_id`` 为空时需现场判别一次）。
    返回 ``(计划, 判定结果)``。路由层与 MCP 工具共用此实现——
    两个入口本该只有一套逻辑。
    """
    profile: Optional[SiteProfile] = None
    verdict_payload: Optional[dict] = None

    if profile_id is not None:
        profile = session.get(SiteProfile, profile_id)
        if profile is None:
            raise ValueError(f"画像不存在: {profile_id}")
    else:
        from discover.profile import SiteProfiler

        analyzer = SiteProfiler(session)
        analyzed = await analyzer.analyze(
            url, declared_authorization=declared_authorization
        )
        profile = session.get(SiteProfile, analyzed.profile["profile_id"])
        verdict_payload = analyzed.verdict

    if profile is None:
        raise ValueError(f"无法获取站点画像: {url}")

    profile_dict = profile.to_dict()

    if verdict_payload is None:
        latest = (
            session.execute(
                select(ComplianceVerdict)
                .where(ComplianceVerdict.profile_id == profile.id)
                .order_by(ComplianceVerdict.id.desc())
                .limit(1)
            )
            .scalars()
            .first()
        )
        verdict_payload = latest.to_dict() if latest else {}

    fields = select_fields(profile_dict, requirement)
    strategy = profile_dict.get("strategy") or {}
    rate = dict(strategy.get("rate") or {})
    rate.setdefault("base_per_second", 1.0)
    rate.setdefault("min_per_second", 0.1)
    rate.setdefault("max_concurrency_per_domain", 2)

    plan = CollectPlan(
        profile_id=profile.id,
        target_url=url,
        requirement=requirement,
        field_mapping=fields,
        strategy_chain=list(strategy.get("chain") or []),
        rate_policy=rate,
        incremental_policy=dict(strategy.get("incremental") or {}),
        verdict_uid=verdict_payload.get("verdict_id"),
        status="ready",
    )
    session.add(plan)
    session.commit()
    session.refresh(plan)

    return plan, verdict_payload
