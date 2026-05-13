# -*- coding: utf-8 -*-
"""
单独生成「图 4-7」深度学习训练损失曲线（training_losses.png）。

优先读取 output/dl_losses.json（运行 python main.py 成功后会自动生成）。
若不存在，则用占位曲线仅便于排版占位——答辩前请运行完整流程替换为真实曲线。
"""
import json
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(PROJECT_DIR, "output")
JSON_PATH = os.path.join(OUTPUT_DIR, "dl_losses.json")
PNG_PATH = os.path.join(OUTPUT_DIR, "training_losses.png")
PNG_THESIS = os.path.join(OUTPUT_DIR, "fig4_7_training_loss.png")

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


def _demo_losses(epochs: int = 10):
    """单调下降的占位损失（仅无 JSON 时使用）。"""
    import math

    def curve(scale, decay):
        return [
            round(scale * math.exp(-decay * (i + 1)) + 0.02 + 0.01 * i / epochs, 4)
            for i in range(epochs)
        ]

    return {
        "TextCNN": curve(0.55, 0.35),
        "BiLSTM": curve(0.62, 0.28),
        "Transformer": curve(0.58, 0.30),
    }


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    used_demo = False
    if os.path.isfile(JSON_PATH):
        with open(JSON_PATH, "r", encoding="utf-8") as f:
            losses_export = json.load(f)
    else:
        losses_export = _demo_losses()
        used_demo = True
        print("[警告] 未找到 output/dl_losses.json，已用占位数据绘图。", file=sys.stderr)
        print("        请在本机成功运行 python main.py 后重新执行本脚本。", file=sys.stderr)

    fig, ax = plt.subplots(figsize=(9, 5.5))
    for name, losses in losses_export.items():
        if not losses:
            continue
        xs = list(range(1, len(losses) + 1))
        ax.plot(xs, losses, marker="o", markersize=5, label=name, linewidth=2)

    ax.set_xlabel("训练轮次 (Epoch)")
    ax.set_ylabel("训练损失 (Loss)")
    ax.set_title("深度学习模型训练损失曲线")
    ax.legend()
    ax.grid(alpha=0.3)

    plt.tight_layout()
    plt.savefig(PNG_PATH, dpi=200, bbox_inches="tight")
    plt.savefig(PNG_THESIS, dpi=200, bbox_inches="tight")
    plt.close()
    print("已保存:", PNG_PATH)
    print("已保存 (论文插图推荐文件名):", PNG_THESIS)
    if used_demo:
        print("（当前为占位图，交稿前务必替换为真实训练输出）")


if __name__ == "__main__":
    main()
