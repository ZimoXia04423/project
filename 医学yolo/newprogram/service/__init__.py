# -*- coding: utf-8 -*-
"""
service 模块 - 服务层
功能：负责模型加载、图像预处理、结果后处理和文件保存
包含：
1. 模型管理服务
2. 图像处理服务
3. 结果分析服务
4. 文件保存服务
"""

import os
import cv2
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from ultralytics import YOLO

# 导入预处理模块
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from preprocess.image_preprocess import ImagePreprocessor


class ModelService:
    """模型管理服务"""
    
    def __init__(self):
        """初始化模型服务"""
        self.loaded_models = {}
        self.current_model = None
        self.current_model_name = None
    
    def load_model(
        self,
        name: str,
        weights_path: str,
        device: str = '0'
    ) -> YOLO:
        """
        加载模型
        
        参数:
            name: 模型名称
            weights_path: 权重路径
            device: 设备
            
        返回:
            YOLO 模型
        """
        if name in self.loaded_models:
            print(f"模型 {name} 已加载，直接返回")
            return self.loaded_models[name]
        
        if not Path(weights_path).exists():
            raise FileNotFoundError(f"权重文件不存在：{weights_path}")
        
        model = YOLO(weights_path)
        model.to(device)
        
        self.loaded_models[name] = model
        self.current_model = model
        self.current_model_name = name
        
        print(f"模型 {name} 加载成功")
        return model
    
    def switch_model(self, name: str) -> Optional[YOLO]:
        """切换当前使用的模型"""
        if name in self.loaded_models:
            self.current_model = self.loaded_models[name]
            self.current_model_name = name
            print(f"切换到模型：{name}")
            return self.current_model
        else:
            print(f"模型 {name} 未加载")
            return None
    
    def get_current_model(self) -> Optional[YOLO]:
        """获取当前模型"""
        return self.current_model
    
    def unload_model(self, name: str):
        """卸载模型"""
        if name in self.loaded_models:
            del self.loaded_models[name]
            if self.current_model_name == name:
                self.current_model = None
                self.current_model_name = None
            print(f"模型 {name} 已卸载")


class ImageService:
    """图像预处理服务"""
    
    def __init__(self):
        """初始化图像服务"""
        self.preprocessor = ImagePreprocessor(
            target_size=(640, 640),
            clip_limit=2.0,
            use_denoise=True
        )
    
    def load_image(self, image_path: str) -> Optional[np.ndarray]:
        """加载图像"""
        if not Path(image_path).exists():
            return None
        
        image = cv2.imread(image_path)
        return image
    
    def preprocess(self, image: np.ndarray) -> np.ndarray:
        """预处理图像"""
        return self.preprocessor.preprocess(image)
    
    def resize_image(
        self,
        image: np.ndarray,
        width: int,
        height: int,
        keep_aspect_ratio: bool = True
    ) -> np.ndarray:
        """
        调整图像尺寸
        
        参数:
            image: 输入图像
            width: 目标宽度
            height: 目标高度
            keep_aspect_ratio: 是否保持宽高比
            
        返回:
            调整后的图像
        """
        if keep_aspect_ratio:
            # 保持宽高比
            h, w = image.shape[:2]
            scale = min(width / w, height / h)
            new_w = int(w * scale)
            new_h = int(h * scale)
            
            resized = cv2.resize(image, (new_w, new_h))
            
            # 填充到目标尺寸
            padded = np.zeros((height, width, 3), dtype=np.uint8)
            y_offset = (height - new_h) // 2
            x_offset = (width - new_w) // 2
            padded[y_offset:y_offset+new_h, x_offset:x_offset+new_w] = resized
            
            return padded
        else:
            return cv2.resize(image, (width, height))


