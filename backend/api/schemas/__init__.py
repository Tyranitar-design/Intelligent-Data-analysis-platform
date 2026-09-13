"""
Pydantic 模型
============

用于请求/响应验证
"""
from pydantic import BaseModel, Field
from typing import Optional, Any, Dict, List
from datetime import datetime

# ==================== User ====================
from api.schemas.user import UserCreate, UserResponse, UserLogin

# ==================== Crawl Task ====================
from api.schemas.crawl_task import CrawlTaskCreate, CrawlTaskResponse, CrawlTaskUpdate

# ==================== Dataset ====================
from api.schemas.dataset import DatasetCreate, DatasetResponse, DatasetUpload

# ==================== Analysis Task ====================
from api.schemas.analysis_task import AnalysisTaskCreate, AnalysisTaskResponse

# ==================== Data Source ====================
class DataSourceCreate(BaseModel):
    name: str
    source_type: str  # api, web, local
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None

class DataSourceResponse(BaseModel):
    id: int
    name: str
    source_type: str
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    status: str = "active"
    created_at: Optional[datetime] = None
    class Config:
        from_attributes = True

# ==================== ML Model ====================
class MLModelCreate(BaseModel):
    algorithm: str
    task_type: str  # classification, regression, clustering
    target_column: str
    dataset_id: Optional[int] = None
    data: Optional[List[Dict[str, Any]]] = None
    test_size: float = 0.2
    tuning: Optional[Dict[str, Any]] = None
    cv_folds: int = 5

class MLModelResponse(BaseModel):
    id: int
    algorithm: str
    task_type: str
    model_id: Optional[str] = None
    evaluation: Optional[Dict[str, Any]] = None
    feature_importance: Optional[Dict[str, Any]] = None
    training_time_seconds: Optional[float] = None
    cv_mean: Optional[float] = None
    created_at: Optional[datetime] = None
    class Config:
        from_attributes = True

class PredictRequest(BaseModel):
    model_id: int
    data: List[Dict[str, Any]]

class PredictionResponse(BaseModel):
    predictions: List[Any]
    model_id: int

# ==================== Report ====================
class ReportCreate(BaseModel):
    name: Optional[str] = None
    report_type: str = "eda"  # eda, ml, full
    format: str = "markdown"  # markdown, html
    dataset_id: Optional[int] = None
    model_id: Optional[int] = None

class ReportResponse(BaseModel):
    id: int
    name: str
    report_type: str
    format: str
    content: Optional[str] = None
    html_content: Optional[str] = None
    created_at: Optional[datetime] = None
    class Config:
        from_attributes = True

# ==================== 通用响应 ====================
class SuccessResponse(BaseModel):
    success: bool = True
    message: str = "操作成功"
    data: Optional[Any] = None

__all__ = [
    "UserCreate", "UserResponse", "UserLogin",
    "CrawlTaskCreate", "CrawlTaskResponse", "CrawlTaskUpdate",
    "DatasetCreate", "DatasetResponse", "DatasetUpload",
    "AnalysisTaskCreate", "AnalysisTaskResponse",
    "DataSourceCreate", "DataSourceResponse",
    "MLModelCreate", "MLModelResponse", "PredictRequest", "PredictionResponse",
    "ReportCreate", "ReportResponse",
    "SuccessResponse",
]
