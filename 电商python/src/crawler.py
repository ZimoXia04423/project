"""
数据爬取模块：电商平台用户评论数据抓取
支持多平台评论抓取，包含完整的反爬策略
注：实际运行时使用本地模拟数据源，避免法律风险
"""
import requests
import time
import random
import json
import os
import logging
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class AntiCrawlStrategy:
    """反爬虫策略管理器"""
    
    # 常用User-Agent列表，模拟不同浏览器
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    ]
    
    # IP代理池（示例，实际使用需替换为有效代理）
    PROXY_POOL = [
        # {"http": "http://proxy1:port", "https": "https://proxy1:port"},
        # {"http": "http://proxy2:port", "https": "https://proxy2:port"},
    ]
    
    def __init__(self, min_delay=1.0, max_delay=3.0):
        """
        初始化反爬策略
        
        Parameters:
            min_delay: 最小请求间隔（秒）
            max_delay: 最大请求间隔（秒）
        """
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.request_count = 0
        self.last_request_time = 0
    
    def get_random_headers(self):
        """生成随机请求头，模拟真实浏览器行为"""
        return {
            "User-Agent": random.choice(self.USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Cache-Control": "max-age=0",
            "Referer": "https://www.taobao.com/",
        }
    
    def get_random_proxy(self):
        """从代理池中随机选取一个代理"""
        if self.PROXY_POOL:
            return random.choice(self.PROXY_POOL)
        return None
    
    def wait(self):
        """智能等待，控制请求频率避免触发反爬"""
        elapsed = time.time() - self.last_request_time
        delay = random.uniform(self.min_delay, self.max_delay)
        
        # 每10次请求额外等待，模拟人工浏览行为
        if self.request_count > 0 and self.request_count % 10 == 0:
            delay += random.uniform(3, 8)
            logger.info(f"  已完成{self.request_count}次请求，额外等待 {delay:.1f}s 避免封禁")
        
        if elapsed < delay:
            time.sleep(delay - elapsed)
        
        self.last_request_time = time.time()
        self.request_count += 1


class EcommerceReviewCrawler:
    """
    电商平台评论爬虫
    
    支持的平台（框架设计）：
    - 淘宝/天猫 (taobao)
    - 京东 (jd)
    - 拼多多 (pdd)
    
    注：由于合规要求，实际运行时使用本地模拟数据源
    """
    
    # 平台API端点配置（示例结构）
    PLATFORM_CONFIG = {
        "taobao": {
            "base_url": "https://rate.taobao.com/feedRateList.htm",
            "params_template": {
                "auctionNumId": "{product_id}",
                "currentPageNum": "{page}",
                "pageSize": 20,
                "orderType": "feedbackdate",
            },
        },
        "jd": {
            "base_url": "https://club.jd.com/comment/productPageComments.action",
            "params_template": {
                "productId": "{product_id}",
                "score": 0,  # 0=全部, 1=差评, 3=好评
                "sortType": 6,  # 按时间排序
                "page": "{page}",
                "pageSize": 10,
            },
        },
        "pdd": {
            "base_url": "https://mobile.yangkeduo.com/proxy/api/reviews",
            "params_template": {
                "goods_id": "{product_id}",
                "page": "{page}",
                "size": 20,
            },
        },
    }
    
    def __init__(self, platform="taobao", use_local=True):
        """
        初始化爬虫
        
        Parameters:
            platform: 目标平台 ('taobao', 'jd', 'pdd')
            use_local: 是否使用本地模拟数据（合规模式）
        """
        self.platform = platform
        self.use_local = use_local
        self.anti_crawl = AntiCrawlStrategy(min_delay=1.5, max_delay=4.0)
        self.session = requests.Session()
        self.crawl_stats = {
            "total_requests": 0,
            "success_count": 0,
            "fail_count": 0,
            "total_reviews": 0,
            "start_time": None,
            "end_time": None,
        }
        logger.info(f"爬虫初始化完成 | 平台: {platform} | 模式: {'本地模拟' if use_local else '在线抓取'}")
    
    def _make_request(self, url, params=None):
        """
        发送HTTP请求（含重试机制）
        
        Parameters:
            url: 请求URL
            params: 请求参数
        
        Returns:
            dict: 响应JSON数据
        """
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.anti_crawl.wait()
                headers = self.anti_crawl.get_random_headers()
                proxy = self.anti_crawl.get_random_proxy()
                
                response = self.session.get(
                    url, params=params, headers=headers,
                    proxies=proxy, timeout=15
                )
                response.raise_for_status()
                self.crawl_stats["success_count"] += 1
                self.crawl_stats["total_requests"] += 1
                return response.json()
            except requests.exceptions.RequestException as e:
                self.crawl_stats["fail_count"] += 1
                self.crawl_stats["total_requests"] += 1
                logger.warning(f"  请求失败 (第{attempt+1}次): {e}")
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 5
                    logger.info(f"  等待 {wait_time}s 后重试...")
                    time.sleep(wait_time)
        return None
    
    def _parse_review(self, raw_review, platform):
        """
        解析原始评论数据为统一格式
        
        Parameters:
            raw_review: 原始评论字典
            platform: 平台名称
        
        Returns:
            dict: 统一格式的评论数据
        """
        if platform == "taobao":
            return {
                "review_id": raw_review.get("id", ""),
                "product_id": raw_review.get("auctionSku", ""),
                "user_id": raw_review.get("user", {}).get("nick", ""),
                "review_text": raw_review.get("content", ""),
                "rating": raw_review.get("rate", 5),
                "review_time": raw_review.get("date", ""),
                "platform": "taobao",
                "crawl_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        elif platform == "jd":
            return {
                "review_id": str(raw_review.get("id", "")),
                "product_id": str(raw_review.get("productId", "")),
                "user_id": raw_review.get("nickname", ""),
                "review_text": raw_review.get("content", ""),
                "rating": raw_review.get("score", 5),
                "review_time": raw_review.get("creationTime", ""),
                "platform": "jd",
                "crawl_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        else:
            return {
                "review_id": str(raw_review.get("id", "")),
                "product_id": str(raw_review.get("goods_id", "")),
                "user_id": raw_review.get("user_name", ""),
                "review_text": raw_review.get("comment", ""),
                "rating": raw_review.get("rating", 5),
                "review_time": raw_review.get("time", ""),
                "platform": platform,
                "crawl_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
    
    def crawl_product_reviews(self, product_id, max_pages=5):
        """
        抓取指定商品的评论数据
        
        Parameters:
            product_id: 商品ID
            max_pages: 最大抓取页数
        
        Returns:
            list: 评论数据列表
        """
        if self.use_local:
            return self._crawl_local_simulation(product_id, max_pages)
        
        config = self.PLATFORM_CONFIG.get(self.platform)
        if not config:
            logger.error(f"不支持的平台: {self.platform}")
            return []
        
        all_reviews = []
        for page in range(1, max_pages + 1):
            logger.info(f"  正在抓取第 {page}/{max_pages} 页评论...")
            
            params = {}
            for k, v in config["params_template"].items():
                if isinstance(v, str):
                    params[k] = v.replace("{product_id}", str(product_id)).replace("{page}", str(page))
                else:
                    params[k] = v
            
            data = self._make_request(config["base_url"], params)
            if not data:
                logger.warning(f"  第{page}页抓取失败，跳过")
                continue
            
            reviews = self._extract_reviews_from_response(data)
            if not reviews:
                logger.info(f"  第{page}页无更多评论，结束抓取")
                break
            
            for r in reviews:
                parsed = self._parse_review(r, self.platform)
                all_reviews.append(parsed)
            
            logger.info(f"  第{page}页获取 {len(reviews)} 条评论")
        
        self.crawl_stats["total_reviews"] += len(all_reviews)
        return all_reviews
    
    def _extract_reviews_from_response(self, data):
        """从API响应中提取评论列表"""
        if self.platform == "taobao":
            return data.get("comments", [])
        elif self.platform == "jd":
            return data.get("comments", [])
        else:
            return data.get("data", {}).get("list", [])
    
    def _crawl_local_simulation(self, product_id, max_pages):
        """
        本地模拟爬取（合规模式）
        使用data_generator生成的数据模拟爬虫抓取过程
        """
        from src.data_generator import generate_dataset
        
        logger.info(f"[合规模式] 使用本地模拟数据源替代在线抓取")
        logger.info(f"  模拟抓取商品 {product_id} 的评论...")
        
        # 模拟生成数据
        n_per_page = 20
        total_reviews = n_per_page * max_pages
        df = generate_dataset(n_samples=total_reviews, random_seed=hash(product_id) % 10000)
        
        all_reviews = []
        for page in range(max_pages):
            # 模拟网络延迟
            delay = random.uniform(0.1, 0.3)
            time.sleep(delay)
            
            start_idx = page * n_per_page
            end_idx = min(start_idx + n_per_page, len(df))
            page_df = df.iloc[start_idx:end_idx]
            
            self.crawl_stats["success_count"] += 1
            self.crawl_stats["total_requests"] += 1
            
            for _, row in page_df.iterrows():
                review = {
                    "review_id": f"R{product_id}_{random.randint(100000, 999999)}",
                    "product_id": str(product_id),
                    "user_id": f"user_{random.randint(10000, 99999)}",
                    "review_text": row["review_text"],
                    "rating": int(row["rating"]),
                    "review_time": (datetime.now() - timedelta(
                        days=random.randint(1, 365)
                    )).strftime("%Y-%m-%d %H:%M:%S"),
                    "platform": self.platform,
                    "crawl_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "review_length": int(row["review_length"]),
                    "exclamation_count": int(row["exclamation_count"]),
                    "repeat_char_ratio": float(row["repeat_char_ratio"]),
                    "sentiment_score": float(row["sentiment_score"]),
                    "user_review_count": int(row["user_review_count"]),
                    "avg_review_interval_days": float(row["avg_review_interval_days"]),
                    "label": int(row["label"]),
                }
                all_reviews.append(review)
            
            logger.info(f"  第 {page+1}/{max_pages} 页: 获取 {len(page_df)} 条评论 (延迟 {delay:.2f}s)")
        
        self.crawl_stats["total_reviews"] += len(all_reviews)
        return all_reviews
    
    def crawl_multiple_products(self, product_ids, max_pages_per_product=5):
        """
        批量抓取多个商品的评论
        
        Parameters:
            product_ids: 商品ID列表
            max_pages_per_product: 每个商品最大抓取页数
        
        Returns:
            list: 所有评论数据
        """
        self.crawl_stats["start_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        all_reviews = []
        
        for i, pid in enumerate(product_ids):
            logger.info(f"正在抓取商品 [{i+1}/{len(product_ids)}]: {pid}")
            reviews = self.crawl_product_reviews(pid, max_pages_per_product)
            all_reviews.extend(reviews)
            logger.info(f"  商品 {pid} 抓取完成，获取 {len(reviews)} 条评论")
        
        self.crawl_stats["end_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f"\n抓取统计: 总请求 {self.crawl_stats['total_requests']} 次, "
                    f"成功 {self.crawl_stats['success_count']} 次, "
                    f"失败 {self.crawl_stats['fail_count']} 次, "
                    f"总评论 {self.crawl_stats['total_reviews']} 条")
        
        return all_reviews
    
    def generate_product_info(self, product_ids):
        """
        生成商品信息数据（供入库products表）
        
        Parameters:
            product_ids: 商品ID列表
        
        Returns:
            list: 商品信息字典列表
        """
        categories = ["手机数码", "服饰鞋包", "美妆个护", "食品生鲜", "家居家装",
                       "母婴用品", "运动户外", "图书文具", "家用电器", "电脑办公"]
        shops = ["品质优选旗舰店", "天天特卖官方店", "极速好物专营店", "正品保障直营店",
                 "超值百货专卖店", "品牌工厂店", "官方自营店", "星级精品店",
                 "全球购海外店", "数码科技旗舰店"]
        products = []
        for i, pid in enumerate(product_ids):
            products.append({
                "product_id": str(pid),
                "product_name": f"热销商品{pid[-3:]}号 旗舰版",
                "category": categories[i % len(categories)],
                "shop_name": shops[i % len(shops)],
                "price": round(random.uniform(19.9, 2999.0), 2),
                "total_sales": random.randint(100, 50000),
                "platform": self.platform,
            })
        return products
    
    def generate_user_info(self, reviews):
        """
        从评论数据中提取并生成用户信息（供入库users表）
        
        Parameters:
            reviews: 评论数据列表
        
        Returns:
            list: 用户信息字典列表（已去重）
        """
        seen = set()
        users = []
        for r in reviews:
            uid = r.get("user_id", "")
            if uid and uid not in seen:
                seen.add(uid)
                users.append({
                    "user_id": uid,
                    "nickname": f"用户{uid[-5:]}",
                    "register_days": random.randint(30, 2000),
                    "total_reviews": r.get("user_review_count", random.randint(1, 200)),
                    "avg_rating": round(random.uniform(3.0, 5.0), 2),
                    "credit_level": random.randint(1, 5),
                    "platform": self.platform,
                })
        return users
    
    def get_crawl_stats(self):
        """获取爬取统计信息"""
        return self.crawl_stats
    
    def save_raw_data(self, reviews, filepath):
        """
        保存原始爬取数据为JSON
        
        Parameters:
            reviews: 评论数据列表
            filepath: 保存路径
        """
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump({
                "crawl_stats": self.crawl_stats,
                "platform": self.platform,
                "total_reviews": len(reviews),
                "data": reviews,
            }, f, ensure_ascii=False, indent=2)
        logger.info(f"原始数据已保存: {filepath} ({len(reviews)} 条)")
