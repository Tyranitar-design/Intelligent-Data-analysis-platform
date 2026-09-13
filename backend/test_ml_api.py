# -*- coding: utf-8 -*-
"""测试 ML 训练 API"""
import requests
import json

# 1. 加载数据
print("1. 加载数据...")
load_res = requests.post('http://localhost:8000/api/v1/data/load/jd_products_20260424_221820.json')
print(f"   数据条数: {load_res.json().get('total_rows', 0)}")

data = load_res.json().get('data', [])
numeric_cols = load_res.json().get('numeric_columns', [])
print(f"   数值列: {numeric_cols}")

if not numeric_cols or len(data) < 10:
    print("数据不足，跳过训练测试")
    exit()

# 2. 训练回归模型
print("\n2. 训练回归模型...")
train_res = requests.post('http://localhost:8000/api/v1/ml/train/enhanced', json={
    'data': data[:100],  # 只用100条测试
    'model_type': 'regression',
    'algorithm': 'random_forest',
    'features': numeric_cols[:3] if len(numeric_cols) > 3 else numeric_cols,
    'target': numeric_cols[-1] if numeric_cols else None,
    'test_size': 0.2
})

print(f"   状态: {train_res.status_code}")
if train_res.status_code == 200:
    result = train_res.json()
    print(f"   成功: {result.get('success')}")
    print(f"   训练时间: {result.get('training_time')}s")
    print(f"   指标: {result.get('metrics')}")
    print(f"   可视化: {list(result.get('visualizations', {}).keys())}")
else:
    print(f"   错误: {train_res.text[:200]}")

print("\n测试完成!")
