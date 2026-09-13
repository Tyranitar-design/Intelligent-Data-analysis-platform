"""
深度学习服务层
- LSTM 时间序列预测
- 简单神经网络分类
- Autoencoder 异常检测
"""
import pandas as pd
import numpy as np
import os
import time
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset


# ==================== 模型定义 ====================

class LSTMForecaster(nn.Module):
    """LSTM 时间序列预测模型"""

    def __init__(self, input_size=1, hidden_size=64, num_layers=2, output_size=1, dropout=0.2):
        super().__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers,
                            batch_first=True, dropout=dropout)
        self.fc = nn.Linear(hidden_size, output_size)

    def forward(self, x):
        # x: (batch, seq_len, input_size)
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size)
        c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size)
        out, _ = self.lstm(x, (h0, c0))
        out = self.fc(out[:, -1, :])  # 取最后一个时间步
        return out


class SimpleClassifier(nn.Module):
    """简单全连接分类网络"""

    def __init__(self, input_size, hidden_sizes=[128, 64], num_classes=2, dropout=0.3):
        super().__init__()
        layers = []
        prev_size = input_size
        for h in hidden_sizes:
            layers.extend([
                nn.Linear(prev_size, h),
                nn.ReLU(),
                nn.Dropout(dropout),
            ])
            prev_size = h
        layers.append(nn.Linear(prev_size, num_classes))
        self.network = nn.Sequential(*layers)

    def forward(self, x):
        return self.network(x)


class Autoencoder(nn.Module):
    """自编码器异常检测"""

    def __init__(self, input_size, encoding_dim=8):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_size, 64),
            nn.ReLU(),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, encoding_dim),
        )
        self.decoder = nn.Sequential(
            nn.Linear(encoding_dim, 32),
            nn.ReLU(),
            nn.Linear(32, 64),
            nn.ReLU(),
            nn.Linear(64, input_size),
        )

    def forward(self, x):
        encoded = self.encoder(x)
        decoded = self.decoder(encoded)
        return decoded


# ==================== 服务类 ====================

