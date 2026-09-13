"""
深度学习路由 - 支持从数据库读取数据
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List, Optional

from dl.service import DLService
from pydantic import BaseModel, Field

router = APIRouter()

dl_service = DLService()


# ==================== 从数据库读取 ====================

@router.get("/db/data/{source}")
async def get_dl_data_from_db(
    source: str,
    platform: str = None,
    keyword: str = None,
    symbols: str = None,
    limit: int = 1000
):
    """从数据库获取DL数据"""
    if source == "stock" and symbols:
        sym_list = [s.strip() for s in symbols.split(",")]
        df = dl_service.load_stock_for_dl(symbols=sym_list, limit=limit)
    else:
        df = dl_service.load_from_db(source=source, platform=platform, keyword=keyword, limit=limit)

    if df.empty:
        raise HTTPException(status_code=404, detail=f"No data for source={source}")

    import math
    result = df.to_dict(orient="records")
    for row in result:
        for k, v in row.items():
            if v is not None and isinstance(v, float) and math.isnan(v):
                row[k] = None

    return {"count": len(result), "columns": list(df.columns), "data": result}


# ==================== LSTM 时间序列预测 ====================

class LSTMTrainRequest(BaseModel):
    source: str = Field("stock", description="Data source")
    platform: Optional[str] = None
    symbols: Optional[str] = None
    target_col: str = Field("close", description="Target column")
    seq_length: int = Field(5, ge=2, le=30)
    epochs: int = Field(50, ge=1, le=500)
    lr: float = Field(0.001, ge=0.0001, le=0.1)
    hidden_size: int = Field(64, ge=16, le=256)
    limit: int = Field(500, ge=20, le=10000)


@router.post("/train/lstm")
async def train_lstm(request: LSTMTrainRequest):
    """训练 LSTM 时间序列预测"""
    if request.source == "stock" and request.symbols:
        sym_list = [s.strip() for s in request.symbols.split(",")]
        df = dl_service.load_stock_for_dl(symbols=sym_list, limit=request.limit)
    else:
        df = dl_service.load_from_db(
            source=request.source,
            platform=request.platform,
            limit=request.limit
        )

    if df.empty:
        raise HTTPException(status_code=404, detail=f"No data for source={request.source}")

    if request.target_col not in df.columns:
        raise HTTPException(status_code=400, detail=f"Column '{request.target_col}' not found")

    config = {
        "target_col": request.target_col,
        "seq_length": request.seq_length,
        "epochs": request.epochs,
        "lr": request.lr,
        "hidden_size": request.hidden_size,
    }

    try:
        result = dl_service.train_lstm(df, config)
        result["source"] = request.source
        result["record_count"] = len(df)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 神经网络分类 ====================

class ClassifierTrainRequest(BaseModel):
    source: str = Field("ecommerce", description="Data source")
    platform: Optional[str] = None
    keyword: Optional[str] = None
    features: Optional[List[str]] = None
    target: str = Field("brand", description="Target column")
    epochs: int = Field(50, ge=1, le=500)
    lr: float = Field(0.001, ge=0.0001, le=0.1)
    limit: int = Field(1000, ge=10, le=10000)


@router.post("/train/classifier")
async def train_classifier(request: ClassifierTrainRequest):
    """训练神经网络分类器"""
    df = dl_service.load_from_db(
        source=request.source,
        platform=request.platform,
        keyword=request.keyword,
        limit=request.limit
    )

    if df.empty:
        raise HTTPException(status_code=404, detail=f"No data for source={request.source}")

    import numpy as np
    features = request.features
    if not features:
        features = df.select_dtypes(include=[np.number]).columns.tolist()
        features = [c for c in features if c not in ('id', 'source_record_id')]

    if not features:
        raise HTTPException(status_code=400, detail="No numeric features found")

    if request.target not in df.columns:
        raise HTTPException(status_code=400, detail=f"Column '{request.target}' not found")

    config = {
        "features": features,
        "target": request.target,
        "epochs": request.epochs,
        "lr": request.lr,
    }

    try:
        result = dl_service.train_classifier(df, config)
        result["source"] = request.source
        result["record_count"] = len(df)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Autoencoder 异常检测 ====================

class AutoencoderTrainRequest(BaseModel):
    source: str = Field("stock", description="Data source")
    platform: Optional[str] = None
    features: Optional[List[str]] = None
    epochs: int = Field(50, ge=1, le=500)
    lr: float = Field(0.001, ge=0.0001, le=0.1)
    encoding_dim: int = Field(8, ge=2, le=64)
    threshold_percentile: float = Field(95, ge=80, le=99)
    limit: int = Field(1000, ge=10, le=10000)


@router.post("/train/autoencoder")
async def train_autoencoder(request: AutoencoderTrainRequest):
    """训练 Autoencoder 异常检测"""
    df = dl_service.load_from_db(
        source=request.source,
        platform=request.platform,
        limit=request.limit
    )

    if df.empty:
        raise HTTPException(status_code=404, detail=f"No data for source={request.source}")

    import numpy as np
    features = request.features
    if not features:
        features = df.select_dtypes(include=[np.number]).columns.tolist()
        features = [c for c in features if c not in ('id', 'source_record_id')]

    if not features:
        raise HTTPException(status_code=400, detail="No numeric features found")

    config = {
        "features": features,
        "epochs": request.epochs,
        "lr": request.lr,
        "encoding_dim": request.encoding_dim,
        "threshold_percentile": request.threshold_percentile,
    }

    try:
        result = dl_service.train_autoencoder(df, config)
        result["source"] = request.source
        result["record_count"] = len(df)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 已保存模型 ====================

@router.get("/models")
async def list_dl_models():
    """列出已保存的深度学习模型"""
    models = dl_service.list_models()
    return {"count": len(models), "models": models}
