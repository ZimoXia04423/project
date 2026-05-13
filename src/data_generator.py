"""
数据生成模块：生成模拟电商平台用户评论数据集
包含真实评论和虚假评论两类样本，含易分类和难分类样本
"""
import random
import pandas as pd
import numpy as np
import os

# 真实评论模板（自然、多样、有具体细节）
REAL_REVIEW_TEMPLATES = [
    "这个产品质量还行，用了几天感觉不错，物流也挺快的",
    "收到货了，包装还可以，但是颜色和图片有点差别",
    "用了一周了，整体感觉还行吧，性价比一般",
    "东西还可以，就是物流太慢了，等了好久才到",
    "产品和描述基本一致，做工还行，好评",
    "第二次购买了，质量稳定，推荐给朋友了",
    "收到了，还没用，看着还行，用了再来评价",
    "一般般吧，没有想象中那么好，凑合用",
    "挺不错的，比实体店便宜很多，下次还来",
    "买给老人用的，操作简单，老人很喜欢",
    "质量很好，做工精细，值这个价格",
    "等了三天到的，包装完好，产品没问题",
    "还行吧，中规中矩，没有太多惊喜也没有失望",
    "用了半个月了，暂时没发现什么问题，还可以",
    "性价比挺高的，比之前买的那个好用",
    "不太满意，有点小瑕疵，但不影响使用",
    "快递给力，产品也不错，满意的一次购物",
    "第一次买这个牌子，感觉还行，观望中",
    "材质摸着挺好的，尺寸也合适，满意",
    "买了两个，一个自用一个送人，都说不错",
    "商品质量一般，这个价格也算可以了",
    "整体还行，就是说明书写得不太清楚",
    "外观好看，手感不错，就是有点重",
    "用了几天感觉还好，没什么大问题",
    "物流很快，第二天就到了，好评",
    "和朋友买的一样，质量确实不错",
    "还可以吧，不算特别好但也不差",
    "这个颜色很正，实物和图片差不多",
    "买回来发现有个小划痕，不过不明显",
    "总体来说还是不错的，推荐购买",
    "配送速度快，东西也还行，满意",
    "价格实惠，质量过得去，下次继续",
    "用了一段时间，质量还是可以的",
    "大小合适，颜色也好看，满意",
    "做工一般，不过功能都正常，凑合用",
    "之前犹豫很久才买的，现在觉得买对了",
    "味道有点大，放了两天就好了",
    "客服态度很好，回复速度也快",
    "有点色差，但是质量还行",
    "比预期的要好，挺惊喜的",
    "这款产品用着还行吧，就是声音稍微有点大",
    "颜色很正，和网上图片一样，值了",
    "质量中等偏上吧，这个价位还可以",
    "快递包装很严实，没有损坏，好评",
    "女朋友很喜欢，说比专柜便宜不少",
    "功能齐全，就是操作稍微复杂了点",
    "已经用了两个月了，暂时没什么问题",
    "给妈妈买的，她说很实用，挺好",
    "做活动买的，性价比很高，划算",
    "第三次回购了，一如既往的好",
]

# 明显虚假评论（夸张、重复、情绪极端）
OBVIOUS_FAKE_TEMPLATES = [
    "质量非常好非常好，强烈推荐强烈推荐，五星好评！！！",
    "太棒了太棒了！！！这是我买过最好的产品，没有之一！！！",
    "好好好好好好好好好好！强烈推荐大家购买！！！",
    "完美完美完美！简直太完美了！必须五星好评！",
    "真的太好用了吧！！！后悔没有早点买！！！全五星！",
    "哇塞！收到就惊呆了！质量超级好！推荐推荐推荐！",
    "必须给满分！这个产品简直无敌了！大家快来买！",
    "太赞了太赞了！物超所值！买它买它买它！",
    "差差差！垃圾产品！千万不要买！退款退款！",
    "太差了！完全就是骗人的！大家别上当！",
    "假货假货假货！千万不要买这个店的东西！",
    "垃圾中的垃圾！从来没买过这么差的东西！",
    "千万别买！上当受骗！垃圾垃圾垃圾！",
    "好评好评好评好评好评好评好评好评好评好评",
    "默认好评默认好评默认好评默认好评默认好评",
    "不错不错不错不错不错不错不错不错不错不错",
    "这是我买过最好的东西了真的特别好用推荐大家购买物流也很快包装也很好客服态度也不错全五星好评",
    "产品非常好用非常满意非常推荐非常喜欢非常棒",
    "服务态度极差极差极差！产品更是一塌糊涂！",
    "不要不要不要买！切记切记！垃圾产品！",
]

