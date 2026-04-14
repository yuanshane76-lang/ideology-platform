# 红芯理辩 - 辩论功能技术设计文档

## 1. 系统概述

红芯理辩是「红芯平台」的辩论训练模块，核心目标是让大学生在正反交锋中理解马克思主义哲学原理，实现"真理越辩越明"。

系统基于 **RAG（检索增强生成）+ 辩题立场分析 + 马哲立场检测 + 逐步交互** 的架构，用户手动控制辩论进程，AI 双方自动交锋，最终由裁判进行权威总结。

## 2. 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                        前端层 (HTML/JS)                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │  辩题输入   │  │  立场分析   │  │  辩论控制   │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      API层 (Flask)                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │ /topics     │  │  /stream    │  │  /analyze   │          │
│  │  辩题列表   │  │  流式辩论   │  │  辩题分析   │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      服务层 (Service)                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │ TopicAgent  │  │DebateService│  │PromptManager│          │
│  │ 辩题分析    │  │ 辩论编排    │  │ 提示词管理  │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      检索层 (RAG)                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │ 向量检索    │  │ 命题检索    │  │ 多路召回    │          │
│  │  Qdrant     │  │ Propositions│  │  4 Paths    │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
└─────────────────────────────────────────────────────────────┘
```

## 3. 向量数据库结构（实际）

### 3.1 集合概览

| 集合名 | 记录数 | 向量维度 | 距离度量 | 用途 |
|--------|--------|----------|----------|------|
| `debate_chunks` | 553 | 1024 | Cosine | 辩论文档块检索 |
| `debate_propositions` | 1622 | 1024 | Cosine | 辩论命题检索 |
| `moment` | 621 | 1024 | Cosine | 时政新闻检索 |
| `theory` | 2600 | 1024 | Cosine | 理论文献检索 |

### 3.2 debate_chunks（辩论文档块）

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `chunk_id` | str | 唯一标识 | "关于费尔巴哈的提纲-chunk-0001" |
| `source_title` | str | 来源标题 | "关于费尔巴哈的提纲" |
| `source_type` | str | 来源类型 | "book" |
| `author` | str | 作者 | "马克思" |
| `chapter` | str | 章节 | "关于费尔巴哈的提纲" |
| `theory_modules` | list | 理论模块 | ["实践观", "唯物史观", "认识论"] |
| `keywords` | list | 关键词 | ["实践", "社会生活", "唯物主义"] |
| `text` | str | 文本内容 | "全部社会生活在本质上是实践的..." |
| `char_count` | int | 字符数 | 257 |

### 3.3 debate_propositions（辩论命题）⭐核心集合

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `prop_id` | str | 命题ID | "关于费尔巴哈的提纲-prop-0001-1" |
| `source_title` | str | 来源标题 | "关于费尔巴哈的提纲" |
| `source_type` | str | 来源类型 | "book" |
| `author` | str | 作者 | "马克思" |
| `chapter` | str | 章节 | "关于费尔巴哈的提纲" |
| `proposition` | str | 命题陈述 | "实践是检验真理的唯一标准..." |
| `source_text` | str | 原文引用 | "人的思维是否具有客观的..." |
| `theory_module` | str | 理论模块 | "认识论" |
| `applicable_scenarios` | list | 适用场景 | ["科学理论的验证", "社会改革方案的可行性评估"] |
| `common_misuse` | list | 常见误用 | ["将理论争论视为纯粹逻辑推演..."] |
| `support_angle` | str | **支持角度** | "支持实践作为真理标准的观点..." |
| `refute_angle` | str | **反驳角度** | "反驳脱离实践的纯思辨哲学..." |

### 3.4 moment（时政新闻）

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `title` | str | 标题 | "习近平同科特迪瓦总统瓦塔拉通电话" |
| `date` | str | 日期 | "2022-12-20" |
| `source` | str | 来源 | "新华网" |
| `type` | str | 类型 | "其他" |
| `content` | str | 内容 | "国家主席习近平20日下午应约..." |
| `key_words` | list | 关键词 | ["中科建交", "一个中国原则"] |

### 3.5 theory（理论文献）

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `Chapter` | str | 章节 | "导论" |
| `Section` | str | 节 | null |
| `Subsection` | str | 小节 | "一、什么是马克思主义" |
| `Subsubsection` | str | 更小节 | null |
| `Content` | str | 原始内容 | "只有正确理解马克思主义..." |
| `Keywords` | list | 关键词 | ["马克思主义", "科学理论体系"] |
| `source` | str | 来源 | "马克思主义原理" |
| `content_chunk` | str | 内容块 | "只有正确理解马克思主义..." |
| `chunk_index` | int | 块索引 | 0 |
| `chunk_id` | str | 块ID | "0_0" |
| `token_count` | int | token数 | 582 |
| `original_id` | int | 原始ID | 0 |

## 4. 核心数据模型

### 4.1 TopicAnalysis（辩题分析结果）

| 字段 | 类型 | 说明 |
|------|------|------|
| `topic` | str | 辩题原文 |
| `pro_position` | str | 正方核心立场 |
| `con_position` | str | 反方核心立场 |
| `marxism_side` | str | 马克思主义支持哪方（正方/反方） |
| `marxism_reason` | str | 马哲支持理由 |
| `core_concepts` | list | 核心概念列表 |
| `debate_focus` | str | 核心争议点 |
| `involves_marxism_stance` | bool | 是否涉及马哲核心立场 |
| `stance_type` | enum | 立场类型（neutral/aligned_pro/aligned_con） |
| `theory_modules` | list | 相关理论模块（映射到debate_propositions.theory_module） |

### 4.2 DebateSession（辩论会话）

| 字段 | 类型 | 说明 |
|------|------|------|
| `session_id` | str | 会话唯一标识 |
| `topic_analysis` | TopicAnalysis | 辩题分析结果 |
| `current_round` | int | 当前轮次 |
| `max_rounds` | int | 最大轮次（默认3） |
| `protagonist_messages` | list | 正方发言历史 |
| `antagonist_messages` | list | 反方发言历史 |
| `judge_summary` | str | 裁判总结 |
| `status` | str | 会话状态（initialized/debating/completed） |

### 4.3 StanceType（立场类型枚举）

| 值 | 说明 | 正方提示词 | 反方提示词 |
|---|------|-----------|-----------|
| `neutral` | 中性辩题 | 可引用马哲 | 可引用马哲 |
| `aligned_pro` | 马哲支持正方 | 积极引用马哲 | 禁止引用马哲 |
| `aligned_con` | 马哲支持反方 | 禁止引用马哲 | 积极引用马哲 |

### 4.4 DebateTopic（辩题定义）

| 字段 | 类型 | 说明 |
|------|------|------|
| `title` | str | 辩题标题 |
| `description` | str | 辩题描述 |
| `difficulty` | str | 难度等级（基础级/进阶级） |
| `tags` | list | 标签列表 |

## 5. 核心模块设计

### 5.1 TopicAnalysisAgent（辩题分析Agent）

**职责**：分析辩题，确定正反方立场，判断马哲立场

**提示词设计**：
- 输入：辩题文本
- 输出：JSON格式的分析结果
- 判断标准：
  - 涉及马哲核心概念（阶级斗争、唯物史观、剩余价值等）→ `involves_marxism_stance=True`
  - 中性话题（短视频、AI等）→ `involves_marxism_stance=False`

**理论模块映射**：
```python
THEORY_MODULE_MAPPING = {
    "实践观": ["实践", "认识", "真理"],
    "唯物史观": ["社会存在", "社会意识", "生产力", "生产关系"],
    "认识论": ["认识", "真理", "实践检验"],
    "辩证法": ["矛盾", "质量互变", "否定之否定"],
    "剩余价值": ["劳动", "资本", "剥削"],
}
```

### 5.2 PromptManager（提示词管理器）

**职责**：根据立场类型提供对应的提示词模板

**提示词策略**：

| 场景 | 正方提示词 | 反方提示词 |
|------|-----------|-----------|
| 中性辩题 | 可引用马哲理论 | 可引用马哲理论 |
| 马哲支持正方 | 强调马哲支持，积极引用 | 警告禁止引用马哲 |
| 马哲支持反方 | 警告禁止引用马哲 | 强调马哲支持，积极引用 |

**实际提示词模板**（来自现有实现）：

```python
PROTAGONIST_PROMPT = """你是红芯理辩的正方辩手。
【目标】你的核心任务是：在交锋中把道理讲清楚，让"真理越辩越明"。
【辩题】{topic}
【表达要求】
1. 先亮明本轮结论，再展开论证。
2. 尽量使用"概念解释 -> 现实例子 -> 推理结论"的结构。
3. 必须回应反方上一轮最强的一条质疑，不回避关键问题。
4. 反驳时要明确指出对方漏洞（如偷换概念、以偏概全、因果倒置、证据不足）。
5. 语言要让大学生易懂，少堆术语，不空喊口号。
【风格】坚定、清晰、克制、有逻辑。
【长度】280-420字。
"""