class ResultService:
    """结果分析服务"""
    
    def __init__(self):
        """初始化结果服务"""
        # 骨折分级规则
        self.grade_rules = {
            'severe': {
                'name': '重度骨折',
                'condition': lambda classes: 0 in classes and 1 in classes
            },
            'moderate': {
                'name': '中度骨折',
                'condition': lambda classes: 0 in classes and (2 in classes or 3 in classes)
            },
            'mild': {
                'name': '轻度骨折',
                'condition': lambda classes: 0 in classes
            },
            'none': {
                'name': '未见骨折',
                'condition': lambda classes: 0 not in classes
            }
        }
    
    def analyze_detection(self, detections: List[Dict]) -> Dict:
        """
        分析检测结果
        
        参数:
            detections: 检测结果列表
            
        返回:
            分析结果
        """
        # 提取检测到的类别
        detected_classes = set()
        for det in detections:
            detected_classes.add(det['class_id'])
        
        # 判定骨折等级
        grade = self._determine_grade(detected_classes)
        
        # 生成报告
        report = {
            'grade': grade,
            'detected_classes': list(detected_classes),
            'detection_count': len(detections),
            'details': detections
        }
        
        return report
    
    def _determine_grade(self, classes: set) -> Dict:
        """
        判定骨折等级
        
        参数:
            classes: 检测到的类别集合
            
        返回:
            等级信息
        """
        # 按优先级检查
        priority_order = ['severe', 'moderate', 'mild', 'none']
        
        for grade_key in priority_order:
            rule = self.grade_rules[grade_key]
            if rule['condition'](classes):
                return {
                    'level': grade_key,
                    'name': rule['name'],
                    'description': self._get_grade_description(grade_key)
                }
        
        return {'level': 'unknown', 'name': '未知', 'description': ''}
    
    def _get_grade_description(self, grade: str) -> str:
        """获取等级描述"""
        descriptions = {
            'severe': '检测到骨折伴骨膜反应',
            'moderate': '检测到骨折伴软组织肿胀/旋前征',
            'mild': '检测到单纯骨折',
            'none': '未检测到明确骨折征象'
        }
        return descriptions.get(grade, '')
    
    def generate_report(
        self,
        image_path: str,
        detections: List[Dict],
        save_path: Optional[str] = None
    ) -> str:
        """
        生成检测报告
        
        参数:
            image_path: 图像路径
            detections: 检测结果
            save_path: 保存路径
            
        返回:
            报告文本
        """
        analysis = self.analyze_detection(detections)
        
        report_lines = [
            "=" * 60,
            "骨折检测报告",
            "=" * 60,
            f"图像：{image_path}",
            f"检测时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "【检测结果】",
            f"  骨折等级：{analysis['grade']['name']}",
            f"  描述：{analysis['grade']['description']}",
            f"  检测数量：{analysis['detection_count']}",
            "",
            "【详细病灶】"
        ]
        
        for det in detections:
            report_lines.append(
                f"  - {det['class_name']}: 置信度 {det['confidence']:.2f}"
            )
        
        report_lines.append("=" * 60)
        
        report_text = "\n".join(report_lines)
        
        # 保存报告
        if save_path:
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(report_text)
            print(f"报告已保存到：{save_path}")
        
        return report_text


class FileService:
    """文件保存服务"""
    
    def __init__(self, base_dir: str = 'results'):
        """
        初始化文件服务
        
        参数:
            base_dir: 基础保存目录
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def save_image(
        self,
        image: np.ndarray,
        filename: str,
        sub_dir: Optional[str] = None
    ) -> str:
        """
        保存图像
        
        参数:
            image: 图像
            filename: 文件名
            sub_dir: 子目录
            
        返回:
            保存路径
        """
        if sub_dir:
            save_dir = self.base_dir / sub_dir
            save_dir.mkdir(parents=True, exist_ok=True)
        else:
            save_dir = self.base_dir
        
        save_path = save_dir / filename
        cv2.imwrite(str(save_path), image)
        
        return str(save_path)
    
    def save_text(
        self,
        content: str,
        filename: str,
        sub_dir: Optional[str] = None
    ) -> str:
        """
        保存文本
        
        参数:
            content: 文本内容
            filename: 文件名
            sub_dir: 子目录
            
        返回:
            保存路径
        """
        if sub_dir:
            save_dir = self.base_dir / sub_dir
            save_dir.mkdir(parents=True, exist_ok=True)
        else:
            save_dir = self.base_dir
        
        save_path = save_dir / filename
        with open(save_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return str(save_path)
    
    def create_result_directory(self, experiment_name: str) -> Path:
        """
        创建结果目录
        
        参数:
            experiment_name: 实验名称
            
        返回:
            目录路径
        """
        result_dir = self.base_dir / experiment_name
        result_dir.mkdir(parents=True, exist_ok=True)
        return result_dir
