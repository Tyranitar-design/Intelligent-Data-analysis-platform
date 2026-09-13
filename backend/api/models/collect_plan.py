"""
采集计划模型
============

一份计划 = 一个画像 + 一条需求 + 一套字段映射与策略。

计划是"可执行、可复核、可审计"的最小单位：生成计划不触碰目标站点，
执行计划才产生网络请求，且执行前必须携带有效判定。
"""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.sql import func

from api.core.database import Base


class CollectPlan(Base):
    """采集计划表"""

    __tablename__ = "collect_plans"

    id = Column(Integer, primary_key=True, index=True)

    profile_id = Column(
        Integer, ForeignKey("site_profiles.id"), nullable=True, index=True
    )
    target_url = Column(String(1000), nullable=False)

    # 用户需求（自然语言），为空表示按画像推荐的全字段方案
    requirement = Column(Text, nullable=True)

    # 字段映射 [{name, path, source, type, coverage}]
    field_mapping = Column(JSON, nullable=True)
    # 能力链 ["feed_reader", "sitemap_walker", ...]
    strategy_chain = Column(JSON, nullable=True)
    # 频率策略 {base_per_second, min_per_second, max_concurrency_per_domain}
    rate_policy = Column(JSON, nullable=True)
    # 增量策略 {mode, stop_rule, dedup_key, content_hash}
    incremental_policy = Column(JSON, nullable=True)

    # 关联的合规判定
    verdict_uid = Column(String(64), nullable=True, index=True)

    # draft | ready | running | done | failed | cancelled
    status = Column(String(20), default="draft", nullable=False, index=True)

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<CollectPlan(id={self.id}, status={self.status}, target={self.target_url[:40]})>"

    def to_dict(self) -> dict:
        return {
            "plan_id": self.id,
            "profile_id": self.profile_id,
            "target_url": self.target_url,
            "requirement": self.requirement,
            "field_mapping": self.field_mapping or [],
            "strategy_chain": self.strategy_chain or [],
            "rate_policy": self.rate_policy or {},
            "incremental_policy": self.incremental_policy or {},
            "verdict_id": self.verdict_uid,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
