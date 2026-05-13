# -*- coding: utf-8 -*-
"""
image_preprocess.py - 图像预处理模块
功能：对 X 光图像进行标准化预处理，增强骨折特征
包含：
1. 灰度归一化：统一像素值范围 [0, 255]
2. CLAHE 增强：提升骨皮质边界清晰度
3. 尺寸标准化：缩放至模型输入尺寸（默认 640x640）
4. 噪声抑制：中值滤波去除随机噪声
"""

import cv2
import numpy as np
from typing import Tuple, Optional


class ImagePreprocessor:
    """X 光图像预处理器"""
    
    def __init__(
        self,
        target_size: Tuple[int, int] = (640, 640),
        clip_limit: float = 2.0,
        grid_size: Tuple[int, int] = (8, 8),
        use_denoise: bool = True,
        denoise_strength: float = 0.6
    ):
        """
        初始化预处理器
        
        参数:
            target_size: 目标尺寸 (宽，高)，默认 640x640
            clip_limit: CLAHE 对比度限制，默认 2.0
            grid_size: CLAHE 网格大小 (宽，高)，默认 8x8
            use_denoise: 是否使用中值滤波去噪，默认 True
            denoise_strength: 去噪强度 (0-1)，默认 0.6
        """
        self.target_size = target_size
        self.clip_limit = clip_limit
        self.grid_size = grid_size
        self.use_denoise = use_denoise
        self.denoise_strength = denoise_strength
        
        # 创建 CLAHE 对象
        self.clahe = cv2.createCLAHE(
            clipLimit=clip_limit,
            tileGridSize=grid_size
        )
    
    def preprocess(self, image: np.ndarray) -> np.ndarray:
        """
        完整预处理流程
        
        参数:
            image: 输入图像（BGR 或灰度）
            
        返回:
            预处理后的图像（RGB，尺寸标准化）
        """
        # 1. 灰度化（如果是彩色图像）
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # 2. 灰度归一化到 [0, 255]
        normalized = self._normalize_grayscale(gray)
        
        # 3. CLAHE 对比度增强
        enhanced = self.clahe.apply(normalized)
        
        # 4. 噪声抑制（可选）
        if self.use_denoise:
            denoised = self._denoise(enhanced)
        else:
            denoised = enhanced
        
        # 5. 尺寸标准化
        resized = cv2.resize(
            denoised,
            self.target_size,
            interpolation=cv2.INTER_LINEAR
        )
        
        # 6. 转换为 RGB 三通道（模型输入要求）
        result = cv2.cvtColor(resized, cv2.COLOR_GRAY2RGB)
        
        return result
    
    def _normalize_grayscale(self, image: np.ndarray) -> np.ndarray:
        """
        灰度归一化：将像素值映射到 [0, 255]
        
        参数:
            image: 灰度图像
            
        返回:
            归一化后的图像
        """
        min_val = np.min(image)
        max_val = np.max(image)
        
        # 避免除零
        if max_val - min_val < 1e-6:
            return np.zeros_like(image, dtype=np.uint8)
        
        # 线性映射到 [0, 255]
        normalized = (image - min_val) / (max_val - min_val) * 255.0
        return normalized.astype(np.uint8)
    
    def _denoise(self, image: np.ndarray) -> np.ndarray:
        """
        中值滤波去噪
        
        参数:
            image: 输入图像
            
        返回:
            去噪后的图像
        """
        # 根据强度计算内核大小
        kernel_size = int(3 + self.denoise_strength * 2)
        if kernel_size % 2 == 0:
            kernel_size += 1
        
        denoised = cv2.medianBlur(image, kernel_size)
        return denoised
    
    def preprocess_batch(self, image_paths: list) -> np.ndarray:
        """
        批量预处理图像
        
        参数:
            image_paths: 图像路径列表
            
        返回:
            预处理后的图像数组 (N, H, W, C)
        """
        images = []
        for path in image_paths:
            image = cv2.imread(path)
            if image is not None:
                processed = self.preprocess(image)
                images.append(processed)
        
        return np.array(images, dtype=np.uint8)
    
    def get_config(self) -> dict:
        """获取预处理器配置"""
        return {
            'target_size': self.target_size,
            'clip_limit': self.clip_limit,
            'grid_size': self.grid_size,
            'use_denoise': self.use_denoise,
            'denoise_strength': self.denoise_strength
        }
