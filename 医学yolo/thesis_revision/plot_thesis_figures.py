# -*- coding: utf-8 -*-
"""
论文 5.3.2 性能测试相关图：从 Ultralytics results.csv 画训练曲线；
表 5-3 多模型对比柱状图（数据与正文表一致时请自行核对修改 TABLE53）。
运行：在 thesis_revision 目录下执行
    python plot_thesis_figures.py
输出：thesis_revision/figures/ 下 PNG。
"""
from __future__ import annotations

import csv
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False

# 与论文表 5-3 一致时请核对；若你实测不同，只改此字典即可重画图。
TABLE53 = [
    ("Faster R-CNN", 89.4, 83.6, 88.7, 61.8, 82),
    ("SSD", 82.1, 76.5, 80.3, 53.4, 19),
    ("YOLOv5", 88.2, 85.1, 90.5, 64.9, 12),
    ("YOLOv8", 89.6, 87.4, 91.9, 67.8, 11),
    ("原生YOLOv10", 90.1, 88.0, 92.4, 68.6, 9),
    ("改进YOLOv10", 92.3, 90.8, 94.1, 71.9, 10),
]


def _fkey(row: dict, *keys: str):
    for k in keys:
        if k in row and row[k] not in ("", "nan", None):
            try:
                v = float(row[k])
                if v == v:
                    return v
            except ValueError:
                pass
    return None


def load_results(csv_path: Path):
    epochs, prec, rec, m50, m5095 = [], [], [], [], []
    t_box, t_cls, t_dfl = [], [], []
    v_box, v_cls, v_dfl = [], [], []
    with csv_path.open(newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            try:
                ep = int(float(row["epoch"]))
            except (KeyError, ValueError):
                continue
            epochs.append(ep)
            prec.append(_fkey(row, "metrics/precision(B)", "precision"))
            rec.append(_fkey(row, "metrics/recall(B)", "recall"))
            m50.append(_fkey(row, "metrics/mAP50(B)", "mAP50(B)"))
            m5095.append(_fkey(row, "metrics/mAP50-95(B)", "mAP50-95(B)"))
            t_box.append(_fkey(row, "train/box_loss"))
            t_cls.append(_fkey(row, "train/cls_loss"))
            t_dfl.append(_fkey(row, "train/dfl_loss"))
            v_box.append(_fkey(row, "val/box_loss"))
            v_cls.append(_fkey(row, "val/cls_loss"))
            v_dfl.append(_fkey(row, "val/dfl_loss"))
    return {
        "epoch": epochs,
        "precision": prec,
        "recall": rec,
        "mAP50": m50,
        "mAP5095": m5095,
        "train_box": t_box,
        "train_cls": t_cls,
        "train_dfl": t_dfl,
        "val_box": v_box,
        "val_cls": v_cls,
        "val_dfl": v_dfl,
    }


def _mask_series(epochs, series):
    x, y = [], []
    for e, v in zip(epochs, series):
        if v is not None:
            x.append(e)
            y.append(v * 100 if v <= 1.5 else v)  # 0~1 视为比例转百分比
    return x, y


def plot_training_metrics_panel(data: dict, out_path: Path, title: str):
    """Precision / Recall / mAP@0.5 / mAP@0.5:0.95 随 epoch，四子图。"""
    ep = data["epoch"]
    if not ep:
        return
    fig, axes = plt.subplots(2, 2, figsize=(10, 8))
    pairs = [
        (axes[0, 0], "Precision", data["precision"], "#165DFF"),
        (axes[0, 1], "Recall", data["recall"], "#00B42A"),
        (axes[1, 0], "mAP@0.5", data["mAP50"], "#722ED1"),
        (axes[1, 1], "mAP@0.5:0.95", data["mAP5095"], "#FF7D00"),
    ]
    for ax, name, ser, c in pairs:
        x, y = _mask_series(ep, ser)
        if not x:
            ax.set_visible(False)
            continue
        ax.plot(x, y, color=c, linewidth=1.6)
        ax.set_xlabel("Epoch")
        ax.set_ylabel("数值 (%)" if y and max(y) <= 100 else "数值")
        ax.set_title(name)
        ax.grid(True, alpha=0.3)
        ax.set_xlim(left=1)
    fig.suptitle(title, fontsize=14, y=1.02)
    fig.tight_layout()
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("saved:", out_path)


def plot_loss_curves(data: dict, out_path: Path, title: str):
    ep = data["epoch"]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for label, ser, c in [
        ("train/box_loss", data["train_box"], "#165DFF"),
        ("train/cls_loss", data["train_cls"], "#00B42A"),
        ("val/box_loss", data["val_box"], "#F77234"),
        ("val/cls_loss", data["val_cls"], "#722ED1"),
    ]:
        x, y = [], []
        for e, v in zip(ep, ser):
            if v is not None:
                x.append(e)
                y.append(v)
        if x:
            ax.plot(x, y, label=label, linewidth=1.4, color=c)
    ax.set_xlabel("Epoch")
    ax.set_ylabel("Loss")
    ax.set_title(title)
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("saved:", out_path)


def plot_table53_grouped_bars(out_path: Path):
    """表 5-3：各模型 Precision、Recall、mAP@0.5、mAP@0.5:0.95 分组柱状图。"""
    names = [r[0] for r in TABLE53]
    prec = [r[1] for r in TABLE53]
    rec = [r[2] for r in TABLE53]
    m50 = [r[3] for r in TABLE53]
    m95 = [r[4] for r in TABLE53]
    x = np.arange(len(names))
    w = 0.2
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.bar(x - 1.5 * w, prec, w, label="Precision (%)", color="#165DFF")
    ax.bar(x - 0.5 * w, rec, w, label="Recall (%)", color="#00B42A")
    ax.bar(x + 0.5 * w, m50, w, label="mAP@0.5 (%)", color="#722ED1")
    ax.bar(x + 1.5 * w, m95, w, label="mAP@0.5:0.95 (%)", color="#FF7D00")
    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=15, ha="right")
    ax.set_ylabel("百分比 / %")
    ax.set_title("不同检测模型性能对比（与表 5-3 对应）")
    ax.legend(loc="lower right", ncol=2)
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("saved:", out_path)


