"""
数据清洗模块：从数据库读取原始数据，进行清洗、去重、标注
实现完整的数据清洗管线（pipeline）
"""
import re
import logging
import pandas as pd
import numpy as np
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class DataCleaner:
    """评论数据清洗器"""
    
    def __init__(self, db):
        """
        初始化清洗器
        
        Parameters:
            db: ReviewDatabase实例
        """
        self.db = db
        self.stats = {
            "total_before": 0,
            "duplicates_removed": 0,
            "empty_removed": 0,
            "short_removed": 0,
            "invalid_removed": 0,
            "total_after": 0,
        }
    
    def run_pipeline(self, min_length=4):
        """
        执行完整的数据清洗管线
        
        Pipeline步骤：
        1. 去除重复评论
        2. 去除空白/无效评论
        3. 去除过短评论
        4. 文本规范化（去除特殊字符、统一格式）
        5. 标记清洗完成
        
        Parameters:
            min_length: 最短评论字数
        
        Returns:
            dict: 清洗统计信息
        """
        logger.info("=" * 60)
        logger.info("开始数据清洗管线")
        logger.info("=" * 60)
        
        # 获取总数据量
        with self.db.conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM reviews")
            self.stats["total_before"] = cursor.fetchone()[0]
        logger.info(f"清洗前总数据量: {self.stats['total_before']} 条")
        
        # Step 1: 去重
        self._step_remove_duplicates()
        
        # Step 2: 去除空白评论
        self._step_remove_empty()
        
        # Step 3: 去除过短评论
        self._step_remove_short(min_length)
        
        # Step 4: 文本规范化
        self._step_normalize_text()
        
        # Step 5: 标记已清洗
        self._step_mark_cleaned()
        
        # 统计结果
        with self.db.conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM reviews WHERE is_cleaned = 1 AND is_duplicate = 0")
            self.stats["total_after"] = cursor.fetchone()[0]
        
        # 记录清洗日志
        self._log_cleaning()
        
        logger.info(f"\n清洗完成: {self.stats['total_before']} → {self.stats['total_after']} 条")
        logger.info(f"  去重: {self.stats['duplicates_removed']} 条")
        logger.info(f"  去空白: {self.stats['empty_removed']} 条")
        logger.info(f"  去过短: {self.stats['short_removed']} 条")
        logger.info("=" * 60)
        
        return self.stats
    
    def _step_remove_duplicates(self):
        """Step 1: 基于评论文本去重"""
        logger.info("[Step 1] 去除重复评论...")
        count = self.db.mark_duplicates()
        self.stats["duplicates_removed"] = count
    
    def _step_remove_empty(self):
        """Step 2: 去除空白/无内容评论"""
        logger.info("[Step 2] 去除空白评论...")
        with self.db.conn.cursor() as cursor:
            cursor.execute("""
                UPDATE reviews SET is_duplicate = 1
                WHERE is_duplicate = 0 AND (
                    review_text IS NULL 
                    OR TRIM(review_text) = ''
                    OR review_text = '此用户未填写评价内容'
                    OR review_text = '默认好评'
                    OR review_text = '系统默认好评'
                )
            """)
            count = cursor.rowcount
        self.db.conn.commit()
        self.stats["empty_removed"] = count
        logger.info(f"  移除空白评论: {count} 条")
    
    def _step_remove_short(self, min_length):
        """Step 3: 去除过短评论"""
        logger.info(f"[Step 3] 去除过短评论 (最少{min_length}字)...")
        with self.db.conn.cursor() as cursor:
            cursor.execute("""
                UPDATE reviews SET is_duplicate = 1
                WHERE is_duplicate = 0 AND CHAR_LENGTH(TRIM(review_text)) < %s
            """, (min_length,))
            count = cursor.rowcount
        self.db.conn.commit()
        self.stats["short_removed"] = count
        logger.info(f"  移除过短评论: {count} 条")
    
    def _step_normalize_text(self):
        """Step 4: 文本规范化"""
        logger.info("[Step 4] 文本规范化...")
        with self.db.conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, review_text FROM reviews 
                WHERE is_duplicate = 0
            """)
            rows = cursor.fetchall()
            
            update_count = 0
            for row in rows:
                original = row[1]
                cleaned = self._normalize(original)
                if cleaned != original:
                    cursor.execute("UPDATE reviews SET review_text = %s WHERE id = %s",
                                 (cleaned, row[0]))
                    update_count += 1
        
        self.db.conn.commit()
        logger.info(f"  规范化处理: {update_count} 条评论被修正")
    
    def _normalize(self, text):
        """
        文本规范化处理
        - 去除多余空白
        - 全角转半角标点
        - 去除URL
        - 去除HTML标签
        - 去除连续重复标点
        """
        if not text:
            return ""
        # 去除HTML标签
        text = re.sub(r"<[^>]+>", "", text)
        # 去除URL
        text = re.sub(r"https?://\S+", "", text)
        # 去除多余空白
        text = re.sub(r"\s+", " ", text).strip()
        # 去除连续重复标点（超过3个）
        text = re.sub(r"([！!？?。，,\.]{3})[！!？?。，,\.]+", r"\1", text)
        return text
    
    def _step_mark_cleaned(self):
        """Step 5: 标记所有有效评论为已清洗"""
        with self.db.conn.cursor() as cursor:
            cursor.execute("""
                UPDATE reviews SET is_cleaned = 1
                WHERE is_duplicate = 0
            """)
        self.db.conn.commit()
        logger.info("[Step 5] 有效评论已标记为已清洗")
    
    def _log_cleaning(self):
        """记录清洗日志到数据库"""
        with self.db.conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO cleaning_logs 
                (total_before, duplicates_removed, empty_removed, short_removed,
                 total_after, cleaning_time)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                self.stats["total_before"],
                self.stats["duplicates_removed"],
                self.stats["empty_removed"],
                self.stats["short_removed"],
                self.stats["total_after"],
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ))
        self.db.conn.commit()
    
    def get_clean_dataframe(self):
        """
        获取清洗后的DataFrame，供后续建模使用
        
        Returns:
            pd.DataFrame: 清洗后的评论数据
        """
        df = self.db.export_to_dataframe(cleaned_only=True, exclude_duplicates=True)
        
        # 选择建模需要的列
        required_cols = [
            "review_text", "label", "rating",
            "review_length", "exclamation_count", "repeat_char_ratio",
            "sentiment_score", "user_review_count", "avg_review_interval_days",
        ]
        available_cols = [c for c in required_cols if c in df.columns]
        df = df[available_cols].copy()
        
        # 确保label列存在且有效
        if "label" in df.columns:
            df = df[df["label"].isin([0, 1])].reset_index(drop=True)
        
        logger.info(f"清洗后可用数据: {len(df)} 条 (真实: {(df['label']==0).sum()}, 虚假: {(df['label']==1).sum()})")
        return df
