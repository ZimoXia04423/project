"""
不依赖 MySQL，仅用本地 data/ecommerce_reviews.csv 重训最优 ML 模型并导出 SHAP 图。
用于调整 interpretability.py 绘图样式后快速更新 output/shap_feature_importance.png。
"""
import os
import sys

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_DIR)

import pandas as pd
from sklearn.model_selection import train_test_split

from src.preprocessing import preprocess_dataframe
from src.feature_extraction import (
    extract_tfidf_features,
    extract_manual_features,
    combine_features,
)
from src.ml_models import get_ml_models, train_and_evaluate_all_ml
from src.evaluation import evaluate_all_models
from src.interpretability import shap_explain


def main():
    csv_path = os.path.join(PROJECT_DIR, "data", "ecommerce_reviews.csv")
    output_dir = os.path.join(PROJECT_DIR, "output")
    stopwords_path = os.path.join(PROJECT_DIR, "data", "stopwords.txt")

    if not os.path.isfile(csv_path):
        print(f"未找到 {csv_path}，请先成功运行一次 main.py 生成 CSV。")
        sys.exit(1)

    df = pd.read_csv(csv_path)
    df = preprocess_dataframe(df, stopwords_path)
    train_df, test_df = train_test_split(
        df, test_size=0.2, random_state=42, stratify=df["label"]
    )
    y_train = train_df["label"].values
    y_test = test_df["label"].values

    X_train_tfidf, X_test_tfidf, vectorizer = extract_tfidf_features(
        train_df["tokenized_text"], test_df["tokenized_text"]
    )
    train_manual = extract_manual_features(train_df)
    test_manual = extract_manual_features(test_df)
    X_train_combined = combine_features(X_train_tfidf, train_manual)
    X_test_combined = combine_features(X_test_tfidf, test_manual)

    ml_models = get_ml_models()
    ml_results = train_and_evaluate_all_ml(
        ml_models, X_train_combined, y_train, X_test_combined
    )
    df_metrics = evaluate_all_models(ml_results, y_test)
    ml_names = list(ml_results.keys())
    df_ml = df_metrics[df_metrics["model"].isin(ml_names)]
    best_ml_name = df_ml.loc[df_ml["f1"].idxmax(), "model"]
    print(f"SHAP 使用模型: {best_ml_name}")

    feature_names = vectorizer.get_feature_names_out().tolist()
    feature_names += [
        "review_length",
        "exclamation_count",
        "repeat_char_ratio",
        "sentiment_score",
        "user_review_count",
        "avg_review_interval_days",
        "rating",
    ]

    best_model = ml_results[best_ml_name]["model"]
    shap_explain(
        best_model,
        X_train_combined,
        X_test_combined,
        feature_names,
        output_dir=output_dir,
        n_background=50,
    )
    print(f"已写入: {os.path.join(output_dir, 'shap_feature_importance.png')}")


if __name__ == "__main__":
    main()
