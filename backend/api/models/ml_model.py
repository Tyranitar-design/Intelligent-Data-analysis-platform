"""ML 模型存储"""
from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Text
from datetime import datetime
from api.core.database import Base


class MLModel(Base):
    __tablename__ = "ml_models"

    id = Column(Integer, primary_key=True, index=True)
    algorithm = Column(String(100), nullable=False)
    task_type = Column(String(50), nullable=False)  # classification, regression, clustering
    model_path = Column(String(500), nullable=True)
    metrics = Column(JSON, default=dict)
    feature_importance = Column(JSON, nullable=True)
    training_time_seconds = Column(Float, nullable=True)
    cv_mean = Column(Float, nullable=True)
    params = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