ANTAGONIST_PROMPT = """你是红芯理辩的反方辩手。
【目标】你的核心任务是：精准质疑正方论证中的漏洞，逼近问题本质，推动"真理越辩越明"。
【辩题】{topic}
【表达要求】
1. 先准确复述正方关键观点，再开始反驳，避免答非所问。
2. 优先攻击逻辑漏洞：定义不清、逻辑跳步、以偏概全、因果不成立、举例不能推出结论。
3. 每次反驳后给出替代解释，不能只说"你错了"。
4. 使用短句和追问句增强交锋感，但禁止人身攻击。
5. 结尾抛出一个正方尚未回答的关键问题。
【风格】犀利、紧凑、讲证据、讲推理。
【长度】240-380字。
"""

JUDGE_PROMPT = """你是红芯理辩的裁判。
【目标】不是简单站队，而是把争议讲透，让用户清楚看到：为什么"真理越辩越明"。
【辩题】{topic}
【输出结构】
1. 争议焦点（不超过3点）
2. 双方最强攻防点评（各1-2条）
3. 漏洞判定（谁在哪些点上更完整，为什么）
4. 结论与引导（给出更清楚的正确理解）
5. 给大学生的1条实践建议
【要求】
- 必须引用双方辩论中的具体论点进行评议。
- 不能泛泛总结，必须指出"关键句哪里成立/不成立"。
- 语言简明，避免空泛套话。
【长度】420-700字。
"""
```

### 5.3 DebateRetriever（RAG检索器）⭐核心模块

**职责**：根据辩题和立场检索相关参考资料

**关键理解：support_angle 与 refute_angle**

| 字段 | 含义 | 使用场景 |
|------|------|---------|
| `support_angle` | **支持该命题**的论点 | 当命题与己方立场一致时使用 |
| `refute_angle` | **反驳该命题**的论点 | 当命题与己方立场相悖时使用 |

**检索策略**（基于实际数据结构）：

```
┌─────────────────────────────────────────────────────────────┐
│                    检索策略决策树                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  输入：辩题 + 立场类型 + 当前角色                            │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 立场判断：是否允许引用马哲？                          │   │
│  └─────────────────────────────────────────────────────┘   │
│                         │                                   │
│         ┌───────────────┴───────────────┐                  │
│         ▼                               ▼                  │
│  【允许引用】                       【禁止引用】             │
│  执行多路召回                       返回空结果              │
│         │                                                   │
│         ▼                                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 路径1: debate_propositions 命题检索                  │   │
│  │   - 按theory_module过滤                              │   │
│  │   - 判断命题与己方立场的关系：                        │   │
│  │     · 命题支持己方 → 返回 support_angle              │   │
│  │     · 命题反对己方 → 返回 refute_angle               │   │
│  └─────────────────────────────────────────────────────┘   │
│         │                                                   │
│         ▼                                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 路径2: debate_chunks 文档块检索                      │   │
│  │   - 按theory_modules过滤                             │   │
│  │   - 返回text + source_title + author                 │   │
│  └─────────────────────────────────────────────────────┘   │
│         │                                                   │
│         ▼                                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 路径3: theory 理论文献检索                           │   │
│  │   - 按Keywords过滤                                   │   │
│  │   - 返回Content + Chapter + Subsection               │   │
│  └─────────────────────────────────────────────────────┘   │
│         │                                                   │
│         ▼                                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 路径4: moment 时政新闻检索                           │   │
│  │   - 按key_words过滤                                  │   │
│  │   - 返回content + title + date                       │   │
│  └─────────────────────────────────────────────────────┘   │
│         │                                                   │
│         ▼                                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 结果合并与去重                                        │   │
│  │   - 按相关度排序                                      │   │
│  │   - 返回top-k结果                                     │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**角度选择示例**：

