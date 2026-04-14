from typing import Dict, Literal
from ..state import RAGState
from ..clients import openai_client
from ..config import settings


def router_agent(state: RAGState) -> Dict:
    """
    路由智能体：检索策略师
    - 问题分类（理论/时政/混合型/闲聊）
    - 数据库匹配
    - top-k 参数配置
    - 关键词提取
    
    优化：合并关键词提取和问题分类为一次 LLM 调用
    """
    query = state.get("enhanced_query") or state.get("current_query", "")
    
    print(f"🎯 [RouterAgent] 收到查询: {query[:50]}...")
    
    query_lower = query.lower().strip()
    
    casual_keywords = [
        '你好', '嗨', 'hello', 'hi', '早上好', '下午好', '晚上好', '晚安',
        '吃了吗', '吃饭了吗', '在干嘛', '在吗', '最近怎样', '最近怎么样',
        '还好吗', '还好么', '心情', '情绪', '感觉', '今天天气',
        '天气怎么样', '天气如何', '随便聊聊', '聊聊天', '闲聊',
        '今天怎么样', '今天如何', '最近好吗', '最近好么', '嘿', '哈喽'
    ]
    
    for keyword in casual_keywords:
        if keyword in query_lower:
            print(f"[RouterAgent] 🎯 强制识别为闲聊: 包含关键词 '{keyword}'")
            return {
                "query_type": "no_retrieve",
                "retrieve_strategy": "no_retrieve",
                "retrieve_params": {
                    "theory_top_k": 0,
                    "politics_top_k": 0,
                    "use_cache": False
                },
                "extracted_keywords": [],
                "theory_docs": [],
                "politics_docs": []
            }
    
    result = _classify_and_extract(query)
    
    print(f"[RouterAgent] Query type: {result['query_type']}, Strategy: {result['retrieve_strategy']}")
    
    return {
        "query_type": result["query_type"],
        "retrieve_strategy": result["retrieve_strategy"],
        "retrieve_params": result["retrieve_params"],
        "extracted_keywords": result["keywords"],
        "theory_docs": [],
        "politics_docs": []
    }


def _classify_and_extract(query: str) -> dict:
    """
    合并操作：一次 LLM 调用同时完成关键词提取和问题分类
    """
    sys_prompt = "你是一个问题分析专家，负责同时提取关键词和判断问题类型。"
    user_prompt = f"""请分析用户问题，完成两个任务：

用户问题：{query}

【任务1：提取关键词】
提取2-6个最相关的关键词，包括：
- 实体关键词（人名、会议名、专有名词）
- 概念关键词（理论、思想、原则）
- 主题关键词（话题、领域）

【任务2：判断问题类型】
- hybrid（混合型）：需要思政专业知识的问题，如理论探讨、政策解读、时政分析
- no_retrieve（无需检索）：日常闲聊、简单问候、个人心情分享

请返回标准 JSON 格式：
{{
  "keywords": ["关键词1", "关键词2"],
  "query_type": "hybrid" 或 "no_retrieve",
  "retrieve_strategy": "hybrid" 或 "no_retrieve",
  "theory_top_k": 3,
  "politics_top_k": 3
}}"""
    
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
        
        query_type = obj.get("query_type", "hybrid")
        retrieve_strategy = obj.get("retrieve_strategy", "hybrid")
        keywords = obj.get("keywords", [])
        
        if query_type not in ["hybrid", "no_retrieve"]:
            query_type = "hybrid"
        if retrieve_strategy not in ["hybrid", "no_retrieve"]:
            retrieve_strategy = "hybrid"

        if retrieve_strategy == "no_retrieve":
            theory_top_k = 0
            politics_top_k = 0
        else:
            theory_top_k = min(obj.get("theory_top_k", 3), 3)
            politics_top_k = min(obj.get("politics_top_k", 3), 3)
        
        return {
            "query_type": query_type,
            "retrieve_strategy": retrieve_strategy,
            "keywords": keywords,
            "retrieve_params": {
                "theory_top_k": theory_top_k,
                "politics_top_k": politics_top_k,
                "use_cache": False
            }
        }
        
    except Exception as e:
        print(f"[RouterAgent] Error in classification: {e}")
        return {
            "query_type": "hybrid",
            "retrieve_strategy": "hybrid",
            "keywords": [],
            "retrieve_params": {
                "theory_top_k": 3,
                "politics_top_k": 3,
                "use_cache": False
            }
        }
