"""
分析任务模型
===========
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from api.core.database import Base


class AnalysisTask(Base):
    """分析任务表"""
    __tablename__ = "analysis_tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    
    # 任务类型
    task_type = Column(String(50), nullable=False)  # eda | ml_train | ml_predict | dl | mining
    
    # 配置
    config = Column(JSON, nullable=False, default=dict)
    
    # 状态
    status = Column(String(50), default="pending", nullable=False)
    progress = Column(Integer, default=0, nullable=False)
    
    # 结果
    result = Column(JSON, nullable=True)
    metrics = Column(JSON, nullable=True)  # 评估指标
    visualizations = Column(JSON, nullable=True)  # 可视化配置
    
    # 模型信息
    model_path = Column(String(500), nullable=True)
    model_metrics = Column(JSON, nullable=True)
    
    # 执行信息
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    execution_time = Column(Integer, nullable=True)
    
    # 关联
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user = relationship("User", backref="analysis_tasks")
    
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False)
    dataset = relationship("Dataset", backref="analysis_tasks")
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<AnalysisTask(id={self.id}, name={self.name}, type={self.task_type})>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "task_type": self.task_type,
            "status": self.status,
            "progress": self.progress,
            "metrics": self.metrics,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
