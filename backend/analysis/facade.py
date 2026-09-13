"""
分析门面
========

统一入口：以 ``dataset_id`` 为输入，分发到 EDA / 统计 / 挖掘各能力，
输出统一为 ``{result, charts}``。

为什么需要这一层：现有的 ``AnalysisService`` / ``EDAEngine`` 接收的是 DataFrame，
而平台的标准输入是数据集 ID。门面负责把"数据集"翻译成"DataFrame"，
再把各引擎的结果翻译成统一的输出结构——分析逻辑本身不重写。

图表输出采用 ECharts option 结构，前端可直接渲染。
"""
from __future__ import annotations

import logging
from typing import Any, Optional

import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.models import Dataset
from pipeline.storage import table_name_for

logger = logging.getLogger(__name__)

# 支持的分析类型
SUPPORTED_TYPES = (
    "eda",
    "stats",
    "correlation",
    "outliers",
    "missing",
    "preview",
)

# 低基数阈值：唯一值不超过此比例的列适合做分类图表
CATEGORICAL_RATIO = 0.3
CATEGORICAL_MAX_UNIQUE = 30
MAX_ROWS_FOR_ANALYSIS = 200_000


class AnalysisFacade:
    """数据集分析的统一入口。"""

    def __init__(self, session: Session) -> None:
        self.session = session

    # ------------------------------------------------------------------ #
    # 数据加载
    # ------------------------------------------------------------------ #

    def load_frame(self, dataset_id: int, limit: Optional[int] = None) -> pd.DataFrame:
        """把物化后的数据集读成 DataFrame。"""
        dataset = self.session.get(Dataset, dataset_id)
        if dataset is None:
            raise ValueError(f"数据集不存在: {dataset_id}")

        table_name = dataset.table_name or table_name_for(dataset_id)
        sql = f'SELECT * FROM "{table_name}"'
        if limit:
            sql += f" LIMIT {int(limit)}"

        try:
            frame = pd.read_sql(text(sql), self.session.connection())
        except Exception as exc:  # noqa: BLE001 - 表缺失要给出可诊断的错误
            raise ValueError(
                f"数据集 #{dataset_id} 的物理表不可读（{table_name}）: {str(exc)[:160]}"
            ) from exc

        if len(frame) > MAX_ROWS_FOR_ANALYSIS:
            logger.info(
                "数据集 %s 行数 %s 超过分析上限，采样 %s 行",
                dataset_id,
                len(frame),
                MAX_ROWS_FOR_ANALYSIS,
            )
            frame = frame.head(MAX_ROWS_FOR_ANALYSIS)

        return frame

    # ------------------------------------------------------------------ #
    # 分析分发
    # ------------------------------------------------------------------ #

    def run(
        self,
        dataset_id: int,
        analysis_type: str = "eda",
        params: Optional[dict] = None,
    ) -> dict:
        """执行分析。

        返回 ``{dataset_id, analysis_type, result, charts, summary}``。
        """
        if analysis_type not in SUPPORTED_TYPES:
            raise ValueError(
                f"不支持的分析类型: {analysis_type}（可选 {list(SUPPORTED_TYPES)}）"
            )

        params = params or {}
        frame = self.load_frame(dataset_id, limit=params.get("row_limit"))
        dataset = self.session.get(Dataset, dataset_id)
        dataset_name = dataset.name if dataset else f"dataset_{dataset_id}"

        if frame.empty:
            return {
                "dataset_id": dataset_id,
                "analysis_type": analysis_type,
                "result": {},
                "charts": [],
                "summary": "数据集为空，无可分析内容",
            }

        if analysis_type == "eda":
            result = self._run_eda(frame, dataset_name)
            charts = self._build_charts(frame, params.get("max_charts", 4))
            summary = self._summarize_eda(result)

        elif analysis_type == "stats":
            result = self._run_stats(frame, params.get("columns"))
            charts = []
            summary = f"完成 {len(result.get('numeric', {}))} 个数值字段的描述统计"

        elif analysis_type == "correlation":
            result = self._run_correlation(frame)
            charts = self._chart_correlation(result)
            summary = (
                f"计算了 {len(result.get('columns', []))} 个数值字段的相关性"
                if result.get("columns")
                else "数值字段不足，无法计算相关性"
            )

        elif analysis_type == "outliers":
            result = self._run_outliers(frame)
            charts = []
            summary = f"检测到 {result.get('total_outliers', 0)} 个可疑值"

        elif analysis_type == "missing":
            result = self._run_missing(frame)
            charts = self._chart_missing(result)
            summary = (
                f"共 {len(result.get('fields', {}))} 个字段存在缺失"
                if result.get("fields")
                else "无缺失值"
            )

        else:  # preview
            result = {
                "columns": list(frame.columns),
                "row_count": len(frame),
                "sample": frame.head(10).to_dict(orient="records"),
                "dtypes": {c: str(t) for c, t in frame.dtypes.items()},
            }
            charts = []
            summary = f"{len(frame)} 行 × {len(frame.columns)} 列"

        return {
            "dataset_id": dataset_id,
            "analysis_type": analysis_type,
            "result": result,
            "charts": charts,
            "summary": summary,
        }

    # ------------------------------------------------------------------ #
    # 各类分析
    # ------------------------------------------------------------------ #

    def _run_eda(self, frame: pd.DataFrame, dataset_name: str) -> dict:
        """完整 EDA：复用现有 EDAEngine。"""
        try:
            from analysis.eda_engine import EDAEngine

            return EDAEngine().analyze(frame, dataset_name=dataset_name)
        except ImportError as exc:
            logger.warning("EDAEngine 不可用，退化为内置实现: %s", exc)
            return self._fallback_eda(frame)

    def _fallback_eda(self, frame: pd.DataFrame) -> dict:
        """EDAEngine 不可用时的最小实现，保证分析链不中断。"""
        numeric = frame.select_dtypes(include="number")
        return {
            "overview": {
                "row_count": len(frame),
                "column_count": len(frame.columns),
                "numeric_columns": list(numeric.columns),
            },
            "data_quality": {
                "duplicate_rows": int(frame.duplicated().sum()),
                "total_missing": int(frame.isna().sum().sum()),
            },
            "columns_profile": [
                {
                    "name": column,
                    "dtype": str(frame[column].dtype),
                    "missing": int(frame[column].isna().sum()),
                    "unique": int(frame[column].nunique()),
                }
                for column in frame.columns
            ],
        }

    def _run_stats(self, frame: pd.DataFrame, columns: Optional[list[str]]) -> dict:
        numeric = frame.select_dtypes(include="number")
        if columns:
            numeric = numeric[[c for c in columns if c in numeric.columns]]

        stats: dict[str, dict[str, Any]] = {}
        for column in numeric.columns:
            series = numeric[column].dropna()
            if series.empty:
                continue
            stats[column] = {
                "count": int(series.count()),
                "mean": round(float(series.mean()), 4),
                "std": round(float(series.std()), 4) if len(series) > 1 else 0.0,
                "min": float(series.min()),
                "p25": float(series.quantile(0.25)),
                "median": float(series.median()),
                "p75": float(series.quantile(0.75)),
                "max": float(series.max()),
            }

        categorical: dict[str, dict[str, Any]] = {}
        for column in frame.select_dtypes(exclude="number").columns:
            counts = frame[column].value_counts().head(10)
            if counts.empty:
                continue
            categorical[column] = {
                "unique": int(frame[column].nunique()),
                "top": {str(k): int(v) for k, v in counts.items()},
            }

        return {"numeric": stats, "categorical": categorical}

    def _run_correlation(self, frame: pd.DataFrame) -> dict:
        numeric = frame.select_dtypes(include="number")
        if numeric.shape[1] < 2:
            return {"columns": [], "matrix": []}

        corr = numeric.corr(numeric_only=True).round(4)
        columns = [str(c) for c in corr.columns]
        matrix = [
            [None if pd.isna(v) else float(v) for v in row]
            for row in corr.values.tolist()
        ]

        # 挑出强相关对，便于直接解读
        pairs: list[dict[str, Any]] = []
        for i, left in enumerate(columns):
            for j, right in enumerate(columns):
                if j <= i:
                    continue
                value = matrix[i][j]
                if value is None:
                    continue
                if abs(value) >= 0.5:
                    pairs.append(
                        {
                            "left": left,
                            "right": right,
                            "r": value,
                            "strength": _describe_r(value),
                        }
                    )
        pairs.sort(key=lambda p: -abs(p["r"]))

        return {"columns": columns, "matrix": matrix, "strong_pairs": pairs[:10]}

    def _run_outliers(self, frame: pd.DataFrame) -> dict:
        numeric = frame.select_dtypes(include="number")
        details: dict[str, dict[str, Any]] = {}
        total = 0

        for column in numeric.columns:
            series = numeric[column].dropna()
            if len(series) < 8:
                continue
            q1, q3 = series.quantile(0.25), series.quantile(0.75)
            iqr = q3 - q1
            if iqr == 0:
                continue
            low, high = q1 - 1.5 * iqr, q3 + 1.5 * iqr
            mask = (series < low) | (series > high)
            count = int(mask.sum())
            if count == 0:
                continue
            total += count
            details[column] = {
                "count": count,
                "ratio": round(count / max(1, len(series)), 4),
                "lower_bound": round(float(low), 4),
                "upper_bound": round(float(high), 4),
                "examples": [float(v) for v in series[mask].head(5)],
            }

        return {"total_outliers": total, "fields": details, "method": "IQR(1.5)"}

    def _run_missing(self, frame: pd.DataFrame) -> dict:
        total = len(frame)
        fields: dict[str, dict[str, Any]] = {}
        for column in frame.columns:
            missing = int(frame[column].isna().sum())
            if missing == 0:
                continue
            fields[str(column)] = {
                "missing": missing,
                "ratio": round(missing / max(1, total), 4),
            }
        return {
            "row_count": total,
            "fields": dict(
                sorted(fields.items(), key=lambda kv: -kv[1]["ratio"])
            ),
        }

    # ------------------------------------------------------------------ #
    # 图表
    # ------------------------------------------------------------------ #

    def _build_charts(self, frame: pd.DataFrame, max_charts: int = 4) -> list[dict]:
        """为数值列与低基数分类列生成 ECharts option。"""
        charts: list[dict] = []

        numeric = frame.select_dtypes(include="number")
        for column in list(numeric.columns)[:max_charts]:
            series = numeric[column].dropna()
            if series.empty:
                continue
            counts, bins = _histogram(series)
            charts.append(
                {
                    "id": f"hist_{column}",
                    "type": "histogram",
                    "title": f"{column} 分布",
                    "option": {
                        "xAxis": {
                            "type": "category",
                            "data": [f"{bins[i]:.2f}" for i in range(len(counts))],
                            "name": str(column),
                        },
                        "yAxis": {"type": "value", "name": "频数"},
                        "series": [{"type": "bar", "data": counts}],
                    },
                }
            )
            if len(charts) >= max_charts:
                return charts

        for column in frame.select_dtypes(exclude="number").columns:
            if len(charts) >= max_charts:
                break
            counts = frame[column].value_counts().head(10)
            if counts.empty or len(counts) > CATEGORICAL_MAX_UNIQUE:
                continue
            charts.append(
                {
                    "id": f"cat_{column}",
                    "type": "bar",
                    "title": f"{column} 取值分布 Top 10",
                    "option": {
                        "xAxis": {
                            "type": "category",
                            "data": [str(k)[:20] for k in counts.index],
                        },
                        "yAxis": {"type": "value"},
                        "series": [{"type": "bar", "data": [int(v) for v in counts.values]}],
                    },
                }
            )

        return charts

    def _chart_correlation(self, result: dict) -> list[dict]:
        columns = result.get("columns") or []
        matrix = result.get("matrix") or []
        if not columns or not matrix:
            return []

        data = []
        for i, left in enumerate(columns):
            for j, right in enumerate(columns):
                value = matrix[i][j]
                if value is None:
                    continue
                data.append([j, i, round(float(value), 3)])

        return [
            {
                "id": "corr_heatmap",
                "type": "heatmap",
                "title": "字段相关性",
                "option": {
                    "xAxis": {"type": "category", "data": columns},
                    "yAxis": {"type": "category", "data": columns},
                    "visualMap": {"min": -1, "max": 1, "calculable": True},
                    "series": [{"type": "heatmap", "data": data}],
                },
            }
        ]

    def _chart_missing(self, result: dict) -> list[dict]:
        fields = result.get("fields") or {}
        if not fields:
            return []
        names = list(fields.keys())[:15]
        ratios = [round(fields[n]["ratio"] * 100, 2) for n in names]
        return [
            {
                "id": "missing_ratio",
                "type": "bar",
                "title": "字段缺失率（%）",
                "option": {
                    "xAxis": {"type": "value"},
                    "yAxis": {"type": "category", "data": names},
                    "series": [{"type": "bar", "data": ratios}],
                },
            }
        ]

    @staticmethod
    def _summarize_eda(result: dict) -> str:
        overview = result.get("overview") or {}
        quality = result.get("data_quality") or {}
        rows = overview.get("row_count", overview.get("rows"))
        cols = overview.get("column_count", overview.get("columns"))
        parts = []
        if rows is not None:
            parts.append(f"{rows} 行")
        if cols is not None:
            parts.append(f"{cols} 列")
        dup = quality.get("duplicate_rows")
        if dup:
            parts.append(f"重复行 {dup}")
        missing = quality.get("total_missing")
        if missing:
            parts.append(f"缺失值 {missing}")
        return "，".join(parts) if parts else "EDA 完成"

    # ------------------------------------------------------------------ #
    # 报告与导出
    # ------------------------------------------------------------------ #

    def build_report(
        self,
        dataset_id: int,
        analysis_type: str = "eda",
        fmt: str = "markdown",
    ) -> dict:
        """生成分析报告。

        报告包含：数据集元信息、血缘、分析结果、图表、质量提示。
        """
        dataset = self.session.get(Dataset, dataset_id)
        if dataset is None:
            raise ValueError(f"数据集不存在: {dataset_id}")

        run_result = self.run(dataset_id, analysis_type)
        sections = self._report_sections(dataset, run_result)

        if fmt == "json":
            content = {
                "dataset": dataset.to_dict(),
                "analysis": run_result,
            }
        elif fmt == "html":
            content = _render_html(sections)
        else:
            content = _render_markdown(sections)

        return {
            "dataset_id": dataset_id,
            "analysis_type": analysis_type,
            "format": fmt,
            "title": sections["title"],
            "content": content,
            "sections": [s["heading"] for s in sections["blocks"]],
        }

    def _report_sections(self, dataset: Dataset, run_result: dict) -> dict:
        dataset_dict = dataset.to_dict()
        blocks: list[dict] = []

        blocks.append(
            {
                "heading": "数据集概况",
                "body": [
                    f"名称：{dataset_dict.get('name')}",
                    f"来源：{dataset_dict.get('source_type')}",
                    f"规模：{dataset_dict.get('row_count')} 行 × {dataset_dict.get('column_count')} 列",
                    f"创建时间：{dataset_dict.get('created_at')}",
                ],
            }
        )

        summary = run_result.get("summary")
        if summary:
            blocks.append({"heading": "分析摘要", "body": [summary]})

        result = run_result.get("result") or {}
        stats = result.get("numeric") or {}
        if stats:
            rows = ["| 字段 | 均值 | 中位数 | 标准差 | 最小 | 最大 |", "|---|---|---|---|---|---|"]
            for name, values in list(stats.items())[:15]:
                rows.append(
                    f"| {name} | {values.get('mean')} | {values.get('median')} | "
                    f"{values.get('std')} | {values.get('min')} | {values.get('max')} |"
                )
            blocks.append({"heading": "数值字段统计", "body": rows})

        pairs = (result.get("strong_pairs") or [])
        if pairs:
            rows = ["| 字段 A | 字段 B | 相关系数 | 判读 |", "|---|---|---|---|"]
            for pair in pairs:
                rows.append(
                    f"| {pair['left']} | {pair['right']} | {pair['r']} | {pair['strength']} |"
                )
            blocks.append({"heading": "显著相关", "body": rows})

        outliers = result.get("fields") or {}
        if result.get("total_outliers"):
            rows = ["| 字段 | 异常数 | 占比 | 上下界 |", "|---|---|---|---|"]
            for name, values in list(outliers.items())[:10]:
                rows.append(
                    f"| {name} | {values.get('count')} | {values.get('ratio')} | "
                    f"{values.get('lower_bound')} ~ {values.get('upper_bound')} |"
                )
            blocks.append({"heading": "异常值", "body": rows})

        missing = result.get("fields") or {}
        if missing:
            rows = ["| 字段 | 缺失数 | 缺失率 |", "|---|---|---|"]
            for name, values in list(missing.items())[:10]:
                rows.append(f"| {name} | {values.get('missing')} | {values.get('ratio')} |")
            blocks.append({"heading": "缺失情况", "body": rows})

        charts = run_result.get("charts") or []
        if charts:
            blocks.append(
                {
                    "heading": "图表",
                    "body": [f"- {c.get('title')}（{c.get('type')}）" for c in charts],
                }
            )

        lineage = dataset_dict.get("lineage") or []
        if lineage:
            rows = ["| 字段 | 提取规则 | 覆盖率 |", "|---|---|---|"]
            for entry in lineage[:20]:
                rows.append(
                    f"| {entry.get('field')} | {entry.get('extractor_rule')} | "
                    f"{entry.get('coverage')} |"
                )
            blocks.append({"heading": "数据血缘", "body": rows})

        pii_policy = dataset_dict.get("pii_policy") or {}
        if pii_policy:
            blocks.append(
                {
                    "heading": "隐私处理",
                    "body": [f"- {k}：{v}" for k, v in pii_policy.items()],
                }
            )

        return {
            "title": f"数据集分析报告 · {dataset_dict.get('name')}",
            "generated_at": _now_iso(),
            "blocks": blocks,
        }

    def export(
        self, dataset_id: int, fmt: str = "csv"
    ) -> tuple[bytes, str, str]:
        """导出数据集。返回 ``(内容字节, 文件名, media_type)``。"""
        dataset = self.session.get(Dataset, dataset_id)
        if dataset is None:
            raise ValueError(f"数据集不存在: {dataset_id}")

        frame = self.load_frame(dataset_id)
        safe_name = "".join(
            ch if ch.isalnum() or ch in "-_" else "_"
            for ch in (dataset.name or f"dataset_{dataset_id}")
        )[:60]

        if fmt == "json":
            payload = frame.to_json(orient="records", force_ascii=False, indent=2)
            return payload.encode("utf-8"), f"{safe_name}.json", "application/json"

        if fmt == "excel":
            import io

            buffer = io.BytesIO()
            frame.to_excel(buffer, index=False, engine="openpyxl")
            return (
                buffer.getvalue(),
                f"{safe_name}.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

        csv_text = frame.to_csv(index=False)
        return (
            csv_text.encode("utf-8-sig"),
            f"{safe_name}.csv",
            "text/csv; charset=utf-8",
        )


def _now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def _render_markdown(sections: dict) -> str:
    lines = [
        f"# {sections['title']}",
        "",
        f"> 生成时间：{sections.get('generated_at', '')}",
        "",
    ]
    for block in sections.get("blocks", []):
        lines.append(f"## {block['heading']}")
        lines.append("")
        lines.extend(block.get("body") or [])
        lines.append("")
    return "\n".join(lines)


def _render_html(sections: dict) -> str:
    parts = [
        "<!DOCTYPE html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\">",
        f"<title>{sections['title']}</title>",
        "<style>body{font-family:system-ui,sans-serif;max-width:900px;margin:2rem auto;"
        "line-height:1.6;color:#1a1a1a}h1{border-bottom:2px solid #333;padding-bottom:.3rem}"
        "h2{margin-top:1.8rem;color:#333}table{border-collapse:collapse;width:100%;margin:.6rem 0}"
        "td,th{border:1px solid #ddd;padding:.4rem .6rem;font-size:.9rem}"
        "th{background:#f5f5f5;text-align:left}blockquote{color:#666;border-left:3px solid #ccc;"
        "margin:0;padding-left:.8rem}</style></head><body>",
        f"<h1>{sections['title']}</h1>",
        f"<blockquote>生成时间：{sections.get('generated_at', '')}</blockquote>",
    ]
    for block in sections.get("blocks", []):
        parts.append(f"<h2>{block['heading']}</h2>")
        body = block.get("body") or []
        if any(str(line).startswith("|") for line in body):
            parts.append(_markdown_table_to_html(body))
        else:
            parts.append("<ul>")
            for line in body:
                parts.append(f"<li>{line}</li>")
            parts.append("</ul>")
    parts.append("</body></html>")
    return "\n".join(parts)


def _markdown_table_to_html(lines: list[str]) -> str:
    rows = [line for line in lines if str(line).strip().startswith("|")]
    if len(rows) < 2:
        return ""
    html = ["<table>"]
    for index, row in enumerate(rows):
        cells = [c.strip() for c in str(row).strip("|").split("|")]
        if index == 1 and all(set(c) <= {"-", ":"} for c in cells):
            continue
        tag = "th" if index == 0 else "td"
        html.append("<tr>" + "".join(f"<{tag}>{c}</{tag}>" for c in cells) + "</tr>")
    html.append("</table>")
    return "".join(html)


def _histogram(series: pd.Series, bins: int = 10) -> tuple[list[int], list[float]]:
    """计算直方图频数与分箱边界。"""
    try:
        counts, edges = pd.cut(series, bins=bins, retbins=True)
        frequency = counts.value_counts(sort=False).tolist()
        return [int(v) for v in frequency], [float(e) for e in edges]
    except (ValueError, TypeError):
        return [], []


def _describe_r(value: float) -> str:
    magnitude = abs(value)
    direction = "正" if value > 0 else "负"
    if magnitude >= 0.8:
        return f"强{direction}相关"
    if magnitude >= 0.5:
        return f"中等{direction}相关"
    if magnitude >= 0.3:
        return f"弱{direction}相关"
    return "几乎无关"
