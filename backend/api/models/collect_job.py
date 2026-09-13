"""
采集任务模型
============

三层结构：

    CollectJob   用户看到的任务单位（一个计划的一次执行）
    CollectTask  调度单位（可分片、可断点续传）
    CollectItem  数据单位（一条规范化记录）

``CollectItem.verdict_id`` 外键到 ``compliance_verdicts``，是合规强制点之一：
没有判定留痕的数据无法入库。
"""
from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from api.core.database import Base


class CollectJob(Base):
    """采集任务（用户可见单位）"""

    __tablename__ = "collect_jobs"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("collect_plans.id"), nullable=False, index=True)

    # pending | running | succeeded | partial | failed | waiting_human | cancelled
    status = Column(String(20), default="pending", nullable=False, index=True)

    total_tasks = Column(Integer, default=0, nullable=False)
    done_tasks = Column(Integer, default=0, nullable=False)
    items_count = Column(Integer, default=0, nullable=False)

    # 去重统计 {key_hits, content_hits, inserted, skipped}
    dedup_stats = Column(JSON, nullable=True)
    # 质量分（字段完整度 × 有效行占比）
    quality_score = Column(Float, default=0.0, nullable=False)
    # 错误分布 {error_type: count}
    error_dist = Column(JSON, nullable=True)

    # 人机协同票据（waiting_human 时填充）
    assist_ticket = Column(JSON, nullable=True)

    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<CollectJob(id={self.id}, status={self.status}, items={self.items_count})>"

    def to_dict(self) -> dict:
        return {
            "job_id": self.id,
            "plan_id": self.plan_id,
            "status": self.status,
            "total_tasks": self.total_tasks,
            "done_tasks": self.done_tasks,
            "items_count": self.items_count,
            "dedup_stats": self.dedup_stats or {},
            "quality_score": self.quality_score,
            "error_dist": self.error_dist or {},
            "assist_ticket": self.assist_ticket,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class CollectTask(Base):
    """采集分片（调度单位，支持断点续传）"""

    __tablename__ = "collect_tasks"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("collect_jobs.id"), nullable=False, index=True)

    # 分片描述 {kind: "list"|"detail"|"feed"|"sitemap", urls: [...], page: N}
    shard_spec = Column(JSON, nullable=True)
    # 断点游标（粒度是分片，不是条目）
    cursor = Column(JSON, nullable=True)

    # pending | running | done | failed | skipped
    status = Column(String(20), default="pending", nullable=False, index=True)
    capability_used = Column(String(50), nullable=True)
    attempts = Column(Integer, default=0, nullable=False)
    last_error = Column(Text, nullable=True)

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<CollectTask(id={self.id}, job={self.job_id}, status={self.status})>"


class CollectItem(Base):
    """采集数据条目（数据单位）"""

    __tablename__ = "collect_items"
    __table_args__ = (
        UniqueConstraint("item_key", name="uq_collect_items_item_key"),
    )

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("collect_jobs.id"), nullable=False, index=True)
    task_id = Column(Integer, ForeignKey("collect_tasks.id"), nullable=True, index=True)

    # 合规强制点：每条数据都要能追溯到判定
    verdict_id = Column(
        Integer, ForeignKey("compliance_verdicts.id"), nullable=True, index=True
    )

    # 去重第 1 级：归一化 URL 的指纹
    item_key = Column(String(64), nullable=False, index=True)
    source_url = Column(String(1000), nullable=True)

    # 去重第 2 级：正文 SimHash（64 位，存为有符号整数以适配 SQLite）
    content_simhash = Column(BigInteger, nullable=True, index=True)

    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=True, index=True)

    # 规范化后的字段值
    payload = Column(JSON, nullable=True)
    # 字段完整度（本条目有多少字段拿到了值）
    completeness = Column(Float, default=0.0, nullable=False)

    item_version = Column(Integer, default=1, nullable=False)

    first_seen = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_seen = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<CollectItem(id={self.id}, key={self.item_key[:12]}, v={self.item_version})>"