# 高仿虚假评论（模仿真实评论风格，但有细微特征差异）
SUBTLE_FAKE_TEMPLATES = [
    "产品质量不错，物流也很快，好评",
    "挺好的，很满意，值得购买推荐",
    "质量很好，物流很快，包装完好，满意",
    "东西很好，很喜欢，会再来买的",
    "很不错的产品，使用很满意，推荐给大家",
    "收到了，质量很好，满意好评",
    "物流快，质量好，价格便宜，好评",
    "产品很好，跟描述的一样，满意",
    "非常好，质量很好，物流也快，全五星",
    "产品不错，性价比高，推荐购买",
    "很好用，质量也不错，推荐",
    "收到了，还不错，物美价廉",
    "东西不错，跟描述一样，好评",
    "质量可以，价格实惠，值得推荐",
    "满意满意，非常好的一次购物体验",
    "整体感觉很好，质量也行，推荐大家购买",
    "很喜欢，质量也好，下次还来这家",
    "物流速度很快，产品质量很好，满意",
    "好用不贵，性价比很高，推荐推荐",
    "收到了，东西挺好的，满意好评",
    "产品质量好，做工精细，好评推荐",
    "非常满意的一次购物，产品确实不错",
    "给好评，产品质量好，客服态度也好",
    "价格合理，质量过关，推荐入手",
    "收到了很满意，质量很好，物流也快",
    "很不错，符合预期，推荐大家买",
    "东西还行，质量可以，价格也合适",
    "用了几天感觉不错，好用推荐",
    "总体满意，质量做工都不错",
    "挺好的一款产品，值得入手购买",
]


