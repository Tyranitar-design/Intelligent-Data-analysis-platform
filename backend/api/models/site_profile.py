"""
站点画像模型
============

SiteProfile 是判别层的核心对象：一次探测的结果落库后可复用、可版本化，
避免"每次见到同一个站点都当成新站点"。

同域下不同栏目（url_pattern 不同）算不同画像；站点改版时新增 version 而非覆盖。
"""
from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    JSON,
)
from sqlalchemy.sql import func

from api.core.database import Base


class SiteProfile(Base):
    """站点画像表"""

    __tablename__ = "site_profiles"

    id = Column(Integer, primary_key=True, index=True)

    # 定位：同域 + 同一 URL 模式 = 同一画像
    domain = Column(String(255), nullable=False, index=True)
    url_pattern = Column(String(500), nullable=False, index=True)
    version = Column(Integer, default=1, nullable=False)
    sample_url = Column(String(1000), nullable=True)

    # 站点元信息 {title, description, type, lang, tech_stack}
    site_meta = Column(JSON, nullable=True)

    # 访问状态 {protection, requires_credentials, crawl_delay, robots_allowed,
    #          robots_disallow, sitemaps, feeds, http_status}
    access_state = Column(JSON, nullable=True)

    # 结构信息 {has_sitemap, has_rss, list_pattern, detail_pattern,
    #          pagination: {mode, param, sample}, structured_data_kinds}
    structure = Column(JSON, nullable=True)

    # 可采字段 [{name, path, type, sample, coverage, source}]
    fields = Column(JSON, nullable=True)

    # 推荐采集策略 {chain, rate, incremental}
    strategy = Column(JSON, nullable=True)

    # 判定结果快照 {decision, dimensions, reasons, conditions}
    compliance = Column(JSON, nullable=True)

    # 质量指标
    confidence = Column(Float, default=0.0, nullable=False)
    coverage = Column(Float, default=0.0, nullable=False)

    # 来源与时间
    verified_by = Column(String(50), default="discoverer", nullable=False)
    first_seen = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_verified = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<SiteProfile(id={self.id}, domain={self.domain}, "
            f"v{self.version}, confidence={self.confidence:.2f})>"
        )

    def to_dict(self) -> dict:
        return {
            "profile_id": self.id,
            "domain": self.domain,
            "url_pattern": self.url_pattern,
            "version": self.version,
            "sample_url": self.sample_url,
            "site": self.site_meta or {},
            "access": self.access_state or {},
            "structure": self.structure or {},
            "fields": self.fields or [],
            "strategy": self.strategy or {},
            "compliance": self.compliance or {},
            "confidence": self.confidence,
            "coverage": self.coverage,
            "verified_by": self.verified_by,
            "first_seen": self.first_seen.isoformat() if self.first_seen else None,
            "last_verified": (
                self.last_verified.isoformat() if self.last_verified else None
            ),
        }
