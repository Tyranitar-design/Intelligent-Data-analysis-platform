"""
数据挖掘服务层
- 关联规则挖掘 (Apriori)
- 异常检测 (Isolation Forest)
- 时序模式挖掘
"""
import pandas as pd
import numpy as np
import os
import time
from typing import Dict, Any, List, Optional

from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler


class MiningService:
    """数据挖掘服务"""

    def __init__(self, output_dir: str = None, db_path: str = None):
        if output_dir is None:
            output_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "data", "mining_results"
            )
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

        # 数据库服务
        self._db_service = None
        self._db_path = db_path

    @property
    def db_service(self):
        """懒加载数据库服务"""
        if self._db_service is None:
            try:
                from database.service import DataService
                self._db_service = DataService(self._db_path)
            except Exception:
                pass
        return self._db_service

    def load_from_db(self, source: str = None, platform: str = None,
                     keyword: str = None, limit: int = 1000) -> pd.DataFrame:
        """从数据库加载数据"""
        if self.db_service is None:
            return pd.DataFrame()
        return self.db_service.get_data_for_analysis(
            source=source, platform=platform, keyword=keyword, limit=limit
        )

    def load_ecommerce_for_mining(self, platform: str = None, keywords: List[str] = None,
                                   limit: int = 1000) -> pd.DataFrame:
        """从数据库加载电商数据用于挖掘"""
        if self.db_service is None:
            return pd.DataFrame()
        return self.db_service.get_ecommerce_data(
            platform=platform, keywords=keywords, limit=limit
        )

    def apriori(self, df: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apriori 关联规则挖掘

        Args:
            df: 数据
            config: 配置
                - item_col: 商品列名
                - group_col: 分组列名（如订单ID）
                - min_support: 最小支持度
                - min_confidence: 最小置信度
        """
        start_time = time.time()
        item_col = config.get("item_col", "brand")
        group_col = config.get("group_col", "keyword")
        min_support = config.get("min_support", 0.1)
        min_confidence = config.get("min_confidence", 0.5)

        # 构建事务集
        transactions = df.groupby(group_col)[item_col].apply(set).tolist()

        if not transactions:
            return {"status": "completed", "rules": [], "transaction_count": 0}

        # 计算频繁项集
        n_transactions = len(transactions)
        items = set()
        for t in transactions:
            items.update(t)

        # 1-项集
        freq_1 = {}
        for item in items:
            support = sum(1 for t in transactions if item in t) / n_transactions
            if support >= min_support:
                freq_1[frozenset([item])] = support

        if not freq_1:
            return {
                "status": "completed",
                "transaction_count": n_transactions,
                "frequent_itemsets": [],
                "rules": [],
                "message": "No frequent itemsets found at this support level"
            }

        # 2-项集
        freq_2 = {}
        items_list = list(freq_1.keys())
        for i in range(len(items_list)):
            for j in range(i + 1, len(items_list)):
                pair = items_list[i] | items_list[j]
                support = sum(1 for t in transactions if pair.issubset(t)) / n_transactions
                if support >= min_support:
                    freq_2[pair] = support

        # 生成关联规则
        rules = []
        for itemset, support in {**freq_1, **freq_2}.items():
            if len(itemset) < 2:
                continue
            items_in_set = list(itemset)
            for i in range(len(items_in_set)):
                antecedent = frozenset([items_in_set[i]])
                consequent = itemset - antecedent
                if not consequent:
                    continue

                # 计算置信度
                ant_support = sum(1 for t in transactions if antecedent.issubset(t)) / n_transactions
                if ant_support == 0:
                    continue
                confidence = support / ant_support

                # 计算提升度
                cons_support = sum(1 for t in transactions if consequent.issubset(t)) / n_transactions
                lift = confidence / cons_support if cons_support > 0 else 0

                if confidence >= min_confidence:
                    rules.append({
                        "antecedent": list(antecedent),
                        "consequent": list(consequent),
                        "support": round(support, 4),
                        "confidence": round(confidence, 4),
                        "lift": round(lift, 4),
                    })

        # 排序
        rules.sort(key=lambda x: x["confidence"], reverse=True)

        elapsed = time.time() - start_time
        return {
            "status": "completed",
            "transaction_count": n_transactions,
            "unique_items": len(items),
            "frequent_1_itemsets": len(freq_1),
            "frequent_2_itemsets": len(freq_2),
            "rules_count": len(rules),
            "rules": rules[:20],  # 最多返回20条
            "min_support": min_support,
            "min_confidence": min_confidence,
            "elapsed_time": round(elapsed, 2),
        }

    def isolation_forest(self, df: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Isolation Forest 异常检测

        Args:
            df: 数据
            config: 配置
                - features: 特征列
                - contamination: 异常比例
                - n_estimators: 树的数量
        """
        start_time = time.time()
        features = config.get("features", [])
        contamination = config.get("contamination", 0.1)
        n_estimators = config.get("n_estimators", 100)

        X = df[features].fillna(0)

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        model = IsolationForest(
            contamination=contamination,
            n_estimators=n_estimators,
            random_state=42,
        )
        labels = model.fit_predict(X_scaled)
        scores = model.decision_function(X_scaled)

        # -1 = 异常, 1 = 正常
        anomaly_mask = labels == -1
        n_anomalies = int(anomaly_mask.sum())

        # 异常样本详情
        anomaly_indices = np.where(anomaly_mask)[0].tolist()
        anomaly_scores = scores[anomaly_mask].tolist()

        elapsed = time.time() - start_time
        return {
            "status": "completed",
            "method": "isolation_forest",
            "metrics": {
                "total_samples": len(df),
                "anomaly_count": n_anomalies,
                "anomaly_pct": round(n_anomalies / len(df) * 100, 2),
                "normal_count": len(df) - n_anomalies,
                "contamination": contamination,
                "score_mean": round(float(np.mean(scores)), 4),
                "score_std": round(float(np.std(scores)), 4),
            },
            "anomalies": {
                "indices": anomaly_indices[:50],
                "scores": [round(s, 4) for s in anomaly_scores[:50]],
            },
            "elapsed_time": round(elapsed, 2),
        }

    def time_series_patterns(self, df: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        时序模式挖掘

        Args:
            df: 数据
            config: 配置
                - date_col: 日期列
                - value_col: 数值列
                - window: 滑动窗口大小
        """
        start_time = time.time()
        date_col = config.get("date_col", "date")
        value_col = config.get("value_col", "close")
        window = config.get("window", 5)

        series = df[value_col].astype(float)

        # 滑动平均
        rolling_mean = series.rolling(window=window).mean()
        rolling_std = series.rolling(window=window).std()

        # 变化率
        pct_change = series.pct_change()

        # 趋势判断
        if len(rolling_mean.dropna()) > 1:
            recent_mean = rolling_mean.dropna().iloc[-1]
            earlier_mean = rolling_mean.dropna().iloc[0]
            trend = "up" if recent_mean > earlier_mean else "down"
            trend_pct = round(float((recent_mean - earlier_mean) / earlier_mean * 100), 2) if earlier_mean != 0 else 0
        else:
            trend = "unknown"
            trend_pct = 0

        # 波动性
        volatility = round(float(rolling_std.dropna().mean()), 4) if len(rolling_std.dropna()) > 0 else 0

        # 最大涨幅/跌幅
        max_gain = round(float(pct_change.max()), 4) if len(pct_change.dropna()) > 0 else 0
        max_loss = round(float(pct_change.min()), 4) if len(pct_change.dropna()) > 0 else 0

        elapsed = time.time() - start_time
        return {
            "status": "completed",
            "method": "time_series_patterns",
            "metrics": {
                "data_points": len(df),
                "trend": trend,
                "trend_pct": trend_pct,
                "volatility": volatility,
                "max_gain": max_gain,
                "max_loss": max_loss,
                "mean_value": round(float(series.mean()), 4),
                "std_value": round(float(series.std()), 4),
                "window": window,
            },
            "pattern_summary": {
                "trend_direction": trend,
                "trend_strength": "strong" if abs(trend_pct) > 5 else "weak",
                "volatility_level": "high" if volatility > series.std() else "low",
                "max_single_day_gain": f"{max_gain * 100:.2f}%",
                "max_single_day_loss": f"{max_loss * 100:.2f}%",
            },
            "elapsed_time": round(elapsed, 2),
        }