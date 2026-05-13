# -*- coding: utf-8 -*-
"""
Flask Web应用主程序
提供数据可视化展示界面，集成热点排行榜、趋势分析、关键词分析、情感分析等功能
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from functools import wraps
import json
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import FLASK_CONFIG
from database.db_operations import (
    get_crawl_times, get_top_videos, query_videos,
    query_all_comments, get_all_tnames, get_video_trend,
    get_video_count, get_comment_count, get_video_title_by_bvid
)
from analyzer.data_analyzer import (
    analyze_hot_ranking, analyze_trend, analyze_keywords,
    analyze_keywords_tfidf, analyze_sentiment, get_category_distribution
)
from analyzer.chart_generator import (
    generate_ranking_bar, generate_trend_line,
    generate_keyword_wordcloud, generate_sentiment_pie,
    generate_ranking_bar_mpl, generate_sentiment_pie_mpl,
    generate_keyword_bar_mpl
)

app = Flask(__name__)
app.secret_key = FLASK_CONFIG["SECRET_KEY"]

# 管理员账号配置
ADMIN_USER = {"username": "admin", "password": "admin123"}


def login_required(f):
    """登录验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


@app.route("/login", methods=["GET", "POST"])
def login():
    """管理员登录页面"""
    if session.get("logged_in"):
        return redirect(url_for("index"))
    error = None
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if username == ADMIN_USER["username"] and password == ADMIN_USER["password"]:
            session["logged_in"] = True
            session["username"] = username
            return redirect(url_for("index"))
        else:
            error = "用户名或密码错误，请重试"
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    """退出登录"""
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def index():
    """首页 - 系统概览"""
    try:
        crawl_times = get_crawl_times()
        tnames = get_all_tnames()
        top_videos = get_top_videos(limit=10)
        total_videos = get_video_count()
        total_comments = get_comment_count()
    except Exception:
        crawl_times = []
        tnames = []
        top_videos = []
        total_videos = 0
        total_comments = 0

    return render_template("index.html",
                           crawl_times=crawl_times,
                           tnames=tnames,
                           top_videos=top_videos,
                           total_videos=total_videos,
                           total_comments=total_comments,
                           crawl_count=len(crawl_times))


@app.route("/ranking")
@login_required
def ranking():
    """热度排行榜页面"""
    start_time = request.args.get("start_time", "")
    end_time = request.args.get("end_time", "")
    order_by = request.args.get("order_by", "view_count")
    limit = int(request.args.get("limit", 20))

    data = analyze_hot_ranking(
        start_time=start_time or None,
        end_time=end_time or None,
        order_by=order_by,
        limit=limit
    )

    # 图表数据
    titles = [d["title"][:15] for d in data]
    values = [d[order_by] for d in data]

    order_label_map = {
        "view_count": "播放量",
        "like_count": "点赞数",
        "coin_count": "投币数",
        "danmaku_count": "弹幕数",
        "favorite_count": "收藏数",
        "reply_count": "评论数",
    }
    order_label = order_label_map.get(order_by, "播放量")

    return render_template("ranking.html",
                           data=data,
                           titles=json.dumps(titles, ensure_ascii=False),
                           values=json.dumps(values),
                           order_by=order_by,
                           order_label=order_label,
                           start_time=start_time,
                           end_time=end_time,
                           limit=limit)


@app.route("/trend")
@login_required
def trend():
    """热度趋势分析页面"""
    bvid = request.args.get("bvid", "")
    trend_data = {}
    video_title = ""

    if bvid:
        trend_data = analyze_trend(bvid)
        video_title = get_video_title_by_bvid(bvid)

    # 获取所有视频列表供选择
    all_videos = get_top_videos(limit=100)
    # 去重bvid
    seen = set()
    unique_videos = []
    for v in all_videos:
        if v["bvid"] not in seen:
            seen.add(v["bvid"])
            unique_videos.append({"bvid": v["bvid"], "title": v["title"]})

    return render_template("trend.html",
                           trend_data=json.dumps(trend_data, ensure_ascii=False, default=str),
                           bvid=bvid,
                           video_title=video_title,
                           video_list=unique_videos)


