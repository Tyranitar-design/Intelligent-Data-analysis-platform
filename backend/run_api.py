"""启动 FastAPI 服务"""
import sys
import os

# 获取当前脚本所在目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 添加项目根目录到路径
sys.path.insert(0, BASE_DIR)

# 确保使用虚拟环境
VENV_PATH = os.path.join(BASE_DIR, "venv", "Lib", "site-packages")
if os.path.exists(VENV_PATH) and VENV_PATH not in sys.path:
    sys.path.insert(0, VENV_PATH)

import uvicorn

if __name__ == "__main__":
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
