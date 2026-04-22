# ============================================
# 思政云伴侣 - Docker 镜像
# 基于 Python 3.12 slim，内置 Playwright Chromium
# ============================================

FROM docker.mirrors.ustc.edu.cn/library/python:3.12-slim AS base

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PLAYWRIGHT_BROWSERS_PATH=/opt/playwright

WORKDIR /app

# ---- 依赖安装层（利用 Docker 缓存） ----
# 先只复制依赖文件，依赖不变时无需重新安装
COPY requirements.txt .

# 安装系统依赖 + Python 依赖 + Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Playwright 系统依赖
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 libxcomposite1 \
    libxdamage1 libxfixes3 libxrandr2 libgbm1 \
    libpango-1.0-0 libcairo2 libasound2 \
    # 字体支持（中文渲染）
    fonts-noto-cjk \
    # 其他工具
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --upgrade pip \
    && pip install -r requirements.txt \
    && playwright install chromium --with-deps

# ---- 应用代码层 ----
COPY . .

# 创建必要目录
RUN mkdir -p outputs/html outputs/ppt outputs/ppt_image_cache \
    downloads cache/sessions

# 暴露端口
EXPOSE 6006

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:6006/ || exit 1

# 生产模式启动
CMD ["gunicorn", "-w", "1", "--threads", "6", "-b", "0.0.0.0:6006", "--timeout", "120", "app:app"]
