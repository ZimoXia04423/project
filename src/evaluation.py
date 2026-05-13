"""
模型评估与对比模块：计算各项指标并生成对比图表
"""
import os
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import seaborn as sns
from sklearn.metrics import (accuracy_score, precision_score, recall_score, 
                             f1_score, roc_auc_score, confusion_matrix,
                             roc_curve, classification_report)


# 设置中文字体
plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


def evaluate_model(y_true, y_pred, y_prob=None):
    """
    计算单个模型的评估指标
    
    Returns:
        dict: 各项评估指标
    """
    metrics = {
        "accuracy": round(accuracy_score(y_true, y_pred), 4),
        "precision": round(precision_score(y_true, y_pred), 4),
        "recall": round(recall_score(y_true, y_pred), 4),
        "f1": round(f1_score(y_true, y_pred), 4),
    }
    if y_prob is not None:
        metrics["auc"] = round(roc_auc_score(y_true, y_prob), 4)
    return metrics


def evaluate_all_models(results, y_true):
    """
    评估所有模型并汇总结果
    
    Parameters:
        results: {model_name: {y_pred, y_prob, train_time, predict_time, ...}}
        y_true: 真实标签
    
    Returns:
        DataFrame: 所有模型的评估指标对比表
    """
    all_metrics = []
    for name, res in results.items():
        metrics = evaluate_model(y_true, res["y_pred"], res.get("y_prob"))
        metrics["model"] = name
        metrics["train_time"] = res["train_time"]
        metrics["predict_time"] = res["predict_time"]
        all_metrics.append(metrics)
    
    df_metrics = pd.DataFrame(all_metrics)
    cols = ["model", "accuracy", "precision", "recall", "f1", "auc", 
            "train_time", "predict_time"]
    existing_cols = [c for c in cols if c in df_metrics.columns]
    df_metrics = df_metrics[existing_cols]
    
    print("\n" + "=" * 80)
    print("模型评估结果对比")
    print("=" * 80)
    print(df_metrics.to_string(index=False))
    print("=" * 80)
    
    return df_metrics


