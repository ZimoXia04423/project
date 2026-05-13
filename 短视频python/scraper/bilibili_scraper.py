# -*- coding: utf-8 -*-
"""
B站数据抓取模块
基于Requests库调用B站公开API接口，采集热门排行榜视频信息及用户评论文本
设置请求间隔与异常重试机制保障采集稳定性
"""

import requests
import time
import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import BILIBILI_API, HEADERS, SCRAPER_CONFIG


def _request_with_retry(url, params=None):
    """带重试机制的HTTP GET请求"""
    max_retries = SCRAPER_CONFIG["max_retries"]
    retry_delay = SCRAPER_CONFIG["retry_delay"]
    timeout = SCRAPER_CONFIG["timeout"]

    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, headers=HEADERS, params=params, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") == 0:
                return data
            else:
                print(f"[Scraper] API返回错误码: {data.get('code')}, "
                      f"消息: {data.get('message')}, 第{attempt}次尝试")
        except requests.exceptions.RequestException as e:
            print(f"[Scraper] 请求异常: {e}, 第{attempt}次尝试")

        if attempt < max_retries:
            print(f"[Scraper] {retry_delay}秒后重试...")
            time.sleep(retry_delay)

    print(f"[Scraper] 请求失败，已达最大重试次数: {url}")
    return None


def fetch_ranking(rid=0):
    """
    获取B站热门排行榜视频列表
    rid: 分区ID，0表示全站排行
    返回: list of dict（视频基本信息列表）
    """
    print("[Scraper] 正在获取热门排行榜...")
    params = {"rid": rid, "type": "all"}
    data = _request_with_retry(BILIBILI_API["ranking"], params)

    if not data:
        return []

    crawl_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    video_list = data["data"]["list"]
    results = []

    for i, video in enumerate(video_list, 1):
        stat = video.get("stat", {})
        owner = video.get("owner", {})
        pub_ts = video.get("pubdate", 0)
        pub_date = datetime.fromtimestamp(pub_ts).strftime("%Y-%m-%d %H:%M:%S") if pub_ts else None

        video_info = {
            "rank_position": i,
            "bvid": video.get("bvid", ""),
            "aid": video.get("aid", 0),
            "title": video.get("title", ""),
            "author": owner.get("name", ""),
            "author_mid": owner.get("mid", 0),
            "tname": video.get("tname", ""),
            "tid": video.get("tid", 0),
            "description": video.get("desc", ""),
            "duration": video.get("duration", 0),
            "pub_date": pub_date,
            "view_count": stat.get("view", 0),
            "danmaku_count": stat.get("danmaku", 0),
            "like_count": stat.get("like", 0),
            "coin_count": stat.get("coin", 0),
            "favorite_count": stat.get("favorite", 0),
            "share_count": stat.get("share", 0),
            "reply_count": stat.get("reply", 0),
            "score": video.get("score", 0),
            "crawl_time": crawl_time,
        }
        results.append(video_info)

    print(f"[Scraper] 成功获取 {len(results)} 条排行榜视频数据")
    return results


def fetch_video_comments(bvid, aid, max_pages=None):
    """
    获取指定视频的评论数据
    bvid: 视频BV号
    aid: 视频AV号
    max_pages: 最大抓取页数
    返回: list of dict（评论列表）
    """
    if max_pages is None:
        max_pages = SCRAPER_CONFIG["comments_per_video"]
    ps = SCRAPER_CONFIG["comments_per_page"]
    crawl_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    interval = SCRAPER_CONFIG["request_interval"]

    all_comments = []

    for pn in range(1, max_pages + 1):
        params = {
            "type": 1,
            "oid": aid,
            "pn": pn,
            "ps": ps,
            "sort": 1,
        }
        data = _request_with_retry(BILIBILI_API["comments"], params)

        if not data:
            break

        replies = data.get("data", {}).get("replies") or []
        if not replies:
            break

        for reply in replies:
            member = reply.get("member", {})
            content_obj = reply.get("content", {})
            ctime = reply.get("ctime", 0)
            comment_time = datetime.fromtimestamp(ctime).strftime(
                "%Y-%m-%d %H:%M:%S") if ctime else None

            comment_info = {
                "bvid": bvid,
                "aid": aid,
                "rpid": reply.get("rpid", 0),
                "user_name": member.get("uname", ""),
                "user_mid": member.get("mid", 0),
                "content": content_obj.get("message", ""),
                "like_count": reply.get("like", 0),
                "reply_count": reply.get("rcount", 0),
                "comment_time": comment_time,
                "crawl_time": crawl_time,
            }
            all_comments.append(comment_info)

        if pn < max_pages:
            time.sleep(interval)

    return all_comments


def run_full_crawl():
    """
    执行完整的数据抓取流程：
    1. 抓取热门排行榜
    2. 逐个抓取视频评论
    返回: (videos_list, comments_list)
    """
    print("=" * 60)
    print("[Scraper] 开始执行完整数据抓取流程")
    print(f"[Scraper] 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    interval = SCRAPER_CONFIG["request_interval"]

    # 1. 抓取排行榜
    videos = fetch_ranking()
    if not videos:
        print("[Scraper] 排行榜获取失败，终止抓取")
        return [], []

    # 2. 抓取每个视频的评论
    all_comments = []
    total = len(videos)
    for idx, video in enumerate(videos, 1):
        bvid = video["bvid"]
        aid = video["aid"]
        title = video["title"][:30]
        print(f"[Scraper] ({idx}/{total}) 正在抓取评论: {title}...")

        comments = fetch_video_comments(bvid, aid)
        all_comments.extend(comments)
        print(f"[Scraper]   获取 {len(comments)} 条评论")

        time.sleep(interval)

    print("=" * 60)
    print(f"[Scraper] 抓取完成！视频: {len(videos)} 条, 评论: {len(all_comments)} 条")
    print(f"[Scraper] 结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    return videos, all_comments


if __name__ == "__main__":
    videos, comments = run_full_crawl()
    print(f"\n抓取结果: {len(videos)} 个视频, {len(comments)} 条评论")
