# -*- coding: utf-8 -*-
"""
visualize_effects.py - 生成可视化效果图
展示图像预处理和数据增强的实际效果。

说明：create_test_image() 使用的是「合成矩形伪影 + 噪声」，仅便于肉眼看清几何/颜色类增强，
并非医学影像；论文 4.1.3 插图请使用 demo_with_real_image.py 导出的真实 X 光图
（thesis_figures_4_1/fig_4_1_3_real_xray_augmentation.jpg）。
"""

import sys
import cv2
import numpy as np
from pathlib import Path
from datetime import datetime

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from preprocess import ImagePreprocessor, DataAugmenter


def create_test_image():
    """创建测试 X 光图像（模拟）"""
    # 创建一个模拟的 X 光图像（灰度）
    img = np.ones((640, 640), dtype=np.uint8) * 50
    
    # 添加一些模拟的骨骼结构
    cv2.rectangle(img, (200, 100), (440, 540), 150, -1)
    cv2.rectangle(img, (250, 150), (390, 490), 120, -1)
    
    # 添加一些噪声
    noise = np.random.randint(0, 30, (640, 640), dtype=np.uint8)
    img = cv2.add(img, noise)
    
    # 转换为 BGR
    img_bgr = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    
    return img_bgr


def visualize_preprocessing():
    """可视化图像预处理效果"""
    print("\n" + "="*60)
    print("生成图像预处理效果图")
    print("="*60)
    
    # 创建测试图像
    original = create_test_image()
    
    # 创建预处理器（不同参数）
    preprocessors = {
        '原始图像': None,
        '灰度归一化': ImagePreprocessor(clip_limit=1.0, use_denoise=False),
        'CLAHE 增强': ImagePreprocessor(clip_limit=2.0, use_denoise=False),
        'CLAHE+ 去噪': ImagePreprocessor(clip_limit=2.0, use_denoise=True),
        '完整预处理': ImagePreprocessor(clip_limit=2.0, use_denoise=True)
    }
    
    # 处理图像
    results = []
    for name, preprocessor in preprocessors.items():
        if preprocessor is None:
            results.append(original)
        else:
            processed = preprocessor.preprocess(original)
            results.append(processed)
    
    # 拼接图像（横向排列）
    # 调整所有图像为相同大小
    target_size = (400, 400)
    resized = []
    for img in results:
        resized_img = cv2.resize(img, target_size)
        # 添加标题
        cv2.putText(resized_img, name, (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        resized.append(resized_img)
    
    # 横向拼接
    combined = np.hstack(resized)
    
    # 保存
    save_dir = Path('visualization_results')
    save_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    save_path = save_dir / f'preprocessing_effect_{timestamp}.jpg'
    cv2.imwrite(str(save_path), combined)
    
    print(f"[OK] 预处理效果图已保存到：{save_path}")
    print(f"     图像尺寸：{combined.shape}")
    
    return save_path


def visualize_augmentation():
    """可视化数据增强效果"""
    print("\n" + "="*60)
    print("生成数据增强效果图")
    print("="*60)
    
    # 创建测试图像
    original = create_test_image()
    
    # 创建增强器
    augmenter = DataAugmenter(
        h_flip_prob=0.5,
        v_flip_prob=0.2,
        rotation_range=(-30, 30),
        brightness_range=(0.7, 1.3),
        contrast_range=(0.7, 1.3),
        scale_range=(0.8, 1.2),
        translate_range=(-0.15, 0.15)
    )
    
    # 生成多个增强样本
    n_samples = 12
    augmented_images = [original]
    
    for i in range(n_samples - 1):
        aug_img, _ = augmenter.augment(original)
        augmented_images.append(aug_img)
    
    # 调整大小
    target_size = (200, 200)
    resized = []
    for i, img in enumerate(augmented_images):
        resized_img = cv2.resize(img, target_size)
        if i == 0:
            label = 'Original'
        else:
            label = f'Aug {i}'
        cv2.putText(resized_img, label, (10, 25),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        resized.append(resized_img)
    
    # 排列成 3x4 网格
    rows = []
    for i in range(3):
        row_imgs = resized[i*4:(i+1)*4]
        row = np.hstack(row_imgs)
        rows.append(row)
    
    combined = np.vstack(rows)
    
    # 保存
    save_dir = Path('visualization_results')
    save_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    save_path = save_dir / f'augmentation_effect_{timestamp}.jpg'
    cv2.imwrite(str(save_path), combined)
    
    print(f"[OK] 数据增强效果图已保存到：{save_path}")
    print(f"     图像尺寸：{combined.shape}")
    
    return save_path


def visualize_detection_simulation():
    """模拟可视化检测结果"""
    print("\n" + "="*60)
    print("生成检测结果模拟图")
    print("="*60)
    
    # 创建测试图像
    original = create_test_image()
    
    # 模拟检测结果
    detections = [
        {'class_id': 0, 'class_name': 'fracture', 'confidence': 0.95, 
         'bbox': [250, 200, 390, 280]},
        {'class_id': 1, 'class_name': 'periostealreaction', 'confidence': 0.87,
         'bbox': [260, 300, 380, 360]},
        {'class_id': 3, 'class_name': 'softtissue', 'confidence': 0.76,
         'bbox': [240, 400, 400, 480]}
    ]
    
    # 颜色映射
    colors = {
        0: (0, 0, 255),       # 红色 - fracture
        1: (0, 165, 255),     # 橙色 - periostealreaction
        2: (0, 255, 0),       # 绿色 - pronatorsign
        3: (255, 0, 0)        # 蓝色 - softtissue
    }
    
    # 绘制检测框
    vis_image = original.copy()
    for det in detections:
        x1, y1, x2, y2 = map(int, det['bbox'])
        class_id = det['class_id']
        class_name = det['class_name']
        confidence = det['confidence']
        
        color = colors.get(class_id, (255, 255, 255))
        
        # 绘制矩形框
        cv2.rectangle(vis_image, (x1, y1), (x2, y2), color, 3)
        
        # 绘制标签
        label = f"{class_name}: {confidence:.2f}"
        label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
        
        # 标签背景
        cv2.rectangle(
            vis_image,
            (x1, y1 - label_size[1] - 10),
            (x1 + label_size[0] + 10, y1),
            color,
            -1
        )
        
        # 标签文字
        cv2.putText(
            vis_image,
            label,
            (x1 + 5, y1 - 5),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2
        )
    
    # 添加骨折等级判定
    grade_text = "骨折等级：重度骨折"
    cv2.putText(vis_image, grade_text, (20, 50),
               cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)
    
    # 保存
    save_dir = Path('visualization_results')
    save_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    save_path = save_dir / f'detection_result_{timestamp}.jpg'
    cv2.imwrite(str(save_path), vis_image)
    
    print(f"[OK] 检测结果图已保存到：{save_path}")
    
    return save_path


def main():
    """生成所有可视化效果图"""
    print("\n" + "="*60)
    print("骨折检测系统 - 可视化效果图生成器")
    print("="*60)
    
    try:
        # 生成效果图
        preproc_path = visualize_preprocessing()
        aug_path = visualize_augmentation()
        detect_path = visualize_detection_simulation()
        
        print("\n" + "="*60)
        print("所有效果图已生成完毕！")
        print("="*60)
        print(f"\n1. 预处理效果：{preproc_path}")
        print(f"2. 数据增强效果：{aug_path}")
        print(f"3. 检测结果模拟：{detect_path}")
        print("\n请在文件资源管理器中打开查看。")
        print("="*60 + "\n")
        
        # 尝试用默认程序打开
        try:
            import os
            os.startfile(str(preproc_path))
        except:
            pass
        
    except Exception as e:
        print(f"\n[ERROR] 生成失败：{e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
