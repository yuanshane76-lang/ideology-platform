from typing import Generator, List, Dict, Any, Optional
from dataclasses import dataclass, field
from dashscope import Generation

from ..config import settings
from ..debate_retriever import DebateRetriever


@dataclass
class DebateSession:
    session_id: str
    topic: str
    description: str
    antagonist_type: str = "反方"
    max_rounds: int = 10
    current_round: int = 0
    protagonist_messages: List[str] = field(default_factory=list)
    antagonist_messages: List[str] = field(default_factory=list)
    judge_summary: Optional[str] = None
    status: str = "initialized"
    theory_context: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "topic": self.topic,
            "description": self.description,
            "antagonist_type": self.antagonist_type,
            "max_rounds": self.max_rounds,
            "current_round": self.current_round,
            "protagonist_messages": self.protagonist_messages,
            "antagonist_messages": self.antagonist_messages,
            "judge_summary": self.judge_summary,
            "status": self.status,
            "theory_context": self.theory_context,
        }


debate_sessions: Dict[str, DebateSession] = {}
retriever = DebateRetriever()


PROTAGONIST_PROMPT = """你是红芯理辩的正方辩手，一位善于用辩证思维分析问题的思想者。

【核心立场】
你相信"实践出真知"，善于从实际出发分析问题。你懂得事物是普遍联系和发展变化的，要用全面的、历史的、发展的眼光看问题。

【辩题】
{topic}

【参考视角】
以下是分析此问题可以借鉴的思考角度，请自然融入你的论证中：
{theory_support}

【论证方法】
1. 立论时先分析问题的内在矛盾，揭示事物的本质。
2. 具体问题具体分析，避免抽象空洞的论证。
3. 论证过程要体现从现象到本质的思维路径。
4. 举例要贴近大学生的现实生活，让道理在实践中得到检验。
5. 反驳时指出对方是否只看到问题的一面，忽视了其他方面。

【表达要求】
1. 先亮明本轮结论，再用辩证思维展开论证。
2. 使用"现象分析 → 矛盾揭示 → 本质把握 → 实践检验"的结构。
3. 必须回应反方上一轮的质疑，不能回避关键问题。
4. 语言要让大学生易懂，把深刻的道理讲清楚。
5. 自然融入理论观点，但不要说"某某认为"、"根据什么理论"这类话。

【风格】
坚定、清晰、有理有据、辩证统一。

【长度】
280-420字。
"""


ANTAGONIST_PROMPT = """你是红芯理辩的反方辩手，一位善于发现问题的批判者。

【核心立场】
你深知"矛盾是事物发展的动力"，善于发现正方论证中的内在矛盾。你懂得任何事物都有两面性，要善于在对立中把握统一，在统一中把握对立。

【辩题】
{topic}

【参考视角】
以下是质疑此问题可以借鉴的思考角度，请自然融入你的批判中：
{theory_support}

【批判方法】
1. 揭示正方论证中的主要矛盾和次要矛盾。
2. 检验正方是否只看到问题的一面，忽视了事物的复杂性。
3. 追问正方是否看到了事物的两面性。
4. 指出正方是否把特殊当一般，把局部当整体。
5. 用发展的眼光质疑正方的结论是否经得起检验。

【表达要求】
1. 先准确复述正方关键观点，再展开批判。
2. 优先揭示正方论证中的逻辑矛盾和现实矛盾。
3. 每次反驳后给出更符合实际的替代解释。
4. 使用追问句引导思考，但禁止人身攻击。
5. 结尾抛出一个正方尚未回答的关键问题。
6. 自然融入理论观点，但不要说"某某认为"、"根据什么理论"这类话。

【风格】
犀利、深刻、辩证、有批判精神。

【长度】
240-380字。
"""


