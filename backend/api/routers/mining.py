"""
数据挖掘路由 - 支持从数据库读取数据
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional

from api.database import get_db
from mining.service import MiningService
from pydantic import BaseModel, Field

router = APIRouter()

mining_service = MiningService()


# ==================== 从数据库读取 ====================

@router.get("/db/data/{source}")
async def get_mining_data_from_db(
    source: str,
    platform: str = None,
    keyword: str = None,
    limit: int = 1000
):
    """从数据库获取挖掘数据"""
    df = mining_service.load_from_db(source=source, platform=platform, keyword=keyword, limit=limit)
    if df.empty:
        raise HTTPException(status_code=404, detail=f"No data for source={source}")

    import math
    result = df.to_dict(orient="records")
    for row in result:
        for k, v in row.items():
            if v is not None and isinstance(v, float) and math.isnan(v):
                row[k] = None

    return {"count": len(result), "columns": list(df.columns), "data": result}


# ==================== 关联规则挖掘 ====================

class AprioriRequest(BaseModel):
    source: str = Field("ecommerce", description="Data source")
    platform: Optional[str] = None
    keyword: Optional[str] = None
    item_col: str = Field("brand", description="Item column for association")
    group_col: str = Field("keyword", description="Group column (transaction ID)")
    min_support: float = Field(0.1, ge=0.01, le=1.0)
    min_confidence: float = Field(0.5, ge=0.01, le=1.0)
    limit: int = Field(1000, ge=10, le=10000)


@router.post("/apriori")
async def run_apriori(request: AprioriRequest):
    """关联规则挖掘 (Apriori)"""
    df = mining_service.load_from_db(
        source=request.source,
        platform=request.platform,
        keyword=request.keyword,
        limit=request.limit
    )

    if df.empty:
        raise HTTPException(status_code=404, detail=f"No data for source={request.source}")

    config = {
        "item_col": request.item_col,
        "group_col": request.group_col,
        "min_support": request.min_support,
        "min_confidence": request.min_confidence,
    }

    try:
        result = mining_service.apriori(df, config)
        result["source"] = request.source
        result["record_count"] = len(df)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 异常检测 ====================

class IsolationForestRequest(BaseModel):
    source: str = Field("stock", description="Data source")
    platform: Optional[str] = None
    features: Optional[List[str]] = None
    contamination: float = Field(0.1, ge=0.01, le=0.5)
    n_estimators: int = Field(100, ge=10, le=500)
    limit: int = Field(1000, ge=10, le=10000)


@router.post("/isolation-forest")
async def run_isolation_forest(request: IsolationForestRequest):
    """Isolation Forest 异常检测"""
    df = mining_service.load_from_db(
        source=request.source,
        platform=request.platform,
        limit=request.limit
    )

    if df.empty:
        raise HTTPException(status_code=404, detail=f"No data for source={request.source}")

    # 如果没有指定特征，自动选择数值列
    features = request.features
    if not features:
        import numpy as np
        features = df.select_dtypes(include=[np.number]).columns.tolist()
        # 排除 id 列
        features = [c for c in features if c not in ('id', 'source_record_id')]

    if not features:
        raise HTTPException(status_code=400, detail="No numeric features found")

    config = {
        "features": features,
        "contamination": request.contamination,
        "n_estimators": request.n_estimators,
    }

    try:
        result = mining_service.isolation_forest(df, config)
        result["source"] = request.source
        result["record_count"] = len(df)
        result["features_used"] = features
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 时序模式挖掘 ====================

class TimeSeriesRequest(BaseModel):
    source: str = Field("stock", description="Data source")
    platform: Optional[str] = None
    date_col: str = Field("date", description="Date column")
    value_col: str = Field("close", description="Value column")
    window: int = Field(5, ge=2, le=30)
    limit: int = Field(500, ge=10, le=10000)


@router.post("/time-series-patterns")
async def run_time_series_patterns(request: TimeSeriesRequest):
    """时序模式挖掘"""
    df = mining_service.load_from_db(
        source=request.source,
        platform=request.platform,
        limit=request.limit
    )

    if df.empty:
        raise HTTPException(status_code=404, detail=f"No data for source={request.source}")

    config = {
        "date_col": request.date_col,
        "value_col": request.value_col,
        "window": request.window,
    }

    try:
        result = mining_service.time_series_patterns(df, config)
        result["source"] = request.source
        result["record_count"] = len(df)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
