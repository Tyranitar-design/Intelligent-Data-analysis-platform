# -*- coding: utf-8 -*-
"""Smoke Center non-auth orchestration service."""
from __future__ import annotations

from typing import Any, Dict, List

from analysis.service import AnalysisService
from crawlers.dataset_service import DatasetService
from crawlers.robots_checker import RobotsChecker
from reports.service import ReportService

from .memory_capture import record_smoke_memory_capture
from .models import SmokeRunRequest
from .scenario_registry import get_scenario


dataset_service = DatasetService()
analysis_service = AnalysisService()
report_service = ReportService()
robots_checker = RobotsChecker()


def _normalize_columns(rows: List[Dict[str, Any]]) -> List[str]:
    columns: list[str] = []
    for row in rows:
        for key in row.keys():
            if key not in columns:
                columns.append(key)
    return columns


def _build_result(
    *,
    scenario_id: str,
    status: str,
    stage: str,
    requires_human: bool,
    dataset_saved: bool,
    analysis_passed: bool,
    report_passed: bool,
    crawl_strategy: str | None,
    robots: Dict[str, Any],
    artifacts: Dict[str, Any],
    notes: list[str] | None = None,
    error: str | None = None,
) -> Dict[str, Any]:
    return {
        "success": True,
        "scenario_id": scenario_id,
        "status": status,
        "stage": stage,
        "requires_human": requires_human,
        "dataset_saved": dataset_saved,
        "analysis_passed": analysis_passed,
        "report_passed": report_passed,
        "crawl_strategy": crawl_strategy,
        "robots": robots,
        "artifacts": artifacts,
        "memory_capture": {},
        "notes": notes or [],
        "error": error,
    }


def _attach_memory_capture(
    result: Dict[str, Any],
    *,
    scenario_title: str,
    mode: str,
    url: str | None,
) -> Dict[str, Any]:
    memory_capture = record_smoke_memory_capture(
        result,
        scenario_id=result["scenario_id"],
        scenario_title=scenario_title,
        mode=mode,
        url=url,
    )
    result["memory_capture"] = memory_capture
    if memory_capture.get("captured"):
        result["notes"] = [*result.get("notes", []), "Smoke 结果已自动写入 Little C 记忆。"]
    elif memory_capture.get("error"):
        result["notes"] = [*result.get("notes", []), f"记忆写入跳过：{memory_capture['error']}"]
    return result


