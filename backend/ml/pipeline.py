# -*- coding: utf-8 -*-
"""
ML Pipeline v2.0
================

功能:
- 一键训练 Pipeline (数据准备 → 特征工程 → 训练 → 评估)
- 超参调优 (GridSearch / RandomizedSearch / Optuna Bayesian)
- 交叉验证 + 学习曲线
- 模型评估报告 (混淆矩阵 / ROC-AUC / 特征重要性)
- 模型持久化 + 版本管理
"""
import json
import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import (
    train_test_split, cross_val_score, GridSearchCV,
    RandomizedSearchCV, StratifiedKFold, KFold,
    learning_curve
)
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    classification_report, confusion_matrix, roc_auc_score, roc_curve,
    mean_squared_error, mean_absolute_error, r2_score,
    silhouette_score
)
from sklearn.preprocessing import LabelEncoder

from analysis.feature_engine import FeatureEngine

logger = logging.getLogger(__name__)


# ==================== 模型注册 ====================

MODEL_REGISTRY = {
    # 分类
    "classification": {
        "logistic_regression": {
            "name": "逻辑回归",
            "class": "sklearn.linear_model.LogisticRegression",
            "default_params": {"max_iter": 1000, "random_state": 42},
            "param_grid": {"C": [0.01, 0.1, 1, 10], "penalty": ["l1", "l2"]},
        },
        "random_forest": {
            "name": "随机森林",
            "class": "sklearn.ensemble.RandomForestClassifier",
            "default_params": {"n_estimators": 100, "random_state": 42},
            "param_grid": {"n_estimators": [50, 100, 200], "max_depth": [5, 10, None]},
        },
        "xgboost": {
            "name": "XGBoost",
            "class": "xgboost.XGBClassifier",
            "default_params": {"n_estimators": 100, "random_state": 42, "use_label_encoder": False, "eval_metric": "logloss"},
            "param_grid": {"n_estimators": [50, 100, 200], "max_depth": [3, 5, 7], "learning_rate": [0.01, 0.1, 0.3]},
        },
        "lightgbm": {
            "name": "LightGBM",
            "class": "lightgbm.LGBMClassifier",
            "default_params": {"n_estimators": 100, "random_state": 42, "verbose": -1},
            "param_grid": {"n_estimators": [50, 100, 200], "max_depth": [3, 5, -1], "learning_rate": [0.01, 0.1, 0.3]},
        },
        "svm": {
            "name": "SVM",
            "class": "sklearn.svm.SVC",
            "default_params": {"random_state": 42},
            "param_grid": {"C": [0.1, 1, 10], "kernel": ["rbf", "linear"]},
        },
    },
    # 回归
    "regression": {
        "linear_regression": {
            "name": "线性回归",
            "class": "sklearn.linear_model.LinearRegression",
            "default_params": {},
            "param_grid": {},
        },
        "ridge": {
            "name": "岭回归",
            "class": "sklearn.linear_model.Ridge",
            "default_params": {"random_state": 42},
            "param_grid": {"alpha": [0.01, 0.1, 1, 10, 100]},
        },
        "lasso": {
            "name": "Lasso",
            "class": "sklearn.linear_model.Lasso",
            "default_params": {"random_state": 42},
            "param_grid": {"alpha": [0.01, 0.1, 1, 10]},
        },
        "random_forest": {
            "name": "随机森林回归",
            "class": "sklearn.ensemble.RandomForestRegressor",
            "default_params": {"n_estimators": 100, "random_state": 42},
            "param_grid": {"n_estimators": [50, 100, 200], "max_depth": [5, 10, None]},
        },
        "xgboost": {
            "name": "XGBoost回归",
            "class": "xgboost.XGBRegressor",
            "default_params": {"n_estimators": 100, "random_state": 42},
            "param_grid": {"n_estimators": [50, 100, 200], "max_depth": [3, 5, 7], "learning_rate": [0.01, 0.1, 0.3]},
        },
        "lightgbm": {
            "name": "LightGBM回归",
            "class": "lightgbm.LGBMRegressor",
            "default_params": {"n_estimators": 100, "random_state": 42, "verbose": -1},
            "param_grid": {"n_estimators": [50, 100, 200], "max_depth": [3, 5, -1], "learning_rate": [0.01, 0.1, 0.3]},
        },
    },
    # 聚类
    "clustering": {
        "kmeans": {
            "name": "K-Means",
            "class": "sklearn.cluster.KMeans",
            "default_params": {"n_clusters": 3, "random_state": 42},
            "param_grid": {"n_clusters": [2, 3, 4, 5, 6]},
        },
        "dbscan": {
            "name": "DBSCAN",
            "class": "sklearn.cluster.DBSCAN",
            "default_params": {"eps": 0.5, "min_samples": 5},
            "param_grid": {"eps": [0.3, 0.5, 0.7], "min_samples": [3, 5, 10]},
        },
    },
}