def generate_dataset(n_samples=2000, random_seed=42):
    """
    生成模拟电商评论数据集
    包含：真实评论、明显虚假评论、高仿虚假评论三类
    
    Parameters:
        n_samples: 总样本数
        random_seed: 随机种子
    
    Returns:
        DataFrame: 包含评论文本、标签和特征的数据集
    """
    random.seed(random_seed)
    np.random.seed(random_seed)
    
    data = []
    n_real = n_samples // 2
    n_fake = n_samples - n_real
    n_obvious_fake = n_fake // 2
    n_subtle_fake = n_fake - n_obvious_fake
    
    # 随机细节短语（插入模板中使每条评论唯一）
    time_phrases = [
        "用了两天", "用了三天", "用了一周", "用了半个月", "用了一个月",
        "买了三天了", "到手一周", "入手半月", "刚收到", "收到两天了",
    ]
    detail_phrases = [
        "整体还行", "还会回购", "好评", "推荐", "可以的", "不错",
        "挺满意", "还可以吧", "值得", "感觉一般", "挺好", "满意",
        "还不错", "性价比高", "物美价廉", "符合预期", "比想象中好",
        "算是合格吧", "中规中矩", "基本满意", "大体满意", "总体OK",
    ]
    connector = ["，", "，", "。", "～", "...", " ", "！", "；"]
    
    def _make_unique(template, variations):
        """通过随机组合使每条评论文本唯一"""
        suffix = random.choice(variations)
        # 50%概率再加一个随机时间或细节短语
        if random.random() < 0.5:
            suffix += random.choice(connector) + random.choice(detail_phrases)
        # 30%概率加时间短语
        if random.random() < 0.3:
            suffix = random.choice(connector) + random.choice(time_phrases) + suffix
        return template + suffix
    
    # 生成真实评论
    real_variations = [
        "", "。", "～", "...", " ",
        "，整体还行", "，还会回购", "，好评",
        "，推荐", "，可以的", "，不错",
        "，总的来说还行", "，下次再来", "，物流不错",
        "，挺实用", "，够用了", "，比较满意",
    ]
    for i in range(n_real):
        template = random.choice(REAL_REVIEW_TEMPLATES)
        review = _make_unique(template, real_variations)
        
        review_length = len(review)
        exclamation_count = review.count("！") + review.count("!")
        repeat_char_ratio = _calc_repeat_ratio(review)
        # 真实评论：情感中等偏正，用户评论数多，评论间隔长
        sentiment_score = round(random.gauss(0.55, 0.15), 3)
        sentiment_score = max(0.1, min(0.9, sentiment_score))
        user_review_count = random.randint(5, 200)
        avg_review_interval_days = round(random.uniform(3, 60), 1)
        rating = random.choices([2, 3, 4, 5], weights=[5, 20, 40, 35])[0]
        
        data.append({
            "review_text": review,
            "label": 0,
            "review_length": review_length,
            "exclamation_count": exclamation_count,
            "repeat_char_ratio": repeat_char_ratio,
            "sentiment_score": sentiment_score,
            "user_review_count": user_review_count,
            "avg_review_interval_days": avg_review_interval_days,
            "rating": rating,
        })
    
    # 生成明显虚假评论
    obvious_variations = [
        "", "！", "！！！", "!!!", "～～～",
        "，强烈推荐！", "，必买！", "，五星！",
        "，太好了", "，超赞", "，绝了", "，无敌了",
    ]
    for i in range(n_obvious_fake):
        template = random.choice(OBVIOUS_FAKE_TEMPLATES)
        review = _make_unique(template, obvious_variations)
        
        review_length = len(review)
        exclamation_count = review.count("！") + review.count("!")
        repeat_char_ratio = _calc_repeat_ratio(review)
        # 明显虚假：情感极端（很高或很低）
        if random.random() < 0.3:
            sentiment_score = round(random.uniform(0.0, 0.15), 3)
        else:
            sentiment_score = round(random.uniform(0.88, 1.0), 3)
        user_review_count = random.randint(1, 15)
        avg_review_interval_days = round(random.uniform(0.05, 1.5), 1)
        rating = random.choices([1, 5], weights=[25, 75])[0]
        
        data.append({
            "review_text": review,
            "label": 1,
            "review_length": review_length,
            "exclamation_count": exclamation_count,
            "repeat_char_ratio": repeat_char_ratio,
            "sentiment_score": sentiment_score,
            "user_review_count": user_review_count,
            "avg_review_interval_days": avg_review_interval_days,
            "rating": rating,
        })
    
    # 生成高仿虚假评论（最难区分的部分，特征接近真实评论）
    subtle_variations = [
        "", "。", "，好评", "，推荐",
        "，值得购买", "，不错", "，满意",
        "，真心推荐", "，必入", "，回购了",
    ]
    for i in range(n_subtle_fake):
        template = random.choice(SUBTLE_FAKE_TEMPLATES)
        review = _make_unique(template, subtle_variations)
        
        review_length = len(review)
        exclamation_count = review.count("！") + review.count("!")
        repeat_char_ratio = _calc_repeat_ratio(review)
        # 高仿虚假：情感偏高但不极端，行为特征有细微差异
        sentiment_score = round(random.gauss(0.72, 0.1), 3)
        sentiment_score = max(0.4, min(0.95, sentiment_score))
        user_review_count = random.randint(1, 50)
        avg_review_interval_days = round(random.uniform(0.2, 8), 1)
        rating = random.choices([4, 5], weights=[30, 70])[0]
        
        data.append({
            "review_text": review,
            "label": 1,
            "review_length": review_length,
            "exclamation_count": exclamation_count,
            "repeat_char_ratio": repeat_char_ratio,
            "sentiment_score": sentiment_score,
            "user_review_count": user_review_count,
            "avg_review_interval_days": avg_review_interval_days,
            "rating": rating,
        })
    
    df = pd.DataFrame(data)
    df = df.sample(frac=1, random_state=random_seed).reset_index(drop=True)
    return df


def _calc_repeat_ratio(text):
    """计算文本中重复字符占比"""
    if len(text) <= 1:
        return 0.0
    repeat_count = sum(1 for i in range(1, len(text)) if text[i] == text[i-1])
    return round(repeat_count / len(text), 3)


def save_dataset(df, output_dir="data"):
    """保存数据集到CSV文件"""
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, "ecommerce_reviews.csv")
    df.to_csv(filepath, index=False, encoding="utf-8-sig")
    print(f"数据集已保存到 {filepath}，共 {len(df)} 条记录")
    return filepath


if __name__ == "__main__":
    df = generate_dataset(2000)
    save_dataset(df)
    print(f"\n数据集统计：")
    print(f"真实评论: {len(df[df['label']==0])} 条")
    print(f"虚假评论: {len(df[df['label']==1])} 条")
    print(f"\n样例数据：")
    print(df.head(10).to_string())
