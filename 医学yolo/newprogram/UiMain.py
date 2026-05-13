# -*- coding: utf-8 -*-
"""
UiMain.py - 骨折分级智能检测系统 主界面模块 v4
功能：无边框深蓝医疗科技风主窗口，支持单图检测、双模型对比、后置融合分级判定
布局：左原始图 + 中检测结果图(医疗蓝框) + 右控制面板(分级结论+病灶详情表格+对比分析)
模型输出：4类病灶(fracture/periostealreaction/pronatorsign/softtissue)
后置分级：FractureGrader 根据病灶组合自动判定 重度/中度/轻度/未见骨折
"""

import os
import time
import cv2
import numpy as np

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSlider, QTableWidget,
    QTableWidgetItem, QGroupBox, QComboBox,
    QDoubleSpinBox, QSizeGrip, QToolButton, QSplitter,
    QFrame, QScrollArea, QTextEdit, QApplication,
    QSizePolicy, QHeaderView
)
from PyQt5.QtCore import Qt, QPoint, pyqtSignal, QThread
from PyQt5.QtGui import (QPixmap, QImage, QIcon, QColor, QFont)


# ==================== 模型类别常量 ====================

# 【核心】模型输出的4类病灶 ID → 名称（严格按 data.yaml 定义）
CLASS_NAMES = {
    0: "fracture",           # 骨折（核心必要条件）
    1: "periostealreaction", # 骨膜反应（最高优先级 → 重度）
    2: "pronatorsign",       # 旋前征
    3: "softtissue",         # 软组织肿胀
}

# 【新增】每类病灶使用独立颜色（BGR），视觉区分度高，医疗专业感强
CLASS_COLORS_BGR = {
    0: (63, 63, 245),       # fracture → 红 #F53F3F
    1: (0, 125, 255),       # periostealreaction → 橙 #FF7D00
    2: (42, 180, 0),        # pronatorsign → 绿 #00B42A
    3: (255, 93, 22),       # softtissue → 医疗蓝 #165DFF
}


# 分级结论配置（供 UI 显示用）
GRADE_CONFIG = {
    3: ("重度骨折", "#F53F3F", "检测到骨折伴骨膜反应"),
    2: ("中度骨折", "#FF7D00", "检测到骨折伴软组织肿胀 / 旋前征"),
    1: ("轻度骨折", "#00B42A", "检测到单纯骨折"),
    0: ("未见骨折", "#86909C", "图像中未检测到明确骨折征象"),
}


# 模型配置映射：下拉框显示名 → 权重文件名
MODEL_CONFIG = {
    "YOLOv8 骨折分级模型": "yolov8_best.pt",
    "YOLOv10 骨折分级模型": "yolov10_best.pt",
}


# 程序根目录（newprogram所在目录）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEIGHTS_DIR = os.path.join(BASE_DIR, "weights")

# 可选扩展名：配合文件对话框「所有文件 (*.*)」做格式校验（测试用例：加载非图像文件 → 格式错误提示）
ALLOWED_IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp",
}

# Qt 在 Windows 下须使用 (*.*)「所有文件」才能选中文本等非图像；单独写 (*) 会被系统忽略导致只能看到图片
IMAGE_FILE_DIALOG_FILTER = (
    "\u56fe\u7247\u6587\u4ef6 (*.jpg *.jpeg *.png *.bmp *.tif *.tiff);;"
    "\u6240\u6709\u6587\u4ef6 (*.*)"
)


def _suffix_allowed_for_image(path: str) -> bool:
    return os.path.splitext(path)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


# ==================== 无边框窗口基类 ====================

class FramelessWindow(QMainWindow):
    """无边框可拖拽窗口基类"""

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.old_pos = self.pos()
        self._is_maximized = False
        self._old_geometry = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.old_pos = event.globalPos()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            delta = QPoint(event.globalPos() - self.old_pos)
            new_pos = self.pos() + delta
            self.move(new_pos)
            self.old_pos = event.globalPos()

    def toggle_maximize(self):
        """切换最大化/还原状态"""
        if self._is_maximized:
            if self._old_geometry:
                self.setGeometry(self._old_geometry)
            self._is_maximized = False
            if hasattr(self, 'maximize_btn'):
                self.maximize_btn.setText("\u25a1")
        else:
            self._old_geometry = self.geometry()
            self.showMaximized()
            self._is_maximized = True
            if hasattr(self, 'maximize_btn'):
                self.maximize_btn.setText("\u2501")


# ==================== 骨折分级器（后置融合逻辑）====================

class FractureGrader:
    """
    后置融合分级判定器
    输入：模型检测结果列表（每个结果包含 class_id, confidence）
    输出：(grade_id, grade_name, grade_color, justification)

    判定规则（优先级从高到低，一旦满足即停止）：
      1. 重度：有 fracture + periostealreaction（无论其他）
      2. 中度：有 fracture + (softtissue 或 pronatorsign) 且无 periostealreaction
      3. 轻度：仅有 fracture，无其他伴随病灶
      4. 未见：无 fracture
    """

    # 关键类ID（用于判定逻辑）
    ID_FRACTURE = 0          # 骨折 — 核心必要条件
    ID_PERIOSTEA = 1         # 骨膜反应 — 最高优先级伴随征象
    ID_PRONATOR = 2          # 旋前征 — 中度伴随征象
    ID_SOFTTISSUE = 3        # 软组织肿胀 — 中度伴随征象

    @classmethod
    def grade(cls, detection_list):
        """
        对检测结果进行后置融合分级
        参数：
            detection_list: list[dict]，每项含 {"class_id": int, "confidence": float}
        返回：
            dict: {
                "grade_id": int (3=重度, 2=中度, 1=轻度, 0=未见),
                "grade_name": str,
                "grade_color": str (HEX),
                "justification": str,
                "detected_classes": set,  # 检测到的类ID集合（便于调试）
            }
        """
        # 提取所有检测到的类ID集合
        detected_classes = set()
        for det in detection_list:
            detected_classes.add(det.get("class_id", -1))

        has_fracture = cls.ID_FRACTURE in detected_classes
        has_periosteal = cls.ID_PERIOSTEA in detected_classes
        has_moderate_sign = (
            cls.ID_SOFTTISSUE in detected_classes or
            cls.ID_PRONATOR in detected_classes
        )

        # ---- 严格按优先级判定 ----
        # 优先级1：重度 — 有骨折 + 有骨膜反应（最高优先级，无论是否有其他）
        if has_fracture and has_periosteal:
            return cls._make_result(3)

        # 优先级2：中度 — 有骨折 + 有软组织/旋前征 + 无骨膜反应
        if has_fracture and has_moderate_sign and not has_periosteal:
            return cls._make_result(2)

        # 优先级3：轻度 — 仅有骨折，无任何伴随病灶
        if has_fracture and not has_periosteal and not has_moderate_sign:
            return cls._make_result(1)

        # 优先级4：未见 — 无骨折
        return cls._make_result(0)

    @classmethod
    def _make_result(cls, grade_id):
        """根据 grade_id 构建返回字典"""
        name, color, justification = GRADE_CONFIG[grade_id]
        return {
            "grade_id": grade_id,
            "grade_name": name,
            "grade_color": color,
            "justification": justification,
        }


# ==================== 检测线程 ====================

