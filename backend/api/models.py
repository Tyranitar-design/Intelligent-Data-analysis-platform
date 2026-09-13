"""
数据模型定义
- DataSource: 数据源
- CrawlTask: 爬虫任务
- Dataset: 数据集
- MLModel: ML 模型
- PredictionTask: 预测任务
- Report: 分析报告
"""
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from api.database import Base


class DataSource(Base):
    """数据源"""
    __tablename__ = "data_sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, comment="名称")
    source_type = Column(String(20), nullable=False, comment="类型: ecommerce/finance/social")
    config = Column(JSON, default=dict, comment="配置")
    status = Column(String(20), default="active", comment="状态")
    description = Column(Text, default="", comment="描述")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    # 关联
    crawl_tasks = relationship("CrawlTask", back_populates="source")

    def __repr__(self):
        return f"<DataSource {self.name}>"


class CrawlTask(Base):
    """爬虫任务"""
    __tablename__ = "crawl_tasks"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("data_sources.id"), nullable=True, comment="Data Source ID")
    status = Column(String(20), default="pending", comment="状态: pending/running/completed/failed")
    config = Column(JSON, default=dict, comment="配置")
    result = Column(JSON, default=dict, comment="结果")
    total_items = Column(Integer, default=0, comment="采集总数")
    saved_items = Column(Integer, default=0, comment="保存数")
    error_message = Column(Text, default="", comment="错误信息")
    started_at = Column(DateTime, nullable=True, comment="开始时间")
    completed_at = Column(DateTime, nullable=True, comment="完成时间")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")

    # 关联
    source = relationship("DataSource", back_populates="crawl_tasks")

    def __repr__(self):
        return f"<CrawlTask {self.id} - {self.status}>"


class Dataset(Base):
    """数据集"""
    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, comment="名称")
    description = Column(Text, default="", comment="描述")
    dataset_type = Column(String(50), default="raw", comment="Type")
    table_name = Column(String(100), comment="表名")
    file_path = Column(String(255), comment="文件路径")
    row_count = Column(Integer, default=0, comment="行数")
    column_count = Column(Integer, default=0, comment="列数")
    columns_info = Column(JSON, default=list, comment="列信息")
    size_mb = Column(Float, default=0, comment="大小(MB)")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")

    def __repr__(self):
        return f"<Dataset {self.name}>"


class MLModel(Base):
    """机器学习模型"""
    __tablename__ = "ml_models"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, comment="名称")
    model_type = Column(String(20), nullable=False, comment="类型: classification/regression/clustering")
    algorithm = Column(String(50), nullable=False, comment="算法")
    dataset_id = Column(Integer, ForeignKey("datasets.id"), comment="数据集ID")
    params = Column(JSON, default=dict, comment="参数")
    metrics = Column(JSON, default=dict, comment="指标")
    features = Column(JSON, default=list, comment="特征列表")
    target = Column(String(100), comment="目标变量")
    model_path = Column(String(255), comment="模型路径")
    training_time = Column(Float, default=0, comment="训练时间(秒)")
    status = Column(String(20), default="created", comment="状态")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")

    # 关联
    predictions = relationship("PredictionTask", back_populates="model")

    def __repr__(self):
        return f"<MLModel {self.name} ({self.algorithm})>"


class PredictionTask(Base):
    """预测任务"""
    __tablename__ = "prediction_tasks"

    id = Column(Integer, primary_key=True, index=True)
    model_id = Column(Integer, ForeignKey("ml_models.id"), comment="模型ID")
    input_data = Column(JSON, default=dict, comment="输入数据")
    result = Column(JSON, default=dict, comment="预测结果")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")

    # 关联
    model = relationship("MLModel", back_populates="predictions")

    def __repr__(self):
        return f"<PredictionTask {self.id}>"


class Report(Base):
    """分析报告"""
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False, comment="标题")
    report_type = Column(String(20), nullable=False, comment="类型: daily/weekly/monthly")
    template = Column(String(50), default="default", comment="模板")
    content = Column(JSON, default=dict, comment="内容")
    status = Column(String(20), default="pending", comment="状态")
    file_path = Column(String(255), comment="文件路径")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")

    def __repr__(self):
        return f"<Report {self.title}>"