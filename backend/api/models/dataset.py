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
    file_format = Column(String(50), nullable=True)  # csv | json | parquet | xlsx | table
    # 物化表名：采集产出的数据集会落成真实表，供分析层直接 SQL 读取
    table_name = Column(String(100), nullable=True)
    
    # 统计信息
    statistics = Column(JSON, nullable=True)  # 基本统计
    sample_data = Column(JSON, nullable=True)  # 样本数据（前5行）
    
    # 关联：采集产出的数据集可以没有用户归属（系统任务产出属正常情况）
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    user = relationship("User", backref="datasets")

    # 采集来源与血缘
    collect_job_id = Column(
        Integer, ForeignKey("collect_jobs.id"), nullable=True, index=True
    )
    profile_id = Column(
        Integer, ForeignKey("site_profiles.id"), nullable=True, index=True
    )
    # 字段级血缘 [{field, item_field, extractor_rule, profile_id}]
    lineage = Column(JSON, nullable=True)
    # PII 处理策略留痕 {field: "hashed" | "binned" | "generalized" | "dropped"}
    pii_policy = Column(JSON, nullable=True)
    
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
            "collect_job_id": self.collect_job_id,
            "profile_id": self.profile_id,
            "row_count": self.row_count,
            "column_count": self.column_count,
            "size_bytes": self.size_bytes,
            "file_format": self.file_format,
            "statistics": self.statistics,
            "sample_data": self.sample_data,
            "schema": self.schema,
            "lineage": self.lineage,
            "pii_policy": self.pii_policy,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
