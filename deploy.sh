#!/bin/bash
# ============================================
# 思政云伴侣 - Docker 一键部署脚本
# 使用方法: bash deploy.sh
# ============================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=========================================="
echo "  思政云伴侣 - Docker 部署"
echo "=========================================="

# ---- 1. 检查 Docker ----
echo ""
echo -e "${YELLOW}[STEP 1]${NC} 检查 Docker 环境..."
if ! command -v docker &> /dev/null; then
    echo -e "${RED}错误: Docker 未安装${NC}"
    echo "请先安装 Docker: curl -fsSL https://get.docker.com | sh"
    exit 1
fi

if ! docker compose version &> /dev/null; then
    echo -e "${RED}错误: Docker Compose V2 未安装${NC}"
    echo "请更新 Docker 到包含 Compose V2 的版本"
    exit 1
fi

echo -e "${GREEN}Docker 环境正常${NC}"

# ---- 2. 检查 .env ----
echo ""
echo -e "${YELLOW}[STEP 2]${NC} 检查环境变量..."
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}.env 不存在，从模板创建...${NC}"
    cp .env.example .env
    echo -e "${RED}请编辑 .env 填入你的 DASHSCOPE_API_KEY！${NC}"
    echo "  命令: nano .env"
    echo ""
    read -p "已填好 API Key？按回车继续..."
fi

# 检查 API Key 是否还是占位符
if grep -q "your_api_key_here" .env 2>/dev/null; then
    echo -e "${RED}警告: .env 中 DASHSCOPE_API_KEY 仍为占位符，服务将无法正常工作${NC}"
    read -p "是否继续部署？(y/N) " -n 1 -r
    echo
    [[ ! $REPLY =~ ^[Yy]$ ]] && exit 1
fi

# ---- 3. 检查 Qdrant 数据 ----
echo ""
echo -e "${YELLOW}[STEP 3]${NC} 检查向量数据库..."
if [ ! -d "./Qdrant/qdrant_db/collection" ]; then
    echo -e "${RED}警告: Qdrant 向量数据目录不存在！${NC}"
    echo "请确保 Qdrant/qdrant_db 目录已从开发机复制过来"
    echo "  包含 theory、moment、debate_chunks 等集合"
    read -p "数据已就位？按回车继续..."
else
    COLLECTION_COUNT=$(ls ./Qdrant/qdrant_db/collection/ 2>/dev/null | wc -l)
    echo -e "${GREEN}向量数据库正常，包含 ${COLLECTION_COUNT} 个集合${NC}"
fi

# ---- 4. 检查教材数据 ----
echo ""
echo -e "${YELLOW}[STEP 4]${NC} 检查教材内容..."
if [ ! -d "./content/textbook" ]; then
    echo -e "${RED}警告: 教材内容目录不存在！${NC}"
    echo "请确保 content/ 目录已从开发机复制过来"
    read -p "数据已就位？按回车继续..."
else
    echo -e "${GREEN}教材内容目录正常${NC}"
fi

# ---- 5. 创建运行时目录 ----
echo ""
echo -e "${YELLOW}[STEP 5]${NC} 创建运行时目录..."
mkdir -p outputs/html outputs/ppt outputs/ppt_image_cache \
    downloads cache/sessions Qdrant/qdrant_db
# 确保 chat_history.db 存在（避免 Docker 挂载目录而非文件）
touch -a chat_history.db 2>/dev/null || true
touch -a daily_news.json 2>/dev/null || true
echo -e "${GREEN}目录就绪${NC}"

# ---- 6. 构建镜像 ----
echo ""
echo -e "${YELLOW}[STEP 6]${NC} 构建 Docker 镜像（首次约 5-8 分钟）..."
docker compose build

echo ""
echo -e "${GREEN}镜像构建完成${NC}"

# ---- 7. 启动服务 ----
echo ""
echo -e "${YELLOW}[STEP 7]${NC} 启动服务..."
docker compose up -d

echo ""
echo "=========================================="
echo -e "  ${GREEN}部署完成！${NC}"
echo "=========================================="
echo ""
echo "访问地址: http://$(hostname -I 2>/dev/null | awk '{print $1}' || echo '<服务器IP>'):6006"
echo ""
echo "常用命令:"
echo "  查看日志:   docker compose logs -f"
echo "  停止服务:   docker compose down"
echo "  重启服务:   docker compose restart"
echo "  查看状态:   docker compose ps"
echo "  重新构建:   docker compose up -d --build"
echo ""
