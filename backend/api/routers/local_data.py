# -*- coding: utf-8 -*-
"""
本地数据文件 API - 从 JSON 文件加载数据用于 ML
"""
import os
import json
import glob
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import pandas as pd

router = APIRouter()

# 数据目录
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "raw")

# 支持的数据类型
DATA_TYPES = {
    "jd": "京东商品数据",
    "taobao": "淘宝商品数据",
    "pdd": "拼多多数据",
    "stock": "股票数据",
    "energy": "能源数据",
    "news": "新闻数据",
}


class DataFileInfo(BaseModel):
    """数据文件信息"""
    filename: str
    filepath: str
    platform: str
    size: int
    record_count: int
    fields: List[str]


class DatasetPreview(BaseModel):
    """数据集预览"""
    columns: List[str]
    dtypes: Dict[str, str]
    sample_data: List[Dict]
    total_rows: int
    numeric_columns: List[str]
    categorical_columns: List[str]


@router.get("/files", response_model=List[DataFileInfo])
async def list_data_files(platform: str = None, keyword: str = None):
    """
    获取本地数据文件列表
    
    Args:
        platform: 过滤平台 (jd, taobao, stock, etc.)
        keyword: 关键词过滤
    
    Returns:
        数据文件列表
    """
    if not os.path.exists(DATA_DIR):
        raise HTTPException(status_code=404, detail="数据目录不存在")
    
    # 获取所有 JSON 文件
    json_files = glob.glob(os.path.join(DATA_DIR, "*.json"))
    
    files = []
    for filepath in json_files:
        filename = os.path.basename(filepath)
        
        # 解析文件名获取平台
        platform_type = None
        for p in DATA_TYPES.keys():
            if p in filename.lower():
                platform_type = p
                break
        
        # 过滤
        if platform and platform_type != platform:
            continue
        if keyword and keyword not in filename.lower():
            continue
        
        # 读取文件统计
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            record_count = len(data) if isinstance(data, list) else 1
            fields = list(data[0].keys()) if isinstance(data, list) and data else []
            
            files.append(DataFileInfo(
                filename=filename,
                filepath=filepath,
                platform=platform_type or "unknown",
                size=os.path.getsize(filepath),
                record_count=record_count,
                fields=fields
            ))
        except Exception as e:
            continue
    
    # 按记录数排序
    files.sort(key=lambda x: x.record_count, reverse=True)
    
    return files


@router.get("/preview/{filename}", response_model=DatasetPreview)
async def preview_data_file(filename: str):
    """
    预览数据文件内容
    
    Args:
        filename: 文件名
    
    Returns:
        数据集预览信息
    """
    filepath = os.path.join(DATA_DIR, filename)
    
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="文件不存在")
    
    try:
        # 读取数据
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not isinstance(data, list) or not data:
            raise ValueError("数据格式错误")
        
        # 转为 DataFrame
        df = pd.DataFrame(data)
        
        # 分类列类型
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
        
        # 构建响应
        preview = DatasetPreview(
            columns=df.columns.tolist(),
            dtypes=df.dtypes.apply(str).to_dict(),
            sample_data=df.head(5).to_dict('records'),
            total_rows=len(df),
            numeric_columns=numeric_cols,
            categorical_columns=categorical_cols
        )
        
        return preview
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"读取失败: {str(e)}")


@router.post("/load/{filename}")
async def load_data_for_ml(filename: str, config: Dict[str, Any] = None):
    """
    加载数据用于 ML 训练
    
    Args:
        filename: 文件名
        config: 配置（列选择等）
    
    Returns:
        训练用数据
    """
    filepath = os.path.join(DATA_DIR, filename)
    
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="文件不存在")
    
    try:
        # 读取数据
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        df = pd.DataFrame(data)
        
        # 应用配置
        if config:
            # 选择列
            if 'columns' in config and config['columns']:
                df = df[config['columns']]
            
            # 过滤行
            if 'filters' in config:
                for col, val in config['filters'].items():
                    if col in df.columns:
                        df = df[df[col] == val]
            
            # 限制数量
            if 'limit' in config:
                df = df.head(config['limit'])
        
        # 返回数据信息
        return {
            "filename": filename,
            "total_rows": len(df),
            "columns": df.columns.tolist(),
            "numeric_columns": df.select_dtypes(include=['number']).columns.tolist(),
            "categorical_columns": df.select_dtypes(include=['object']).columns.tolist(),
            "data": df.to_dict('records')[:100]  # 返回前100条
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"加载失败: {str(e)}")


@router.get("/sample/{filename}")
async def get_sample_data(filename: str, limit: int = 10):
    """
    获取样本数据
    
    Args:
        filename: 文件名
        limit: 返回条数
    
    Returns:
        样本数据
    """
    filepath = os.path.join(DATA_DIR, filename)
    
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="文件不存在")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if isinstance(data, list):
            return data[:limit]
        else:
            return [data]
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"读取失败: {str(e)}")