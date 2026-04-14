from typing import Dict, List
from ..state import RAGState
from ..retriever import search_moment
from ..conversation import conversation_store

def politics_retriever_agent(state: RAGState) -> Dict:
    """
    时政检索智能体：时政信息检索器
    - 增强问题向量化
    - 时政库 Top-K 召回
    """
    query = state.get("enhanced_query") or state.get("current_query", "")
    keywords = state.get("extracted_keywords", [])
    retrieve_params = state.get("retrieve_params", {})
    conversation_id = state.get("conversation_id", "")
    
    politics_top_k = retrieve_params.get("politics_top_k", 3)
    
    print(f"[PoliticsRetriever] Retrieving from politics DB (top_k={politics_top_k}): {query[:50]}...")
    
    # 执行检索
    politics_docs = search_moment(query, keywords, top_k=politics_top_k)
    
    print(f"[PoliticsRetriever] Retrieved {len(politics_docs)} documents")
    
    # 更新证据缓存
    if conversation_id:
        theory_docs = state.get("theory_docs", [])
        conversation_store.update_evidence_cache(conversation_id, theory_docs, politics_docs)
    
    return {
        "politics_docs": politics_docs
    }
