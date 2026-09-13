"""
Pydantic Schema 定义
API 请求和响应的数据模型
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# ==================== 数据源 ====================

class DataSourceBase(BaseModel):
    name: str = Field(..., description="名称")
    source_type: str = Field(..., description="类型: ecommerce/finance/social")
    config: Optional[Dict[str, Any]] = Field(default={}, description="配置")
    description: Optional[str] = Field(default="", description="描述")

class DataSourceCreate(DataSourceBase):
    pass

class DataSourceResponse(DataSourceBase):
    id: int
    status: Optional[str] = "active"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ==================== 爬虫任务 ====================

class CrawlTaskCreate(BaseModel):
    source_id: int = Field(..., description="数据源ID")
    config: Optional[Dict[str, Any]] = Field(default={}, description="配置")

class CrawlTaskResponse(BaseModel):
    id: int
    source_id: Optional[int] = None
    status: str
    config: Optional[Dict[str, Any]] = {}
    result: Optional[Dict[str, Any]] = {}
    total_items: Optional[int] = 0
    saved_items: Optional[int] = 0
    error_message: Optional[str] = ""
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ==================== 数据集 ====================

class DatasetCreate(BaseModel):
    name: str = Field(..., description="Name")
    description: Optional[str] = Field(default="", description="Description")
    dataset_type: Optional[str] = Field(default="raw", description="Type")
    file_path: Optional[str] = Field(default=None, description="File path")
    row_count: Optional[int] = Field(default=0, description="Row count")
    column_count: Optional[int] = Field(default=0, description="Column count")

class DatasetResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = ""
    dataset_type: Optional[str] = "raw"
    table_name: Optional[str] = None
    file_path: Optional[str] = None
    row_count: Optional[int] = 0
    column_count: Optional[int] = 0
    columns_info: Optional[List[Dict[str, Any]]] = []
    size_mb: Optional[float] = 0.0
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ==================== ML 模型 ====================

class MLModelCreate(BaseModel):
    name: str = Field(..., description="名称")
    model_type: str = Field(..., description="类型: classification/regression/clustering")
    algorithm: str = Field(..., description="算法")
    dataset_id: Optional[int] = Field(default=None, description="数据集ID")
    params: Optional[Dict[str, Any]] = Field(default={}, description="参数")
    features: Optional[List[str]] = Field(default=[], description="特征列表")
    target: Optional[str] = Field(default=None, description="目标变量")

class MLModelResponse(BaseModel):
    id: int
    name: str
    model_type: str
    algorithm: str
    dataset_id: Optional[int] = None
    params: Optional[Dict[str, Any]] = {}
    metrics: Optional[Dict[str, Any]] = {}
    features: Optional[List[str]] = []
    target: Optional[str] = None
    model_path: Optional[str] = None
    training_time: Optional[float] = 0
    status: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ==================== 预测任务 ====================

class PredictRequest(BaseModel):
    model_id: int = Field(..., description="模型ID")
    data: List[Dict[str, Any]] = Field(..., description="输入数据")

class PredictionResponse(BaseModel):
    id: int
    model_id: int
    input_data: Dict[str, Any]
    result: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== 报告 ====================

class ReportCreate(BaseModel):
    title: str = Field(..., description="标题")
    report_type: str = Field(..., description="类型: daily/weekly/monthly")
    template: Optional[str] = Field(default="default", description="模板")

class ReportResponse(BaseModel):
    id: int
    title: str
    report_type: Optional[str] = ""
    template: Optional[str] = "default"
    content: Optional[Dict[str, Any]] = {}
    status: Optional[str] = "created"
    file_path: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ==================== 通用响应 ====================

class SuccessResponse(BaseModel):
    success: bool = True
    message: str = "操作成功"

class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    detail: Optional[str] = None