# -*- coding: utf-8 -*-
"""
demo_with_real_image.py - 使用真实图像演示效果
如果有真实的 X 光图像，使用真实图像；否则使用测试图像
"""

import sys
import cv2
import numpy as np
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from preprocess import ImagePreprocessor, DataAugmenter


def inpaint_edge_R_markers_bgr(
    img_bgr: np.ndarray,
    band_frac: float = 0.14,
    bright_thresh: int = 192,
    dilate_ksize: int = 7,
    inpaint_radius: int = 12,
) -> np.ndarray:
    """
    去除贴近图像边缘的高亮侧位标记（如右侧中部的白色「R/L」块）。
    用「距边缘 band 像素以内的带状区域 ∩ 高灰度」作掩膜再 inpaint；
    旋转/翻转增强后标记常落在任意一边，故扫描整圈边缘。
    """
    if img_bgr is None or img_bgr.size == 0:
        return img_bgr
    h, w = img_bgr.shape[:2]
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    band = max(32, int(min(h, w) * band_frac))
    yy, xx = np.indices((h, w))
    edge = (xx < band) | (xx >= w - band) | (yy < band) | (yy >= h - band)
    bright = gray >= bright_thresh
    mask = ((edge & bright).astype(np.uint8)) * 255
    if not np.any(mask):
        return img_bgr
    k = max(3, dilate_ksize | 1)
    mask = cv2.dilate(mask, np.ones((k, k), np.uint8), iterations=3)
    return cv2.inpaint(img_bgr, mask, inpaint_radius, cv2.INPAINT_TELEA)


def inpaint_edge_R_markers_rgb(img_rgb: np.ndarray, **kwargs) -> np.ndarray:
    """RGB（ImagePreprocessor 输出）版本。"""
    if img_rgb is None or img_rgb.size == 0:
        return img_rgb
    bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
    out = inpaint_edge_R_markers_bgr(bgr, **kwargs)
    return cv2.cvtColor(out, cv2.COLOR_BGR2RGB)


def find_test_images():
    """在测试图片目录中查找图像"""
    # 查找测试图片目录
    test_dirs = [
        Path('测试图片'),
        Path('yolo_dataset_final/images/val'),
        Path('yolo_dataset_final/images/train')
    ]
    
    for test_dir in test_dirs:
        if test_dir.exists():
            # 查找前 3 张图像
            images = []
            for ext in ['.jpg', '.jpeg', '.png', '.bmp']:
                images.extend(test_dir.glob(f'*{ext}'))
            
            if images:
                print(f"[OK] 找到测试图像目录：{test_dir}")
                return sorted(images)[:3]
    
    return None


def process_real_image(image_path):
    """处理真实图像并显示效果"""
    print(f"\n处理图像：{image_path.name}")
    print("-" * 60)
    
    # 读取图像
    original = cv2.imread(str(image_path))
    if original is None:
        print(f"[ERROR] 无法读取图像")
        return
    
    print(f"原始图像尺寸：{original.shape}")

    # 论文用图：去掉边缘 R/L 高亮水印（整圈边缘带状 inpaint）
    original = inpaint_edge_R_markers_bgr(original)
    
    # 创建预处理器
    preprocessor = ImagePreprocessor(
        target_size=(640, 640),
        clip_limit=2.0,
        use_denoise=True
    )
    
    # 预处理（RGB）；CLAHE 可能仍突出残余标记，再抹一轮边缘高亮
    processed = preprocessor.preprocess(original)
    processed = inpaint_edge_R_markers_rgb(processed)
    print(f"预处理后尺寸：{processed.shape}")
    
    # 创建增强器
    augmenter = DataAugmenter(
        h_flip_prob=0.5,
        rotation_range=(-15, 15),
        brightness_range=(0.8, 1.2)
    )
    
    # 生成 3 个增强样本
    augmented_list = []
    for i in range(3):
        aug_img, _ = augmenter.augment(original)
        aug_img = inpaint_edge_R_markers_bgr(aug_img)
        augmented_list.append(aug_img)
    
    # 拼接图像进行对比
    # 调整大小以便显示
    target_size = (400, 400)
    
    original_resized = cv2.resize(original, target_size)
    processed_bgr = cv2.cvtColor(processed, cv2.COLOR_RGB2BGR)
    processed_resized = cv2.resize(processed_bgr, target_size)
    # 缩放后标记有时仍会露头，再弱一轮
    original_resized = inpaint_edge_R_markers_bgr(
        original_resized, band_frac=0.16, bright_thresh=188
    )
    processed_resized = inpaint_edge_R_markers_bgr(
        processed_resized, band_frac=0.16, bright_thresh=188
    )

    # 第一行：原始 vs 预处理（BGR，不写标注）
    row1_top = np.hstack([original_resized.copy(), processed_resized.copy()])
    
    # 第二行：3 个增强样本（无标注）
    aug_resized = []
    for img in augmented_list:
        r = cv2.resize(img, target_size)
        r = inpaint_edge_R_markers_bgr(r, band_frac=0.16, bright_thresh=188)
        aug_resized.append(r)
    row2_imgs = list(aug_resized)
    
    row2_top = np.hstack(row2_imgs)
    
    # 合并所有行
    # 需要调整行高
    h1, w1 = row1_top.shape[:2]
    h2, w2 = row2_top.shape[:2]
    
    # 缩放第二行使宽度匹配
    row2_scaled = cv2.resize(row2_top, (w1, int(h2 * w1 / w2)))
    
    combined = np.vstack([row1_top, row2_scaled])
    
    # 保存结果
    save_dir = Path('demo_results')
    save_dir.mkdir(parents=True, exist_ok=True)
    
    save_path = save_dir / f'demo_{image_path.stem}.jpg'
    cv2.imwrite(str(save_path), combined)

    # 4.1.3 专用：真实 X 光「原图 + 增强」横排（非 visualize_effects 里的合成方格示意）
    thesis_dir = Path("thesis_figures_4_1")
    thesis_dir.mkdir(parents=True, exist_ok=True)
    aug_413 = np.hstack([original_resized] + aug_resized)
    p_413 = thesis_dir / "fig_4_1_3_real_xray_augmentation.jpg"
    cv2.imwrite(str(p_413), aug_413)
    
    print(f"[OK] 效果对比图已保存到：{save_path}")
    print(f"[OK] 4.1.3 真实增强示意（横排）：{p_413.resolve()}")
    print(f"     组合图像尺寸：{combined.shape}")
    
    # 尝试打开
    try:
        import os
        os.startfile(str(save_path))
    except:
        pass
    
    return save_path


def main():
    """主函数"""
    print("\n" + "="*60)
    print("骨折检测系统 - 真实图像效果演示")
    print("="*60)
    
    # 查找测试图像
    test_images = find_test_images()
    
    if test_images:
        print(f"找到 {len(test_images)} 张测试图像")
        
        # 处理第一张图像
        process_real_image(test_images[0])
        
        print("\n" + "="*60)
        print("演示完成！请查看生成的对比图。")
        print("="*60)
    else:
        print("[INFO] 未找到测试图像，将运行通用演示。")
        print("提示：可以将 X 光图像放入以下任一目录：")
        print("  - 测试图片/")
        print("  - yolo_dataset_final/images/val/")
        print("  - yolo_dataset_final/images/train/")
        
        # 运行通用可视化
        print("\n正在生成通用可视化效果图...")
        import subprocess
        subprocess.run([
            str(Path(sys.executable)),
            str(Path(__file__).parent / 'visualize_effects.py')
        ])


if __name__ == '__main__':
    main()
