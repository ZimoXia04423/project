"""
特征提取模块：TF-IDF特征 + 手工特征
"""
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from scipy.sparse import hstack, csr_matrix


def extract_tfidf_features(train_texts, test_texts, max_features=5000):
    """
    提取TF-IDF特征
    
    Parameters:
        train_texts: 训练集分词后的文本
        test_texts: 测试集分词后的文本
        max_features: 最大特征数
    
    Returns:
        X_train_tfidf, X_test_tfidf, vectorizer
    """
    vectorizer = TfidfVectorizer(max_features=max_features, ngram_range=(1, 2))
    X_train_tfidf = vectorizer.fit_transform(train_texts)
    X_test_tfidf = vectorizer.transform(test_texts)
    
    print(f"TF-IDF特征维度: {X_train_tfidf.shape[1]}")
    return X_train_tfidf, X_test_tfidf, vectorizer


def extract_manual_features(df):
    """
    提取手工特征（用户行为特征 + 文本统计特征）
    
    Returns:
        numpy array of manual features
    """
    features = df[["review_length", "exclamation_count", "repeat_char_ratio",
                    "sentiment_score", "user_review_count", 
                    "avg_review_interval_days", "rating"]].values
    return features


def combine_features(tfidf_features, manual_features):
    """将TF-IDF特征和手工特征合并"""
    manual_sparse = csr_matrix(manual_features)
    combined = hstack([tfidf_features, manual_sparse])
    print(f"合并后特征维度: {combined.shape[1]}")
    return combined
