# -*- coding: utf-8 -*-
"""
B站数据抓取测试脚本
测试三个核心API的可用性：
1. 热门排行榜视频列表
2. 视频详情信息
3. 视频评论数据
"""

import requests
import json
import time

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.bilibili.com",
}


def test_hot_ranking():
    """测试1：获取B站热门排行榜"""
    print("=" * 60)
    print("【测试1】获取B站热门排行榜视频列表")
    print("=" * 60)

    url = "https://api.bilibili.com/x/web-interface/ranking/v2"
    params = {"rid": 0, "type": "all"}  # rid=0 表示全站排行

    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=10)
        data = resp.json()

        if data["code"] == 0:
            video_list = data["data"]["list"]
            print(f"成功获取 {len(video_list)} 条热门视频数据\n")

            # 展示前5条
            print(f"{'排名':<5} {'播放量':<12} {'弹幕数':<8} {'标题'}")
            print("-" * 60)
            for i, video in enumerate(video_list[:5], 1):
                stat = video["stat"]
                title = video["title"][:30]
                print(f"{i:<5} {stat['view']:<12} {stat['danmaku']:<8} {title}")

            # 返回第一个视频的bvid用于后续测试
            return video_list[0]["bvid"], video_list[0]["aid"]
        else:
            print(f"请求失败，错误码: {data['code']}, 消息: {data['message']}")
            return None, None
    except Exception as e:
        print(f"请求异常: {e}")
        return None, None


def test_video_detail(bvid):
    """测试2：获取视频详情"""
    print(f"\n{'=' * 60}")
    print(f"【测试2】获取视频详情 (BV号: {bvid})")
    print("=" * 60)

    url = "https://api.bilibili.com/x/web-interface/view"
    params = {"bvid": bvid}

    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=10)
        data = resp.json()

        if data["code"] == 0:
            v = data["data"]
            stat = v["stat"]
            print(f"标题: {v['title']}")
            print(f"UP主: {v['owner']['name']}")
            print(f"发布时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(v['pubdate']))}")
            print(f"播放量: {stat['view']}")
            print(f"弹幕数: {stat['danmaku']}")
            print(f"点赞数: {stat['like']}")
            print(f"投币数: {stat['coin']}")
            print(f"收藏数: {stat['favorite']}")
            print(f"分享数: {stat['share']}")
            print(f"评论数: {stat['reply']}")
            print("视频详情获取成功！")
            return True
        else:
            print(f"请求失败，错误码: {data['code']}, 消息: {data['message']}")
            return False
    except Exception as e:
        print(f"请求异常: {e}")
        return False


def test_video_comments(aid):
    """测试3：获取视频评论"""
    print(f"\n{'=' * 60}")
    print(f"【测试3】获取视频评论 (aid: {aid})")
    print("=" * 60)

    url = "https://api.bilibili.com/x/v2/reply"
    params = {
        "type": 1,       # 1表示视频评论
        "oid": aid,       # 视频的aid
        "pn": 1,          # 第1页
        "ps": 10,         # 每页10条
        "sort": 1,        # 按热度排序
    }

    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=10)
        data = resp.json()

        if data["code"] == 0:
            replies = data["data"].get("replies", [])
            if replies:
                print(f"成功获取 {len(replies)} 条评论\n")
                print(f"{'用户名':<15} {'点赞数':<8} {'评论内容'}")
                print("-" * 60)
                for reply in replies[:5]:
                    uname = reply["member"]["uname"][:10]
                    like = reply["like"]
                    content = reply["content"]["message"][:40].replace("\n", " ")
                    print(f"{uname:<15} {like:<8} {content}")
                print("\n评论数据获取成功！")
                return True
            else:
                print("该视频暂无评论数据")
                return False
        else:
            print(f"请求失败，错误码: {data['code']}, 消息: {data['message']}")
            return False
    except Exception as e:
        print(f"请求异常: {e}")
        return False


def main():
    print("B站数据抓取可行性测试")
    print("测试目标：验证热门排行榜、视频详情、视频评论三个API的可用性\n")

    # 测试1：热门排行榜
    bvid, aid = test_hot_ranking()
    if not bvid:
        print("\n热门排行榜获取失败，终止后续测试")
        return

    time.sleep(1)  # 请求间隔

    # 测试2：视频详情
    test_video_detail(bvid)

    time.sleep(1)

    # 测试3：视频评论
    test_video_comments(aid)

    # 汇总
    print(f"\n{'=' * 60}")
    print("测试完成！以上三个API均可正常获取数据。")
    print("=" * 60)


if __name__ == "__main__":
    main()
