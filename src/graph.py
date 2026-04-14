from langgraph.graph import StateGraph, END
from .state import RAGState
from .supervisor import supervisor_node
from .agents.memory_agent import memory_agent
from .agents.router_agent import router_agent
from .agents.theory_retriever_agent import theory_retriever_agent
from .agents.politics_retriever_agent import politics_retriever_agent
from .agents.generator_agent import generator_agent
from .agents.validator_agent import validator_agent

def build_supervisor_graph():
    """
    构建基于监督者模式的多智能体协作工作流
    监督者作为中央调度器，所有智能体执行后都回到监督者
    """
    workflow = StateGraph(RAGState)
    
    # 添加所有智能体节点
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("memory_agent", memory_agent)
    workflow.add_node("router_agent", router_agent)
    workflow.add_node("theory_retriever_agent", theory_retriever_agent)
    workflow.add_node("politics_retriever_agent", politics_retriever_agent)
    workflow.add_node("generator_agent", generator_agent)
    workflow.add_node("validator_agent", validator_agent)
    
    # 设置入口点为监督者
    workflow.set_entry_point("supervisor")
    
    # 监督者 → 所有智能体的条件边
    workflow.add_conditional_edges(
        "supervisor",
        lambda state: state.get("next_agent", "END"),
        {
            "memory_agent": "memory_agent",
            "router_agent": "router_agent",
            "theory_retriever_agent": "theory_retriever_agent",
            "politics_retriever_agent": "politics_retriever_agent",
            "generator_agent": "generator_agent",
            "validator_agent": "validator_agent",
            "END": END
        }
    )
    
    # 所有智能体执行后都回到监督者
    workflow.add_edge("memory_agent", "supervisor")
    workflow.add_edge("router_agent", "supervisor")
    workflow.add_edge("theory_retriever_agent", "supervisor")
    workflow.add_edge("politics_retriever_agent", "supervisor")
    workflow.add_edge("generator_agent", "supervisor")
    workflow.add_edge("validator_agent", "supervisor")
    
    return workflow.compile()

# 创建全局图实例
app_graph = build_supervisor_graph()
