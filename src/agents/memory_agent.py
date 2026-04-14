from typing import Dict, List
from ..state import RAGState
from ..clients import openai_client
from ..config import settings
from ..conversation import conversation_store

def memory_agent(state: RAGState) -> Dict:
    """
    记忆智能体：上下文管家
    - 历史对话存储
    - 增强问题生成（解决指代/省略问题）
    - 记忆截断（保留最近5轮）
    """
    current_query = state.get("current_query", "")
    conversation_id = state.get("conversation_id", "")
    
    print(f"[MemoryAgent] Processing query: {current_query[:50]}...")
    
    # 获取历史对话
    dialogue_history = state.get("dialogue_history", [])
    if conversation_id:
        conv = conversation_store.get_conversation(conversation_id)
        if conv:
            # 获取最近N轮对话（从配置读取）
            max_turns = settings.max_memory_turns
            recent_messages = conversation_store.get_recent_messages(conversation_id, max_count=max_turns * 2)
            dialogue_history = [
                {"role": msg.role, "content": msg.content}
                for msg in recent_messages
            ]
            
            # 记忆截断：只保留最近N轮（2N条消息）
            if len(dialogue_history) > max_turns * 2:
                dialogue_history = dialogue_history[-max_turns * 2:]
    
    # 生成增强问题
    if dialogue_history and len(dialogue_history) > 0:
        enhanced_query = _generate_enhanced_query(current_query, dialogue_history)
    else:
        enhanced_query = current_query
    
    print(f"[MemoryAgent] Enhanced query: {enhanced_query[:80]}...")
    
    return {
        "enhanced_query": enhanced_query,
        "dialogue_history": dialogue_history
    }

def _generate_enhanced_query(current_query: str, dialogue_history: List[Dict]) -> str:
    """
    生成增强问题：将指代改写为完整问题
    """
    # 构建历史对话文本
    history_text = "\n".join([
        f"{msg['role']}: {msg['content']}"
        for msg in dialogue_history[-6:]
    ])
    
    sys_prompt = "你是一个问题改写专家，负责将包含指代的追问改写为完整、独立的问题。"
    user_prompt = f"""请将用户当前问题改写为完整、独立的问题，消除所有指代和省略。

当前问题：{current_query}

历史对话：
{history_text}

改写规则：
1. 将"它"、"这个"、"刚才说的"等指代替换为具体内容
2. 特别注意：如果用户提到"第一个/第二个问题"、"第1点/第2点"等序号指代：
   - 仔细查找上一轮回答中的"延伸思考"或编号列表
   - 将序号指代替换为对应的完整问题/内容
3. 补充省略的信息，使问题完整自洽
4. 保持问题的原意和语气
5. 直接输出改写后的问题，不要添加解释

示例：
- 原问题："第二个问题怎么理解"
- 如果上一轮延伸思考第二个是"新质生产力与传统生产力有何区别？"
- 改写为："请解释新质生产力与传统生产力有何区别？"
"""
    
    try:
        enhanced_query = openai_client.chat.completions.create(
            model=settings.fast_model,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt}
            ],
            stream=False
        ).choices[0].message.content or current_query
        
        enhanced_query = enhanced_query.strip()
        
        if not enhanced_query or len(enhanced_query) < 3:
            enhanced_query = current_query
        
        print(f"[MemoryAgent] Rewritten: '{current_query}' -> '{enhanced_query}'")
        
        return enhanced_query
    except Exception as e:
        print(f"[MemoryAgent] Error in query rewriting: {e}")
        return current_query
