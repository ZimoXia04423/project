# -*- coding: utf-8 -*-
"""
train 模块 - 训练入口
功能：负责 YOLOv10 模型的训练、参数配置与日志输出
包含：
1. 训练配置
2. 训练循环
3. 验证与评估
4. 日志记录
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime
from ultralytics import YOLO


class Trainer:
    """YOLO 模型训练器"""
    
    def __init__(
        self,
        data_yaml: str,
        model_type: str = 'yolov10',
        epochs: int = 100,
        batch_size: int = 16,
        img_size: int = 640,
        device: str = '0',
        project: str = 'runs',
        name: Optional[str] = None
    ):
        """
        初始化训练器
        
        参数:
            data_yaml: 数据集配置文件路径
            model_type: 模型类型 ('yolov8' 或 'yolov10')
            epochs: 训练轮数
            batch_size: 批次大小
            img_size: 输入图像尺寸
            device: GPU 设备 ('0', 'cpu', '0,1,2,3')
            project: 项目目录
            name: 实验名称
        """
        self.data_yaml = data_yaml
        self.model_type = model_type
        self.epochs = epochs
        self.batch_size = batch_size
        self.img_size = img_size
        self.device = device
        self.project = Path(project)
        self.name = name or f"{model_type}_train_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 创建项目目录
        self.project.mkdir(parents=True, exist_ok=True)
        
        # 加载模型
        self.model = self._load_model()
        
        # 训练配置
        self.train_config = {
            'data': data_yaml,
            'epochs': epochs,
            'batch': batch_size,
            'imgsz': img_size,
            'device': device,
            'project': str(project),
            'name': self.name,
            'patience': 50,
            'save': True,
            'save_period': 10,
            'verbose': True,
            'exist_ok': False,
            'optimizer': 'auto',
            'amp': True,
            'cos_lr': True,
            'warmup_epochs': 3,
        }
    
    def _load_model(self) -> YOLO:
        """加载模型"""
        if self.model_type == 'yolov8':
            model = YOLO('yolov8.pt')
        elif self.model_type == 'yolov10':
            model = YOLO('yolov10.pt')
        else:
            raise ValueError(f"不支持的模型类型：{self.model_type}")
        
        return model
    
    def train(self, **kwargs):
        """
        开始训练
        
        参数:
            **kwargs: 覆盖默认训练配置
        """
        # 更新配置
        config = {**self.train_config, **kwargs}
        
        print("\n" + "="*60)
        print("开始训练")
        print("="*60)
        print(f"模型类型：{self.model_type}")
        print(f"数据集：{self.data_yaml}")
        print(f"批次大小：{config['batch']}")
        print(f"图像尺寸：{config['imgsz']}")
        print(f"训练轮数：{config['epochs']}")
        print(f"设备：{config['device']}")
        print(f"保存目录：{config['project']}/{config['name']}")
        print("="*60 + "\n")
        
        # 开始训练
        results = self.model.train(**config)
        
        return results
    
    def validate(self, split: str = 'val'):
        """
        验证模型
        
        参数:
            split: 验证集划分 ('val' 或 'test')
        """
        print(f"\n在 {split} 集上验证模型...")
        metrics = self.model.val(split=split)
        
        print(f"\n验证结果:")
        print(f"  mAP50: {metrics.box.map50:.4f}")
        print(f"  mAP50-95: {metrics.box.map:.4f}")
        print(f"  Precision: {metrics.box.mp:.4f}")
        print(f"  Recall: {metrics.box.mr:.4f}")
        
        return metrics
    
    def export(self, format: str = 'onnx', **kwargs):
        """
        导出模型
        
        参数:
            format: 导出格式 ('onnx', 'torchscript', 'openvino', 'engine')
            **kwargs: 其他导出参数
        """
        print(f"\n导出模型为 {format} 格式...")
        export_path = self.model.export(format=format, **kwargs)
        print(f"模型已导出到：{export_path}")
        return export_path
    
    def get_training_config(self) -> Dict:
        """获取训练配置"""
        return self.train_config.copy()


def train_from_config(config_path: str):
    """
    从配置文件加载并训练
    
    参数:
        config_path: 配置文件路径（YAML 格式）
    """
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    trainer = Trainer(
        data_yaml=config.get('data', 'data.yaml'),
        model_type=config.get('model_type', 'yolov10'),
        epochs=config.get('epochs', 100),
        batch_size=config.get('batch_size', 16),
        img_size=config.get('img_size', 640),
        device=config.get('device', '0'),
        project=config.get('project', 'runs'),
        name=config.get('name')
    )
    
    # 开始训练
    results = trainer.train()
    
    # 验证
    trainer.validate()
    
    return results


if __name__ == '__main__':
    # 示例：直接运行训练
    trainer = Trainer(
        data_yaml='yolo_dataset_final/data.yaml',
        model_type='yolov10',
        epochs=100,
        batch_size=16,
        img_size=640,
        device='0'
    )
    
    trainer.train()
