# 电商平台用户评论虚假信息识别模型构建与比较研究

## 项目简介

本项目围绕电商平台用户评论虚假信息识别展开，构建并对比了多种机器学习和深度学习模型，从准确率、精确率、召回率、F1值、AUC、运行效率等多维度进行全面比较分析。

## 项目结构

```
├── main.py                 # 主程序（一键运行全流程）
├── dashboard.html           # 可视化仪表盘（浏览器打开）
├── requirements.txt         # Python依赖
├── README.md
├── data/
│   ├── stopwords.txt        # 停用词表
│   └── ecommerce_reviews.csv # 生成的数据集（运行后生成）
├── src/
│   ├── data_generator.py    # 数据生成模块
│   ├── preprocessing.py     # 文本预处理模块
│   ├── feature_extraction.py # 特征提取模块
│   ├── ml_models.py         # 机器学习模型
│   ├── dl_models.py         # 深度学习模型
│   ├── evaluation.py        # 模型评估与可视化
│   ├── interpretability.py  # 可解释性分析(LIME/SHAP)
│   └── robustness.py        # 鲁棒性分析
└── output/                  # 输出目录（运行后生成）
    ├── metrics.json          # 评估指标JSON
    ├── metrics_comparison.png
    ├── roc_curves.png
    ├── confusion_matrices.png
    ├── time_comparison.png
    ├── training_losses.png
    ├── robustness_analysis.png
    ├── shap_feature_importance.png
    └── lime_explanation_*.png
```

## 模型列表

| 类型 | 模型 | 说明 |
|------|------|------|
| 机器学习 | 逻辑回归 (LR) | 线性分类基线模型 |
| 机器学习 | 支持向量机 (SVM) | RBF核的非线性分类 |
| 机器学习 | 随机森林 (RF) | 集成学习-Bagging |
| 机器学习 | XGBoost | 集成学习-Boosting |
| 深度学习 | TextCNN | 多尺度卷积提取N-gram特征 |
| 深度学习 | BiLSTM | 双向长短期记忆网络 |
| 深度学习 | Transformer | 基于自注意力机制 |

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 运行主程序

```bash
python main.py
```

运行完成后，所有图表和结果数据将保存在 `output/` 目录下。

### 3. 查看可视化仪表盘

用浏览器直接打开 `dashboard.html` 即可查看所有结果图表和对比数据。

## 评估维度

- **准确率 (Accuracy)**: 整体预测正确率
- **精确率 (Precision)**: 预测为虚假评论中的正确比例
- **召回率 (Recall)**: 实际虚假评论被正确识别的比例
- **F1值**: 精确率和召回率的调和平均
- **AUC**: ROC曲线下面积
- **训练/预测时间**: 运行效率对比
- **鲁棒性**: 不同噪声级别下的性能衰减
- **可解释性**: LIME局部解释 + SHAP全局特征重要性
