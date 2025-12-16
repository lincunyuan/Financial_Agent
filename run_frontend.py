import subprocess
import sys
import os

# 获取当前目录
current_dir = os.path.dirname(os.path.abspath(__file__))

# 构建Streamlit命令
streamlit_command = [
    sys.executable,
    "-m",
    "streamlit",
    "run",
    "app.py",
    "--server.port",
    "8503",  # 更改端口为8503
    "--server.address",
    "localhost"
]

print("=== 启动金融助手前端界面 ===")
print(f"正在启动Streamlit服务器...")
print(f"访问地址: http://localhost:8503")  # 更新访问地址
print(f"按 Ctrl+C 停止服务器")
print("===========================")

# 启动Streamlit服务器
subprocess.run(streamlit_command, cwd=current_dir)