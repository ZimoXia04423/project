# -*- coding: utf-8 -*-
"""
gui 模块 - 表现层
功能：基于 PyQt5 实现图形界面，向用户提供操作入口
包含：
1. 主窗口界面
2. 图像显示组件
3. 检测控制面板
4. 结果展示组件
"""

import sys
import os

# 添加父目录到路径
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFileDialog, QMessageBox,
    QSplitter, QFrame, QScrollArea, QTextEdit,
    QComboBox, QGroupBox, QTableWidget, QTableWidgetItem
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap, QImage, QFont

# 导入服务层
from service import ModelService, ImageService, ResultService, FileService


class DetectionThread(QThread):
    """检测线程"""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, model_service, image_path):
        super().__init__()
        self.model_service = model_service
        self.image_path = image_path
    
    def run(self):
        try:
            model = self.model_service.get_current_model()
            if model is None:
                self.error.emit("未加载模型")
                return
            
            # 执行检测
            results = model.predict(
                source=self.image_path,
                conf=0.25,
                iou=0.45,
                verbose=False
            )
            
            # 解析结果
            result = results[0]
            detection_info = self._parse_result(result)
            self.finished.emit(detection_info)
        
        except Exception as e:
            self.error.emit(str(e))
    
    def _parse_result(self, result):
        """解析检测结果"""
        boxes = result.boxes
        if boxes is None:
            return {'detections': [], 'count': 0}
        
        detections = []
        for i in range(len(boxes)):
            box = boxes[i]
            x1, y1, x2, y2 = map(float, box.xyxy[0].cpu().numpy())
            confidence = float(box.conf[0].cpu().numpy())
            class_id = int(box.cls[0].cpu().numpy())
            class_name = model.names[class_id]
            
            detections.append({
                'class_id': class_id,
                'class_name': class_name,
                'confidence': confidence,
                'bbox': [x1, y1, x2, y2]
            })
        
        return {
            'detections': detections,
            'count': len(detections)
        }