```
辩题："个人努力能否改变命运"（马哲支持反方：社会条件决定命运）

正方立场：个人努力是改变命运的关键
反方立场：社会条件决定命运，努力作用有限

检索到的命题："社会存在决定社会意识"
├── 该命题支持反方立场
│
├── 正方使用时 → 命题与己方立场相悖 → 使用 refute_angle
│   └── "反驳：社会存在决定意识不否定主观能动性..."
│
└── 反方使用时 → 命题与己方立场一致 → 使用 support_angle
    └── "支持：经济基础决定上层建筑，社会条件是根本..."

检索到的命题："实践是检验真理的唯一标准"
├── 该命题为中性，双方都可用
│
├── 正方使用时 → 可用于支持努力实践的观点 → support_angle
│
└── 反方使用时 → 可用于反驳脱离实际的空想 → support_angle
```

**核心方法**：

```python
def retrieve_for_debate(
    self,
    topic: str,
    stance_type: StanceType,
    role: str,
    my_position: str,
    theory_modules: List[str] = None,
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """
    根据辩题和立场检索相关参考资料
    
    Args:
        topic: 辩题文本
        stance_type: 立场类型
        role: 当前角色（protagonist/antagonist）
        my_position: 己方立场描述
        theory_modules: 相关理论模块
        top_k: 返回结果数量
    
    Returns:
        检索结果列表，包含：
        - proposition: 命题陈述
        - angle: 支持或反驳角度
        - angle_type: 角度类型（support/refute）
        - source: 来源信息
        - score: 相关度分数
    """
    if self._should_block_retrieval(stance_type, role):
        return []
    
    results = []
    
    results.extend(self._retrieve_propositions(topic, my_position, theory_modules, top_k=2))
    
    results.extend(self._retrieve_chunks(topic, theory_modules, top_k=2))
    
    results.extend(self._retrieve_theory(topic, top_k=1))
    
    return self._deduplicate_and_rank(results, top_k)

def _retrieve_propositions(
    self,
    topic: str,
    my_position: str,
    theory_modules: List[str],
    top_k: int
) -> List[Dict[str, Any]]:
    """
    从debate_propositions检索命题
    
    关键：根据命题与己方立场的关系选择角度
    - 命题支持己方立场 → 使用 support_angle
    - 命题反对己方立场 → 使用 refute_angle
    """
    query_vector = get_embedding(topic)
    
    must_conditions = []
    if theory_modules:
        must_conditions.append(
            FieldCondition(key="theory_module", match=MatchAny(any=theory_modules))
        )
    
    results = self.client.search(
        collection_name="debate_propositions",
        query_vector=query_vector,
        query_filter=Filter(must=must_conditions) if must_conditions else None,
        limit=top_k
    )
    
    formatted = []
    for result in results:
        payload = result.payload
        proposition = payload.get("proposition")
        
        angle_type = self._determine_angle_type(proposition, my_position)
        angle_key = "support_angle" if angle_type == "support" else "refute_angle"
        
        formatted.append({
            "type": "proposition",
            "proposition": proposition,
            "angle": payload.get(angle_key),
            "angle_type": angle_type,
            "source": f"{payload.get('author')}《{payload.get('source_title')}》",
            "theory_module": payload.get("theory_module"),
            "score": result.score
        })
    
    return formatted

def _determine_angle_type(self, proposition: str, my_position: str) -> str:
    """
    判断命题与己方立场的关系，决定使用哪个角度
    
    Returns:
        "support": 命题支持己方立场，使用 support_angle
        "refute": 命题反对己方立场，使用 refute_angle
    """
    prompt = f"""判断以下命题与立场的关系：
    
命题：{proposition}
己方立场：{my_position}

请判断该命题是"支持"还是"反对"己方立场。
只回答"支持"或"反对"。
"""
    response = self.llm.call(prompt)
    return "support" if "支持" in response else "refute"
```

