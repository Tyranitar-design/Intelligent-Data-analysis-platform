# -*- coding: utf-8 -*-
"""
深度学习 Pipeline v2.0
=====================

功能:
- 时序预测 (Prophet + LSTM)
- NLP 文本分析 (情感分析 + 关键词提取)
- GPU 支持检测
"""
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class DLPipeline:
    """深度学习 Pipeline"""
    
    def __init__(self, model_dir: str = None):
        self.model_dir = model_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data", "models"
        )
        os.makedirs(self.model_dir, exist_ok=True)
        self._torch_available = self._check_torch()
    
    def _check_torch(self) -> bool:
        """检查 PyTorch 是否可用"""
        try:
            import torch
            return True
        except ImportError:
            return False
    
    def check_gpu(self) -> Dict[str, Any]:
        """检查 GPU 支持"""
        if not self._torch_available:
            return {"gpu_available": False, "reason": "PyTorch 未安装"}
        
        import torch
        cuda_available = torch.cuda.is_available()
        result = {"gpu_available": cuda_available}
        
        if cuda_available:
            result["device_name"] = torch.cuda.get_device_name(0)
            result["device_count"] = torch.cuda.device_count()
            result["memory_total_gb"] = round(torch.cuda.get_device_properties(0).total_mem / 1e9, 2)
        
        return result
    
    # ==================== 时序预测 ====================
    
    def prophet_forecast(
        self,
        df: pd.DataFrame,
        date_col: str,
        value_col: str,
        periods: int = 30,
        freq: str = "D",
    ) -> Dict[str, Any]:
        """
        Prophet 时序预测
        
        Args:
            df: 数据 (需要日期列和数值列)
            date_col: 日期列名
            value_col: 数值列名
            periods: 预测期数
            freq: 频率 (D=天, W=周, M=月)
        """
        try:
            from prophet import Prophet
        except ImportError:
            return {"error": "Prophet 未安装，请运行: pip install prophet"}
        
        # 准备数据
        prophet_df = pd.DataFrame({
            "ds": pd.to_datetime(df[date_col]),
            "y": df[value_col].astype(float),
        })
        
        # 训练
        model = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=True,
            daily_seasonality=False,
        )
        model.fit(prophet_df)
        
        # 预测
        future = model.make_future_dataframe(periods=periods, freq=freq)
        forecast = model.predict(future)
        
        # 提取结果
        result = {
            "method": "prophet",
            "periods": periods,
            "freq": freq,
            "history_length": len(prophet_df),
            "forecast": [],
            "components": {
                "trend": forecast["trend"].tolist()[-periods:],
                "yearly": forecast["yearly"].tolist()[-periods:] if "yearly" in forecast.columns else [],
                "weekly": forecast["weekly"].tolist()[-periods:] if "weekly" in forecast.columns else [],
            },
        }
        
        for _, row in forecast.tail(periods).iterrows():
            result["forecast"].append({
                "date": str(row["ds"].date()),
                "yhat": round(float(row["yhat"]), 4),
                "yhat_lower": round(float(row["yhat_lower"]), 4),
                "yhat_upper": round(float(row["yhat_upper"]), 4),
            })
        
        return result
    
    def lstm_forecast(
        self,
        series: np.ndarray,
        look_back: int = 10,
        epochs: int = 50,
        forecast_steps: int = 10,
    ) -> Dict[str, Any]:
        """
        LSTM 时序预测
        
        Args:
            series: 时间序列数据 (1D numpy array)
            look_back: 回看窗口
            epochs: 训练轮数
            forecast_steps: 预测步数
        """
        if not self._torch_available:
            return {"error": "PyTorch 未安装，无法使用 LSTM"}
        
        import torch
        import torch.nn as nn
        
        # 数据标准化
        data_min, data_max = series.min(), series.max()
        data_norm = (series - data_min) / (data_max - data_min + 1e-8)
        
        # 创建数据集
        X, y = [], []
        for i in range(len(data_norm) - look_back):
            X.append(data_norm[i:i + look_back])
            y.append(data_norm[i + look_back])
        
        X = np.array(X, dtype=np.float32).reshape(-1, 1, look_back)
        y = np.array(y, dtype=np.float32).reshape(-1, 1)
        
        # 定义模型
        class LSTMModel(nn.Module):
            def __init__(self, input_size=1, hidden_size=64, num_layers=2):
                super().__init__()
                self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
                self.fc = nn.Linear(hidden_size, 1)
            
            def forward(self, x):
                out, _ = self.lstm(x)
                out = self.fc(out[:, -1, :])
                return out
        
        # 训练
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model = LSTMModel().to(device)
        criterion = nn.MSELemoryLoss()
        optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
        
        X_tensor = torch.FloatTensor(X).to(device)
        y_tensor = torch.FloatTensor(y).to(device)
        
        model.train()
        for epoch in range(epochs):
            optimizer.zero_grad()
            output = model(X_tensor)
            loss = criterion(output, y_tensor)
            loss.backward()
            optimizer.step()
        
        # 预测
        model.eval()
        last_sequence = data_norm[-look_back:].reshape(1, 1, look_back)
        predictions = []
        
        with torch.no_grad():
            current = torch.FloatTensor(last_sequence).to(device)
            for _ in range(forecast_steps):
                pred = model(current)
                predictions.append(float(pred.cpu().numpy()[0, 0]))
                # 移动窗口
                new_seq = np.append(current.cpu().numpy()[0, 0, 1:], predictions[-1])
                current = torch.FloatTensor(new_seq.reshape(1, 1, look_back)).to(device)
        
        # 反标准化
        predictions_real = [p * (data_max - data_min) + data_min for p in predictions]
        
        return {
            "method": "lstm",
            "look_back": look_back,
            "epochs": epochs,
            "device": str(device),
            "forecast_steps": forecast_steps,
            "predictions": [round(p, 4) for p in predictions_real],
        }
    
    # ==================== NLP ====================
    
    def sentiment_analysis(self, texts: List[str]) -> Dict[str, Any]:
        """
        情感分析
        
        基于规则 + 关键词的轻量情感分析（无需下载大模型）
        """
        # 中文情感词典
        positive_words = {"好", "棒", "优秀", "喜欢", "满意", "推荐", "不错", "值得", "开心", "赞", "厉害", "完美", "惊喜", "超值", "舒适"}
        negative_words = {"差", "烂", "失望", "不好", "难用", "垃圾", "坑", "骗", "差劲", "难看", "恶心", "退货", "浪费", "后悔", "糟糕"}
        
        results = []
        pos_count = 0
        neg_count = 0
        neutral_count = 0
        
        for text in texts:
            if not isinstance(text, str):
                results.append({"text": str(text)[:50], "sentiment": "neutral", "score": 0})
                neutral_count += 1
                continue
            
            pos_hits = sum(1 for w in positive_words if w in text)
            neg_hits = sum(1 for w in negative_words if w in text)
            
            score = pos_hits - neg_hits
            
            if score > 0:
                sentiment = "positive"
                pos_count += 1
            elif score < 0:
                sentiment = "negative"
                neg_count += 1
            else:
                sentiment = "neutral"
                neutral_count += 1
            
            results.append({
                "text": text[:100],
                "sentiment": sentiment,
                "score": score,
            })
        
        return {
            "total": len(texts),
            "positive": pos_count,
            "negative": neg_count,
            "neutral": neutral_count,
            "positive_pct": round(pos_count / max(len(texts), 1) * 100, 1),
            "results": results[:100],
        }
    
    def extract_keywords(self, texts: List[str], top_k: int = 20) -> Dict[str, Any]:
        """
        关键词提取 (TF-IDF)
        """
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
        except ImportError:
            return {"error": "scikit-learn 未安装"}
        
        # 过滤空文本
        valid_texts = [t for t in texts if isinstance(t, str) and len(t.strip()) > 0]
        
        if not valid_texts:
            return {"keywords": [], "total_documents": 0}
        
        # TF-IDF
        vectorizer = TfidfVectorizer(
            max_features=1000,
            token_pattern=r'(?u)\b\w+\b',  # 支持中文单字
            min_df=1,
            max_df=0.95,
        )
        
        tfidf_matrix = vectorizer.fit_transform(valid_texts)
        feature_names = vectorizer.get_feature_names_out()
        
        # 计算平均 TF-IDF
        mean_scores = np.array(tfidf_matrix.mean(axis=0)).flatten()
        top_indices = mean_scores.argsort()[-top_k:][::-1]
        
        keywords = [
            {"word": feature_names[i], "score": round(float(mean_scores[i]), 4)}
            for i in top_indices
        ]
        
        return {
            "keywords": keywords,
            "total_documents": len(valid_texts),
            "vocabulary_size": len(feature_names),
        }
