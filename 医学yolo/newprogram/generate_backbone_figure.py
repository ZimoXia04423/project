# -*- coding: utf-8 -*-
"""
生成论文用「检测网络 Backbone（主干特征提取）」示意图。
基于 YOLO 系列常见的 Stem + 多级 C2f 下采样结构（与 Ultralytics YOLOv8/YOLOv10 主干表述一致，便于正文引用）。
运行：python generate_backbone_figure.py
输出：figures_framework/backbone_architecture_yolo_style.png（及 thesis_chapter2_figures 副本）
"""
from __future__ import annotations

import shutil
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch


def _setup_zh():
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False


def draw_backbone(out: Path) -> None:
    _setup_zh()
    fig, ax = plt.subplots(figsize=(13, 5.2))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 6)
    ax.axis("off")

    ax.text(
        7,
        5.55,
        "YOLO 系列检测网络 Backbone（主干网络）结构示意图",
        ha="center",
        fontsize=15,
        fontweight="bold",
        color="#1D2129",
    )

    # 横向主干：输入 → Stem → 多级 C2f（示意与 YOLOv8/YOLOv10 文档一致）
    stages = [
        (1.1, "输入影像", "H×W×3\n(如 640×640)", "#F2F3F5"),
        (3.1, "Stem", "卷积下采样\n+P1/P2 特征", "#E8F3FF"),
        (5.1, "Stage 2", "C2f 模块堆叠\n尺度 ≈ 1/8", "#D6F5DE"),
        (7.1, "Stage 3", "C2f 模块堆叠\n尺度 ≈ 1/16", "#EAD9FF"),
        (9.1, "Stage 4", "C2f + SPPF\n尺度 ≈ 1/32", "#FFE8CC"),
        (11.5, "输出", "多尺度特征\n送入 Neck", "#FFD6E0"),
    ]

    cx = []
    for x0, title, sub, face in stages:
        w, h = 1.65, 2.35
        x, y = x0 - w / 2, 2.0 - h / 2
        r = mpatches.FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.02,rounding_size=0.12",
            linewidth=1.6,
            edgecolor="#1D2129",
            facecolor=face,
        )
        ax.add_patch(r)
        ax.text(x0, y + h * 0.72, title, ha="center", va="center", fontsize=11, fontweight="bold")
        ax.text(x0, y + h * 0.38, sub, ha="center", va="center", fontsize=8.8, color="#4E5969")
        cx.append(x0)

    for i in range(len(cx) - 1):
        ax.annotate(
            "",
            xy=(cx[i + 1] - 0.95, 2.0),
            xytext=(cx[i] + 0.95, 2.0),
            arrowprops=dict(arrowstyle="-|>", color="#1D2129", lw=2.0, mutation_scale=14),
        )

    # 自下至上引出 P3/P4/P5（示意 Neck 融合的多尺度来源）
    branch_x = [cx[2], cx[3], cx[4]]
    labels = ["P3\n(相对高分辨率)", "P4", "P5\n(深层语义)"]
    by = 4.85
    for bx, lb in zip(branch_x, labels):
        ax.plot([bx, bx], [3.15, 4.35], color="#86909C", lw=1.5, linestyle="--")
        ax.annotate(
            "",
            xy=(bx, 4.35),
            xytext=(bx, 3.2),
            arrowprops=dict(arrowstyle="-|>", color="#86909C", lw=1.3, mutation_scale=11),
        )
        ax.text(bx, by, lb, ha="center", va="bottom", fontsize=9, color="#1D2129")

    ax.text(
        7,
        0.55,
        "说明：Backbone 负责自浅至深提取层次化特征；P3/P4/P5 交由 Neck（特征融合）与 Head（检测头）完成预测。"
        "\n图为原理示意图，具体层数与通道数以所用 YAML/权重为准（Ultralytics YOLOv10）。",
        ha="center",
        fontsize=8.8,
        color="#86909C",
    )

    fig.tight_layout()
    fig.savefig(out, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main():
    root = Path(__file__).resolve().parent
    out_dir = root / "figures_framework"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "backbone_architecture_yolo_style.png"
    draw_backbone(out)

    ch2 = root / "thesis_chapter2_figures"
    ch2.mkdir(parents=True, exist_ok=True)
    shutil.copy2(out, ch2 / "backbone_architecture_yolo_style.png")

    print("已生成:")
    print(" ", out.resolve())
    print(" ", (ch2 / "backbone_architecture_yolo_style.png").resolve())


if __name__ == "__main__":
    main()
