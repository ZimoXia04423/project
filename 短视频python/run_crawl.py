# -*- coding: utf-8 -*-
"""
数据抓取主程序
执行完整的数据采集流程：抓取 -> 清洗 -> 存储
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.db_init import init_database
from scraper.bilibili_scraper import run_full_crawl
from cleaner.data_cleaner import clean_videos, clean_comments, prepare_ranking_records
from database.db_operations import insert_ranking_records, insert_videos, insert_comments


def main():
    """主流程"""
    print("=" * 60)
    print("B站热点话题数据抓取与存储系统")
    print("=" * 60)

    # 1. 初始化数据库
    print("\n[Step 1] 初始化数据库...")
    try:
        init_database()
    except Exception as e:
        print(f"[Error] 数据库初始化失败: {e}")
        print("请检查MySQL服务是否启动，以及config.py中的数据库配置是否正确")
        return

    # 2. 执行数据抓取
    print("\n[Step 2] 开始数据抓取...")
    videos_raw, comments_raw = run_full_crawl()

    if not videos_raw:
        print("[Error] 未获取到任何视频数据，流程终止")
        return

    # 3. 数据清洗
    print("\n[Step 3] 执行数据清洗...")
    videos_cleaned = clean_videos(videos_raw)
    comments_cleaned = clean_comments(comments_raw)
    ranking_records = prepare_ranking_records(videos_cleaned)

    # 4. 存储到数据库（先插入视频主表，再插入外键关联的排行榜和评论表）
    print("\n[Step 4] 存储数据到MySQL...")
    v_count = insert_videos(videos_cleaned)
    print(f"  视频信息: 写入 {v_count} 条")

    r_count = insert_ranking_records(ranking_records)
    print(f"  排行榜记录: 写入 {r_count} 条")

    c_count = insert_comments(comments_cleaned)
    print(f"  评论数据: 写入 {c_count} 条")

    # 5. 完成
    print("\n" + "=" * 60)
    print("数据采集与存储完成！")
    print(f"  排行榜记录: {r_count} 条")
    print(f"  视频信息: {v_count} 条")
    print(f"  评论数据: {c_count} 条")
    print("=" * 60)
    print("\n提示: 运行 python app.py 启动Web可视化界面查看分析结果")


if __name__ == "__main__":
    main()
