"""
数据分析服务层
- EDA 探索性数据分析
- 统计分析
- 数据可视化
- 支持从数据库读取数据
"""
import pandas as pd
import numpy as np
import json
import os
from typing import Dict, Any, List, Optional


class AnalysisService:
    """数据分析服务"""

    def __init__(self, data_dir: str = None, db_path: str = None):
        if data_dir is None:
            data_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "data", "raw"
            )
        self.data_dir = data_dir

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
        """从数据库加载数据

        Args:
            source: 数据源 (jd, taobao, stock, etc.)
            platform: 平台
            keyword: 关键词
            limit: 数量限制

        Returns:
            DataFrame
        """
        if self.db_service is None:
            return pd.DataFrame()

        return self.db_service.get_data_for_analysis(
            source=source,
            platform=platform,
            keyword=keyword,
            limit=limit
        )

    def load_ecommerce_data(self, platform: str = None, keywords: List[str] = None,
                            min_price: float = None, max_price: float = None,
                            brands: List[str] = None, limit: int = 1000) -> pd.DataFrame:
        """从数据库加载电商数据"""
        if self.db_service is None:
            return pd.DataFrame()

        return self.db_service.get_ecommerce_data(
            platform=platform,
            keywords=keywords,
            min_price=min_price,
            max_price=max_price,
            brands=brands,
            limit=limit
        )

    def load_data(self, filepath: str) -> pd.DataFrame:
        """加载数据文件"""
        if filepath.endswith(".json"):
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            return pd.DataFrame(data)
        elif filepath.endswith(".csv"):
            return pd.read_csv(filepath, encoding="utf-8")
        else:
            raise ValueError(f"Unsupported file format: {filepath}")

    def get_latest_file(self, source_type: str) -> Optional[str]:
        """获取最新的数据文件"""
        files = [f for f in os.listdir(self.data_dir) if f.startswith(source_type)]
        if not files:
            return None
        files.sort(reverse=True)
        return os.path.join(self.data_dir, files[0])

    def eda(self, df: pd.DataFrame) -> Dict[str, Any]:
        """探索性数据分析"""
        result = {
            "overview": {
                "row_count": len(df),
                "column_count": len(df.columns),
                "columns": list(df.columns),
                "dtypes": {col: str(df[col].dtype) for col in df.columns},
                "missing_values": int(df.isnull().sum().sum()),
                "missing_pct": round(df.isnull().sum().sum() / (len(df) * len(df.columns)) * 100, 2),
                "duplicate_rows": int(df.drop(columns=[col for col in df.columns if df[col].apply(type).eq(list).any()], errors='ignore').duplicated().sum()),
                "memory_mb": round(df.memory_usage(deep=True).sum() / 1024 / 1024, 2),
            },
            "numeric_summary": {},
            "categorical_summary": {},
            "correlation": {},
        }

        # 数值列统计
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if numeric_cols:
            desc = df[numeric_cols].describe().to_dict()
            result["numeric_summary"] = {
                col: {
                    "count": int(desc[col]["count"]),
                    "mean": round(float(desc[col]["mean"]), 4),
                    "std": round(float(desc[col]["std"]), 4),
                    "min": round(float(desc[col]["min"]), 4),
                    "25%": round(float(desc[col]["25%"]), 4),
                    "50%": round(float(desc[col]["50%"]), 4),
                    "75%": round(float(desc[col]["75%"]), 4),
                    "max": round(float(desc[col]["max"]), 4),
                }
                for col in numeric_cols
            }

            # 相关系数
            if len(numeric_cols) > 1:
                corr = df[numeric_cols].corr().round(4).to_dict()
                result["correlation"] = corr

        # 分类列统计（排除列表类型的列）
        cat_cols = df.select_dtypes(include=["object"]).columns.tolist()
        if cat_cols:
            for col in cat_cols:
                try:
                    # 跳过包含列表的列
                    sample = df[col].dropna().iloc[0] if len(df[col].dropna()) > 0 else None
                    if isinstance(sample, (list, dict)):
                        continue
                    result["categorical_summary"][col] = {
                        "unique_count": int(df[col].nunique()),
                        "top_values": df[col].value_counts().head(5).to_dict(),
                        "missing_count": int(df[col].isnull().sum()),
                    }
                except Exception:
                    continue

        return result

    def statistics(self, df: pd.DataFrame, columns: List[str] = None) -> Dict[str, Any]:
        """统计分析"""
        if columns:
            df = df[columns]

        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        result = {
            "descriptive": {},
            "distribution": {},
            "outliers": {},
        }

        for col in numeric_cols:
            series = df[col].dropna()

            # 描述性统计
            result["descriptive"][col] = {
                "mean": round(float(series.mean()), 4),
                "median": round(float(series.median()), 4),
                "mode": round(float(series.mode().iloc[0]), 4) if len(series.mode()) > 0 else None,
                "std": round(float(series.std()), 4),
                "var": round(float(series.var()), 4),
                "skewness": round(float(series.skew()), 4),
                "kurtosis": round(float(series.kurtosis()), 4),
            }

            # 分布信息
            result["distribution"][col] = {
                "histogram_bins": self._compute_histogram(series),
                "quantiles": {
                    "1%": round(float(series.quantile(0.01)), 4),
                    "5%": round(float(series.quantile(0.05)), 4),
                    "25%": round(float(series.quantile(0.25)), 4),
                    "50%": round(float(series.quantile(0.50)), 4),
                    "75%": round(float(series.quantile(0.75)), 4),
                    "95%": round(float(series.quantile(0.95)), 4),
                    "99%": round(float(series.quantile(0.99)), 4),
                }
            }

            # 异常值检测 (IQR 方法)
            Q1 = series.quantile(0.25)
            Q3 = series.quantile(0.75)
            IQR = Q3 - Q1
            lower = Q1 - 1.5 * IQR
            upper = Q3 + 1.5 * IQR
            outliers = series[(series < lower) | (series > upper)]
            result["outliers"][col] = {
                "count": int(len(outliers)),
                "pct": round(len(outliers) / len(series) * 100, 2),
                "lower_bound": round(float(lower), 4),
                "upper_bound": round(float(upper), 4),
            }

        return result

    def _compute_histogram(self, series: pd.Series, bins: int = 10) -> List[Dict]:
        """计算直方图数据"""
        counts, edges = np.histogram(series.dropna(), bins=bins)
        result = []
        for i in range(len(counts)):
            result.append({
                "bin_start": round(float(edges[i]), 4),
                "bin_end": round(float(edges[i + 1]), 4),
                "count": int(counts[i]),
            })
        return result

    def generate_chart_data(self, df: pd.DataFrame, chart_type: str, x: str, y: str = None) -> Dict[str, Any]:
        """生成图表数据"""
        if chart_type == "bar":
            if y and y in df.columns:
                data = df.groupby(x)[y].mean().sort_values(ascending=False).head(20)
                return {
                    "type": "bar",
                    "x": data.index.tolist(),
                    "y": [round(float(v), 2) for v in data.values],
                    "title": f"{y} by {x}",
                }
            else:
                data = df[x].value_counts().head(20)
                return {
                    "type": "bar",
                    "x": data.index.tolist(),
                    "y": data.values.tolist(),
                    "title": f"Count by {x}",
                }

        elif chart_type == "scatter":
            if y and x in df.columns and y in df.select_dtypes(include=[np.number]).columns:
                return {
                    "type": "scatter",
                    "x": df[x].head(100).tolist(),
                    "y": df[y].head(100).tolist(),
                    "title": f"{x} vs {y}",
                }

        elif chart_type == "line":
            if y:
                return {
                    "type": "line",
                    "x": df[x].head(50).tolist() if x in df.columns else list(range(len(df))),
                    "y": df[y].head(50).tolist(),
                    "title": f"{y} over {x}",
                }

        elif chart_type == "pie":
            data = df[x].value_counts().head(10)
            return {
                "type": "pie",
                "labels": data.index.tolist(),
                "values": data.values.tolist(),
                "title": f"Distribution of {x}",
            }

        return {"type": chart_type, "title": "Chart", "data": {}}