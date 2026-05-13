"""
鲁棒性分析模块：通过对抗样本和噪声数据测试模型鲁棒性
"""
import os
import random
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


def add_text_noise(text, noise_level=0.1):
    """
    向文本中添加噪声（随机插入、删除、替换字符）
    
    Parameters:
        text: 原始文本
        noise_level: 噪声比例
    
    Returns:
        添加噪声后的文本
    """
    chars = list(text)
    n_changes = max(1, int(len(chars) * noise_level))
    
    noise_chars = list("的了是在有和就不人都一个上也很到说要去你会着没看好")
    
    for _ in range(n_changes):
        if not chars:
            break
        op = random.choice(["insert", "delete", "replace"])
        pos = random.randint(0, max(0, len(chars) - 1))
        
        if op == "insert":
            chars.insert(pos, random.choice(noise_chars))
        elif op == "delete" and len(chars) > 5:
            chars.pop(pos)
        elif op == "replace":
            chars[pos] = random.choice(noise_chars)
    
    return "".join(chars)


def generate_adversarial_samples(texts, labels, noise_level=0.1, seed=42):
    """生成对抗样本数据集"""
    random.seed(seed)
    noisy_texts = [add_text_noise(t, noise_level) for t in texts]
    return noisy_texts, labels


def robustness_test(model, vectorizer, original_texts, noisy_texts_dict, y_true,
                    manual_features=None, combine_fn=None):
    """
    对模型进行鲁棒性测试
    
    Parameters:
        model: 训练好的模型
        vectorizer: TF-IDF向量化器
        original_texts: 原始文本
        noisy_texts_dict: {noise_level: noisy_texts} 不同噪声级别的文本
        y_true: 真实标签
        manual_features: 手工特征（可选）
        combine_fn: 特征合并函数（可选）
    
    Returns:
        dict: {noise_level: {accuracy, precision, recall, f1}}
    """
    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
    
    results = {}
    
    # 原始数据表现
    X_orig = vectorizer.transform(original_texts)
    if manual_features is not None and combine_fn is not None:
        X_orig = combine_fn(X_orig, manual_features)
    y_pred_orig = model.predict(X_orig)
    results[0.0] = {
        "accuracy": round(accuracy_score(y_true, y_pred_orig), 4),
        "precision": round(precision_score(y_true, y_pred_orig), 4),
        "recall": round(recall_score(y_true, y_pred_orig), 4),
        "f1": round(f1_score(y_true, y_pred_orig), 4),
    }
    
    # 不同噪声级别的表现
    for noise_level, noisy_texts in noisy_texts_dict.items():
        X_noisy = vectorizer.transform(noisy_texts)
        if manual_features is not None and combine_fn is not None:
            X_noisy = combine_fn(X_noisy, manual_features)
        y_pred_noisy = model.predict(X_noisy)
        results[noise_level] = {
            "accuracy": round(accuracy_score(y_true, y_pred_noisy), 4),
            "precision": round(precision_score(y_true, y_pred_noisy), 4),
            "recall": round(recall_score(y_true, y_pred_noisy), 4),
            "f1": round(f1_score(y_true, y_pred_noisy), 4),
        }
    
    return results


def robustness_test_all_models(models_dict, vectorizer, original_texts, y_true,
                                noise_levels=(0.05, 0.1, 0.15, 0.2),
                                manual_features=None, combine_fn=None):
    """
    对所有模型进行鲁棒性测试
    
    Returns:
        dict: {model_name: {noise_level: metrics}}
    """
    # 生成不同噪声级别的数据
    noisy_texts_dict = {}
    for nl in noise_levels:
        noisy_texts, _ = generate_adversarial_samples(
            original_texts.tolist() if hasattr(original_texts, "tolist") else list(original_texts),
            y_true, noise_level=nl
        )
        noisy_texts_dict[nl] = noisy_texts
    
    all_results = {}
    for name, model in models_dict.items():
        print(f"  测试 {name} 的鲁棒性...")
        result = robustness_test(
            model, vectorizer, original_texts, noisy_texts_dict, y_true,
            manual_features, combine_fn
        )
        all_results[name] = result
    
    return all_results


def plot_robustness_results(all_results, output_dir="output"):
    """绘制鲁棒性测试结果图"""
    os.makedirs(output_dir, exist_ok=True)
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    # Accuracy vs Noise Level
    for name, results in all_results.items():
        noise_levels = sorted(results.keys())
        accuracies = [results[nl]["accuracy"] for nl in noise_levels]
        axes[0].plot(noise_levels, accuracies, marker="o", label=name, linewidth=2)
    
    axes[0].set_xlabel("噪声级别")
    axes[0].set_ylabel("准确率")
    axes[0].set_title("模型准确率随噪声级别变化")
    axes[0].legend(fontsize=8)
    axes[0].grid(alpha=0.3)
    
    # F1 vs Noise Level
    for name, results in all_results.items():
        noise_levels = sorted(results.keys())
        f1s = [results[nl]["f1"] for nl in noise_levels]
        axes[1].plot(noise_levels, f1s, marker="s", label=name, linewidth=2)
    
    axes[1].set_xlabel("噪声级别")
    axes[1].set_ylabel("F1值")
    axes[1].set_title("模型F1值随噪声级别变化")
    axes[1].legend(fontsize=8)
    axes[1].grid(alpha=0.3)
    
    plt.tight_layout()
    path = os.path.join(output_dir, "robustness_analysis.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"鲁棒性分析图已保存: {path}")
    return path
