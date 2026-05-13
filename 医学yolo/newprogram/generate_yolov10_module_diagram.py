# -*- coding: utf-8 -*-
"""
生成与「Ultralytics / YOLO 论文风格」相近的分支结构图：
三路并行 X0 / X1 / X2，每路为上、下两支 CBS + Conv2d 再 Concat，块上为卷积参数、下为通道×空间尺寸。
运行：python generate_yolov10_module_diagram.py
输出：figures_framework/yolov10_style_parallel_heads.png
"""
from __future__ import annotations

import shutil
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch


def _setup():
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False


def _draw_box(ax, cx, cy, w, h, title, param_line, dim_line, face, edge, title_size=9):
    x, y = cx - w / 2, cy - h / 2
    r = mpatches.FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.01,rounding_size=0.06",
        linewidth=1.35,
        edgecolor=edge,
        facecolor=face,
    )
    ax.add_patch(r)
    ax.text(cx, cy + h * 0.28, param_line, ha="center", va="center", fontsize=7.2, color="#4E5969")
    ax.text(cx, cy + h * 0.02, title, ha="center", va="center", fontsize=title_size, fontweight="bold", color="#1D2129")
    ax.text(cx, cy - h * 0.30, dim_line, ha="center", va="center", fontsize=7.2, color="#4E5969")


def _arrow(ax, x1, y1, x2, y2):
    ax.add_patch(
        FancyArrowPatch(
            (x1, y1),
            (x2, y2),
            arrowstyle="-|>",
            mutation_scale=10,
            linewidth=1.05,
            color="#1D2129",
            shrinkA=2,
            shrinkB=2,
        )
    )


def _draw_row(
    ax,
    cy: float,
    name: str,
    in_dim: str,
    spat: str,
    out_dim: str,
    bottom_conv_ch: str,
):
    """
    单行：Input → 上支 (CBS,CBS,Conv2d) + 下支 (CBS×4,Conv2d) → Concat → Output
    spat 例如 "80 × 60"，用于中间特征图文字。
    """
    blue_fill, blue_edge = "#D8ECFF", "#165DFF"
    orange_fill, orange_edge = "#FFE8CC", "#D97706"
    white_fill, black_edge = "#FFFFFF", "#1D2129"

    x0 = 0.55
    # 输入
    _draw_box(ax, x0 + 0.55, cy, 1.15, 0.72, name, "", in_dim, blue_fill, blue_edge, title_size=10)

    split_x = x0 + 1.35
    upper_y = cy + 0.62
    lower_y = cy - 0.62

    # 上支：2×CBS + Conv2d
    ux = [2.35, 3.55, 4.75]
    _draw_box(ax, ux[0], upper_y, 0.72, 0.58, "CBS", "3, 1, 1", f"64 × {spat}", orange_fill, orange_edge)
    _draw_box(ax, ux[1], upper_y, 0.72, 0.58, "CBS", "3, 1, 1", f"64 × {spat}", orange_fill, orange_edge)
    _draw_box(ax, ux[2], upper_y, 0.72, 0.58, "Conv2d", "1, 1, 0", f"64 × {spat}", white_fill, black_edge)

    # 下支：4×CBS + Conv2d（通道按参考图示意）
    lx = [2.35, 3.35, 4.35, 5.35, 6.55]
    chs = [
        f"192 × {spat}",
        f"192 × {spat}",
        f"128 × {spat}",
        f"96 × {spat}",
    ]
    for i in range(4):
        _draw_box(ax, lx[i], lower_y, 0.72, 0.58, "CBS", "3, 1, 1", chs[i], orange_fill, orange_edge)
    _draw_box(
        ax,
        lx[4],
        lower_y,
        0.72,
        0.58,
        "Conv2d",
        "1, 1, 0",
        f"{bottom_conv_ch} × {spat}",
        white_fill,
        black_edge,
    )

    cx_concat = 8.05
    _draw_box(ax, cx_concat, cy, 0.82, 0.62, "Concat", "dim=1", f"144 × {spat}", white_fill, black_edge)

    cx_out = 9.55
    _draw_box(ax, cx_out, cy, 1.05, 0.72, name, "", out_dim, blue_fill, blue_edge, title_size=10)

    # 连线：输入 → 分叉
    _arrow(ax, x0 + 1.05, cy, split_x, upper_y)
    _arrow(ax, x0 + 1.05, cy, split_x, lower_y)

    # 上支链
    _arrow(ax, split_x + 0.05, upper_y, ux[0] - 0.38, upper_y)
    for a, b in zip(ux[:-1], ux[1:]):
        _arrow(ax, a + 0.38, upper_y, b - 0.38, upper_y)
    _arrow(ax, ux[-1] + 0.38, upper_y, cx_concat - 0.48, cy + 0.18)

    # 下支链
    _arrow(ax, split_x + 0.05, lower_y, lx[0] - 0.38, lower_y)
    for a, b in zip(lx[:-1], lx[1:]):
        _arrow(ax, a + 0.38, lower_y, b - 0.38, lower_y)
    _arrow(ax, lx[-1] + 0.38, lower_y, cx_concat - 0.48, cy - 0.18)

    _arrow(ax, cx_concat + 0.45, cy, cx_out - 0.58, cy)


def draw_figure(out: Path) -> None:
    _setup()
    fig, ax = plt.subplots(figsize=(14.5, 8.2))
    ax.set_xlim(0, 10.8)
    ax.set_ylim(0, 8.6)
    ax.axis("off")

    ax.text(
        5.4,
        8.28,
        "多尺度并行分支结构示意图（X0 / X1 / X2）",
        ha="center",
        fontsize=14,
        fontweight="bold",
        color="#1D2129",
    )
    ax.text(
        5.4,
        7.85,
        "风格参照：浅蓝 I/O、橙色 CBS、白底 Conv2d / Concat；块上方为卷积参数，下方为特征维度（示意）。",
        ha="center",
        fontsize=9,
        color="#4E5969",
    )

    # 三路纵向排布（与参考图一致的量级）
    _draw_row(
        ax,
        6.35,
        "X0",
        "1 × 192 × 80 × 60",
        "80 × 60",
        "1 × 144 × 80 × 60",
        "80",
    )
    _draw_row(
        ax,
        4.05,
        "X1",
        "1 × 384 × 40 × 30",
        "40 × 30",
        "1 × 144 × 40 × 30",
        "80",
    )
    _draw_row(
        ax,
        1.75,
        "X2",
        "1 × 576 × 20 × 15",
        "20 × 15",
        "1 × 144 × 20 × 15",
        "80",
    )

    ax.text(
        5.4,
        0.42,
        "说明：本图为论文用示意拓扑，通道与空间尺寸与参考风格对齐；若需与某一版 yolov10.yaml 完全一致，请以官方配置为准可对通道数微调。\n"
        "cv2/cv3 等代码索引可在定稿时用小字标注于对应 Conv2d 旁。",
        ha="center",
        fontsize=8.2,
        color="#86909C",
    )

    fig.tight_layout()
    fig.savefig(out, dpi=240, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main():
    root = Path(__file__).resolve().parent
    out_dir = root / "figures_framework"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "yolov10_style_parallel_heads.png"
    draw_figure(out)

    ch2 = root / "thesis_chapter2_figures"
    ch2.mkdir(parents=True, exist_ok=True)
    shutil.copy2(out, ch2 / "yolov10_style_parallel_heads.png")
    shutil.copy2(out, out_dir / "fig_parallel_x012.png")

    print("已生成:", out.resolve())


if __name__ == "__main__":
    main()
