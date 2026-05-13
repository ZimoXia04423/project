# -*- coding: utf-8 -*-
"""
main.py - 骨折分级智能检测系统 入口程序
功能：程序启动入口，负责初始化登录流程与主窗口调度
运行方式: python main.py
"""

import sys
import os

# 将程序目录添加到 Python 搜索路径，确保相对导入正常工作
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Windows：须在任何 PyQt5 模块加载之前初始化 torch，否则后续 ultralytics 导入 torch
# 时可能出现 WinError 1114（c10.dll 初始化失败），界面表现为「模型加载失败」。
try:
    import torch  # noqa: F401
except ImportError:
    pass

from PyQt5.QtWidgets import QApplication, QDialog
from PyQt5.QtCore import Qt

from LoginWindow import LoginWindow
from UiMain import UiMainWindow


def main():
    """应用程序主函数"""
    # 创建 Qt 应用实例
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # 使用 Fusion 风格保证跨平台一致性

    # 设置全局字体（中文友好）
    font = app.font()
    font.setFamily("Microsoft YaHei" if sys.platform == "win32" else "PingFang SC")
    app.setFont(font)

    # ── 第一步：登录认证 ──
    login_window = LoginWindow()

    # 以模态对话框形式显示登录窗口
    # 用户点击「登录」成功时返回 QDialog.Accepted
    # 用户关闭窗口时返回 QDialog.Rejected
    login_result = login_window.exec_()

    if login_result == QDialog.Accepted:
        # ── 第二步：进入主系统 ──
        main_window = UiMainWindow()
        main_window.show()
        exit_code = app.exec_()
    else:
        # 用户取消登录，直接退出
        exit_code = 0

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
