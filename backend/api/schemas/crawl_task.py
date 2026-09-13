"""
采集任务相关 Pydantic 模型
=========================
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class CrawlTaskBase(BaseModel):
    """采集任务基础模型"""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    source_type: str = Field(..., pattern="^(api|web|local)$")
    config: Dict[str, Any] = Field(default_factory=dict)


class CrawlTaskCreate(CrawlTaskBase):
    """创建采集任务"""
    pass


class CrawlTaskUpdate(BaseModel):
    """更新采集任务"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class CrawlTaskResponse(CrawlTaskBase):
    """采集任务响应"""
    id: int
    status: str
    progress: int = Field(..., ge=0, le=100)
    result_count: int
    result_summary: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    execution_time: Optional[int] = None
    user_id: int
    dataset_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class CrawlConfig(BaseModel):
    """采集配置"""
    # 通用配置
    request_delay: float = Field(default=1.0, ge=0.1, le=60.0)
    max_retries: int = Field(default=3, ge=0, le=10)
    timeout: int = Field(default=30, ge=1, le=300)
    respect_robots: bool = True
    
    # API 配置
    url: Optional[str] = None
    method: str = Field(default="GET", pattern="^(GET|POST|PUT|DELETE)$")
    headers: Optional[Dict[str, str]] = None
    params: Optional[Dict[str, Any]] = None
    body: Optional[Dict[str, Any]] = None
    auth: Optional[Dict[str, Any]] = None
    
    # 网页配置
    selectors: Optional[Dict[str, str]] = None
    pagination: Optional[Dict[str, Any]] = None
    
    # 本地文件配置
    file_type: Optional[str] = Field(None, pattern="^(csv|json|xlsx|parquet)$")
    delimiter: Optional[str] = None
    encoding: Optional[str] = "utf-8"