### 5.4 DebateService（辩论服务）

**职责**：协调各模块，管理辩论流程

**核心方法**：

| 方法 | 说明 |
|------|------|
| `stream_debate_events(topic, description, rounds)` | 流式执行完整辩论流程 |
| `_build_protagonist_user_prompt(round, description, last_antagonist)` | 构建正方提示词 |
| `_build_antagonist_user_prompt(round, description, protagonist_message)` | 构建反方提示词 |
| `_stream_completion(system_prompt, user_prompt)` | 流式LLM生成 |

**轮次策略**（现有实现）：

| 轮次 | 正方任务 | 反方任务 |
|------|---------|---------|
| 第1轮 | 定义关键概念，完整立论，预判反驳 | 优先攻击定义和前提 |
| 第2轮 | 逐点回应质疑，补齐论证链 | 继续深挖，检验证据和推理 |
| 第3轮 | 收束争点，给出最终判断 | 最终反压，指出核心缺口 |

## 6. API接口设计

### 6.1 获取辩题列表

```http
GET /api/debate/topics
```

**响应**：
```json
[
    {
        "title": "努力就一定能改变命运吗？",
        "description": "讨论个人奋斗与社会条件的关系",
        "difficulty": "基础级",
        "tags": ["奋斗", "成长", "公平"]
    }
]
```

