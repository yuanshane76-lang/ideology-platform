# 红芯理辩功能增强 - 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 增强辩论功能，实现辩题分析、智能角度选择、引用来源展示等核心功能

**Architecture:** 基于 RAG + LLM 的辩论系统，核心流程：辩题分析 → 立场判断 → RAG检索（角度选择）→ 流式辩论 → 裁判总结

**Tech Stack:** Python 3.10+, Flask, Qdrant, DashScope, OpenAI SDK

---

## 文件结构

```
src/debate/
├── __init__.py           # 模块导出（修改）
├── constants.py          # 常量定义（现有）
├── service.py            # 辩论服务（修改：集成RAG）
├── models.py             # 数据模型（新建）
└── topic_agent.py        # 辩题分析Agent（新建）

src/
├── debate_retriever.py   # RAG检索器（修改：增强角度选择）
├── config.py             # 配置管理（现有）
└── ...

app.py                    # API接口（修改：添加/analyze接口）

tests/
├── test_topic_agent.py   # 辩题分析测试（新建）
├── test_debate_retriever.py  # 检索器测试（新建）
└── test_debate_service.py    # 服务测试（新建）
```

---

## Task 1: 创建数据模型

**Files:**
- Create: `src/debate/models.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: 创建测试文件**

```python
# tests/test_models.py
from src.debate.models import TopicAnalysis, DebateSession, StanceType

def test_stance_type_enum():
    assert StanceType.NEUTRAL == "neutral"
    assert StanceType.ALIGNED_PRO == "aligned_pro"
    assert StanceType.ALIGNED_CON == "aligned_con"

def test_topic_analysis_creation():
    analysis = TopicAnalysis(
        topic="个人努力能否改变命运",
        pro_position="个人努力是改变命运的关键",
        con_position="社会条件决定命运，努力作用有限",
        marxism_side="反方",
        marxism_reason="马克思主义认为社会存在决定社会意识",
        core_concepts=["个人奋斗", "社会结构", "唯物史观"],
        debate_focus="个人努力与社会条件的辩证关系",
        involves_marxism_stance=True,
        stance_type=StanceType.ALIGNED_CON,
        theory_modules=["唯物史观", "实践观"]
    )
    assert analysis.topic == "个人努力能否改变命运"
    assert analysis.stance_type == StanceType.ALIGNED_CON

def test_debate_session_creation():
    session = DebateSession(
        session_id="test-123",
        topic_analysis=None,
        current_round=0,
        max_rounds=3,
        protagonist_messages=[],
        antagonist_messages=[],
        judge_summary=None,
        status="initialized"
    )
    assert session.session_id == "test-123"
    assert session.max_rounds == 3
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd d:\Desktop\大四学习资料\workspace\ideology-platform && python -m pytest tests/test_models.py -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: 创建数据模型文件**

```python
# src/debate/models.py
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


class StanceType(str, Enum):
    NEUTRAL = "neutral"
    ALIGNED_PRO = "aligned_pro"
    ALIGNED_CON = "aligned_con"


@dataclass
class TopicAnalysis:
    topic: str
    pro_position: str
    con_position: str
    marxism_side: str
    marxism_reason: str
    core_concepts: List[str]
    debate_focus: str
    involves_marxism_stance: bool
    stance_type: StanceType
    theory_modules: List[str] = field(default_factory=list)


@dataclass
class DebateSession:
    session_id: str
    topic_analysis: Optional[TopicAnalysis]
    current_round: int = 0
    max_rounds: int = 3
    protagonist_messages: List[str] = field(default_factory=list)
    antagonist_messages: List[str] = field(default_factory=list)
    judge_summary: Optional[str] = None
    status: str = "initialized"
```

- [ ] **Step 4: 更新模块导出**

