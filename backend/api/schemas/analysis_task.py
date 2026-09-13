"""分析任务相关 Schema"""
from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime


class AnalysisTaskCreate(BaseModel):
    dataset_id: Optional[int] = None
    analysis_type: str  # eda, statistics, feature_engineering
    config: Optional[dict] = None


class AnalysisTaskResponse(BaseModel):
    id: int
    dataset_id: Optional[int] = None
    analysis_type: str
    status: str = "pending"
    result: Optional[Any] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True
