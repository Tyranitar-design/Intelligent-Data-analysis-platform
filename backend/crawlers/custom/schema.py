# -*- coding: utf-8 -*-
"""
自定义采集配置 Schema
====================
"""
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class SourceType(str, Enum):
    """采集源类型"""
    WEB = "web"
    API = "api"
    LOCAL = "local"


class WebConfig(BaseModel):
    """网页爬取配置"""
    url: str = Field(..., description="目标 URL")
    method: str = Field(default="GET", description="HTTP 方法")
    headers: Dict[str, str] = Field(default_factory=dict, description="自定义请求头")
    selectors: Dict[str, str] = Field(default_factory=dict, description="CSS 选择器映射")
    container_selector: Optional[str] = Field(default=None, description="列表项容器选择器")
    item_selectors: Dict[str, str] = Field(default_factory=dict, description="列表项字段选择器映射")
    pagination: Optional[Dict[str, Any]] = Field(default=None, description="分页配置")
    use_scrapling: bool = Field(default=False, description="是否使用 Scrapling")
    stealthy: bool = Field(default=False, description="是否使用隐身模式")


class ApiConfig(BaseModel):
    """API 采集配置"""
    endpoint: str = Field(..., description="API 端点 URL")
    method: str = Field(default="GET", description="HTTP 方法")
    params: Dict[str, Any] = Field(default_factory=dict, description="查询参数")
    headers: Dict[str, Any] = Field(default_factory=dict, description="请求头")
    body: Optional[Dict[str, Any]] = Field(default=None, description="请求体")
    auth: Optional[Dict[str, str]] = Field(default=None, description="认证配置")
    data_path: str = Field(default="", description="数据路径")
    pagination: Optional[Dict[str, Any]] = Field(default=None, description="分页配置")


class LocalConfig(BaseModel):
    """本地文件配置"""
    file_path: str = Field(..., description="文件路径")
    file_type: str = Field(default="csv", description="文件类型")
    encoding: Optional[str] = Field(default=None, description="文件编码")
    delimiter: str = Field(default=",", description="CSV 分隔符")
    sheet_name: Any = Field(default=0, description="Excel Sheet")
    skip_rows: int = Field(default=0, description="跳过行数")


class CrawlConfigSchema(BaseModel):
    """用户自定义采集配置"""
    name: str = Field(..., min_length=1, max_length=100, description="任务名称")
    source_type: SourceType = Field(..., description="采集源类型")
    web: Optional[WebConfig] = Field(default=None)
    api: Optional[ApiConfig] = Field(default=None)
    local: Optional[LocalConfig] = Field(default=None)
    request_delay: float = Field(default=1.0, ge=0, le=60)
    max_retries: int = Field(default=3, ge=0, le=10)
    timeout: int = Field(default=30, ge=5, le=300)
    respect_robots: bool = Field(default=True)
    output_format: str = Field(default="json")
    
    @field_validator("web")
    @classmethod
    def validate_web(cls, v, info):
        if info.data.get("source_type") == SourceType.WEB and v is None:
            raise ValueError("source_type=web 时必须提供 web 配置")
        return v
    
    @field_validator("api")
    @classmethod
    def validate_api(cls, v, info):
        if info.data.get("source_type") == SourceType.API and v is None:
            raise ValueError("source_type=api 时必须提供 api 配置")
        return v
    
    @field_validator("local")
    @classmethod
    def validate_local(cls, v, info):
        if info.data.get("source_type") == SourceType.LOCAL and v is None:
            raise ValueError("source_type=local 时必须提供 local 配置")
        return v
