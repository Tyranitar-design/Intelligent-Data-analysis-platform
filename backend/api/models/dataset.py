"""
数据集模型
=========
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, BigInteger
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from api.core.database import Base


class Dataset(Base):
    """数据集表"""
    __tablename__ = "datasets"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    
    # 数据来源
    source_type = Column(String(50), nullable=False)  # crawl | upload | api
    source_id = Column(Integer, nullable=True)  # 关联的采集任务ID或数据源ID
    
    # 数据信息
    schema = Column(JSON, nullable=True)  # 字段定义
    row_count = Column(BigInteger, default=0, nullable=False)
    column_count = Column(Integer, default=0, nullable=False)
    size_bytes = Column(BigInteger, default=0, nullable=False)
    
    # 文件信息
    file_path = Column(String(500), nullable=True)  # 存储路径
    file_format = Column(String(50), nullable=True)  # csv | json | parquet | xlsx
    
    # 统计信息
    statistics = Column(JSON, nullable=True)  # 基本统计
    sample_data = Column(JSON, nullable=True)  # 样本数据（前5行）
    
    # 关联
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user = relationship("User", backref="datasets")
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<Dataset(id={self.id}, name={self.name}, rows={self.row_count})>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "source_type": self.source_type,
            "row_count": self.row_count,
            "column_count": self.column_count,
            "size_bytes": self.size_bytes,
            "file_format": self.file_format,
            "statistics": self.statistics,
            "sample_data": self.sample_data,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
