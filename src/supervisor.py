from typing import Dict, Literal
from .state import RAGState


def supervisor_node(state: RAGState) -> Dict:
    """
    监督者节点：严格的流水线控制
    流程：Validator -> Memory -> Router -> Retrievers -> Generator -> END
    """
    turn_id = state.get("turn_id", 1)
    if "current_query" not in state:
        state["current_query"] = state.get("user_query", "")

    print(f"[Supervisor] Checkpoint | Turn: {turn_id} | "
          f"Enhanced: {bool(state.get('enhanced_query'))} | "
          f"Strategy: {state.get('retrieve_strategy')} | "
          f"Theory: {len(state.get('theory_docs', []))} | "
          f"Politics: {len(state.get('politics_docs', []))}")

    if state.get("generated_answer") and state.get("audit_passed") is None:
        print(f"[Supervisor] ➡️ Routing to Validator (Draft needs review)")
        return {"next_agent": "validator_agent"}
    
    if state.get("audit_passed") is not None:
        need_supplement = state.get("need_supplement", False)
        retry_count = state.get("retry_count", 0)
        
        if need_supplement and retry_count < 2:
            print(f"[Supervisor] 🔄 Validator requested supplement. Retrying retrieval.")
            retrieve_params = state.get("retrieve_params", {})
            retrieve_params["theory_top_k"] = retrieve_params.get("theory_top_k", 3) + 2
            retrieve_params["politics_top_k"] = retrieve_params.get("politics_top_k", 3) + 2
            
            strategy = state.get("retrieve_strategy", "hybrid")
            next_agent = "theory_retriever_agent" if strategy in ["theory_only", "hybrid"] else "politics_retriever_agent"
            
            return {
                "next_agent": next_agent,
                "retrieve_params": retrieve_params,
                "retry_count": retry_count + 1,
                "generated_answer": None, 
                "audit_passed": None
            }
        
        print(f"[Supervisor] ✅ Workflow Finished.")
        return {"next_agent": "END"}

    if turn_id > 1 and not state.get("enhanced_query"):
        print(f"[Supervisor] ➡️ Routing to MemoryAgent (Context enhancement needed)")
        return {"next_agent": "memory_agent"}

    if not state.get("retrieve_strategy"):
        print(f"[Supervisor] ➡️ Routing to RouterAgent (Strategy needed)")
        return {"next_agent": "router_agent"}

    retrieve_strategy = state.get("retrieve_strategy")
    theory_docs = state.get("theory_docs")
    politics_docs = state.get("politics_docs")

    if retrieve_strategy == "hybrid":
        if not theory_docs: 
            print(f"[Supervisor] ➡️ Routing to TheoryRetriever (Hybrid step 1)")
            return {"next_agent": "theory_retriever_agent"}
        if not politics_docs:
            print(f"[Supervisor] ➡️ Routing to PoliticsRetriever (Hybrid step 2)")
            return {"next_agent": "politics_retriever_agent"}
    
    elif retrieve_strategy == "theory_only":
        if not theory_docs:
            print(f"[Supervisor] ➡️ Routing to TheoryRetriever")
            return {"next_agent": "theory_retriever_agent"}
            
    elif retrieve_strategy == "politics_only":
        if not politics_docs:
            print(f"[Supervisor] ➡️ Routing to PoliticsRetriever")
            return {"next_agent": "politics_retriever_agent"}

    print(f"[Supervisor] ➡️ All data ready. Routing to GeneratorAgent")
    return {"next_agent": "generator_agent", "query_type": state.get("query_type", "hybrid")}