async def execute_non_auth_smoke_run(request: SmokeRunRequest) -> Dict[str, Any]:
    """Execute the first non-auth smoke scenarios."""
    scenario = get_scenario(request.scenario_id)
    if scenario is None:
        return _attach_memory_capture(_build_result(
            scenario_id=request.scenario_id,
            status="failed",
            stage="scenario_loaded",
            requires_human=False,
            dataset_saved=False,
            analysis_passed=False,
            report_passed=False,
            crawl_strategy=None,
            robots={"checked": False},
            artifacts={},
            error=f"Unknown scenario: {request.scenario_id}",
        ), scenario_title="unknown-scenario", mode="unknown", url=request.url)

    if scenario.mode == "local":
        if not request.rows:
            return _attach_memory_capture(_build_result(
                scenario_id=request.scenario_id,
                status="failed",
                stage="scenario_loaded",
                requires_human=False,
                dataset_saved=False,
                analysis_passed=False,
                report_passed=False,
                crawl_strategy="local",
                robots={"checked": False},
                artifacts={},
                error="Local smoke requires rows",
            ), scenario_title=scenario.title, mode=scenario.mode, url=request.url)

        dataset_name = request.dataset_name or "smoke_local_dataset"
        columns = _normalize_columns(request.rows)
        save_result = dataset_service.save_dataset(
            name=dataset_name,
            description=request.dataset_description,
            columns=columns,
            data=request.rows,
            source_url=None,
            source_type="smoke_local",
        )

        if not save_result.get("success"):
            return _attach_memory_capture(_build_result(
                scenario_id=request.scenario_id,
                status="failed",
                stage="dataset_save",
                requires_human=False,
                dataset_saved=False,
                analysis_passed=False,
                report_passed=False,
                crawl_strategy="local",
                robots={"checked": False},
                artifacts={},
                error=save_result.get("error", "Dataset save failed"),
            ), scenario_title=scenario.title, mode=scenario.mode, url=request.url)

        import pandas as pd

        df = pd.DataFrame(request.rows)
        eda_result = analysis_service.eda(df)
        analysis_passed = bool(eda_result.get("overview"))
        report = report_service.generate_table_eda_report(
            table_name=save_result["table_name"],
            dataset_name=save_result["name"],
            eda_result=eda_result,
            row_count=save_result["row_count"],
            column_count=save_result["column_count"],
        )
        report_passed = bool(report.get("title"))

        return _attach_memory_capture(_build_result(
            scenario_id=request.scenario_id,
            status="passed",
            stage="completed",
            requires_human=False,
            dataset_saved=True,
            analysis_passed=analysis_passed,
            report_passed=report_passed,
            crawl_strategy="local",
            robots={"checked": False, "allowed": True, "source": "local"},
            artifacts={
                "dataset": {
                    "name": save_result["name"],
                    "table_name": save_result["table_name"],
                    "row_count": save_result["row_count"],
                    "column_count": save_result["column_count"],
                },
                "analysis": {
                    "row_count": eda_result["overview"]["row_count"],
                    "column_count": eda_result["overview"]["column_count"],
                },
                "report": {
                    "title": report.get("title"),
                    "filepath": report.get("filepath"),
                },
            },
            notes=["Local smoke completed successfully"],
            error=None,
        ), scenario_title=scenario.title, mode=scenario.mode, url=request.url)

    if scenario.mode == "live-public":
        if not request.url:
            return _attach_memory_capture(_build_result(
                scenario_id=request.scenario_id,
                status="failed",
                stage="scenario_loaded",
                requires_human=False,
                dataset_saved=False,
                analysis_passed=False,
                report_passed=False,
                crawl_strategy=scenario.preferred_strategy,
                robots={"checked": False},
                artifacts={},
                error="Live public smoke requires url",
            ), scenario_title=scenario.title, mode=scenario.mode, url=request.url)

        report = await robots_checker.check(request.url)
        robots_payload = report.to_dict()
        robots_payload["checked"] = True

        if not report.allowed:
            return _attach_memory_capture(_build_result(
                scenario_id=request.scenario_id,
                status="blocked_by_robots",
                stage="robots_check",
                requires_human=False,
                dataset_saved=False,
                analysis_passed=False,
                report_passed=False,
                crawl_strategy=scenario.preferred_strategy,
                robots=robots_payload,
                artifacts={},
                notes=["Target disallowed by robots.txt"],
                error=None,
            ), scenario_title=scenario.title, mode=scenario.mode, url=request.url)

        return _attach_memory_capture(_build_result(
            scenario_id=request.scenario_id,
            status="skipped",
            stage="robots_check",
            requires_human=False,
            dataset_saved=False,
            analysis_passed=False,
            report_passed=False,
            crawl_strategy=scenario.preferred_strategy,
            robots=robots_payload,
            artifacts={},
            notes=["Live public crawl execution will be implemented in the next runner slice"],
            error=None,
        ), scenario_title=scenario.title, mode=scenario.mode, url=request.url)

    return _attach_memory_capture(_build_result(
        scenario_id=request.scenario_id,
        status="skipped",
        stage="scenario_loaded",
        requires_human=scenario.requires_human,
        dataset_saved=False,
        analysis_passed=False,
        report_passed=False,
        crawl_strategy=scenario.preferred_strategy,
        robots={"checked": False},
        artifacts={},
        notes=["Scenario mode not handled by non-auth runner"],
        error=None,
    ), scenario_title=scenario.title, mode=scenario.mode, url=request.url)