```python
# src/debate/__init__.py
from .constants import SAMPLE_TOPICS, ANTAGONIST_TYPES, DebateTopic
from .service import stream_debate_events
from .models import TopicAnalysis, DebateSession, StanceType

__all__ = [
    "SAMPLE_TOPICS",
    "ANTAGONIST_TYPES", 
    "DebateTopic",
    "stream_debate_events",
    "TopicAnalysis",
    "DebateSession",
    "StanceType",
]
```

- [ ] **Step 5: 运行测试确认通过**

Run: `cd d:\Desktop\大四学习资料\workspace\ideology-platform && python -m pytest tests/test_models.py -v`
Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add src/debate/models.py src/debate/__init__.py tests/test_models.py
git commit -m "feat(debate): add data models for TopicAnalysis and DebateSession"
```

---

## Task 2: 实现辩题分析Agent

**Files:**
- Create: `src/debate/topic_agent.py`
- Test: `tests/test_topic_agent.py`

- [ ] **Step 1: 创建测试文件**

```python
# tests/test_topic_agent.py
import pytest
from src.debate.topic_agent import TopicAnalysisAgent
from src.debate.models import StanceType

@pytest.fixture
def agent():
    return TopicAnalysisAgent()

def test_analyze_neutral_topic(agent):
    result = agent.analyze("短视频让大学生更容易学习，还是更难深度思考？")
    assert result.involves_marxism_stance == False
    assert result.stance_type == StanceType.NEUTRAL

def test_analyze_marxism_aligned_topic(agent):
    result = agent.analyze("个人努力能否改变命运？")
    assert result.involves_marxism_stance == True
    assert result.stance_type in [StanceType.ALIGNED_PRO, StanceType.ALIGNED_CON]

def test_analyze_returns_theory_modules(agent):
    result = agent.analyze("实践是检验真理的唯一标准吗？")
    assert len(result.theory_modules) > 0
    assert "认识论" in result.theory_modules or "实践观" in result.theory_modules
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd d:\Desktop\大四学习资料\workspace\ideology-platform && python -m pytest tests/test_topic_agent.py -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: 创建TopicAnalysisAgent**

