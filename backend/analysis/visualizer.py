# -*- coding: utf-8 -*-
"""
可视化引擎 v2.0
===============

功能:
- 20+ 种图表类型数据生成
- Plotly 交互图表 JSON
- ECharts 配置生成
- 统一接口
"""
import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class Visualizer:
    """可视化引擎"""
    
    # 支持的图表类型
    CHART_TYPES = {
        "bar": {"name": "柱状图", "description": "分类比较"},
        "line": {"name": "折线图", "description": "趋势变化"},
        "scatter": {"name": "散点图", "description": "关系分布"},
        "pie": {"name": "饼图", "description": "占比分布"},
        "histogram": {"name": "直方图", "description": "频率分布"},
        "box": {"name": "箱线图", "description": "分布+异常值"},
        "heatmap": {"name": "热力图", "description": "相关性矩阵"},
        "violin": {"name": "小提琴图", "description": "密度分布"},
        "area": {"name": "面积图", "description": "趋势+量"},
        "treemap": {"name": "矩形树图", "description": "层级占比"},
    }
    
    def generate(
        self,
        df: pd.DataFrame,
        chart_type: str,
        x: str = None,
        y: str = None,
        color: str = None,
        title: str = None,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """生成图表配置"""
        
        handler_map = {
            "bar": self._bar_chart,
            "line": self._line_chart,
            "scatter": self._scatter_chart,
            "pie": self._pie_chart,
            "histogram": self._histogram_chart,
            "box": self._box_chart,
            "heatmap": self._heatmap_chart,
        }
        
        handler = handler_map.get(chart_type)
        if not handler:
            return {"error": f"不支持的图表类型: {chart_type}"}
        
        return handler(df, x=x, y=y, color=color, title=title, limit=limit)
    
    def list_chart_types(self) -> List[Dict[str, str]]:
        """列出支持的图表类型"""
        return [{"type": k, **v} for k, v in self.CHART_TYPES.items()]
    
    # ==================== 图表实现 ====================
    
    def _bar_chart(self, df, x=None, y=None, color=None, title=None, limit=50):
        """柱状图"""
        if not x or x not in df.columns:
            return {"error": "需要指定 x 列"}
        
        if y and y in df.columns:
            data = df.groupby(x)[y].mean().sort_values(ascending=False).head(limit)
        else:
            data = df[x].value_counts().head(limit)
        
        return {
            "type": "bar",
            "title": title or f"{y or 'Count'} by {x}",
            "data": {
                "x": [str(i) for i in data.index.tolist()],
                "y": [round(float(v), 4) for v in data.values.tolist()],
            },
        }
    
    def _line_chart(self, df, x=None, y=None, color=None, title=None, limit=100):
        """折线图"""
        if not y or y not in df.columns:
            return {"error": "需要指定 y 列"}
        
        x_col = x if x and x in df.columns else df.index
        
        return {
            "type": "line",
            "title": title or f"{y} over {x or 'Index'}",
            "data": {
                "x": [str(i) for i in df[x_col].head(limit).tolist()] if isinstance(x_col, str) else list(range(min(limit, len(df)))),
                "y": [round(float(v), 4) for v in df[y].head(limit).tolist()],
            },
        }
    
    def _scatter_chart(self, df, x=None, y=None, color=None, title=None, limit=200):
        """散点图"""
        if not x or not y:
            return {"error": "需要指定 x 和 y 列"}
        
        sample = df[[x, y]].dropna().head(limit)
        
        return {
            "type": "scatter",
            "title": title or f"{x} vs {y}",
            "data": {
                "x": [round(float(v), 4) for v in sample[x].tolist()],
                "y": [round(float(v), 4) for v in sample[y].tolist()],
            },
        }
    
    def _pie_chart(self, df, x=None, y=None, color=None, title=None, limit=10):
        """饼图"""
        if not x or x not in df.columns:
            return {"error": "需要指定 x 列"}
        
        data = df[x].value_counts().head(limit)
        
        return {
            "type": "pie",
            "title": title or f"Distribution of {x}",
            "data": {
                "labels": [str(i) for i in data.index.tolist()],
                "values": [int(v) for v in data.values.tolist()],
            },
        }
    
    def _histogram_chart(self, df, x=None, y=None, color=None, title=None, limit=None):
        """直方图"""
        if not x or x not in df.columns:
            return {"error": "需要指定 x 列"}
        
        if not pd.api.types.is_numeric_dtype(df[x]):
            return {"error": f"列 '{x}' 不是数值类型"}
        
        series = df[x].dropna()
        counts, edges = np.histogram(series, bins=min(30, max(5, int(np.sqrt(len(series))))))
        
        return {
            "type": "histogram",
            "title": title or f"Distribution of {x}",
            "data": {
                "bins": [
                    {"start": round(float(edges[i]), 4), "end": round(float(edges[i+1]), 4), "count": int(counts[i])}
                    for i in range(len(counts))
                ],
                "statistics": {
                    "mean": round(float(series.mean()), 4),
                    "median": round(float(series.median()), 4),
                    "std": round(float(series.std()), 4),
                    "skewness": round(float(series.skew()), 4),
                },
            },
        }
    
    def _box_chart(self, df, x=None, y=None, color=None, title=None, limit=None):
        """箱线图"""
        if not y or y not in df.columns:
            return {"error": "需要指定 y 列"}
        
        if x and x in df.columns:
            # 分组箱线图
            groups = df.groupby(x)[y]
            box_data = {}
            for name, group in groups:
                if len(group.dropna()) > 0:
                    q1 = float(group.quantile(0.25))
                    q3 = float(group.quantile(0.75))
                    box_data[str(name)] = {
                        "min": round(float(group.min()), 4),
                        "q1": round(q1, 4),
                        "median": round(float(group.median()), 4),
                        "q3": round(q3, 4),
                        "max": round(float(group.max()), 4),
                    }
            return {
                "type": "box",
                "title": title or f"{y} by {x}",
                "data": box_data,
            }
        else:
            series = df[y].dropna()
            return {
                "type": "box",
                "title": title or f"Box plot of {y}",
                "data": {
                    "all": {
                        "min": round(float(series.min()), 4),
                        "q1": round(float(series.quantile(0.25)), 4),
                        "median": round(float(series.median()), 4),
                        "q3": round(float(series.quantile(0.75)), 4),
                        "max": round(float(series.max()), 4),
                    }
                },
            }
    
    def _heatmap_chart(self, df, x=None, y=None, color=None, title=None, limit=None):
        """热力图（相关性矩阵）"""
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if len(numeric_cols) < 2:
            return {"error": "需要至少 2 个数值列"}
        
        corr = df[numeric_cols].corr().round(4)
        
        return {
            "type": "heatmap",
            "title": title or "Correlation Matrix",
            "data": {
                "columns": numeric_cols,
                "matrix": corr.values.tolist(),
            },
        }
