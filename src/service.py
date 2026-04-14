import threading
import queue
import json
import logging
import time
from typing import Dict, Any, Generator
from threading import Semaphore

from src.conversation import conversation_store
from src.graph import app_graph
from src.callbacks import StreamingQueueCallbackHandler
from src.clients import openai_client
from src.config import settings

logger = logging.getLogger(__name__)

_api_semaphore = Semaphore(8)


def _generate_smart_title_async(conversation_id: str, query: str, answer: str):
    """
    异步生成标题（不阻塞主流程）
    """
    try:
        sys_prompt = "你是一个善于总结的助手。"
        user_prompt = f"""请为以下对话生成一个极其简短的标题（4-8个字）。
要求：
1. 精准概括核心话题。
2. 严禁使用标点符号。
3. 严禁使用引号。
4. 直接输出标题文本。

用户：{query[:100]}
AI：{answer[:100]}

标题："""
        
        resp = openai_client.chat.completions.create(
            model=settings.fast_model,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=20,
            stream=False
        )
        title = resp.choices[0].message.content.strip()
        title = title.replace('"', '').replace('"', '').replace('"', '').replace('《', '').replace('》', '').replace('。', '')
        
        if title and len(title) <= 15:
            conversation_store.update_title(conversation_id, title)
            print(f"[Title] Generated: {title}")
    except Exception as e:
        print(f"[Title] Generation failed: {e}")
        logger.error(f"Title generation failed: {e}")


def run_graph_in_thread(input_state: Dict[str, Any], config: Dict[str, Any], q: queue.Queue, stop_event: threading.Event, result_container: Dict[str, Any]):
    """
    子线程任务：运行 LangGraph 并监控状态变化
    """
    try:
        current_state = input_state.copy()
        final_state = input_state.copy()
        initial_retry_count = input_state.get("retry_count", 0)
        last_retry_count = initial_retry_count
        retrieval_done_signaled = False

        for output in app_graph.stream(input_state, config=config, stream_mode="updates"):
            for node_name, state_update in output.items():
                final_state.update(state_update)
                
                if node_name == "router_agent":
                    q.put({"type": "thinking", "content": "正在分析您的问题意图..."})
                elif node_name == "memory_agent":
                    q.put({"type": "thinking", "content": "正在回顾历史对话上下文..."})
                elif node_name == "theory_retriever_agent":
                    q.put({"type": "thinking", "content": "正在检索马克思主义理论文库..."})
                elif node_name == "politics_retriever_agent":
                    q.put({"type": "thinking", "content": "正在查阅最新时政文献..."})

                if not retrieval_done_signaled:
                    theory_docs = final_state.get("theory_docs", [])
                    politics_docs = final_state.get("politics_docs", [])
                    retrieve_strategy = final_state.get("retrieve_strategy", "")
                    retrieval_ready = (
                        retrieve_strategy == "no_retrieve" or
                        (retrieve_strategy == "theory_only" and theory_docs) or
                        (retrieve_strategy == "politics_only" and politics_docs) or
                        (retrieve_strategy == "hybrid" and theory_docs and politics_docs)
                    )
                    if retrieval_ready:
                        retrieval_done_signaled = True
                        try:
                            from src.reference_composer import deduplicate_references
                            raw_refs = []
                            for doc in theory_docs:
                                if "reference" in doc:
                                    ref = doc["reference"].copy()
                                    ref["score"] = ref.get("score", 0)
                                    raw_refs.append(ref)
                            for doc in politics_docs:
                                if "reference" in doc:
                                    ref = doc["reference"].copy()
                                    ref["score"] = ref.get("score", 0)
                                    raw_refs.append(ref)
                            merged = deduplicate_references(raw_refs)
                            result_container["phase1_refs"] = merged
                            print(f"[Phase1] Dedup done: {len(merged)} refs")
                        except Exception as e:
                            print(f"[Phase1] Failed: {e}")
                            result_container["phase1_refs"] = []

                current_retry_count = state_update.get("retry_count", last_retry_count)
                if current_retry_count > last_retry_count:
                    logger.info(f"Retry detected: {last_retry_count} -> {current_retry_count}. Sending clear signal.")
                    q.put({"type": "clear"})
                    q.put({"type": "thinking", "content": "审核未通过，正在根据修改意见重新生成..."})
                    last_retry_count = current_retry_count

        result_container['final_state'] = final_state

    except Exception as e:
        logger.error(f"Graph execution failed: {e}", exc_info=True)
        result_container['error'] = str(e)
    finally:
        stop_event.set()


