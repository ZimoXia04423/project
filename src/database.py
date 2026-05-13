"""
数据库模块：使用MySQL实现评论数据的存储、查询与管理
采用规范化关系型数据库设计，包含5张表：
  - products:      商品信息表
  - users:         用户信息表
  - reviews:       评论主表（关联products和users）
  - crawl_logs:    爬取任务日志表
  - cleaning_logs: 数据清洗日志表
"""
import os
import logging
import pandas as pd
import pymysql
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# MySQL连接配置
MYSQL_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "wmr04423",
    "charset": "utf8mb4",
}
DB_NAME = "fake_review_detection"


class ReviewDatabase:
    """电商评论MySQL数据库管理器（5表关系型设计）"""
    
    def __init__(self, db_name=DB_NAME, config=None):
        """
        初始化MySQL数据库连接，自动创建数据库和表
        
        Parameters:
            db_name: 数据库名称
            config: MySQL连接配置字典
        """
        self.db_name = db_name
        self.config = config or MYSQL_CONFIG.copy()
        self._ensure_database()
        self.config["database"] = db_name
        self.conn = pymysql.connect(**self.config)
        self._create_tables()
        logger.info(f"MySQL数据库已连接: {self.config['host']}:{self.config['port']}/{db_name}")
    
    def _ensure_database(self):
        """确保目标数据库存在，不存在则创建"""
        conn = pymysql.connect(**self.config)
        try:
            with conn.cursor() as cursor:
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{self.db_name}` "
                             f"DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            conn.commit()
        finally:
            conn.close()
    
    def _create_tables(self):
        """创建5张数据库表及其关联关系"""
        with self.conn.cursor() as cursor:
            # 1. 商品信息表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    product_id VARCHAR(32) UNIQUE NOT NULL COMMENT '商品唯一编号',
                    product_name VARCHAR(256) COMMENT '商品名称',
                    category VARCHAR(64) COMMENT '商品类目',
                    shop_name VARCHAR(128) COMMENT '店铺名称',
                    price DECIMAL(10,2) COMMENT '商品价格',
                    total_sales INT DEFAULT 0 COMMENT '总销量',
                    platform VARCHAR(16) COMMENT '所属平台',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_category (category),
                    INDEX idx_platform (platform)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='商品信息表'
            """)
            
            # 2. 用户信息表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id VARCHAR(64) UNIQUE NOT NULL COMMENT '用户唯一编号',
                    nickname VARCHAR(64) COMMENT '用户昵称',
                    register_days INT DEFAULT 0 COMMENT '注册天数',
                    total_reviews INT DEFAULT 0 COMMENT '历史评论总数',
                    avg_rating DECIMAL(3,2) COMMENT '平均评分',
                    credit_level INT DEFAULT 0 COMMENT '信用等级(1-5)',
                    platform VARCHAR(16) COMMENT '所属平台',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_platform (platform)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户信息表'
            """)
            
            # 3. 评论主表（关联products和users）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reviews (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    review_id VARCHAR(64) UNIQUE NOT NULL COMMENT '评论唯一编号',
                    product_id VARCHAR(32) NOT NULL COMMENT '关联商品ID',
                    user_id VARCHAR(64) NOT NULL COMMENT '关联用户ID',
                    review_text TEXT NOT NULL COMMENT '评论正文',
                    rating INT COMMENT '评分(1-5)',
                    review_time VARCHAR(32) COMMENT '评论时间',
                    platform VARCHAR(16) COMMENT '来源平台',
                    crawl_time VARCHAR(32) COMMENT '爬取时间',
                    review_length INT COMMENT '评论字数',
                    exclamation_count INT COMMENT '感叹号数量',
                    repeat_char_ratio DOUBLE COMMENT '重复字符比例',
                    sentiment_score DOUBLE COMMENT '情感得分(0-1)',
                    user_review_count INT COMMENT '用户历史评论数',
                    avg_review_interval_days DOUBLE COMMENT '平均评论间隔天数',
                    label INT DEFAULT -1 COMMENT '标签(-1未标注,0真实,1虚假)',
                    is_cleaned TINYINT DEFAULT 0 COMMENT '是否已清洗',
                    is_duplicate TINYINT DEFAULT 0 COMMENT '是否重复',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_product_id (product_id),
                    INDEX idx_user_id (user_id),
                    INDEX idx_label (label),
                    INDEX idx_is_cleaned (is_cleaned),
                    INDEX idx_platform (platform),
                    CONSTRAINT fk_review_product FOREIGN KEY (product_id) 
                        REFERENCES products(product_id) ON DELETE CASCADE,
                    CONSTRAINT fk_review_user FOREIGN KEY (user_id) 
                        REFERENCES users(user_id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='评论主表'
            """)
            
            # 4. 爬取任务日志表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS crawl_logs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    task_name VARCHAR(64) COMMENT '任务名称',
                    platform VARCHAR(16) COMMENT '目标平台',
                    target_products INT COMMENT '目标商品数',
                    total_requests INT COMMENT '总请求数',
                    success_count INT COMMENT '成功请求数',
                    fail_count INT COMMENT '失败请求数',
                    total_reviews INT COMMENT '获取评论数',
                    start_time VARCHAR(32) COMMENT '开始时间',
                    end_time VARCHAR(32) COMMENT '结束时间',
                    status VARCHAR(16) DEFAULT 'completed' COMMENT '任务状态',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='爬取任务日志表'
            """)
            
            # 5. 数据清洗日志表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cleaning_logs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    total_before INT COMMENT '清洗前总数',
                    duplicates_removed INT COMMENT '去重删除数',
                    empty_removed INT COMMENT '空白删除数',
                    short_removed INT COMMENT '过短删除数',
                    total_after INT COMMENT '清洗后总数',
                    cleaning_time VARCHAR(32) COMMENT '清洗耗时',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='数据清洗日志表'
            """)
        
        self.conn.commit()
        logger.info("MySQL 5张表结构已创建/验证 (products, users, reviews, crawl_logs, cleaning_logs)")
    
    def clear_tables(self):
        """清空所有表数据（重新运行时使用，注意外键顺序）"""
        with self.conn.cursor() as cursor:
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
            cursor.execute("TRUNCATE TABLE reviews")
            cursor.execute("TRUNCATE TABLE users")
            cursor.execute("TRUNCATE TABLE products")
            cursor.execute("TRUNCATE TABLE crawl_logs")
            cursor.execute("TRUNCATE TABLE cleaning_logs")
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
        self.conn.commit()
        logger.info("已清空所有表数据")
    
    def insert_products(self, products):
        """
        批量插入商品数据
        
        Parameters:
            products: 商品数据列表
        
        Returns:
            int: 插入成功数
        """
        sql = """
            INSERT IGNORE INTO products 
            (product_id, product_name, category, shop_name, price, total_sales, platform)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        count = 0
        with self.conn.cursor() as cursor:
            for p in products:
                cursor.execute(sql, (
                    p["product_id"], p.get("product_name", ""),
                    p.get("category", ""), p.get("shop_name", ""),
                    p.get("price", 0), p.get("total_sales", 0),
                    p.get("platform", ""),
                ))
                count += cursor.rowcount
        self.conn.commit()
        logger.info(f"商品信息入库: {count} 条")
        return count
    
    def insert_users(self, users):
        """
        批量插入用户数据
        
        Parameters:
            users: 用户数据列表
        
        Returns:
            int: 插入成功数
        """
        sql = """
            INSERT IGNORE INTO users 
            (user_id, nickname, register_days, total_reviews, avg_rating, credit_level, platform)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        count = 0
        with self.conn.cursor() as cursor:
            for u in users:
                cursor.execute(sql, (
                    u["user_id"], u.get("nickname", ""),
                    u.get("register_days", 0), u.get("total_reviews", 0),
                    u.get("avg_rating", 0), u.get("credit_level", 0),
                    u.get("platform", ""),
                ))
                count += cursor.rowcount
        self.conn.commit()
        logger.info(f"用户信息入库: {count} 条")
        return count
    
    def insert_reviews(self, reviews):
        """
        批量插入评论数据（自动去重）
        
        Parameters:
            reviews: 评论数据列表
        
        Returns:
            tuple: (插入成功数, 重复跳过数)
        """
        inserted = 0
        duplicated = 0
        
        sql = """
            INSERT IGNORE INTO reviews 
            (review_id, product_id, user_id, review_text, rating, 
             review_time, platform, crawl_time,
             review_length, exclamation_count, repeat_char_ratio,
             sentiment_score, user_review_count, avg_review_interval_days, label)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        with self.conn.cursor() as cursor:
            for review in reviews:
                try:
                    cursor.execute(sql, (
                        review.get("review_id", ""),
                        review.get("product_id", ""),
                        review.get("user_id", ""),
                        review.get("review_text", ""),
                        review.get("rating", 0),
                        review.get("review_time", ""),
                        review.get("platform", ""),
                        review.get("crawl_time", ""),
                        review.get("review_length", 0),
                        review.get("exclamation_count", 0),
                        review.get("repeat_char_ratio", 0.0),
                        review.get("sentiment_score", 0.0),
                        review.get("user_review_count", 0),
                        review.get("avg_review_interval_days", 0.0),
                        review.get("label", -1),
                    ))
                    if cursor.rowcount > 0:
                        inserted += 1
                    else:
                        duplicated += 1
                except pymysql.Error as e:
                    logger.warning(f"  插入失败: {e}")
                    duplicated += 1
        
        self.conn.commit()
        logger.info(f"评论数据入库: 插入 {inserted} 条, 去重跳过 {duplicated} 条")
        return inserted, duplicated
    
    def log_crawl(self, stats, platform, target_products=0):
        """记录爬取任务日志"""
        sql = """
            INSERT INTO crawl_logs 
            (task_name, platform, target_products, total_requests, success_count, 
             fail_count, total_reviews, start_time, end_time, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        with self.conn.cursor() as cursor:
            cursor.execute(sql, (
                f"{platform}_评论采集",
                platform,
                target_products,
                stats.get("total_requests", 0),
                stats.get("success_count", 0),
                stats.get("fail_count", 0),
                stats.get("total_reviews", 0),
                stats.get("start_time", ""),
                stats.get("end_time", ""),
                "completed",
            ))
        self.conn.commit()
    
    def mark_duplicates(self):
        """标记重复评论（基于review_text完全匹配）"""
        with self.conn.cursor() as cursor:
            cursor.execute("""
                UPDATE reviews SET is_duplicate = 1
                WHERE id NOT IN (
                    SELECT min_id FROM (
                        SELECT MIN(id) AS min_id FROM reviews GROUP BY review_text
                    ) AS t
                ) AND is_duplicate = 0
            """)
            count = cursor.rowcount
        self.conn.commit()
        logger.info(f"标记重复评论: {count} 条")
        return count
    
    def get_reviews(self, cleaned_only=False, exclude_duplicates=True, 
                    platform=None, limit=None):
        """查询评论数据，返回DataFrame"""
        conditions = []
        params = []
        
        if cleaned_only:
            conditions.append("r.is_cleaned = 1")
        if exclude_duplicates:
            conditions.append("r.is_duplicate = 0")
        if platform:
            conditions.append("r.platform = %s")
            params.append(platform)
        
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        limit_clause = f" LIMIT {limit}" if limit else ""
        
        query = f"SELECT r.* FROM reviews r{where} ORDER BY r.id{limit_clause}"
        df = pd.read_sql_query(query, self.conn, params=params if params else None)
        return df
    
    def get_statistics(self):
        """获取数据库统计信息（含各表记录数）"""
        stats = {}
        
        with self.conn.cursor() as cursor:
            # 各表行数
            cursor.execute("SELECT COUNT(*) FROM products")
            stats["total_products"] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM users")
            stats["total_users"] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM reviews")
            stats["total_reviews"] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM reviews WHERE is_duplicate = 0")
            stats["unique_reviews"] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM reviews WHERE is_cleaned = 1")
            stats["cleaned_reviews"] = cursor.fetchone()[0]
            
            # 标签分布
            cursor.execute("""
                SELECT label, COUNT(*) as cnt FROM reviews 
                WHERE is_duplicate = 0 GROUP BY label
            """)
            label_counts = {}
            for row in cursor.fetchall():
                label_name = {0: "真实评论", 1: "虚假评论", -1: "未标注"}.get(row[0], f"标签{row[0]}")
                label_counts[label_name] = row[1]
            stats["label_distribution"] = label_counts
            
            # 平台分布
            cursor.execute("""
                SELECT platform, COUNT(*) as cnt FROM reviews 
                WHERE is_duplicate = 0 GROUP BY platform
            """)
            stats["platform_distribution"] = {row[0]: row[1] for row in cursor.fetchall()}
            
            # 评分分布
            cursor.execute("""
                SELECT rating, COUNT(*) as cnt FROM reviews 
                WHERE is_duplicate = 0 GROUP BY rating ORDER BY rating
            """)
            stats["rating_distribution"] = {str(row[0]): row[1] for row in cursor.fetchall()}
            
            # 爬取会话数
            cursor.execute("SELECT COUNT(*) FROM crawl_logs")
            stats["crawl_sessions"] = cursor.fetchone()[0]
        
        return stats
    
    def export_to_csv(self, filepath, cleaned_only=True, exclude_duplicates=True):
        """将评论数据导出为CSV"""
        df = self.get_reviews(cleaned_only=cleaned_only, 
                              exclude_duplicates=exclude_duplicates)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        df.to_csv(filepath, index=False, encoding="utf-8-sig")
        logger.info(f"数据已导出到 {filepath}，共 {len(df)} 条记录")
        return len(df)
    
    def export_to_dataframe(self, cleaned_only=True, exclude_duplicates=True):
        """将数据导出为DataFrame"""
        return self.get_reviews(cleaned_only=cleaned_only,
                                exclude_duplicates=exclude_duplicates)
    
    def close(self):
        """关闭数据库连接"""
        if self.conn and self.conn.open:
            self.conn.close()
            logger.info("MySQL数据库连接已关闭")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
