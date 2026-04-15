#!/bin/bash
# AutoDL 部署脚本
# 使用方法: bash deploy_autodl.sh

set -e

echo "=========================================="
echo "  思政云伴侣 - AutoDL 部署脚本"
echo "=========================================="

# 检查Python版本
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "[INFO] Python版本: $PYTHON_VERSION"

# 1. 创建虚拟环境
echo "[STEP 1] 创建虚拟环境..."
python3 -m venv venv
source venv/bin/activate

# 2. 安装依赖
echo "[STEP 2] 安装Python依赖..."
pip install --upgrade pip
pip install -r requirements.txt

# 3. 安装Playwright浏览器
echo "[STEP 3] 安装Playwright浏览器（Chromium）..."
playwright install chromium
playwright install-deps chromium

# 4. 检查环境变量
echo "[STEP 4] 检查环境变量..."
if [ ! -f ".env" ]; then
    echo "[WARNING] .env文件不存在，正在创建模板..."
    cat > .env << 'EOF'
# DashScope API配置
DASHSCOPE_API_KEY=your_api_key_here
BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen-turbo
AUDITOR_MODEL=qwen-turbo
FAST_MODEL=qwen-flash
EMBEDDING_MODEL=text-embedding-v4
VECTOR_DIM=1024
QDRANT_PATH=./Qdrant/qdrant_db
MAX_MESSAGES_BEFORE_SUMMARY=10
MAX_CHARS_BEFORE_SUMMARY=6000

MAX_RETRY_COUNT=2
CONFIDENCE_THRESHOLD=0.7
MAX_MEMORY_TURNS=5
DEFAULT_THEORY_TOP_K=3
DEFAULT_POLITICS_TOP_K=3

# 讯飞PPT配置（可选）
XUNFEI_PPT_APP_ID=
XUNFEI_PPT_API_SECRET=
XUNFEI_PPT_API_KEY=

# SiliconFlow API配置（可选）
SILICONFLOW_API_KEY=
EOF
    echo "[WARNING] 请编辑 .env 文件填入你的API Key！"
fi

# 5. 检查Qdrant数据
echo "[STEP 5] 检查向量数据库..."
if [ -d "./Qdrant/qdrant_db" ]; then
    echo "[INFO] 向量数据库已存在"
else
    echo "[WARNING] 向量数据库不存在，请确保复制了Qdrant目录"
fi

# 6. 创建输出目录
echo "[STEP 6] 创建输出目录..."
mkdir -p outputs/html outputs/ppt outputs/ppt_image_cache downloads cache/sessions

echo ""
echo "=========================================="
echo "  部署完成！"
echo "=========================================="
echo ""
echo "启动方式："
echo "  开发模式: python app.py"
echo "  生产模式: gunicorn -w 1 --threads 6 -b 0.0.0.0:6006 --timeout 120 app:app"
echo "  后台运行: nohup gunicorn -w 1 --threads 6 -b 0.0.0.0:6006 --timeout 120 app:app > app.log 2>&1 &"
echo ""
echo "【推荐】使用systemd管理服务："
echo "  cp ideology.service /etc/systemd/system/"
echo "  systemctl daemon-reload"
echo "  systemctl enable ideology"
echo "  systemctl start ideology"
echo "  systemctl status ideology"
echo ""
echo "访问地址: http://<服务器公网IP>:6006"
echo ""
