"""
数据源配置模型
=============
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from api.core.database import Base


class DataSource(Base):
    """数据源配置表"""
    __tablename__ = "data_sources"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    
    # 数据源类型
    source_type = Column(String(50), nullable=False)  # api | web | database | file
    
    # 连接配置
    config = Column(JSON, nullable=False, default=dict)
    
    # 状态
    is_active = Column(Boolean, default=True, nullable=False)
    is_public = Column(Boolean, default=False, nullable=False)  # 是否公开给所有用户
    
    # 统计
    last_used = Column(DateTime(timezone=True), nullable=True)
    use_count = Column(Integer, default=0, nullable=False)
    
    # 关联
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user = relationship("User", backref="data_sources")
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<DataSource(id={self.id}, name={self.name}, type={self.source_type})>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "source_type": self.source_type,
            "is_active": self.is_active,
            "is_public": self.is_public,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "use_count": self.use_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
