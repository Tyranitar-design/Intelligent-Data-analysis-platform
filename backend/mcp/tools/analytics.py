"""
MCP 工具 · 数据与分析
=====================

三个工具：``query_dataset`` / ``run_analysis`` / ``make_report``。

三者共享 ``analysis.facade`` 的能力，不重复实现分析逻辑。
"""
from __future__ import annotations

import logging
from typing import Any

from mcp.protocol import RESOURCE_NOT_FOUND, MCPError
from mcp.registry import ToolContext, ToolSpec

logger = logging.getLogger(__name__)

MAX_QUERY_LIMIT = 500


# --------------------------------------------------------------------------- #
# 5. query_dataset
# --------------------------------------------------------------------------- #

QUERY_DATASET_SCHEMA = {
    "type": "object",
    "properties": {
        "dataset_id": {"type": "integer", "description": "数据集 ID"},
        "limit": {
            "type": "integer",
            "description": f"返回行数上限，默认 50，最大 {MAX_QUERY_LIMIT}",
        },
        "offset": {"type": "integer", "description": "起始偏移，默认 0"},
    },
    "required": ["dataset_id"],
}


async def query_dataset(arguments: dict, ctx: ToolContext) -> dict:
    """按页读取数据集内容。"""
    from pipeline.storage import DatasetMaterializer

    dataset_id = int(arguments["dataset_id"])
    limit = min(int(arguments.get("limit") or 50), MAX_QUERY_LIMIT)
    offset = max(int(arguments.get("offset") or 0), 0)

    materializer = DatasetMaterializer(ctx.session)
    try:
        payload = materializer.read_dataset(dataset_id, limit=limit, offset=offset)
    except ValueError as exc:
        raise MCPError(RESOURCE_NOT_FOUND, str(exc)) from exc

    if payload.get("missing_table"):
        raise MCPError(
            RESOURCE_NOT_FOUND,
            f"数据集 #{dataset_id} 的物理表不存在，可能已被清理",
        )
    return payload


# --------------------------------------------------------------------------- #
# 6. run_analysis
# --------------------------------------------------------------------------- #

RUN_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "dataset_id": {"type": "integer", "description": "数据集 ID"},
        "analysis_type": {
            "type": "string",
            "enum": ["eda", "stats", "correlation", "outliers", "missing", "preview"],
            "description": "分析类型，默认 eda",
        },
        "params": {
            "type": "object",
            "description": "附加参数，如 {row_limit: 5000, max_charts: 6}",
        },
    },
    "required": ["dataset_id"],
}


async def run_analysis(arguments: dict, ctx: ToolContext) -> dict:
    """对数据集执行分析，返回结果与图表（ECharts option 结构）。"""
    from analysis.facade import AnalysisFacade

    dataset_id = int(arguments["dataset_id"])
    analysis_type = str(arguments.get("analysis_type") or "eda")

    facade = AnalysisFacade(ctx.session)
    try:
        return facade.run(dataset_id, analysis_type, arguments.get("params"))
    except ValueError as exc:
        raise MCPError(RESOURCE_NOT_FOUND, str(exc)) from exc


# --------------------------------------------------------------------------- #
# 7. make_report
# --------------------------------------------------------------------------- #

MAKE_REPORT_SCHEMA = {
    "type": "object",
    "properties": {
        "dataset_id": {"type": "integer", "description": "数据集 ID"},
        "analysis_type": {
            "type": "string",
            "enum": ["eda", "stats", "correlation", "outliers", "missing"],
            "description": "用于生成报告的分析类型，默认 eda",
        },
        "format": {
            "type": "string",
            "enum": ["markdown", "html", "json"],
            "description": "报告格式，默认 markdown",
        },
    },
    "required": ["dataset_id"],
}


async def make_report(arguments: dict, ctx: ToolContext) -> dict:
    """生成分析报告，含数据集概况、统计、图表清单、血缘与隐私处理记录。"""
    from analysis.facade import AnalysisFacade

    dataset_id = int(arguments["dataset_id"])
    analysis_type = str(arguments.get("analysis_type") or "eda")
    fmt = str(arguments.get("format") or "markdown")

    facade = AnalysisFacade(ctx.session)
    try:
        return facade.build_report(dataset_id, analysis_type, fmt)
    except ValueError as exc:
        raise MCPError(RESOURCE_NOT_FOUND, str(exc)) from exc


# --------------------------------------------------------------------------- #
# 注册
# --------------------------------------------------------------------------- #

TOOL_SPECS = [
    ToolSpec(
        name="query_dataset",
        description=(
            "读取数据集内容（分页）。返回列名、行数据、总行数与偏移信息。"
        ),
        input_schema=QUERY_DATASET_SCHEMA,
        handler=query_dataset,
    ),
    ToolSpec(
        name="run_analysis",
        description=(
            "对数据集执行分析：eda（完整探索）/ stats（描述统计）/ "
            "correlation（相关性）/ outliers（异常值）/ missing（缺失）/ preview（预览）。"
            "返回结构化结果与 ECharts 图表配置。"
        ),
        input_schema=RUN_ANALYSIS_SCHEMA,
        handler=run_analysis,
    ),
    ToolSpec(
        name="make_report",
        description=(
            "生成分析报告，支持 markdown / html / json 三种格式。"
            "报告含数据集概况、字段统计、图表清单、数据血缘与隐私处理记录。"
        ),
        input_schema=MAKE_REPORT_SCHEMA,
        handler=make_report,
    ),
]
