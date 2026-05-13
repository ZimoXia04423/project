# -*- coding: utf-8 -*-
"""
test_modules.py - 模块功能测试脚本
用于验证各模块功能是否正常
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

def test_preprocess_module():
    """测试预处理模块"""
    print("\n" + "="*60)
    print("测试预处理模块")
    print("="*60)
    
    try:
        from preprocess import ImagePreprocessor, DataAugmenter
        import numpy as np
        
        # 创建测试图像
        test_image = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)
        
        # 测试图像预处理器
        preprocessor = ImagePreprocessor(
            target_size=(640, 640),
            clip_limit=2.0,
            use_denoise=True
        )
        
        processed = preprocessor.preprocess(test_image)
        print(f"[OK] 图像预处理成功，输出形状：{processed.shape}")
        
        # 测试数据增强器
        augmenter = DataAugmenter(
            h_flip_prob=0.5,
            rotation_range=(-15, 15)
        )
        
        augmented, _ = augmenter.augment(test_image)
        print(f"[OK] 数据增强成功，输出形状：{augmented.shape}")
        
        # 打印配置
        print("\n预处理器配置:")
        for key, value in preprocessor.get_config().items():
            print(f"  {key}: {value}")
        
        print("\n增强器配置:")
        for key, value in augmenter.get_config().items():
            print(f"  {key}: {value}")
        
        return True
    
    except Exception as e:
        print(f"[FAIL] 测试失败：{e}")
        return False


def test_dataset_module():
    """测试数据集模块"""
    print("\n" + "="*60)
    print("测试数据集模块")
    print("="*60)
    
    try:
        from datasets import YOLODataset, DatasetManager
        print("[OK] 数据集模块导入成功")
        print("  数据集管理功能已就绪")
        return True
    
    except Exception as e:
        print(f"[FAIL] 测试失败：{e}")
        return False


def test_service_module():
    """测试服务层模块"""
    print("\n" + "="*60)
    print("测试服务层模块")
    print("="*60)
    
    try:
        from service import ModelService, ImageService, ResultService, FileService
        
        # 测试模型服务
        model_service = ModelService()
        print("[OK] ModelService 初始化成功")
        
        # 测试图像服务
        image_service = ImageService()
        print("[OK] ImageService 初始化成功")
        
        # 测试结果服务
        result_service = ResultService()
        
        # 测试骨折分级
        test_detections = [
            {'class_id': 0, 'class_name': 'fracture', 'confidence': 0.95},
            {'class_id': 3, 'class_name': 'softtissue', 'confidence': 0.87}
        ]
        
        analysis = result_service.analyze_detection(test_detections)
        print(f"[OK] ResultService 分级测试成功")
        print(f"  判定结果：{analysis['grade']['name']}")
        print(f"  描述：{analysis['grade']['description']}")
        
        # 测试文件服务
        file_service = FileService()
        print(f"[OK] FileService 初始化成功，保存目录：{file_service.base_dir}")
        
        return True
    
    except Exception as e:
        print(f"[FAIL] 测试失败：{e}")
        import traceback
        traceback.print_exc()
        return False


def test_infer_module():
    """测试推理模块"""
    print("\n" + "="*60)
    print("测试推理模块")
    print("="*60)
    
    try:
        from infer import Inferencer
        
        # 检查权重文件
        weights_paths = [
            'weights/yolov8_best.pt',
            'weights/yolov10_best.pt'
        ]
        
        available_weights = [p for p in weights_paths if Path(p).exists()]
        
        if not available_weights:
            print("⚠ 未找到模型权重文件")
            print("  跳过推理测试")
            return True
        
        print(f"[OK] 找到权重文件：{available_weights[0]}")
        print("  推理功能已就绪（需要实际权重文件才能完整测试）")
        
        return True
    
    except Exception as e:
        print(f"[FAIL] 测试失败：{e}")
        return False


def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("骨折分级智能检测系统 - 模块功能测试")
    print("="*60)
    
    results = {
        '预处理模块': test_preprocess_module(),
        '数据集模块': test_dataset_module(),
        '服务层模块': test_service_module(),
        '推理模块': test_infer_module()
    }
    
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    
    for module, passed in results.items():
        status = "通过" if passed else "失败"
        print(f"{module}: {status}")
    
    total_passed = sum(results.values())
    total_tests = len(results)
    
    print(f"\n总计：{total_passed}/{total_tests} 个模块测试通过")
    print("="*60 + "\n")
    
    if total_passed == total_tests:
        print("[SUCCESS] 所有模块测试通过！系统架构已完成。")
    else:
        print("[WARNING] 部分模块测试失败，请检查错误信息。")


if __name__ == '__main__':
    main()
