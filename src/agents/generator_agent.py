from typing import Dict
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from ..state import RAGState
from ..config import settings

# 1. 初始化 LangChain 的 LLM
# 必须开启 streaming=True，这样 service.py 里的回调才能捕获到 Token 推送给前端
llm = ChatOpenAI(
    model=settings.llm_model,
    temperature=0.7,
    streaming=True,
    # 如果你的 settings 里有 base_url 或 api_key，建议在这里显式传入，例如：
    openai_api_key=settings.api_key,
    base_url=settings.base_url
)

def generator_agent(state: RAGState) -> Dict:
    """
    生成智能体：答案创作者
    - 融合历史+双库上下文
    - 生成连贯准确回答
    """
    query = state.get("enhanced_query") or state.get("current_query", "")
    theory_docs = state.get("theory_docs", [])
    politics_docs = state.get("politics_docs", [])
    turn_id = state.get("turn_id", 1)
    conversation_summary = state.get("conversation_summary", "")
    query_type = state.get("query_type", "hybrid")  # 获取问题类型
    dialogue_history = state.get("dialogue_history", [])
    
    print(f"[Generator] Generating answer for turn {turn_id}: {query[:50]}...")
    
    # --- 保持你原有的 Prompt 构建逻辑不变 ---
    
    # 构建检索内容
    t_text = "\n".join([d["content"] for d in theory_docs]) or "（暂无直接理论）"
    m_text = "\n".join([d["content"] for d in politics_docs]) or "（暂无时政案例）"
    
    # 构建上下文部分
    context_parts = []
    if turn_id > 1:
        if conversation_summary:
            context_parts.append(f"【对话背景】：{conversation_summary}")
        if dialogue_history:
            last_assistant_answer = ""
            for msg in reversed(dialogue_history):
                if msg.get("role") == "assistant":
                    last_assistant_answer = msg.get("content", "")
                    break
            if last_assistant_answer:
                context_parts.append(f"【上一轮回答要点】：{last_assistant_answer[:300]}")
        context_parts.append("注意：这是多轮对话的后续问题，请在回答中适当引用上一轮的要点，保持对话连贯性。")
    
    context_text = "\n\n".join(context_parts) if context_parts else ""
    
    # 构建 prompt 文本
    # 根据 query_type 选择不同的提示词
    if query_type == "no_retrieve":
        # 闲聊模式：自然友好的提示词
        sys_prompt_text = """你是一位友善的大学辅导员，擅长与学生进行日常交流。
你的特点是自然、友好、有同理心。请根据学生的问题给出贴心的回应。"""
    else:
        # 思政模式
        sys_prompt_text = """你是一位既有理论深度又有教育温度的高校思政课教师。
你的特点是：
1. 专业严谨但不刻板，善于用生动的语言讲解理论
2. 关注学生成长，回答中体现对学生的关心和理解
3. 将宏大理论与学生实际生活联系起来
4. 适当使用鼓励性、启发性的语言，让思政教育既有深度又有温度"""
    
    # 根据 query_type 构建用户提示词
    if query_type == "no_retrieve":
        # 闲聊模式
        user_prompt_text = f"""学生问题：{query}

请给出一个自然、友好的回应，像朋友一样聊天。
要求：
1. 回答简短友好（1-3句话）
2. 表达理解和关心
3. 如果学生心情不好，给予适当安慰
4. 不要强行关联思政理论"""
        
        # 闲聊模式不需要检索内容
        t_text = ""
        m_text = ""
        context_text = ""  # 闲聊模式也不需要对话历史
        
    else:
        # 原有的思政模式提示词
        user_prompt_text = f"""请基于以下材料回答学生问题。

【理论依据】:
{t_text}

【时政案例】:
{m_text}

{context_text}

学生问题：{query}

要求：
1. 以学生为中心，先理解学生的困惑点
2. 用生动、亲切的语言讲解理论，适当使用比喻和故事
3. 必须引用【理论依据】中的核心观点，但避免机械引用
4. 结合【时政案例】进行分析，展示理论的实际应用
5. 政治立场坚定，但表达方式要有温度、有共鸣
6. 结尾可以给予鼓励或提出启发式问题
7. {"如果是多轮对话，请适当引用上一轮要点，保持对话自然连贯。" if turn_id > 1 else ""}
"""
    try:
        # 2. 转换 Prompt 为 LangChain 消息格式
        messages = [
            SystemMessage(content=sys_prompt_text),
            HumanMessage(content=user_prompt_text)
        ]

        # 3. 调用 LLM
        # 使用 invoke 而不是 raw client
        # LangChain 会自动处理流式聚合：
        # - 一边通过 callback 推送 token 给前端 (service.py 里的逻辑)
        # - 一边在内部拼接完整文本
        response = llm.invoke(messages)
        
        # 获取完整回答
        answer = response.content
        
        print(f"[Generator] Generated answer length: {len(answer)}")
        
        return {
            "generated_answer": answer,
            # 生成了新答案，重置审核状态，触发 Validator
            "audit_passed": None 
        }

    except Exception as e:
        print(f"[Generator] Error in answer generation: {e}")
        return {
            "generated_answer": "抱歉，生成回答时出现错误，请稍后重试。",
            "audit_passed": None
        }