JUDGE_PROMPT = """你是红芯理辩的裁判，一位善于总结和引导的思考者。

【核心立场】
你相信"真理越辩越明"，善于从双方的交锋中提炼出有价值的认识。你懂得用实践的标准来检验观点，用发展的眼光来看待问题。

【辩题】
{topic}

【参考视角】
以下是评判此问题可以借鉴的思考角度，可作为评判的参考依据：
{theory_support}

【评判原则】
1. 看谁的论证更贴近实际，更能解释现实中的现象。
2. 看谁更善于看到问题的多个方面，而不是只盯着一点。
3. 看谁的结论更经得起推敲，有没有考虑边界情况。
4. 看谁更善于用发展的眼光看问题，承认事物是会变化的。
5. 看谁能抓住问题的核心，而不是在细枝末节上纠缠。

【输出结构】
1. 争议焦点（这个辩题到底在争什么？背后的问题是什么？）
2. 双方亮点（各自说对了什么？哪里有启发？）
3. 关键分歧（两人最大的分歧在哪里？为什么会这样？）
4. 实践启示（在现实生活中，我们应该怎么看待这类问题？）
5. 一句话建议（给大学生的一条建议，怎么培养这种思考能力）

【要求】
- 用大白话总结，不要用学术腔。
- 要引用双方的具体观点，说明好在哪里、问题在哪里。
- 让人看完觉得"原来这个问题可以这样想"。
- 自然融入理论观点，但不要说"某某认为"、"根据什么理论"这类话。

【长度】
420-700字。
"""


def _stream_completion(system_prompt: str, user_prompt: str, max_tokens: int | None = None) -> Generator[str, None, None]:
    final_max_tokens = max_tokens or settings.debate_max_tokens

    responses = Generation.call(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        api_key=settings.api_key,
        temperature=settings.debate_temperature,
        max_tokens=final_max_tokens,
        result_format="message",
        stream=True,
        incremental_output=True,
    )

    for response in responses:
        if response.status_code == 200:
            content = response.output.choices[0].message.content
            if content:
                yield content
        else:
            raise RuntimeError(f"API调用失败: {response.code} - {response.message}")


def _retrieve_theory_for_protagonist(topic: str, description: str) -> str:
    results = retriever.retrieve(topic, top_k=3, collection_name="debate_propositions")
    chunk_results = retriever.retrieve(topic, top_k=2, collection_name="debate_chunks")
    
    theory_lines = []
    
    for r in results[:3]:
        content = r.get("content", r.get("proposition", ""))
        source = r.get("source", "马克思主义文献")
        if content:
            theory_lines.append(f"• {content}（出处：{source}）")
    
    for r in chunk_results[:2]:
        content = r.get("content", r.get("text", ""))
        source = r.get("source", "理论文献")
        if content:
            theory_lines.append(f"• {content[:200]}...（出处：{source}）")
    
    if not theory_lines:
        return "暂无相关理论支撑，请运用马克思主义基本原理进行论证。"
    
    return "\n".join(theory_lines)


def _retrieve_theory_for_antagonist(topic: str, description: str) -> str:
    results = retriever.retrieve(topic, top_k=3, collection_name="debate_propositions")
    chunk_results = retriever.retrieve(topic, top_k=2, collection_name="debate_chunks")
    
    theory_lines = []
    
    for r in results[:3]:
        content = r.get("content", r.get("proposition", ""))
        source = r.get("source", "马克思主义文献")
        if content:
            theory_lines.append(f"• {content}（出处：{source}）")
    
    for r in chunk_results[:2]:
        content = r.get("content", r.get("text", ""))
        source = r.get("source", "理论文献")
        if content:
            theory_lines.append(f"• {content[:200]}...（出处：{source}）")
    
    if not theory_lines:
        return "暂无相关理论支撑，请运用马克思主义基本原理进行批判。"
    
    return "\n".join(theory_lines)


def _retrieve_theory_for_judge(topic: str) -> str:
    results = retriever.retrieve(topic, top_k=4, collection_name="debate_propositions")
    chunk_results = retriever.retrieve(topic, top_k=3, collection_name="debate_chunks")
    
    theory_lines = []
    
    for r in results[:4]:
        content = r.get("content", r.get("proposition", ""))
        source = r.get("source", "马克思主义文献")
        if content:
            theory_lines.append(f"• {content}（出处：{source}）")
    
    for r in chunk_results[:3]:
        content = r.get("content", r.get("text", ""))
        source = r.get("source", "理论文献")
        if content:
            theory_lines.append(f"• {content[:200]}...（出处：{source}）")
    
    if not theory_lines:
        return "暂无相关理论参考，请运用马克思主义基本原理进行评判。"
    
    return "\n".join(theory_lines)


