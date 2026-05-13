# 4.6 评价指标设计（公式版 — 可直接复制到 Word）

> 使用说明：用 Cursor / 记事本 / VS Code 打开本文件，全选复制到 Word 后，公式块可改为 Word「插入 → 公式」逐条录入；文末附「纯文本公式行」便于直接粘贴。

---

## 4.6 评价指标设计

为全面评估模型性能，本文从检测正确性、综合排序质量与推理效率三个层面选取指标。检测任务中，预测框与真实框需先通过交并比（Intersection over Union，IoU）判定是否匹配，再统计真正例、假正例与假负例，进而计算 Precision、Recall、F1；在 IoU 阈值固定或步进变化下，由精确率—召回率曲线面积得到 AP，再对所有类别取平均得到 mAP。此外，本文以 FPS 或单张图像推理时间衡量实时性。

### 4.6.1 交并比 IoU

设某类目标的真实框为 \(B^{\mathrm{gt}}\)，模型预测框为 \(B^{\mathrm{pred}}\)，则二者交并比定义为：

\[
\mathrm{IoU}\bigl(B^{\mathrm{pred}}, B^{\mathrm{gt}}\bigr)=\frac{\bigl|B^{\mathrm{pred}}\cap B^{\mathrm{gt}}\bigr|}{\bigl|B^{\mathrm{pred}}\cup B^{\mathrm{gt}}\bigr|}.
\]

在给定 IoU 阈值（如 0.5）下，若某预测框与匹配的真实框满足 IoU ≥ τ，且该真实框尚未被其它更高置信度预测占用，则记为一次成功检测（TP）；否则记为 FP。若某真实框未被任何满足阈值的预测匹配，则记为 FN。

### 4.6.2 精确率、召回率与 F1 分数

在由 TP、FP、FN 构成的混淆统计意义下，精确率表示预测为正的样本中实际为正的比例，召回率表示所有实际为正样本中被正确检出的比例：

\[
\mathrm{Precision}=\frac{\mathrm{TP}}{\mathrm{TP}+\mathrm{FP}},\qquad
\mathrm{Recall}=\frac{\mathrm{TP}}{\mathrm{TP}+\mathrm{FN}}.
\]

F1 分数为精确率与召回率的调和平均，用于在二者不可同时最优时给出单一标量评价：

\[
\mathrm{F1}=\frac{2\cdot \mathrm{Precision}\cdot \mathrm{Recall}}{\mathrm{Precision}+\mathrm{Recall}}
=\frac{2\,\mathrm{TP}}{2\,\mathrm{TP}+\mathrm{FP}+\mathrm{FN}}.
\]

### 4.6.3 平均精度 AP 与 mAP

对某一类别，在给定 IoU 阈值下，按置信度从高到低排序预测框，可绘制精确率—召回率（P-R）曲线。该曲线下的面积即为该类别的平均精度（Average Precision，AP）：

\[
\mathrm{AP}=\int_{0}^{1} P(R)\,\mathrm{d}R,
\]

其中 \(P(R)\) 为召回率为 R 时对应的最大精确率（或按 COCO 等基准采用的插值/采样规则计算，与 Ultralytics 等工具默认实现一致即可）。

设类别数为 K，mAP@0.5 表示在 IoU = 0.5 阈值下各类别 AP 的算术平均：

\[
\mathrm{mAP@0.5}=\frac{1}{K}\sum_{k=1}^{K}\mathrm{AP}_k\bigl|_{\tau=0.5}.
\]

mAP@0.5:0.95（常记作 mAP@[.5:.95]）表示在 τ ∈ {0.50, 0.55, …, 0.95} 共 10 个 IoU 阈值上分别计算 mAP，再取平均，用于更严格地评价框定位精度：

\[
\mathrm{mAP@0.5:0.95}=\frac{1}{10}\sum_{\tau\in\{0.50,\ldots,0.95\}}
\left(\frac{1}{K}\sum_{k=1}^{K}\mathrm{AP}_k\bigl|_{\mathrm{IoU}=\tau}\right).
\]

### 4.6.4 推理速度

FPS（Frames Per Second）定义为每秒可完成推理的图像帧数；若单张图像推理时间为 T（秒），则近似有 FPS = 1/T。本文在相同软硬件环境下记录单图推理时间或 FPS，用于对比不同模型的实时性。

---

## 与原文六条列表的对应（可选保留在 4.6 开头）

1. 精确率（Precision）：见式（4.6.2-1）前一式。  
2. 召回率（Recall）：见式（4.6.2-1）后一式。  
3. F1 分数（F1-score）：见式（4.6.2-2）。  
4. mAP@0.5：见式（4.6.3-2）。  
5. mAP@0.5:0.95：见式（4.6.3-3）。  
6. FPS 或单张推理时间：见 4.6.4。

（定稿时请将「式（4.6.x）」改为学校模板要求的编号，如「式（4-1）」。）

---

## 纯文本公式行（便于直接粘到 Word 正文）

IoU = |B_pred ∩ B_gt| / |B_pred ∪ B_gt|

Precision = TP / (TP + FP)

Recall = TP / (TP + FN)

F1 = 2 × Precision × Recall / (Precision + Recall) = 2×TP / (2×TP + FP + FN)

AP = ∫_0^1 P(R) dR

mAP@0.5 = (1/K) × Σ AP_k（在 IoU=0.5 下）

mAP@0.5:0.95 = 对 τ=0.50,0.55,…,0.95 共 10 档 IoU 分别算各类 AP 再平均，最后对 10 档再取平均

FPS ≈ 1 / T（T 为单张推理时间，单位：秒）
