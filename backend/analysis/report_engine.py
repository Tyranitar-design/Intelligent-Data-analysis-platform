# -*- coding: utf-8 -*-
"""
分析报告引擎 v2.0
=================

功能:
- 自动分析报告生成
- Markdown / HTML 输出
- 图表数据嵌入
- 报告模板系统
"""
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class ReportEngine:
    """分析报告引擎"""
    
    def generate_eda_report(
        self,
        eda_result: Dict[str, Any],
        dataset_name: str = "dataset",
        format: str = "markdown",  # markdown / html
    ) -> str:
        """生成 EDA 报告"""
        if format == "html":
            return self._eda_to_html(eda_result, dataset_name)
        return self._eda_to_markdown(eda_result, dataset_name)
    
    def generate_ml_report(
        self,
        ml_result: Dict[str, Any],
        format: str = "markdown",
    ) -> str:
        """生成 ML 训练报告"""
        if format == "html":
            return self._ml_to_html(ml_result)
        return self._ml_to_markdown(ml_result)
    
    def generate_full_report(
        self,
        dataset_name: str,
        eda_result: Dict[str, Any] = None,
        ml_result: Dict[str, Any] = None,
        mining_result: Dict[str, Any] = None,
        dl_result: Dict[str, Any] = None,
        format: str = "markdown",
    ) -> str:
        """生成完整分析报告"""
        sections = []
        
        # 标题
        sections.append(f"# 📊 {dataset_name} — 数据分析报告\n")
        sections.append(f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        
        # EDA 部分
        if eda_result:
            sections.append(self._eda_to_markdown(eda_result, dataset_name))
        
        # ML 部分
        if ml_result:
            sections.append(self._ml_to_markdown(ml_result))
        
        # 数据挖掘部分
        if mining_result:
            sections.append(self._mining_to_markdown(mining_result))
        
        # DL 部分
        if dl_result:
            sections.append(self._dl_to_markdown(dl_result))
        
        return "\n\n---\n\n".join(sections)
    
    # ==================== EDA 报告 ====================
    
    def _eda_to_markdown(self, result: Dict, dataset_name: str) -> str:
        """EDA → Markdown"""
        lines = []
        
        # 概览
        ov = result.get("overview", {})
        dq = result.get("data_quality", {})
        
        lines.append("## 📋 数据概览")
        lines.append("")
        lines.append(f"| 指标 | 值 |")
        lines.append(f"|------|-----|")
        lines.append(f"| 数据集 | {dataset_name} |")
        lines.append(f"| 行数 | {ov.get('row_count', 'N/A')} |")
        lines.append(f"| 列数 | {ov.get('column_count', 'N/A')} |")
        lines.append(f"| 数值列 | {ov.get('numeric_column_count', 'N/A')} |")
        lines.append(f"| 分类列 | {ov.get('categorical_column_count', 'N/A')} |")
        lines.append(f"| 重复行 | {ov.get('duplicate_row_count', 'N/A')} |")
        lines.append(f"| 内存 | {ov.get('memory_mb', 'N/A')} MB |")
        lines.append("")
        
        # 质量评分
        lines.append("## 🏆 数据质量评分")
        lines.append("")
        grade = dq.get("grade", "?")
        score = dq.get("overall_score", 0)
        lines.append(f"**综合评分: {score}/100 ({grade}级)**")
        lines.append("")
        lines.append(f"> {dq.get('grade_description', '')}")
        lines.append("")
        
        dims = dq.get("dimensions", {})
        lines.append("| 维度 | 分数 | 权重 |")
        lines.append("|------|------|------|")
        for dim_name, dim_info in dims.items():
            lines.append(f"| {dim_name} | {dim_info['score']} | {dim_info['weight']} |")
        lines.append("")
        
        # 缺失值
        mv = result.get("missing_values", {})
        if mv.get("columns_detail"):
            lines.append("## 🔍 缺失值分析")
            lines.append("")
            lines.append(f"总缺失: {mv.get('total_missing', 0)} 格 ({mv.get('total_missing_pct', 0)}%)")
            lines.append("")
            lines.append("| 列名 | 缺失率 | 建议操作 |")
            lines.append("|------|--------|----------|")
            for detail in mv.get("columns_detail", []):
                lines.append(f"| {detail['column']} | {detail['missing_pct']}% | {detail['suggestion']['action']} |")
            lines.append("")
        
        # 建议
        suggestions = result.get("suggestions", [])
        if suggestions:
            lines.append("## 💡 分析建议")
            lines.append("")
            for s in suggestions:
                priority = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(s.get("priority", "low"), "⚪")
                lines.append(f"- {priority} **{s.get('title', '')}** — {s.get('description', s.get('action', ''))}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _eda_to_html(self, result: Dict, dataset_name: str) -> str:
        """EDA → HTML"""
        md_content = self._eda_to_markdown(result, dataset_name)
        return self._markdown_to_html(md_content, f"EDA 报告 — {dataset_name}")
    
    # ==================== ML 报告 ====================
    
    def _ml_to_markdown(self, result: Dict) -> str:
        """ML → Markdown"""
        lines = []
        
        lines.append("## 🤖 机器学习模型报告")
        lines.append("")
        
        lines.append(f"| 指标 | 值 |")
        lines.append(f"|------|-----|")
        lines.append(f"| 算法 | {result.get('algorithm', 'N/A')} |")
        lines.append(f"| 任务类型 | {result.get('task_type', 'N/A')} |")
        lines.append(f"| 模型ID | {result.get('model_id', 'N/A')} |")
        lines.append(f"| 训练时间 | {result.get('training_time_seconds', 'N/A')}s |")
        lines.append(f"| CV均值 | {result.get('cv_mean', 'N/A')} |")
        lines.append("")
        
        # 评估指标
        ev = result.get("evaluation", {})
        if ev:
            lines.append("### 📈 评估指标")
            lines.append("")
            lines.append("| 指标 | 值 |")
            lines.append("|------|-----|")
            for key, value in ev.items():
                if key not in ["confusion_matrix"] and not isinstance(value, (list, dict)):
                    lines.append(f"| {key} | {value} |")
            lines.append("")
        
        # 特征重要性
        fi = result.get("feature_importance", {})
        if fi:
            lines.append("### 🔑 特征重要性 (Top 10)")
            lines.append("")
            sorted_fi = sorted(fi.items(), key=lambda x: -x[1])[:10]
            for name, importance in sorted_fi:
                bar = "█" * int(importance * 50)
                lines.append(f"- **{name}**: {importance:.4f} {bar}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _ml_to_html(self, result: Dict) -> str:
        """ML → HTML"""
        md_content = self._ml_to_markdown(result)
        return self._markdown_to_html(md_content, "ML 模型报告")
    
    # ==================== 挖掘报告 ====================
    
    def _mining_to_markdown(self, result: Dict) -> str:
        lines = []
        lines.append("## ⛏️ 数据挖掘结果")
        lines.append("")
        
        # 异常检测
        if "anomaly_count" in result:
            lines.append(f"### 异常检测 ({result.get('method', '')})")
            lines.append(f"- 异常样本: {result['anomaly_count']}/{result['total_samples']} ({result['anomaly_pct']}%)")
            lines.append("")
        
        # 关联规则
        if "rules" in result:
            rules = result.get("rules", [])
            lines.append(f"### 关联规则 (共 {len(rules)} 条)")
            lines.append("")
            for r in rules[:10]:
                lines.append(f"- {list(r['antecedents'])} → {list(r['consequents'])} (支持度={r['support']}, 置信度={r['confidence']}, 提升度={r['lift']})")
            lines.append("")
        
        # 降维
        if "points" in result:
            lines.append(f"### 降维可视化 ({result.get('method', '')})")
            lines.append(f"- 样本数: {result.get('sample_size', 'N/A')}")
            if "explained_variance" in result:
                lines.append(f"- 解释方差: {result.get('total_variance_explained', 'N/A')}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _dl_to_markdown(self, result: Dict) -> str:
        lines = []
        lines.append("## 🧠 深度学习结果")
        lines.append("")
        
        method = result.get("method", "")
        if "prophet" in method.lower() or "forecast" in result:
            lines.append(f"### 时序预测 ({method})")
            forecast = result.get("forecast", [])
            if forecast:
                lines.append(f"- 预测期数: {len(forecast)}")
                lines.append(f"- 第一期预测: {forecast[0] if forecast else 'N/A'}")
                lines.append(f"- 最后一期预测: {forecast[-1] if forecast else 'N/A'}")
        elif "sentiment" in str(result):
            lines.append("### 情感分析")
            lines.append(f"- 正面: {result.get('positive', 'N/A')}")
            lines.append(f"- 负面: {result.get('negative', 'N/A')}")
            lines.append(f"- 中性: {result.get('neutral', 'N/A')}")
        
        lines.append("")
        return "\n".join(lines)
    
    # ==================== 工具方法 ====================
    
    def _markdown_to_html(self, md: str, title: str = "分析报告") -> str:
        """Markdown → 简易 HTML"""
        # 简单转换（生产环境应用 markdown 库）
        html = md
        html = html.replace("\n", "<br>\n")
        html = html.replace("## ", "<h2>")
        html = html.replace("### ", "<h3>")
        html = html.replace("**", "<strong>")
        html = html.replace("| ", "<td>")
        
        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{title}</title>
    <style>
        body {{ font-family: -apple-system, sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px; }}
        h1 {{ color: #1a1a2e; border-bottom: 2px solid #16213e; padding-bottom: 10px; }}
        h2 {{ color: #16213e; margin-top: 30px; }}
        h3 {{ color: #0f3460; }}
        table {{ border-collapse: collapse; width: 100%; margin: 15px 0; }}
        td, th {{ border: 1px solid #ddd; padding: 8px 12px; text-align: left; }}
        blockquote {{ background: #f8f9fa; padding: 15px; border-left: 4px solid #0f3460; margin: 15px 0; }}
    </style>
</head>
<body>
{html}
</body>
</html>"""
