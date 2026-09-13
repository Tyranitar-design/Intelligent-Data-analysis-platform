"""数据集相关 Schema"""
from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime


class DatasetCreate(BaseModel):
    name: str
    description: Optional[str] = None
    source_type: Optional[str] = None


class DatasetUpload(BaseModel):
    filename: str
    format: Optional[str] = None  # csv, json, excel, parquet


class DatasetResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    source_type: Optional[str] = None
    row_count: Optional[int] = None
    column_count: Optional[int] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
