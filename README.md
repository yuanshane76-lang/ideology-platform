# Ideology-RAG 思政教育智能问答系统

基于 LangGraph 的多智能体 RAG（检索增强生成）架构，专注于思政教育领域的智能问答平台。涵盖马克思主义理论、思想道德与法治、中国近现代史纲要、毛泽东思想和中国特色社会主义理论体系概论、习近平新时代中国特色社会主义思想概论等多门思政课程内容。

## 🌟 项目特点

- **多智能体协作架构**：采用 Supervisor 模式协调多个专业智能体
- **双库检索系统**：理论库 + 时政库，提供全面的知识支持
- **流式响应**：实时显示思考过程和生成内容
- **对话历史管理**：支持多轮对话和会话管理
- **智能标题生成**：自动为对话生成简洁标题
- **引用文献溯源**：自动提取、清理、高亮引用文献，支持 docx 下载
- **PPT 智能生成**：基于 HTML 转 PPT 技术，支持多种主题风格
- **高性能并发**：优化后总耗时从 15s 降至 5-6s，首字延迟 0.5s
- **红芯理辩**：AI驱动的哲学辩论训练，通过正反交锋帮助用户理解马克思主义哲学原理

## 🏗️ 系统架构

### 问答系统架构

```
用户提问
    ↓
RouterAgent（路由分析）
    ↓
MemoryAgent（记忆检索）→ TheoryRetriever（理论检索）
                              ↓
                        PoliticsRetriever（时政检索）
                              ↓
                        [阶段一] ReferenceComposer（去重+清理）
                              ↓
                        GeneratorAgent（答案生成）
                              ↓
                        ValidatorAgent（答案验证）
                              ↓
                        [阶段二] 高亮识别（后台异步）
                              ↓
                        用户收到回答 + 引用文献
```

### PPT 生成架构

```
用户需求描述
    ↓
大纲生成器（AI生成灵活章节标题）
    ↓
HTML 幻灯片生成（AI + 主题系统）
    ↓
Playwright 截图
    ↓
python-pptx 组装
    ↓
用户下载 PPT
```

### 红芯理辩架构

```
用户输入辩题
    ↓
正方立论（基于马克思主义哲学原理）
    ↓
反方反驳（辩证分析，指出逻辑漏洞）
    ↓
（多轮交锋）
    ↓
裁判总结（综合评议 + 哲学启示）
    ↓
用户获得：辩论记录 + 思维训练 + 原理理解
```

**理辩特点**：
- **角色设定**：红芯正方（坚定清晰）、红芯反方（犀利辩证）、红芯裁判（中立剖析）
- **哲学深度**：辩论内容融入马克思主义哲学原理（实践论、矛盾论、唯物史观等）
- **教育目标**：通过"真理越辩越明"帮助用户理解哲学方法论
- **交互体验**：流式输出，实时显示交锋过程

### 核心组件

| 组件 | 功能 |
|------|------|
| **RouterAgent** | 分析用户意图，确定检索策略 |
| **MemoryAgent** | 检索对话历史，维护上下文 |
| **TheoryRetriever** | 从理论库检索相关知识点 |
| **PoliticsRetriever** | 从时政库检索最新案例 |
| **GeneratorAgent** | 生成完整、准确的回答 |
| **ValidatorAgent** | 验证回答质量，确保准确性 |
| **ReferenceComposer** | 去重、清理、高亮引用文献 |
| **OutlineGenerator** | PPT 大纲生成 |
| **HTMLGenerator** | HTML 幻灯片生成 |
| **HTMLtoPPT** | HTML 转 PPT |
| **DebateService** | 红芯理辩核心服务（正方/反方/裁判） |

## 🚀 快速开始

### 环境要求

- Python 3.8+
- 阿里云 DashScope API Key
- Playwright（用于 PPT 截图）

### 安装依赖

```bash
pip install -r requirements.txt
pip install python-docx  # 用于 docx 下载功能
playwright install chromium  # 用于 PPT 截图
```

### 配置环境变量

创建 `.env` 文件：

```env
DASHSCOPE_API_KEY=your_api_key_here
BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen-turbo
AUDITOR_MODEL=qwen-turbo
FAST_MODEL=qwen-flash
EMBEDDING_MODEL=text-embedding-v4
VECTOR_DIM=1024
QDRANT_PATH=./Qdrant/qdrant_db
```

### 启动服务

```bash
python app.py
```

访问 http://127.0.0.1:6006 即可使用。

## 📁 项目结构

