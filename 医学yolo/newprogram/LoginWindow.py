# -*- coding: utf-8 -*-
"""
LoginWindow.py - 登录注册窗口模块
功能：基于 PyQt5 QDialog 实现用户登录与注册界面
数据存储：本地 JSON 文件 (accounts.json)，用户名-密码键值对
UI风格：极简医疗蓝白扁平设计
"""

import os
import json
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QMessageBox, QFrame
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QColor


class LoginWindow(QDialog):
    """登录注册窗口 - 极简医疗蓝白扁平风格"""

    # 分级颜色映射常量（供外部引用）
    FRACTURE_LEVELS = {
        0: ("轻度骨折", "#00B42A"),   # 医疗绿 - 轻度
        1: ("中度骨折", "#FF7D00"),   # 橙色 - 中度
        2: ("重度骨折", "#F53F3F"),   # 红色 - 重度
    }

    def __init__(self):
        super().__init__()
        self.setWindowTitle("骨折分级智能检测系统 - 用户登录")
        self.setFixedSize(420, 520)
        self.setup_ui()
        self.load_accounts()

    # ==================== UI 构建 ====================

    def setup_ui(self):
        """构建登录窗口完整UI布局"""
        # 窗口整体样式：浅灰背景，无硬边框
        self.setStyleSheet("""
            QDialog {
                background: #F5F7FA;
                color: #1d2129;
            }
        """)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(36, 32, 36, 32)
        main_layout.setSpacing(20)

        # ── 标题区域（深色标题 + 蓝色装饰线）──
        title_label = QLabel("骨折分级智能检测系统")
        title_label.setStyleSheet("""
            font-size: 22px;
            font-weight: bold;
            color: #1d2129;
            padding-bottom: 12px;
            border-bottom: 2px solid #165DFF;
            letter-spacing: 2px;
        """)
        title_label.setAlignment(Qt.AlignCenter)

        subtitle = QLabel("用户身份验证")
        subtitle.setStyleSheet("""
            font-size: 13px;
            color: #86909c;
            margin-top: -8px;
        """)
        subtitle.setAlignment(Qt.AlignCenter)

        # ── 表单容器（白色圆角卡片）──
        form_frame = QFrame()
        form_frame.setStyleSheet("""
            QFrame {
                background: #ffffff;
                border-radius: 12px;
                border: none;
            }
        """)  # 无边框纯白卡片

        form_layout = QVBoxLayout()
        form_layout.setSpacing(18)
        form_layout.setContentsMargins(24, 28, 24, 28)

        # 用户名输入
        username_label = QLabel("用户名")
        username_label.setStyleSheet("font-size: 13px; color: #4e5969; font-weight: bold;")
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("请输入用户名")
        self.username_input.setStyleSheet(self._get_input_style())

        # 密码输入
        password_label = QLabel("密码")
        password_label.setStyleSheet("font-size: 13px; color: #4e5969; font-weight: bold;")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("请输入密码（至少6位）")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setStyleSheet(self._get_input_style())

        # 按钮行（主按钮填充 + 次按钮描边）
        button_layout = QHBoxLayout()
        button_layout.setSpacing(14)

        self.login_btn = QPushButton("登 录")
        self.login_btn.setStyleSheet(self._get_primary_button_style())
        self.login_btn.setFixedHeight(44)

        self.register_btn = QPushButton("注 册")
        self.register_btn.setStyleSheet(self._get_secondary_button_style())
        self.register_btn.setFixedHeight(44)

        button_layout.addWidget(self.login_btn)
        button_layout.addWidget(self.register_btn)

        # 提示文字
        hint_label = QLabel("首次使用请先注册账号")
        hint_label.setStyleSheet("font-size: 12px; color: #86909c;")
        hint_label.setAlignment(Qt.AlignCenter)

        # 组装表单
        form_layout.addWidget(username_label)
        form_layout.addWidget(self.username_input)
        form_layout.addWidget(password_label)
        form_layout.addWidget(self.password_input)
        form_layout.addLayout(button_layout)
        form_layout.addWidget(hint_label)
        form_frame.setLayout(form_layout)

        # 组装主布局
        main_layout.addWidget(title_label)
        main_layout.addWidget(subtitle)
        main_layout.addWidget(form_frame)
        main_layout.addStretch()
        self.setLayout(main_layout)

        # 绑定信号槽
        self.login_btn.clicked.connect(self.handle_login)
        self.register_btn.clicked.connect(self.handle_register)
        # 回车键触发登录
        self.password_input.returnPressed.connect(self.handle_login)

    # ==================== 样式方法 ====================

    @staticmethod
    def _get_input_style():
        """输入框统一样式：浅灰底 + 圆角 + 聚焦蓝色高亮"""
        return """
            QLineEdit {
                background: #f2f3f5;
                border: 1px solid #e5e6eb;
                border-radius: 8px;
                padding: 11px 14px;
                color: #1d2129;
                font-size: 14px;
                selection-background-color: #165DFF30;
            }
            QLineEdit:focus {
                border: 1.5px solid #165DFF;
                background: #ffffff;
            }
            QLineEdit:hover {
                border: 1px solid #c9cdd4;
            }
        """

    @staticmethod
    def _get_primary_button_style():
        """主按钮样式：医疗蓝填充，白色文字，无发光"""
        return """
            QPushButton {
                background-color: #165DFF;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 4px;
                font-size: 14px;
                font-weight: 600;
                letter-spacing: 4px;
            }
            QPushButton:hover {
                background-color: #4080ff;
            }
            QPushButton:pressed {
                background-color: #0e42d2;
            }
        """

    @staticmethod
    def _get_secondary_button_style():
        """次按钮样式：蓝色描边 + 蓝色文字（扁平化）"""
        return """
            QPushButton {
                background-color: transparent;
                color: #165DFF;
                border: 1.5px solid #165DFF;
                border-radius: 8px;
                padding: 4px;
                font-size: 14px;
                font-weight: 600;
                letter-spacing: 4px;
            }
            QPushButton:hover {
                background-color: #165DFF0f;
            }
            QPushButton:pressed {
                background-color: #165DFF1a;
            }
        """

    # ==================== 账户管理 ====================

    def load_accounts(self):
        """从 accounts.json 加载账户数据到内存字典"""
        self.accounts = {}
        account_path = os.path.join(os.path.dirname(__file__), "accounts.json")
        if os.path.exists(account_path):
            try:
                with open(account_path, "r", encoding="utf-8") as f:
                    self.accounts = json.load(f)
            except (json.JSONDecodeError, IOError):
                pass  # 文件损坏时以空字典开始

    def save_accounts(self):
        """将当前账户数据写回 accounts.json"""
        account_path = os.path.join(os.path.dirname(__file__), "accounts.json")
        try:
            with open(account_path, "w", encoding="utf-8") as f:
                json.dump(self.accounts, f, ensure_ascii=False, indent=2)
        except IOError as e:
            QMessageBox.critical(self, "错误", f"保存账户数据失败：{str(e)}")

    # ==================== 业务逻辑 ====================

    def handle_login(self):
        """处理登录请求"""
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        # 非空校验
        if not username or not password:
            QMessageBox.warning(self, "提示", "用户名和密码不能为空！")
            return

        # 凭证校验
        if username in self.accounts and self.accounts[username] == password:
            self.accept()  # 关闭窗口并返回 QDialog.Accepted
        else:
            QMessageBox.warning(self, "登录失败", "用户名或密码错误，请重新输入。")
            self.password_input.clear()
            self.password_input.setFocus()

    def handle_register(self):
        """处理新用户注册"""
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        # 非空校验
        if not username or not password:
            QMessageBox.warning(self, "提示", "用户名和密码不能为空！")
            return

        # 唯一性校验
        if username in self.accounts:
            QMessageBox.warning(self, "注册失败", "该用户名已被注册，请更换用户名。")
            return

        # 密码强度校验
        if len(password) < 6:
            QMessageBox.warning(self, "提示", "密码长度至少需要6个字符，请重新设置。")
            self.password_input.setFocus()
            return

        # 写入账户数据
        self.accounts[username] = password
        self.save_accounts()
        QMessageBox.information(self, "注册成功",
                                f"账号「{username}」注册成功！\n现在可以使用该账号登录系统。")
