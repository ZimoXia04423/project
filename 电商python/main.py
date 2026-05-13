"""
电商平台用户评论虚假信息识别模型构建与比较研究
主程序：串联数据爬取、数据库存储、数据清洗、预处理、特征提取、模型训练、评估、
       可解释性和鲁棒性分析全流程
"""
import os
import sys
import json
import warnings
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

warnings.filterwarnings("ignore")

# 将项目根目录加入路径
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_DIR)

from src.crawler import EcommerceReviewCrawler
from src.database import ReviewDatabase
from src.data_cleaning import DataCleaner
from src.preprocessing import preprocess_dataframe
from src.feature_extraction import extract_tfidf_features, extract_manual_features, combine_features
from src.ml_models import get_ml_models, train_and_evaluate_all_ml
from src.dl_models import (build_vocab, texts_to_sequences, 
                            train_and_evaluate_all_dl)
from src.evaluation import (evaluate_all_models, plot_metrics_comparison,
                             plot_roc_curves, plot_confusion_matrices,
                             plot_time_comparison, plot_training_losses,
                             save_metrics_to_json)
from src.interpretability import lime_explain, shap_explain
from src.robustness import robustness_test_all_models, plot_robustness_results


def main():
    OUTPUT_DIR = os.path.join(PROJECT_DIR, "output")
    DATA_DIR = os.path.join(PROJECT_DIR, "data")
    STOPWORDS_PATH = os.path.join(DATA_DIR, "stopwords.txt")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    print("=" * 70)
    print("  电商平台用户评论虚假信息识别模型构建与比较研究")
    print("=" * 70)
    
    # ==================== 1. 数据爬取 ====================
    print("\n>>> [1/10] 数据爬取（合规模式：本地模拟数据源）...")
    crawler = EcommerceReviewCrawler(platform="taobao", use_local=True)
    
    # 模拟抓取多个商品的评论（20个商品 × 5页 × 20条/页 = 2000条）
    product_ids = [f"P{10001+i}" for i in range(20)]
    all_reviews = crawler.crawl_multiple_products(product_ids, max_pages_per_product=5)
    
    # 保存原始爬取数据
    raw_data_path = os.path.join(DATA_DIR, "raw_crawled_data.json")
    crawler.save_raw_data(all_reviews, raw_data_path)
    crawl_stats = crawler.get_crawl_stats()
    print(f"  爬取完成: 共 {len(all_reviews)} 条原始评论")
    
    # ==================== 2. 数据库存储 ====================
    print("\n>>> [2/10] 数据入库（MySQL: fake_review_detection）...")
    db = ReviewDatabase()
    db.clear_tables()
    
    # 先入商品表和用户表（外键约束要求）
    product_info = crawler.generate_product_info(product_ids)
    user_info = crawler.generate_user_info(all_reviews)
    db.insert_products(product_info)
    db.insert_users(user_info)
    
    # 再入评论表
    inserted, duplicated = db.insert_reviews(all_reviews)
    db.log_crawl(crawl_stats, platform="taobao", target_products=len(product_ids))
    
    db_stats = db.get_statistics()
    print(f"  数据库统计:")
    print(f"    商品数: {db_stats['total_products']}, 用户数: {db_stats['total_users']}")
    print(f"    评论数: {db_stats['total_reviews']} 条")
    print(f"    标签分布: {db_stats['label_distribution']}")
    print(f"    评分分布: {db_stats['rating_distribution']}")
    
    # 保存数据库统计到JSON
    with open(os.path.join(OUTPUT_DIR, "db_stats.json"), "w", encoding="utf-8") as f:
        json.dump(db_stats, f, ensure_ascii=False, indent=2)
    
    # ==================== 3. 数据清洗 ====================
    print("\n>>> [3/10] 数据清洗...")
    cleaner = DataCleaner(db)
    cleaning_stats = cleaner.run_pipeline(min_length=4)
    
    # 获取清洗后的DataFrame
    df = cleaner.get_clean_dataframe()
    
    # 同时导出CSV备份
    csv_path = os.path.join(DATA_DIR, "ecommerce_reviews.csv")
    db.export_to_csv(csv_path)
    
    # 保存清洗统计
    with open(os.path.join(OUTPUT_DIR, "cleaning_stats.json"), "w", encoding="utf-8") as f:
        json.dump(cleaning_stats, f, ensure_ascii=False, indent=2)
    
    print(f"  清洗后数据集: {len(df)} 条")
    print(f"  真实评论: {(df['label']==0).sum()} 条, 虚假评论: {(df['label']==1).sum()} 条")
    
    # 关闭数据库
    db.close()
    
    # ==================== 4. 文本预处理 ====================
    print("\n>>> [4/10] 文本预处理...")
    df = preprocess_dataframe(df, STOPWORDS_PATH)
    
    # ==================== 5. 数据集划分 ====================
    print("\n>>> [5/10] 划分训练集和测试集...")
    train_df, test_df = train_test_split(df, test_size=0.2, random_state=42, stratify=df["label"])
    print(f"  训练集: {len(train_df)} 条, 测试集: {len(test_df)} 条")
    
    y_train = train_df["label"].values
    y_test = test_df["label"].values
    
    # ==================== 6. 特征提取（机器学习用） ====================
    print("\n>>> [6/10] 提取特征...")
    X_train_tfidf, X_test_tfidf, vectorizer = extract_tfidf_features(
        train_df["tokenized_text"], test_df["tokenized_text"]
    )
    
    train_manual = extract_manual_features(train_df)
    test_manual = extract_manual_features(test_df)
    
    X_train_combined = combine_features(X_train_tfidf, train_manual)
    X_test_combined = combine_features(X_test_tfidf, test_manual)
    
    # ==================== 7. 机器学习模型 ====================
    print("\n>>> [7/10] 训练机器学习模型...")
    ml_models = get_ml_models()
    ml_results = train_and_evaluate_all_ml(ml_models, X_train_combined, y_train, X_test_combined)
    
    # ==================== 8. 深度学习模型 ====================
    print("\n>>> [8/10] 训练深度学习模型...")
    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"  使用设备: {device}")
    
    # 构建词汇表和序列
    all_tokens = pd.concat([train_df["tokenized"], test_df["tokenized"]]).tolist()
    vocab = build_vocab(all_tokens, max_vocab=8000)
    MAX_LEN = 64
    
    X_train_seq = texts_to_sequences(train_df["tokenized"].tolist(), vocab, max_len=MAX_LEN)
    X_test_seq = texts_to_sequences(test_df["tokenized"].tolist(), vocab, max_len=MAX_LEN)
    
    dl_results = train_and_evaluate_all_dl(
        X_train_seq, y_train, X_test_seq, y_test,
        vocab_size=len(vocab), max_len=MAX_LEN, epochs=10, device=device
    )
    
    # ==================== 9. 模型评估与对比 ====================
    print("\n>>> [9/10] 模型评估与可视化...")
    # 合并所有结果
    all_results = {}
    all_results.update(ml_results)
    all_results.update(dl_results)
    
    # 评估
    df_metrics = evaluate_all_models(all_results, y_test)
    
    # 生成图表
    plot_metrics_comparison(df_metrics, OUTPUT_DIR)
    plot_roc_curves(all_results, y_test, OUTPUT_DIR)
    plot_confusion_matrices(all_results, y_test, OUTPUT_DIR)
    plot_time_comparison(df_metrics, OUTPUT_DIR)
    plot_training_losses(dl_results, OUTPUT_DIR)
    save_metrics_to_json(df_metrics, OUTPUT_DIR)
    
    # ==================== 10. 可解释性与鲁棒性分析 ====================
    print("\n>>> [10/10] 可解释性与鲁棒性分析...")
    
    # LIME分析
    print("\n--- LIME可解释性分析 ---")
    ml_model_names = list(ml_results.keys())
    df_ml_metrics = df_metrics[df_metrics["model"].isin(ml_model_names)]
    best_ml_name = df_ml_metrics.loc[df_ml_metrics["f1"].idxmax(), "model"]
    print(f"  选择最佳ML模型进行可解释性分析: {best_ml_name}")
    # 只对TF-IDF特征做LIME（LIME需要文本输入）
    lime_data = None
    try:
        # 用一个仅基于TF-IDF的简单模型做LIME解释
        from sklearn.linear_model import LogisticRegression
        lime_model = LogisticRegression(max_iter=1000, random_state=42)
        lime_model.fit(X_train_tfidf, y_train)
        lime_data = lime_explain(
            lime_model, X_train_tfidf, X_test_tfidf, vectorizer,
            test_df["tokenized_text"].reset_index(drop=True),
            pd.Series(y_test),
            n_samples=3, output_dir=OUTPUT_DIR
        )
    except Exception as e:
        print(f"  LIME分析出错: {e}")
    
    # SHAP分析
    print("\n--- SHAP可解释性分析 ---")
    shap_data = None
    try:
        feature_names = vectorizer.get_feature_names_out().tolist()
        feature_names += ["review_length", "exclamation_count", "repeat_char_ratio",
                          "sentiment_score", "user_review_count", 
                          "avg_review_interval_days", "rating"]
        
        best_ml_model = ml_results[best_ml_name]["model"]
        shap_data = shap_explain(
            best_ml_model, X_train_combined, X_test_combined, 
            feature_names, OUTPUT_DIR, n_background=50
        )
    except Exception as e:
        print(f"  SHAP分析出错: {e}")
    
    # 鲁棒性分析（仅对机器学习模型）
    print("\n--- 鲁棒性分析 ---")
    ml_model_objs = {name: res["model"] for name, res in ml_results.items()}
    robustness_results = robustness_test_all_models(
        ml_model_objs, vectorizer, 
        test_df["tokenized_text"].reset_index(drop=True),
        y_test, noise_levels=[0.05, 0.1, 0.15, 0.2],
        manual_features=test_manual, combine_fn=combine_features
    )
    plot_robustness_results(robustness_results, OUTPUT_DIR)
    
    # 保存鲁棒性结果
    robustness_json = {}
    for model_name, res in robustness_results.items():
        robustness_json[model_name] = {str(k): v for k, v in res.items()}
    with open(os.path.join(OUTPUT_DIR, "robustness.json"), "w", encoding="utf-8") as f:
        json.dump(robustness_json, f, ensure_ascii=False, indent=2)
    
    # 保存LIME结果
    if lime_data:
        with open(os.path.join(OUTPUT_DIR, "lime_results.json"), "w", encoding="utf-8") as f:
            json.dump(lime_data, f, ensure_ascii=False, indent=2)
    
    # 保存SHAP结果
    if shap_data:
        with open(os.path.join(OUTPUT_DIR, "shap_results.json"), "w", encoding="utf-8") as f:
            json.dump(shap_data, f, ensure_ascii=False, indent=2)
    
    # ==================== 完成 ====================
    print("\n" + "=" * 70)
    print("  全部流程执行完毕！")
    print(f"  所有输出文件保存在: {OUTPUT_DIR}")
    print("=" * 70)
    print("\n生成的文件：")
    if os.path.exists(OUTPUT_DIR):
        for f in sorted(os.listdir(OUTPUT_DIR)):
            fpath = os.path.join(OUTPUT_DIR, f)
            size = os.path.getsize(fpath)
            print(f"  - {f} ({size:,} bytes)")


if __name__ == "__main__":
    main()
