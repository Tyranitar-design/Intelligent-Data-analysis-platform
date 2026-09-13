"""
报告生成路由 - 接入真实报告服务
"""
import json
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from api.core.database import get_db
from api.models import Report, Dataset
from api.schemas import ReportResponse, SuccessResponse
from reports.service import ReportService
from analysis.service import AnalysisService
from ml.service import MLService
from crawlers.dataset_service import DatasetService

router = APIRouter()

report_service = ReportService()
analysis_service = AnalysisService()
ml_service = MLService()
dataset_service = DatasetService()


@router.get("/", response_model=list[ReportResponse])
async def list_reports(db: Session = Depends(get_db)):
    """获取报告列表"""
    return db.query(Report).order_by(Report.created_at.desc()).all()


@router.post("/generate", response_model=SuccessResponse)
async def generate_report(
    source_type: str,
    report_type: str = Query("eda", description="Report type: eda/ml/comprehensive"),
    model_id: Optional[int] = Query(None, description="ML model ID (for ml/comprehensive reports)"),
    db: Session = Depends(get_db),
):
    """生成报告"""
    result = None

    if report_type == "eda":
        filepath = analysis_service.get_latest_file(source_type)
        if not filepath:
            raise HTTPException(status_code=404, detail=f"No data for: {source_type}")
        df = analysis_service.load_data(filepath)
        eda_result = analysis_service.eda(df)
        result = report_service.generate_eda_report(eda_result, source_type)

    elif report_type == "ml":
        if not model_id:
            raise HTTPException(status_code=400, detail="model_id required for ML report")
        model = db.query(Report).filter(Report.id == model_id).first()
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")
        result = report_service.generate_ml_report({}, {})

    elif report_type == "comprehensive":
        filepath = analysis_service.get_latest_file(source_type)
        if not filepath:
            raise HTTPException(status_code=404, detail=f"No data for: {source_type}")
        df = analysis_service.load_data(filepath)
        eda_result = analysis_service.eda(df)
        ml_result = {"algorithm": "N/A", "model_type": "N/A", "metrics": {}, "training_time": 0}
        if model_id:
            model_record = db.query(Report).filter(Report.id == model_id).first()
        result = report_service.generate_comprehensive_report(eda_result, ml_result, source_type)

    else:
        raise HTTPException(status_code=400, detail=f"Unknown report type: {report_type}")

    # 保存到数据库
    report = Report(
        name=result.get("title", "Report"),
        report_type=report_type,
        format="markdown",
        content=json.dumps(result, ensure_ascii=False, indent=2),
        html_content=None,
        meta={
            "source_type": source_type,
            "report_type": report_type,
        },
    )
    db.add(report)
    db.commit()

    return SuccessResponse(message=f"Report generated: {result.get('title')}")


@router.post("/generate-from-table", response_model=SuccessResponse)
async def generate_report_from_table(
    table_name: str,
    report_type: str = Query("eda", description="Report type: eda/comprehensive"),
    db: Session = Depends(get_db),
):
    """基于真实数据表生成报告"""
    dataset = db.query(Dataset).filter(Dataset.table_name == table_name).first()
    if not dataset:
        raise HTTPException(status_code=404, detail=f"Dataset table not found: {table_name}")

    table_data = dataset_service.get_dataset_data(table_name=table_name, limit=2000)
    rows = table_data.get("data", [])
    if not rows:
        raise HTTPException(status_code=404, detail=f"No data found in table: {table_name}")

    import pandas as pd

    df = pd.DataFrame(rows)
    eda_result = analysis_service.eda(df)

    if report_type == "eda":
        result = report_service.generate_table_eda_report(
            table_name=table_name,
            dataset_name=dataset.name,
            eda_result=eda_result,
            row_count=len(df),
            column_count=len(df.columns),
        )
    elif report_type == "comprehensive":
        ml_result = {"algorithm": "N/A", "model_type": "N/A", "metrics": {}, "training_time": 0}
        result = report_service.generate_comprehensive_report(eda_result, ml_result, table_name)
        result["dataset_name"] = dataset.name
        result["table_name"] = table_name
        result["row_count"] = len(df)
        result["column_count"] = len(df.columns)
        result["source_type"] = "dataset_table"
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported table-driven report type: {report_type}")

    report = Report(
        name=result.get("title", f"Report - {dataset.name}"),
        report_type=report_type,
        format="markdown",
        content=json.dumps(result, ensure_ascii=False, indent=2),
        html_content=None,
        meta={
            "table_name": table_name,
            "dataset_name": dataset.name,
            "row_count": len(df),
            "column_count": len(df.columns),
            "source_type": "dataset_table",
        },
    )
    db.add(report)
    db.commit()

    return SuccessResponse(
        message=f"Report generated from table: {dataset.name}",
        data={
            "table_name": table_name,
            "dataset_name": dataset.name,
            "report_type": report_type,
        },
    )


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(report_id: int, db: Session = Depends(get_db)):
    """获取报告详情"""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.delete("/{report_id}", response_model=SuccessResponse)
async def delete_report(report_id: int, db: Session = Depends(get_db)):
    """删除报告"""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    db.delete(report)
    db.commit()
    return SuccessResponse(message="Report deleted")