def plot_metrics_comparison(df_metrics, output_dir="output"):
    """绘制模型指标对比柱状图"""
    os.makedirs(output_dir, exist_ok=True)
    
    metric_cols = ["accuracy", "precision", "recall", "f1"]
    existing_metrics = [c for c in metric_cols if c in df_metrics.columns]
    
    fig, ax = plt.subplots(figsize=(12, 6))
    x = np.arange(len(df_metrics))
    width = 0.18
    
    colors = ["#4C78A8", "#F58518", "#E45756", "#72B7B2"]
    for i, metric in enumerate(existing_metrics):
        bars = ax.bar(x + i * width, df_metrics[metric], width, 
                      label=metric.upper(), color=colors[i], alpha=0.85)
        for bar, val in zip(bars, df_metrics[metric]):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.005,
                    f"{val:.3f}", ha="center", va="bottom", fontsize=7)
    
    ax.set_xlabel("模型")
    ax.set_ylabel("指标值")
    ax.set_title("各模型识别性能指标对比")
    ax.set_xticks(x + width * 1.5)
    ax.set_xticklabels(df_metrics["model"], rotation=15, ha="right")
    ax.legend(loc="lower right")
    ax.set_ylim(0, 1.15)
    ax.grid(axis="y", alpha=0.3)
    
    plt.tight_layout()
    path = os.path.join(output_dir, "metrics_comparison.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"指标对比图已保存: {path}")
    return path


def plot_roc_curves(results, y_true, output_dir="output"):
    """绘制所有模型的ROC曲线"""
    os.makedirs(output_dir, exist_ok=True)
    
    fig, ax = plt.subplots(figsize=(8, 6))
    colors = plt.cm.Set2(np.linspace(0, 1, len(results)))
    
    for (name, res), color in zip(results.items(), colors):
        if res.get("y_prob") is not None:
            fpr, tpr, _ = roc_curve(y_true, res["y_prob"])
            auc_val = roc_auc_score(y_true, res["y_prob"])
            ax.plot(fpr, tpr, color=color, lw=2, 
                    label=f"{name} (AUC={auc_val:.3f})")
    
    ax.plot([0, 1], [0, 1], "k--", lw=1, alpha=0.5)
    ax.set_xlabel("假正率 (FPR)")
    ax.set_ylabel("真正率 (TPR)")
    ax.set_title("ROC曲线对比")
    ax.legend(loc="lower right", fontsize=8)
    ax.grid(alpha=0.3)
    
    plt.tight_layout()
    path = os.path.join(output_dir, "roc_curves.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"ROC曲线图已保存: {path}")
    return path


def plot_confusion_matrices(results, y_true, output_dir="output"):
    """绘制所有模型的混淆矩阵"""
    os.makedirs(output_dir, exist_ok=True)
    
    n_models = len(results)
    cols = min(4, n_models)
    rows = (n_models + cols - 1) // cols
    
    fig, axes = plt.subplots(rows, cols, figsize=(4 * cols, 4 * rows))
    if n_models == 1:
        axes = np.array([axes])
    axes = axes.flatten() if hasattr(axes, "flatten") else [axes]
    
    for idx, (name, res) in enumerate(results.items()):
        cm = confusion_matrix(y_true, res["y_pred"])
        sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", ax=axes[idx],
                    xticklabels=["真实", "虚假"], yticklabels=["真实", "虚假"])
        axes[idx].set_title(name, fontsize=10)
        axes[idx].set_xlabel("预测标签")
        axes[idx].set_ylabel("真实标签")
    
    # 隐藏多余的子图
    for idx in range(n_models, len(axes)):
        axes[idx].set_visible(False)
    
    plt.suptitle("各模型混淆矩阵", fontsize=14)
    plt.tight_layout()
    path = os.path.join(output_dir, "confusion_matrices.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"混淆矩阵图已保存: {path}")
    return path


def plot_time_comparison(df_metrics, output_dir="output"):
    """绘制训练/预测时间对比图"""
    os.makedirs(output_dir, exist_ok=True)
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    
    colors = plt.cm.Set3(np.linspace(0, 1, len(df_metrics)))
    
    # 训练时间（横轴上限随最大值留出边距，避免长条被裁切）
    train_max = float(df_metrics["train_time"].max())
    pred_max = float(df_metrics["predict_time"].max())
    train_xlim = max(train_max * 1.15, train_max + 1e-6)
    pred_xlim = max(pred_max * 1.25, pred_max + 1e-6)

    bars1 = ax1.barh(df_metrics["model"], df_metrics["train_time"], color=colors)
    ax1.set_xlabel("训练时间 (秒)")
    ax1.set_title("模型训练时间对比")
    ax1.set_xlim(0, train_xlim)
    for bar, val in zip(bars1, df_metrics["train_time"]):
        ax1.text(bar.get_width() + 0.01, bar.get_y() + bar.get_height() / 2,
                f"{val:.3f}s", va="center", fontsize=9)
    
    # 预测时间
    bars2 = ax2.barh(df_metrics["model"], df_metrics["predict_time"], color=colors)
    ax2.set_xlabel("预测时间 (秒)")
    ax2.set_title("模型预测时间对比")
    ax2.set_xlim(0, pred_xlim)
    for bar, val in zip(bars2, df_metrics["predict_time"]):
        ax2.text(bar.get_width() + max(pred_xlim * 0.002, 0.001), bar.get_y() + bar.get_height() / 2,
                f"{val:.3f}s", va="center", fontsize=9)
    
    plt.tight_layout()
    path = os.path.join(output_dir, "time_comparison.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"时间对比图已保存: {path}")
    return path


def plot_training_losses(dl_results, output_dir="output"):
    """绘制深度学习模型的训练损失曲线，并导出 dl_losses.json 便于单独重绘"""
    os.makedirs(output_dir, exist_ok=True)
    
    losses_export = {}
    for name, res in dl_results.items():
        if "losses" in res and res["losses"]:
            losses_export[name] = [float(x) for x in res["losses"]]
    if losses_export:
        json_path = os.path.join(output_dir, "dl_losses.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(losses_export, f, ensure_ascii=False, indent=2)
        print(f"深度学习训练损失已导出: {json_path}")
    
    fig, ax = plt.subplots(figsize=(8, 5))
    for name, res in dl_results.items():
        if "losses" in res and res["losses"]:
            ax.plot(range(1, len(res["losses"]) + 1), res["losses"], 
                    marker="o", markersize=4, label=name, linewidth=2)
    
    ax.set_xlabel("训练轮次 (Epoch)")
    ax.set_ylabel("训练损失 (Loss)")
    ax.set_title("深度学习模型训练损失曲线")
    ax.legend()
    ax.grid(alpha=0.3)
    
    plt.tight_layout()
    path = os.path.join(output_dir, "training_losses.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"训练损失曲线已保存: {path}")
    return path


def save_metrics_to_json(df_metrics, output_dir="output"):
    """将评估结果保存为JSON文件"""
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, "metrics.json")
    records = df_metrics.to_dict(orient="records")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    print(f"评估结果JSON已保存: {path}")
    return path
