# -*- coding: utf-8 -*-
"""Phase 3 综合验证测试"""
import sys, os, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "."))
import pandas as pd
import numpy as np

def test_eda():
    from analysis.eda_engine import EDAEngine
    np.random.seed(42)
    df = pd.DataFrame({
        "price": np.random.lognormal(3, 1, 200),
        "category": np.random.choice(["A", "B", "C"], 200),
        "score": np.random.normal(75, 10, 200),
    })
    df.loc[np.random.choice(200, 15), "price"] = np.nan
    
    engine = EDAEngine()
    result = engine.analyze(df, "test")
    dq = result["data_quality"]
    print(f"[EDA] Quality: {dq['overall_score']} ({dq['grade']}) | Suggestions: {len(result['suggestions'])}")
    return True

def test_ml():
    from ml.pipeline import MLPipeline
    np.random.seed(42)
    df = pd.DataFrame({
        "x1": np.random.normal(0, 1, 200),
        "x2": np.random.normal(2, 1, 200),
        "cat": np.random.choice(["A", "B"], 200),
    })
    df["y"] = (df["x1"] + df["x2"] > 1).astype(int)
    
    pipeline = MLPipeline()
    result = pipeline.train(df, "y", "random_forest", "classification")
    ev = result["evaluation"]
    print(f"[ML] Accuracy: {ev.get('accuracy')} | F1: {ev.get('f1')} | CV: {result.get('cv_mean')}")
    return True

def test_dl_nlp():
    from dl.pipeline import DLPipeline
    dl = DLPipeline()
    
    # 情感分析
    texts = ["这个产品很好用", "太差了完全不行", "还行吧一般般", "非常满意推荐给大家", "垃圾产品退货"]
    result = dl.sentiment_analysis(texts)
    print(f"[DL/NLP] Sentiment: pos={result['positive']}, neg={result['negative']}, neutral={result['neutral']}")
    
    # 关键词提取
    texts_kw = ["数据分析平台", "机器学习算法", "深度学习模型", "数据可视化工具", "自然语言处理"]
    result = dl.extract_keywords(texts_kw)
    print(f"[DL/NLP] Keywords: {len(result.get('keywords', []))} extracted")
    return True

def test_mining():
    from mining.pipeline import MiningPipeline
    
    np.random.seed(42)
    # 异常检测
    df = pd.DataFrame({
        "value": np.concatenate([np.random.normal(0, 1, 190), np.random.normal(10, 1, 10)]),
        "feature": np.random.normal(5, 2, 200),
    })
    
    pipeline = MiningPipeline()
    result = pipeline.anomaly_detection(df, method="isolation_forest", contamination=0.05)
    print(f"[Mining] Anomalies: {result['anomaly_count']}/{result['total_samples']} ({result['anomaly_pct']}%)")
    
    # PCA 降维
    result = pipeline.dimensionality_reduction(df, method="pca", n_components=2)
    print(f"[Mining] PCA: {result['sample_size']} points, variance={result.get('total_variance_explained')}")
    return True

def test_report():
    from analysis.eda_engine import EDAEngine
    from analysis.report_engine import ReportEngine
    
    np.random.seed(42)
    df = pd.DataFrame({"x": np.random.normal(0, 1, 100), "y": np.random.choice(["A", "B"], 100)})
    
    eda_engine = EDAEngine()
    eda_result = eda_engine.analyze(df, "test_report")
    
    report_engine = ReportEngine()
    md_report = report_engine.generate_eda_report(eda_result, "test_report", "markdown")
    html_report = report_engine.generate_eda_report(eda_result, "test_report", "html")
    
    print(f"[Report] Markdown: {len(md_report)} chars | HTML: {len(html_report)} chars")
    return len(md_report) > 100 and len(html_report) > 100

def test_feature_engine():
    from analysis.feature_engine import FeatureEngine
    np.random.seed(42)
    df = pd.DataFrame({
        "x1": np.random.normal(0, 1, 100),
        "cat": np.random.choice(["A", "B", "C"], 100),
        "y": np.random.choice([0, 1], 100),
    })
    df.loc[0:5, "x1"] = np.nan
    
    engine = FeatureEngine()
    df_out, report = engine.engineer(df, "y", "classification")
    print(f"[Feature] Shape: {report['original_shape']} -> {report['final_shape']}, Steps: {len(report['steps'])}")
    return True

def main():
    print("Phase 3 综合验证\n")
    
    tests = [
        ("EDA Engine v2", test_eda),
        ("Feature Engine", test_feature_engine),
        ("ML Pipeline v2", test_ml),
        ("DL/NLP Pipeline", test_dl_nlp),
        ("Mining Pipeline", test_mining),
        ("Report Engine", test_report),
    ]
    
    all_pass = True
    for name, test_fn in tests:
        try:
            passed = test_fn()
            status = "PASS" if passed else "FAIL"
            print(f"  {status} | {name}\n")
            if not passed:
                all_pass = False
        except Exception as e:
            print(f"  FAIL | {name}: {e}\n")
            all_pass = False
    
    if all_pass:
        print("Phase 3 All tests passed!")
    else:
        print("Some tests failed")

if __name__ == "__main__":
    main()