class DLService:
    """深度学习服务"""

    def __init__(self, model_dir: str = None, db_path: str = None):
        if model_dir is None:
            model_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "data", "dl_models"
            )
        self.model_dir = model_dir
        os.makedirs(model_dir, exist_ok=True)
        self.device = torch.device("cpu")

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

    def load_ecommerce_for_dl(self, platform: str = None, keywords: List[str] = None,
                              limit: int = 1000) -> pd.DataFrame:
        """从数据库加载电商数据用于深度学习"""
        if self.db_service is None:
            return pd.DataFrame()
        return self.db_service.get_ecommerce_data(
            platform=platform, keywords=keywords, limit=limit
        )

    def load_stock_for_dl(self, symbols: List[str] = None,
                           start_date: str = None, end_date: str = None,
                           limit: int = 5000) -> pd.DataFrame:
        """从数据库加载股票数据用于深度学习"""
        if self.db_service is None:
            return pd.DataFrame()
        return self.db_service.get_stock_data_for_ml(
            symbols=symbols, start_date=start_date, end_date=end_date, limit=limit
        )

    def train_lstm(self, df: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        训练 LSTM 时间序列预测模型

        Args:
            df: 数据
            config: 配置
                - target_col: 目标列
                - seq_length: 序列长度
                - epochs: 训练轮数
                - lr: 学习率
                - hidden_size: 隐藏层大小
        """
        start_time = time.time()
        target_col = config.get("target_col", "close")
        seq_length = config.get("seq_length", 5)
        epochs = config.get("epochs", 50)
        lr = config.get("lr", 0.001)
        hidden_size = config.get("hidden_size", 64)

        # 准备数据
        series = df[target_col].values.astype(np.float32)

        # 标准化
        mean = series.mean()
        std = series.std()
        series_norm = (series - mean) / std

        # 创建序列
        X, y = [], []
        for i in range(len(series_norm) - seq_length):
            X.append(series_norm[i:i + seq_length])
            y.append(series_norm[i + seq_length])

        X = torch.FloatTensor(np.array(X)).unsqueeze(-1)  # (N, seq, 1)
        y = torch.FloatTensor(np.array(y)).unsqueeze(-1)   # (N, 1)

        # 分割
        split = int(len(X) * 0.8)
        X_train, X_test = X[:split], X[split:]
        y_train, y_test = y[:split], y[split:]

        train_dataset = TensorDataset(X_train, y_train)
        train_loader = DataLoader(train_dataset, batch_size=16, shuffle=True)

        # 创建模型
        model = LSTMForecaster(
            input_size=1, hidden_size=hidden_size,
            num_layers=2, output_size=1
        ).to(self.device)

        criterion = nn.MSELoss()
        optimizer = torch.optim.Adam(model.parameters(), lr=lr)

        # 训练
        train_losses = []
        for epoch in range(epochs):
            epoch_loss = 0
            for batch_x, batch_y in train_loader:
                optimizer.zero_grad()
                pred = model(batch_x)
                loss = criterion(pred, batch_y)
                loss.backward()
                optimizer.step()
                epoch_loss += loss.item()
            avg_loss = epoch_loss / len(train_loader)
            train_losses.append(round(avg_loss, 6))

        # 评估
        model.eval()
        with torch.no_grad():
            test_pred = model(X_test)
            test_loss = criterion(test_pred, y_test).item()

        # 反标准化计算真实误差
        y_test_real = y_test.numpy() * std + mean
        pred_real = test_pred.numpy() * std + mean
        rmse = float(np.sqrt(np.mean((y_test_real - pred_real) ** 2)))
        mae = float(np.mean(np.abs(y_test_real - pred_real)))

        # 保存模型
        model_path = self._save_model(model, {
            "model_type": "lstm",
            "target_col": target_col,
            "seq_length": seq_length,
            "mean": float(mean),
            "std": float(std),
            "hidden_size": hidden_size,
        })

        elapsed = time.time() - start_time
        return {
            "status": "completed",
            "model_type": "lstm",
            "model_path": model_path,
            "metrics": {
                "train_loss": train_losses[-1],
                "test_loss": round(test_loss, 6),
                "rmse": round(rmse, 4),
                "mae": round(mae, 4),
                "train_size": len(X_train),
                "test_size": len(X_test),
            },
            "training_info": {
                "epochs": epochs,
                "final_loss": train_losses[-1],
                "loss_trend": train_losses[-5:] if len(train_losses) >= 5 else train_losses,
            },
            "training_time": round(elapsed, 2),
        }

    def train_classifier(self, df: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        训练神经网络分类器

        Args:
            df: 数据
            config: 配置
                - features: 特征列
                - target: 目标列
                - epochs: 训练轮数
                - lr: 学习率
        """
        start_time = time.time()
        features = config.get("features", [])
        target = config.get("target")
        epochs = config.get("epochs", 50)
        lr = config.get("lr", 0.001)

        from sklearn.preprocessing import LabelEncoder, StandardScaler

        X = df[features].fillna(0).values.astype(np.float32)
        y = df[target].values

        le = LabelEncoder()
        y_encoded = le.fit_transform(y)
        num_classes = len(le.classes_)

        scaler = StandardScaler()
        X = scaler.fit_transform(X).astype(np.float32)

        X_tensor = torch.FloatTensor(X)
        y_tensor = torch.LongTensor(y_encoded)

        split = int(len(X) * 0.8)
        X_train, X_test = X_tensor[:split], X_tensor[split:]
        y_train, y_test = y_tensor[:split], y_tensor[split:]

        train_dataset = TensorDataset(X_train, y_train)
        train_loader = DataLoader(train_dataset, batch_size=16, shuffle=True)

        model = SimpleClassifier(
            input_size=len(features),
            num_classes=num_classes
        ).to(self.device)

        criterion = nn.CrossEntropyLoss()
        optimizer = torch.optim.Adam(model.parameters(), lr=lr)

        train_losses = []
        for epoch in range(epochs):
            epoch_loss = 0
            for batch_x, batch_y in train_loader:
                optimizer.zero_grad()
                pred = model(batch_x)
                loss = criterion(pred, batch_y)
                loss.backward()
                optimizer.step()
                epoch_loss += loss.item()
            train_losses.append(round(epoch_loss / len(train_loader), 6))

        # 评估
        model.eval()
        with torch.no_grad():
            test_pred = model(X_test)
            pred_classes = test_pred.argmax(dim=1).numpy()
            accuracy = float((pred_classes == y_test.numpy()).mean())

        model_path = self._save_model(model, {
            "model_type": "nn_classifier",
            "features": features,
            "target": target,
            "num_classes": num_classes,
            "classes": le.classes_.tolist(),
            "scaler_mean": scaler.mean_.tolist(),
            "scaler_scale": scaler.scale_.tolist(),
        })

        elapsed = time.time() - start_time
        return {
            "status": "completed",
            "model_type": "nn_classifier",
            "model_path": model_path,
            "metrics": {
                "accuracy": round(accuracy, 4),
                "train_size": len(X_train),
                "test_size": len(X_test),
                "num_classes": num_classes,
                "final_loss": train_losses[-1],
            },
            "training_info": {
                "epochs": epochs,
                "loss_trend": train_losses[-5:] if len(train_losses) >= 5 else train_losses,
            },
            "training_time": round(elapsed, 2),
        }

    def train_autoencoder(self, df: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        训练自编码器异常检测

        Args:
            df: 数据
            config: 配置
                - features: 特征列
                - epochs: 训练轮数
                - threshold_percentile: 异常阈值百分位
        """
        start_time = time.time()
        features = config.get("features", [])
        epochs = config.get("epochs", 50)
        lr = config.get("lr", 0.001)
        encoding_dim = config.get("encoding_dim", 8)
        threshold_pct = config.get("threshold_percentile", 95)

        from sklearn.preprocessing import StandardScaler

        X = df[features].fillna(0).values.astype(np.float32)
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X).astype(np.float32)

        X_tensor = torch.FloatTensor(X_scaled)
        train_dataset = TensorDataset(X_tensor)
        train_loader = DataLoader(train_dataset, batch_size=16, shuffle=True)

        model = Autoencoder(
            input_size=len(features),
            encoding_dim=encoding_dim
        ).to(self.device)

        criterion = nn.MSELoss()
        optimizer = torch.optim.Adam(model.parameters(), lr=lr)

        train_losses = []
        for epoch in range(epochs):
            epoch_loss = 0
            for (batch_x,) in train_loader:
                optimizer.zero_grad()
                output = model(batch_x)
                loss = criterion(output, batch_x)
                loss.backward()
                optimizer.step()
                epoch_loss += loss.item()
            train_losses.append(round(epoch_loss / len(train_loader), 6))

        # 计算重构误差
        model.eval()
        with torch.no_grad():
            reconstructed = model(X_tensor)
            errors = torch.mean((reconstructed - X_tensor) ** 2, dim=1).numpy()

        threshold = float(np.percentile(errors, threshold_pct))
        n_anomalies = int(np.sum(errors > threshold))

        model_path = self._save_model(model, {
            "model_type": "autoencoder",
            "features": features,
            "encoding_dim": encoding_dim,
            "threshold": threshold,
            "threshold_percentile": threshold_pct,
            "scaler_mean": scaler.mean_.tolist(),
            "scaler_scale": scaler.scale_.tolist(),
        })

        elapsed = time.time() - start_time
        return {
            "status": "completed",
            "model_type": "autoencoder",
            "model_path": model_path,
            "metrics": {
                "anomaly_count": n_anomalies,
                "anomaly_pct": round(n_anomalies / len(X) * 100, 2),
                "threshold": round(threshold, 6),
                "mean_error": round(float(errors.mean()), 6),
                "max_error": round(float(errors.max()), 6),
                "final_loss": train_losses[-1],
            },
            "training_info": {
                "epochs": epochs,
                "loss_trend": train_losses[-5:] if len(train_losses) >= 5 else train_losses,
            },
            "training_time": round(elapsed, 2),
        }

    def list_models(self) -> List[Dict]:
        """列出已保存的 DL 模型"""
        models = []
        for f in os.listdir(self.model_dir):
            if f.endswith(".pt"):
                filepath = os.path.join(self.model_dir, f)
                meta_path = filepath.replace(".pt", "_meta.json")
                meta = {}
                if os.path.exists(meta_path):
                    with open(meta_path, "r") as fh:
                        meta = json.load(fh)
                models.append({
                    "filename": f,
                    "path": filepath,
                    "size_kb": round(os.path.getsize(filepath) / 1024, 2),
                    **meta,
                })
        return models

    def _save_model(self, model: nn.Module, meta: Dict) -> str:
        """保存模型"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_type = meta.get("model_type", "unknown")
        filename = f"{model_type}_{timestamp}.pt"
        filepath = os.path.join(self.model_dir, filename)

        torch.save(model.state_dict(), filepath)

        # 保存元数据
        meta_path = filepath.replace(".pt", "_meta.json")
        with open(meta_path, "w") as f:
            json.dump(meta, f, indent=2)

        return filepath