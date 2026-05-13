# -*- coding: utf-8 -*-
"""
数据清洗模块
利用Pandas完成数据格式标准化、去重和缺失值处理
"""

import pandas as pd
import numpy as np
import re
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def clean_videos(videos_raw):
    """
    清洗视频数据
    - 去除重复记录（同一次抓取中相同bvid）
    - 填充缺失值
    - 数值字段类型转换
    - 标题去除HTML标签
    """
    if not videos_raw:
        return []

    df = pd.DataFrame(videos_raw)

    # 去除HTML标签
    df["title"] = df["title"].apply(lambda x: re.sub(r"<[^>]+>", "", str(x)))
    df["description"] = df["description"].apply(lambda x: re.sub(r"<[^>]+>", "", str(x)) if pd.notna(x) else "")

    # 去重：同一crawl_time下相同bvid只保留第一条
    df.drop_duplicates(subset=["bvid", "crawl_time"], keep="first", inplace=True)

    # 填充缺失值
    str_cols = ["title", "author", "tname", "description", "bvid"]
    for col in str_cols:
        if col in df.columns:
            df[col] = df[col].fillna("")

    num_cols = ["view_count", "danmaku_count", "like_count", "coin_count",
                "favorite_count", "share_count", "reply_count", "duration",
                "aid", "author_mid", "tid"]
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    # score字段
    if "score" in df.columns:
        df["score"] = pd.to_numeric(df["score"], errors="coerce").fillna(0).astype(int)

    # 去除标题为空的记录
    df = df[df["title"].str.strip() != ""]

    print(f"[Cleaner] 视频数据清洗完成，有效记录: {len(df)} 条")
    return df.to_dict("records")


def clean_comments(comments_raw):
    """
    清洗评论数据
    - 去除重复评论（相同rpid）
    - 去除空内容评论
    - 去除HTML标签和特殊字符
    - 填充缺失值
    """
    if not comments_raw:
        return []

    df = pd.DataFrame(comments_raw)

    # 去除HTML标签
    df["content"] = df["content"].apply(lambda x: re.sub(r"<[^>]+>", "", str(x)))
    # 去除多余空白
    df["content"] = df["content"].apply(lambda x: re.sub(r"\s+", " ", x).strip())

    # 去重：相同rpid只保留第一条
    df.drop_duplicates(subset=["rpid"], keep="first", inplace=True)

    # 去除空内容
    df = df[df["content"].str.strip() != ""]

    # 填充缺失值
    df["user_name"] = df["user_name"].fillna("匿名用户")
    num_cols = ["like_count", "reply_count", "aid", "user_mid", "rpid"]
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    print(f"[Cleaner] 评论数据清洗完成，有效记录: {len(df)} 条")
    return df.to_dict("records")


def prepare_ranking_records(videos_cleaned):
    """
    从清洗后的视频数据中提取排行榜记录
    """
    records = []
    for v in videos_cleaned:
        records.append({
            "crawl_time": v["crawl_time"],
            "rank_position": v.get("rank_position", 0),
            "bvid": v["bvid"],
            "aid": v["aid"],
            "score": v.get("score", 0),
        })
    return records
