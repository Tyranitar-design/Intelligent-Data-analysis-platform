"""
机器学习服务层
- 分类模型
- 回归模型
- 聚类模型
- 模型评估
"""
import pandas as pd
import numpy as np
import json
import os
import time
import joblib
from typing import Dict, Any, List, Optional
from datetime import datetime

from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor, GradientBoostingClassifier, GradientBoostingRegressor
from sklearn.linear_model import LogisticRegression, LinearRegression, Ridge, Lasso
from sklearn.svm import SVC, SVR
from sklearn.cluster import KMeans, DBSCAN
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score, classification_report,
    mean_squared_error, mean_absolute_error, r2_score,
    silhouette_score
)
import xgboost as xgb
import lightgbm as lgb


class MLService:
    """机器学习服务"""

    def __init__(self, model_dir: str = None, db_path: str = None):
        if model_dir is None:
            model_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "data", "models"
            )
        self.model_dir = model_dir
        os.makedirs(model_dir, exist_ok=True)

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

    def load_ecommerce_for_ml(self, platform: str = None, keywords: List[str] = None,
                               min_price: float = None, max_price: float = None,
                               limit: int = 1000) -> pd.DataFrame:
        """从数据库加载电商数据用于ML"""
        if self.db_service is None:
            return pd.DataFrame()
        return self.db_service.get_ecommerce_data(
            platform=platform, keywords=keywords,
            min_price=min_price, max_price=max_price, limit=limit
        )

    # ==================== 算法映射 ====================

    CLASSIFIERS = {
        "random_forest": RandomForestClassifier,
        "logistic_regression": LogisticRegression,
        "gradient_boosting": GradientBoostingClassifier,
        "xgboost": xgb.XGBClassifier,
        "lightgbm": lgb.LGBMClassifier,
        "svc": SVC,
    }

    REGRESSORS = {
        "random_forest": RandomForestRegressor,
        "linear_regression": LinearRegression,
        "ridge": Ridge,
        "lasso": Lasso,
        "gradient_boosting": GradientBoostingRegressor,
        "xgboost": xgb.XGBRegressor,
        "lightgbm": lgb.LGBMRegressor,
        "svr": SVR,
    }

    CLUSTERERS = {
        "kmeans": KMeans,
        "dbscan": DBSCAN,
    }

    def train(self, df: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        训练模型

        Args:
            df: 训练数据
            config: 训练配置
                - model_type: classification/regression/clustering
                - algorithm: 算法名称
                - features: 特征列
                - target: 目标列（分类/回归）
                - params: 模型参数
                - test_size: 测试集比例

        Returns:
            训练结果
        """
        model_type = config["model_type"]
        algorithm = config["algorithm"]
        features = config.get("features", [])
        target = config.get("target")
        params = config.get("params", {})
        test_size = config.get("test_size", 0.2)

        start_time = time.time()

        # 准备数据
        X = df[features] if features else df.select_dtypes(include=[np.number])

        # 处理缺失值
        X = X.fillna(X.mean(numeric_only=True))

        # 标准化
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        if model_type == "classification":
            result = self._train_classification(X_scaled, df[target], algorithm, params, test_size, features, scaler)
        elif model_type == "regression":
            result = self._train_regression(X_scaled, df[target], algorithm, params, test_size, features, scaler)
        elif model_type == "clustering":
            result = self._train_clustering(X_scaled, algorithm, params, features, scaler)
        else:
            raise ValueError(f"Unknown model type: {model_type}")

        elapsed = time.time() - start_time
        result["training_time"] = round(elapsed, 2)
        result["model_type"] = model_type
        result["algorithm"] = algorithm
        result["features"] = features
        result["target"] = target
        result["row_count"] = len(df)
        result["feature_count"] = len(features) if features else X.shape[1]

        return result

    def _train_classification(self, X, y, algorithm, params, test_size, features, scaler):
        """训练分类模型"""
        # 标签编码
        le = LabelEncoder()
        y_encoded = le.fit_transform(y)

        # 分割数据
        X_train, X_test, y_train, y_test = train_test_split(
            X, y_encoded, test_size=test_size, random_state=42, stratify=y_encoded
        )

        # 创建模型
        model_class = self.CLASSIFIERS.get(algorithm)
        if not model_class:
            raise ValueError(f"Unknown classifier: {algorithm}")

        model = model_class(**params, random_state=42) if "random_state" in model_class().get_params() else model_class(**params)
        model.fit(X_train, y_train)

        # 预测
        y_pred = model.predict(X_test)

        # 评估
        metrics = {
            "accuracy": round(float(accuracy_score(y_test, y_pred)), 4),
            "precision": round(float(precision_score(y_test, y_pred, average="weighted", zero_division=0)), 4),
            "recall": round(float(recall_score(y_test, y_pred, average="weighted", zero_division=0)), 4),
            "f1_score": round(float(f1_score(y_test, y_pred, average="weighted", zero_division=0)), 4),
            "train_size": len(X_train),
            "test_size": len(X_test),
            "classes": le.classes_.tolist(),
        }

        # 交叉验证
        cv_scores = cross_val_score(model, X, y_encoded, cv=5, scoring="accuracy")
        metrics["cv_accuracy_mean"] = round(float(cv_scores.mean()), 4)
        metrics["cv_accuracy_std"] = round(float(cv_scores.std()), 4)

        # 保存模型
        model_path = self._save_model(model, scaler, le, algorithm, "classification")

        return {"metrics": metrics, "model_path": model_path, "status": "completed"}

    def _train_regression(self, X, y, algorithm, params, test_size, features, scaler):
        """训练回归模型"""
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42
        )

        model_class = self.REGRESSORS.get(algorithm)
        if not model_class:
            raise ValueError(f"Unknown regressor: {algorithm}")

        model = model_class(**params, random_state=42) if "random_state" in model_class().get_params() else model_class(**params)
        model.fit(X_train, y_train)

        y_pred = model.predict(X_test)

        metrics = {
            "r2": round(float(r2_score(y_test, y_pred)), 4),
            "mae": round(float(mean_absolute_error(y_test, y_pred)), 4),
            "rmse": round(float(np.sqrt(mean_squared_error(y_test, y_pred))), 4),
            "train_size": len(X_train),
            "test_size": len(X_test),
        }

        cv_scores = cross_val_score(model, X, y, cv=5, scoring="r2")
        metrics["cv_r2_mean"] = round(float(cv_scores.mean()), 4)
        metrics["cv_r2_std"] = round(float(cv_scores.std()), 4)

        model_path = self._save_model(model, scaler, None, algorithm, "regression")

        return {"metrics": metrics, "model_path": model_path, "status": "completed"}

    def _train_clustering(self, X, algorithm, params, features, scaler):
        """训练聚类模型"""
        model_class = self.CLUSTERERS.get(algorithm)
        if not model_class:
            raise ValueError(f"Unknown clusterer: {algorithm}")

        model = model_class(**params)
        labels = model.fit_predict(X)

        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        metrics = {
            "n_clusters": n_clusters,
            "noise_points": int(np.sum(labels == -1)) if -1 in labels else 0,
        }

        if n_clusters > 1:
            metrics["silhouette_score"] = round(float(silhouette_score(X, labels)), 4)

        model_path = self._save_model(model, scaler, None, algorithm, "clustering")

        return {"metrics": metrics, "model_path": model_path, "status": "completed", "labels": labels.tolist()[:100]}

    def predict(self, model_path: str, data: pd.DataFrame) -> List:
        """使用已保存的模型进行预测"""
        artifact = joblib.load(model_path)
        model = artifact["model"]
        scaler = artifact["scaler"]
        le = artifact.get("label_encoder")

        X = data.select_dtypes(include=[np.number]).fillna(0)
        X_scaled = scaler.transform(X)

        predictions = model.predict(X_scaled)

        if le is not None:
            predictions = le.inverse_transform(predictions)

        return predictions.tolist()

    def _save_model(self, model, scaler, le, algorithm, model_type):
        """保存模型"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{model_type}_{algorithm}_{timestamp}.joblib"
        filepath = os.path.join(self.model_dir, filename)

        artifact = {
            "model": model,
            "scaler": scaler,
            "label_encoder": le,
            "algorithm": algorithm,
            "model_type": model_type,
            "saved_at": timestamp,
        }

        joblib.dump(artifact, filepath)
        return filepath

    def list_algorithms(self) -> Dict[str, Any]:
        """列出所有可用算法"""
        return {
            "classification": list(self.CLASSIFIERS.keys()),
            "regression": list(self.REGRESSORS.keys()),
            "clustering": list(self.CLUSTERERS.keys()),
        }