"""
文本预处理模块：分词、去停用词、文本清洗
"""
import re
import os
import jieba
import pandas as pd


def load_stopwords(filepath="data/stopwords.txt"):
    """加载停用词表"""
    stopwords = set()
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                stopwords.add(line.strip())
    return stopwords


def clean_text(text):
    """文本清洗：去除特殊字符、多余空格等"""
    text = re.sub(r"[^\u4e00-\u9fa5a-zA-Z0-9，。！？、；：""''（）\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def tokenize(text, stopwords=None):
    """中文分词并去停用词"""
    words = jieba.lcut(text)
    if stopwords:
        words = [w for w in words if w.strip() and w not in stopwords]
    else:
        words = [w for w in words if w.strip()]
    return words


def preprocess_dataframe(df, stopwords_path="data/stopwords.txt"):
    """
    对DataFrame进行完整的文本预处理
    
    Parameters:
        df: 包含review_text列的DataFrame
        stopwords_path: 停用词表路径
    
    Returns:
        处理后的DataFrame（新增clean_text和tokenized列）
    """
    stopwords = load_stopwords(stopwords_path)
    
    # 文本清洗
    df["clean_text"] = df["review_text"].apply(clean_text)
    
    # 分词
    df["tokenized"] = df["clean_text"].apply(lambda x: tokenize(x, stopwords))
    
    # 分词后的文本（空格连接，用于TF-IDF等）
    df["tokenized_text"] = df["tokenized"].apply(lambda x: " ".join(x))
    
    print(f"文本预处理完成，共处理 {len(df)} 条评论")
    return df


if __name__ == "__main__":
    test_texts = [
        "这个产品质量非常好！！！强烈推荐大家购买！",
        "一般般吧，没有想象中那么好",
    ]
    stopwords = load_stopwords()
    for text in test_texts:
        cleaned = clean_text(text)
        tokens = tokenize(cleaned, stopwords)
        print(f"原文: {text}")
        print(f"清洗: {cleaned}")
        print(f"分词: {tokens}")
        print()