def chat_service_stream(conversation_id: str, user_query: str) -> Generator[str, None, None]:
    """
    流式对话服务核心函数
    """
    if not conversation_id:
        conversation_id = conversation_store.create_conversation()
    
    conv = conversation_store.get_conversation(conversation_id)
    if not conv:
        conversation_id = conversation_store.create_conversation()
        conv = conversation_store.get_conversation(conversation_id)

    conversation_store.add_message(conversation_id, "user", user_query)

    initial_state = {
        "current_query": user_query,
        "user_query": user_query,
        "conversation_id": conversation_id,
        "turn_id": conv.turn_id,
        "retry_count": 0,
        "is_terminated": False
    }

    if conv.turn_id > 1:
        initial_state["conversation_summary"] = conversation_store.get_conversation_summary(conversation_id)
        initial_state["dialogue_history"] = conversation_store.get_recent_messages_dict(conversation_id, max_count=10)
        if conv.evidence_cache:
            initial_state["theory_docs"] = conv.evidence_cache.theory_docs
            initial_state["politics_docs"] = conv.evidence_cache.moment_docs

    msg_queue = queue.Queue()
    stop_event = threading.Event()
    result_container = {}
    callback = StreamingQueueCallbackHandler(msg_queue, stop_event)

    run_config = {
        "callbacks": [callback],
        "recursion_limit": 25
    }

    thread = threading.Thread(
        target=run_graph_in_thread,
        args=(initial_state, run_config, msg_queue, stop_event, result_container)
    )
    thread.start()

    yield f"data: {json.dumps({'type': 'meta', 'conversation_id': conversation_id})}\n\n"
    yield f"data: {json.dumps({'type': 'thinking', 'content': 'AI正在启动思维链...'})}\n\n"

    while not stop_event.is_set() or not msg_queue.empty():
        try:
            event = msg_queue.get(timeout=0.05)
            if isinstance(event, dict):
                yield f"data: {json.dumps(event)}\n\n"
        except queue.Empty:
            continue
    
    thread.join()

    if 'error' in result_container:
        yield f"data: {json.dumps({'type': 'error', 'content': result_container['error']})}\n\n"
        
    elif 'final_state' in result_container:
        final_state = result_container['final_state']
        final_ans = final_state.get("generated_answer", "")
        
        if not final_ans:
            final_ans = "抱歉，由于某种原因我无法生成有效的回复。"

        conversation_store.add_message(conversation_id, "assistant", final_ans)
        
        try:
            from src.reference_composer import deduplicate_references, highlight_references_parallel

            merged = result_container.get("phase1_refs")

            if merged is None:
                raw_references = []
                for doc in final_state.get("theory_docs", []):
                    if "reference" in doc:
                        ref = doc["reference"].copy()
                        ref["score"] = ref.get("score", 0)
                        raw_references.append(ref)
                for doc in final_state.get("politics_docs", []):
                    if "reference" in doc:
                        ref = doc["reference"].copy()
                        ref["score"] = ref.get("score", 0)
                        raw_references.append(ref)
                merged = deduplicate_references(raw_references)

            if merged:
                base_refs = []
                for ref in merged:
                    r = ref.copy()
                    r["score"] = round(r.get("score", 0) * 100)
                    r["highlights"] = []
                    base_refs.append(r)
                yield f"data: {json.dumps({'type': 'references', 'data': base_refs}, ensure_ascii=False)}\n\n"

                def _run_phase2(merged_refs, answer, msg_queue):
                    try:
                        highlighted = highlight_references_parallel(merged_refs, answer)
                        highlights_update = [
                            {"ref_index": i, "highlights": ref.get("highlights", [])}
                            for i, ref in enumerate(highlighted)
                        ]
                        msg_queue.put({"type": "references_highlight", "data": highlights_update})
                    except Exception as e:
                        print(f"[Phase2] Highlight failed: {e}")

                phase2_thread = threading.Thread(
                    target=_run_phase2,
                    args=(merged, final_ans, msg_queue),
                    daemon=True
                )
                phase2_thread.start()

        except Exception as ref_err:
            print(f"[Service] Reference compose failed (non-fatal): {ref_err}")
        
        latest_conv = conversation_store.get_conversation(conversation_id)
        should_gen_title = False
        
        if latest_conv:
            if not latest_conv.title or len(latest_conv.title.strip()) == 0:
                should_gen_title = True
            elif len(latest_conv.title) > 15:
                should_gen_title = True

        if should_gen_title:
            title_thread = threading.Thread(
                target=_generate_smart_title_async,
                args=(conversation_id, user_query, final_ans),
                daemon=True
            )
            title_thread.start()
        
        if conv.turn_id == 1 and "extracted_keywords" in final_state:
            conversation_store.update_topic_keywords(conversation_id, final_state["extracted_keywords"])
        
        chips = []
        if final_state.get("theory_docs"):
            chips.append("查看相关理论原文")
        if final_state.get("politics_docs"):
            chips.append("更多时政案例")
        chips.append("我对这个回答有疑问")

        yield f"data: {json.dumps({'type': 'done', 'chips': chips, 'final_answer': final_ans}, ensure_ascii=False)}\n\n"
    
    else:
        yield f"data: {json.dumps({'type': 'error', 'content': '未知系统错误：流程异常终止'})}\n\n"