class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        
        # 初始化服务
        self.model_service = ModelService()
        self.image_service = ImageService()
        self.result_service = ResultService()
        self.file_service = FileService()
        
        # 当前图像
        self.current_image = None
        self.current_image_path = None
        
        # 初始化 UI
        self.setup_ui()
    
    def setup_ui(self):
        """设置界面"""
        self.setWindowTitle("骨折分级智能检测系统")
        self.setGeometry(100, 100, 1400, 900)
        
        # 中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # 标题
        title_label = QLabel("骨折分级智能检测系统")
        title_label.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #1a73e8;
            padding: 10px;
        """)
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # 分割器
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # 左侧：图像显示区
        left_widget = self._create_image_display()
        splitter.addWidget(left_widget)
        
        # 右侧：控制面板
        right_widget = self._create_control_panel()
        splitter.addWidget(right_widget)
        
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)
    
    def _create_image_display(self):
        """创建图像显示区"""
        widget = QFrame()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        
        # 原始图像
        original_group = QGroupBox("原始图像")
        original_layout = QVBoxLayout()
        original_group.setLayout(original_layout)
        
        self.original_label = QLabel("请加载图像")
        self.original_label.setAlignment(Qt.AlignCenter)
        self.original_label.setMinimumSize(512, 512)
        self.original_label.setStyleSheet("""
            QLabel {
                background: #f5f5f5;
                border: 2px dashed #cccccc;
                border-radius: 8px;
            }
        """)
        original_layout.addWidget(self.original_label)
        
        layout.addWidget(original_group)
        
        # 检测结果图像
        result_group = QGroupBox("检测结果")
        result_layout = QVBoxLayout()
        result_group.setLayout(result_layout)
        
        self.result_label = QLabel("等待检测")
        self.result_label.setAlignment(Qt.AlignCenter)
        self.result_label.setMinimumSize(512, 512)
        self.result_label.setStyleSheet("""
            QLabel {
                background: #f5f5f5;
                border: 2px dashed #cccccc;
                border-radius: 8px;
            }
        """)
        result_layout.addWidget(self.result_label)
        
        layout.addWidget(result_group)
        
        return widget
    
    def _create_control_panel(self):
        """创建控制面板"""
        widget = QScrollArea()
        widget.setWidgetResizable(True)
        
        content_widget = QWidget()
        layout = QVBoxLayout()
        content_widget.setLayout(layout)
        
        # 模型选择
        model_group = QGroupBox("模型选择")
        model_layout = QVBoxLayout()
        model_group.setLayout(model_layout)
        
        self.model_combo = QComboBox()
        self.model_combo.addItems([
            "YOLOv8 骨折分级模型",
            "YOLOv10 骨折分级模型"
        ])
        model_layout.addWidget(self.model_combo)
        
        load_model_btn = QPushButton("加载模型")
        load_model_btn.setStyleSheet("""
            QPushButton {
                background: #1a73e8;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: #1557b0;
            }
        """)
        load_model_btn.clicked.connect(self.load_model)
        model_layout.addWidget(load_model_btn)
        
        layout.addWidget(model_group)
        
        # 图像操作
        image_group = QGroupBox("图像操作")
        image_layout = QVBoxLayout()
        image_group.setLayout(image_layout)
        
        load_image_btn = QPushButton("加载图像")
        load_image_btn.setStyleSheet("""
            QPushButton {
                background: #34a853;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: #2d8e47;
            }
        """)
        load_image_btn.clicked.connect(self.load_image)
        image_layout.addWidget(load_image_btn)
        
        detect_btn = QPushButton("开始检测")
        detect_btn.setStyleSheet("""
            QPushButton {
                background: #ea4335;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: #c5221f;
            }
        """)
        detect_btn.clicked.connect(self.start_detection)
        image_layout.addWidget(detect_btn)
        
        layout.addWidget(image_group)
        
        # 检测结果
        result_group = QGroupBox("检测结果")
        result_layout = QVBoxLayout()
        result_group.setLayout(result_layout)
        
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMinimumHeight(200)
        result_layout.addWidget(self.result_text)
        
        layout.addWidget(result_group)
        
        # 病灶详情表格
        detail_group = QGroupBox("病灶详情")
        detail_layout = QVBoxLayout()
        detail_group.setLayout(detail_layout)
        
        self.detail_table = QTableWidget()
        self.detail_table.setColumnCount(3)
        self.detail_table.setHorizontalHeaderLabels(["类别", "置信度", "位置"])
        detail_layout.addWidget(self.detail_table)
        
        layout.addWidget(detail_group)
        
        widget.setWidget(content_widget)
        return widget
    
    def load_model(self):
        """加载模型"""
        model_name = self.model_combo.currentText()
        
        # 权重文件路径
        weights_map = {
            "YOLOv8 骨折分级模型": "weights/yolov8_best.pt",
            "YOLOv10 骨折分级模型": "weights/yolov10_best.pt"
        }
        
        weights_path = weights_map.get(model_name)
        
        if not weights_path or not Path(weights_path).exists():
            QMessageBox.warning(self, "警告", f"模型文件不存在：{weights_path}")
            return
        
        try:
            self.model_service.load_model(model_name, weights_path)
            QMessageBox.information(self, "成功", f"模型 {model_name} 加载成功")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"模型加载失败：{str(e)}")
    
    def load_image(self):
        """加载图像"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择图像",
            "",
            "图像文件 (*.jpg *.jpeg *.png *.bmp *.tif *.tiff);;所有文件 (*.*)",
        )

        if not file_path:
            return

        allowed = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
        ext = Path(file_path).suffix.lower()
        if ext not in allowed:
            QMessageBox.warning(
                self,
                "格式错误",
                "所选文件不是支持的医学影像格式，请选择 JPG、JPEG、PNG、BMP、TIF、TIFF 等图像文件。",
            )
            return

        self.current_image_path = file_path
        self.current_image = self.image_service.load_image(file_path)
        if self.current_image is None:
            QMessageBox.warning(
                self,
                "格式错误",
                "无法将所选文件解析为图像，可能文件已损坏或内容与扩展名不符。",
            )
            return

        self._display_image(self.original_label, self.current_image)
    
    def start_detection(self):
        """开始检测"""
        if self.current_image is None:
            QMessageBox.warning(self, "警告", "请先加载图像")
            return
        
        if self.model_service.get_current_model() is None:
            QMessageBox.warning(self, "警告", "请先加载模型")
            return
        
        # 创建检测线程
        self.detection_thread = DetectionThread(
            self.model_service,
            self.current_image_path
        )
        self.detection_thread.finished.connect(self.on_detection_finished)
        self.detection_thread.error.connect(self.on_detection_error)
        self.detection_thread.start()
    
    def on_detection_finished(self, result):
        """检测完成"""
        # 分析结果
        analysis = self.result_service.analyze_detection(result['detections'])
        
        # 显示结果
        report = self.result_service.generate_report(
            self.current_image_path,
            result['detections']
        )
        self.result_text.setText(report)
        
        # 更新表格
        self._update_detail_table(result['detections'])
    
    def on_detection_error(self, error_msg):
        """检测出错"""
        QMessageBox.critical(self, "错误", f"检测失败：{error_msg}")
    
    def _display_image(self, label, image):
        """显示图像"""
        if image is None:
            return
        
        # 转换为 RGB
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        
        # 创建 QImage
        q_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        
        # 缩放并显示
        pixmap = QPixmap.fromImage(q_image)
        scaled_pixmap = pixmap.scaled(
            label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        label.setPixmap(scaled_pixmap)
    
    def _update_detail_table(self, detections):
        """更新详情表格"""
        self.detail_table.setRowCount(len(detections))
        
        for i, det in enumerate(detections):
            class_item = QTableWidgetItem(det['class_name'])
            conf_item = QTableWidgetItem(f"{det['confidence']:.2f}")
            
            bbox = det.get('bbox', [])
            if len(bbox) == 4:
                pos_text = f"({bbox[0]:.0f}, {bbox[1]:.0f}) - ({bbox[2]:.0f}, {bbox[3]:.0f})"
            else:
                pos_text = "N/A"
            pos_item = QTableWidgetItem(pos_text)
            
            self.detail_table.setItem(i, 0, class_item)
            self.detail_table.setItem(i, 1, conf_item)
            self.detail_table.setItem(i, 2, pos_item)


def run_gui():
    """运行 GUI"""
    app = QApplication(sys.argv)
    
    # 设置全局字体
    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    run_gui()