```python
# src/debate/topic_agent.py
import json
from typing import Dict, Any
from dashscope import Generation
from .models import TopicAnalysis, StanceType
from ..config import settings


THEORY_MODULE_MAPPING = {
    "实践观": ["实践", "认识", "真理", "检验"],
    "唯物史观": ["社会存在", "社会意识", "生产力", "生产关系", "社会条件"],
    "认识论": ["认识", "真理", "实践检验", "客观"],
    "辩证法": ["矛盾", "质量互变", "否定之否定", "对立统一"],
    "剩余价值": ["劳动", "资本", "剥削", "价值"],
}


class TopicAnalysisAgent:
    def __init__(self):
        self.api_key = settings.api_key
        self.model = settings.llm_model
    
    def analyze(self, topic: str, description: str = "") -> TopicAnalysis:
        prompt = self._build_prompt(topic, description)
        response = self._call_llm(prompt)
        result = self._parse_response(response, topic)
        return result
    
    def _build_prompt(self, topic: str, description: str) -> str:
        return f"""你是一个马克思主义哲学专家，请分析以下辩题：

辩题：{topic}
描述：{description or '无'}

请以JSON格式输出分析结果，包含以下字段：
1. pro_position: 正方核心立场（一句话）
2. con_position: 反方核心立场（一句话）
3. marxism_side: 马克思主义支持哪方（"正方"/"反方"/"中立"）
4. marxism_reason: 马哲支持理由（一句话）
5. core_concepts: 核心概念列表（3-5个关键词）
6. debate_focus: 核心争议点（一句话）
7. involves_marxism_stance: 是否涉及马哲核心立场（true/false）
8. stance_type: 立场类型（"neutral"/"aligned_pro"/"aligned_con"）
9. theory_modules: 相关理论模块（从以下选择：实践观、唯物史观、认识论、辩证法、剩余价值）

判断标准：
- 涉及阶级斗争、唯物史观、剩余价值、社会存在决定社会意识等马哲核心概念 → involves_marxism_stance=true
- 中性话题（短视频、AI、就业选择等）→ involves_marxism_stance=false
- 马哲支持正方 → stance_type="aligned_pro"
- 马哲支持反方 → stance_type="aligned_con"  
- 马哲中立 → stance_type="neutral"

只输出JSON，不要其他内容。"""

    def _call_llm(self, prompt: str) -> str:
        response = Generation.call(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            api_key=self.api_key,
            result_format="message",
        )
        if response.status_code != 200:
            raise RuntimeError(f"LLM调用失败: {response.code} - {response.message}")
        return response.output.choices[0].message.content
    
    def _parse_response(self, response: str, topic: str) -> TopicAnalysis:
        try:
            json_str = response.strip()
            if json_str.startswith("```"):
                json_str = json_str.split("```")[1]
                if json_str.startswith("json"):
                    json_str = json_str[4:]
            data = json.loads(json_str)
            
            stance_type = StanceType(data.get("stance_type", "neutral"))
            
            return TopicAnalysis(
                topic=topic,
                pro_position=data.get("pro_position", ""),
                con_position=data.get("con_position", ""),
                marxism_side=data.get("marxism_side", "中立"),
                marxism_reason=data.get("marxism_reason", ""),
                core_concepts=data.get("core_concepts", []),
                debate_focus=data.get("debate_focus", ""),
                involves_marxism_stance=data.get("involves_marxism_stance", False),
                stance_type=stance_type,
                theory_modules=data.get("theory_modules", [])
            )
        except Exception as e:
            return TopicAnalysis(
                topic=topic,
                pro_position="正方立场",
                con_position="反方立场",
                marxism_side="中立",
                marxism_reason="",
                core_concepts=[],
                debate_focus="",
                involves_marxism_stance=False,
                stance_type=StanceType.NEUTRAL,
                theory_modules=[]
            )
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd d:\Desktop\大四学习资料\workspace\ideology-platform && python -m pytest tests/test_topic_agent.py -v`
Expected: PASS

- [ ] **Step 5: 更新模块导出**

```python
# src/debate/__init__.py (追加)
from .topic_agent import TopicAnalysisAgent

__all__.append("TopicAnalysisAgent")
```

- [ ] **Step 6: 提交**

```bash
git add src/debate/topic_agent.py src/debate/__init__.py tests/test_topic_agent.py
git commit -m "feat(debate): add TopicAnalysisAgent for topic analysis"
```

---

## Task 3: 增强DebateRetriever - 角度选择

**Files:**
- Modify: `src/debate_retriever.py`
- Test: `tests/test_debate_retriever.py`

- [ ] **Step 1: 创建测试文件**

```python
# tests/test_debate_retriever.py
import pytest
from src.debate_retriever import DebateRetriever
from src.debate.models import StanceType

@pytest.fixture
def retriever():
    return DebateRetriever()

def test_retrieve_for_debate_returns_empty_when_blocked(retriever):
    results = retriever.retrieve_for_debate(
        topic="个人努力能否改变命运",
        stance_type=StanceType.ALIGNED_CON,
        role="protagonist",
        my_position="个人努力是改变命运的关键"
    )
    assert results == []

def test_retrieve_for_debate_returns_results_when_allowed(retriever):
    results = retriever.retrieve_for_debate(
        topic="个人努力能否改变命运",
        stance_type=StanceType.ALIGNED_CON,
        role="antagonist",
        my_position="社会条件决定命运",
        theory_modules=["唯物史观"],
        top_k=3
    )
    assert len(results) > 0
    assert "angle" in results[0]
    assert "angle_type" in results[0]

