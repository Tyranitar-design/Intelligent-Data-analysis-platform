"""
合规判定记录模型
================

四维矩阵（可访问性 × 授权基础 × 行为合规 × 数据属性）的判定结果留痕。

这张表是合规强制点之一：采集产出的每条数据都要求能追溯到一条判定记录，
没有判定记录的数据无法入库。
"""
from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    JSON,
)
from sqlalchemy.sql import func

from api.core.database import Base


class ComplianceVerdict(Base):
    """合规判定记录表"""

    __tablename__ = "compliance_verdicts"

    id = Column(Integer, primary_key=True, index=True)

    # 对外标识：调用方持此 ID 引用判定结果
    verdict_uid = Column(String(64), unique=True, index=True, nullable=False)

    profile_id = Column(
        Integer, ForeignKey("site_profiles.id"), nullable=True, index=True
    )
    target_url = Column(String(1000), nullable=False)

    # 判定结论：proceed | confirm_required | blocked
    decision = Column(String(30), nullable=False, index=True)

    # 四维取值
    dim_access = Column(String(10), nullable=False)          # A1-A4
    dim_authorization = Column(String(10), nullable=False)   # B1-B5
    dim_behavior = Column(String(10), nullable=False)        # C1-C5
    dim_data = Column(String(10), nullable=False)            # D1-D4

    # 逐维取证依据
    reasons = Column(JSON, nullable=True)
    # confirm_required 时的解锁条件
    conditions = Column(JSON, nullable=True)
    # blocked 时的替代数据源 [{kind, detail, coverage}]
    alternatives = Column(JSON, nullable=True)
    coverage_estimate = Column(Float, nullable=True)

    # 解锁令牌（补齐授权后由调用方携带重放）
    authorization_token = Column(String(128), nullable=True, index=True)
    token_expires_at = Column(DateTime(timezone=True), nullable=True)

    # 操作者与授权依据声明
    operator = Column(String(100), nullable=True)
    authorization_basis = Column(String(200), nullable=True)

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<ComplianceVerdict(uid={self.verdict_uid}, "
            f"decision={self.decision}, A={self.dim_access}, B={self.dim_authorization})>"
        )

    def to_dict(self) -> dict:
        return {
            "verdict_id": self.verdict_uid,
            "profile_id": self.profile_id,
            "target_url": self.target_url,
            "decision": self.decision,
            "dimensions": {
                "access": self.dim_access,
                "authorization": self.dim_authorization,
                "behavior": self.dim_behavior,
                "data": self.dim_data,
            },
            "reasons": self.reasons or [],
            "conditions": self.conditions or [],
            "alternatives": self.alternatives or [],
            "coverage_estimate": self.coverage_estimate,
            "has_token": bool(self.authorization_token),
            "token_expires_at": (
                self.token_expires_at.isoformat() if self.token_expires_at else None
            ),
            "operator": self.operator,
            "authorization_basis": self.authorization_basis,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
