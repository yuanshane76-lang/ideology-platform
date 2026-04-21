# Ideology-Platform 🎓 思政云

<div align="center">

**基于 LangGraph 多智能体架构的思政教育智能化平台**

[![Python](https://img.shields.io/badge/Python-3.13-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0-green.svg)](https://flask.palletsprojects.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2-orange.svg)](https://github.com/langchain-ai/langgraph)
[![Qdrant](https://img.shields.io/badge/Qdrant-1.9-red.svg)](https://qdrant.tech/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**🌐 在线体验：http://82.156.211.237:6006**

</div>

---

## 📖 项目简介

**Ideology-Platform（思政云）** 是一款面向高校思政教育领域的智能化教学辅助平台，融合检索增强生成（RAG）、多智能体协作、流式推理等前沿 AI 技术，为思政课程学习提供一站式智能服务。

平台覆盖《马克思主义基本原理》、《思想道德与法治》、《中国近现代史纲要》、《毛泽东思想和中国特色社会主义理论体系概论》、《习近平新时代中国特色社会主义思想概论》等核心思政课程内容。

---

## ✨ 五大核心功能

### 📚 1. 教材伴读系统

沉浸式结构化阅读体验，让思政教材"活"起来：

- **智能目录导航**：可视化章节结构，一键跳转到任意小节
- **AI 伴读助手**：选中任意段落，即可进行解释、提问、记笔记
- **概念关联图谱**：自动识别并关联相关知识点，构建知识网络
- **阅读进度同步**：自动保存阅读位置，支持多设备接续阅读

> 💡 **使用场景**：课前预习时快速定位重点，课后复习时查漏补缺

---

### 💬 2. 智能问答系统

基于 RAG 技术的思政知识问答，让理论学习更高效：

- **双库融合检索**：教材知识库 + 时政案例库，理论与实践结合
- **流式实时响应**：AI 思考过程实时可见，答案逐字呈现
- **精准溯源引用**：每个答案都附带原文出处，支持一键跳转验证
- **多轮上下文对话**：支持追问和深入探讨，像老师一样耐心解答

> 💡 **使用场景**：遇到不理解的概念随时提问，写论文时查找理论依据

---

### 📊 3. PPT 智能生成

输入主题，一键生成专业级思政课件：

- **AI 大纲规划**：自动分析主题，生成逻辑清晰的幻灯片结构
- **智能内容填充**：结合教材内容自动填充每页要点
- **精美主题切换**：党建红、科技蓝、学术绿等多种风格可选
- **高清导出下载**：自动生成可编辑的 `.pptx` 文件

> 💡 **使用场景**：课堂展示、小组汇报、党课宣讲，5 分钟搞定课件

---

### ⚔️ 4. 红芯理辩系统

基于辩证思维的 AI 辩论训练，提升批判性思维能力：

- **三方角色扮演**：红芯正方、红芯反方、红芯裁判，模拟真实辩论
- **哲学深度论证**：结合马克思主义原理进行立论与反驳
- **攻防策略训练**：学习如何构建论点、寻找漏洞、组织反击
- **全程记录复盘**：保存辩论记录，支持事后回顾分析

> 💡 **使用场景**：准备辩论赛、锻炼思辨能力、深入理解辩证唯物主义

---

### 📰 5. 思政要闻整理

每日自动聚合最新时政热点，理论联系实际：

- **智能抓取聚合**：自动采集权威媒体的时政要闻
- **AI 智能摘要**：自动生成新闻摘要，快速了解核心内容
- **理论关联分析**：自动关联教材相关知识点，学以致用
- **定时更新推送**：每日 8 点自动刷新，保持内容时效性

> 💡 **使用场景**：了解时事动态、积累时政案例、准备时政考试

---

## 🏗️ 技术架构

### 系统架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Frontend Layer                                 │
│                   (HTML + Tailwind CSS + Vanilla JS)                     │
└─────────────────────────────┬───────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         API Gateway (Flask)                              │
│                    REST API + SSE Streaming                              │
└─────────────────────────────┬───────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   QA Service    │ │   PPT Service   │ │ Debate Service  │
│  (RAG Pipeline) │ │ (HTML-to-PPTX)  │ │ (Multi-Round)   │
└────────┬────────┘ └────────┬────────┘ └────────┬────────┘
         │                   │                   │
         ▼                   ▼                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     LangGraph Multi-Agent System                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │  Router  │ │  Memory  │ │ Retriever│ │Generator │ │Validator │       │
│  │  Agent   │→│  Agent   │→│  Agents  │→│  Agent   │→│  Agent   │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
└─────────────────────────────┬───────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      Knowledge Layer                                     │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐                │
│  │  Theory DB    │  │  Politics DB  │  │  Debate DB    │                │
│  │  (Qdrant)     │  │  (Qdrant)     │  │  (Qdrant)     │                │
│  └───────────────┘  └───────────────┘  └───────────────┘                │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     LLM Layer (DashScope)                                │
│         Qwen-Turbo (推理)  |  Qwen-Flash (快速任务)  |  Text-Embedding-V4 │
└─────────────────────────────────────────────────────────────────────────┘
```

### 核心技术栈

| 技术领域 | 选型 | 说明 |
|---------|------|------|
| **后端框架** | Flask | 轻量级 Python Web 框架 |
| **AI 框架** | LangGraph | 多智能体工作流编排 |
| **向量数据库** | Qdrant | 高性能向量检索 |
| **LLM 服务** | DashScope | 阿里云大模型 API |
| **前端技术** | Tailwind CSS | 原子化 CSS 框架 |
| **PPT 生成** | Playwright + python-pptx | HTML 渲染转 PPT |

---

## 🚀 快速开始

### 环境要求

- Python 3.8+
- 阿里云 DashScope API Key
- Playwright（用于 PPT 截图）
- **Qdrant 向量数据库数据（重要！）**

### 安装步骤

```bash
# 1. 克隆仓库
git clone https://github.com/yuanshane76-lang/ideology-platform.git
cd ideology-platform

# 2. 安装依赖
pip install -r requirements.txt

# 3. 安装 Playwright 浏览器
playwright install chromium

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入你的 DashScope API Key
```

### 配置说明

创建 `.env` 文件：

```env
# DashScope API 配置
DASHSCOPE_API_KEY=your_api_key_here
BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

# 模型配置
LLM_MODEL=qwen-turbo          # 主力推理模型
AUDITOR_MODEL=qwen-turbo      # 审核验证模型
FAST_MODEL=qwen-flash         # 快速任务模型
EMBEDDING_MODEL=text-embedding-v4
VECTOR_DIM=1024

# 向量数据库配置
QDRANT_PATH=./Qdrant/qdrant_db
```

### 启动服务

```bash
python app.py
```

访问 http://127.0.0.1:6006 即可使用。

---

## ⚠️ 重要部署说明

### 关于 Qdrant 向量数据库

**GitHub 仓库不包含 Qdrant 数据文件**，因此直接克隆代码无法运行问答功能。Qdrant 数据包含：
- 教材知识向量库（约 500MB）
- 时政案例向量库
- 辩论语料向量库

**获取数据的方式**：
1. **联系作者**获取 Qdrant 数据文件
2. **自行构建**：使用 `scripts/` 目录下的数据预处理脚本生成
3. **使用空数据运行**：修改配置跳过向量检索（功能受限）

**数据目录结构**：
```
Qdrant/
└── qdrant_db/
    ├── theory/          # 教材知识库
    ├── politics/        # 时政案例库
    └── debate/          # 辩论语料库
```

---

## 🌐 公网部署

### 方案一：Cloudflare Tunnel（免费推荐）

适合快速测试和演示，无需购买服务器：

```bash
# 1. 安装 cloudflared
winget install cloudflare.cloudflared

# 2. 启动应用
python app.py

# 3. 启动隧道（新终端）
cloudflared tunnel --url http://localhost:6006

# 会生成公网 URL: https://xxx-xxx-xxx.trycloudflare.com
```

**特点**：
- ✅ 完全免费，5分钟配置
- ✅ 自带HTTPS证书
- ✅ 支持WebSocket和SSE流式接口
- ⚠️ 需要本地电脑保持开机

### 方案二：云服务器部署（生产推荐）

适合长期稳定运行，支持定时任务：

**服务器配置**（<20并发）：
- CPU: 1核
- 内存: 2G
- 带宽: 2-3Mbps
- 成本: 约30-50元/月

**部署步骤**：

```bash
# 1. 安装依赖
sudo apt update
sudo apt install python3.13 python3.13-venv nginx

# 2. 配置Python环境
python3.13 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. 使用Gunicorn启动（单进程多线程，避免Qdrant锁文件问题）
gunicorn -w 1 --threads 6 -b 127.0.0.1:6006 --timeout 120 app:app
```

**Nginx配置**：
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:6006;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        
        # SSE流式接口必需配置
        proxy_buffering off;
        proxy_cache off;
    }
}
```

**systemd服务配置**：
```ini
[Unit]
Description=Ideology Platform
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/path/to/ideology-platform
Environment="PATH=/path/to/ideology-platform/venv/bin"
ExecStart=/path/to/venv/bin/gunicorn -w 1 --threads 6 -b 127.0.0.1:6006 --timeout 120 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

**定时任务（每天8点刷新思政要闻）**：
```bash
# 编辑crontab
crontab -e

# 添加定时任务
0 8 * * * cd /path/to/ideology-platform && /path/to/venv/bin/python refresh_news.py >> /var/log/news_refresh.log 2>&1
```

---

## 📁 项目结构

```
ideology-platform/
├── app.py                      # Flask 主应用入口
├── requirements.txt            # Python 依赖
├── .env                        # 环境变量配置
├── LICENSE                     # MIT 许可证
│
├── src/                        # 核心源代码
│   ├── agents/                 # 智能体模块
│   ├── ppt/                    # PPT 生成模块
│   ├── debate/                 # 红芯理辩模块
│   ├── textbook/               # 教材伴读模块
│   ├── news/                   # 思政要闻模块
│   ├── graph.py                # LangGraph 工作流
│   └── service.py              # 对话服务层
│
├── templates/                  # HTML 模板
├── static/                     # 静态资源
├── content/                    # 教材内容数据
├── Qdrant/                     # 向量数据库（需单独获取）
└── scripts/                    # 数据处理脚本
```

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建你的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开一个 Pull Request

---

## 📄 许可证

本项目基于 [MIT License](LICENSE) 开源。

Copyright (c) 2025 yuanshane76-lang

---

## 💬 联系我们

如有问题或建议，欢迎通过以下方式联系：

- 📧 Email: 45070293@qq.com
- 🐙 GitHub Issues: [提交问题](https://github.com/yuanshane76-lang/ideology-platform/issues)

---

<div align="center">

**⭐ 如果这个项目对你有帮助，请给个 Star 支持一下！**

</div>