class DetectionThread(QThread):
    """
    单图检测线程 - 在后台执行模型推理，避免UI阻塞
    输出原始4类病灶检测结果，不做分级（分级由主线程调用 FractureGrader 完成）
    """
    finished_signal = pyqtSignal(object, list)  # (annotated_bgr_image, detections_list)

    def __init__(self, model, image_path, conf, iou):
        super().__init__()
        self.model = model
        self.image_path = image_path
        self.conf = conf
        self.iou = iou

    def run(self):
        results_list = []
        annotated_img = None
        try:
            frame = cv2.imread(self.image_path)
            if frame is None:
                self.finished_signal.emit(None, [])
                return
            original_frame = frame.copy()
            results = self.model(frame, conf=self.conf, iou=self.iou, verbose=False)
            annotated_img = self._draw_detections(original_frame, results[0], results_list)
        except Exception as e:
            print(f"[DetectionThread] 推理异常: {e}")
        finally:
            self.finished_signal.emit(annotated_img, results_list)

    def _draw_detections(self, frame, result, results_list):
        """
        在图像上绘制所有检测框
        按病灶类别使用不同颜色边框，标签格式："病灶名 置信度%"
        """
        annotated = frame.copy()
        if result.boxes is None or len(result.boxes) == 0:
            return annotated
        for box in result.boxes:
            class_id = int(box.cls[0])
            confidence = float(box.conf[0])
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())

            # 获取病灶名称（回退处理未知类ID）
            class_name = CLASS_NAMES.get(class_id, f"unknown_{class_id}")

            # 【变更】按类别取对应颜色，未识别类默认医疗蓝
            box_color = CLASS_COLORS_BGR.get(class_id, (255, 93, 22))

            # 用该类别专属颜色绘制边框
            cv2.rectangle(annotated, (x1, y1), (x2, y2), box_color, 2)

            # 标签文字：病灶名 + 置信度百分比
            label_text = f"{class_name} {confidence:.0%}"
            (text_w, text_h), baseline = cv2.getTextSize(
                label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2
            )
            label_y1 = max(y1 - text_h - 12, 0)
            label_y2 = y1 - 4
            # 标签背景使用同色
            cv2.rectangle(annotated, (x1, label_y1),
                          (x1 + text_w + 8, label_y2), box_color, -1)
            cv2.putText(annotated, label_text,
                        (x1 + 4, label_y2 - baseline // 2 - 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)

            # 记录检测结果（用于后续分级和表格展示）
            center_x = (x1 + x2) / 2.0
            center_y = (y1 + y2) / 2.0
            results_list.append({
                "class_id": class_id,
                "class_name": class_name,
                "confidence": confidence,
                "center_x": center_x,
                "center_y": center_y,
            })
        return annotated


# ==================== 对比检测线程 ====================

class CompareThread(QThread):
    """
    双模型对比检测线程 - 同时运行两个模型进行推理
    同样输出原始4类病灶检测结果，不做分级
    """
    compare_finished = pyqtSignal(object, list, object, list)  # (v8_img, v8_results, v10_img, v10_results)

    def __init__(self, model_v8, model_v10, image_path, conf, iou):
        super().__init__()
        self.model_v8 = model_v8
        self.model_v10 = model_v10
        self.image_path = image_path
        self.conf = conf
        self.iou = iou

    def run(self):
        v8_results, v8_anno, v10_results, v10_ano = [], None, [], None
        try:
            frame = cv2.imread(self.image_path)
            if frame is None:
                self.compare_finished.emit(None, [], None, [])
                return
            try:
                res_v8 = self.model_v8(frame, conf=self.conf, iou=self.iou, verbose=False)
                # 【修复】传入实际图像 frame；_draw_detections 是实例方法需补 self=None
                v8_anno = DetectionThread._draw_detections(None, frame.copy(), res_v8[0], v8_results)
            except Exception as e:
                print(f"[CompareThread] V8推理异常: {e}")
            try:
                res_v10 = self.model_v10(frame, conf=self.conf, iou=self.iou, verbose=False)
                # 【修复】传入实际图像 frame；补 self=None
                v10_ano = DetectionThread._draw_detections(None, frame.copy(), res_v10[0], v10_results)
            except Exception as e:
                print(f"[CompareThread] V10推理异常: {e}")
        except Exception as e:
            print(f"[CompareThread] 图片读取异常: {e}")
        finally:
            self.compare_finished.emit(v8_anno, v8_results, v10_ano, v10_results)


# ==================== 主界面类 ====================

class UiMainWindow(FramelessWindow):
    """
    骨折分级智能检测系统主界面 v4
    布局策略：
      - 左侧：原始影像
      - 中间：检测结果图（医疗蓝框标注所有病灶）
      - 右侧：控制面板（上=分级结论卡片 | 下=病灶详情表格 + 对比分析）
      - 使用 QSplitter 实现左右比例可调
      - 所有图片区域 KeepAspectRatio 自适应
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("骨折分级智能检测系统")
        self.resize(1400, 850)

        # 运行状态变量
        self.current_image_path = None
        self.last_result_image = None
        self.detection_thread = None
        self.compare_thread = None
        self.model_manager = ModelManager()

        # 构建界面
        self._setup_ui()
        self._connect_signals()
        self._on_model_changed(0)

    # ==================== UI 构建 ====================

    def _setup_ui(self):
        """构建完整的主界面UI"""
        self.setStyleSheet("background: #F5F7FA;")

        # ---- 主容器 ----
        container = QWidget()
        container.setObjectName("mainContainer")
        container.setStyleSheet("""
            #mainContainer {
                background: #F5F7FA;
                border: none;
                border-radius: 12px;
            }
        """)
        self.setCentralWidget(container)

        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(2, 2, 2, 2)
        main_layout.setSpacing(0)

        # ---- 标题栏 ----
        title_bar = self._create_title_bar()
        main_layout.addWidget(title_bar)

        # ---- 内容区域 ----
        content_widget = QWidget()
        content_widget.setStyleSheet("background: transparent;")
        content_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(4)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background: #e5e6eb; border-radius: 2px;
            }
            QSplitter::handle:hover { background: #c9cdd4; }
        """)
        splitter.setStretchFactor(0, 58)
        splitter.setStretchFactor(1, 42)

        # 左侧：图片显示区（原图 + 结果图 并排）
        left_area = self._create_image_panel()
        left_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        splitter.addWidget(left_area)

        # 右侧：控制面板（分级结论 + 表格 + 对比）
        right_area = self._create_control_panel()
        right_area.setMaximumWidth(520)
        right_area.setMinimumWidth(380)
        splitter.addWidget(right_area)

        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(12, 10, 12, 10)
        content_layout.setSpacing(0)
        content_layout.addWidget(splitter)
        main_layout.addWidget(content_widget, 1)

        # ---- 状态栏 ----
        self._setup_status_bar(main_layout)

    # ---------- 标题栏 ----------

    def _create_title_bar(self):
        """创建自定义标题栏"""
        bar = QWidget()
        bar.setObjectName("titleBar")
        bar.setFixedHeight(50)
        bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        bar.setStyleSheet("""
            #titleBar {
                background: #ffffff;
                border-top-left-radius: 11px;
                border-top-right-radius: 11px;
                border-bottom: 1px solid #e5e6eb;
            }
        """)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(18, 0, 12, 0)
        layout.setSpacing(10)

        icon_lbl = QLabel("\u2695")
        icon_lbl.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        icon_lbl.setStyleSheet("font-size: 20px; background: transparent; color: #165DFF;")

        title_lbl = QLabel(" \u9aa8\u6298\u5206\u7ea7\u667a\u80fd\u68c0\u6d4b\u7cfb\u7edf  |  AI-Powered Fracture Classification")
        title_lbl.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        title_lbl.setStyleSheet("""
            color: #1d2129; font-size: 14px; font-weight: bold; letter-spacing: 1px;
        """)
        title_lbl.setWordWrap(False)

        layout.addWidget(icon_lbl)
        layout.addWidget(title_lbl)
        layout.addStretch()

        # 窗口控制按钮
        self.minimize_btn = self._make_title_btn("-", "#86909c")
        self.minimize_btn.clicked.connect(self.showMinimized)
        self.maximize_btn = self._make_title_btn("\u25a1", "#86909c")
        self.maximize_btn.clicked.connect(self.toggle_maximize)
        self.close_btn = self._make_title_btn("\u2715", "#F53F3F")
        self.close_btn.clicked.connect(self.close)

        layout.addWidget(self.minimize_btn)
        layout.addWidget(self.maximize_btn)
        layout.addWidget(self.close_btn)
        return bar

    @staticmethod
    def _make_title_btn(text, color):
        btn = QToolButton()
        btn.setText(text)
        btn.setFixedSize(30, 30)
        btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        btn.setStyleSheet(f"""
            QToolButton {{
                background-color: transparent; color: {color};
                border: none; border-radius: 15px; font-size: 13px; font-weight: bold;
            }}
            QToolButton:hover {{ background-color: #f2f3f5; }}
            QToolButton:pressed {{ background-color: #e5e6eb; }}
        """)
        return btn

    # ---------- 左侧图片面板 ----------

    def _create_image_panel(self):
        """
        左侧图片区域：原始图 与 检测结果图 水平并排
        针对窄长型医学影像优化布局
        """
        h_layout = QHBoxLayout()
        h_layout.setSpacing(10)
        h_layout.setContentsMargins(0, 0, 0, 0)

        # ── 原始图像 ──
        orig_group = QGroupBox("\u539f\u59cb\u5f71\u50cf")
        orig_group.setStyleSheet(self._card_style())
        orig_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        orig_layout = QVBoxLayout()
        orig_layout.setContentsMargins(10, 20, 10, 10)
        orig_layout.setSpacing(0)

        self.original_label = QLabel()
        self.original_label.setAlignment(Qt.AlignCenter)
        self.original_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.original_label.setMinimumSize(200, 150)
        self.original_label.setStyleSheet(self._image_display_style())
        self.original_label.setText("\u8bf7\u9009\u62e9\u5f85\u68c0\u6d4b\u7684\u533b\u5b66\u5f71\u50cf")
        orig_layout.addWidget(self.original_label, 1)
        orig_group.setLayout(orig_layout)
        h_layout.addWidget(orig_group, 1)

        # ── 检测结果图 ──
        result_group = QGroupBox("\u68c0\u6d4b\u7ed3\u679c")
        result_group.setStyleSheet(self._card_style())
        result_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        result_layout = QVBoxLayout()
        result_layout.setContentsMargins(10, 20, 10, 10)
        result_layout.setSpacing(0)

        self.result_label = QLabel()
        self.result_label.setAlignment(Qt.AlignCenter)
        self.result_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.result_label.setMinimumSize(200, 150)
        self.result_label.setStyleSheet(self._image_display_style())
        self.result_label.setText("\u7b49\u5f85\u68c0\u6d4b...")
        result_layout.addWidget(self.result_label, 1)
        result_group.setLayout(result_layout)
        h_layout.addWidget(result_group, 1)

        return self._wrap_in_widget(h_layout, expanding=True)

    # ---------- 右侧控制面板 ----------

    def _create_control_panel(self):
        """
        右侧控制面板（可滚动）
        从上到下：模型选择 → 参数 → 按钮 → 分级结论卡(新!) → 病灶表格 → 对比分析
        """
        outer_widget = QWidget()
        outer_layout = QVBoxLayout(outer_widget)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # 可滚动容器
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollArea > QWidget > QWidget { background: transparent; }
            QScrollBar:vertical {
                background: transparent; width: 6px; margin: 0;
                border: none; border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: #c9cdd4; min-height: 24px; border-radius: 3px;
            }
            QScrollBar::handle:vertical:hover { background: #86909c; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; background: none; }
        """)

        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        panel = QVBoxLayout(scroll_content)
        panel.setSpacing(8)
        panel.setContentsMargins(0, 0, 4, 0)

        # ===== 1. 模型选择卡片 =====
        model_group = QGroupBox("\u6a21\u578b\u914d\u7f6e")
        model_group.setStyleSheet(self._card_style())
        model_layout = QVBoxLayout()
        model_layout.setContentsMargins(14, 20, 14, 10)
        model_layout.setSpacing(8)

        model_layout.addWidget(self._styled_label("\u9009\u62e9\u68c0\u6d4b\u6a21\u578b"))
        self.model_combo = QComboBox()
        self.model_combo.addItems(list(MODEL_CONFIG.keys()))
        self.model_combo.setStyleSheet(self._combo_style())
        self.model_combo.setFixedHeight(34)
        self.model_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        model_layout.addWidget(self.model_combo)

        status_row = QHBoxLayout()
        self.model_status_label = QLabel("\u72b6\u6001: \u672a\u52a0\u8f7d")
        self.model_status_label.setStyleSheet("color: #86909c; font-size: 11px;")
        self.model_status_label.setWordWrap(False)
        status_row.addWidget(self.model_status_label)
        status_row.addStretch()
        model_layout.addLayout(status_row)
        model_group.setLayout(model_layout)
        panel.addWidget(model_group)

        # ===== 2. 检测参数卡片 =====
        params_group = QGroupBox("\u68c0\u6d4b\u53c2\u6570")
        params_group.setStyleSheet(self._card_style())
        params_layout = QVBoxLayout()
        params_layout.setContentsMargins(14, 20, 14, 10)
        params_layout.setSpacing(8)

        # 置信度
        self.confidence_label = self._styled_label("\u7f6e\u4fe1\u5ea6\u9608\u503c: 0.25")
        params_layout.addWidget(self.confidence_label)
        self.confidence_slider = QSlider(Qt.Horizontal)
        self.confidence_slider.setRange(0, 100)
        self.confidence_slider.setValue(25)
        self.confidence_slider.setFixedHeight(22)
        self.confidence_slider.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.confidence_slider.setStyleSheet(self._slider_style())
        params_layout.addWidget(self.confidence_slider)
        self.confidence_spinbox = QDoubleSpinBox()
        self.confidence_spinbox.setRange(0.01, 1.0)
        self.confidence_spinbox.setSingleStep(0.05)
        self.confidence_spinbox.setValue(0.25)
        self.confidence_spinbox.setFixedHeight(32)
        self.confidence_spinbox.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.confidence_spinbox.setStyleSheet(self._spinbox_style())
        params_layout.addWidget(self.confidence_spinbox)

        # IoU
        self.iou_label = self._styled_label("IoU\u9608\u503c: 0.45")
        params_layout.addWidget(self.iou_label)
        self.iou_slider = QSlider(Qt.Horizontal)
        self.iou_slider.setRange(0, 100)
        self.iou_slider.setValue(45)
        self.iou_slider.setFixedHeight(22)
        self.iou_slider.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.iou_slider.setStyleSheet(self._slider_style())
        params_layout.addWidget(self.iou_slider)
        self.iou_spinbox = QDoubleSpinBox()
        self.iou_spinbox.setRange(0.01, 1.0)
        self.iou_spinbox.setSingleStep(0.05)
        self.iou_spinbox.setValue(0.45)
        self.iou_spinbox.setFixedHeight(32)
        self.iou_spinbox.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.iou_spinbox.setStyleSheet(self._spinbox_style())
        params_layout.addWidget(self.iou_spinbox)

        params_group.setLayout(params_layout)
        panel.addWidget(params_group)

        # ===== 3. 功能按钮卡片 =====
        btn_group = QGroupBox("\u529f\u80fd\u64cd\u4f5c")
        btn_group.setStyleSheet(self._card_style())
        btn_layout = QVBoxLayout()
        btn_layout.setContentsMargins(14, 20, 14, 10)
        btn_layout.setSpacing(8)

        self.detect_btn = self._make_primary_action_btn("\u9009\u62e9\u56fe\u7247\u5e76\u68c0\u6d4b", "#165DFF")
        self.save_btn = self._make_secondary_action_btn("\u4fdd\u5b58\u68c0\u6d4b\u7ed3\u679c", "#165DFF")
        self.compare_btn = self._make_secondary_action_btn("\u53cc\u6a21\u578b\u5bf9\u6bd4\u68c0\u6d4b", "#722ED1")

        for btn in [self.detect_btn, self.save_btn, self.compare_btn]:
            btn.setFixedHeight(38)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        btn_layout.addWidget(self.detect_btn)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.compare_btn)
        btn_group.setLayout(btn_layout)
        panel.addWidget(btn_group)

        # ===== 4. 【核心新增】分级结论展示卡片 =====
        grade_group = QGroupBox("\u5206\u7ea7\u7ed3\u8bba")
        grade_group.setStyleSheet(self._card_style())
        grade_layout = QVBoxLayout()
        grade_layout.setContentsMargins(14, 20, 14, 12)
        grade_layout.setSpacing(8)

        # 第一行：分级结论大字（动态颜色）
        self.grade_title_label = QLabel("\u5c45\u67e5\u540e\u663e\u793a")
        self.grade_title_label.setAlignment(Qt.AlignCenter)
        self.grade_title_label.setWordWrap(False)
        self.grade_title_label.setMinimumHeight(36)
        self._apply_grade_default_style()
        grade_layout.addWidget(self.grade_title_label)

        # 第二行：判定依据小字
        self.grade_detail_label = QLabel("\u8bf7\u5148\u8fdb\u884c\u56fe\u7247\u68c0\u6d4b")
        self.grade_detail_label.setAlignment(Qt.AlignCenter)
        self.grade_detail_label.setWordWrap(False)
        self.grade_detail_label.setStyleSheet(
            "color: #86909c; font-size: 12px; padding: 2px 0;"
        )
        grade_layout.addWidget(self.grade_detail_label)

        # 第三行：【新增】"查看分级依据" 可点击链接按钮
        self.grade_help_btn = QLabel('<a href="#" style="color:#165DFF; font-size:12px; text-decoration:none;">\U0001f4cb \u67e5\u770b\u5206\u7ea7\u4f9d\u636e</a>')
        self.grade_help_btn.setAlignment(Qt.AlignCenter)
        self.grade_help_btn.setOpenExternalLinks(False)
        self.grade_help_btn.setCursor(Qt.PointingHandCursor)
        self.grade_help_btn.setStyleSheet("padding-top:2px;")
        self.grade_help_btn.linkActivated.connect(self._show_grading_criteria)
        grade_layout.addWidget(self.grade_help_btn)

        grade_group.setLayout(grade_layout)
        panel.addWidget(grade_group)

        # ===== 5. 病灶检测详情表格（3列）=====
        table_group = QGroupBox("\u75c5\u7076\u68c0\u6d4b\u8be6\u60c5")
        table_group.setStyleSheet(self._card_style())
        table_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        table_layout = QVBoxLayout()
        table_layout.setContentsMargins(8, 20, 8, 8)
        table_layout.setSpacing(0)

        self.results_table = QTableWidget()
        # 【重构】3列：病灶类型 | 置信度 | 位置
        self.results_table.setColumnCount(3)
        self.results_table.setHorizontalHeaderLabels([
            "\u75c5\u7076\u7c7b\u578b", "\u7f6e\u4fe1\u5ea6", "\u4f4d\u7f6e(X,Y)"
        ])
        self.results_table.verticalHeader().setVisible(False)
        self.results_table.setStyleSheet(self._table_style())
        self.results_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setStretchLastSection(True)
        self.results_table.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.results_table.setMinimumHeight(100)

        table_layout.addWidget(self.results_table, 1)
        table_group.setLayout(table_layout)
        panel.addWidget(table_group, 1)

        # ===== 6. 双模型对比分析卡片 =====
        compare_group = QGroupBox("\u53cc\u6a21\u578b\u5bf9\u6bd4\u5206\u6790")
        compare_group.setStyleSheet(self._card_style())
        compare_layout = QVBoxLayout()
        compare_layout.setContentsMargins(12, 20, 12, 8)
        compare_layout.setSpacing(6)

        self.compare_info_text = QTextEdit()
        self.compare_info_text.setReadOnly(True)
        self.compare_info_text.setMinimumHeight(90)
        self.compare_info_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.compare_info_text.setStyleSheet(self._textedit_style())
        self.compare_info_text.setText(
            "\u70b9\u51fb\u300c\u53cc\u6a21\u578b\u5bf9\u6bd4\u68c0\u6d4b\u300d\u540e\uff0c\n"
            "\u6b64\u5904\u5c06\u663e\u793a\u4e24\u4e2a\u6a21\u578b\u7684\u5bf9\u6bd4\u5206\u6790\u7ed3\u8bba\u3002"
        )
        compare_layout.addWidget(self.compare_info_text)

        split_hint = self._styled_label("\u25C0 \u5de6\u4fa7V8  |  V10 \u25B6")
        split_hint.setStyleSheet(split_hint.styleSheet() + "; color: #86909c; font-size: 11px;")
        split_hint.setWordWrap(False)
        compare_layout.addWidget(split_hint)
        compare_group.setLayout(compare_layout)
        panel.addWidget(compare_group)

        panel.addStretch(0)
        scroll.setWidget(scroll_content)
        outer_layout.addWidget(scroll, 1)
        return outer_widget

    # ---------- 状态栏 ----------

    def _setup_status_bar(self, parent_layout):
        """底部状态栏"""
        status = self.statusBar()
        status.setFixedHeight(28)
        status.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        status.setStyleSheet("""
            QStatusBar {
                background: #ffffff; color: #86909c;
                border-bottom-left-radius: 11px;
                border-bottom-right-radius: 11px;
                border-top: 1px solid #e5e6eb; font-size: 12px; padding-left: 14px;
            }
        """)
        status.showMessage("\u7cfb\u7edf\u5c31\u7eea | \u51c6\u5907\u5f00\u59cb\u68c0\u6d4b")

        grip = QSizeGrip(self)
        grip.setStyleSheet("QSizeGrip { width:18px; height:18px; background:transparent; }")
        status.addPermanentWidget(grip)

    # ══════════════════════════════════════
    #  样式工厂方法
    # ══════════════════════════════════════

    @staticmethod
    def _card_style():
        """白色圆角卡片样式"""
        return """
            QGroupBox {
                background-color: #ffffff; border-radius: 10px;
                border: none; margin-top: 2px; padding-top: 14px;
                color: #1d2129; font-size: 13px; font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin; left: 12px;
                padding: 0 4px; color: #1d2129;
            }
        """

    @staticmethod
    def _combo_style():
        return """
            QComboBox {
                background-color: #f2f3f5; color: #1d2129;
                border: 1px solid #e5e6eb; border-radius: 8px;
                padding: 6px 10px; font-size: 13px;
            }
            QComboBox:hover { border: 1px solid #c9cdd4; }
            QComboBox:focus { border: 1.5px solid #165DFF; background: #ffffff; }
            QComboBox::drop-down { border:none; width:24px; }
            QComboBox::down-arrow {
                width:0; height:0; border-left:5px solid transparent;
                border-right:5px solid transparent; border-top:6px solid #86909c;
                margin-right:6px;
            }
            QComboBox QAbstractItemView {
                background-color:#ffffff; color:#1d2129;
                selection-background-color:#E8F3FF; selection-color:#165DFF;
                border:1px solid #e5e6eb; border-radius: 8px; outline:none;
            }
            QComboBox QAbstractItemView::item { padding: 5px 10px; min-height: 26px; }
        """

    @staticmethod
    def _slider_style():
        return """
            QSlider::groove:horizontal {
                height: 4px; background: #e5e6eb; border-radius: 2px;
            }
            QSlider::sub-page:horizontal {
                background: #165DFF; border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #ffffff; border: 2px solid #165DFF;
                width: 15px; height: 15px; margin: -6px 0; border-radius: 7.5px;
            }
            QSlider::handle:horizontal:hover { background: #165DFF; }
        """

    @staticmethod
    def _spinbox_style():
        return """
            QDoubleSpinBox {
                background-color: #f2f3f5; color: #1d2129;
                border: 1px solid #e5e6eb; border-radius: 8px;
                padding: 5px 8px; font-size: 13px;
            }
            QDoubleSpinBox:focus { border: 1.5px solid #165DFF; background: #ffffff; }
            QDoubleSpinBox:hover { border: 1px solid #c9cdd4; }
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
                width: 20px; border:none; background: transparent;
            }
            QDoubleSpinBox::up-arrow, QDoubleSpinBox::down-arrow { width: 7px; height: 7px; }
        """

    @staticmethod
    def _table_style():
        """表格样式：斑马纹 + 自适应列宽"""
        return """
            QTableWidget {
                background-color: #ffffff; color: #1d2129;
                border: 1px solid #e5e6eb; border-radius: 8px;
                gridline-color: #f2f3f5; font-size: 12px;
                alternate-background-color: #fafbfc;
            }
            QTableWidget::item { padding: 4px 6px; border: none; }
            QTableWidget::item:selected {
                background-color: #E8F3FF; color: #165DFF;
            }
            QHeaderView::section {
                background: #f7f8fa; color: #4e5969;
                padding: 6px 6px; border: none;
                border-bottom: 1px solid #e5e6eb;
                font-weight: 600; font-size: 11px;
            }
            QScrollBar:vertical {
                background: transparent; width: 8px; margin: 0;
                border: none; border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #c9cdd4; min-height: 24px; border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover { background: #86909c; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0;background:none; }
        """

    @staticmethod
    def _textedit_style():
        return """
            QTextEdit {
                background: #fafbfc; color: #4e5969;
                border: 1px solid #e5e6eb; border-radius: 8px;
                font-size: 12px; padding: 8px; line-height: 1.5;
            }
        """

    @staticmethod
    def _image_display_style():
        """图片占位/显示区域样式（圆角背景）"""
        return """
            background-color: #fafbfc; border-radius: 8px;
            border: 1px dashed #e5e6eb; color: #c9cdd4; font-size: 13px;
        """

    @staticmethod
    def _make_primary_action_btn(text, color):
        btn = QPushButton(text)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color}; color: #ffffff; border: none;
                border-radius: 8px; padding: 6px; font-size: 13px;
                font-weight: 600; letter-spacing: 1px;
            }}
            QPushButton:hover {{ background-color: #4080ff; }}
            QPushButton:pressed {{ background-color: #0e42d2; }}
            QPushButton:disabled {{ background: #f2f3f5; color: #c9cdd4; }}
        """)
        return btn

    @staticmethod
    def _make_secondary_action_btn(text, color):
        btn = QPushButton(text)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent; color: {color};
                border: 1.5px solid {color}; border-radius: 8px;
                padding: 6px; font-size: 13px; font-weight: 600; letter-spacing: 1px;
            }}
            QPushButton:hover {{ background-color: {color}0f; }}
            QPushButton:pressed {{ background-color: {color}1a; }}
            QPushButton:disabled {{
                background: transparent; color: #c9cdd4; border: 1px solid #e5e6eb;
            }}
        """)
        return btn

    @staticmethod
    def _styled_label(text):
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #86909c; font-size: 12px; padding: 1px 0;")
        lbl.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        lbl.setWordWrap(False)
        return lbl

    @staticmethod
    def _wrap_in_widget(layout, expanding=True):
        widget = QWidget()
        widget.setStyleSheet("background: transparent;")
        widget.setLayout(layout)
        if expanding:
            widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        else:
            widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        return widget

    # ==================== 分级结论UI更新方法 ====================

    def _show_grading_criteria(self):
        """
        【新增】弹出"骨折分级依据说明"对话框
        展示4级分级的完整判定规则、病灶类别含义、优先级逻辑
        """
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton

        dialog = QDialog(self)
        dialog.setWindowTitle("\u9aa8\u6298\u5206\u7ea7\u4f9d\u636e\u8bf4\u660e")
        dialog.setFixedSize(520, 560)
        dialog.setStyleSheet("""
            QDialog {
                background: #F5F7FA;
                border-radius: 12px;
            }
            QLabel { color: #1d2129; font-size: 13px; line-height: 1.6; }
            QPushButton {
                background: #165DFF; color: white; font-weight: bold;
                border: none; padding: 8px 28px; border-radius: 8px;
                font-size: 13px;
            }
            QPushButton:hover { background: #0e42d2; }
            QScrollArea { background: transparent; border: 1px solid #e5e6eb; border-radius: 8px; }
        """)

        layout = QVBoxLayout(dialog)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 18, 20, 14)

        title = QLabel("<b style='font-size:16px; color:#165DFF;'>\U00002753 \u9aa8\u6298\u667a\u80fd\u5206\u7ea7\u4f9d\u636e</b>")
        layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        content_layout = QVBoxLayout(scroll_content)
        content_layout.setSpacing(8)
        content_layout.setContentsMargins(16, 12, 16, 12)

        html_text = (
            "<style>"
            ".rule-box { background:white; border-left:4px solid %s; "
            "padding:10px 14px; margin-bottom:10px; border-radius:0 8px 8px 0; }"
            "b { font-size:14px; } .sub { color:#86909c; font-size:12px; margin-top:4px; }"
            "</style>"

            "<p><b>\U0001f4a1 \u57fa\u7840\u77e5\u8bc6\uff1a\u75c5\u7076\u7c7b\u522b</b></p>"
            "<p class='sub'>\u6a21\u578b\u68c0\u6d4b\u51fa\u4ee5\u4e0b 4 \u79cd\u75c5\u7076\uff1a</p>"
            "<ul style='margin:0 0 10px 20px; color:#4e5969;'>"
            "  <li><span style='color:#F53F3F;font-weight:bold;'>fracture</span> - \u9aa8\u6298\uff08\u6838\u5fc3\u5fc5\u8981\u6761\u4ef6\uff09</li>"
            "  <li><span style='color:#FF7D00;font-weight:bold;'>periostealreaction</span> - \u9aa8\u819c\u53cd\u5e94</li>"
            "  <li><span style='color:#00B42A;font-weight:bold;'>pronatorsign</span> - \u65cb\u524d\u5f81</li>"
            "  <li><span style='color:#165DFF;font-weight:bold;'>softtissue</span> - \u8f6f\u7ec4\u7ec7\u80bf\u80c0</li>"
            "</ul>"

            "<p><b>\U0001f4cc \u5206\u7ea7\u89c4\u5219\uff08\u4f18\u5148\u7ea7\u4ece\u9ad8\u5230\u4f4e\uff09</b></p>"

            "<div class='rule-box' style='border-color:#F53F3F;'>"
            "<p><b style='color:#F53F3F;'>\u2620 \u91cd\u5ea6\u9aa8\u6298</b></p>"
            "<p class='sub'>\u5224\u5b9a\u6761\u4ef6\uff1a\u68c0\u6d4b\u5230 fracture <b>&amp;</b> periostealreaction<br/>"
            "\u65e0\u8bba\u662f\u5426\u6709\u5176\u4ed6\u75c5\u7076\uff0c\u53ea\u8981\u51fa\u73b0\u9aa8\u819c\u53cd\u5e94\u5373\u5224\u4e3a\u91cd\u5ea6</p></div>"

            "<div class='rule-box' style='border-color:#FF7D00;'>"
            "<p><b style='color:#FF7D00;'>\u26a0 \u4e2d\u5ea6\u9aa8\u6298</b></p>"
            "<p class='sub'>\u5224\u5b9a\u6761\u4ef6\uff1a\u68c0\u6d4b\u5230 fracture <b>&amp;</b> (softtissue / pronatorsign)<br/>"
            "\u4e14 <b>\u672a</b> \u68c0\u6d4b\u5230 periostealreaction</p></div>"

            "<div class='rule-box' style='border-color:#00B42A;'>"
            "<p><b style='color:#00B42A;'>\U00002705 \u8f7b\u5ea6\u9aa8\u6298</b></p>"
            "<p class='sub'>\u5224\u5b9a\u6761\u4ef6\uff1a\u4ec5\u68c0\u6d4b\u5230 fracture\uff0c<b>\u672a</b>\u68c0\u6d4b\u5230\u5176\u4ed6\u4efb\u4f55\u75c5\u7076</p></div>"

            "<div class='rule-box' style='border-color:#86909C;'>"
            "<p><b style='color:#86909C;'>\U0001f6ab \u672a\u89c1\u9aa8\u6298</b></p>"
            "<p class='sub'>\u5224\u5b9a\u6761\u4ef6\uff1a\u56fe\u50cf\u4e2d<b>\u672a\u68c0\u6d4b\u5230</b> fracture</p></div>"

            "<hr style='border:none;border-top:1px solid #e5e6eb;margin:12px 0;'/>"

            "<p><b>\U0001f504 \u5224\u5b9a邏輯\u793a\u610f</b></p>"
            "<p class='sub'>\u7cfb\u7edf\u91c7\u7528<strong>\u540e\u7f6e\u878d\u5408</strong>\u7b56\u7565\uff0a"
            "\u5148\u7531\u6a21\u578b\u8bc6\u522b\u5404\u7c7b\u75c5\u7076\uff0c"
            "\u518d\u6839\u636e\u4ee5\u4e0a\u4f18\u5148\u7ea7\u89c4\u5219\u81ea\u52a8\u5224\u5b9a\u6700\u7ec8\u5206\u7ea7\u3002"
            "\u53ea\u8981\u6ee1\u8db3\u9ad8\u4f18\u5148\u7ea7\u6761\u4ef6\u5373\u505c\u6b62\u5224\u5b9a\u3002</p>"
        )

        info_label = QLabel(html_text)
        info_label.setTextFormat(Qt.RichText)
        info_label.setWordWrap(True)
        info_label.setOpenExternalLinks(False)
        content_layout.addWidget(info_label)

        scroll.setWidget(scroll_content)
        layout.addWidget(scroll, 1)

        close_btn = QPushButton("\u6211\u77e5\u9053\u4e86")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(dialog.close)
        close_btn.setFixedHeight(36)
        layout.addWidget(close_btn)

        dialog.exec_()

    def _update_grade_display(self, grade_result=None):
        """
        更新右侧分级结论展示区
        参数：
            grade_result: FractureGrader.grade() 返回的字典，或 None（重置状态）
        """
        if grade_result is None:
            self._apply_grade_default_style()
            self.grade_title_label.setText("\u5c45\u67e5\u540e\u663e\u793a")
            self.grade_detail_label.setText("\u8bf7\u5148\u8fdb\u884c\u56fe\u7247\u68c0\u6d4b")
            return

        grade_id = grade_result["grade_id"]
        grade_name = grade_result["grade_name"]
        grade_color = grade_result["grade_color"]
        justification = grade_result["justification"]

        # 第一行：大字分级结论 + 动态颜色
        self.grade_title_label.setText(grade_name)
        self.grade_title_label.setStyleSheet(f"""
            color: {grade_color}; font-size: 24px; font-weight: bold;
            padding: 8px 0; background: transparent;
        """)

        # 第二行：灰色判定依据文字
        self.grade_detail_label.setText(f"\u5224\u5b9a\u4f9d\u636e\uff1a{justification}")

    def _apply_grade_default_style(self):
        """应用默认待机样式"""
        self.grade_title_label.setStyleSheet("""
            color: #c9cdd4; font-size: 18px; font-weight: bold;
            padding: 8px 0; background: transparent;
        """)

    # ==================== 信号连接 ====================

    def _connect_signals(self):
        """连接所有 UI 信号槽"""
        self.model_combo.currentIndexChanged.connect(self._on_model_changed)
        self.confidence_slider.valueChanged.connect(self._update_confidence_from_slider)
        self.confidence_spinbox.valueChanged.connect(self._update_confidence_from_spinbox)
        self.iou_slider.valueChanged.connect(self._update_iou_from_slider)
        self.iou_spinbox.valueChanged.connect(self._update_iou_from_spinbox)
        self.detect_btn.clicked.connect(self._detect_single_image)
        self.save_btn.clicked.connect(self._save_detection_result)
        self.compare_btn.clicked.connect(self._run_compare_detection)

    # ==================== 参数联动 ====================

    def _update_confidence_from_slider(self, value):
        val = value / 100.0
        self.confidence_spinbox.blockSignals(True)
        self.confidence_spinbox.setValue(val)
        self.confidence_spinbox.blockSignals(False)
        self.confidence_label.setText(f"\u7f6e\u4fe1\u5ea6\u9608\u503c: {val:.2f}")

    def _update_confidence_from_spinbox(self, value):
        self.confidence_slider.blockSignals(True)
        self.confidence_slider.setValue(int(value * 100))
        self.confidence_slider.blockSignals(False)
        self.confidence_label.setText(f"\u7f6e\u4fe1\u5ea6\u9608\u503c: {value:.2f}")

    def _update_iou_from_slider(self, value):
        val = value / 100.0
        self.iou_spinbox.blockSignals(True)
        self.iou_spinbox.setValue(val)
        self.iou_spinbox.blockSignals(False)
        self.iou_label.setText(f"IoU\u9608\u503c: {val:.2f}")

    def _update_iou_from_spinbox(self, value):
        self.iou_slider.blockSignals(True)
        self.iou_slider.setValue(int(value * 100))
        self.iou_slider.blockSignals(False)
        self.iou_label.setText(f"IoU\u9608\u503c: {value:.2f}")

    # ==================== 模型管理 ====================

    def _on_model_changed(self, index):
        """切换模型时重新加载"""
        display_name = self.model_combo.currentText()
        weight_name = MODEL_CONFIG.get(display_name)
        if not weight_name:
            self.model_status_label.setText("\u72b6\u6001: \u65e0\u6548\u6a21\u578b\u9009\u9879")
            self.model_status_label.setStyleSheet("color: #F53F3F; font-size: 11px;")
            return

        weight_path = os.path.join(WEIGHTS_DIR, weight_name)
        if not os.path.exists(weight_path):
            self.model_status_label.setText("\u72b6\u6001: \u6a21\u578b\u6587\u4ef6\u7f3a\u5931")
            self.model_status_label.setStyleSheet("color: #F53F3F; font-size: 11px;")
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(
                self, "\u6a21\u578b\u6587\u4ef6\u672a\u627e\u5230",
                f"\u65e0\u6cd5\u627e\u5230\u6a21\u578b\u6743\u91cd\u6587\u4ef6:\n{weight_path}\n\n"
                f"\u8bf7\u786e\u8ba4 weights/ \u76ee\u5f55\u4e0b\u5b58\u5728 {weight_name}\n\n"
                f"\u63d0\u793a\uff1a\u53ef\u5c06\u8bad\u7ec3\u597d\u7684 best.pt \u91cd\u547d\u540d\u540e\u653e\u5165\u8be5\u76ee\u5f55\u3002"
            )
            return

        success = self.model_manager.load_model(weight_path, display_name)
        if success:
            short_name = display_name.split()[0]
            self.model_status_label.setText(f"\u72b6\u6001: {short_name} \u5c31\u7eea")
            self.model_status_label.setStyleSheet("color: #00B42A; font-size: 11px;")
            self.update_status(f"\u6a21\u578b\u52a0\u8f7d\u6210\u529f: {display_name}")
        else:
            self.model_status_label.setText("\u72b6\u6001: \u52a0\u8f7d\u5931\u8d25")
            self.model_status_label.setStyleSheet("color: #F53F3F; font-size: 11px;")

    # ==================== 业务逻辑：单图检测 ====================

    def _detect_single_image(self):
        """选择图片并执行单模型检测"""
        from PyQt5.QtWidgets import QFileDialog, QMessageBox
        file_path, _ = QFileDialog.getOpenFileName(
            self, "\u9009\u62e9\u533b\u5b66\u5f71\u50cf",
            "",
            IMAGE_FILE_DIALOG_FILTER,
        )
        if not file_path:
            return

        if not _suffix_allowed_for_image(file_path):
            QMessageBox.warning(
                self,
                "\u683c\u5f0f\u9519\u8bef",
                "\u6240\u9009\u6587\u4ef6\u4e0d\u662f\u652f\u6301\u7684\u533b\u5b66\u5f71\u50cf\u683c\u5f0f\uff0c\u8bf7\u9009\u62e9 JPG\u3001JPEG\u3001PNG\u3001BMP\u3001TIF\u3001TIFF \u7b49\u56fe\u50cf\u6587\u4ef6\u3002",
            )
            return

        test_img = cv2.imread(file_path)
        if test_img is None:
            QMessageBox.warning(
                self,
                "\u683c\u5f0f\u9519\u8bef",
                "\u65e0\u6cd5\u5c06\u6240\u9009\u6587\u4ef6\u89e3\u6790\u4e3a\u56fe\u50cf\uff0c\u53ef\u80fd\u6587\u4ef6\u5df2\u635f\u574f\u6216\u5185\u5bb9\u4e0e\u6269\u5c55\u540d\u4e0d\u7b26\u3002",
            )
            return

        self.current_image_path = file_path
        self.clear_results()

        # 显示原始图像
        rgb_img = cv2.cvtColor(test_img, cv2.COLOR_BGR2RGB)
        self.display_image(self.original_label, rgb_img)

        self.result_label.clear()
        self.result_label.setStyleSheet(self._image_display_style())
        self.result_label.setText("\u6b63\u5728\u68c0\u6d4b...")

        # 重置分级显示为待机态
        self._update_grade_display(None)

        conf = self.confidence_spinbox.value()
        iou = self.iou_spinbox.value()
        current_model = self.model_manager.get_current_model()

        if current_model is None:
            self.result_label.setStyleSheet(self._image_display_style())
            self.result_label.setText("\u7b49\u5f85\u68c0\u6d4b...")
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "\u63d0\u793a",
                "\u6a21\u578b\u672a\u52a0\u8f7d\u6210\u529f\uff0c\u65e0\u6cd5\u68c0\u6d4b\u3002\u8bf7\u67e5\u53f3\u4fa7\u300c\u6a21\u578b\u914d\u7f6e\u300d\u72b6\u6001\uff0c\u5b8c\u5168\u9000\u51fa\u7a0b\u5e8f\u540e\u518d\u91cd\u542f\uff1b\u82e5\u4ecd\u5931\u8d25\uff0c\u8bf7\u5728\u8fd0\u884c\u7a0b\u5e8f\u7684\u7ec8\u7aef\u4e2d\u67e5\u770b\u9519\u8bef\u4fe1\u606f\u3002",
            )
            return

        self.detect_btn.setEnabled(False)
        self.detect_btn.setText("\u68c0\u6d4b\u4e2d...")

        self.detection_thread = DetectionThread(current_model, file_path, conf, iou)
        self.detection_thread.finished_signal.connect(self._on_single_detect_done)
        self.detection_thread.start()

        self.update_status(f"\u6b63\u5728\u68c0\u6d4b: {os.path.basename(file_path)}")

    def _on_single_detect_done(self, annotated_bgr, detections):
        """
        单图检测完成回调
        流程：显示结果图 → 调用FractureGrader分级 → 更新表格 → 更新分级结论卡
        """
        self.detect_btn.setEnabled(True)
        self.detect_btn.setText("\u9009\u62e9\u56fe\u7247\u5e76\u68c0\u6d4b")

        if annotated_bgr is None:
            self.result_label.setStyleSheet(self._image_display_style())
            self.result_label.setText("\u68c0\u6d4b\u5931\u8d25")
            self.update_status("\u68c0\u6d4b\u5931\u8d25\uff0c\u8bf7\u68c0\u67e5\u56fe\u7247\u6216\u6a21\u578b\u3002")
            # 即使失败也尝试分级（无检测结果 → 未见骨折）
            grade_result = FractureGrader.grade([])
            self._update_grade_display(grade_result)
            return

        # 显示检测结果图
        rgb_annotated = cv2.cvtColor(annotated_bgr, cv2.COLOR_BGR2RGB)
        self.display_image(self.result_label, rgb_annotated)
        self.last_result_image = annotated_bgr

        # 【核心】调用后置融合分级器
        grade_result = FractureGrader.grade(detections)
        self._update_grade_display(grade_result)

        # 填充病灶详情表格（仅展示原始检测信息，不含分级）
        for idx, det in enumerate(detections):
            row_idx = self.results_table.rowCount()
            self.results_table.insertRow(row_idx)
            # 3列：病灶类型 | 置信度 | 位置
            items_data = [
                det["class_name"],
                f"{det['confidence']:.1%}",
                f"({det['center_x']:.0f}, {det['center_y']:.0f})",
            ]
            for col_idx, txt in enumerate(items_data):
                item = QTableWidgetItem(txt)
                item.setTextAlignment(Qt.AlignCenter)
                item.setForeground(QColor("#1d2129"))
                self.results_table.setItem(row_idx, col_idx, item)

        # 更新状态栏
        total_count = len(detections)
        grade_name = grade_result["grade_name"]
        if total_count > 0:
            self.update_status(
                f"\u68c0\u6d4b\u5b8c\u6210 | {total_count}\u5904\u75c5\u7076 | \u5206\u7ea7: {grade_name}"
            )
        else:
            self.update_status(f"\u68c0\u6d4b\u5b8c\u6210 | \u672a\u68c0\u6d4b\u5230\u75c5\u7070 | \u5206\u7ea7: {grade_name}")

    # ==================== 业务逻辑：双模型对比 ====================

    def _run_compare_detection(self):
        """启动双模型对比检测"""
        from PyQt5.QtWidgets import QFileDialog, QMessageBox

        if not self.current_image_path:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "\u9009\u62e9\u7528\u4e8e\u5bf9\u6bd4\u7684\u533b\u5b66\u5f71\u50cf",
                "",
                IMAGE_FILE_DIALOG_FILTER,
            )
            if not file_path:
                return
            if not _suffix_allowed_for_image(file_path):
                QMessageBox.warning(
                    self,
                    "\u683c\u5f0f\u9519\u8bef",
                    "\u6240\u9009\u6587\u4ef6\u4e0d\u662f\u652f\u6301\u7684\u533b\u5b66\u5f71\u50cf\u683c\u5f0f\uff0c\u8bf7\u9009\u62e9 JPG\u3001JPEG\u3001PNG\u3001BMP\u3001TIF\u3001TIFF \u7b49\u56fe\u50cf\u6587\u4ef6\u3002",
                )
                return
            test_img = cv2.imread(file_path)
            if test_img is None:
                QMessageBox.warning(
                    self,
                    "\u683c\u5f0f\u9519\u8bef",
                    "\u65e0\u6cd5\u5c06\u6240\u9009\u6587\u4ef6\u89e3\u6790\u4e3a\u56fe\u50cf\uff0c\u53ef\u80fd\u6587\u4ef6\u5df2\u635f\u574f\u6216\u5185\u5bb9\u4e0e\u6269\u5c55\u540d\u4e0d\u7b26\u3002",
                )
                return
            self.current_image_path = file_path
            self.display_image(self.original_label, cv2.cvtColor(test_img, cv2.COLOR_BGR2RGB))

        model_v8 = self.model_manager.load_model(
            os.path.join(WEIGHTS_DIR, "yolov8_best.pt"), "YOLOv8"
        )
        model_v10 = self.model_manager.load_model(
            os.path.join(WEIGHTS_DIR, "yolov10_best.pt"), "YOLOv10"
        )

        if model_v8 is None or model_v10 is None:
            QMessageBox.warning(self, "\u6a21\u578b\u4e0d\u53ef\u7528",
                                "\u53cc\u6a21\u578b\u5bf9\u6bd4\u9700\u8981\u540c\u65f6\u52a0\u8f7d YOLOv8 \u548c YOLOv10 \u6a21\u578b\u3002\n"
                                "\u8bf7\u786e\u8ba4 weights/ \u76ee\u5f55\u4e0b\u5305\u542b yolov8_best.pt \u548c yolov10_best.pt\u3002")
            return

        conf = self.confidence_spinbox.value()
        iou = self.iou_spinbox.value()

        self.clear_results()
        self.compare_btn.setEnabled(False)
        self.compare_btn.setText("\u5bf9\u6bd4\u68c0\u6d4b\u4e2d...")

        self.compare_thread = CompareThread(model_v8, model_v10, self.current_image_path, conf, iou)
        self.compare_thread.compare_finished.connect(self._on_compare_done)
        self.compare_thread.start()

        self.update_status("\u53cc\u6a21\u578b\u5bf9\u6bd4\u68c0\u6d4b\u4e2d...")

    def _on_compare_done(self, v8_image, v8_results, v10_image, v10_results):
        """
        双模型对比完成回调
        分别对 V8/V10 结果做独立分级，在分级结论区和对比报告中分别展示
        """
        self.compare_btn.setEnabled(True)
        self.compare_btn.setText("\u53cc\u6a21\u578b\u5bf9\u6bd4\u68c0\u6d4b")

        # 不清除原图，保留左侧原始影像
        self.result_label.clear()

        combined_display = self._create_split_view(v8_image, v10_image)
        if combined_display is not None:
            self.display_image(self.result_label, combined_display)
            self.last_result_image = combined_display

        # 【核心】对两组检测结果分别做后置融合分级
        v8_grade = FractureGrader.grade(v8_results)
        v10_grade = FractureGrader.grade(v10_results)
        # 分级结论区显示当前选中模型的分级（或V8作为主要参考）
        self._update_grade_display(v8_grade)

        # 合并填充表格
        all_results = []
        for d in v8_results:
            dc = dict(d); dc["model"] = "V8"; all_results.append(dc)
        for d in v10_results:
            dc = dict(d); dc["model"] = "V10"; all_results.append(dc)

        for idx, det in enumerate(all_results):
            row_idx = self.results_table.rowCount()
            self.results_table.insertRow(row_idx)
            model_tag = det.get('model', '?')
            items_data = [
                f"{det['class_name']} ({model_tag})",
                f"{det['confidence']:.1%}",
                f"({det['center_x']:.0f}, {det['center_y']:.0f})",
            ]
            for col_idx, txt in enumerate(items_data):
                item = QTableWidgetItem(txt)
                item.setTextAlignment(Qt.AlignCenter)
                item.setForeground(QColor("#1d2129"))
                self.results_table.setItem(row_idx, col_idx, item)

        # 生成对比报告（含双方分级结论）
        report = self._generate_compare_report(v8_results, v10_results, v8_grade, v10_grade)
        self.compare_info_text.setText(report)
        self.update_status("\u53cc\u6a21\u578b\u5bf9\u6bd4\u68c0\u6d4b\u5b8c\u6210")

    def _create_split_view(self, img_left, img_right):
        """创建左右分屏拼接图像（V8 | V10）"""
        if img_left is None and img_right is None:
            return None
        if img_left is None:
            return img_right
        if img_right is None:
            return img_left

        h1, w1 = img_left.shape[:2]
        h2, w2 = img_right.shape[:2]
        target_h = max(h1, h2)

        if h1 < target_h:
            img_left = cv2.resize(img_left, (int(w1 * target_h / h1), target_h))
        elif h2 < target_h:
            img_right = cv2.resize(img_right, (int(w2 * target_h / h2), target_h))

        lw = img_left.shape[1]
        rw = img_right.shape[1]
        gap = 4
        combined_w = lw + rw + gap
        combined = np.zeros((target_h, combined_w, 3), dtype=np.uint8)
        combined[:, :lw] = img_left
        combined[:, lw+gap:] = img_right
        combined[:, lw:lw+gap] = [240, 242, 245]

        cv2.putText(combined, "YOLOv8", (15, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.85, (22, 93, 255), 2)
        cv2.putText(combined, "YOLOv10", (lw + gap + 15, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.85, (114, 46, 209), 2)
        return combined

    def _generate_compare_report(self, v8_results, v10_results, v8_grade, v10_grade):
        """
        生成双模型对比报告
        包含检测数量、置信度、以及各自的后置融合分级结论
        """
        lines = ["\u2500\u2500\u2500 \u53cc\u6a21\u578b\u5bf9\u6bd4\u5206\u6790\u62a5\u544a \u2500\u2500\u2500\n"]

        v8_count = len(v8_results)
        v8_max_conf = max([r["confidence"] for r in v8_results]) if v8_results else 0

        v10_count = len(v10_results)
        v10_max_conf = max([r["confidence"] for r in v10_results]) if v10_results else 0

        # V8 信息
        lines.append(f"\u3010YOLOv8\u3011  \u68c0\u51fa\u6570\u91cf: {v8_count}  \u6700\u9ad8\u7f6e\u4fe1\u5ea6: {v8_max_conf:.1%}")
        lines.append(f"           \u5206\u7ea7\u7ed3\u8bba: {v8_grade['grade_name']}\uff08{v8_grade['justification']}\uff09")
        lines.append("")

        # V10 信息
        lines.append(f"\u3010YOLOv10\u3011  \u68c0\u51fa\u6570\u91cf: {v10_count}  \u6700\u9ad8\u7f6e\u4fe1\u5ea6: {v10_max_conf:.1%}")
        lines.append(f"            \u5206\u7ea7\u7ed3\u8bba: {v10_grade['grade_name']}\uff08{v10_grade['justification']}\uff09")
        lines.append("")

        # 综合结论
        lines.append("\u3010\u7efc\u5408\u7ed3\u8bba\u3011")
        if v8_count == 0 and v10_count == 0:
            lines.append("  \u4e24\u6a21\u578b\u5747\u672a\u68c0\u51fa\u75c5\u7070\u5f81\u8c61\uff0c\u5efa\u8bae\u7ed3\u5408\u4e34\u5e8a\u8bca\u65ad\u3002")
        else:
            diff = abs(v8_count - v10_count)
            if v10_count > v8_count:
                lines.append(f"  YOLOv10 \u591a\u68c0\u51fa {diff} \u5904\u76ee\u6807\uff0c\u654f\u611f\u5ea6\u66f4\u9ad8\u3002")
            elif v8_count > v10_count:
                lines.append(f"  YOLOv8 \u591a\u68c0\u51fa {diff} \u5904\u76ee\u6807\u3002")
            else:
                lines.append(f"  \u4e24\u6a21\u578b\u68c0\u51fa\u6570\u91cf\u4e00\u81f4\uff0c\u5747\u4e3a {v8_count} \u5904\u3002")
            if v10_max_conf > v8_max_conf:
                lines.append(f"  YOLOv10 \u6700\u9ad8\u7f6e\u4fe1\u5ea6\u66f4\u9ad8 ({v10_max_conf:.1%} > {v8_max_conf:.1%})\u3002")
            elif v8_max_conf > v10_max_conf:
                lines.append(f"  YOLOv8 \u6700\u9ad8\u7f6e\u4fe1\u5ea6\u66f4\u9ad8 ({v8_max_conf:.1%} > {v10_max_conf:.1%})\u3002")

        # 分级一致性判断
        if v8_grade["grade_id"] == v10_grade["grade_id"]:
            lines.append(f"  \u5206\u7ea7\u4e00\u81f4\uff1a\u4e24\u6a21\u578b\u5224\u5b9a均为\u3010{v8_grade['grade_name']}\u3011\u3002")
        else:
            lines.append(
                f"  \u5206\u7ea7\u5dee\u5f02\uff1aV8\u5224\u5b9a\u3010{v8_grade['grade_name']}\u3011 vs "
                f"V10\u5224\u5b9a\u3010{v10_grade['grade_name']}\u3011\uff0c\u5efa\u8bae\u7ed3\u5408\u4e34\u5e8a\u8bca\u65ad\u3002"
            )

        return "\n".join(lines)

    # ==================== 结果保存 ====================

    def _save_detection_result(self):
        """保存检测结果图片"""
        from PyQt5.QtWidgets import QFileDialog, QMessageBox
        if self.last_result_image is None:
            QMessageBox.information(self, "\u63d0\u793a",
                                    "\u6682\u65e0\u68c0\u6d4b\u7ed3\u679c\u53ef\u4fdd\u5b58\u3002\n\u8bf7\u5148\u6267\u884c\u56fe\u7247\u68c0\u6d4b\u6216\u5bf9\u6bd4\u68c0\u6d4b\u3002")
            return

        save_dir = os.path.join(os.getcwd(), "results")
        os.makedirs(save_dir, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        default_name = f"fracture_detect_{timestamp}.jpg"

        save_path, _ = QFileDialog.getSaveFileName(
            self, "\u4fdd\u5b58\u68c0\u6d4b\u7ed3\u679c",
            os.path.join(save_dir, default_name),
            "JPEG \u56fe\u7247 (*.jpg);;PNG \u56fe\u7247 (*.png);;\u6240\u6709\u6587\u4ef6 (*.*)",
        )
        if save_path:
            try:
                cv2.imwrite(save_path, self.last_result_image)
                self.update_status(f"\u7ed3\u679c\u5df2\u4fdd\u5b58\u81f3: {save_path}")
            except Exception as e:
                QMessageBox.critical(self, "\u4fdd\u5b58\u5931\u8d25", f"\u5199\u5165\u6587\u4ef6\u65f6\u51fa\u9519:\n{str(e)}")

    # ══════════════════════════════════════
    #  公共工具方法
    # ══════════════════════════════════════

    @staticmethod
    def display_image(label, rgb_image):
        """在QLabel上显示 OpenCV RGB 图像（KeepAspectRatio不变形）"""
        if rgb_image is None:
            return
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qimg = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg)
        scaled = pixmap.scaled(label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        label.setPixmap(scaled)
        label.setStyleSheet(UiMainWindow._image_display_style())

    def clear_results(self):
        """
        清空所有检测结果展示区域
        包括：病灶表格、分级结论区、对比分析区
        每次更换检测图片时自动调用，避免残留上一次的数据
        """
        # 1. 清空病灶详情表格
        self.results_table.setRowCount(0)

        # 2. 重置分级结论为待机状态
        self._apply_grade_default_style()
        self.grade_title_label.setText("\u5c45\u67e5\u540e\u663e\u793a")
        self.grade_detail_label.setText("\u8bf7\u5148\u8fdb\u884c\u56fe\u7247\u68c0\u6d4b")

        # 3. 重置双模型对比分析区
        self.compare_info_text.setText(
            "\u70b9\u51fb\u300c\u53cc\u6a21\u578b\u5bf9\u6bd4\u68c0\u6d4b\u300d\u540e\uff0c\n"
            "\u6b64\u5904\u5c06\u663e\u793a\u4e24\u4e2a\u6a21\u578b\u7684\u5bf9\u6bd4\u5206\u679e\u7ed3\u8bba\u3002"
        )

    def update_status(self, message):
        """更新状态栏文本"""
        now = time.strftime("%H:%M:%S")
        self.statusBar().showMessage(f"\u72b6\u6001: {message} | {now}")

    # ==================== 窗口事件 ====================

    def closeEvent(self, event):
        """窗口关闭时清理检测线程"""
        if self.detection_thread and self.detection_thread.isRunning():
            self.detection_thread.quit()
            self.detection_thread.wait(3000)
        if self.compare_thread and self.compare_thread.isRunning():
            self.compare_thread.quit()
            self.compare_thread.wait(3000)
        event.accept()


# ==================== 模型管理器 ====================

class ModelManager:
    """模型管理器 - 封装加载与缓存，支持多模型切换"""

    def __init__(self):
        self._models = {}
        self._current_key = None
        self._current_name = ""

    def load_model(self, weight_path, display_name=""):
        """加载模型（带缓存机制，避免重复加载）"""
        if weight_path in self._models:
            self._current_key = weight_path
            self._current_name = display_name
            return self._models[weight_path]
        if not os.path.exists(weight_path):
            print(f"[ModelManager] 模型文件不存在: {weight_path}")
            return None
        try:
            from ultralytics import YOLO
            model = YOLO(weight_path)
            self._models[weight_path] = model
            self._current_key = weight_path
            self._current_name = display_name
            print(f"[ModelManager] 模型加载成功: {display_name} -> {weight_path}")
            return model
        except Exception as e:
            print(f"[ModelManager] 模型加载失败: {e}")
            return None

    def get_current_model(self):
        """获取当前已加载的模型实例"""
        if self._current_key is not None:
            return self._models.get(self._current_key)
        return None
