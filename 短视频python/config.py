# -*- coding: utf-8 -*-
"""
系统配置文件
包含数据库连接、API请求、Flask应用等配置项
"""

# MySQL数据库配置
DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "123456",     # 请根据实际情况修改
    "database": "bilibili_hotspot",
    "charset": "utf8mb4",
}

# B站API配置
BILIBILI_API = {
    "ranking": "https://api.bilibili.com/x/web-interface/ranking/v2",
    "video_detail": "https://api.bilibili.com/x/web-interface/view",
    "comments": "https://api.bilibili.com/x/v2/reply",
    "hot_search": "https://app.bilibili.com/x/v2/search/trending/ranking",
}

# 请求头
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.bilibili.com",
}

# 爬虫配置
SCRAPER_CONFIG = {
    "request_interval": 1.5,    # 请求间隔（秒）
    "max_retries": 3,           # 最大重试次数
    "retry_delay": 3,           # 重试等待时间（秒）
    "timeout": 15,              # 请求超时时间（秒）
    "comments_per_video": 3,    # 每个视频抓取评论页数
    "comments_per_page": 20,    # 每页评论条数
}

# Flask应用配置
FLASK_CONFIG = {
    "SECRET_KEY": "bilibili_hotspot_analysis_2024",
    "DEBUG": True,
    "HOST": "0.0.0.0",
    "PORT": 5000,
}
