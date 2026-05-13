# -*- coding: utf-8 -*-
"""
图表生成模块
使用Pyecharts生成交互式HTML图表，使用Matplotlib生成静态图片
为Flask Web应用提供可视化支持
"""

import os
import sys
import base64
from io import BytesIO

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pyecharts.charts import Bar, Line, Pie, WordCloud
from pyecharts import options as opts

import matplotlib
matplotlib.use("Agg")  # 非交互式后端，适合服务器环境
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# 设置matplotlib中文字体
plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "Arial Unicode MS"]
plt.rcParams["axes.unicode_minus"] = False


# ================ Pyecharts 图表 ================

def generate_ranking_bar(titles, values, order_label="播放量"):
    """
    使用Pyecharts生成热度排行柱状图
    返回: HTML字符串（可嵌入页面）
    """
    bar = (
        Bar(init_opts=opts.InitOpts(width="100%", height="400px"))
        .add_xaxis(titles)
        .add_yaxis(order_label, values, color="#5470c6")
        .set_global_opts(
            title_opts=opts.TitleOpts(title="热度排行榜", subtitle=f"按{order_label}排序"),
            xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=30)),
            tooltip_opts=opts.TooltipOpts(trigger="axis"),
            datazoom_opts=opts.DataZoomOpts(type_="slider"),
        )
        .set_series_opts(label_opts=opts.LabelOpts(is_show=False))
    )
    return bar.render_embed()


def generate_trend_line(trend_data, video_title=""):
    """
    使用Pyecharts生成热度趋势折线图
    trend_data: dict with keys: times, views, likes, danmakus, coins, favorites, replies
    返回: HTML字符串
    """
    if not trend_data.get("times"):
        return ""

    line = (
        Line(init_opts=opts.InitOpts(width="100%", height="400px"))
        .add_xaxis(trend_data["times"])
        .add_yaxis("播放量", trend_data["views"], is_smooth=True)
        .add_yaxis("点赞数", trend_data["likes"], is_smooth=True)
        .add_yaxis("弹幕数", trend_data["danmakus"], is_smooth=True)
        .add_yaxis("投币数", trend_data["coins"], is_smooth=True)
        .add_yaxis("收藏数", trend_data["favorites"], is_smooth=True)
        .add_yaxis("评论数", trend_data["replies"], is_smooth=True)
        .set_global_opts(
            title_opts=opts.TitleOpts(title="热度趋势分析", subtitle=video_title),
            tooltip_opts=opts.TooltipOpts(trigger="axis"),
            legend_opts=opts.LegendOpts(pos_top="8%"),
            xaxis_opts=opts.AxisOpts(type_="category"),
        )
    )
    return line.render_embed()


def generate_keyword_wordcloud(kw_freq):
    """
    使用Pyecharts生成关键词词云图
    kw_freq: list of (word, count)
    返回: HTML字符串
    """
    if not kw_freq:
        return ""

    wc = (
        WordCloud(init_opts=opts.InitOpts(width="100%", height="400px"))
        .add(
            series_name="关键词",
            data_pair=kw_freq,
            word_size_range=[14, 66],
            shape="circle",
        )
        .set_global_opts(
            title_opts=opts.TitleOpts(title="关键词词云"),
            tooltip_opts=opts.TooltipOpts(is_show=True),
        )
    )
    return wc.render_embed()


def generate_sentiment_pie(positive, neutral, negative):
    """
    使用Pyecharts生成情感分布饼图
    返回: HTML字符串
    """
    pie = (
        Pie(init_opts=opts.InitOpts(width="100%", height="400px"))
        .add(
            series_name="情感分布",
            data_pair=[
                ("正面", positive),
                ("中性", neutral),
                ("负面", negative),
            ],
            radius=["30%", "60%"],
            label_opts=opts.LabelOpts(formatter="{b}: {c} ({d}%)"),
        )
        .set_global_opts(
            title_opts=opts.TitleOpts(title="评论情感分布"),
            legend_opts=opts.LegendOpts(pos_left="left", orient="vertical"),
        )
        .set_colors(["#91cc75", "#fac858", "#ee6666"])
    )
    return pie.render_embed()


# ================ Matplotlib 图表 ================

def _fig_to_base64(fig):
    """将Matplotlib图表转为Base64编码的PNG图片"""
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight",
                facecolor="white", edgecolor="none")
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    return f"data:image/png;base64,{b64}"


def generate_ranking_bar_mpl(titles, values, order_label="播放量"):
    """
    使用Matplotlib生成热度排行柱状图
    返回: base64编码的PNG图片（data URI）
    """
    fig, ax = plt.subplots(figsize=(12, 5))
    bars = ax.barh(range(len(titles)), values, color="#5470c6", edgecolor="white")
    ax.set_yticks(range(len(titles)))
    ax.set_yticklabels(titles, fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel(order_label)
    ax.set_title(f"热度排行榜（按{order_label}）", fontsize=14)
    ax.grid(axis="x", alpha=0.3)
    for bar, val in zip(bars, values):
        ax.text(bar.get_width(), bar.get_y() + bar.get_height() / 2,
                f" {val:,}", va="center", fontsize=8)
    fig.tight_layout()
    return _fig_to_base64(fig)


def generate_sentiment_pie_mpl(positive, neutral, negative):
    """
    使用Matplotlib生成情感分布饼图
    返回: base64编码的PNG图片（data URI）
    """
    labels = ["正面", "中性", "负面"]
    sizes = [positive, neutral, negative]
    colors = ["#91cc75", "#fac858", "#ee6666"]
    explode = (0.03, 0.03, 0.03)

    fig, ax = plt.subplots(figsize=(6, 5))
    wedges, texts, autotexts = ax.pie(
        sizes, explode=explode, labels=labels, colors=colors,
        autopct="%1.1f%%", startangle=90, pctdistance=0.75,
        textprops={"fontsize": 12}
    )
    ax.set_title("评论情感分布", fontsize=14, pad=15)
    ax.legend(wedges, [f"{l}: {s}条" for l, s in zip(labels, sizes)],
              loc="lower right", fontsize=10)
    return _fig_to_base64(fig)


def generate_keyword_bar_mpl(kw_freq, top_n=20):
    """
    使用Matplotlib生成关键词频率柱状图
    kw_freq: list of (word, count)
    返回: base64编码的PNG图片（data URI）
    """
    if not kw_freq:
        return ""
    data = kw_freq[:top_n]
    words = [k[0] for k in data]
    counts = [k[1] for k in data]

    fig, ax = plt.subplots(figsize=(12, 5))
    bars = ax.barh(range(len(words)), counts, color="#ee6666", edgecolor="white")
    ax.set_yticks(range(len(words)))
    ax.set_yticklabels(words, fontsize=10)
    ax.invert_yaxis()
    ax.set_xlabel("词频")
    ax.set_title("高频关键词 TOP{}".format(top_n), fontsize=14)
    ax.grid(axis="x", alpha=0.3)
    for bar, val in zip(bars, counts):
        ax.text(bar.get_width(), bar.get_y() + bar.get_height() / 2,
                f" {val}", va="center", fontsize=9)
    fig.tight_layout()
    return _fig_to_base64(fig)
