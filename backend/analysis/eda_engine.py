# -*- coding: utf-8 -*-
"""
EDA 增强引擎 v2.0
================

功能:
- 数据画像（质量评分、字段类型推断）
- 缺失值分析 + 处理建议
- 分布分析 + 可视化数据
- 异常值检测增强（IQR + Z-Score + Isolation Forest）
- 相关性分析（Pearson + Spearman + Kendall）
- 自动 EDA 报告生成
"""
import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

logger = logging.getLogger(__name__)


class EDAEngine:
    """EDA 增强引擎"""
    
    def analyze(self, df: pd.DataFrame, dataset_name: str = "dataset") -> Dict[str, Any]:
        """
        执行完整 EDA 分析
        
        Returns:
            {
                "dataset_name": str,
                "overview": {...},
                "data_quality": {...},
                "columns_profile": [...],
                "missing_values": {...},
                "correlation": {...},
                "outliers": {...},
                "suggestions": [...],
            }
        """
        result = {
            "dataset_name": dataset_name,
            "overview": self._overview(df),
            "data_quality": self._data_quality(df),
            "columns_profile": self._columns_profile(df),
            "missing_values": self._missing_values(df),
            "correlation": self._correlation(df),
            "outliers": self._outliers(df),
            "suggestions": self._generate_suggestions(df),
        }
        return result
    
    # ==================== 数据概览 ====================
    
    def _overview(self, df: pd.DataFrame) -> Dict[str, Any]:
        """数据概览"""
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
        datetime_cols = df.select_dtypes(include=["datetime"]).columns.tolist()
        
        return {
            "row_count": len(df),
            "column_count": len(df.columns),
            "numeric_column_count": len(numeric_cols),
            "categorical_column_count": len(cat_cols),
            "datetime_column_count": len(datetime_cols),
            "numeric_columns": numeric_cols,
            "categorical_columns": cat_cols,
            "datetime_columns": datetime_cols,
            "memory_mb": round(df.memory_usage(deep=True).sum() / 1024 / 1024, 2),
            "duplicate_row_count": int(df.duplicated().sum()),
            "duplicate_row_pct": round(df.duplicated().sum() / max(len(df), 1) * 100, 2),
        }
    
    # ==================== 数据质量评分 ====================
    
    def _data_quality(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        数据质量评分
        
        评分维度:
        - 完整性 (0-100): 无缺失值 = 100
        - 唯一性 (0-100): 无重复 = 100
        - 一致性 (0-100): 数据类型一致 = 100
        - 及时性 (0-100): 有时间字段且近期 = 100
        """
        total_cells = len(df) * len(df.columns)
        missing_cells = int(df.isnull().sum().sum())
        
        # 完整性
        completeness = round((1 - missing_cells / max(total_cells, 1)) * 100, 1)
        
        # 唯一性
        uniqueness = round((1 - df.duplicated().sum() / max(len(df), 1)) * 100, 1)
        
        # 一致性（检查混合类型列）
        inconsistent_cols = 0
        for col in df.columns:
            if df[col].dtype == object:
                non_null = df[col].dropna()
                if len(non_null) > 0:
                    types = set(type(v).__name__ for v in non_null.head(100))
                    if len(types) > 1:
                        inconsistent_cols += 1
        consistency = round((1 - inconsistent_cols / max(len(df.columns), 1)) * 100, 1)
        
        # 综合评分
        overall = round(completeness * 0.4 + uniqueness * 0.3 + consistency * 0.3, 1)
        
        # 质量等级
        if overall >= 90:
            grade = "A"
            grade_desc = "优秀 - 数据质量很高，可直接用于分析"
        elif overall >= 75:
            grade = "B"
            grade_desc = "良好 - 数据质量较好，轻微清洗后可用"
        elif overall >= 60:
            grade = "C"
            grade_desc = "一般 - 需要一定清洗和预处理"
        elif overall >= 40:
            grade = "D"
            grade_desc = "较差 - 需要大量清洗工作"
        else:
            grade = "F"
            grade_desc = "很差 - 数据质量严重不足，建议重新采集"
        
        return {
            "overall_score": overall,
            "grade": grade,
            "grade_description": grade_desc,
            "dimensions": {
                "completeness": {"score": completeness, "weight": 0.4},
                "uniqueness": {"score": uniqueness, "weight": 0.3},
                "consistency": {"score": consistency, "weight": 0.3},
            },
            "missing_cells": missing_cells,
            "total_cells": total_cells,
            "duplicate_rows": int(df.duplicated().sum()),
        }
    
    # ==================== 列画像 ====================
    
    def _columns_profile(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """每列详细画像"""
        profiles = []
        
        for col in df.columns:
            series = df[col]
            non_null = series.dropna()
            profile = {
                "name": col,
                "dtype": str(series.dtype),
                "count": len(series),
                "non_null_count": len(non_null),
                "null_count": int(series.isnull().sum()),
                "null_pct": round(series.isnull().sum() / max(len(series), 1) * 100, 2),
                "inferred_type": self._infer_column_type(non_null),
            }
            
            # 数值列
            if pd.api.types.is_numeric_dtype(series):
                profile.update({
                    "mean": round(float(non_null.mean()), 4) if len(non_null) > 0 else None,
                    "median": round(float(non_null.median()), 4) if len(non_null) > 0 else None,
                    "std": round(float(non_null.std()), 4) if len(non_null) > 1 else None,
                    "min": round(float(non_null.min()), 4) if len(non_null) > 0 else None,
                    "max": round(float(non_null.max()), 4) if len(non_null) > 0 else None,
                    "skewness": round(float(non_null.skew()), 4) if len(non_null) > 2 else None,
                    "kurtosis": round(float(non_null.kurtosis()), 4) if len(non_null) > 3 else None,
                    "unique_count": int(non_null.nunique()),
                    "zero_count": int((non_null == 0).sum()),
                    "negative_count": int((non_null < 0).sum()),
                })
            # 分类列
            elif pd.api.types.is_string_dtype(series) or pd.api.types.is_object_dtype(series):
                value_counts = non_null.value_counts().head(10)
                profile.update({
                    "unique_count": int(non_null.nunique()),
                    "top_values": {str(k): int(v) for k, v in value_counts.items()},
                    "avg_length": round(float(non_null.str.len().mean()), 1) if len(non_null) > 0 else 0,
                })
            # 日期列
            elif pd.api.types.is_datetime64_any_dtype(series):
                profile.update({
                    "min_date": str(non_null.min()) if len(non_null) > 0 else None,
                    "max_date": str(non_null.max()) if len(non_null) > 0 else None,
                    "date_range_days": int((non_null.max() - non_null.min()).days) if len(non_null) > 1 else 0,
                })
            
            profiles.append(profile)
        
        return profiles
    
    def _infer_column_type(self, series: pd.Series) -> str:
        """推断列的语义类型"""
        if len(series) == 0:
            return "empty"
        
        if pd.api.types.is_numeric_dtype(series):
            # 检查是否是 ID
            if series.nunique() == len(series):
                return "id"
            # 检查是否是布尔值（0/1）
            if set(series.unique()) <= {0, 1, 0.0, 1.0}:
                return "boolean_numeric"
            # 检查是否是类别（少量唯一值）
            if series.nunique() <= 10:
                return "categorical_numeric"
            return "continuous"
        
        if pd.api.types.is_datetime64_any_dtype(series):
            return "datetime"
        
        if pd.api.types.is_string_dtype(series) or pd.api.types.is_object_dtype(series):
            nunique = series.nunique()
            # 高唯一性 → ID 或文本
            if nunique > len(series) * 0.8:
                # 检查是否像邮箱
                sample = str(series.iloc[0]) if len(series) > 0 else ""
                if "@" in sample:
                    return "email"
                if sample.startswith("http"):
                    return "url"
                return "id_or_text"
            # 低唯一性 → 类别
            if nunique <= 20:
                return "categorical"
            return "text"
        
        return "other"
    
    # ==================== 缺失值分析 ====================
    
    def _missing_values(self, df: pd.DataFrame) -> Dict[str, Any]:
        """缺失值分析 + 处理建议"""
        total_cells = len(df) * len(df.columns)
        missing_per_col = df.isnull().sum()
        missing_cols = missing_per_col[missing_per_col > 0]
        
        result = {
            "total_missing": int(missing_per_col.sum()),
            "total_missing_pct": round(missing_per_col.sum() / max(total_cells, 1) * 100, 2),
            "columns_with_missing": len(missing_cols),
            "columns_detail": [],
            "patterns": [],
            "suggestions": [],
        }
        
        # 每列缺失详情
        for col in missing_cols.index:
            missing_count = int(missing_cols[col])
            missing_pct = round(missing_count / len(df) * 100, 2)
            
            suggestion = self._missing_value_suggestion(df, col, missing_pct)
            
            result["columns_detail"].append({
                "column": col,
                "missing_count": missing_count,
                "missing_pct": missing_pct,
                "dtype": str(df[col].dtype),
                "suggestion": suggestion,
            })
        
        # 缺失模式检测
        if len(missing_cols) > 1:
            # 检查是否同时缺失
            missing_matrix = df[missing_cols.index].isnull()
            co_missing = missing_matrix.corr()
            
            for i, col1 in enumerate(co_missing.columns):
                for j, col2 in enumerate(co_missing.columns):
                    if i < j and abs(co_missing.iloc[i, j]) > 0.7:
                        result["patterns"].append({
                            "type": "co_missing",
                            "columns": [col1, col2],
                            "correlation": round(float(co_missing.iloc[i, j]), 4),
                            "description": f"{col1} 和 {col2} 的缺失高度相关 ({co_missing.iloc[i, j]:.2f})",
                        })
        
        return result
    
    def _missing_value_suggestion(self, df: pd.DataFrame, col: str, missing_pct: float) -> Dict[str, Any]:
        """缺失值处理建议"""
        if missing_pct > 80:
            return {
                "action": "drop_column",
                "reason": f"缺失率 {missing_pct}% 过高，建议删除该列",
                "confidence": "high",
            }
        
        if pd.api.types.is_numeric_dtype(df[col]):
            return {
                "action": "fill_median",
                "reason": f"数值列，缺失率 {missing_pct}%，建议用中位数填充（抗异常值）",
                "confidence": "high",
                "alternatives": ["fill_mean", "fill_mode", "interpolate", "fill_knn"],
            }
        
        return {
            "action": "fill_mode",
            "reason": f"分类列，缺失率 {missing_pct}%，建议用众数填充或新增'未知'类别",
            "confidence": "medium",
            "alternatives": ["fill_unknown_category", "drop_rows"],
        }
    
    # ==================== 相关性分析 ====================
    
    def _correlation(self, df: pd.DataFrame) -> Dict[str, Any]:
        """相关性分析（Pearson + Spearman）"""
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        result = {
            "pearson": {},
            "spearman": {},
            "high_correlation_pairs": [],
        }
        
        if len(numeric_cols) < 2:
            return result
        
        numeric_df = df[numeric_cols].dropna()
        
        if len(numeric_df) < 3:
            return result
        
        # Pearson
        try:
            pearson_corr = numeric_df.corr(method='pearson').round(4)
            result["pearson"] = pearson_corr.to_dict()
        except Exception:
            pass
        
        # Spearman
        try:
            spearman_corr = numeric_df.corr(method='spearman').round(4)
            result["spearman"] = spearman_corr.to_dict()
        except Exception:
            pass
        
        # 高相关性对
        for i, col1 in enumerate(numeric_cols):
            for j, col2 in enumerate(numeric_cols):
                if i < j:
                    try:
                        p_corr = pearson_corr.loc[col1, col2] if col1 in pearson_corr.index and col2 in pearson_corr.columns else 0
                        if abs(p_corr) > 0.7:
                            result["high_correlation_pairs"].append({
                                "col1": col1,
                                "col2": col2,
                                "pearson": round(float(p_corr), 4),
                                "interpretation": self._interpret_correlation(p_corr),
                            })
                    except Exception:
                        pass
        
        return result
    
    def _interpret_correlation(self, r: float) -> str:
        """解释相关性"""
        abs_r = abs(r)
        direction = "正" if r > 0 else "负"
        if abs_r > 0.9:
            return f"极强{direction}相关"
        elif abs_r > 0.7:
            return f"强{direction}相关"
        elif abs_r > 0.5:
            return f"中等{direction}相关"
        elif abs_r > 0.3:
            return f"弱{direction}相关"
        else:
            return "极弱相关或无关"
    
    # ==================== 异常值检测 ====================
    
    def _outliers(self, df: pd.DataFrame) -> Dict[str, Any]:
        """异常值检测（IQR + Z-Score）"""
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        result = {"columns": {}}
        
        for col in numeric_cols:
            series = df[col].dropna()
            if len(series) < 4:
                continue
            
            col_outliers = {}
            
            # IQR 方法
            Q1 = series.quantile(0.25)
            Q3 = series.quantile(0.75)
            IQR = Q3 - Q1
            lower = Q1 - 1.5 * IQR
            upper = Q3 + 1.5 * IQR
            iqr_outliers = series[(series < lower) | (series > upper)]
            
            col_outliers["iqr"] = {
                "count": int(len(iqr_outliers)),
                "pct": round(len(iqr_outliers) / len(series) * 100, 2),
                "lower_bound": round(float(lower), 4),
                "upper_bound": round(float(upper), 4),
            }
            
            # Z-Score 方法
            z_scores = np.abs((series - series.mean()) / series.std())
            z_outliers = series[z_scores > 3]
            
            col_outliers["zscore"] = {
                "count": int(len(z_outliers)),
                "pct": round(len(z_outliers) / len(series) * 100, 2),
                "threshold": 3.0,
            }
            
            # 处理建议
            outlier_pct = max(col_outliers["iqr"]["pct"], col_outliers["zscore"]["pct"])
            if outlier_pct > 10:
                col_outliers["suggestion"] = "异常值较多，建议使用 IQR 截断或对数变换"
            elif outlier_pct > 3:
                col_outliers["suggestion"] = "存在少量异常值，建议 IQR 截断"
            else:
                col_outliers["suggestion"] = "异常值很少，可保留或轻微处理"
            
            result["columns"][col] = col_outliers
        
        return result
    
    # ==================== 建议生成 ====================
    
    def _generate_suggestions(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """基于分析结果生成建议"""
        suggestions = []
        
        # 1. 缺失值建议
        missing_cols = df.isnull().sum()
        high_missing = missing_cols[missing_cols > len(df) * 0.5]
        if len(high_missing) > 0:
            suggestions.append({
                "type": "missing_values",
                "priority": "high",
                "title": "高缺失率列",
                "description": f"发现 {len(high_missing)} 列缺失率 >50%，建议删除或谨慎处理",
                "columns": list(high_missing.index),
            })
        
        # 2. 重复行建议
        dup_count = int(df.duplicated().sum())
        if dup_count > 0:
            suggestions.append({
                "type": "duplicates",
                "priority": "medium",
                "title": "重复行",
                "description": f"发现 {dup_count} 行重复数据 ({dup_count/len(df)*100:.1f}%)",
                "action": "建议去重",
            })
        
        # 3. 高基数分类列
        cat_cols = df.select_dtypes(include=["object"]).columns
        for col in cat_cols:
            nunique = df[col].nunique()
            if nunique > 50:
                suggestions.append({
                    "type": "high_cardinality",
                    "priority": "low",
                    "title": f"高基数分类列: {col}",
                    "description": f"列 '{col}' 有 {nunique} 个唯一值，编码时注意维度",
                    "action": "建议使用目标编码或哈希编码",
                })
        
        # 4. 偏态分布
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            if df[col].skew() > 2 or df[col].skew() < -2:
                suggestions.append({
                    "type": "skewness",
                    "priority": "medium",
                    "title": f"严重偏态: {col}",
                    "description": f"列 '{col}' 偏度={df[col].skew():.2f}，分布严重偏斜",
                    "action": "建议对数变换或 Box-Cox 变换",
                })
        
        # 5. 高相关性
        if len(numeric_cols) >= 2:
            corr = df[numeric_cols].corr()
            for i, c1 in enumerate(numeric_cols):
                for j, c2 in enumerate(numeric_cols):
                    if i < j and abs(corr.loc[c1, c2]) > 0.9:
                        suggestions.append({
                            "type": "multicollinearity",
                            "priority": "medium",
                            "title": f"多重共线性: {c1} ↔ {c2}",
                            "description": f"相关系数={corr.loc[c1, c2]:.4f}，高度相关",
                            "action": "建议删除其中一列或使用 PCA 降维",
                        })
        
        return suggestions
