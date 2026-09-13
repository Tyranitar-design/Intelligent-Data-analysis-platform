# -*- coding: utf-8 -*-
"""
数据挖掘 Pipeline v2.0
=====================

功能:
- 关联规则 (Apriori / FP-Growth)
- 异常检测 (Isolation Forest)
- 降维可视化 (PCA / t-SNE / UMAP)
"""
import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.ensemble import IsolationForest
from sklearn.manifold import TSNE

logger = logging.getLogger(__name__)


class MiningPipeline:
    """数据挖掘 Pipeline"""
    
    # ==================== 关联规则 ====================
    
    def association_rules(
        self,
        df: pd.DataFrame,
        columns: List[str] = None,
        min_support: float = 0.05,
        min_confidence: float = 0.5,
        min_lift: float = 1.0,
        max_rules: int = 50,
    ) -> Dict[str, Any]:
        """
        关联规则挖掘 (Apriori)
        
        Args:
            df: 数据 (分类列效果最好)
            columns: 参与分析的列
            min_support: 最小支持度
            min_confidence: 最小置信度
            min_lift: 最小提升度
        """
        try:
            from mlxtend.frequent_patterns import apriori, association_rules as ar_func
            from mlxtend.preprocessing import TransactionEncoder
        except ImportError:
            return {"error": "mlxtend 未安装，请运行: pip install mlxtend"}
        
        # 准备数据
        if columns:
            df = df[columns]
        
        # 分类列独热编码
        cat_cols = df.select_dtypes(include=["object"]).columns.tolist()
        if cat_cols:
            df_encoded = pd.get_dummies(df[cat_cols], dtype=bool)
        else:
            # 数值列二值化
            df_encoded = (df > df.median()).astype(bool)
        
        # Apriori
        frequent_items = apriori(df_encoded, min_support=min_support, use_colnames=True)
        
        if len(frequent_items) == 0:
            return {
                "rules": [],
                "frequent_itemsets_count": 0,
                "message": f"未找到支持度 >= {min_support} 的频繁项集，请降低 min_support",
            }
        
        # 生成规则
        try:
            rules = ar_func(frequent_items, metric="confidence", min_threshold=min_confidence)
        except Exception as e:
            return {"rules": [], "frequent_itemsets_count": len(frequent_items), "message": str(e)}
        
        # 过滤 lift
        rules = rules[rules["lift"] >= min_lift]
        
        # 排序
        rules = rules.sort_values("lift", ascending=False).head(max_rules)
        
        result_rules = []
        for _, row in rules.iterrows():
            result_rules.append({
                "antecedents": list(row["antecedents"]),
                "consequents": list(row["consequents"]),
                "support": round(float(row["support"]), 4),
                "confidence": round(float(row["confidence"]), 4),
                "lift": round(float(row["lift"]), 4),
            })
        
        return {
            "rules": result_rules,
            "frequent_itemsets_count": len(frequent_items),
            "rules_count": len(result_rules),
            "min_support": min_support,
            "min_confidence": min_confidence,
        }
    
    # ==================== 异常检测 ====================
    
    def anomaly_detection(
        self,
        df: pd.DataFrame,
        columns: List[str] = None,
        contamination: float = 0.05,
        method: str = "isolation_forest",  # isolation_forest / zscore
    ) -> Dict[str, Any]:
        """
        异常检测
        
        Args:
            df: 数据
            columns: 参与检测的数值列
            contamination: 异常比例
            method: 检测方法
        """
        if columns:
            numeric_df = df[columns].select_dtypes(include=[np.number])
        else:
            numeric_df = df.select_dtypes(include=[np.number])
        
        if numeric_df.empty:
            return {"error": "无数值列可用于异常检测"}
        
        # 填充缺失值
        numeric_df = numeric_df.fillna(numeric_df.median())
        
        if method == "isolation_forest":
            iso = IsolationForest(contamination=contamination, random_state=42)
            labels = iso.fit_predict(numeric_df)
            scores = iso.decision_function(numeric_df)
        elif method == "zscore":
            # Z-Score 综合异常
            z_scores = np.abs((numeric_df - numeric_df.mean()) / numeric_df.std())
            max_z = z_scores.max(axis=1)
            labels = np.where(max_z > 3, -1, 1)
            scores = -max_z  # 越小越异常
        else:
            return {"error": f"未知方法: {method}"}
        
        anomaly_mask = labels == -1
        anomaly_indices = np.where(anomaly_mask)[0].tolist()
        
        result = {
            "method": method,
            "total_samples": len(numeric_df),
            "anomaly_count": int(anomaly_mask.sum()),
            "anomaly_pct": round(float(anomaly_mask.sum() / len(numeric_df) * 100), 2),
            "anomaly_indices": anomaly_indices[:100],
            "columns_used": list(numeric_df.columns),
        }
        
        # 异常样本统计
        if anomaly_mask.sum() > 0:
            normal_stats = numeric_df[~anomaly_mask].describe().to_dict()
            anomaly_stats = numeric_df[anomaly_mask].describe().to_dict()
            
            result["comparison"] = {}
            for col in numeric_df.columns:
                result["comparison"][col] = {
                    "normal_mean": round(float(normal_stats[col]["mean"]), 4),
                    "anomaly_mean": round(float(anomaly_stats[col]["mean"]), 4),
                    "diff_pct": round(
                        float((anomaly_stats[col]["mean"] - normal_stats[col]["mean"]) / max(abs(normal_stats[col]["mean"]), 1e-8) * 100),
                        2
                    ),
                }
        
        return result
    
    # ==================== 降维可视化 ====================
    
    def dimensionality_reduction(
        self,
        df: pd.DataFrame,
        columns: List[str] = None,
        method: str = "pca",  # pca / tsne / umap
        n_components: int = 2,
        labels: List = None,
        sample_size: int = 1000,
    ) -> Dict[str, Any]:
        """
        降维可视化
        
        Args:
            df: 数据
            columns: 数值列
            method: 降维方法
            n_components: 目标维度
            labels: 标签 (用于着色)
            sample_size: 采样数量 (t-SNE/UMAP 较慢)
        """
        if columns:
            numeric_df = df[columns].select_dtypes(include=[np.number])
        else:
            numeric_df = df.select_dtypes(include=[np.number])
        
        numeric_df = numeric_df.fillna(numeric_df.median())
        
        if len(numeric_df) > sample_size:
            sample_idx = np.random.choice(len(numeric_df), sample_size, replace=False)
            numeric_df = numeric_df.iloc[sample_idx]
            if labels:
                labels = [labels[i] for i in sample_idx]
        
        if method == "pca":
            reducer = PCA(n_components=n_components)
            embedding = reducer.fit_transform(numeric_df)
            explained_var = reducer.explained_variance_ratio_
        elif method == "tsne":
            reducer = TSNE(n_components=n_components, random_state=42, perplexity=min(30, len(numeric_df) - 1))
            embedding = reducer.fit_transform(numeric_df)
            explained_var = None
        elif method == "umap":
            try:
                import umap
                reducer = umap.UMAP(n_components=n_components, random_state=42)
                embedding = reducer.fit_transform(numeric_df)
                explained_var = None
            except ImportError:
                return {"error": "umap-learn 未安装，请运行: pip install umap-learn"}
        else:
            return {"error": f"未知方法: {method}"}
        
        result = {
            "method": method,
            "n_components": n_components,
            "sample_size": len(numeric_df),
            "points": [],
        }
        
        if explained_var is not None:
            result["explained_variance"] = [round(float(v), 4) for v in explained_var]
            result["total_variance_explained"] = round(float(sum(explained_var)), 4)
        
        for i in range(len(embedding)):
            point = {
                "x": round(float(embedding[i, 0]), 4),
                "y": round(float(embedding[i, 1]), 4) if n_components >= 2 else None,
            }
            if labels and i < len(labels):
                point["label"] = str(labels[i])
            result["points"].append(point)
        
        return result
