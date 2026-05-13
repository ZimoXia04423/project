"""
启动项目仪表盘（不执行训练）
启动本地HTTP服务器并自动打开浏览器查看 dashboard.html
"""
import os
import sys
import webbrowser
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
PORT = 8080


def check_output():
    """检查 output 目录是否存在且有结果文件"""
    output_dir = os.path.join(PROJECT_DIR, "output")
    if not os.path.exists(output_dir):
        print("[警告] output/ 目录不存在，请先运行 python main.py 生成结果数据。")
        return False
    files = os.listdir(output_dir)
    if not files:
        print("[警告] output/ 目录为空，请先运行 python main.py 生成结果数据。")
        return False
    print(f"[信息] 检测到 {len(files)} 个结果文件:")
    for f in sorted(files):
        print(f"  - {f}")
    return True


def open_browser():
    """延迟打开浏览器"""
    url = f"http://localhost:{PORT}/dashboard.html"
    webbrowser.open(url)


def main():
    print("=" * 50)
    print("  电商评论虚假信息识别 - 仪表盘启动器")
    print("=" * 50)

    if not check_output():
        sys.exit(1)

    os.chdir(PROJECT_DIR)

    print(f"\n[启动] HTTP服务器: http://localhost:{PORT}")
    print(f"[访问] 仪表盘地址: http://localhost:{PORT}/dashboard.html")
    print("[提示] 按 Ctrl+C 停止服务器\n")

    # 1秒后自动打开浏览器
    threading.Timer(1, open_browser).start()

    server = HTTPServer(("0.0.0.0", PORT), SimpleHTTPRequestHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[停止] 服务器已关闭")
        server.server_close()


if __name__ == "__main__":
    main()
