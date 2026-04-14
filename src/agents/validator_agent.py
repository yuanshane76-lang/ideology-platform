from typing import Dict
from ..state import RAGState
from ..clients import openai_client
from ..config import settings

def validator_agent(state: RAGState) -> Dict:
    """
    校验智能体：质量监督员（简化版）
    - 答案一致性校验
    - 可信度评分
    - 仅在低置信度时触发补充检索
    
    优化：移除冗余的自动修正流程，减少 LLM 调用
    """
    query = state.get("enhanced_query") or state.get("current_query", "")
    answer = state.get("generated_answer", "")
    theory_docs = state.get("theory_docs", [])
    politics_docs = state.get("politics_docs", [])
    query_type = state.get("query_type", "hybrid")
    retry_count = state.get("retry_count", 0)
    
    if query_type == "no_retrieve":
        print(f"[Validator] Skipping audit for casual chat")
        return {
            "generated_answer": answer,
            "audit_passed": True,
            "audit_feedback": "闲聊模式无需审核",
            "answer_confidence": 1.0,
            "need_supplement": False
        }
    
    print(f"[Validator] Validating answer (retry {retry_count}): {answer[:50]}...")
    
    t_text = "\n".join([d["content"] for d in theory_docs]) or "（暂无直接理论）"
    m_text = "\n".join([d["content"] for d in politics_docs]) or "（暂无时政案例）"
    
    audit_result = _audit_answer(query, answer, t_text, m_text)
    
    audit_passed = audit_result["passed"]
    audit_feedback = audit_result["reason"]
    confidence = audit_result["confidence"]
    
    print(f"[Validator] Audit result: passed={audit_passed}, confidence={confidence:.2f}")
    
    need_supplement = (
        not audit_passed and 
        confidence < settings.confidence_threshold and 
        retry_count < settings.max_retry_count
    )
    
    return {
        "generated_answer": answer,
        "audit_passed": audit_passed,
        "audit_feedback": audit_feedback,
        "answer_confidence": confidence,
        "need_supplement": need_supplement
    }

def _audit_answer(query: str, answer: str, t_text: str, m_text: str) -> Dict:
    """
    审核回答并给出评分（简化版 prompt）
    """
    sys_prompt = "你是一名思政内容审核专家。请简洁审核。"
    user_prompt = f"""审核回答是否符合要求。

问题：{query}
回答：{answer[:800]}

审核标准：
1. 符合社会主义核心价值观
2. 无低级红、高级黑
3. 理论引用准确

返回 JSON：
{{"passed": true/false, "reason": "简短意见", "confidence": 0.0-1.0}}"""
    
    try:
        response_text = openai_client.chat.completions.create(
            model=settings.fast_model,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt}
            ],
            stream=False
        ).choices[0].message.content or ""
        
        import json
        response_text = response_text.replace("```json", "").replace("```", "").strip()
        obj = json.loads(response_text)
        
        return {
            "passed": bool(obj.get("passed", False)),
            "reason": obj.get("reason", "未提供原因"),
            "confidence": float(obj.get("confidence", 0.5))
        }
    except Exception as e:
        print(f"[Validator] Error in audit: {e}")
        return {
            "passed": True,
            "reason": "审核服务暂时不可用，默认通过",
            "confidence": 0.7
        }
