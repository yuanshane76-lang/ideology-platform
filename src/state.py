from typing import TypedDict, List, Dict, Optional, Literal

class RAGState(TypedDict, total=False):
    current_query: str
    enhanced_query: str
    dialogue_history: List[Dict]
    theory_docs: List[Dict]
    politics_docs: List[Dict]
    generated_answer: str
    answer_confidence: float
    is_terminated: bool
    query_type: Literal["theory", "politics", "hybrid", "chat"]
    retrieve_strategy: Literal["theory_only", "politics_only", "hybrid", "no_retrieve"]
    retrieve_params: Dict
    need_supplement: bool
    conversation_id: str
    turn_id: int
    conversation_summary: str
    extracted_keywords: List[str]
    audit_passed: bool
    audit_feedback: str
    retry_count: int
    final_answer: str
    follow_up_questions: List[str]
    next_agent: str