def _build_protagonist_user_prompt(
    current_round: int, 
    description: str, 
    last_antagonist: str
) -> str:
    if current_round == 1:
        return (
            f"【当前轮次】第 {current_round} 轮（立论）\n"
            f"【辩题说明】{description or '无'}\n"
            "【任务】先定义关键概念，再给出完整立论。"
            "请结合理论支撑中的观点，主动预判可能反驳并提前回应1个风险点。"
        )
    elif current_round == 2:
        return (
            f"【当前轮次】第 {current_round} 轮（拆解回应）\n"
            f"【辩题说明】{description or '无'}\n"
            f"【反方上一轮观点】{last_antagonist}\n"
            "【任务】逐点回应反方最强质疑，补齐论证链。"
            "请结合理论支撑，点名反方至少1个逻辑漏洞并给出反证。"
        )
    else:
        return (
            f"【当前轮次】第 {current_round} 轮（收束）\n"
            f"【辩题说明】{description or '无'}\n"
            f"【反方上一轮观点】{last_antagonist}\n"
            "【任务】收束争点，给出最终判断。"
            "请用'核心结论 + 关键理由 + 对反方最终回应'完成本轮。"
        )


def _build_antagonist_user_prompt(current_round: int, description: str, protagonist_message: str) -> str:
    if current_round == 1:
        return (
            f"【当前轮次】第 {current_round} 轮（首轮质疑）\n"
            f"【辩题说明】{description or '无'}\n"
            f"【正方本轮观点】{protagonist_message}\n"
            "【任务】优先攻击定义和前提是否成立。"
            "请结合理论支撑，指出正方至少2处可被追问的漏洞，并抛出1个关键追问。"
        )

    if current_round == 2:
        return (
            f"【当前轮次】第 {current_round} 轮（深挖漏洞）\n"
            f"【辩题说明】{description or '无'}\n"
            f"【正方本轮观点】{protagonist_message}\n"
            "【任务】针对正方回应继续深挖。"
            "结合理论支撑，重点检验：其证据是否足够、推理是否跳步、结论是否扩大化。"
        )

    return (
        f"【当前轮次】第 {current_round} 轮（最终反压）\n"
        f"【辩题说明】{description or '无'}\n"
        f"【正方本轮观点】{protagonist_message}\n"
        "【任务】做最终反压：指出正方仍未解释清楚的核心缺口。"
        "请用一段'最强质疑'收尾。"
    )


def create_session(session_id: str, topic: str, description: str, max_rounds: int = 10) -> DebateSession:
    theory_context = {
        "protagonist_theory": _retrieve_theory_for_protagonist(topic, description),
        "antagonist_theory": _retrieve_theory_for_antagonist(topic, description),
        "judge_theory": _retrieve_theory_for_judge(topic),
    }
    
    session = DebateSession(
        session_id=session_id,
        topic=topic,
        description=description,
        max_rounds=min(10, max(1, max_rounds)),
        theory_context=theory_context,
    )
    debate_sessions[session_id] = session
    return session


def get_session(session_id: str) -> Optional[DebateSession]:
    return debate_sessions.get(session_id)


def delete_session(session_id: str):
    if session_id in debate_sessions:
        del debate_sessions[session_id]


