from typing import List, Any, Dict
from .clients import get_qdrant_client
from .embeddings import get_embedding

ALPHA = 1.0
BETA = 0.05
RECALL_K = 15

_qdrant_client = None

def _get_client():
    global _qdrant_client
    if _qdrant_client is None:
        _qdrant_client = get_qdrant_client()
    return _qdrant_client

def calculate_keyword_score(doc_keywords: Any, query_keywords: List[str]) -> float:
    if not doc_keywords or not query_keywords:
        return 0.0

    if isinstance(doc_keywords, list):
        doc_kw_set = {str(k).lower().strip() for k in doc_keywords}
    elif isinstance(doc_keywords, str):
        doc_kw_set = {k.lower().strip() for k in doc_keywords.replace("，", ",").split(",")}
    else:
        doc_kw_set = set()

    match_count = 0
    for q in query_keywords:
        if q.lower().strip() in doc_kw_set:
            match_count += 1
    return match_count * BETA

def search_theory(query: str, keywords: List[str], top_k=3) -> List[Dict]:
    vector = get_embedding(query)
    qdrant_client = _get_client()
    res = qdrant_client.query_points(
        collection_name="theory",
        query=vector,
        limit=RECALL_K,
        with_payload=True
    )

    scored = []
    for p in res.points:
        payload = p.payload or {}
        kw_score = calculate_keyword_score(payload.get("Keywords", []), keywords)
        final_score = (ALPHA * p.score) + kw_score
        scored.append((final_score, p, kw_score))

    scored.sort(key=lambda x: x[0], reverse=True)
    docs = []
    for final_score, p, kw_score in scored[:top_k]:
        payload = p.payload or {}
        context_parts = [
            f"【来源：{payload.get('source', '未知来源')}】",
            f"章节：{payload.get('Chapter', '未知章节')}",
        ]
        for k, label in [("Section","一级标题"),("Subsection","二级标题"),("Subsubsection","三级标题")]:
            v = payload.get(k, "")
            if v:
                context_parts.append(f"{label}：{v}")
        content = payload.get("content_chunk", "")
        if content:
            context_parts.append(f"\n内容：{content}")

        docs.append({
            "content": " | ".join(context_parts),
            "source": "theory",
            "score": final_score,
            "_debug_score": f"Vec:{p.score:.4f} + KwBoost:{kw_score:.2f}",
            "reference": {
                "type": "theory",
                "source": payload.get("source", "未知来源"),
                "chapter": payload.get("Chapter", ""),
                "section": payload.get("Section", ""),
                "subsection": payload.get("Subsection", ""),
                "subsubsection": payload.get("Subsubsection", ""),
                "keywords": payload.get("Keywords", []),
                "content": payload.get("content_chunk", ""),
                "full_content": payload.get("Content", payload.get("content_chunk", "")),
                "score": p.score
            }
        })
    return docs

def search_moment(query: str, keywords: List[str], top_k=3) -> List[Dict]:
    vector = get_embedding(query)
    qdrant_client = _get_client()
    res = qdrant_client.query_points(
        collection_name="moment",
        query=vector,
        limit=RECALL_K,
        with_payload=True
    )

    scored = []
    for p in res.points:
        payload = p.payload or {}
        kw_score = calculate_keyword_score(payload.get("key_words", []), keywords)
        final_score = (ALPHA * p.score) + kw_score
        scored.append((final_score, p, kw_score))

    scored.sort(key=lambda x: x[0], reverse=True)
    docs = []
    for final_score, p, kw_score in scored[:top_k]:
        payload = p.payload or {}
        context = f"【{payload.get('date','')} |{payload.get('source','')}| {payload.get('title','')}】{payload.get('content','')}"
        docs.append({
            "content": context,
            "source": "moment",
            "score": final_score,
            "_debug_score": f"Vec:{p.score:.4f} + KwBoost:{kw_score:.2f}",
            "reference": {
                "type": "moment",
                "title": payload.get("title", "无标题"),
                "date": payload.get("date", ""),
                "source": payload.get("source", "未知来源"),
                "news_type": payload.get("type", ""),
                "keywords": payload.get("key_words", []),
                "content": payload.get("content", ""),
                "score": p.score
            }
        })
    return docs