def plot_inference_time_bars(out_path: Path):
    """单张推理时间（ms）；可由 ms 换算 FPS=1000/ms 标在柱顶。"""
    names = [r[0] for r in TABLE53]
    ms = [r[5] for r in TABLE53]
    fig, ax = plt.subplots(figsize=(10, 4.5))
    colors = ["#86909C"] * (len(names) - 1) + ["#165DFF"]
    x = np.arange(len(names))
    bars = ax.bar(x, ms, color=colors, edgecolor="#1d2129", linewidth=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=15, ha="right")
    ax.set_ylabel("单张推理时间 / ms")
    ax.set_title("各模型单张图像推理时延对比")
    for b, t in zip(bars, ms):
        fps = 1000.0 / t if t > 0 else 0
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 1, f"{t}ms\n({fps:.0f} FPS)", ha="center", va="bottom", fontsize=8)
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("saved:", out_path)


def main():
    base = Path(__file__).resolve().parent
    out = base / "figures"
    out.mkdir(parents=True, exist_ok=True)
    runs = base.parent / "newprogram" / "runs"

    for tag, csv_rel in [("yolov10", "yolov10/results.csv"), ("yolov8", "yolov8/results.csv")]:
        csv_path = runs / csv_rel
        if not csv_path.is_file():
            print("skip (missing):", csv_path)
            continue
        d = load_results(csv_path)
        plot_training_metrics_panel(
            d,
            out / f"{tag}_training_precision_recall_map.png",
            f"{tag.upper()} 验证集指标随 Epoch 变化",
        )
        plot_loss_curves(
            d,
            out / f"{tag}_training_loss.png",
            f"{tag.upper()} 训练/验证 Loss 曲线",
        )

    plot_table53_grouped_bars(out / "table53_models_comparison_bars.png")
    plot_inference_time_bars(out / "table53_inference_time_fps.png")
    print("完成。PR 曲线：results.csv 不含逐阈值 PR 点，需在 val 结束后使用 Ultralytics 导出的 PR 图或运行 yolo detect val ... 生成。")


if __name__ == "__main__":
    main()