def stream_single_round(session: DebateSession) -> Generator[dict, None, None]:
    session.current_round += 1
    current_round = session.current_round

    yield {"type": "round_start", "round": current_round}

    yield {"type": "protagonist_start", "round": current_round}
    last_antagonist = session.antagonist_messages[-1] if session.antagonist_messages else ""
    
    p_user_prompt = _build_protagonist_user_prompt(
        current_round=current_round,
        description=session.description,
        last_antagonist=last_antagonist
    )

    theory_support = session.theory_context.get("protagonist_theory", "") if session.theory_context else ""
    system_prompt = PROTAGONIST_PROMPT.format(
        topic=session.topic,
        theory_support=theory_support
    )

    full_p = ""
    for chunk in _stream_completion(system_prompt, p_user_prompt):
        full_p += chunk
        yield {"type": "protagonist_chunk", "round": current_round, "content": chunk}
    session.protagonist_messages.append(full_p)
    
    yield {"type": "protagonist_end", "round": current_round}

    yield {"type": "antagonist_start", "round": current_round}
    a_user_prompt = _build_antagonist_user_prompt(
        current_round=current_round,
        description=session.description,
        protagonist_message=full_p,
    )

    theory_support = session.theory_context.get("antagonist_theory", "") if session.theory_context else ""
    system_prompt = ANTAGONIST_PROMPT.format(
        topic=session.topic,
        theory_support=theory_support
    )

    full_a = ""
    for chunk in _stream_completion(system_prompt, a_user_prompt):
        full_a += chunk
        yield {"type": "antagonist_chunk", "round": current_round, "content": chunk}
    session.antagonist_messages.append(full_a)
    yield {"type": "antagonist_end", "round": current_round}

    if session.current_round >= session.max_rounds:
        session.status = "max_rounds_reached"
        yield {
            "type": "max_rounds_reached",
            "round": current_round,
            "max_rounds": session.max_rounds,
            "session": session.to_dict(),
        }
    else:
        session.status = "waiting_next"
        yield {
            "type": "round_complete",
            "round": current_round,
            "can_continue": True,
            "session": session.to_dict(),
        }


def stream_judge_summary(session: DebateSession) -> Generator[dict, None, None]:
    yield {"type": "judge_start"}
    
    history = []
    for i in range(len(session.protagonist_messages)):
        history.append(
            f"第{i + 1}轮\n"
            f"正方：{session.protagonist_messages[i]}\n"
            f"反方：{session.antagonist_messages[i]}"
        )

    judge_user_prompt = (
        "【完整辩论记录】\n"
        + "\n\n".join(history)
        + "\n\n【任务】请按结构输出裁判结论，重点说明谁在哪些论证点更完整。"
    )

    theory_support = session.theory_context.get("judge_theory", "") if session.theory_context else ""
    system_prompt = JUDGE_PROMPT.format(
        topic=session.topic,
        theory_support=theory_support
    )

    full_j = ""
    for chunk in _stream_completion(system_prompt, judge_user_prompt, max_tokens=1800):
        full_j += chunk
        yield {"type": "judge_chunk", "content": chunk}
    
    session.judge_summary = full_j
    session.status = "completed"
    yield {"type": "judge_end"}

    yield {
        "type": "complete",
        "session": session.to_dict(),
    }


def stream_debate_events(
    topic: str,
    description: str,
    antagonist_type: str,
    rounds: int,
) -> Generator[dict, None, None]:
    protagonist_messages: List[str] = []
    antagonist_messages: List[str] = []

    final_rounds = max(1, min(3, rounds))

    yield {"type": "start", "topic": topic, "antagonist_type": "反方"}

    protagonist_theory = _retrieve_theory_for_protagonist(topic, description)
    antagonist_theory = _retrieve_theory_for_antagonist(topic, description)
    judge_theory = _retrieve_theory_for_judge(topic)

    for current_round in range(1, final_rounds + 1):
        yield {"type": "round_start", "round": current_round}

        yield {"type": "protagonist_start", "round": current_round}
        last_antagonist = antagonist_messages[-1] if antagonist_messages else ""
        
        p_user_prompt = _build_protagonist_user_prompt(
            current_round=current_round,
            description=description,
            last_antagonist=last_antagonist
        )

        full_p = ""
        for chunk in _stream_completion(
            PROTAGONIST_PROMPT.format(topic=topic, theory_support=protagonist_theory), 
            p_user_prompt
        ):
            full_p += chunk
            yield {"type": "protagonist_chunk", "round": current_round, "content": chunk}
        protagonist_messages.append(full_p)
        
        yield {"type": "protagonist_end", "round": current_round}

        yield {"type": "antagonist_start", "round": current_round}
        a_user_prompt = _build_antagonist_user_prompt(
            current_round=current_round,
            description=description,
            protagonist_message=full_p,
        )

        full_a = ""
        for chunk in _stream_completion(
            ANTAGONIST_PROMPT.format(topic=topic, theory_support=antagonist_theory), 
            a_user_prompt
        ):
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
    for chunk in _stream_completion(JUDGE_PROMPT.format(topic=topic, theory_support=judge_theory), judge_user_prompt, max_tokens=1800):
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
            "status": "completed",
        },
    }
