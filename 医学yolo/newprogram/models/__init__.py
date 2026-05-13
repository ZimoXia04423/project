# -*- coding: utf-8 -*-
"""
models 模块 - 算法层
功能：负责改进 YOLOv10 模型的配置与定义
包含：
1. YOLOv10 模型配置
2. 注意力机制模块定义
3. 模型加载与保存
"""

import torch
import torch.nn as nn
from pathlib import Path
from typing import Optional, Dict
from ultralytics import YOLO


class ModelLoader:
    """模型加载器"""
    
    def __init__(self, weights_dir: str = 'weights'):
        """
        初始化模型加载器
        
        参数:
            weights_dir: 权重文件目录
        """
        self.weights_dir = Path(weights_dir)
        self.weights_dir.mkdir(parents=True, exist_ok=True)
        
        # 支持的模型配置
        self.model_configs = {
            'yolov8': 'yolov8.pt',
            'yolov10': 'yolov10.pt',
        }
    
    def load_model(
        self,
        model_type: str = 'yolov10',
        weights_path: Optional[str] = None,
        pretrained: bool = True
    ) -> YOLO:
        """
        加载 YOLO 模型
        
        参数:
            model_type: 模型类型 ('yolov8' 或 'yolov10')
            weights_path: 权重文件路径（可选，默认使用预训练）
            pretrained: 是否使用预训练权重
            
        返回:
            YOLO 模型实例
        """
        if weights_path and Path(weights_path).exists():
            # 加载自定义权重
            model = YOLO(weights_path)
        elif pretrained:
            # 加载预训练模型
            config = self.model_configs.get(model_type, 'yolov10.pt')
            model = YOLO(config)
        else:
            raise ValueError("请指定权重路径或使用预训练模型")
        
        return model
    
    def save_model(self, model: YOLO, save_path: str):
        """
        保存模型权重
        
        参数:
            model: YOLO 模型
            save_path: 保存路径
        """
        # 导出模型
        model.export(format='pt', save_path=save_path)
    
    def get_model_info(self, model: YOLO) -> Dict:
        """
        获取模型信息
        
        参数:
            model: YOLO 模型
            
        返回:
            模型信息字典
        """
        return {
            'type': model.type,
            'task': model.task,
            'mode': model.mode,
            'names': model.names
        }


class AttentionModule(nn.Module):
    """注意力机制模块（可选，用于改进 YOLO）"""
    
    def __init__(self, channels: int, reduction: int = 16):
        """
        初始化注意力模块
        
        参数:
            channels: 输入通道数
            reduction: 降维比例
        """
        super().__init__()
        
        # 全局平均池化
        self.avg_pool = nn.AdaptiveAvgPool2d(1)
        
        # 通道注意力
        self.channel_attention = nn.Sequential(
            nn.Linear(channels, channels // reduction),
            nn.ReLU(inplace=True),
            nn.Linear(channels // reduction, channels),
            nn.Sigmoid()
        )
        
        # 空间注意力
        self.spatial_attention = nn.Sequential(
            nn.Conv2d(2, 1, kernel_size=7, padding=3, bias=False),
            nn.Sigmoid()
        )
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """前向传播"""
        b, c, h, w = x.size()
        
        # 通道注意力
        channel_out = self.avg_pool(x).view(b, c)
        channel_out = self.channel_attention(channel_out).view(b, c, 1, 1)
        x = x * channel_out
        
        # 空间注意力
        avg_out = torch.mean(x, dim=1, keepdim=True)
        max_out, _ = torch.max(x, dim=1, keepdim=True)
        spatial_out = torch.cat([avg_out, max_out], dim=1)
        spatial_out = self.spatial_attention(spatial_out)
        x = x * spatial_out
        
        return x


class ImprovedYOLOv10:
    """改进的 YOLOv10 模型（可扩展）"""
    
    def __init__(
        self,
        model_type: str = 'yolov10',
        attention_type: Optional[str] = None
    ):
        """
        初始化改进 YOLOv10
        
        参数:
            model_type: 模型类型
            attention_type: 注意力类型（可选）
        """
        self.model_type = model_type
        self.attention_type = attention_type
        self.model = None
    
    def build(self, pretrained: bool = True):
        """
        构建模型
        
        参数:
            pretrained: 是否使用预训练权重
        """
        loader = ModelLoader()
        self.model = loader.load_model(
            model_type=self.model_type,
            pretrained=pretrained
        )
        
        # 如果需要添加注意力机制，可以在此处修改模型结构
        if self.attention_type:
            self._add_attention()
        
        return self.model
    
    def _add_attention(self):
        """添加注意力机制到模型"""
        # 这里可以根据需要修改模型结构
        # 例如在 backbone 或 neck 部分添加注意力模块
        pass
    
    def summary(self):
        """打印模型摘要"""
        if self.model:
            print(f"模型类型：{self.model_type}")
            print(f"注意力机制：{self.attention_type or '无'}")
            # 可以添加更多模型信息
