# -*- coding: utf-8 -*-
"""
生成论文用「YOLOv10 / YOLO 系列 Neck（特征金字塔融合）」示意图。
典型结构：自上而下 FPN（深层语义向浅层传递）+ 自下而上 PAN（再强化定位特征），
与 Ultralytics YOLOv8/YOLOv10 中 PAN-FPN Neck 表述一致。
运行：python generate_neck_figure.py
"""
from __future__ import annotations

import shutil
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches


def _setup_zh():
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False


def _box(ax, cx, cy, w, h, title, sub, face, lw=1.5):
    x, y = cx - w / 2, cy - h / 2
    r = mpatches.FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.02,rounding_size=0.1",
        linewidth=lw,
        edgecolor="#1D2129",
        facecolor=face,
    )
    ax.add_patch(r)
    ax.text(cx, cy + h * 0.18, title, ha="center", va="center", fontsize=10, fontweight="bold")
    ax.text(cx, cy - h * 0.22, sub, ha="center", va="center", fontsize=8, color="#4E5969")


def _arrow(ax, x1, y1, x2, y2, color, lw=1.8, style="-|>"):
    ax.annotate(
        "",
        xy=(x2, y2),
        xytext=(x1, y1),
        arrowprops=dict(arrowstyle=style, color=color, lw=lw, mutation_scale=12),
    )


def draw_neck(out: Path) -> None:
    _setup_zh()
    fig, ax = plt.subplots(figsize=(14, 7.5))
    ax.set_xlim(0, 15)
    ax.set_ylim(0, 9)
    ax.axis("off")

    ax.text(
        7.5,
        8.55,
        "YOLOv10 Neck（PAN-FPN 特征融合）结构示意图",
        ha="center",
        fontsize=15,
        fontweight="bold",
        color="#1D2129",
    )
    ax.text(
        7.5,
        8.05,
        "蓝色箭头：自上而下 FPN（Upsample + Concat + C2f）   橙色箭头：自下而上 PAN（Conv↓ + Concat + C2f）",
        ha="center",
        fontsize=9.8,
        color="#4E5969",
    )

    # Backbone 输出
    _box(ax, 1.4, 6.5, 1.95, 1.0, "P3", "浅层细节", "#E8F3FF")
    _box(ax, 1.4, 4.35, 1.95, 1.0, "P4", "中层特征", "#E8F3FF")
    _box(ax, 1.4, 2.2, 1.95, 1.0, "P5", "深层语义", "#E8F3FF")

    # FPN 阶段
    _box(ax, 5.0, 2.35, 2.1, 1.05, "Upsample ×2", "对齐到 P4", "#FFE8CC")
    _box(ax, 5.0, 4.35, 2.2, 1.15, "Concat + C2f", "FPN 节点①", "#D6F5DE")

    _box(ax, 8.4, 5.55, 2.1, 1.05, "Upsample ×2", "对齐到 P3", "#FFE8CC")
    _box(ax, 8.4, 6.85, 2.2, 1.15, "Concat + C2f", "FPN 节点②\n高语义 P3", "#D6F5DE")

    # PAN 阶段（自下而上再融合）
    _box(ax, 11.5, 5.05, 2.15, 1.15, "Conv↓ + Concat\n+ C2f", "PAN 强化 P4", "#F5E8FF")
    _box(ax, 11.5, 2.85, 2.15, 1.15, "Conv↓ + Concat\n+ C2f", "PAN 强化 P5", "#F5E8FF")

    # 输出至 Head
    _box(ax, 13.85, 6.85, 1.85, 0.95, "→ Detect Head", "高分辨率支路\n（偏小目标）", "#FFD6E0")
    _box(ax, 13.85, 5.05, 1.85, 0.95, "→ Detect Head", "中尺度支路", "#FFD6E0")
    _box(ax, 13.85, 2.85, 1.85, 0.95, "→ Detect Head", "低分辨率支路\n（偏大目标）", "#FFD6E0")

    c_fpn = "#165DFF"
    c_pan = "#FF7D00"

    # P5 → Upsample
    _arrow(ax, 2.45, 2.2, 3.85, 2.35, c_fpn)
    _arrow(ax, 5.0, 2.9, 5.0, 3.75, c_fpn)
    # P4 → Concat①
    _arrow(ax, 2.45, 4.35, 3.85, 4.35, c_fpn)
    _arrow(ax, 5.0 + 1.1, 4.35, 6.1, 4.35, c_fpn)
    # Concat① → Upsample②
    _arrow(ax, 6.1, 4.85, 7.3, 5.2, c_fpn)
    _arrow(ax, 8.4, 5.05, 8.4, 6.2, c_fpn)
    # P3 → Concat②
    _arrow(ax, 2.45, 6.5, 7.2, 6.85, c_fpn)
    _arrow(ax, 8.4 + 1.1, 6.85, 9.5, 6.85, c_fpn)

    # PAN：自上向下
    _arrow(ax, 9.5, 6.5, 10.35, 5.35, c_pan)
    _arrow(ax, 11.5, 4.45, 11.5, 3.55, c_pan)
    _arrow(ax, 6.1, 4.15, 10.35, 3.2, c_pan)

    # 至 Head
    _arrow(ax, 12.55, 6.85, 12.85, 6.85, "#1D2129")
    _arrow(ax, 12.55, 5.05, 12.85, 5.05, "#1D2129")
    _arrow(ax, 12.55, 2.85, 12.85, 2.85, "#1D2129")

    ax.text(
        7.5,
        0.85,
        "说明：Neck 将 Backbone 的 P3、P4、P5 融合为更适合检测的多尺度表征；具体层数与模块命名以所用 Ultralytics YOLOv10 YAML 为准。\n"
        "图中为原理示意图，Detect Head（分类+回归）接在上述三路输出之后。",
        ha="center",
        fontsize=8.6,
        color="#86909C",
    )

    fig.tight_layout()
    fig.savefig(out, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main():
    root = Path(__file__).resolve().parent
    out_dir = root / "figures_framework"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "neck_architecture_yolov10_style.png"
    draw_neck(out)

    ch2 = root / "thesis_chapter2_figures"
    ch2.mkdir(parents=True, exist_ok=True)
    shutil.copy2(out, ch2 / "neck_architecture_yolov10_style.png")
    shutil.copy2(out, out_dir / "fig_neck.png")

    print("已生成:")
    print(" ", out.resolve())
    print(" ", (ch2 / "neck_architecture_yolov10_style.png").resolve())


if __name__ == "__main__":
    main()
