"""
分析路由
========

以 ``dataset_id`` 为统一输入的分析入口。

- ``POST /api/v1/analytics/run``              执行分析，返回结果与图表
- ``POST /api/v1/analytics/report``           生成分析报告（markdown / html / json）
- ``GET  /api/v1/analytics/export/{id}``      导出数据集（csv / json / excel）
- ``GET  /api/v1/analytics/types``            支持的分析类型

请求模型直接定义在本模块：它们只服务于此路由，没有跨模块复用需求。
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from analysis.facade import SUPPORTED_TYPES, AnalysisFacade
from api.core.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter()


class AnalysisRequest(BaseModel):
    """执行分析的请求。"""

    dataset_id: int = Field(..., description="数据集 ID")
    analysis_type: str = Field(
        default="eda", description=f"分析类型，可选 {list(SUPPORTED_TYPES)}"
    )
    params: Optional[dict[str, Any]] = Field(
        default=None, description="附加参数，如 {row_limit: 5000, max_charts: 6}"
    )


class ReportRequest(BaseModel):
    """生成报告的请求。"""

    dataset_id: int
    analysis_type: str = "eda"
    format: str = Field(default="markdown", description="markdown | html | json")


@router.get("/types", summary="支持的分析类型")
def list_types() -> dict:
    return {
        "types": [
            {"name": "eda", "description": "完整探索性分析（概况/质量/字段画像/相关性/异常）"},
            {"name": "stats", "description": "数值与分类字段的描述统计"},
            {"name": "correlation", "description": "数值字段相关性与显著相关对"},
            {"name": "outliers", "description": "IQR 法异常值检测"},
            {"name": "missing", "description": "缺失值分布"},
            {"name": "preview", "description": "结构与样本预览"},
        ]
    }


@router.post("/run", summary="执行分析")
def run_analysis(payload: AnalysisRequest, db: Session = Depends(get_db)) -> dict:
    """对指定数据集执行分析，返回 ``{result, charts, summary}``。"""
    facade = AnalysisFacade(db)
    try:
        return facade.run(payload.dataset_id, payload.analysis_type, payload.params)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - 分析失败要给出可诊断信息
        logger.exception("分析执行失败 dataset=%s", payload.dataset_id)
        raise HTTPException(
            status_code=500,
            detail={"error": "analysis_failed", "message": str(exc)[:300]},
        ) from exc


@router.post("/report", summary="生成分析报告")
def generate_report(payload: ReportRequest, db: Session = Depends(get_db)) -> dict:
    """生成分析报告，含数据集概况、统计、图表清单与血缘。"""
    if payload.format not in ("markdown", "html", "json"):
        raise HTTPException(status_code=400, detail="format 仅支持 markdown / html / json")

    facade = AnalysisFacade(db)
    try:
        return facade.build_report(
            payload.dataset_id, payload.analysis_type, payload.format
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/export/{dataset_id}", summary="导出数据集")
def export_dataset(
    dataset_id: int,
    format: str = Query("csv", description="csv | json | excel"),
    db: Session = Depends(get_db),
) -> Response:
    """导出数据集内容为文件。"""
    if format not in ("csv", "json", "excel"):
        raise HTTPException(status_code=400, detail="format 仅支持 csv / json / excel")

    facade = AnalysisFacade(db)
    try:
        content, filename, media_type = facade.export(dataset_id, format)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
