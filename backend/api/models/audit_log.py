"""
审计日志模型
============

记录谁在什么时候对什么做了什么。审计是"可追溯"的落点：
采集、判定、授权解锁、数据集物化、导出都写审计。

原则：入参只存摘要哈希，不存原文——避免令牌、Cookie 这类敏感值进入日志。
"""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, JSON
from sqlalchemy.sql import func

from api.core.database import Base


class AuditLog(Base):
    """审计日志表"""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    ts = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    # 操作者标识（MCP principal / 用户名 / system）
    principal_id = Column(String(100), nullable=True, index=True)
    # 动作名：discover.analyze / collect.run / dataset.materialize / export 等
    action = Column(String(80), nullable=False, index=True)
    target_type = Column(String(40), nullable=True)
    target_id = Column(String(80), nullable=True)

    # 关联的合规判定（能审计到"依据哪条判定执行"）
    verdict_id = Column(
        Integer, ForeignKey("compliance_verdicts.id"), nullable=True, index=True
    )

    # 入参摘要（哈希，不存原文）
    request_digest = Column(String(64), nullable=True)
    # ok | denied | error
    result = Column(String(20), nullable=False, default="ok")
    # 结构化补充信息（不含敏感值）
    detail = Column(JSON, nullable=True)

    ip = Column(String(60), nullable=True)
    user_agent = Column(String(300), nullable=True)

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, action={self.action}, result={self.result})>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "ts": self.ts.isoformat() if self.ts else None,
            "principal_id": self.principal_id,
            "action": self.action,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "verdict_row_id": self.verdict_id,
            "request_digest": self.request_digest,
            "result": self.result,
            "detail": self.detail or {},
            "ip": self.ip,
        }
