# -*- coding: utf-8 -*-
"""
数据库初始化模块
创建数据库和三张核心数据表：排行榜记录表、视频信息表、评论表
"""

import pymysql
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_CONFIG


def create_database():
    """创建数据库（如果不存在）"""
    conn = pymysql.connect(
        host=DB_CONFIG["host"],
        port=DB_CONFIG["port"],
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"],
        charset=DB_CONFIG["charset"],
    )
    cursor = conn.cursor()
    cursor.execute(
        f"CREATE DATABASE IF NOT EXISTS `{DB_CONFIG['database']}` "
        f"DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    )
    conn.commit()
    cursor.close()
    conn.close()
    print(f"[DB] 数据库 '{DB_CONFIG['database']}' 已就绪")


def create_tables():
    """创建三张核心数据表"""
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()

    # 视频信息表（主表，其他表通过外键引用）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS `videos` (
            `id` INT AUTO_INCREMENT PRIMARY KEY,
            `bvid` VARCHAR(20) NOT NULL COMMENT '视频BV号',
            `aid` BIGINT NOT NULL COMMENT '视频AV号',
            `title` VARCHAR(500) NOT NULL COMMENT '视频标题',
            `author` VARCHAR(100) COMMENT 'UP主名称',
            `author_mid` BIGINT COMMENT 'UP主ID',
            `tname` VARCHAR(50) COMMENT '分区名称',
            `tid` INT COMMENT '分区ID',
            `description` TEXT COMMENT '视频简介',
            `duration` INT DEFAULT 0 COMMENT '时长(秒)',
            `pub_date` DATETIME COMMENT '发布时间',
            `view_count` INT DEFAULT 0 COMMENT '播放量',
            `danmaku_count` INT DEFAULT 0 COMMENT '弹幕数',
            `like_count` INT DEFAULT 0 COMMENT '点赞数',
            `coin_count` INT DEFAULT 0 COMMENT '投币数',
            `favorite_count` INT DEFAULT 0 COMMENT '收藏数',
            `share_count` INT DEFAULT 0 COMMENT '分享数',
            `reply_count` INT DEFAULT 0 COMMENT '评论数',
            `crawl_time` DATETIME NOT NULL COMMENT '抓取时间',
            `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX `idx_crawl_time` (`crawl_time`),
            INDEX `idx_tname` (`tname`),
            INDEX `idx_view_count` (`view_count`),
            UNIQUE KEY `uk_bvid_crawl` (`bvid`, `crawl_time`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='视频信息表';
    """)

    # 排行榜记录表（通过外键关联视频表）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS `ranking_records` (
            `id` INT AUTO_INCREMENT PRIMARY KEY,
            `crawl_time` DATETIME NOT NULL COMMENT '抓取时间',
            `rank_position` INT NOT NULL COMMENT '排名位置',
            `bvid` VARCHAR(20) NOT NULL COMMENT '视频BV号',
            `aid` BIGINT NOT NULL COMMENT '视频AV号',
            `score` INT DEFAULT 0 COMMENT '综合得分',
            `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX `idx_crawl_time` (`crawl_time`),
            INDEX `idx_bvid` (`bvid`),
            CONSTRAINT `fk_ranking_video` FOREIGN KEY (`bvid`, `crawl_time`)
                REFERENCES `videos` (`bvid`, `crawl_time`)
                ON DELETE CASCADE ON UPDATE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='排行榜记录表';
    """)

    # 评论表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS `comments` (
            `id` INT AUTO_INCREMENT PRIMARY KEY,
            `bvid` VARCHAR(20) NOT NULL COMMENT '所属视频BV号',
            `aid` BIGINT NOT NULL COMMENT '所属视频AV号',
            `rpid` BIGINT NOT NULL COMMENT '评论ID',
            `user_name` VARCHAR(100) COMMENT '评论用户名',
            `user_mid` BIGINT COMMENT '评论用户ID',
            `content` TEXT COMMENT '评论内容',
            `like_count` INT DEFAULT 0 COMMENT '评论点赞数',
            `reply_count` INT DEFAULT 0 COMMENT '回复数',
            `comment_time` DATETIME COMMENT '评论时间',
            `crawl_time` DATETIME NOT NULL COMMENT '抓取时间',
            `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX `idx_bvid` (`bvid`),
            INDEX `idx_rpid` (`rpid`),
            INDEX `idx_crawl_time` (`crawl_time`),
            CONSTRAINT `fk_comment_video` FOREIGN KEY (`bvid`, `crawl_time`)
                REFERENCES `videos` (`bvid`, `crawl_time`)
                ON DELETE CASCADE ON UPDATE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='评论表';
    """)

    conn.commit()
    cursor.close()
    conn.close()
    print("[DB] 三张核心数据表已创建完成")


def init_database():
    """初始化数据库（创建库+建表）"""
    create_database()
    create_tables()
    print("[DB] 数据库初始化完成")


if __name__ == "__main__":
    init_database()
