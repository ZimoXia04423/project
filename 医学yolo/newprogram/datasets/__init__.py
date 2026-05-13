# -*- coding: utf-8 -*-
"""
datasets 模块 - 数据层
功能：负责原始图像、标签文件、训练集与测试集管理
包含：
1. 数据集加载与解析
2. YOLO 格式标签读取
3. 数据划分（训练集/验证集/测试集）
4. 数据统计与可视化
"""

import os
import cv2
import yaml
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional


class YOLODataset:
    """YOLO 格式骨折检测数据集"""
    
    def __init__(
        self,
        root_dir: str,
        split: str = 'train',
        img_size: Tuple[int, int] = (640, 640)
    ):
        """
        初始化数据集
        
        参数:
            root_dir: 数据集根目录（包含 images/和 labels/）
            split: 数据集划分 ('train', 'val', 'test')
            img_size: 图像尺寸
        """
        self.root_dir = Path(root_dir)
        self.split = split
        self.img_size = img_size
        
        # 目录路径
        self.images_dir = self.root_dir / 'images' / split
        self.labels_dir = self.root_dir / 'labels' / split
        
        # 加载 data.yaml 配置
        self.data_config = self._load_data_config()
        
        # 获取所有图像路径
        self.image_paths = self._get_image_paths()
        
        # 类别信息
        self.class_names = self.data_config.get('names', {})
        self.nc = len(self.class_names)  # 类别数量
    
    def _load_data_config(self) -> Dict:
        """加载 data.yaml 配置文件"""
        yaml_path = self.root_dir / 'data.yaml'
        if yaml_path.exists():
            with open(yaml_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        return {}
    
    def _get_image_paths(self) -> List[Path]:
        """获取所有图像文件路径"""
        if not self.images_dir.exists():
            return []
        
        extensions = ['.jpg', '.jpeg', '.png', '.bmp']
        image_paths = []
        
        for ext in extensions:
            image_paths.extend(self.images_dir.glob(f'*{ext}'))
        
        return sorted(image_paths)
    
    def __len__(self) -> int:
        return len(self.image_paths)
    
    def __getitem__(self, idx: int) -> Tuple[np.ndarray, np.ndarray, str]:
        """
        获取单个样本
        
        参数:
            idx: 索引
            
        返回:
            (图像，标注框数组，图像路径)
            标注框格式：[class_id, x_center, y_center, width, height] (归一化)
        """
        img_path = self.image_paths[idx]
        
        # 读取图像
        image = cv2.imread(str(img_path))
        if image is None:
            raise ValueError(f"无法读取图像：{img_path}")
        
        # 读取标签
        label_path = self.labels_dir / f"{img_path.stem}.txt"
        boxes = self._load_labels(label_path)
        
        return image, boxes, str(img_path)
    
    def _load_labels(self, label_path: Path) -> np.ndarray:
        """
        加载 YOLO 格式标签
        
        参数:
            label_path: 标签文件路径
            
        返回:
            标注框数组 (N, 5) [class_id, x_center, y_center, width, height]
        """
        if not label_path.exists():
            return np.empty((0, 5))
        
        boxes = []
        with open(label_path, 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 5:
                    box = [float(p) for p in parts[:5]]
                    boxes.append(box)
        
        return np.array(boxes) if boxes else np.empty((0, 5))
    
    def load_all(self) -> Tuple[List[np.ndarray], List[np.ndarray], List[str]]:
        """
        加载所有数据
        
        返回:
            (图像列表，标注框列表，路径列表)
        """
        images = []
        all_boxes = []
        paths = []
        
        total = len(self)
        for idx in range(total):
            try:
                img, boxes, path = self[idx]
                images.append(img)
                all_boxes.append(boxes)
                paths.append(path)
                if (idx + 1) % 10 == 0 or idx == total - 1:
                    print(f"加载进度：{idx + 1}/{total}")
            except Exception as e:
                print(f"加载失败 {self.image_paths[idx]}: {e}")
        
        return images, all_boxes, paths
    
    def get_statistics(self) -> Dict:
        """获取数据集统计信息"""
        total_images = len(self)
        total_boxes = 0
        class_distribution = {i: 0 for i in range(self.nc)}
        
        for idx in range(len(self)):
            _, boxes, _ = self[idx]
            total_boxes += len(boxes)
            
            # 统计类别分布
            for box in boxes:
                if len(box) >= 1:
                    class_id = int(box[0])
                    if class_id in class_distribution:
                        class_distribution[class_id] += 1
        
        return {
            'split': self.split,
            'total_images': total_images,
            'total_annotations': total_boxes,
            'avg_annotations_per_image': total_boxes / max(total_images, 1),
            'class_distribution': class_distribution,
            'class_names': self.class_names
        }
    
    def visualize_sample(
        self,
        idx: int,
        save_path: Optional[str] = None
    ) -> np.ndarray:
        """
        可视化单个样本（图像 + 标注框）
        
        参数:
            idx: 样本索引
            save_path: 保存路径（可选）
            
        返回:
            可视化图像
        """
        image, boxes, path = self[idx]
        
        # 绘制标注框
        vis_image = image.copy()
        h, w = image.shape[:2]
        
        # 颜色映射
        colors = [
            (0, 0, 255),    # 红色 - fracture
            (0, 165, 255),  # 橙色 - periostealreaction
            (0, 255, 0),    # 绿色 - pronatorsign
            (255, 0, 0)     # 蓝色 - softtissue
        ]
        
        for box in boxes:
            if len(box) < 5:
                continue
            
            class_id = int(box[0])
            x_center = box[1] * w
            y_center = box[2] * h
            box_width = box[3] * w
            box_height = box[4] * h
            
            # 转换为左上角和右下角坐标
            x_min = int(x_center - box_width / 2)
            y_min = int(y_center - box_height / 2)
            x_max = int(x_center + box_width / 2)
            y_max = int(y_center + box_height / 2)
            
            # 绘制矩形框
            color = colors[class_id % len(colors)]
            cv2.rectangle(vis_image, (x_min, y_min), (x_max, y_max), color, 2)
            
            # 绘制类别标签
            label = f"{self.class_names.get(class_id, class_id)}"
            cv2.putText(
                vis_image,
                label,
                (x_min, y_min - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                2
            )
        
        # 保存或显示
        if save_path:
            cv2.imwrite(save_path, vis_image)
        
        return vis_image


class DatasetManager:
    """数据集管理器"""
    
    def __init__(self, root_dir: str):
        """
        初始化数据集管理器
        
        参数:
            root_dir: 数据集根目录
        """
        self.root_dir = Path(root_dir)
        self.train_dataset = None
        self.val_dataset = None
        self.test_dataset = None
    
    def load_split(self, split: str = 'train') -> YOLODataset:
        """
        加载指定划分的数据集
        
        参数:
            split: 数据集划分 ('train', 'val', 'test')
            
        返回:
            YOLODataset 实例
        """
        dataset = YOLODataset(self.root_dir, split=split)
        
        if split == 'train':
            self.train_dataset = dataset
        elif split == 'val':
            self.val_dataset = dataset
        elif split == 'test':
            self.test_dataset = dataset
        
        return dataset
    
    def load_all_splits(self) -> Dict[str, YOLODataset]:
        """加载所有数据集划分"""
        datasets = {}
        for split in ['train', 'val', 'test']:
            datasets[split] = self.load_split(split)
        return datasets
    
    def get_full_statistics(self) -> Dict:
        """获取完整的数据集统计信息"""
        stats = {}
        for split in ['train', 'val', 'test']:
            dataset = YOLODataset(self.root_dir, split=split)
            stats[split] = dataset.get_statistics()
        return stats
    
    def print_statistics(self):
        """打印数据集统计信息"""
        stats = self.get_full_statistics()
        
        print("\n" + "="*60)
        print("数据集统计信息")
        print("="*60)
        
        for split, stat in stats.items():
            print(f"\n【{split.upper()}】")
            print(f"  图像数量：{stat['total_images']}")
            print(f"  标注框总数：{stat['total_annotations']}")
            print(f"  平均每张图像标注数：{stat['avg_annotations_per_image']:.2f}")
            print(f"  类别分布:")
            for class_id, count in stat['class_distribution'].items():
                class_name = stat['class_names'].get(class_id, class_id)
                print(f"    {class_name}: {count}")
        
        print("="*60 + "\n")
