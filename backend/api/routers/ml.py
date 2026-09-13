"""
机器学习路由 - 支持从数据库读取数据
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any

from api.database import get_db
from api.models import MLModel, Dataset
from api.schemas import (
    MLModelCreate, MLModelResponse,
    PredictRequest, PredictionResponse,
    SuccessResponse
)
from ml.service import MLService
from analysis.service import AnalysisService
from database.service import DataService
from pydantic import BaseModel, Field

router = APIRouter()

ml_service = MLService()
analysis_service = AnalysisService()
data_service = DataService()


# ==================== 算法列表 ====================

@router.get("/algorithms")
async def list_algorithms():
    """获取可用算法列表"""
    return ml_service.list_algorithms()


# ==================== 模型管理 ====================

@router.get("/models", response_model=List[MLModelResponse])
async def list_models(db: Session = Depends(get_db)):
    """获取模型列表"""
    models = db.query(MLModel).all()
    return models


@router.post("/models", response_model=MLModelResponse)
async def create_model(data: MLModelCreate, db: Session = Depends(get_db)):
    """创建模型（注册，不训练）"""
    model = MLModel(**data.model_dump())
    db.add(model)
    db.commit()
    db.refresh(model)
    return model


@router.get("/models/{model_id}", response_model=MLModelResponse)
async def get_model(model_id: int, db: Session = Depends(get_db)):
    """获取模型详情"""
    model = db.query(MLModel).filter(MLModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return model


@router.delete("/models/{model_id}", response_model=SuccessResponse)
async def delete_model(model_id: int, db: Session = Depends(get_db)):
    """删除模型"""
    model = db.query(MLModel).filter(MLModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    db.delete(model)
    db.commit()
    return SuccessResponse(message="Model deleted")


# ==================== 从数据库加载 & 训练 ====================

@router.get("/db/data/{source}")
async def get_ml_data_from_db(
    source: str,
    platform: str = None,
    keyword: str = None,
    limit: int = 1000
):
    """从数据库获取ML数据"""
    df = ml_service.load_from_db(source=source, platform=platform, keyword=keyword, limit=limit)
    if df.empty:
        raise HTTPException(status_code=404, detail=f"No data for source={source}")

    import math
    result = df.to_dict(orient="records")
    for row in result:
        for k, v in row.items():
            if v is not None and isinstance(v, float) and math.isnan(v):
                row[k] = None

    return {"count": len(result), "columns": list(df.columns), "data": result}


class TrainFromDBRequest(BaseModel):
    source: str = Field(..., description="Data source: stock, energy, ecom")
    platform: Optional[str] = None
    keyword: Optional[str] = None
    model_type: str = Field(..., description="classification/regression/clustering")
    algorithm: str = Field(..., description="Algorithm name")
    features: Optional[List[str]] = None
    target: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    limit: int = Field(1000, ge=10, le=10000)


@router.post("/train/db")
async def train_from_db(request: TrainFromDBRequest):
    """从数据库加载数据并训练模型"""
    # 加载数据
    df = ml_service.load_from_db(
        source=request.source,
        platform=request.platform,
        keyword=request.keyword,
        limit=request.limit
    )

    if df.empty:
        raise HTTPException(status_code=404, detail=f"No data in DB for source={request.source}")

    config = {
        "model_type": request.model_type,
        "algorithm": request.algorithm,
        "features": request.features or [],
        "target": request.target,
        "params": request.params or {},
    }

    try:
        result = ml_service.train(df, config)
        result["source"] = request.source
        result["record_count"] = len(df)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 传统训练（文件回退） ====================

class TrainRequest(BaseModel):
    source_type: str
    model_type: str
    algorithm: str
    features: List[str]
    target: Optional[str] = None
    params: Optional[Dict[str, Any]] = None


@router.post("/train", response_model=SuccessResponse)
async def train_model(request: TrainRequest, db: Session = Depends(get_db)):
    """训练模型（先尝试数据库，回退到文件）"""
    # 尝试从数据库加载
    df = analysis_service.load_from_db(source=request.source_type)

    if df.empty:
        # 回退到文件
        filepath = analysis_service.get_latest_file(request.source_type)
        if not filepath:
            raise HTTPException(status_code=404, detail=f"No data for: {request.source_type}")
        df = analysis_service.load_data(filepath)

    config = {
        "model_type": request.model_type,
        "algorithm": request.algorithm,
        "features": request.features,
        "target": request.target,
        "params": request.params or {},
    }

    result = ml_service.train(df, config)

    # 保存模型记录
    model = MLModel(
        name=f"{request.algorithm}_{request.model_type}",
        model_type=request.model_type,
        algorithm=request.algorithm,
        features=request.features,
        target=request.target,
        params=request.params or {},
        status="completed",
        metrics=result.get("metrics", {}),
        model_path=result.get("model_path"),
        training_time=result.get("training_time", 0),
    )
    db.add(model)
    db.commit()
    db.refresh(model)

    return SuccessResponse(message=f"Model {model.id} trained successfully")


# ==================== 模型预测 ====================

@router.post("/predict")
async def predict(request: PredictRequest, db: Session = Depends(get_db)):
    """模型预测"""
    model = db.query(MLModel).filter(MLModel.id == request.model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    if not model.model_path:
        raise HTTPException(status_code=400, detail="Model not trained yet")

    import pandas as pd
    df = pd.DataFrame(request.data)

    try:
        predictions = ml_service.predict(model.model_path, df)
        return {
            "model_id": request.model_id,
            "predictions": predictions,
            "count": len(predictions)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 从本地 JSON 训练（增强版） ====================

class TrainFromDataRequest(BaseModel):
    data: List[Dict[str, Any]] = Field(..., description="训练数据")
    model_type: str = Field(..., description="classification/regression/clustering")
    algorithm: str = Field(..., description="算法名称")
    features: List[str] = Field(default_factory=list, description="特征列")
    target: Optional[str] = Field(None, description="目标列")
    params: Dict[str, Any] = Field(default_factory=dict, description="模型参数")
    test_size: float = Field(0.2, ge=0.1, le=0.5, description="测试集比例")


@router.post("/train/enhanced")
async def train_enhanced(request: TrainFromDataRequest, db: Session = Depends(get_db)):
    """
    增强训练 API - 支持从本地 JSON 加载数据，返回可视化数据
    """
    import pandas as pd
    import numpy as np
    
    # 准备数据
    df = pd.DataFrame(request.data)
    
    # 如果没有指定特征，使用所有数值列
    if not request.features:
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if request.target and request.target in numeric_cols:
            numeric_cols.remove(request.target)
        features = numeric_cols[:5]  # 默认取前5个
    else:
        features = request.features
    
    config = {
        "model_type": request.model_type,
        "algorithm": request.algorithm,
        "features": features,
        "target": request.target,
        "params": request.params or {},
        "test_size": request.test_size,
    }
    
    try:
        # 训练模型
        result = ml_service.train(df, config)
        
        # 生成可视化数据
        visualizations = generate_visualizations(df, result, features, request.target)
        result["visualizations"] = visualizations
        
        # 保存模型记录
        model = MLModel(
            name=f"{request.algorithm}_{request.model_type}_{int(time.time())}",
            model_type=request.model_type,
            algorithm=request.algorithm,
            features=features,
            target=request.target,
            params=request.params or {},
            status="completed",
            metrics=result.get("metrics", {}),
            model_path=result.get("model_path"),
            training_time=result.get("training_time", 0),
        )
        db.add(model)
        db.commit()
        db.refresh(model)
        result["model_id"] = model.id
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def generate_visualizations(df, result, features, target):
    """生成可视化数据"""
    import pandas as pd
    import numpy as np
    
    visualizations = {}
    
    try:
        # 1. 柱状图 - 特征重要性（如果有）
        if result.get("feature_importance"):
            visualizations["bar"] = {
                "type": "bar",
                "title": "特征重要性",
                "data": [
                    {"name": f, "value": v} 
                    for f, v in result["feature_importance"].items()
                ]
            }
        else:
            # 使用数值特征的统计信息
            numeric_df = df.select_dtypes(include=[np.number])
            if not numeric_df.empty:
                means = numeric_df.mean().head(10)
                visualizations["bar"] = {
                    "type": "bar",
                    "title": "特征均值统计",
                    "data": [
                        {"name": str(k), "value": float(v)} 
                        for k, v in means.items()
                    ]
                }
        
        # 2. 散点图 - 特征关系
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if len(numeric_cols) >= 2:
            x_col = numeric_cols[0]
            y_col = numeric_cols[1] if len(numeric_cols) > 1 else numeric_cols[0]
            sample = df[[x_col, y_col]].dropna().head(100)
            visualizations["scatter"] = {
                "type": "scatter",
                "title": f"{x_col} vs {y_col}",
                "xAxis": x_col,
                "yAxis": y_col,
                "data": [
                    {"x": float(row[x_col]), "y": float(row[y_col])}
                    for _, row in sample.iterrows()
                ]
            }
        
        # 3. 热力图 - 相关性矩阵
        numeric_df = df.select_dtypes(include=[np.number])
        if numeric_df.shape[1] >= 2:
            corr = numeric_df.corr()
            # 转换为热力图数据
            heatmap_data = []
            for i, col1 in enumerate(corr.columns):
                for j, col2 in enumerate(corr.columns):
                    heatmap_data.append({
                        "x": col1,
                        "y": col2,
                        "value": float(corr.iloc[i, j])
                    })
            visualizations["heatmap"] = {
                "type": "heatmap",
                "title": "特征相关性矩阵",
                "xAxis": corr.columns.tolist(),
                "yAxis": corr.columns.tolist(),
                "data": heatmap_data
            }
        
        # 4. 折线图 - 指标趋势（如果有）
        if result.get("metrics"):
            metrics_data = []
            for k, v in result["metrics"].items():
                if isinstance(v, (int, float)):
                    metrics_data.append({"name": k, "value": float(v)})
            if metrics_data:
                visualizations["line"] = {
                    "type": "line",
                    "title": "模型评估指标",
                    "data": metrics_data
                }
                
    except Exception as e:
        print(f"生成可视化数据失败: {e}")
    
    return visualizations


# 导入 time
import time