@app.route("/keywords")
@login_required
def keywords():
    """关键词分析页面"""
    start_time = request.args.get("start_time", "")
    end_time = request.args.get("end_time", "")
    source = request.args.get("source", "title")
    top_n = int(request.args.get("top_n", 50))

    # 词频统计
    kw_freq = analyze_keywords(
        start_time=start_time or None,
        end_time=end_time or None,
        top_n=top_n,
        source=source
    )

    # TF-IDF关键词
    kw_tfidf = analyze_keywords_tfidf(
        start_time=start_time or None,
        end_time=end_time or None,
        top_n=30,
        source=source
    )

    words = [k[0] for k in kw_freq]
    counts = [k[1] for k in kw_freq]
    # 词云数据
    wordcloud_data = [{"name": k[0], "value": k[1]} for k in kw_freq]

    tfidf_words = [k[0] for k in kw_tfidf]
    tfidf_weights = [round(k[1], 4) for k in kw_tfidf]

    return render_template("keywords.html",
                           words=json.dumps(words, ensure_ascii=False),
                           counts=json.dumps(counts),
                           wordcloud_data=json.dumps(wordcloud_data, ensure_ascii=False),
                           tfidf_words=json.dumps(tfidf_words, ensure_ascii=False),
                           tfidf_weights=json.dumps(tfidf_weights),
                           kw_freq=kw_freq[:30],
                           source=source,
                           start_time=start_time,
                           end_time=end_time,
                           top_n=top_n)


@app.route("/sentiment")
@login_required
def sentiment():
    """情感分析页面"""
    start_time = request.args.get("start_time", "")
    end_time = request.args.get("end_time", "")
    bvid = request.args.get("bvid", "")

    result = analyze_sentiment(
        start_time=start_time or None,
        end_time=end_time or None,
        bvid=bvid or None
    )

    pie_data = json.dumps([
        {"name": "正面", "value": result["positive"]},
        {"name": "中性", "value": result["neutral"]},
        {"name": "负面", "value": result["negative"]},
    ], ensure_ascii=False)

    # 获取视频列表供筛选
    all_videos = get_top_videos(limit=100)
    seen = set()
    unique_videos = []
    for v in all_videos:
        if v["bvid"] not in seen:
            seen.add(v["bvid"])
            unique_videos.append({"bvid": v["bvid"], "title": v["title"]})

    return render_template("sentiment.html",
                           result=result,
                           pie_data=pie_data,
                           bvid=bvid,
                           start_time=start_time,
                           end_time=end_time,
                           video_list=unique_videos)


@app.route("/api/chart/ranking")
@login_required
def api_chart_ranking():
    """API: Pyecharts+Matplotlib 排行图表（按需加载）"""
    order_by = request.args.get("order_by", "view_count")
    limit = int(request.args.get("limit", 20))
    data = analyze_hot_ranking(order_by=order_by, limit=limit)
    titles = [d["title"][:15] for d in data]
    values = [d[order_by] for d in data]
    label_map = {"view_count":"播放量","like_count":"点赞数","coin_count":"投币数",
                 "danmaku_count":"弹幕数","favorite_count":"收藏数","reply_count":"评论数"}
    label = label_map.get(order_by, "播放量")
    pyecharts_html = generate_ranking_bar(titles, values, label)
    mpl_img = generate_ranking_bar_mpl(titles, values, label)
    return jsonify({"pyecharts": pyecharts_html, "mpl_img": mpl_img})


@app.route("/api/chart/keywords")
@login_required
def api_chart_keywords():
    """API: Pyecharts+Matplotlib 关键词图表（按需加载）"""
    source = request.args.get("source", "title")
    top_n = int(request.args.get("top_n", 50))
    kw_freq = analyze_keywords(top_n=top_n, source=source)
    pyecharts_wc = generate_keyword_wordcloud(kw_freq)
    mpl_img = generate_keyword_bar_mpl(kw_freq, top_n=20)
    return jsonify({"pyecharts": pyecharts_wc, "mpl_img": mpl_img})


@app.route("/api/chart/sentiment")
@login_required
def api_chart_sentiment():
    """API: Pyecharts+Matplotlib 情感图表（按需加载）"""
    result = analyze_sentiment()
    pyecharts_html = generate_sentiment_pie(result["positive"], result["neutral"], result["negative"])
    mpl_img = generate_sentiment_pie_mpl(result["positive"], result["neutral"], result["negative"])
    return jsonify({"pyecharts": pyecharts_html, "mpl_img": mpl_img})


@app.route("/api/chart/trend")
@login_required
def api_chart_trend():
    """API: Pyecharts 趋势折线图（按需加载）"""
    bvid = request.args.get("bvid", "")
    if not bvid:
        return jsonify({"pyecharts": ""})
    trend_data = analyze_trend(bvid)
    title = get_video_title_by_bvid(bvid)
    pyecharts_html = generate_trend_line(trend_data, title)
    return jsonify({"pyecharts": pyecharts_html})


@app.route("/api/category_distribution")
@login_required
def api_category_distribution():
    """API: 分区分布数据"""
    start_time = request.args.get("start_time", "")
    end_time = request.args.get("end_time", "")
    data = get_category_distribution(
        start_time=start_time or None,
        end_time=end_time or None
    )
    return jsonify([{"name": d[0], "value": d[1]} for d in data])


if __name__ == "__main__":
    app.run(
        host=FLASK_CONFIG["HOST"],
        port=FLASK_CONFIG["PORT"],
        debug=FLASK_CONFIG["DEBUG"]
    )
