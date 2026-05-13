# -*- coding: utf-8 -*-
"""从 runs 目录 results.csv 生成论文用训练/验证曲线图。"""
import csv
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib

matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False


def load_results(csv_path: Path):
    epochs, prec, rec, m50, m5095 = [], [], [], [], []
    with csv_path.open(newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            try:
                ep = int(float(row["epoch"]))
            except (KeyError, ValueError):
                continue
            epochs.append(ep)

            def fkey(*keys):
                for k in keys:
                    if k in row and row[k] not in ("", "nan", None):
                        try:
                            v = float(row[k])
                            if v == v:  # not NaN
                                return v
                        except ValueError:
                            pass
                return None

            prec.append(fkey("metrics/precision(B)", "precision"))
            rec.append(fkey("metrics/recall(B)", "recall"))
            m50.append(fkey("metrics/mAP50(B)", "mAP50(B)"))
            m5095.append(fkey("metrics/mAP50-95(B)", "mAP50-95(B)"))
    return epochs, prec, rec, m50, m5095


def plot_metrics(out_dir: Path, title_zh: str, stem_en: str, csv_path: Path):
    epochs, prec, rec, m50, m5095 = load_results(csv_path)
    if not epochs:
        return
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(epochs, m50, label="mAP@0.5", color="#165DFF", linewidth=1.8)
    ax.plot(epochs, m5095, label="mAP@0.5:0.95", color="#00B42A", linewidth=1.8)
    ax.set_xlabel("Epoch")
    ax.set_ylabel("指标值")
    ax.set_title(f"{title_zh} 验证集 mAP 随训练轮次变化")
    ax.legend(loc="lower right")
    ax.grid(True, alpha=0.3)
    ax.set_xlim(left=1)
    fig.tight_layout()
    p = out_dir / f"{stem_en}_map_curve.png"
    fig.savefig(p, dpi=200)
    plt.close(fig)
    print("saved:", p)


def main():
    base = Path(__file__).resolve().parent
    out = base / "figures"
    out.mkdir(parents=True, exist_ok=True)
    runs = base.parent / "newprogram" / "runs"
    pairs = [
        ("YOLOv10 训练", "yolov10_train", runs / "yolov10" / "results.csv"),
        ("YOLOv8 训练", "yolov8_train", runs / "yolov8" / "results.csv"),
    ]
    for title_zh, stem_en, csv_path in pairs:
        if csv_path.is_file():
            plot_metrics(out, title_zh, stem_en, csv_path)
        else:
            print("skip (missing):", csv_path)


if __name__ == "__main__":
    main()
