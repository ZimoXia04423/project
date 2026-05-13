"""
机器学习模型模块：逻辑回归、支持向量机、随机森林、XGBoost
"""
import time
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier


def get_ml_models():
    """返回所有机器学习模型的字典"""
    models = {
        "逻辑回归(LR)": LogisticRegression(
            max_iter=1000, C=1.0, random_state=42
        ),
        "支持向量机(SVM)": SVC(
            kernel="rbf", C=1.0, gamma="scale", 
            probability=True, random_state=42
        ),
        "随机森林(RF)": RandomForestClassifier(
            n_estimators=100, max_depth=20, 
            random_state=42, n_jobs=-1
        ),
        "XGBoost": XGBClassifier(
            n_estimators=100, max_depth=6, 
            learning_rate=0.1, random_state=42,
            use_label_encoder=False, eval_metric="logloss"
        ),
    }
    return models


def train_ml_model(model, X_train, y_train):
    """
    训练单个机器学习模型并返回训练时间
    
    Returns:
        trained_model, train_time_seconds
    """
    start_time = time.time()
    model.fit(X_train, y_train)
    train_time = time.time() - start_time
    return model, train_time


def predict_ml_model(model, X_test):
    """
    使用模型进行预测并返回预测时间
    
    Returns:
        predictions, probabilities, predict_time_seconds
    """
    start_time = time.time()
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]
    predict_time = time.time() - start_time
    return y_pred, y_prob, predict_time


def train_and_evaluate_all_ml(models, X_train, y_train, X_test):
    """
    训练所有机器学习模型
    
    Returns:
        dict: {model_name: {model, y_pred, y_prob, train_time, predict_time}}
    """
    results = {}
    for name, model in models.items():
        print(f"\n正在训练 {name}...")
        trained_model, train_time = train_ml_model(model, X_train, y_train)
        y_pred, y_prob, predict_time = predict_ml_model(trained_model, X_test)
        
        results[name] = {
            "model": trained_model,
            "y_pred": y_pred,
            "y_prob": y_prob,
            "train_time": round(train_time, 3),
            "predict_time": round(predict_time, 3),
        }
        print(f"  训练时间: {train_time:.3f}s, 预测时间: {predict_time:.3f}s")
    
    return results
