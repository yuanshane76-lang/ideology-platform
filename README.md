# Ideology-Platform 🎓

<div align="center">

**基于 LangGraph 多智能体架构的思政教育智能化平台**

[![Python](https://img.shields.io/badge/Python-3.13-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0-green.svg)](https://flask.palletsprojects.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2-orange.svg)](https://github.com/langchain-ai/langgraph)
[![Qdrant](https://img.shields.io/badge/Qdrant-1.9-red.svg)](https://qdrant.tech/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## 📖 项目简介

**Ideology-Platform** 是一个面向高校思政教育领域的智能化教学辅助平台，融合了检索增强生成（RAG）、多智能体协作、流式推理等前沿 AI 技术，为思政课程学习提供智能问答、PPT 自动生成、哲学辩论训练三大核心功能。

本平台覆盖《马克思主义基本原理》、《思想道德与法治》、《中国近现代史纲要》、《毛泽东思想和中国特色社会主义理论体系概论》、《习近平新时代中国特色社会主义思想概论》等核心思政课程内容。

---

## 🏗️ 系统架构

### 整体架构图

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

---

## 🔧 核心技术框架

### 1. 多智能体协作系统 (LangGraph)

采用 **Supervisor 模式** 构建多智能体协作网络，实现复杂任务的分解与协同处理：

| 智能体 | 职责 | 技术实现 |
|--------|------|----------|
| **RouterAgent** | 意图识别与路由分发 | LLM-based Classification |
| **MemoryAgent** | 对话上下文检索与管理 | Vector Similarity Search |
| **TheoryRetriever** | 理论知识库检索 | Hybrid RAG (Dense + Sparse) |
| **PoliticsRetriever** | 时政案例库检索 | Temporal-aware Retrieval |
| **GeneratorAgent** | 答案生成与流式输出 | Streaming Generation |
| **ValidatorAgent** | 答案质量校验 | LLM-as-Judge |

```python
# 工作流状态机定义
class AgentState(TypedDict):
    query: str
    intent: str
    context: List[Document]
    references: List[Reference]
    answer: str
    validation: ValidationResult
```

### 2. 检索增强生成 (RAG)

#### 双库检索架构

```
┌─────────────────┐     ┌─────────────────┐
│   Theory DB     │     │   Politics DB   │
│  (教材知识库)    │     │  (时政案例库)   │
│                 │     │                 │
│ • 马克思主义原理 │     │ • 时事新闻      │
│ • 思想道德与法治 │     │ • 政策解读      │
│ • 毛泽东思想概论 │     │ • 社会热点      │
│ • 中国近现代史  │     │ • 典型案例      │
│ • 新时代思想    │     │                 │
└────────┬────────┘     └────────┬────────┘
         │                       │
         └───────────┬───────────┘
                     ▼
         ┌─────────────────────┐
         │  Reference Composer │
         │  • 向量去重         │
         │  • 内容清洗         │
         │  • 引用高亮         │
         └─────────────────────┘
```

#### 向量检索配置

```python
# Qdrant 向量数据库配置
COLLECTION_CONFIG = {
    "vectors": {
        "size": 1024,           # text-embedding-v4 维度
        "distance": "Cosine"    # 余弦相似度
    },
    "optimizers_config": {
        "indexing_threshold": 10000
    }
}

# 检索策略
RETRIEVAL_STRATEGY = {
    "top_k": 8,
    "score_threshold": 0.7,
    "rerank": True,
    "hybrid_search": True      # 混合稠密+稀疏检索
}
```

### 3. 流式响应系统 (SSE)

基于 Server-Sent Events 实现实时流式输出，提供即时反馈：

```python
# Flask SSE 响应模式
@app.route('/api/chat', methods=['POST'])
def chat_endpoint():
    return Response(
        stream_with_context(chat_service_stream(conversation_id, query)),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'  # 禁用 Nginx 缓冲
        }
    )
```

**流式事件类型**：
- `thinking`: 思考过程展示
- `content`: 内容增量输出
- `reference`: 引用文献推送
- `done`: 完成信号

### 4. HTML-to-PPTX 生成引擎

创新性地采用 HTML 作为中间表示，实现高度灵活的 PPT 生成：

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  AI Outline │ ──▶ │ HTML Slides │ ──▶ │  Playwright │ ──▶ │  python-pptx│
│  Generator  │     │  Generator  │     │  Screenshot │     │  Assembler  │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
                                                │
                                                ▼
                                        ┌─────────────┐
                                        │ PNG → PPTX  │
                                        │  Slide      │
                                        └─────────────┘
```

**主题系统**：

| 主题 | 配色方案 | CSS 变量 |
|------|----------|----------|
| 党建红 | `#C41E3A` + `#FFD700` | `--primary`, `--accent` |
| 科技蓝 | `#1E90FF` + `#00CED1` | `--primary`, `--accent` |
| 简约白 | `#FFFFFF` + `#6B7280` | `--primary`, `--accent` |
| 学术绿 | `#059669` + `#34D399` | `--primary`, `--accent` |

### 5. 红芯理辩系统

基于辩证思维的 AI 辩论训练系统：

```
┌─────────────────────────────────────────────────────────────────┐
│                     Debate Session Flow                          │
│                                                                   │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐   │
│  │  Topic   │ ─▶ │  Pro     │ ─▶ │  Con     │ ─▶ │  Judge   │   │
│  │ Analysis │    │ Opening  │    │ Rebuttal │    │ Summary  │   │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘   │
│       │              │               │               │          │
│       ▼              ▼               ▼               ▼          │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐   │
│  │ Stance   │    │ Marxism  │    │ Dialectic│    │ Synthesis│   │
│  │ Detection│    │ Principles│    │ Analysis │    │ & Insight│   │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

**辩论角色设定**：
- **红芯正方**: 坚定捍卫马克思主义立场，逻辑清晰有力
- **红芯反方**: 犀利辩证，多角度审视，指出逻辑漏洞
- **红芯裁判**: 中立客观，综合评议，提炼哲学启示

---

## 🚀 快速开始

### 环境要求

- Python 3.8+
- 阿里云 DashScope API Key
- Playwright（用于 PPT 截图）

### 安装步骤

```bash
# 1. 克隆仓库
git clone https://github.com/yuanshane76-lang/ideology-rag.git
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

## 📁 项目结构

```
ideology-platform/
├── app.py                      # Flask 主应用入口
├── requirements.txt            # Python 依赖
├── .env                        # 环境变量配置
│
├── src/                        # 核心源代码
│   ├── agents/                 # 智能体模块
│   │   ├── router_agent.py     # 路由智能体
│   │   ├── memory_agent.py     # 记忆智能体
│   │   ├── theory_retriever_agent.py   # 理论检索智能体
│   │   ├── politics_retriever_agent.py # 时政检索智能体
│   │   ├── generator_agent.py  # 生成智能体
│   │   └── validator_agent.py  # 验证智能体
│   │
│   ├── ppt/                    # PPT 生成模块
│   │   ├── agent.py            # PPT 智能体入口
│   │   ├── outline_generator.py    # 大纲生成器
│   │   ├── html_generator.py       # HTML 幻灯片生成
│   │   ├── html_to_ppt.py          # HTML 转 PPT
│   │   ├── chapter_builders.py     # 章节构建器
│   │   └── themes/                 # 主题系统
│   │       └── html_themes.py
│   │
│   ├── debate/                 # 红芯理辩模块
│   │   ├── models.py           # 数据模型
│   │   ├── service.py          # 辩论服务
│   │   ├── constants.py        # 常量定义
│   │   └── topic_agent.py      # 辩题分析智能体
│   │
│   ├── graph.py                # LangGraph 工作流定义
│   ├── service.py              # 对话服务层
│   ├── retriever.py            # 检索逻辑
│   ├── reference_composer.py   # 引用文献整合器
│   ├── clients.py              # API 客户端
│   ├── config.py               # 配置管理
│   └── conversation.py         # 对话管理
│
├── templates/                  # HTML 模板
│   ├── index.html              # 问答页面
│   ├── ppt.html                # PPT 生成页面
│   └── debate.html             # 红芯理辩页面
│
├── static/                     # 静态资源
│   ├── app.js                  # 问答前端逻辑
│   ├── ppt.js                  # PPT 前端逻辑
│   ├── debate.js               # 理辩前端逻辑
│   └── style.css               # 样式文件
│
├── Qdrant/                     # 向量数据库存储
│   └── qdrant_db/
│       └── collection/
│           ├── theory/         # 理论知识库
│           ├── moment/         # 时政案例库
│           └── debate/         # 辩论素材库
│
├── outputs/                    # 输出文件
│   ├── html/                   # HTML 幻灯片缓存
│   └── ppt/                    # 生成的 PPT 文件
│
└── tests/                      # 测试用例
    └── test_*.py
```

---

## ⚡ 性能优化

### 优化措施

| 优化项 | 改动 | 效果 |
|--------|------|------|
| **API 并发控制** | Semaphore 3 → 8 | 充分利用百炼高并发能力 |
| **生成模型选择** | qwen3-max → qwen-turbo | 延迟降低 50% |
| **验证模型优化** | qwen-flash → qwen-turbo | 延迟降低 40% |
| **高亮识别异步化** | 同步阻塞 → 后台异步 | 不阻塞主流程响应 |
| **引用清理并发** | 串行处理 → 并发处理 N 条 | 引用加载加速 70% |

### 性能指标

| 指标 | 优化前 | 优化后 | 提升 |
|------|--------|--------|------|
| 总响应耗时 | 15s | 5-6s | ⬇️ 65% |
| 首字延迟 | 2s | 0.5s | ⬇️ 75% |
| 引用加载 | 8s | 2-3s | ⬇️ 70% |
| 文档下载 | 8-10s | 1-2s | ⬇️ 80% |

---

## 🔌 API 接口

### 对话接口

```http
POST /api/chat
Content-Type: application/json

{
  "query": "马克思主义的基本特征是什么？",
  "conversation_id": "optional-uuid"
}

Response: SSE Stream
event: thinking
data: {"content": "正在检索相关知识..."}

event: content
data: {"content": "马克思主义的基本特征包括..."}

event: reference
data: {"references": [...]}

event: done
data: {"conversation_id": "uuid", "title": "自动生成的标题"}
```

### PPT 生成接口

```http
POST /api/ppt/outline
Content-Type: application/json

{
  "query": "生成一份关于文化自信的 PPT"
}

Response:
{
  "success": true,
  "outline": {
    "title": "文化自信",
    "chapters": [...]
  }
}
```

### 辩论接口

```http
POST /api/debate/stream
Content-Type: application/json

{
  "title": "努力一定能改变命运吗",
  "rounds": 2
}

Response: SSE Stream
event: protagonist
data: {"content": "正方观点..."}

event: antagonist
data: {"content": "反方反驳..."}

event: judge
data: {"content": "裁判总结..."}
```

---

## 🛠️ 技术栈

### 后端

| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.13 | 主要开发语言 |
| Flask | 3.0 | Web 框架 |
| LangGraph | 0.2+ | 多智能体工作流编排 |
| LangChain | 0.2+ | LLM 应用开发框架 |
| Qdrant | 1.9+ | 向量数据库 |
| DashScope | 1.14+ | 阿里云大模型服务 |

### 文档处理

| 技术 | 用途 |
|------|------|
| python-docx | Word 文档生成 |
| python-pptx | PPT 文件组装 |
| Playwright | HTML 截图渲染 |

### 前端

| 技术 | 用途 |
|------|------|
| HTML5 | 页面结构 |
| Tailwind CSS | 样式框架 |
| Vanilla JavaScript | 交互逻辑 |
| Server-Sent Events | 流式通信 |

---

## 📊 系统特性

- ✅ **多智能体协作**: Supervisor 模式编排，职责分离，高效协同
- ✅ **双库检索增强**: 理论+时政双库互补，知识覆盖全面
- ✅ **流式实时响应**: SSE 长连接，首字延迟 < 1s
- ✅ **引用溯源**: 自动提取、清理、高亮引用文献
- ✅ **PPT 智能生成**: HTML 中间表示，主题灵活可扩展
- ✅ **辩证思维训练**: 红芯理辩系统，哲学方法论实践
- ✅ **高性能并发**: 异步处理，响应时间优化 65%+

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

---

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件。

---

<div align="center">

**如果这个项目对你有帮助，请给一个 ⭐️ Star！**

</div>
