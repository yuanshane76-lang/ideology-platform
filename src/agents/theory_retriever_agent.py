from typing import Dict, List
from ..state import RAGState
from ..retriever import search_theory
from ..conversation import conversation_store

def theory_retriever_agent(state: RAGState) -> Dict:
    """
    理论检索智能体：理论知识检索器
    - 增强问题向量化
    - 理论库 Top-K 召回
    """
    query = state.get("enhanced_query") or state.get("current_query", "")
    keywords = state.get("extracted_keywords", [])
    retrieve_params = state.get("retrieve_params", {})
    conversation_id = state.get("conversation_id", "")
    
    theory_top_k = retrieve_params.get("theory_top_k", 3)
    
    print(f"[TheoryRetriever] Retrieving from theory DB (top_k={theory_top_k}): {query[:50]}...")
    
    # 执行检索
    theory_docs = search_theory(query, keywords, top_k=theory_top_k)
    
    print(f"[TheoryRetriever] Retrieved {len(theory_docs)} documents")
    
    # 更新证据缓存
    if conversation_id:
        politics_docs = state.get("politics_docs", [])
        conversation_store.update_evidence_cache(conversation_id, theory_docs, politics_docs)
    
    return {
        "theory_docs": theory_docs
    }
