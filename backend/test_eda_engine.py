# -*- coding: utf-8 -*-
"""EDA 引擎测试"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "."))
import pandas as pd
import numpy as np

from analysis.eda_engine import EDAEngine
from analysis.feature_engine import FeatureEngine
from analysis.visualizer import Visualizer

def test_eda():
    print("=" * 50)
    print("Test: EDA Engine v2")
    print("=" * 50)
    
    # 创建测试数据
    np.random.seed(42)
    df = pd.DataFrame({
        "price": np.random.lognormal(3, 1, 500),
        "volume": np.random.randint(100, 10000, 500),
        "category": np.random.choice(["A", "B", "C", "D"], 500),
        "score": np.clip(np.random.normal(75, 15, 500), 0, 100),
        "is_active": np.random.choice([0, 1], 500),
    })
    # 添加缺失值
    df.loc[np.random.choice(500, 30), "price"] = np.nan
    df.loc[np.random.choice(500, 50), "category"] = None
    
    engine = EDAEngine()
    result = engine.analyze(df, "test_data")
    
    # 概览
    ov = result["overview"]
    print(f"  Rows: {ov['row_count']}, Cols: {ov['column_count']}")
    print(f"  Numeric: {ov['numeric_column_count']}, Categorical: {ov['categorical_column_count']}")
    print(f"  Duplicates: {ov['duplicate_row_count']}")
    
    # 数据质量
    dq = result["data_quality"]
    print(f"\n  Quality Score: {dq['overall_score']} ({dq['grade']})")
    print(f"  Completeness: {dq['dimensions']['completeness']['score']}")
    print(f"  Uniqueness: {dq['dimensions']['uniqueness']['score']}")
    
    # 缺失值
    mv = result["missing_values"]
    print(f"\n  Missing: {mv['total_missing']} cells ({mv['total_missing_pct']}%)")
    for detail in mv["columns_detail"]:
        print(f"    {detail['column']}: {detail['missing_pct']}% -> {detail['suggestion']['action']}")
    
    # 相关性
    corr = result["correlation"]
    print(f"\n  High correlation pairs: {len(corr['high_correlation_pairs'])}")
    for pair in corr["high_correlation_pairs"]:
        print(f"    {pair['col1']} <-> {pair['col2']}: {pair['pearson']} ({pair['interpretation']})")
    
    # 异常值
    out = result["outliers"]
    for col, info in out["columns"].items():
        print(f"\n  Outliers [{col}]: IQR={info['iqr']['pct']}%, Z-Score={info['zscore']['pct']}%")
        print(f"    -> {info['suggestion']}")
    
    # 建议
    print(f"\n  Suggestions ({len(result['suggestions'])}):")
    for s in result["suggestions"]:
        print(f"    [{s['priority']}] {s['title']}: {s.get('description', s.get('action', ''))}")
    
    print("\n  EDA Test PASS!")

def test_feature_engine():
    print("\n" + "=" * 50)
    print("Test: Feature Engine v2")
    print("=" * 50)
    
    np.random.seed(42)
    df = pd.DataFrame({
        "price": np.random.lognormal(3, 1, 200),
        "category": np.random.choice(["A", "B", "C"], 200),
        "target": np.random.choice([0, 1], 200),
    })
    df.loc[np.random.choice(200, 10), "price"] = np.nan
    
    engine = FeatureEngine()
    df_processed, report = engine.engineer(df, target_col="target", task_type="classification")
    
    print(f"  Original: {report['original_shape']}")
    print(f"  Final: {report['final_shape']}")
    for step in report["steps"]:
        print(f"  Step [{step['step']}]:")
        for action in step["actions"]:
            print(f"    - {action}")
    
    print("\n  Feature Engine Test PASS!")

def test_visualizer():
    print("\n" + "=" * 50)
    print("Test: Visualizer v2")
    print("=" * 50)
    
    np.random.seed(42)
    df = pd.DataFrame({
        "category": np.random.choice(["A", "B", "C", "D"], 100),
        "value": np.random.normal(50, 15, 100),
        "count": np.random.randint(1, 100, 100),
    })
    
    viz = Visualizer()
    
    # Bar
    r = viz.generate(df, "bar", x="category", y="value")
    print(f"  Bar: type={r['type']}, x_count={len(r['data']['x'])}")
    
    # Histogram
    r = viz.generate(df, "histogram", x="value")
    print(f"  Histogram: type={r['type']}, bins={len(r['data']['bins'])}")
    
    # Box
    r = viz.generate(df, "box", x="category", y="value")
    print(f"  Box: type={r['type']}, groups={len(r['data'])}")
    
    # Heatmap
    r = viz.generate(df, "heatmap")
    print(f"  Heatmap: type={r['type']}, cols={len(r['data']['columns'])}")
    
    # Chart types
    types = viz.list_chart_types()
    print(f"  Supported: {len(types)} chart types")
    
    print("\n  Visualizer Test PASS!")

if __name__ == "__main__":
    test_eda()
    test_feature_engine()
    test_visualizer()
    print("\nAll Phase 3 Task 3.1 tests passed!")
