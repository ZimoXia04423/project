# -*- coding: utf-8 -*-
"""
生成论文 3.4 / 3.5 节可用的框架示意图（PNG），便于在 Word 外先预览或手动插入。
运行：在项目根目录执行
    python generate_framework_figures.py
输出：figures_framework/ 目录下 PNG 文件。
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


def draw_system_architecture(out: Path) -> None:
    """3.4 系统总体架构：四层 + 右侧业务流水线。"""
    _setup_zh()
    fig, ax = plt.subplots(figsize=(12, 7.2))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 9)
    ax.axis("off")

    ax.text(
        6,
        8.55,
        "系统总体架构示意图（四层结构）",
        ha="center",
        fontsize=16,
        fontweight="bold",
        color="#1D2129",
    )

    layers = [
        (6.15, "表现层（Presentation）", "PyQt5 图形界面 · 操作入口 · 结果展示"),
        (4.85, "服务层（Service）", "模型加载 · 图像预处理 · 结果后处理 · 文件存储"),
        (3.55, "算法层（Algorithm）", "改进 YOLOv10 · 训练 / 验证 / 推理 · 预处理与增强模块"),
        (2.25, "数据层（Data）", "原始影像 · 标注文件 · 训练集 / 验证集 / 测试集"),
    ]
    colors = ["#D6EFFF", "#D6F5DE", "#EAD9FF", "#FFE8CC"]
    y_positions = []
    for idx, (yc, title, sub) in enumerate(layers):
        y_box = yc - 0.42
        rect = mpatches.FancyBboxPatch(
            (1.2, y_box),
            6.8,
            1.05,
            boxstyle="round,pad=0.02,rounding_size=0.12",
            linewidth=1.8,
            edgecolor="#1D2129",
            facecolor=colors[idx],
        )
        ax.add_patch(rect)
        ax.text(4.6, y_box + 0.72, title, ha="center", va="center", fontsize=13, fontweight="bold")
        ax.text(4.6, y_box + 0.32, sub, ha="center", va="center", fontsize=9.5, color="#4E5969")
        y_positions.append(y_box + 0.52)

    for i in range(len(y_positions) - 1):
        ax.annotate(
            "",
            xy=(4.6, y_positions[i + 1] + 0.55),
            xytext=(4.6, y_positions[i] - 0.55),
            arrowprops=dict(arrowstyle="-|>", color="#1D2129", lw=2, mutation_scale=14),
        )

    ax.text(
        9.65,
        7.1,
        "典型业务流程",
        ha="center",
        fontsize=12,
        fontweight="bold",
    )
    pipeline = [
        "原始数据采集与预处理",
        "数据集划分与标签转换",
        "模型训练与权重保存",
        "推理服务调用",
        "可视化结果输出",
        "用户查看与导出",
    ]
    py = 6.55
    for i, step in enumerate(pipeline):
        ax.text(8.55, py, f"{i + 1}. {step}", fontsize=9.2, va="top", color="#1D2129")
        py -= 0.82
        if i < len(pipeline) - 1:
            ax.annotate(
                "",
                xy=(8.55, py + 0.72),
                xytext=(8.55, py + 1.05),
                arrowprops=dict(arrowstyle="-|>", color="#86909C", lw=1.2, mutation_scale=10),
            )

    ax.text(
        6,
        0.35,
        "说明：自上而下依次为表现层 → 服务层 → 算法层 → 数据层；右侧为与正文一致的端到端流程要点。",
        ha="center",
        fontsize=9,
        color="#86909C",
    )

    fig.tight_layout()
    fig.savefig(out, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def draw_module_structure(out: Path) -> None:
    """3.5 系统模块设计：目录模块及调用关系。"""
    _setup_zh()
    fig, ax = plt.subplots(figsize=(12, 7))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 8.5)
    ax.axis("off")

    ax.text(
        6,
        8.05,
        "系统模块结构示意图（代码目录与数据流）",
        ha="center",
        fontsize=16,
        fontweight="bold",
        color="#1D2129",
    )

    def box(cx, cy, w, h, title, lines, face):
        x, y = cx - w / 2, cy - h / 2
        r = mpatches.FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.02,rounding_size=0.1",
            linewidth=1.6,
            edgecolor="#1D2129",
            facecolor=face,
        )
        ax.add_patch(r)
        ax.text(cx, cy + h * 0.28, title, ha="center", va="center", fontsize=11.5, fontweight="bold")
        ax.text(cx, cy - 0.08, "\n".join(lines), ha="center", va="center", fontsize=8.8, color="#4E5969")

    box(3.0, 6.2, 2.5, 1.35, "datasets/", ["训练/验证/测试图像", "与 YOLO 标签"], "#FFE8CC")
    box(3.0, 4.35, 2.5, 1.35, "preprocess/", ["增强 · 格式转换", "数据集划分辅助"], "#EAD9FF")
    box(3.0, 2.5, 2.5, 1.35, "models/", ["改进 YOLOv10 配置", "注意力等模块定义"], "#D6F5DE")
    box(6.7, 5.3, 2.35, 1.25, "train/", ["训练入口", "参数与日志"], "#D6EFFF")
    box(6.7, 3.25, 2.35, 1.25, "infer/", ["批量推理", "结果绘制与导出"], "#D6EFFF")
    box(9.85, 4.28, 2.25, 1.55, "gui/", ["PyQt5 界面", "加载 infer / service"], "#FFD6E0")

    style = dict(arrowstyle="-|>", color="#4E5969", lw=1.6, mutation_scale=12)

    def arrow(p1, p2):
        ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle=style["arrowstyle"], color=style["color"], lw=style["lw"], mutation_scale=style["mutation_scale"]))

    arrow((3.9, 6.15), (4.35, 5.05))
    arrow((3.9, 4.45), (4.35, 4.85))
    arrow((4.35, 4.15), (5.45, 5.05))
    arrow((4.35, 3.85), (5.45, 3.45))
    arrow((7.85, 5.25), (8.65, 4.65))
    arrow((7.85, 3.35), (8.65, 4.0))

    ax.text(
        6,
        0.95,
        "说明：数据经 preprocess 进入训练 / 推理链路；gui 通过服务逻辑调用 infer 与模型权重，与正文「模块的设计」描述一致。",
        ha="center",
        fontsize=9,
        color="#86909C",
    )

    fig.tight_layout()
    fig.savefig(out, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main():
    out_dir = Path(__file__).resolve().parent / "figures_framework"
    out_dir.mkdir(parents=True, exist_ok=True)
    p1 = out_dir / "图3-4_系统总体架构示意图.png"
    p2 = out_dir / "图3-5_系统模块结构示意图.png"
    draw_system_architecture(p1)
    draw_module_structure(p2)
    shutil.copy2(p1, out_dir / "framework_system_architecture.png")
    shutil.copy2(p2, out_dir / "framework_module_structure.png")
    print("已生成（可直接双击预览）：")
    print(" ", p1.resolve())
    print(" ", p2.resolve())
    print("英文文件名副本：")
    print(" ", (out_dir / "framework_system_architecture.png").resolve())
    print(" ", (out_dir / "framework_module_structure.png").resolve())


if __name__ == "__main__":
    main()
