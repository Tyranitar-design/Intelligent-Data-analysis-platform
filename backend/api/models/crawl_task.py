"""
采集任务模型
===========
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from api.core.database import Base


class CrawlTask(Base):
    """采集任务表"""
    __tablename__ = "crawl_tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    
    # 任务配置
    source_type = Column(String(50), nullable=False)  # api | web | local
    config = Column(JSON, nullable=False, default=dict)
    
    # 任务状态
    status = Column(String(50), default="pending", nullable=False)  # pending | running | completed | failed | cancelled
    progress = Column(Integer, default=0, nullable=False)  # 0-100
    
    # 结果
    result_count = Column(Integer, default=0, nullable=False)
    result_summary = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # 执行信息
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    execution_time = Column(Integer, nullable=True)  # 秒
    
    # 关联
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user = relationship("User", backref="crawl_tasks")
    
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=True)
    dataset = relationship("Dataset", backref="crawl_task")
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<CrawlTask(id={self.id}, name={self.name}, status={self.status})>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "source_type": self.source_type,
            "status": self.status,
            "progress": self.progress,
            "result_count": self.result_count,
            "error_message": self.error_message,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