def test_determine_angle_type(retriever):
    angle_type = retriever._determine_angle_type(
        proposition="社会存在决定社会意识",
        my_position="个人努力是改变命运的关键"
    )
    assert angle_type in ["support", "refute"]
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd d:\Desktop\大四学习资料\workspace\ideology-platform && python -m pytest tests/test_debate_retriever.py -v`
Expected: FAIL with "AttributeError" or "TypeError"

- [ ] **Step 3: 修改DebateRetriever**

```python
# src/debate_retriever.py (修改现有文件，添加以下方法)

from typing import List, Dict, Any, Optional
from .debate.models import StanceType


class DebateRetriever:
    def __init__(self):
        self.client = qdrant_client
    
    def retrieve_for_debate(
        self,
        topic: str,
        stance_type: StanceType,
        role: str,
        my_position: str,
        theory_modules: Optional[List[str]] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        if self._should_block_retrieval(stance_type, role):
            return []
        
        results = []
        results.extend(self._retrieve_propositions(topic, my_position, theory_modules, top_k=2))
        results.extend(self._retrieve_chunks(topic, theory_modules, top_k=2))
        results.extend(self._retrieve_theory(topic, top_k=1))
        
        return self._deduplicate_and_rank(results, top_k)
    
    def _should_block_retrieval(self, stance_type: StanceType, role: str) -> bool:
        if stance_type == StanceType.NEUTRAL:
            return False
        if stance_type == StanceType.ALIGNED_PRO and role == "antagonist":
            return True
        if stance_type == StanceType.ALIGNED_CON and role == "protagonist":
            return True
        return False
    
    def _retrieve_propositions(
        self,
        topic: str,
        my_position: str,
        theory_modules: Optional[List[str]],
        top_k: int
    ) -> List[Dict[str, Any]]:
        query_vector = get_embedding(topic)
        
        must_conditions = []
        if theory_modules:
            must_conditions.append(
                FieldCondition(key="theory_module", match=MatchAny(any=theory_modules))
            )
        
        results = self.client.search(
            collection_name=COLLECTION_PROPOSITIONS,
            query_vector=query_vector,
            query_filter=Filter(must=must_conditions) if must_conditions else None,
            limit=top_k
        )
        
        formatted = []
        for result in results:
            payload = result.payload or {}
            proposition = payload.get("proposition", "")
            
            angle_type = self._determine_angle_type(proposition, my_position)
            angle_key = "support_angle" if angle_type == "support" else "refute_angle"
            
            formatted.append({
                "type": "proposition",
                "proposition": proposition,
                "angle": payload.get(angle_key, ""),
                "angle_type": angle_type,
                "source": f"{payload.get('author', '')}《{payload.get('source_title', '')}》",
                "theory_module": payload.get("theory_module", ""),
                "score": result.score
            })
        
        return formatted
    
    def _determine_angle_type(self, proposition: str, my_position: str) -> str:
        from dashscope import Generation
        from .config import settings
        
        prompt = f"""判断以下命题与立场的关系：

命题：{proposition}
己方立场：{my_position}

请判断该命题是"支持"还是"反对"己方立场。
只回答"支持"或"反对"，不要其他内容。"""

        try:
            response = Generation.call(
                model=settings.llm_model,
                messages=[{"role": "user", "content": prompt}],
                api_key=settings.api_key,
                result_format="message",
            )
            if response.status_code == 200:
                content = response.output.choices[0].message.content
                return "support" if "支持" in content else "refute"
        except:
            pass
        
        return "support"
    
    def _deduplicate_and_rank(
        self,
        results: List[Dict[str, Any]],
        top_k: int
    ) -> List[Dict[str, Any]]:
        seen = set()
        unique = []
        for r in results:
            key = r.get("proposition", "") or r.get("text", "")[:50]
            if key not in seen:
                seen.add(key)
                unique.append(r)
        
        unique.sort(key=lambda x: x.get("score", 0), reverse=True)
        return unique[:top_k]
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd d:\Desktop\大四学习资料\workspace\ideology-platform && python -m pytest tests/test_debate_retriever.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add src/debate_retriever.py tests/test_debate_retriever.py
git commit -m "feat(debate): enhance DebateRetriever with angle selection logic"
```

---

## Task 4: 集成RAG到辩论服务

**Files:**
- Modify: `src/debate/service.py`
- Test: `tests/test_debate_service.py`

- [ ] **Step 1: 创建测试文件**

```python
# tests/test_debate_service.py
import pytest
from src.debate.service import stream_debate_events

def test_stream_debate_events_yields_events():
    events = list(stream_debate_events(
        topic="短视频让大学生更容易学习，还是更难深度思考？",
        description="讨论碎片化信息与系统化学习之间的张力",
        antagonist_type="反方",
        rounds=1
    ))
    
    event_types = [e.get("type") for e in events]
    assert "start" in event_types
    assert "complete" in event_types

def test_stream_debate_events_includes_references():
    events = list(stream_debate_events(
        topic="实践是检验真理的唯一标准吗？",
        description="",
        antagonist_type="反方",
        rounds=1
    ))
    
    complete_event = next(e for e in events if e.get("type") == "complete")
    assert "session" in complete_event
```

- [ ] **Step 2: 修改辩论服务集成RAG**

```python
# src/debate/service.py (修改现有文件)

from ..debate_retriever import DebateRetriever
from .models import StanceType

retriever = DebateRetriever()


def stream_debate_events(
    topic: str,
    description: str,
    antagonist_type: str,
    rounds: int,
) -> Generator[dict, None, None]:
    protagonist_messages: List[str] = []
    antagonist_messages: List[str] = []
    references = []

    final_rounds = max(1, min(3, rounds))

    yield {"type": "start", "topic": topic, "antagonist_type": "反方"}

    for current_round in range(1, final_rounds + 1):
        yield {"type": "round_start", "round": current_round}

        yield {"type": "protagonist_start", "round": current_round}
        last_antagonist = antagonist_messages[-1] if antagonist_messages else ""
        
        rag_results = retriever.retrieve_for_debate(
            topic=topic,
            stance_type=StanceType.NEUTRAL,
            role="protagonist",
            my_position="支持辩题观点",
            top_k=2
        )
        
        p_user_prompt = _build_protagonist_user_prompt(
            current_round=current_round,
            description=description,
            last_antagonist=last_antagonist,
            references=rag_results
        )

        full_p = ""
        for chunk in _stream_completion(PROTAGONIST_PROMPT.format(topic=topic), p_user_prompt):
            full_p += chunk
            yield {"type": "protagonist_chunk", "round": current_round, "content": chunk}
        protagonist_messages.append(full_p)
        
        if rag_results:
            yield {"type": "protagonist_references", "round": current_round, "references": rag_results[:2]}
        
        yield {"type": "protagonist_end", "round": current_round}

        yield {"type": "antagonist_start", "round": current_round}
        a_user_prompt = _build_antagonist_user_prompt(
            current_round=current_round,
            description=description,
            protagonist_message=full_p,
        )

        full_a = ""
        for chunk in _stream_completion(ANTAGONIST_PROMPT.format(topic=topic), a_user_prompt):
            full_a += chunk
            yield {"type": "antagonist_chunk", "round": current_round, "content": chunk}
        antagonist_messages.append(full_a)
        yield {"type": "antagonist_end", "round": current_round}

    yield {"type": "judge_start"}
    history = []
    for i in range(len(protagonist_messages)):
        history.append(
            f"第{i + 1}轮\n"
            f"正方：{protagonist_messages[i]}\n"
            f"反方：{antagonist_messages[i]}"
        )

    judge_user_prompt = (
        "【完整辩论记录】\n"
        + "\n\n".join(history)
        + "\n\n【任务】请按结构输出裁判结论，重点说明谁在哪些论证点更完整。"
    )

    full_j = ""
    for chunk in _stream_completion(JUDGE_PROMPT.format(topic=topic), judge_user_prompt, max_tokens=1800):
        full_j += chunk
        yield {"type": "judge_chunk", "content": chunk}
    yield {"type": "judge_end"}

    yield {
        "type": "complete",
        "session": {
            "topic": topic,
            "description": description,
            "antagonist_type": "反方",
            "rounds": final_rounds,
            "protagonist_messages": protagonist_messages,
            "antagonist_messages": antagonist_messages,
            "judge_summary": full_j,
            "references": references,
            "status": "completed",
        },
    }


def _build_protagonist_user_prompt(
    current_round: int, 
    description: str, 
    last_antagonist: str,
    references: List[Dict] = None
) -> str:
    base_prompt = ""
    if current_round == 1:
        base_prompt = (
            f"【当前轮次】第 {current_round} 轮（立论）\n"
            f"【辩题说明】{description or '无'}\n"
            "【任务】先定义关键概念，再给出完整立论。"
            "请主动预判可能反驳并提前回应1个风险点。"
        )
    elif current_round == 2:
        base_prompt = (
            f"【当前轮次】第 {current_round} 轮（拆解回应）\n"
            f"【辩题说明】{description or '无'}\n"
            f"【反方上一轮观点】{last_antagonist}\n"
            "【任务】逐点回应反方最强质疑，补齐论证链。"
            "请点名反方至少1个逻辑漏洞并给出反证。"
        )
    else:
        base_prompt = (
            f"【当前轮次】第 {current_round} 轮（收束）\n"
            f"【辩题说明】{description or '无'}\n"
            f"【反方上一轮观点】{last_antagonist}\n"
            "【任务】收束争点，给出最终判断。"
            "请用"核心结论 + 关键理由 + 对反方最终回应"完成本轮。"
        )
    
    if references:
        ref_text = "\n".join([
            f"- {r.get('proposition', r.get('text', ''))[:100]}"
            for r in references[:2]
        ])
        base_prompt += f"\n\n【参考资料】\n{ref_text}"
    
    return base_prompt
```

- [ ] **Step 3: 运行测试确认通过**

Run: `cd d:\Desktop\大四学习资料\workspace\ideology-platform && python -m pytest tests/test_debate_service.py -v`
Expected: PASS

- [ ] **Step 4: 提交**

```bash
git add src/debate/service.py tests/test_debate_service.py
git commit -m "feat(debate): integrate RAG retrieval into debate service"
```

---

## Task 5: 添加辩题分析API接口

**Files:**
- Modify: `app.py`

- [ ] **Step 1: 添加辩题分析接口**

```python
# app.py (添加以下代码)

from src.debate import TopicAnalysisAgent

topic_agent = TopicAnalysisAgent()

@app.route('/api/debate/analyze', methods=['POST'])
def analyze_topic():
    """分析辩题，返回立场分析和理论模块"""
    data = request.json or {}
    topic = (data.get('topic') or '').strip()
    description = (data.get('description') or '').strip()
    
    if not topic:
        return jsonify({"error": "缺少辩题"}), 400
    
    try:
        analysis = topic_agent.analyze(topic, description)
        
        return jsonify({
            "session_id": str(uuid.uuid4()),
            "topic_analysis": {
                "topic": analysis.topic,
                "pro_position": analysis.pro_position,
                "con_position": analysis.con_position,
                "marxism_side": analysis.marxism_side,
                "marxism_reason": analysis.marxism_reason,
                "core_concepts": analysis.core_concepts,
                "debate_focus": analysis.debate_focus,
                "involves_marxism_stance": analysis.involves_marxism_stance,
                "stance_type": analysis.stance_type.value,
                "theory_modules": analysis.theory_modules
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

- [ ] **Step 2: 添加uuid导入**

```python
# app.py (确保导入)
import uuid
```

- [ ] **Step 3: 测试接口**

Run: `cd d:\Desktop\大四学习资料\workspace\ideology-platform && python app.py`
Test: `curl -X POST http://localhost:6006/api/debate/analyze -H "Content-Type: application/json" -d "{\"topic\": \"个人努力能否改变命运\"}"`

- [ ] **Step 4: 提交**

```bash
git add app.py
git commit -m "feat(api): add /api/debate/analyze endpoint"
```

---

## Task 6: 前端增强 - 显示引用来源

**Files:**
- Modify: `static/debate.js`
- Modify: `templates/debate.html`

- [ ] **Step 1: 修改前端处理引用事件**

```javascript
// static/debate.js (修改事件处理)

function handleDebateEvent(event) {
    const data = JSON.parse(event.data);
    
    switch (data.type) {
        case 'protagonist_references':
            displayReferences('protagonist', data.round, data.references);
            break;
        case 'antagonist_references':
            displayReferences('antagonist', data.round, data.references);
            break;
        // ... 其他事件处理
    }
}

function displayReferences(role, round, references) {
    if (!references || references.length === 0) return;
    
    const container = document.getElementById(`${role}-${round}-references`);
    if (!container) return;
    
    const html = references.map(ref => `
        <div class="reference-card">
            <div class="reference-source">${ref.source}</div>
            <div class="reference-content">${ref.proposition || ref.text}</div>
        </div>
    `).join('');
    
    container.innerHTML = `<div class="references-title">📚 参考资料</div>${html}`;
}
```

- [ ] **Step 2: 添加引用样式**

```css
/* static/style.css (添加) */

.reference-card {
    background: #f8f9fa;
    border-left: 3px solid #4a90e2;
    padding: 8px 12px;
    margin: 8px 0;
    border-radius: 4px;
}

.reference-source {
    font-size: 12px;
    color: #666;
    margin-bottom: 4px;
}

.reference-content {
    font-size: 13px;
    color: #333;
}

.references-title {
    font-weight: bold;
    margin-bottom: 8px;
    color: #4a90e2;
}
```

- [ ] **Step 3: 提交**

```bash
git add static/debate.js static/style.css templates/debate.html
git commit -m "feat(frontend): display references in debate messages"
```

---

## Task 7: 集成测试

**Files:**
- Create: `tests/test_integration.py`

- [ ] **Step 1: 创建集成测试**

```python
# tests/test_integration.py
import pytest
from src.debate import TopicAnalysisAgent, stream_debate_events, StanceType
from src.debate_retriever import DebateRetriever


def test_full_debate_flow():
    agent = TopicAnalysisAgent()
    
    analysis = agent.analyze("实践是检验真理的唯一标准吗？")
    assert analysis.stance_type in [StanceType.NEUTRAL, StanceType.ALIGNED_PRO, StanceType.ALIGNED_CON]
    
    retriever = DebateRetriever()
    results = retriever.retrieve_for_debate(
        topic=analysis.topic,
        stance_type=analysis.stance_type,
        role="protagonist",
        my_position=analysis.pro_position,
        theory_modules=analysis.theory_modules,
        top_k=3
    )
    
    events = list(stream_debate_events(
        topic=analysis.topic,
        description="讨论实践与真理的关系",
        antagonist_type="反方",
        rounds=1
    ))
    
    event_types = [e.get("type") for e in events]
    assert "start" in event_types
    assert "complete" in event_types
```

- [ ] **Step 2: 运行集成测试**

Run: `cd d:\Desktop\大四学习资料\workspace\ideology-platform && python -m pytest tests/test_integration.py -v`
Expected: PASS

- [ ] **Step 3: 提交**

```bash
git add tests/test_integration.py
git commit -m "test: add integration test for full debate flow"
```

---

## 验收清单

- [ ] 所有单元测试通过
- [ ] 集成测试通过
- [ ] API接口可正常调用
- [ ] 前端正确显示引用来源
- [ ] 角度选择逻辑正确（正方可用refute_angle，反方可用support_angle）
- [ ] 辩题分析返回正确的理论模块

---

**计划版本**：v1.0  
**创建时间**：2026-04-13  
**预计工期**：2-3天