### 6.2 获取反方类型

```http
GET /api/debate/antagonist-types
```

**响应**：
```json
[
    {
        "type": "反方",
        "representative": "观点挑战者",
        "description": "专注抓取论证漏洞，推动观点澄清",
        "avatar": "🔵"
    }
]
```

### 6.3 辩题分析

```http
POST /api/debate/analyze
Content-Type: application/json

{
    "topic": "个人努力能否改变命运",
    "description": "讨论个人奋斗与社会条件的关系"
}
```

**响应**：
```json
{
    "session_id": "abc123",
    "topic_analysis": {
        "topic": "个人努力能否改变命运",
        "pro_position": "个人努力是改变命运的关键",
        "con_position": "社会条件决定命运，努力作用有限",
        "marxism_side": "反方",
        "marxism_reason": "马克思主义认为社会存在决定社会意识，经济基础决定上层建筑",
        "core_concepts": ["个人奋斗", "社会结构", "唯物史观"],
        "debate_focus": "个人努力与社会条件的辩证关系",
        "involves_marxism_stance": true,
        "stance_type": "aligned_con",
        "theory_modules": ["唯物史观", "实践观"]
    }
}
```

### 6.4 流式辩论（核心接口）

```http
POST /api/debate/stream
Content-Type: application/json

{
    "title": "努力就一定能改变命运吗？",
    "description": "讨论个人奋斗与社会条件的关系",
    "antagonist_type": "反方",
    "rounds": 3
}
```

**响应**（SSE流式）：
```
event: message
data: {"type": "start", "topic": "...", "antagonist_type": "反方"}

event: message
data: {"type": "round_start", "round": 1}

event: message
data: {"type": "protagonist_start", "round": 1}

event: message
data: {"type": "protagonist_chunk", "round": 1, "content": "正方观点：..."}

event: message
data: {"type": "protagonist_end", "round": 1}

event: message
data: {"type": "antagonist_start", "round": 1}

event: message
data: {"type": "antagonist_chunk", "round": 1, "content": "反方观点：..."}

event: message
data: {"type": "antagonist_end", "round": 1}

event: message
data: {"type": "judge_start"}

event: message
data: {"type": "judge_chunk", "content": "裁判总结：..."}

event: message
data: {"type": "judge_end"}

event: message
data: {"type": "complete", "session": {...}}
```

## 7. 前端交互设计

### 7.1 页面结构

