# -*- coding: utf-8 -*-
"""根据 output/metrics.json 重绘图 4-6 类「训练/预测时间对比」，修正横轴刻度。"""
import json
import os
import sys

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_DIR)

from pandas import DataFrame

from src.evaluation import plot_time_comparison

METRICS = os.path.join(PROJECT_DIR, "output", "metrics.json")


def main():
    if not os.path.isfile(METRICS):
        print("缺少", METRICS)
        return 1
    with open(METRICS, "r", encoding="utf-8") as f:
        rows = json.load(f)
    df = DataFrame(rows)
    plot_time_comparison(df, os.path.join(PROJECT_DIR, "output"))
    print("已更新 output/time_comparison.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
