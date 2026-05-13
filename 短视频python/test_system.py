# -*- coding: utf-8 -*-
"""系统功能完整性测试脚本"""
import requests
import sys

BASE = "http://127.0.0.1:5000"

def test_pages():
    pages = {
        "/": "首页概览",
        "/ranking": "热度排行",
        "/trend": "趋势分析",
        "/keywords": "关键词分析",
        "/sentiment": "情感分析",
        "/api/category_distribution": "分区分布API",
    }
    results = []
    for path, name in pages.items():
        try:
            r = requests.get(BASE + path, timeout=30)
            status = "OK" if r.status_code == 200 else f"FAIL({r.status_code})"
            size = len(r.text)
            results.append((name, path, status, size))
        except Exception as e:
            results.append((name, path, f"ERROR: {e}", 0))

    print("=" * 60)
    print("Flask Web页面测试")
    print("=" * 60)
    for name, path, status, size in results:
        print(f"  [{status:>6}] {name:10} {path:40} ({size} bytes)")
    return all(r[2] == "OK" for r in results)


def test_db():
    from database.db_operations import (
        query_videos, query_all_comments, get_crawl_times,
        get_top_videos, get_all_tnames
    )
    print("\n" + "=" * 60)
    print("数据库查询测试")
    print("=" * 60)

    videos = query_videos(limit=5)
    print(f"  视频查询: {len(videos)} 条 (limit=5)")

    comments = query_all_comments(limit=5)
    print(f"  评论查询: {len(comments)} 条 (limit=5)")

    times = get_crawl_times()
    print(f"  抓取时间: {len(times)} 个批次")

    top = get_top_videos(limit=3)
    print(f"  TOP视频: {len(top)} 条 (limit=3)")

    tnames = get_all_tnames()
    print(f"  分区列表: {tnames}")

    ok = len(videos) > 0 and len(comments) > 0
    print(f"  结果: {'PASS' if ok else 'FAIL'}")
    return ok


def test_analyzer():
    from analyzer.data_analyzer import (
        analyze_hot_ranking, analyze_keywords,
        analyze_sentiment, get_category_distribution
    )
    print("\n" + "=" * 60)
    print("数据分析模块测试")
    print("=" * 60)

    ranking = analyze_hot_ranking(limit=5)
    print(f"  热度排名: {len(ranking)} 条")
    if ranking:
        print(f"    第1名: {ranking[0]['title'][:30]}  播放:{ranking[0]['view_count']}")

    keywords = analyze_keywords(top_n=10, source="title")
    print(f"  标题关键词: {len(keywords)} 个")
    if keywords:
        print(f"    TOP3: {keywords[:3]}")

    sentiment = analyze_sentiment()
    print(f"  情感分析: 总计{sentiment['total']}条")
    print(f"    正面:{sentiment['positive']}({sentiment['positive_pct']}%) "
          f"中性:{sentiment['neutral']}({sentiment['neutral_pct']}%) "
          f"负面:{sentiment['negative']}({sentiment['negative_pct']}%)")

    cats = get_category_distribution()
    print(f"  分区分布: {len(cats)} 个分区")

    ok = len(ranking) > 0 and len(keywords) > 0 and sentiment['total'] > 0
    print(f"  结果: {'PASS' if ok else 'FAIL'}")
    return ok


if __name__ == "__main__":
    print("\n>>> B站热点话题分析系统 - 功能完整性测试 <<<\n")

    r1 = test_pages()
    r2 = test_db()
    r3 = test_analyzer()

    print("\n" + "=" * 60)
    print("测试汇总")
    print("=" * 60)
    items = [("Flask Web页面", r1), ("数据库查询", r2), ("数据分析模块", r3)]
    for name, ok in items:
        print(f"  {name}: {'PASS ✓' if ok else 'FAIL ✗'}")

    all_pass = all(r for _, r in items)
    print(f"\n总结: {'全部通过!' if all_pass else '存在失败项，请检查'}")
    sys.exit(0 if all_pass else 1)
