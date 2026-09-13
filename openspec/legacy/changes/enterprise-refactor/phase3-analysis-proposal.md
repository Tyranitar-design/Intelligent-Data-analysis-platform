# Proposal: Phase 3 — 分析系统核心

> 状态: 待批准 | 日期: 2026-05-08
> 方法: SDD v2.1 sdd-propose | 作者: 小彩

---

## 1. 变更意图

构建**端到端数据分析 Pipeline**，从原始数据到洞察报告，支持 EDA / ML / DL / 数据挖掘全链路。

**这是平台的核心价值所在**——采集的数据只有经过分析才能产生洞察和决策价值。

## 2. 当前基线

| 组件 | 已有 (v1) | 缺失/需增强 |
|------|-----------|-------------|
| EDA | ✅ 基础统计描述、相关性、异常值 | ❌ 缺失值可视化建议、自动报告 |
| 统计 | ✅ 描述性统计、分位数、偏度峰度 | ❌ 假设检验、显著性分析 |
| 可视化 | ⚠️ 基础4种图表数据生成 | ❌ 无 Plotly/ECharts 交互图表、无仪表盘 |
| ML | ✅ 分类/回归/聚类 + XGBoost/LightGBM | ❌ 无超参调优、无交叉验证报告、无特征工程 |
| DL | ❌ 无 | ❌ 完全缺失 |
| 数据挖掘 | ❌ 无 | ❌ 完全缺失 |
| 报告 | ❌ 无 | ❌ 无自动报告生成 |

## 3. 变更范围 (5 个 Task)

### Task 3.1: EDA 增强引擎
- 完善探索性分析（缺失值分析+处理建议、分布可视化、异常值检测增强）
- 自动数据画像（数据质量评分、字段类型推断增强）
- 自动生成 EDA 报告

### Task 3.2: ML Pipeline v2
- 特征工程引擎（标准化/归一化/编码/特征选择/特征交叉）
- 超参调优（GridSearchCV / RandomizedSearchCV / Optuna Bayesian）
- 交叉验证 + 学习曲线
- 模型评估报告（混淆矩阵、ROC-AUC、特征重要性、SHAP 值）
- 模型版本管理 + 持久化

### Task 3.3: DL Pipeline
- PyTorch 时序预测（LSTM / GRU / Transformer）
- NLP 文本分析（情感分析 / 文本分类 / 关键词提取）
- Prophet 时序预测
- GPU 支持

### Task 3.4: 数据挖掘
- 关联规则（Apriori / FP-Growth）
- 异常检测（Isolation Forest / Autoencoder）
- 降维可视化（PCA / t-SNE / UMAP）

### Task 3.5: 分析报告引擎
- 自动分析报告生成（EDA + 模型结果 → Markdown/HTML）
- 图表嵌入（Plotly 静态图片 / ECharts）
- PDF/Word 导出
- 报告模板系统

## 4. 技术方案

```
backend/
├── analysis/
│   ├── service.py              # 增强 v2
│   ├── eda_engine.py           # 新增: EDA 引擎
│   ├── feature_engine.py       # 新增: 特征工程
│   ├── report_engine.py        # 新增: 报告生成
│   └── visualizer.py           # 新增: 可视化引擎
├── ml/
│   ├── service.py              # 增强 v2
│   ├── pipeline.py             # 新增: ML Pipeline
│   ├── evaluation.py           # 新增: 模型评估
│   ├── tuning.py               # 新增: 超参调优
│   └── models/                 # 新增: 模型存储
├── dl/
│   ├── service.py              # 增强 v2
│   ├── timeseries/             # 新增: 时序预测
│   │   ├── lstm.py
│   │   ├── prophet_model.py
│   │   └── transformer_ts.py
│   └── nlp/                    # 新增: NLP
│       ├── sentiment.py
│       └── keywords.py
├── mining/
│   ├── service.py              # 增强 v2
│   ├── association.py          # 新增: 关联规则
│   ├── anomaly.py              # 新增: 异常检测
│   └── reduction.py            # 新增: 降维可视化
├── api/
│   └── routers/
│       ├── analysis.py         # 增强: EDA + 报告
│       ├── ml.py               # 增强: Pipeline + 调优
│       ├── dl.py                # 增强: 时序 + NLP
│       └── mining.py           # 增强: 关联 + 异常 + 降维
└── api/tasks/
    └── analysis_tasks.py       # 增强: Celery 异步分析
```

## 5. 核心依赖（已有）

| 包 | 版本 | 用途 |
|----|------|------|
| scikit-learn | 1.8.0 | ML 核心 |
| XGBoost | 3.2.0 | 梯度提升 |
| LightGBM | 4.6.0 | 梯度提升 |
| PyTorch | ✅ | DL 核心 |
| Pandas | 3.0.2 | 数据处理 |
| NumPy | 2.4.4 | 数值计算 |
| SciPy | 1.17.1 | 统计检验 |

## 6. 需新增依赖

| 包 | 用途 | 大小 |
|----|------|------|
| optuna | Bayesian 超参调优 | ~5MB |
| shap | 模型解释性 | ~15MB |
| mlxtend | 关联规则(Apriori/FP-Growth) | ✅ 已有 |
| prophet | 时序预测 | ~50MB |
| umap-learn | UMAP 降维 | ~10MB |
| jinja2 | 报告模板 | ✅ 已有 |
| weasyprint/pdfkit | PDF 导出 | ~30MB |

## 7. 预计工期

| Task | 预计时间 | 优先级 |
|------|----------|--------|
| 3.1 EDA 增强引擎 | 40 min | P0 |
| 3.2 ML Pipeline v2 | 60 min | P0 |
| 3.3 DL Pipeline | 50 min | P1 |
| 3.4 数据挖掘 | 35 min | P1 |
| 3.5 分析报告引擎 | 40 min | P1 |

**总计**: ~3.5 小时，建议今晚完成 3.1+3.2，明天继续 3.3-3.5

---

*Proposal | 2026-05-08 | 小彩*
