# -*- coding: utf-8 -*-
"""
数据库操作模块
封装排行榜记录表、视频信息表、评论表的增删改查操作
"""

import pymysql
import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_CONFIG


def get_connection():
    """获取数据库连接"""
    return pymysql.connect(**DB_CONFIG)


# ============ 排行榜记录表操作 ============

def insert_ranking_records(records):
    """
    批量插入排行榜记录
    records: list of dict, 每条包含 crawl_time, rank_position, bvid, aid, score
    """
    if not records:
        return 0
    conn = get_connection()
    cursor = conn.cursor()
    sql = """
        INSERT INTO ranking_records (crawl_time, rank_position, bvid, aid, score)
        VALUES (%s, %s, %s, %s, %s)
    """
    count = 0
    try:
        for r in records:
            cursor.execute(sql, (
                r["crawl_time"], r["rank_position"], r["bvid"], r["aid"],
                r.get("score", 0)
            ))
            count += 1
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"[DB] 插入排行榜记录失败: {e}")
    finally:
        cursor.close()
        conn.close()
    return count


# ============ 视频信息表操作 ============

def insert_videos(videos):
    """
    批量插入视频信息
    videos: list of dict
    """
    if not videos:
        return 0
    conn = get_connection()
    cursor = conn.cursor()
    sql = """
        INSERT INTO videos (bvid, aid, title, author, author_mid, tname, tid,
            description, duration, pub_date, view_count, danmaku_count,
            like_count, coin_count, favorite_count, share_count, reply_count, crawl_time)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    count = 0
    try:
        for v in videos:
            cursor.execute(sql, (
                v["bvid"], v["aid"], v["title"], v.get("author", ""),
                v.get("author_mid", 0), v.get("tname", ""), v.get("tid", 0),
                v.get("description", ""), v.get("duration", 0),
                v.get("pub_date"), v.get("view_count", 0),
                v.get("danmaku_count", 0), v.get("like_count", 0),
                v.get("coin_count", 0), v.get("favorite_count", 0),
                v.get("share_count", 0), v.get("reply_count", 0),
                v["crawl_time"]
            ))
            count += 1
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"[DB] 插入视频信息失败: {e}")
    finally:
        cursor.close()
        conn.close()
    return count


# ============ 评论表操作 ============

def insert_comments(comments):
    """
    批量插入评论数据
    comments: list of dict
    """
    if not comments:
        return 0
    conn = get_connection()
    cursor = conn.cursor()
    sql = """
        INSERT INTO comments (bvid, aid, rpid, user_name, user_mid,
            content, like_count, reply_count, comment_time, crawl_time)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    count = 0
    try:
        for c in comments:
            cursor.execute(sql, (
                c["bvid"], c["aid"], c["rpid"], c.get("user_name", ""),
                c.get("user_mid", 0), c.get("content", ""),
                c.get("like_count", 0), c.get("reply_count", 0),
                c.get("comment_time"), c["crawl_time"]
            ))
            count += 1
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"[DB] 插入评论失败: {e}")
    finally:
        cursor.close()
        conn.close()
    return count


# ============ 查询操作 ============

def query_ranking_by_time(start_time=None, end_time=None, limit=100):
    """按时间范围查询排行榜记录"""
    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    sql = """
        SELECT r.*, v.title, v.author, v.view_count, v.like_count,
               v.coin_count, v.favorite_count, v.danmaku_count, v.reply_count, v.tname
        FROM ranking_records r
        LEFT JOIN videos v ON r.bvid = v.bvid
            AND r.crawl_time = v.crawl_time
        WHERE 1=1
    """
    params = []
    if start_time:
        sql += " AND r.crawl_time >= %s"
        params.append(start_time)
    if end_time:
        sql += " AND r.crawl_time <= %s"
        params.append(end_time)
    sql += " ORDER BY r.crawl_time DESC, r.rank_position ASC LIMIT %s"
    params.append(limit)

    cursor.execute(sql, params)
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return results


def query_videos(start_time=None, end_time=None, tname=None, keyword=None, limit=100):
    """多条件查询视频信息"""
    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    sql = "SELECT * FROM videos WHERE 1=1"
    params = []
    if start_time:
        sql += " AND crawl_time >= %s"
        params.append(start_time)
    if end_time:
        sql += " AND crawl_time <= %s"
        params.append(end_time)
    if tname:
        sql += " AND tname = %s"
        params.append(tname)
    if keyword:
        sql += " AND title LIKE %s"
        params.append(f"%{keyword}%")
    sql += " ORDER BY view_count DESC LIMIT %s"
    params.append(limit)

    cursor.execute(sql, params)
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return results


def query_comments_by_bvid(bvid, limit=500):
    """查询指定视频的评论"""
    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    sql = "SELECT * FROM comments WHERE bvid = %s ORDER BY like_count DESC LIMIT %s"
    cursor.execute(sql, (bvid, limit))
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return results


def query_all_comments(start_time=None, end_time=None, limit=2000):
    """查询时间范围内的所有评论"""
    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    sql = "SELECT * FROM comments WHERE 1=1"
    params = []
    if start_time:
        sql += " AND crawl_time >= %s"
        params.append(start_time)
    if end_time:
        sql += " AND crawl_time <= %s"
        params.append(end_time)
    sql += " ORDER BY crawl_time DESC LIMIT %s"
    params.append(limit)
    cursor.execute(sql, params)
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return results


def get_crawl_times():
    """获取所有不同的抓取时间（用于前端筛选）"""
    conn = get_connection()
    cursor = conn.cursor()
    sql = "SELECT DISTINCT crawl_time FROM ranking_records ORDER BY crawl_time DESC"
    cursor.execute(sql)
    results = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return results


def get_video_trend(bvid):
    """获取指定视频在不同抓取时间的数据变化（趋势分析）"""
    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    sql = """
        SELECT crawl_time, view_count, like_count, danmaku_count,
               coin_count, favorite_count, reply_count
        FROM videos WHERE bvid = %s ORDER BY crawl_time ASC
    """
    cursor.execute(sql, (bvid,))
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return results


def get_video_count():
    """获取视频总数（高效COUNT查询）"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM videos")
    count = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return count


def get_comment_count():
    """获取评论总数（高效COUNT查询）"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM comments")
    count = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return count


def get_video_title_by_bvid(bvid):
    """通过bvid获取视频标题（精确查询，避免全表扫描）"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT title FROM videos WHERE bvid = %s LIMIT 1", (bvid,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row[0] if row else ""


def get_all_tnames():
    """获取所有分区名称"""
    conn = get_connection()
    cursor = conn.cursor()
    sql = "SELECT DISTINCT tname FROM videos WHERE tname IS NOT NULL AND tname != '' ORDER BY tname"
    cursor.execute(sql)
    results = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return results


def get_top_videos(start_time=None, end_time=None, order_by="view_count", limit=20):
    """获取热度排名前N的视频"""
    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    allowed_cols = ["view_count", "like_count", "coin_count", "danmaku_count",
                    "favorite_count", "reply_count"]
    if order_by not in allowed_cols:
        order_by = "view_count"

    sql = f"SELECT * FROM videos WHERE 1=1"
    params = []
    if start_time:
        sql += " AND crawl_time >= %s"
        params.append(start_time)
    if end_time:
        sql += " AND crawl_time <= %s"
        params.append(end_time)
    sql += f" ORDER BY {order_by} DESC LIMIT %s"
    params.append(limit)

    cursor.execute(sql, params)
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return results
