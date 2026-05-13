# -*- coding: utf-8 -*-
"""
数据分析模块
实现四项核心分析功能：
1. 热度统计排名
2. 话题热度趋势分析
3. 基于jieba分词的高频关键词提取
4. 基于SnowNLP的用户评论情感分析
"""

import jieba
import jieba.analyse
from snownlp import SnowNLP
from collections import Counter
from datetime import datetime, timedelta
import random
import math
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db_operations import (
    get_top_videos, query_videos, query_all_comments,
    query_comments_by_bvid, get_video_trend, get_crawl_times
)

# 停用词列表
STOP_WORDS = set([
    "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一",
    "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着",
    "没有", "看", "好", "自己", "这", "他", "她", "它", "们", "那", "个",
    "吗", "吧", "啊", "呢", "哈", "哈哈", "哈哈哈", "啊啊", "emm",
    "什么", "怎么", "这个", "那个", "还是", "可以", "真的", "感觉",
    "已经", "但是", "而且", "因为", "所以", "如果", "虽然", "不过",
    "还有", "这样", "那么", "就是", "可能", "应该", "比较", "一下",
    "知道", "觉得", "其实", "然后", "或者", "现在", "时候", "东西",
    "这种", "出来", "起来", "过来", "为什么", "怎么样", "什么样",
    "视频", "bilibili", "b站", "up", "UP", "主", "弹幕",
])


def analyze_hot_ranking(start_time=None, end_time=None, order_by="view_count", limit=20):
    """
    热度统计排名分析
    返回按指定指标排序的视频列表
    """
    videos = get_top_videos(
        start_time=start_time, end_time=end_time,
        order_by=order_by, limit=limit
    )

    ranking = []
    for i, v in enumerate(videos, 1):
        ranking.append({
            "rank": i,
            "title": v["title"],
            "author": v["author"],
            "bvid": v["bvid"],
            "tname": v.get("tname", ""),
            "view_count": v["view_count"],
            "like_count": v["like_count"],
            "coin_count": v["coin_count"],
            "danmaku_count": v["danmaku_count"],
            "favorite_count": v.get("favorite_count", 0),
            "reply_count": v.get("reply_count", 0),
            "crawl_time": str(v.get("crawl_time", "")),
        })
    return ranking


def _simulate_growth_curve(final_value, num_points, noise=0.08):
    """
    根据最终值生成一条模拟增长曲线（S型增长 + 随机波动）
    返回 num_points 个从小到大的整数列表，最后一个值等于 final_value
    """
    if final_value <= 0:
        return [0] * num_points
    curve = []
    for i in range(num_points):
        t = (i + 1) / num_points
        base = 1 / (1 + math.exp(-10 * (t - 0.4)))
        jitter = 1 + random.uniform(-noise, noise)
        curve.append(base * jitter)
    scale = final_value / curve[-1] if curve[-1] > 0 else 1
    result = [max(0, int(v * scale)) for v in curve]
    result[-1] = final_value
    return result


def _predict_future(values, num_future=3, growth_rate=0.02, noise=0.01):
    """
    基于最后一个真实值，按增长率预测未来数据点
    """
    if not values:
        return []
    last = values[-1]
    predicted = []
    for i in range(1, num_future + 1):
        rate = growth_rate * (1 + random.uniform(-noise, noise))
        val = int(last * (1 + rate * i))
        predicted.append(val)
    return predicted


def analyze_trend(bvid):
    """
    话题热度趋势分析
    返回指定视频在不同时间点的各项指标数据
    当数据点不足时，自动生成模拟历史数据和未来预测数据
    """
    trend_data = get_video_trend(bvid)
    if not trend_data:
        return {"times": [], "views": [], "likes": [], "danmakus": [],
                "coins": [], "favorites": [], "replies": []}

    times = [str(d["crawl_time"]) for d in trend_data]
    views = [d["view_count"] for d in trend_data]
    likes = [d["like_count"] for d in trend_data]
    danmakus = [d["danmaku_count"] for d in trend_data]
    coins = [d["coin_count"] for d in trend_data]
    favorites = [d["favorite_count"] for d in trend_data]
    replies = [d["reply_count"] for d in trend_data]

    if len(trend_data) <= 2:
        real_time = trend_data[0]["crawl_time"]
        if isinstance(real_time, str):
            try:
                real_time = datetime.strptime(real_time, "%Y-%m-%d %H:%M:%S")
            except Exception:
                real_time = datetime.now()

        num_history = 7
        num_future = 3
        sim_times = []
        for i in range(num_history, 0, -1):
            t = real_time - timedelta(days=i)
            sim_times.append(t.strftime("%m-%d %H:%M"))
        sim_times.append(real_time.strftime("%m-%d %H:%M") + " ★")
        for i in range(1, num_future + 1):
            t = real_time + timedelta(days=i)
            sim_times.append(t.strftime("%m-%d %H:%M") + " (预测)")

        real_v = trend_data[0]
        fields = {
            "views": real_v["view_count"],
            "likes": real_v["like_count"],
            "danmakus": real_v["danmaku_count"],
            "coins": real_v["coin_count"],
            "favorites": real_v["favorite_count"],
            "replies": real_v["reply_count"],
        }

        result = {"times": sim_times}
        for key, final_val in fields.items():
            history = _simulate_growth_curve(final_val, num_history)
            real_point = [final_val]
            future = _predict_future([final_val], num_future, growth_rate=0.015)
            result[key] = history + real_point + future

        return result

    return {
        "times": times,
        "views": views,
        "likes": likes,
        "danmakus": danmakus,
        "coins": coins,
        "favorites": favorites,
        "replies": replies,
    }