```
┌──────────────────────────────────────────────────────┐
│  红芯理辩 - 马克思主义哲学辩论训练                   │
├──────────────────────────────────────────────────────┤
│  [预设辩题选择] / [自定义辩题输入]                    │
├──────────────────────────────────────────────────────┤
│  [辩题分析结果卡片]                                  │
│  - 正方立场：xxx                                    │
│  - 反方立场：xxx                                    │
│  - 马哲支持：xxx                                    │
│  - 相关理论模块：[唯物史观, 实践观]                  │
├──────────────────────────────────────────────────────┤
│  [辩论区域]                                         │
│  ┌──────────────────────────────────────────────┐   │
│  │ 🔴 正方 · 第1轮                              │   │
│  │ 发言内容...                                  │   │
│  │ [引用来源] 马克思《关于费尔巴哈的提纲》       │   │
│  └──────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────┐   │
│  │ 🔵 反方 · 第1轮                              │   │
│  │ 发言内容...                                  │   │
│  └──────────────────────────────────────────────┘   │
├──────────────────────────────────────────────────────┤
│  [控制按钮]                                         │
│  [开始辩论] [结束辩论] [重新开始]                   │
└──────────────────────────────────────────────────────┘
```

### 7.2 交互流程

```
1. 用户选择/输入辩题 → 点击"开始辩论"
2. 系统自动执行完整辩论流程（流式输出）
3. 依次显示：正方发言 → 反方发言 → 下一轮...
4. 辩论结束后显示裁判总结
5. 用户可选择"重新开始"或切换辩题
```

### 7.3 状态管理

```javascript
let session = {
    session_id: null,
    topic: null,
    description: null,
    current_round: 0,
    max_rounds: 3,
    protagonist_messages: [],
    antagonist_messages: [],
    judge_summary: null,
    status: "idle",  // idle/debating/completed
    isStreaming: false
};
```

## 8. 文件结构

```
src/debate/
├── __init__.py           # 模块导出
├── constants.py          # 常量定义（DebateTopic, SAMPLE_TOPICS）
└── service.py            # 辩论服务（提示词、流式生成）

src/
├── debate_retriever.py   # RAG检索器（多路召回）
├── config.py             # 配置管理
└── ...
```

**实际文件映射**：

| 设计模块 | 实际文件 | 状态 |
|---------|---------|------|
| DebateRetriever | `src/debate_retriever.py` | ✅ 已实现（需增强） |
| PromptManager + DebateService | `src/debate/service.py` | ✅ 已实现 |
| TopicAnalysisAgent | 待实现 | ⏳ 待开发 |
| 配置管理 | `src/config.py` | ✅ 已实现 |
| API接口 | `app.py` | ✅ 已实现 |

## 9. 环境配置

```yaml
# .env 文件
DASHSCOPE_API_KEY=xxx
QDRANT_PATH=./Qdrant/qdrant_db
DEBATE_ROUNDS=3
DEBATE_TEMPERATURE=0.7
DEBATE_MAX_TOKENS=1000
EMBEDDING_MODEL=text-embedding-v4
VECTOR_DIM=1024
```

## 10. 安全与合规

### 10.1 内容审核

- 辩题内容敏感词检测
- 辩论内容合规性检查
- 禁止恶意引导和不当言论

### 10.2 马哲立场正确性

- 确保马哲支持方判断准确
- 禁止反马哲立场引用马哲理论
- 裁判总结需符合马哲基本原理

### 10.3 数据保护

- 用户对话数据加密存储
- 敏感信息脱敏处理
- 会话数据定期清理

## 11. 部署与运维

### 11.1 依赖要求

| 依赖 | 版本 |
|------|------|
| Python | ≥ 3.10 |
| Flask | ≥ 2.0 |
| qdrant-client | ≥ 1.0 |
| dashscope | ≥ 1.0 |
| openai | ≥ 1.0 |

### 11.2 启动方式

```bash
cd ideology-platform
python app.py
```

### 11.3 服务端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/debate` | GET | 辩论页面 |
| `/api/debate/topics` | GET | 获取辩题列表 |
| `/api/debate/antagonist-types` | GET | 获取反方类型 |
| `/api/debate/stream` | POST | 流式辩论 |
| `/api/debate/analyze` | POST | 辩题分析（待实现） |

---

**文档版本**：v2.0  
**创建时间**：2026-04-13  
**适用项目**：ideology-platform  
**更新说明**：基于实际Qdrant数据结构重新设计，重点增强debate_propositions的support_angle/refute_angle应用