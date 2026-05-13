"""
模型可解释性分析模块：使用LIME和SHAP解释模型决策
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


def lime_explain(model, X_train_tfidf, X_test_tfidf, vectorizer, 
                 test_texts, y_test, n_samples=5, output_dir="output"):
    """
    使用LIME对机器学习模型进行可解释性分析
    
    Parameters:
        model: 训练好的sklearn模型
        X_train_tfidf: 训练集TF-IDF特征
        X_test_tfidf: 测试集TF-IDF特征
        vectorizer: TF-IDF向量化器
        test_texts: 测试集文本
        y_test: 测试集标签
        n_samples: 解释的样本数量
        output_dir: 输出目录
    """
    try:
        from lime.lime_text import LimeTextExplainer
    except ImportError:
        print("LIME未安装，跳过LIME可解释性分析")
        return None
    
    os.makedirs(output_dir, exist_ok=True)
    
    explainer = LimeTextExplainer(class_names=["真实评论", "虚假评论"])
    
    def predict_fn(texts):
        tfidf = vectorizer.transform(texts)
        return model.predict_proba(tfidf)
    
    # 选择一些典型样本进行解释
    indices = []
    # 选择正确分类和错误分类的样本
    y_pred = model.predict(X_test_tfidf)
    correct_idx = np.where(y_pred == y_test)[0]
    wrong_idx = np.where(y_pred != y_test)[0]
    
    if len(correct_idx) > 0:
        indices.extend(np.random.choice(correct_idx, min(3, len(correct_idx)), replace=False))
    if len(wrong_idx) > 0:
        indices.extend(np.random.choice(wrong_idx, min(2, len(wrong_idx)), replace=False))
    
    if not indices:
        indices = list(range(min(n_samples, len(test_texts))))
    
    explanations_data = []
    for i, idx in enumerate(indices[:n_samples]):
        text = test_texts.iloc[idx] if hasattr(test_texts, "iloc") else test_texts[idx]
        exp = explainer.explain_instance(text, predict_fn, num_features=10)
        
        # 保存解释图
        fig = exp.as_pyplot_figure()
        fig.set_size_inches(10, 5)
        plt.title(f"LIME解释 - 样本{i+1} (真实标签: {'虚假' if y_test.iloc[idx] else '真实'})")
        plt.tight_layout()
        path = os.path.join(output_dir, f"lime_explanation_{i+1}.png")
        plt.savefig(path, dpi=150, bbox_inches="tight")
        plt.close()
        
        exp_list = exp.as_list()
        explanations_data.append({
            "sample_index": int(idx),
            "true_label": "虚假" if (y_test.iloc[idx] if hasattr(y_test, "iloc") else y_test[idx]) else "真实",
            "text_snippet": text[:80],
            "top_features": [{"word": w, "weight": round(float(s), 4)} for w, s in exp_list[:10]]
        })
    
    print(f"LIME解释已保存到 {output_dir}")
    return explanations_data


def shap_explain(model, X_train_combined, X_test_combined, feature_names,
                 output_dir="output", n_background=100):
    """
    使用SHAP对机器学习模型进行可解释性分析
    优先使用TreeExplainer（树模型）或LinearExplainer（线性模型）
    
    Parameters:
        model: 训练好的sklearn模型
        X_train_combined: 训练集特征矩阵
        X_test_combined: 测试集特征矩阵
        feature_names: 特征名列表
        output_dir: 输出目录
        n_background: 背景样本数量
    """
    try:
        import shap
    except ImportError:
        print("SHAP未安装，跳过SHAP可解释性分析")
        return None
    
    os.makedirs(output_dir, exist_ok=True)
    
    n_test = min(100, X_test_combined.shape[0])
    X_test_sub = X_test_combined[:n_test]
    
    print("正在计算SHAP值...")
    
    # 根据模型类型选择最合适的Explainer
    model_type = type(model).__name__
    try:
        if model_type in ("RandomForestClassifier", "XGBClassifier", 
                          "GradientBoostingClassifier"):
            explainer = shap.TreeExplainer(model)
            shap_values = explainer.shap_values(X_test_sub)
        else:
            # 通用方法：用较小的背景集
            n_bg = min(n_background, X_train_combined.shape[0])
            X_bg = X_train_combined[:n_bg]
            if hasattr(X_bg, "toarray"):
                X_bg = X_bg.toarray()
            if hasattr(X_test_sub, "toarray"):
                X_test_sub = X_test_sub.toarray()
            explainer = shap.KernelExplainer(model.predict_proba, X_bg)
            shap_values = explainer.shap_values(X_test_sub, nsamples=50)
    except Exception as e:
        print(f"  SHAP Explainer失败 ({e})，使用KernelExplainer重试...")
        n_bg = min(50, X_train_combined.shape[0])
        X_bg = X_train_combined[:n_bg]
        if hasattr(X_bg, "toarray"):
            X_bg = X_bg.toarray()
        if hasattr(X_test_sub, "toarray"):
            X_test_sub = X_test_sub.toarray()
        explainer = shap.KernelExplainer(model.predict_proba, X_bg)
        shap_values = explainer.shap_values(X_test_sub, nsamples=50)
    
    # 取虚假评论类别(label=1)的SHAP值
    if isinstance(shap_values, list):
        shap_vals = shap_values[1]
    elif shap_values.ndim == 3:
        shap_vals = shap_values[:, :, 1]
    else:
        shap_vals = shap_values
    
    if hasattr(shap_vals, "toarray"):
        shap_vals = shap_vals.toarray()
    shap_vals = np.array(shap_vals)
    
    # 绘制SHAP摘要图 - 选择前20个重要特征
    mean_abs_shap = np.mean(np.abs(shap_vals), axis=0)
    n_top = min(20, len(mean_abs_shap))
    top_indices = np.argsort(mean_abs_shap)[-n_top:]
    
    if feature_names and len(feature_names) >= max(top_indices) + 1:
        top_names = [feature_names[i] for i in top_indices]
    else:
        top_names = [f"特征_{i}" for i in top_indices]
    
    fig, ax = plt.subplots(figsize=(11, 9))
    ax.barh(range(len(top_indices)), mean_abs_shap[top_indices], color="#4C78A8")
    ax.set_yticks(range(len(top_indices)))
    # Y 轴为中文 n-gram 与英文特征名混排，字号过小难辨认
    ax.set_yticklabels(top_names, fontsize=11)
    ax.set_xlabel("平均 |SHAP值|", fontsize=12)
    ax.set_title("SHAP特征重要性排名 (Top 20)", fontsize=14, pad=12)
    ax.tick_params(axis="x", labelsize=11)
    ax.grid(axis="x", alpha=0.3)
    
    plt.tight_layout()
    path = os.path.join(output_dir, "shap_feature_importance.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    
    print(f"SHAP分析结果已保存到 {output_dir}")
    
    return {
        "top_features": [{"name": n, "importance": round(float(mean_abs_shap[i]), 6)} 
                         for n, i in zip(top_names, top_indices)]
    }
