"""
自动报告生成服务
- EDA 报告
- ML 模型报告
- 综合分析报告
"""
import os
import json
import time
from typing import Dict, Any, Optional
from datetime import datetime


class ReportService:
    """报告生成服务"""

    def __init__(self, output_dir: str = None):
        if output_dir is None:
            output_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "data", "reports"
            )
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate_eda_report(self, eda_result: Dict, source_type: str) -> Dict[str, Any]:
        """生成 EDA 报告"""
        start_time = time.time()
        overview = eda_result.get("overview", {})
        numeric = eda_result.get("numeric_summary", {})
        categorical = eda_result.get("categorical_summary", {})
        correlation = eda_result.get("correlation", {})

        # 构建报告内容
        sections = []

        # 概述
        sections.append({
            "title": "Data Overview",
            "content": [
                f"Total records: **{overview.get('row_count', 'N/A')}**",
                f"Total columns: **{overview.get('column_count', 'N/A')}**",
                f"Missing values: **{overview.get('missing_values', 0)}** ({overview.get('missing_pct', 0)}%)",
                f"Duplicate rows: **{overview.get('duplicate_rows', 0)}**",
                f"Memory usage: **{overview.get('memory_mb', 0)} MB**",
            ]
        })

        # 数值列分析
        if numeric:
            num_items = []
            for col, stats in numeric.items():
                num_items.append(
                    f"- **{col}**: mean={stats.get('mean')}, std={stats.get('std')}, "
                    f"range=[{stats.get('min')}, {stats.get('max')}]"
                )
            sections.append({
                "title": "Numeric Columns Analysis",
                "content": num_items
            })

        # 分类列分析
        if categorical:
            cat_items = []
            for col, stats in categorical.items():
                top_vals = stats.get("top_values", {})
                top_str = ", ".join([f"{k}({v})" for k, v in list(top_vals.items())[:3]])
                cat_items.append(f"- **{col}**: {stats.get('unique_count')} unique, top: {top_str}")
            sections.append({
                "title": "Categorical Columns Analysis",
                "content": cat_items
            })

        # 相关性
        if correlation:
            corr_items = []
            for col1, corr_dict in correlation.items():
                for col2, val in corr_dict.items():
                    if col1 < col2 and abs(val) > 0.5:
                        strength = "strong" if abs(val) > 0.8 else "moderate"
                        direction = "positive" if val > 0 else "negative"
                        corr_items.append(f"- **{col1}** <-> **{col2}**: {val} ({strength} {direction})")
            if corr_items:
                sections.append({
                    "title": "Notable Correlations",
                    "content": corr_items
                })

        # 保存报告
        report = {
            "title": f"EDA Report - {source_type}",
            "type": "eda",
            "source_type": source_type,
            "generated_at": datetime.now().isoformat(),
            "sections": sections,
            "elapsed_time": round(time.time() - start_time, 2),
        }

        filepath = self._save_report(report, source_type, "eda")
        report["filepath"] = filepath

        return report

    def generate_ml_report(self, model_info: Dict, training_result: Dict) -> Dict[str, Any]:
        """生成 ML 模型报告"""
        start_time = time.time()
        metrics = training_result.get("metrics", {})
        model_type = training_result.get("model_type", "unknown")
        algorithm = training_result.get("algorithm", "unknown")

        sections = []

        # 模型概述
        sections.append({
            "title": "Model Overview",
            "content": [
                f"Model type: **{model_type}**",
                f"Algorithm: **{algorithm}**",
                f"Training time: **{training_result.get('training_time', 'N/A')}s**",
            ]
        })

        # 关键指标
        metric_items = []
        for key, value in metrics.items():
            if isinstance(value, (int, float)):
                metric_items.append(f"- **{key}**: {value}")
        if metric_items:
            sections.append({
                "title": "Key Metrics",
                "content": metric_items
            })

        # 模型评估
        if model_type == "classification":
            accuracy = metrics.get("accuracy", 0)
            f1 = metrics.get("f1_score", 0)
            quality = "Good" if accuracy > 0.8 else "Fair" if accuracy > 0.6 else "Needs improvement"
            sections.append({
                "title": "Classification Assessment",
                "content": [
                    f"Accuracy: **{accuracy}**",
                    f"F1 Score: **{f1}**",
                    f"Model quality: **{quality}**",
                    f"CV Accuracy: **{metrics.get('cv_accuracy_mean', 'N/A')}** (+/- {metrics.get('cv_accuracy_std', 'N/A')})",
                ]
            })
        elif model_type == "regression":
            r2 = metrics.get("r2", 0)
            quality = "Good" if r2 > 0.8 else "Fair" if r2 > 0.5 else "Needs improvement"
            sections.append({
                "title": "Regression Assessment",
                "content": [
                    f"R2 Score: **{r2}**",
                    f"MAE: **{metrics.get('mae', 'N/A')}**",
                    f"RMSE: **{metrics.get('rmse', 'N/A')}**",
                    f"Model quality: **{quality}**",
                ]
            })

        report = {
            "title": f"ML Report - {algorithm} ({model_type})",
            "type": "ml",
            "model_type": model_type,
            "algorithm": algorithm,
            "generated_at": datetime.now().isoformat(),
            "sections": sections,
            "elapsed_time": round(time.time() - start_time, 2),
        }

        filepath = self._save_report(report, f"{algorithm}_{model_type}", "ml")
        report["filepath"] = filepath

        return report

    def generate_comprehensive_report(self, eda_result: Dict, ml_result: Dict,
                                       source_type: str) -> Dict[str, Any]:
        """生成综合分析报告"""
        start_time = time.time()

        sections = []

        # 执行摘要
        sections.append({
            "title": "Executive Summary",
            "content": [
                f"Data source: **{source_type}**",
                f"Records analyzed: **{eda_result.get('overview', {}).get('row_count', 'N/A')}**",
                f"ML model: **{ml_result.get('algorithm', 'N/A')}** ({ml_result.get('model_type', 'N/A')})",
                f"Training time: **{ml_result.get('training_time', 'N/A')}s**",
            ]
        })

        # 数据质量
        overview = eda_result.get("overview", {})
        quality_score = 100
        if overview.get("missing_pct", 0) > 5:
            quality_score -= 20
        if overview.get("duplicate_rows", 0) > 0:
            quality_score -= 10
        quality_score = max(quality_score, 0)

        sections.append({
            "title": "Data Quality Score",
            "content": [
                f"Quality score: **{quality_score}/100**",
                f"Missing data: **{overview.get('missing_pct', 0)}%**",
                f"Duplicate rows: **{overview.get('duplicate_rows', 0)}**",
            ]
        })

        # 模型表现
        ml_metrics = ml_result.get("metrics", {})
        model_type = ml_result.get("model_type", "")
        if model_type == "classification":
            key_metric = f"Accuracy: {ml_metrics.get('accuracy', 'N/A')}"
        elif model_type == "regression":
            key_metric = f"R2: {ml_metrics.get('r2', 'N/A')}"
        elif model_type == "clustering":
            key_metric = f"Silhouette: {ml_metrics.get('silhouette_score', 'N/A')}"
        else:
            key_metric = "N/A"

        sections.append({
            "title": "Model Performance",
            "content": [
                f"Key metric: **{key_metric}**",
                f"Algorithm: **{ml_result.get('algorithm', 'N/A')}**",
            ]
        })

        report = {
            "title": f"Comprehensive Report - {source_type}",
            "type": "comprehensive",
            "source_type": source_type,
            "quality_score": quality_score,
            "generated_at": datetime.now().isoformat(),
            "sections": sections,
            "elapsed_time": round(time.time() - start_time, 2),
        }

        filepath = self._save_report(report, source_type, "comprehensive")
        report["filepath"] = filepath

        return report

    def generate_table_eda_report(
        self,
        table_name: str,
        dataset_name: str,
        eda_result: Dict[str, Any],
        row_count: int,
        column_count: int,
    ) -> Dict[str, Any]:
        """基于真实数据表生成 EDA 报告"""
        report = self.generate_eda_report(eda_result, table_name)
        report["title"] = f"EDA Report - {dataset_name}"
        report["table_name"] = table_name
        report["dataset_name"] = dataset_name
        report["row_count"] = row_count
        report["column_count"] = column_count
        report["source_type"] = "dataset_table"
        return report

    def _save_report(self, report: Dict, name: str, report_type: str) -> str:
        """保存报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{report_type}_{name}_{timestamp}.json"
        filepath = os.path.join(self.output_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)

        return filepath
