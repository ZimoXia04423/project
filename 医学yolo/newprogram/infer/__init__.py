# -*- coding: utf-8 -*-
"""
infer 模块 - 推理服务层
功能：负责模型加载、图像预处理、结果后处理和文件保存
包含：
1. 模型推理
2. 结果可视化
3. 批量检测
4. 结果导出
"""

import os
import cv2
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from datetime import datetime
from ultralytics import YOLO


class Inferencer:
    """骨折检测推理器"""
    
    def __init__(
        self,
        weights_path: str,
        device: str = '0',
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.45
    ):
        """
        初始化推理器
        
        参数:
            weights_path: 模型权重路径
            device: 推理设备 ('0', 'cpu')
            conf_threshold: 置信度阈值
            iou_threshold: NMS IoU 阈值
        """
        self.weights_path = weights_path
        self.device = device
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        
        # 加载模型
        self.model = self._load_model()
        
        # 类别名称
        self.class_names = self.model.names
        
        # 结果保存目录
        self.save_dir = Path('inference_results')
        self.save_dir.mkdir(parents=True, exist_ok=True)
    
    def _load_model(self) -> YOLO:
        """加载模型"""
        if not Path(self.weights_path).exists():
            raise FileNotFoundError(f"权重文件不存在：{self.weights_path}")
        
        model = YOLO(self.weights_path)
        model.to(self.device)
        return model
    
    def predict(
        self,
        image_path: str,
        save_result: bool = True,
        show_result: bool = False
    ) -> Dict:
        """
        单张图像推理
        
        参数:
            image_path: 图像路径
            save_result: 是否保存结果
            show_result: 是否显示结果
            
        返回:
            检测结果字典
        """
        # 读取图像
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"无法读取图像：{image_path}")
        
        # 推理
        results = self.model.predict(
            source=image,
            conf=self.conf_threshold,
            iou=self.iou_threshold,
            verbose=False
        )
        
        # 解析结果
        result = results[0]
        detection_info = self._parse_result(result)
        
        # 可视化
        if save_result or show_result:
            vis_image = self._visualize_detection(image, result)
            
            if save_result:
                # 生成保存文件名
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                save_name = f"detection_{Path(image_path).stem}_{timestamp}.jpg"
                save_path = self.save_dir / save_name
                cv2.imwrite(str(save_path), vis_image)
                detection_info['save_path'] = str(save_path)
            
            if show_result:
                cv2.imshow('Detection Result', vis_image)
                cv2.waitKey(0)
                cv2.destroyAllWindows()
        
        return detection_info
    
    def predict_batch(
        self,
        image_paths: List[str],
        save_results: bool = True
    ) -> List[Dict]:
        """
        批量推理
        
        参数:
            image_paths: 图像路径列表
            save_results: 是否保存结果
            
        返回:
            检测结果列表
        """
        all_results = []
        
        for idx, path in enumerate(image_paths):
            print(f"[{idx+1}/{len(image_paths)}] 处理：{path}")
            try:
                result = self.predict(path, save_result=save_results)
                all_results.append(result)
            except Exception as e:
                print(f"处理失败 {path}: {e}")
                all_results.append({'error': str(e), 'path': path})
        
        return all_results
    
    def _parse_result(self, result) -> Dict:
        """
        解析检测结果
        
        参数:
            result: YOLO 检测结果
            
        返回:
            检测结果字典
        """
        boxes = result.boxes
        if boxes is None:
            return {
                'detections': [],
                'count': 0,
                'classes_detected': set()
            }
        
        detections = []
        classes_detected = set()
        
        for i in range(len(boxes)):
            box = boxes[i]
            
            # 提取信息
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            confidence = float(box.conf[0].cpu().numpy())
            class_id = int(box.cls[0].cpu().numpy())
            class_name = self.class_names[class_id]
            
            detections.append({
                'class_id': class_id,
                'class_name': class_name,
                'confidence': confidence,
                'bbox': {
                    'x1': float(x1),
                    'y1': float(y1),
                    'x2': float(x2),
                    'y2': float(y2)
                }
            })
            
            classes_detected.add(class_id)
        
        return {
            'detections': detections,
            'count': len(detections),
            'classes_detected': classes_detected,
            'image_shape': result.orig_shape
        }
    
    def _visualize_detection(
        self,
        image: np.ndarray,
        result
    ) -> np.ndarray:
        """
        可视化检测结果
        
        参数:
            image: 原始图像
            result: YOLO 检测结果
            
        返回:
            可视化图像
        """
        vis_image = image.copy()
        boxes = result.boxes
        
        if boxes is None:
            return vis_image
        
        # 颜色映射
        colors = {
            0: (0, 0, 255),       # 红色 - fracture
            1: (0, 165, 255),     # 橙色 - periostealreaction
            2: (0, 255, 0),       # 绿色 - pronatorsign
            3: (255, 0, 0)        # 蓝色 - softtissue
        }
        
        for i in range(len(boxes)):
            box = boxes[i]
            x1, y1, x2, y2 = map(int, box.xyxy[0].cpu().numpy())
            confidence = float(box.conf[0].cpu().numpy())
            class_id = int(box.cls[0].cpu().numpy())
            class_name = self.class_names[class_id]
            
            # 绘制矩形框
            color = colors.get(class_id, (255, 255, 255))
            cv2.rectangle(vis_image, (x1, y1), (x2, y2), color, 2)
            
            # 绘制标签
            label = f"{class_name}: {confidence:.2f}"
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
            
            # 标签背景
            cv2.rectangle(
                vis_image,
                (x1, y1),
                (x1 + label_size[0] + 10, y1 + label_size[1] + 10),
                color,
                -1
            )
            
            # 标签文字
            cv2.putText(
                vis_image,
                label,
                (x1 + 5, y1 + label_size[1] + 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 255),
                2
            )
        
        return vis_image
    
    def export_results(
        self,
        results: List[Dict],
        output_path: str,
        format: str = 'txt'
    ):
        """
        导出检测结果
        
        参数:
            results: 检测结果列表
            output_path: 输出路径
            format: 导出格式 ('txt', 'json')
        """
        if format == 'txt':
            with open(output_path, 'w', encoding='utf-8') as f:
                for result in results:
                    if 'error' in result:
                        f.write(f"错误：{result['error']} - {result['path']}\n")
                        continue
                    
                    f.write(f"图像：{result.get('path', 'N/A')}\n")
                    f.write(f"检测数量：{result['count']}\n")
                    for det in result['detections']:
                        f.write(f"  - {det['class_name']}: {det['confidence']:.2f}\n")
                    f.write("\n")
        
        elif format == 'json':
            import json
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"结果已导出到：{output_path}")


def batch_inference(
    image_dir: str,
    weights_path: str,
    output_dir: Optional[str] = None
):
    """
    批量检测目录中的所有图像
    
    参数:
        image_dir: 图像目录
        weights_path: 权重路径
        output_dir: 输出目录
    """
    # 获取所有图像
    image_extensions = ['.jpg', '.jpeg', '.png', '.bmp']
    image_paths = []
    
    for ext in image_extensions:
        image_paths.extend(Path(image_dir).glob(f'*{ext}'))
    
    print(f"找到 {len(image_paths)} 张图像")
    
    # 创建推理器
    inferencer = Inferencer(weights_path=weights_path)
    
    # 批量推理
    results = inferencer.predict_batch(image_paths, save_results=True)
    
    # 导出结果
    if output_dir:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        inferencer.export_results(
            results,
            f"{output_dir}/results.txt",
            format='txt'
        )
        inferencer.export_results(
            results,
            f"{output_dir}/results.json",
            format='json'
        )
    
    # 统计
    total_detections = sum(r.get('count', 0) for r in results)
    print(f"\n检测完成!")
    print(f"总检测数：{total_detections}")
    
    return results