```
ideology-rag/
├── app.py                      # Flask 主应用入口
├── requirements.txt            # Python 依赖
├── .env                        # 环境变量配置
├── src/                        # 核心源代码
│   ├── agents/                # 智能体模块
│   │   ├── router_agent.py
│   │   ├── memory_agent.py
│   │   ├── theory_retriever_agent.py
│   │   ├── politics_retriever_agent.py
│   │   ├── generator_agent.py
│   │   └── validator_agent.py
│   ├── ppt/                   # PPT 生成模块
│   │   ├── outline_generator.py   # 大纲生成器
│   │   ├── html_generator.py      # HTML 幻灯片生成
│   │   ├── html_to_ppt.py         # HTML 转 PPT
│   │   ├── chapter_builders.py    # 章节构建器
│   │   └── themes/                # 主题系统
│   ├── graph.py               # LangGraph 工作流定义
│   ├── service.py             # 对话服务层（流式 SSE）
│   ├── retriever.py           # 检索逻辑
│   ├── reference_composer.py  # 引用文献整合器
│   ├── clients.py             # API 客户端
│   ├── config.py              # 配置管理
│   └── conversation.py        # 对话管理
├── templates/                 # HTML 模板
│   ├── index.html             # 问答页面
│   ├── ppt.html               # PPT 生成页面
│   └── debate.html            # 红芯理辩页面
├── static/                    # 静态资源（JS、CSS）
│   ├── app.js                 # 问答前端逻辑
│   ├── ppt.js                 # PPT 前端逻辑
│   └── debate.js              # 理辩前端逻辑
├── downloads/                 # PPT 下载目录
└── Qdrant/                    # 向量数据库
```

## 💡 使用说明

### 基础对话

1. 在输入框中输入思政教育相关问题（如马克思主义理论、思修、毛概、近代史等）
2. 系统会自动分析意图并检索相关知识
3. 实时查看思考过程和生成的回答
4. 支持多轮对话，系统会记住上下文

### 引用文献功能

1. 回答完成后，自动显示参考资料卡片
2. 点击卡片可查看完整原文和高亮引用处
3. 点击"下载原文"按钮可下载 docx 格式文档
4. 高亮片段会在高亮识别完成后显示

### PPT 生成功能

1. 点击侧边栏"PPT 生成"进入 PPT 页面
2. 输入 PPT 需求描述（如"生成一份关于文化自信的 PPT"）
3. AI 自动生成大纲，可编辑调整
4. 选择主题风格（党建红、科技蓝、简约白等）
5. 生成预览后确认下载

### 红芯理辩功能

1. 点击侧边栏"红芯理辩"进入辩论页面
2. 输入辩题（如"努力一定能改变命运吗"）或选择热门议题
3. 选择交锋轮次（1-3轮）
4. 观看红芯正方与红芯反方的哲学交锋
5. 阅读红芯裁判的总结评议和哲学启示

**理辩价值**：
- 通过正反交锋理解辩证思维方法
- 学习马克思主义哲学原理的实际应用
- 训练批判性思维和逻辑分析能力

### 对话管理

- 对话会自动保存，可在侧边栏查看历史记录
- 支持删除历史对话
- 自动生成对话标题

## 🎨 PPT 主题风格

| 主题 | 主色调 | 适用场景 |
|------|--------|----------|
| 党建红 | 红色 + 金色 | 党政、思政教育 |
| 科技蓝 | 蓝色 + 青色 | 科技、创新主题 |
| 简约白 | 白色 + 灰色 | 通用、学术报告 |
| 学术绿 | 绿色 + 浅绿 | 教育、环保主题 |
| 典雅紫 | 紫色 + 浅紫 | 文化、艺术主题 |
| 活力橙 | 橙色 + 黄色 | 活动、宣传主题 |

## ⚡ 性能优化

### 优化措施

| 优化项 | 改动 | 效果 |
|------|------|------|
| API 并发 | Semaphore 3 → 8 | 充分利用百炼高并发 |
| 生成模型 | qwen3-max → qwen-turbo | 延迟 -50% |
| 验证模型 | qwen-flash → qwen-turbo | 延迟 -40% |
| 高亮识别 | 同步 → 后台异步 | 不阻塞主流程 |
| 引用清理 | 单次 AI 调用 | 并发处理 N 条引用 |

### 性能指标

- **总耗时**：15s → 5-6s ⬇️ 65%
- **首字延迟**：2s → 0.5s ⬇️ 75%
- **引用加载**：8s → 2-3s ⬇️ 70%
- **下载速度**：8-10s → 1-2s ⬇️ 80%

## 🔧 技术栈

- **后端**: Flask, Python 3.13
- **AI 框架**: LangGraph, LangChain
- **向量数据库**: Qdrant
- **大模型**: 阿里云 DashScope (通义千问 turbo/flash)
- **文档生成**: python-docx
- **PPT 生成**: Playwright, python-pptx
- **前端**: HTML, JavaScript, Tailwind CSS

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！
