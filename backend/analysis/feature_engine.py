# -*- coding: utf-8 -*-
"""
特征工程引擎 v2.0
================

功能:
- 标准化 / 归一化 / RobustScaler
- 类别编码 (OneHot / Label / Target / Frequency)
- 特征选择 (方差阈值 / 相关性 / 互信息)
- 特征交叉 / 多项式特征
- 日期特征提取
- 文本特征提取 (TF-IDF)
- Pipeline 一键处理
"""
import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.preprocessing import (
    StandardScaler, MinMaxScaler, RobustScaler,
    LabelEncoder, OneHotEncoder
)
from sklearn.feature_selection import VarianceThreshold, mutual_info_classif, mutual_info_regression
from sklearn.impute import SimpleImputer

logger = logging.getLogger(__name__)


class FeatureEngine:
    """特征工程引擎"""
    
    def engineer(
        self,
        df: pd.DataFrame,
        target_col: str = None,
        task_type: str = "classification",  # classification / regression
        config: Dict[str, Any] = None,
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        执行特征工程 Pipeline
        
        Args:
            df: 原始数据
            target_col: 目标列名
            task_type: 任务类型
            config: 配置 (可选)
        
        Returns:
            (processed_df, report)
        """
        config = config or {}
        report = {"steps": [], "original_shape": df.shape, "final_shape": None}
        
        df_processed = df.copy()
        
        # Step 1: 缺失值处理
        df_processed, step_report = self._handle_missing(df_processed, config.get("missing"))
        report["steps"].append(step_report)
        
        # Step 2: 类别编码
        df_processed, step_report = self._encode_categorical(df_processed, target_col, config.get("encoding"))
        report["steps"].append(step_report)
        
        # Step 3: 数值缩放
        df_processed, step_report = self._scale_numeric(df_processed, target_col, config.get("scaling"))
        report["steps"].append(step_report)
        
        # Step 4: 日期特征提取
        df_processed, step_report = self._extract_datetime_features(df_processed)
        report["steps"].append(step_report)
        
        # Step 5: 特征选择 (如果有目标列)
        if target_col and target_col in df_processed.columns:
            df_processed, step_report = self._select_features(df_processed, target_col, task_type, config.get("selection"))
            report["steps"].append(step_report)
        
        report["final_shape"] = df_processed.shape
        report["columns"] = list(df_processed.columns)
        
        return df_processed, report
    
    # ==================== 缺失值处理 ====================
    
    def _handle_missing(self, df: pd.DataFrame, config: Dict = None) -> Tuple[pd.DataFrame, Dict]:
        """缺失值处理"""
        config = config or {}
        report = {"step": "missing_values", "actions": []}
        
        # 删除高缺失列 (>80%)
        threshold = config.get("drop_threshold", 0.8)
        missing_pct = df.isnull().sum() / len(df)
        drop_cols = missing_pct[missing_pct > threshold].index.tolist()
        if drop_cols:
            df = df.drop(columns=drop_cols)
            report["actions"].append(f"删除高缺失列(>{threshold*100}%): {drop_cols}")
        
        # 数值列: 中位数填充
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if numeric_cols:
            imputer = SimpleImputer(strategy='median')
            df[numeric_cols] = imputer.fit_transform(df[numeric_cols])
            report["actions"].append(f"数值列中位数填充: {numeric_cols}")
        
        # 分类列: 众数填充
        cat_cols = df.select_dtypes(include=["object"]).columns.tolist()
        for col in cat_cols:
            if df[col].isnull().sum() > 0:
                mode_val = df[col].mode()
                fill_val = mode_val.iloc[0] if len(mode_val) > 0 else "Unknown"
                df[col] = df[col].fillna(fill_val)
                report["actions"].append(f"分类列众数填充: {col} → {fill_val}")
        
        return df, report
    
    # ==================== 类别编码 ====================
    
    def _encode_categorical(self, df: pd.DataFrame, target_col: str = None, config: Dict = None) -> Tuple[pd.DataFrame, Dict]:
        """类别编码"""
        config = config or {}
        report = {"step": "encoding", "actions": []}
        
        cat_cols = df.select_dtypes(include=["object"]).columns.tolist()
        if target_col and target_col in cat_cols:
            cat_cols.remove(target_col)
        
        if not cat_cols:
            report["actions"].append("无分类列需要编码")
            return df, report
        
        # 低基数 → One-Hot
        # 高基数 → Label / Frequency
        max_onehot = config.get("max_onehot_categories", 10)
        
        for col in cat_cols:
            nunique = df[col].nunique()
            
            if nunique <= max_onehot:
                # One-Hot 编码
                dummies = pd.get_dummies(df[col], prefix=col, dtype=int)
                df = pd.concat([df.drop(columns=[col]), dummies], axis=1)
                report["actions"].append(f"OneHot编码: {col} ({nunique}类 → {len(dummies.columns)}列)")
            else:
                # Frequency 编码
                freq_map = df[col].value_counts(normalize=True).to_dict()
                df[f"{col}_freq"] = df[col].map(freq_map)
                df = df.drop(columns=[col])
                report["actions"].append(f"Frequency编码: {col} ({nunique}类 → 1列)")
        
        return df, report
    
    # ==================== 数值缩放 ====================
    
    def _scale_numeric(self, df: pd.DataFrame, target_col: str = None, config: Dict = None) -> Tuple[pd.DataFrame, Dict]:
        """数值缩放"""
        config = config or {}
        report = {"step": "scaling", "actions": []}
        
        scale_method = config.get("method", "standard")  # standard / minmax / robust / none
        
        if scale_method == "none":
            report["actions"].append("跳过缩放")
            return df, report
        
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if target_col and target_col in numeric_cols:
            numeric_cols.remove(target_col)
        
        if not numeric_cols:
            report["actions"].append("无数值列需要缩放")
            return df, report
        
        scalers = {
            "standard": StandardScaler(),
            "minmax": MinMaxScaler(),
            "robust": RobustScaler(),
        }
        
        scaler = scalers.get(scale_method, StandardScaler())
        df[numeric_cols] = scaler.fit_transform(df[numeric_cols])
        report["actions"].append(f"{scale_method} 缩放: {numeric_cols}")
        
        return df, report
    
    # ==================== 日期特征 ====================
    
    def _extract_datetime_features(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
        """提取日期特征"""
        report = {"step": "datetime_features", "actions": []}
        
        datetime_cols = df.select_dtypes(include=["datetime"]).columns.tolist()
        
        for col in datetime_cols:
            df[f"{col}_year"] = df[col].dt.year
            df[f"{col}_month"] = df[col].dt.month
            df[f"{col}_day"] = df[col].dt.day
            df[f"{col}_dayofweek"] = df[col].dt.dayofweek
            df[f"{col}_quarter"] = df[col].dt.quarter
            df = df.drop(columns=[col])
            report["actions"].append(f"日期特征提取: {col} → year/month/day/dayofweek/quarter")
        
        if not datetime_cols:
            report["actions"].append("无日期列")
        
        return df, report
    
    # ==================== 特征选择 ====================
    
    def _select_features(self, df: pd.DataFrame, target_col: str, task_type: str, config: Dict = None) -> Tuple[pd.DataFrame, Dict]:
        """特征选择"""
        config = config or {}
        report = {"step": "feature_selection", "actions": []}
        
        if target_col not in df.columns:
            report["actions"].append("目标列不在数据中，跳过特征选择")
            return df, report
        
        # 准备数据
        feature_cols = [c for c in df.select_dtypes(include=[np.number]).columns if c != target_col]
        if not feature_cols:
            return df, report
        
        X = df[feature_cols].fillna(0)
        y = df[target_col]
        
        # 方差阈值
        selector = VarianceThreshold(threshold=config.get("variance_threshold", 0.01))
        X_selected = selector.fit_transform(X)
        selected_mask = selector.get_support()
        dropped_cols = [c for c, s in zip(feature_cols, selected_mask) if not s]
        
        if dropped_cols:
            df = df.drop(columns=dropped_cols)
            report["actions"].append(f"方差阈值删除: {dropped_cols}")
        
        # 互信息特征排名
        try:
            if task_type == "classification":
                mi_scores = mutual_info_classif(X_selected, y, random_state=42)
            else:
                mi_scores = mutual_info_regression(X_selected, y, random_state=42)
            
            remaining_cols = [c for c, s in zip(feature_cols, selected_mask) if s]
            mi_ranking = sorted(zip(remaining_cols, mi_scores), key=lambda x: -x[1])
            report["mutual_info_ranking"] = [
                {"feature": col, "score": round(float(score), 4)} for col, score in mi_ranking[:20]
            ]
            report["actions"].append(f"互信息特征排名完成 (top {min(20, len(mi_ranking))})")
        except Exception as e:
            report["actions"].append(f"互信息计算失败: {e}")
        
        return df, report