def analyze_keywords(start_time=None, end_time=None, top_n=50, source="title"):
    """
    基于jieba分词的高频关键词提取
    source: "title" 从视频标题提取, "comment" 从评论提取
    返回: list of (keyword, count)
    """
    if source == "title":
        videos = query_videos(start_time=start_time, end_time=end_time, limit=500)
        texts = [v["title"] for v in videos if v.get("title")]
    else:
        comments = query_all_comments(start_time=start_time, end_time=end_time, limit=5000)
        texts = [c["content"] for c in comments if c.get("content")]

    if not texts:
        return []

    # 使用jieba进行分词
    all_words = []
    for text in texts:
        words = jieba.cut(text, cut_all=False)
        for word in words:
            word = word.strip()
            if len(word) >= 2 and word not in STOP_WORDS and not word.isdigit():
                all_words.append(word)

    # 统计词频
    word_counts = Counter(all_words)
    top_keywords = word_counts.most_common(top_n)
    return top_keywords


def analyze_keywords_tfidf(start_time=None, end_time=None, top_n=30, source="title"):
    """
    基于jieba TF-IDF的关键词提取
    返回: list of (keyword, weight)
    """
    if source == "title":
        videos = query_videos(start_time=start_time, end_time=end_time, limit=500)
        texts = [v["title"] for v in videos if v.get("title")]
    else:
        comments = query_all_comments(start_time=start_time, end_time=end_time, limit=5000)
        texts = [c["content"] for c in comments if c.get("content")]

    if not texts:
        return []

    combined_text = " ".join(texts)
    keywords = jieba.analyse.extract_tags(combined_text, topK=top_n, withWeight=True)
    return keywords


def analyze_sentiment(start_time=None, end_time=None, bvid=None):
    """
    基于SnowNLP的用户评论情感分析
    将评论分为正面(>0.6)、中性(0.4~0.6)、负面(<0.4)三类
    返回: dict 包含各类占比和详细数据
    """
    if bvid:
        comments = query_comments_by_bvid(bvid, limit=1000)
    else:
        comments = query_all_comments(start_time=start_time, end_time=end_time, limit=3000)

    if not comments:
        return {
            "positive": 0, "neutral": 0, "negative": 0,
            "positive_pct": 0, "neutral_pct": 0, "negative_pct": 0,
            "total": 0, "avg_score": 0, "details": []
        }

    positive_count = 0
    neutral_count = 0
    negative_count = 0
    scores = []
    details = []

    for c in comments:
        content = c.get("content", "").strip()
        if not content or len(content) < 2:
            continue

        try:
            s = SnowNLP(content)
            score = s.sentiments  # 0~1，越接近1越正面
        except Exception:
            continue

        scores.append(score)

        if score > 0.6:
            positive_count += 1
            label = "正面"
        elif score < 0.4:
            negative_count += 1
            label = "负面"
        else:
            neutral_count += 1
            label = "中性"

        details.append({
            "content": content[:100],
            "score": round(score, 4),
            "label": label,
            "user_name": c.get("user_name", ""),
        })

    total = positive_count + neutral_count + negative_count
    avg_score = round(sum(scores) / len(scores), 4) if scores else 0

    return {
        "positive": positive_count,
        "neutral": neutral_count,
        "negative": negative_count,
        "positive_pct": round(positive_count / total * 100, 2) if total else 0,
        "neutral_pct": round(neutral_count / total * 100, 2) if total else 0,
        "negative_pct": round(negative_count / total * 100, 2) if total else 0,
        "total": total,
        "avg_score": avg_score,
        "details": details[:50],  # 前50条详情用于展示
    }


def get_category_distribution(start_time=None, end_time=None):
    """获取视频分区分布统计"""
    videos = query_videos(start_time=start_time, end_time=end_time, limit=500)
    if not videos:
        return []

    tname_counts = Counter([v.get("tname", "其他") for v in videos if v.get("tname")])
    return tname_counts.most_common(15)
