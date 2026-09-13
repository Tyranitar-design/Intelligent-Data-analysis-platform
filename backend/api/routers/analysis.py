"""
数据分析路由 - 支持从数据库和文件读取数据
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from api.database import get_db
from api.models import Dataset
from api.schemas import DatasetCreate, DatasetResponse, SuccessResponse
from analysis.service import AnalysisService

router = APIRouter()

analysis_service = AnalysisService()


# ==================== 数据源概览 ====================

@router.get("/overview")
async def get_data_overview():
    """获取数据库数据概览"""
    summary = analysis_service.db_service.get_data_summary() if analysis_service.db_service else {}
    return summary


@router.get("/db/data/{source}")
async def get_db_data(
    source: str,
    platform: str = Query(None, description="Platform: jd, eastmoney, etc."),
    keyword: str = Query(None, description="Search keyword"),
    limit: int = Query(100, ge=1, le=5000)
):
    """从数据库获取数据"""
    if analysis_service.db_service is None:
        raise HTTPException(status_code=500, detail="Database service not available")

    df = analysis_service.db_service.get_data_for_analysis(
        source=source, platform=platform, keyword=keyword, limit=limit
    )

    if df.empty:
        raise HTTPException(status_code=404, detail=f"No data found for source={source}")

    # 转换为字典列表
    result = df.to_dict(orient="records")
    # 处理 NaN
    for row in result:
        for k, v in row.items():
            import math
            if v is not None and (isinstance(v, float) and math.isnan(v)):
                row[k] = None

    return {"count": len(result), "columns": list(df.columns), "data": result}


# ==================== EDA 分析 ====================

@router.post("/eda/{source_type}")
async def eda_by_source(source_type: str):
    """按数据源类型进行 EDA 分析"""
    df = analysis_service.load_from_db(source=source_type)

    if df.empty:
        # 回退到文件
        filepath = analysis_service.get_latest_file(source_type)
        if not filepath:
            raise HTTPException(status_code=404, detail=f"No data found for: {source_type}")
        df = analysis_service.load_data(filepath)

    result = analysis_service.eda(df)
    result["source_type"] = source_type
    return result


@router.post("/eda/db/{source}")
async def eda_from_db(
    source: str,
    platform: str = Query(None),
    keyword: str = Query(None),
    limit: int = Query(1000, ge=1, le=10000)
):
    """从数据库读取数据并做 EDA 分析"""
    df = analysis_service.load_from_db(source=source, platform=platform, keyword=keyword, limit=limit)

    if df.empty:
        raise HTTPException(status_code=404, detail=f"No data in DB for source={source}")

    result = analysis_service.eda(df)
    result["source"] = source
    result["platform"] = platform
    result["record_count"] = len(df)
    return result


# ==================== 统计分析 ====================

@router.post("/statistics/{source_type}")
async def statistics_by_source(
    source_type: str,
    columns: Optional[str] = Query(None, description="Comma-separated column names")
):
    """按数据源类型进行统计分析"""
    df = analysis_service.load_from_db(source=source_type)

    if df.empty:
        filepath = analysis_service.get_latest_file(source_type)
        if not filepath:
            raise HTTPException(status_code=404, detail=f"No data found for: {source_type}")
        df = analysis_service.load_data(filepath)

    col_list = columns.split(",") if columns else None
    result = analysis_service.statistics(df, col_list)
    result["source_type"] = source_type
    return result


@router.post("/statistics/db/{source}")
async def statistics_from_db(
    source: str,
    columns: Optional[str] = Query(None),
    platform: str = Query(None),
    limit: int = Query(1000)
):
    """从数据库读取数据并做统计分析"""
    df = analysis_service.load_from_db(source=source, platform=platform, limit=limit)

    if df.empty:
        raise HTTPException(status_code=404, detail=f"No data in DB for source={source}")

    col_list = columns.split(",") if columns else None
    result = analysis_service.statistics(df, col_list)
    result["source"] = source
    result["record_count"] = len(df)
    return result


# ==================== 可视化 ====================

@router.post("/chart/{source_type}")
async def generate_chart(
    source_type: str,
    chart_type: str = Query("bar", description="Chart type: bar/line/scatter/pie"),
    x: str = Query(..., description="X axis column"),
    y: Optional[str] = Query(None, description="Y axis column"),
):
    """生成图表数据"""
    df = analysis_service.load_from_db(source=source_type)

    if df.empty:
        filepath = analysis_service.get_latest_file(source_type)
        if not filepath:
            raise HTTPException(status_code=404, detail=f"No data found for: {source_type}")
        df = analysis_service.load_data(filepath)

    if x not in df.columns:
        raise HTTPException(status_code=400, detail=f"Column '{x}' not found")

    result = analysis_service.generate_chart_data(df, chart_type, x, y)
    return result


@router.get("/visualizations")
async def get_visualizations():
    """获取可视化图表类型列表"""
    return {
        "chart_types": [
            {"type": "bar", "name": "Bar Chart", "description": "Compare categories"},
            {"type": "line", "name": "Line Chart", "description": "Show trends over time"},
            {"type": "scatter", "name": "Scatter Plot", "description": "Show relationships"},
            {"type": "pie", "name": "Pie Chart", "description": "Show proportions"},
            {"type": "heatmap", "name": "Heatmap", "description": "Correlation matrix"},
        ]
    }


# ==================== 数据集管理 ====================

@router.get("/datasets", response_model=List[DatasetResponse])
async def list_datasets(db: Session = Depends(get_db)):
    """获取数据集列表"""
    datasets = db.query(Dataset).all()
    return datasets


@router.post("/datasets", response_model=DatasetResponse)
async def create_dataset(data: DatasetCreate, db: Session = Depends(get_db)):
    """创建数据集"""
    dataset = Dataset(**data.model_dump())
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    return dataset


@router.get("/datasets/{dataset_id}", response_model=DatasetResponse)
async def get_dataset(dataset_id: int, db: Session = Depends(get_db)):
    """获取数据集详情"""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset


@router.delete("/datasets/{dataset_id}", response_model=SuccessResponse)
async def delete_dataset(dataset_id: int, db: Session = Depends(get_db)):
    """删除数据集"""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    db.delete(dataset)
    db.commit()
    return SuccessResponse(message="Dataset deleted")