class MLPipeline:
    """ML Pipeline v2"""
    
    def __init__(self, model_dir: str = None):
        if model_dir is None:
            model_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "data", "models"
            )
        self.model_dir = model_dir
        os.makedirs(model_dir, exist_ok=True)
        self.feature_engine = FeatureEngine()
    
    def list_algorithms(self) -> Dict[str, Any]:
        """列出可用算法"""
        result = {}
        for task_type, models in MODEL_REGISTRY.items():
            result[task_type] = [
                {
                    "id": model_id,
                    "name": info["name"],
                    "class": info["class"],
                }
                for model_id, info in models.items()
            ]
        return result
    
    def train(
        self,
        df: pd.DataFrame,
        target_col: str,
        algorithm: str,
        task_type: str = "auto",
        test_size: float = 0.2,
        feature_config: Dict = None,
        tune: bool = False,
        tune_method: str = "grid",  # grid / random / optuna
        cv_folds: int = 5,
        random_state: int = 42,
    ) -> Dict[str, Any]:
        """
        训练模型 — 完整 Pipeline
        
        Returns:
            {
                "model_id": str,
                "algorithm": str,
                "task_type": str,
                "feature_report": {...},
                "train_score": float,
                "test_score": float,
                "cv_scores": [...],
                "evaluation": {...},
                "feature_importance": {...},
                "training_time_seconds": float,
            }
        """
        start_time = time.time()
        
        # 自动推断任务类型
        if task_type == "auto":
            task_type = self._infer_task_type(df[target_col])
        
        # 获取模型配置
        model_info = MODEL_REGISTRY.get(task_type, {}).get(algorithm)
        if not model_info:
            available = list(MODEL_REGISTRY.get(task_type, {}).keys())
            return {"error": f"算法 '{algorithm}' 不适用于 {task_type}，可用: {available}"}
        
        # 特征工程
        df_processed, feature_report = self.feature_engine.engineer(
            df, target_col=target_col, task_type=task_type, config=feature_config
        )
        
        # 准备数据
        X = df_processed.drop(columns=[target_col])
        y = df_processed[target_col]
        
        # 分割数据
        if task_type == "clustering":
            X_train, X_test, y_train, y_test = X, X, y, y
        else:
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=test_size, random_state=random_state,
                stratify=y if task_type == "classification" else None,
            )
        
        # 创建模型
        model_class = self._import_class(model_info["class"])
        model = model_class(**model_info["default_params"])
        
        # 超参调优
        if tune and model_info["param_grid"]:
            model, tune_report = self._tune(
                model, model_info["param_grid"], X_train, y_train,
                task_type, tune_method, cv_folds,
            )
        else:
            tune_report = None
        
        # 训练
        model.fit(X_train, y_train)
        
        # 评估
        evaluation = self._evaluate(model, X_test, y_test, X_train, y_train, task_type)
        
        # 交叉验证
        cv_scores = []
        if task_type != "clustering":
            try:
                scoring = "accuracy" if task_type == "classification" else "r2"
                cv = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=random_state) if task_type == "classification" else KFold(n_splits=cv_folds, shuffle=True, random_state=random_state)
                cv_result = cross_val_score(model, X, y, cv=cv, scoring=scoring)
                cv_scores = [round(float(s), 4) for s in cv_result]
            except Exception as e:
                logger.warning(f"交叉验证失败: {e}")
        
        # 特征重要性
        feature_importance = self._get_feature_importance(model, list(X.columns), task_type)
        
        # 保存模型
        model_id = f"{algorithm}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        model_path = os.path.join(self.model_dir, f"{model_id}.joblib")
        joblib.dump(model, model_path)
        
        training_time = round(time.time() - start_time, 2)
        
        return {
            "model_id": model_id,
            "algorithm": algorithm,
            "task_type": task_type,
            "model_path": model_path,
            "feature_report": feature_report,
            "data_shape": {"train": X_train.shape, "test": X_test.shape},
            "evaluation": evaluation,
            "cv_scores": cv_scores,
            "cv_mean": round(np.mean(cv_scores), 4) if cv_scores else None,
            "feature_importance": feature_importance,
            "tune_report": tune_report,
            "training_time_seconds": training_time,
        }
    
    def predict(self, model_id: str, data: pd.DataFrame) -> Dict[str, Any]:
        """使用模型预测"""
        model_path = os.path.join(self.model_dir, f"{model_id}.joblib")
        if not os.path.exists(model_path):
            return {"error": f"模型不存在: {model_id}"}
        
        model = joblib.load(model_path)
        
        # 特征工程（使用相同 Pipeline）
        feature_cols = [c for c in data.columns if c in model.feature_names_in_] if hasattr(model, 'feature_names_in_') else data.select_dtypes(include=[np.number]).columns
        X = data[list(feature_cols)]
        
        predictions = model.predict(X)
        
        result = {
            "model_id": model_id,
            "predictions": predictions.tolist()[:1000],
            "count": len(predictions),
        }
        
        # 概率预测（分类模型）
        if hasattr(model, 'predict_proba'):
            try:
                proba = model.predict_proba(X)
                result["probabilities"] = proba.tolist()[:1000]
            except Exception:
                pass
        
        return result
    
    # ==================== 内部方法 ====================
    
    def _infer_task_type(self, y: pd.Series) -> str:
        """自动推断任务类型"""
        nunique = y.nunique()
        if pd.api.types.is_numeric_dtype(y):
            if nunique <= 10 and set(y.dropna().unique()) <= {0, 1, 0.0, 1.0}:
                return "classification"
            if nunique <= 20 and nunique / len(y) < 0.05:
                return "classification"
            return "regression"
        return "classification"
    
    def _import_class(self, class_path: str):
        """动态导入类"""
        parts = class_path.rsplit(".", 1)
        module_path = parts[0]
        class_name = parts[1]
        
        import importlib
        module = importlib.import_module(module_path)
        return getattr(module, class_name)
    
    def _tune(self, model, param_grid, X, y, task_type, method, cv_folds):
        """超参调优"""
        scoring = "accuracy" if task_type == "classification" else "r2"
        
        if method == "optuna":
            return self._tune_optuna(model, param_grid, X, y, task_type, cv_folds)
        elif method == "random":
            search = RandomizedSearchCV(
                model, param_grid, n_iter=20, cv=cv_folds,
                scoring=scoring, random_state=42, n_jobs=-1,
            )
        else:  # grid
            search = GridSearchCV(
                model, param_grid, cv=cv_folds,
                scoring=scoring, n_jobs=-1,
            )
        
        search.fit(X, y)
        
        return search.best_estimator_, {
            "method": method,
            "best_params": search.best_params_,
            "best_score": round(float(search.best_score_), 4),
        }
    
    def _tune_optuna(self, model, param_grid, X, y, task_type, cv_folds):
        """Optuna Bayesian 调优"""
        try:
            import optuna
            optuna.logging.set_verbosity(optuna.logging.WARNING)
        except ImportError:
            logger.warning("optuna 未安装，回退到 GridSearch")
            return self._tune(model, param_grid, X, y, task_type, "grid", cv_folds)
        
        from sklearn.model_selection import cross_val_score
        from sklearn.base import clone
        
        scoring = "accuracy" if task_type == "classification" else "r2"
        
        def objective(trial):
            params = {}
            for param_name, param_values in param_grid.items():
                if isinstance(param_values[0], int):
                    params[param_name] = trial.suggest_int(param_name, min(param_values), max(param_values))
                elif isinstance(param_values[0], float):
                    params[param_name] = trial.suggest_float(param_name, min(param_values), max(param_values), log=True if any(v < 0.1 for v in param_values) else False)
                else:
                    params[param_name] = trial.suggest_categorical(param_name, param_values)
            
            m = clone(model).set_params(**params)
            scores = cross_val_score(m, X, y, cv=cv_folds, scoring=scoring)
            return scores.mean()
        
        study = optuna.create_study(direction="maximize")
        study.optimize(objective, n_trials=30, show_progress_bar=False)
        
        best_model = clone(model).set_params(**study.best_params)
        best_model.fit(X, y)
        
        return best_model, {
            "method": "optuna",
            "best_params": study.best_params,
            "best_score": round(float(study.best_value), 4),
            "n_trials": len(study.trials),
        }
    
    def _evaluate(self, model, X_test, y_test, X_train, y_train, task_type) -> Dict[str, Any]:
        """模型评估"""
        y_pred = model.predict(X_test)
        
        if task_type == "classification":
            report = {
                "accuracy": round(float(accuracy_score(y_test, y_pred)), 4),
                "precision": round(float(precision_score(y_test, y_pred, average="weighted", zero_division=0)), 4),
                "recall": round(float(recall_score(y_test, y_pred, average="weighted", zero_division=0)), 4),
                "f1": round(float(f1_score(y_test, y_pred, average="weighted", zero_division=0)), 4),
            }
            
            # 混淆矩阵
            cm = confusion_matrix(y_test, y_pred)
            report["confusion_matrix"] = cm.tolist()
            
            # ROC-AUC (二分类)
            if len(np.unique(y_test)) == 2 and hasattr(model, 'predict_proba'):
                try:
                    y_proba = model.predict_proba(X_test)[:, 1]
                    report["roc_auc"] = round(float(roc_auc_score(y_test, y_proba)), 4)
                except Exception:
                    pass
            
            # 训练集得分
            y_train_pred = model.predict(X_train)
            report["train_accuracy"] = round(float(accuracy_score(y_train, y_train_pred)), 4)
            
        elif task_type == "regression":
            report = {
                "r2": round(float(r2_score(y_test, y_pred)), 4),
                "rmse": round(float(np.sqrt(mean_squared_error(y_test, y_pred))), 4),
                "mae": round(float(mean_absolute_error(y_test, y_pred)), 4),
                "mse": round(float(mean_squared_error(y_test, y_pred)), 4),
            }
            
            y_train_pred = model.predict(X_train)
            report["train_r2"] = round(float(r2_score(y_train, y_train_pred)), 4)
            
        elif task_type == "clustering":
            if len(np.unique(y_pred)) > 1:
                report = {
                    "silhouette_score": round(float(silhouette_score(X_test, y_pred)), 4),
                    "n_clusters": int(len(np.unique(y_pred))),
                }
            else:
                report = {"n_clusters": int(len(np.unique(y_pred)))}
        
        return report
    
    def _get_feature_importance(self, model, feature_names, task_type) -> Dict[str, Any]:
        """获取特征重要性"""
        importance = {}
        
        # Tree-based models
        if hasattr(model, 'feature_importances_'):
            importances = model.feature_importances_
            importance = {
                name: round(float(imp), 6)
                for name, imp in sorted(
                    zip(feature_names, importances),
                    key=lambda x: -x[1]
                )
            }
        # Linear models
        elif hasattr(model, 'coef_'):
            coef = model.coef_
            if coef.ndim > 1:
                coef = coef[0]
            importance = {
                name: round(float(c), 6)
                for name, c in sorted(
                    zip(feature_names, coef),
                    key=lambda x: -abs(x[1])
                )
            }
        
        # 返回 top 20
        top_items = list(importance.items())[:20]
        return dict(top_items)
