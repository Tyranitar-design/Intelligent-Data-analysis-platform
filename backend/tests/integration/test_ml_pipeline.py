# -*- coding: utf-8 -*-
"""ML Pipeline v2 测试"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "."))
import pandas as pd
import numpy as np
from ml.pipeline import MLPipeline

def test_classification():
    print("=" * 50)
    print("Test: ML Pipeline - Classification")
    print("=" * 50)
    
    np.random.seed(42)
    n = 300
    df = pd.DataFrame({
        "feature_1": np.random.normal(0, 1, n),
        "feature_2": np.random.normal(2, 1.5, n),
        "feature_3": np.random.choice(["A", "B", "C"], n),
        "feature_4": np.random.uniform(0, 10, n),
    })
    # 目标变量
    df["target"] = (df["feature_1"] + df["feature_4"] * 0.5 + np.random.normal(0, 1, n) > 3).astype(int)
    
    pipeline = MLPipeline()
    
    # 训练随机森林
    result = pipeline.train(
        df, target_col="target",
        algorithm="random_forest",
        task_type="classification",
        tune=False,
    )
    
    print(f"  Model ID: {result['model_id']}")
    print(f"  Algorithm: {result['algorithm']}")
    print(f"  Task Type: {result['task_type']}")
    print(f"  Data Shape: {result['data_shape']}")
    
    ev = result["evaluation"]
    print(f"  Accuracy: {ev.get('accuracy')}")
    print(f"  F1 Score: {ev.get('f1')}")
    print(f"  Train Accuracy: {ev.get('train_accuracy')}")
    print(f"  CV Mean: {result.get('cv_mean')}")
    
    fi = result["feature_importance"]
    print(f"  Feature Importance: {fi}")
    
    print(f"  Training Time: {result['training_time_seconds']}s")
    
    assert ev.get("accuracy", 0) > 0.5, "Accuracy too low"
    print("  PASS!")

def test_regression():
    print("\n" + "=" * 50)
    print("Test: ML Pipeline - Regression")
    print("=" * 50)
    
    np.random.seed(42)
    n = 200
    df = pd.DataFrame({
        "x1": np.random.uniform(0, 10, n),
        "x2": np.random.normal(5, 2, n),
        "x3": np.random.choice(["A", "B"], n),
    })
    df["y"] = 2 * df["x1"] + 3 * df["x2"] + np.random.normal(0, 2, n)
    
    pipeline = MLPipeline()
    result = pipeline.train(
        df, target_col="y",
        algorithm="xgboost",
        task_type="regression",
        tune=False,
    )
    
    ev = result["evaluation"]
    print(f"  R2: {ev.get('r2')}")
    print(f"  RMSE: {ev.get('rmse')}")
    print(f"  MAE: {ev.get('mae')}")
    
    assert ev.get("r2", 0) > 0.7, "R2 too low"
    print("  PASS!")

def test_clustering():
    print("\n" + "=" * 50)
    print("Test: ML Pipeline - Clustering")
    print("=" * 50)
    
    np.random.seed(42)
    df = pd.DataFrame({
        "x": np.concatenate([np.random.normal(0, 1, 100), np.random.normal(5, 1, 100)]),
        "y": np.concatenate([np.random.normal(0, 1, 100), np.random.normal(5, 1, 100)]),
        "dummy_target": np.zeros(200),  # clustering doesn't use target
    })
    
    pipeline = MLPipeline()
    result = pipeline.train(
        df, target_col="dummy_target",
        algorithm="kmeans",
        task_type="clustering",
    )
    
    ev = result["evaluation"]
    print(f"  N Clusters: {ev.get('n_clusters')}")
    print(f"  Silhouette: {ev.get('silhouette_score')}")
    print("  PASS!")

def test_list_algorithms():
    print("\n" + "=" * 50)
    print("Test: List Algorithms")
    print("=" * 50)
    
    pipeline = MLPipeline()
    algorithms = pipeline.list_algorithms()
    
    for task_type, models in algorithms.items():
        names = [m["name"] for m in models]
        print(f"  {task_type}: {names}")
    
    total = sum(len(v) for v in algorithms.values())
    print(f"  Total: {total} algorithms")
    print("  PASS!")

if __name__ == "__main__":
    test_list_algorithms()
    test_classification()
    test_regression()
    test_clustering()
    print("\nAll ML Pipeline v2 tests passed!")
