from typing import Dict, Any, Iterator
from .clients import openai_client
from .config import settings


# src/node.py

def final_answer_stream(state: Dict[str, Any]) -> Iterator[str]:
    """
    最终稿：流式输出
    """
    t_text = "\n".join([d["content"] for d in state.get("theory_docs", [])]) or "（暂无直接理论）"
    m_text = "\n".join([d["content"] for d in state.get("politics_docs", [])]) or "（暂无时政案例）"

    draft = state.get("generated_answer", "")
    audit_passed = state.get("audit_passed", False)
    feedback = state.get("audit_feedback", "")
    
    # 多轮对话上下文
    conversation_summary = state.get("conversation_summary", "")
    dialogue_history = state.get("dialogue_history", [])
    turn_id = state.get("turn_id", 1)
    
    # 构建上下文部分
    context_parts = []
    if turn_id > 1:
        # 仅提供摘要，减少具体内容的干扰
        if conversation_summary:
            context_parts.append(f"【对话背景摘要】：{conversation_summary}")
        
        # 弱化上一轮的具体内容，只作为参考
        if dialogue_history:
            last_assistant_answer = ""
            for msg in reversed(dialogue_history):
                if msg.get("role") == "assistant":
                    last_assistant_answer = msg.get("content", "")
                    break
            # 截取长度缩短，防止模型过度关注旧内容
            if last_assistant_answer:
                context_parts.append(f"【上一轮回答片段】：{last_assistant_answer[:200]}...")
    
    context_text = "\n\n".join(context_parts) if context_parts else ""
    
    sys_prompt = "你是一名高校思政课教师与严谨的写作者。你的任务是对【初稿】进行结构化润色。"
    
    # 【核心修改】：调整 Prompt，强调以初稿为主
    user_prompt = f"""请对以下【初稿】进行最终润色，生成 Markdown 格式回答。

【理论依据】:
{t_text}

【时政案例】:
{m_text}

{context_text}

【初稿】:
{draft}

【审核结果】: {"通过" if audit_passed else "未通过"}
【审核意见】:
{feedback}

要求：
1) **核心内容必须完全基于【初稿】**，不要随意发散或改变初稿的主题。
2) 若审核未通过：请根据意见修正表述。
4) 连贯性：仅在文章开头或结尾简要呼应上一轮对话（如“正如我们之前讨论的...”），**严禁让上一轮的主题覆盖当前问题的核心**。
5) 保持【理论依据】和【时政案例】的引用准确性。
6) 在末尾自然追加一个小节：
   ---
   ### 延伸思考
   - 问题1
   - 问题2
"""

    stream = openai_client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_prompt},
        ],
        stream=True,
    )

  
    # 收集完整答案
    full_answer = ""
    
    for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        if delta and getattr(delta, "content", None):
            content = delta.content
            full_answer += content
            # 同步保存到 state
            state["final_answer"] = full_answer
            yield content
    
    # 流式输出结束后，确保 final_answer 完整保存
    if full_answer:
        state["final_answer"] = full_answer
        print(f"[final_answer_stream] Saved final answer to state: {len(full_answer)} chars")


def final_answer_text(state: Dict[str, Any]) -> str:
    """非流式：把流式 token 拼起来"""
    return "".join(list(final_answer_stream(state)))


def summarizer_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    对话摘要节点：当消息数量或总字符数超过阈值时生成/更新对话摘要
    """
    from .conversation import conversation_store
    from .config import settings
    
    conversation_id = state.get("conversation_id", "")
    if not conversation_id:
        return {}
    
    conv = conversation_store.get_conversation(conversation_id)
    if not conv:
        return {}
    
    # 检查是否需要生成摘要
    messages = conv.messages
    total_chars = sum(len(msg.content) for msg in messages)
    
    if len(messages) < settings.max_messages_before_summary and total_chars < settings.max_chars_before_summary:
        # 不需要摘要
        return {}
    
    # 构建消息历史（用于摘要）
    messages_text = "\n".join([
        f"{msg.role}: {msg.content}" 
        for msg in messages[-settings.max_messages_before_summary:]
    ])
    
    old_summary = conv.summary or "（无历史摘要）"
    
    sys_prompt = "你是一个对话摘要专家，负责将多轮对话压缩为简洁的摘要。"
    user_prompt = f"""请基于以下对话历史，生成或更新对话摘要。

【历史摘要】：
{old_summary}

【最近对话】：
{messages_text}

要求：
1. 保留核心主题和关键信息
2. 压缩到200字以内
3. 突出主要讨论的问题和要点
4. 直接输出摘要内容，不要添加"摘要："等前缀"""
    
    new_summary = openai_client.chat.completions.create(
        model=settings.fast_model,
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_prompt}
        ],
        stream=False
    ).choices[0].message.content or ""
    
    # 更新摘要
    if new_summary:
        conversation_store.update_summary(conversation_id, new_summary)
        return {"conversation_summary": new_summary}
    
    return {}











