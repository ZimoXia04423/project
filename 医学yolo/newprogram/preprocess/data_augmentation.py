# -*- coding: utf-8 -*-
"""
data_augmentation.py - 数据增强模块
功能：对医学 X 光图像进行适度增强，提升模型泛化能力
包含：
1. 随机翻转与轻微旋转（增强体位变化的鲁棒性）
2. 亮度与对比度扰动（增强对曝光差异的适应性）
3. 随机缩放与平移（提升模型对位置变化的泛化能力）
4. Mosaic 增强（可选，需谨慎使用）
5. MixUp 增强（可选，需谨慎使用）

注意：医学图像增强需避免破坏医学结构语义
"""

import cv2
import numpy as np
from typing import Tuple, Optional, List
import random


class DataAugmenter:
    """医学 X 光图像数据增强器"""
    
    def __init__(
        self,
        # 翻转参数
        h_flip_prob: float = 0.5,
        v_flip_prob: float = 0.2,
        
        # 旋转参数
        rotation_range: Tuple[float, float] = (-15, 15),
        
        # 亮度对比度参数
        brightness_range: Tuple[float, float] = (0.8, 1.2),
        contrast_range: Tuple[float, float] = (0.8, 1.2),
        
        # 缩放平移参数
        scale_range: Tuple[float, float] = (0.9, 1.1),
        translate_range: Tuple[float, float] = (-0.1, 0.1),
        
        # Mosaic 参数
        use_mosaic: bool = False,
        mosaic_prob: float = 0.3,
        
        # MixUp 参数
        use_mixup: bool = False,
        mixup_prob: float = 0.2,
        mixup_alpha: float = 0.2
    ):
        """
        初始化数据增强器
        
        参数:
            h_flip_prob: 水平翻转概率，默认 0.5
            v_flip_prob: 垂直翻转概率，默认 0.2（医学图像谨慎使用）
            rotation_range: 旋转角度范围（度），默认 (-15, 15)
            brightness_range: 亮度缩放范围，默认 (0.8, 1.2)
            contrast_range: 对比度缩放范围，默认 (0.8, 1.2)
            scale_range: 缩放比例范围，默认 (0.9, 1.1)
            translate_range: 平移比例范围，默认 (-0.1, 0.1)
            use_mosaic: 是否使用 Mosaic 增强，默认 False
            mosaic_prob: Mosaic 增强概率，默认 0.3
            use_mixup: 是否使用 MixUp 增强，默认 False
            mixup_prob: MixUp 增强概率，默认 0.2
            mixup_alpha: MixUp 分布参数，默认 0.2
        """
        self.h_flip_prob = h_flip_prob
        self.v_flip_prob = v_flip_prob
        self.rotation_range = rotation_range
        self.brightness_range = brightness_range
        self.contrast_range = contrast_range
        self.scale_range = scale_range
        self.translate_range = translate_range
        self.use_mosaic = use_mosaic
        self.mosaic_prob = mosaic_prob
        self.use_mixup = use_mixup
        self.mixup_prob = mixup_prob
        self.mixup_alpha = mixup_alpha
    
    def augment(self, image: np.ndarray, boxes: Optional[np.ndarray] = None) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """
        对单张图像进行数据增强
        
        参数:
            image: 输入图像（H, W, C）
            boxes: 标注框数组 (N, 4) [x_min, y_min, x_max, y_max]，可选
            
        返回:
            (增强后的图像，增强后的标注框)
        """
        # 如果启用 Mosaic，且满足概率条件
        if self.use_mosaic and random.random() < self.mosaic_prob:
            # Mosaic 需要 4 张图像，这里简化处理
            pass
        
        # 如果启用 MixUp，且满足概率条件
        if self.use_mixup and random.random() < self.mixup_prob:
            # MixUp 需要另一张图像，这里简化处理
            pass
        
        # 1. 随机翻转
        augmented = self._apply_flip(image)
        if boxes is not None:
            boxes = self._apply_flip_boxes(boxes, augmented.shape)
        
        # 2. 随机旋转
        augmented, transform_matrix = self._apply_rotation(augmented)
        if boxes is not None:
            boxes = self._apply_transform_boxes(boxes, transform_matrix, augmented.shape)
        
        # 3. 亮度对比度扰动
        augmented = self._apply_brightness_contrast(augmented)
        
        # 4. 随机缩放平移
        augmented, transform_matrix = self._apply_scale_translate(augmented)
        if boxes is not None:
            boxes = self._apply_transform_boxes(boxes, transform_matrix, augmented.shape)
        
        return augmented, boxes
    
    def _apply_flip(self, image: np.ndarray) -> np.ndarray:
        """应用随机翻转"""
        # 水平翻转
        if random.random() < self.h_flip_prob:
            image = cv2.flip(image, 1)  # 1 = 水平翻转
        
        # 垂直翻转（医学图像谨慎使用）
        if random.random() < self.v_flip_prob:
            image = cv2.flip(image, 0)  # 0 = 垂直翻转
        
        return image
    
    def _apply_flip_boxes(self, boxes: np.ndarray, image_shape: Tuple) -> np.ndarray:
        """翻转标注框"""
        h, w = image_shape[:2]
        boxes = boxes.copy()
        
        # 水平翻转
        if random.random() < self.h_flip_prob:
            x_min = w - boxes[:, 2]
            x_max = w - boxes[:, 0]
            boxes[:, 0] = x_min
            boxes[:, 2] = x_max
        
        # 垂直翻转
        if random.random() < self.v_flip_prob:
            y_min = h - boxes[:, 3]
            y_max = h - boxes[:, 1]
            boxes[:, 1] = y_min
            boxes[:, 3] = y_max
        
        return boxes
    
    def _apply_rotation(self, image: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        应用随机旋转
        
        返回:
            (旋转后的图像，变换矩阵)
        """
        angle = random.uniform(*self.rotation_range)
        h, w = image.shape[:2]
        center = (w / 2, h / 2)
        
        # 获取旋转矩阵
        matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        
        # 应用旋转
        rotated = cv2.warpAffine(
            image,
            matrix,
            (w, h),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_REFLECT
        )
        
        return rotated, matrix
    
    def _apply_brightness_contrast(self, image: np.ndarray) -> np.ndarray:
        """应用亮度和对比度扰动"""
        # 亮度调整
        brightness_factor = random.uniform(*self.brightness_range)
        image = cv2.multiply(image, brightness_factor)
        
        # 对比度调整
        contrast_factor = random.uniform(*self.contrast_range)
        image = cv2.addWeighted(image, contrast_factor, image, 0, 0)
        
        # 裁剪到 [0, 255]
        image = np.clip(image, 0, 255).astype(np.uint8)
        
        return image
    
    def _apply_scale_translate(self, image: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        应用随机缩放和平移
        
        返回:
            (变换后的图像，变换矩阵)
        """
        h, w = image.shape[:2]
        
        # 随机缩放
        scale = random.uniform(*self.scale_range)
        
        # 随机平移
        tx = random.uniform(*self.translate_range) * w
        ty = random.uniform(*self.translate_range) * h
        
        # 构建仿射变换矩阵
        matrix = np.array([
            [scale, 0, tx],
            [0, scale, ty]
        ], dtype=np.float32)
        
        # 应用变换
        transformed = cv2.warpAffine(
            image,
            matrix,
            (w, h),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_REFLECT
        )
        
        return transformed, matrix
    
    def _apply_transform_boxes(self, boxes: np.ndarray, matrix: np.ndarray, image_shape: Tuple) -> np.ndarray:
        """应用仿射变换到标注框"""
        h, w = image_shape[:2]
        boxes = boxes.copy()
        
        # 扩展矩阵为 3x3
        if matrix.shape[0] == 2:
            matrix = np.vstack([matrix, [0, 0, 1]])
        
        # 变换每个框的四个角点
        new_boxes = []
        for box in boxes:
            x_min, y_min, x_max, y_max = box
            
            # 四个角点
            corners = np.array([
                [x_min, y_min, 1],
                [x_max, y_min, 1],
                [x_max, y_max, 1],
                [x_min, y_max, 1]
            ]).T
            
            # 应用变换
            transformed = matrix @ corners
            
            # 计算新边界框
            x_min_new = max(0, np.min(transformed[0]))
            y_min_new = max(0, np.min(transformed[1]))
            x_max_new = min(w, np.max(transformed[0]))
            y_max_new = min(h, np.max(transformed[1]))
            
            new_boxes.append([x_min_new, y_min_new, x_max_new, y_max_new])
        
        return np.array(new_boxes)
    
    def apply_mosaic(self, images: List[np.ndarray], boxes_list: List[np.ndarray]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Mosaic 增强：将 4 张图像拼接成一张
        
        参数:
            images: 4 张图像列表
            boxes_list: 对应的标注框列表
            
        返回:
            (Mosaic 图像，合并的标注框)
        """
        if len(images) != 4:
            raise ValueError("Mosaic 需要 4 张图像")
        
        h, w = images[0].shape[:2]
        
        # 创建输出图像
        mosaic = np.zeros((h * 2, w * 2, 3), dtype=np.uint8)
        
        # 随机裁剪点
        xc = int(random.uniform(w * 0.4, w * 0.6))
        yc = int(random.uniform(h * 0.4, h * 0.6))
        
        # 放置 4 张图像
        # 左上
        mosaic[0:yc, 0:xc] = cv2.resize(images[0], (xc, yc))
        # 右上
        mosaic[0:yc, xc:w*2] = cv2.resize(images[1], (w-xc, yc))
        # 左下
        mosaic[yc:h*2, 0:xc] = cv2.resize(images[2], (xc, h-yc))
        # 右下
        mosaic[yc:h*2, xc:w*2] = cv2.resize(images[3], (w-xc, h-yc))
        
        # 合并标注框（简化处理，需要调整坐标）
        all_boxes = []
        for i, boxes in enumerate(boxes_list):
            if boxes is None or len(boxes) == 0:
                continue
            
            # 根据位置调整坐标
            offset_x = 0 if i % 2 == 0 else w
            offset_y = 0 if i < 2 else h
            scale = 0.5  # 因为图像被缩小了一半
            
            for box in boxes:
                new_box = [
                    (box[0] * scale) + offset_x,
                    (box[1] * scale) + offset_y,
                    (box[2] * scale) + offset_x,
                    (box[3] * scale) + offset_y
                ]
                all_boxes.append(new_box)
        
        return mosaic, np.array(all_boxes) if all_boxes else np.empty((0, 4))
    
    def apply_mixup(
        self,
        image1: np.ndarray,
        image2: np.ndarray,
        boxes1: Optional[np.ndarray] = None,
        boxes2: Optional[np.ndarray] = None
    ) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """
        MixUp 增强：混合两张图像
        
        参数:
            image1, image2: 两张图像
            boxes1, boxes2: 对应的标注框
            
        返回:
            (混合后的图像，合并的标注框)
        """
        # 生成混合权重
        lam = np.random.beta(self.mixup_alpha, self.mixup_alpha)
        
        # 混合图像
        mixed = cv2.addWeighted(image1, lam, image2, 1 - lam, 0)
        
        # 合并标注框（简化处理）
        if boxes1 is not None and boxes2 is not None:
            all_boxes = np.vstack([boxes1, boxes2])
        elif boxes1 is not None:
            all_boxes = boxes1
        elif boxes2 is not None:
            all_boxes = boxes2
        else:
            all_boxes = None
        
        return mixed, all_boxes
    
    def get_config(self) -> dict:
        """获取数据增强器配置"""
        return {
            'h_flip_prob': self.h_flip_prob,
            'v_flip_prob': self.v_flip_prob,
            'rotation_range': self.rotation_range,
            'brightness_range': self.brightness_range,
            'contrast_range': self.contrast_range,
            'scale_range': self.scale_range,
            'translate_range': self.translate_range,
            'use_mosaic': self.use_mosaic,
            'mosaic_prob': self.mosaic_prob,
            'use_mixup': self.use_mixup,
            'mixup_prob': self.mixup_prob,
            'mixup_alpha': self.mixup_alpha
        }
