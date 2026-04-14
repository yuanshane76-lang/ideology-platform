# src/reference_composer.py
"""
引用文献整合器 - 优化版
优化：
1. 移除不必要的 AI 清理步骤（原文通常已经足够干净）
2. 简化高亮识别逻辑
3. 减少并发 API 调用数量
"""

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict
from threading import Semaphore

from .clients import openai_client
from .config import settings

logger = logging.getLogger(__name__)

_api_semaphore = Semaphore(4)


def _get_theory_group_key(ref: Dict) -> str:
    source = ref.get("source", "")
    chapter = ref.get("chapter", "") or ""
    section = ref.get("section", "") or ""
    subsection = ref.get("subsection", "") or ""
    subsubsection = ref.get("subsubsection", "") or ""
    if subsubsection:
        return f"{source}||{chapter}||{section}||{subsection}||{subsubsection}"
    elif subsection:
        return f"{source}||{chapter}||{section}||{subsection}"
    elif section:
        return f"{source}||{chapter}||{section}"
    elif chapter:
        return f"{source}||{chapter}"
    return source


def _merge_theory_chunks(refs: List[Dict]) -> Dict:
    refs_sorted = sorted(refs, key=lambda x: x.get("score", 0), reverse=True)
    best = refs_sorted[0].copy()
    seen = set()
    full_parts = []
    for r in refs_sorted:
        chunk = (r.get("full_content") or r.get("content", "")).strip()
        if chunk and chunk not in seen:
            seen.add(chunk)
            full_parts.append(chunk)
    best["full_content"] = "\n\n".join(full_parts)
    best["chunk_count"] = len(refs)
    best["highlights"] = []
    return best


def _merge_moment_chunks(refs: List[Dict]) -> Dict:
    refs_sorted = sorted(refs, key=lambda x: x.get("score", 0), reverse=True)
    best = refs_sorted[0].copy()
    all_contents = [
        (r.get("full_content") or r.get("content", ""))
        for r in refs_sorted
        if (r.get("full_content") or r.get("content"))
    ]
    best["full_content"] = max(all_contents, key=len) if all_contents else best.get("content", "")
    best["chunk_count"] = len(refs)
    best["highlights"] = []
    return best


def deduplicate_references(raw_refs: List[Dict]) -> List[Dict]:
    """去重合并（纯内存操作）"""
    theory_groups: Dict[str, List[Dict]] = {}
    moment_groups: Dict[str, List[Dict]] = {}
    for ref in raw_refs:
        if ref.get("type") == "theory":
            key = _get_theory_group_key(ref)
            theory_groups.setdefault(key, []).append(ref)
        elif ref.get("type") == "moment":
            title = ref.get("title", "")
            moment_groups.setdefault(title, []).append(ref)
    merged = []
    for group in theory_groups.values():
        merged.append(_merge_theory_chunks(group))
    for group in moment_groups.values():
        merged.append(_merge_moment_chunks(group))
    merged.sort(key=lambda x: x.get("score", 0), reverse=True)
    return merged


def clean_references_parallel(merged: List[Dict]) -> List[Dict]:
    """
    优化：跳过 AI 清理步骤，直接返回
    原文通常已经足够干净，AI 清理增加延迟但收益有限
    """
    return merged


def _highlight_single_ref(idx: int, ref: Dict, ai_answer: str) -> Dict:
    """对单条引用识别高亮片段（简化版）"""
    with _api_semaphore:
        content_sample = ref.get("full_content", ref.get("content", ""))[:400]

        prompt = f"""找出 AI 回答中来自参考资料的片段。

参考资料：{content_sample}

AI 回答：{ai_answer[:600]}

返回 JSON：{{"highlights": ["片段1", "片段2"]}}（若无则空列表）"""

        try:
            response = openai_client.chat.completions.create(
                model=settings.fast_model,
                messages=[
                    {"role": "system", "content": "你是文本分析助手，只返回 JSON。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                stream=False,
                timeout=15
            )
            raw = response.choices[0].message.content or ""
            raw = raw.replace("```json", "").replace("```", "").strip()
            result = json.loads(raw)
            return {"ref_index": idx, "highlights": result.get("highlights", [])}
        except Exception as e:
            logger.warning(f"[Composer] highlight ref[{idx}] failed: {e}")
            return {"ref_index": idx, "highlights": []}


def highlight_references_parallel(merged: List[Dict], ai_answer: str) -> List[Dict]:
    """
    阶段二：并发识别高亮（限制并发数）
    """
    if not merged:
        return merged

    max_workers = min(len(merged), 4)
    results = [None] * len(merged)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_idx = {
            executor.submit(_highlight_single_ref, idx, ref, ai_answer): idx
            for idx, ref in enumerate(merged)
        }
        for future in as_completed(future_to_idx):
            try:
                result = future.result(timeout=10)
                results[result["ref_index"]] = result
            except Exception as e:
                idx = future_to_idx[future]
                logger.warning(f"[Composer] parallel highlight task[{idx}] failed: {e}")
                results[idx] = {"ref_index": idx, "highlights": []}

    for i, ref in enumerate(merged):
        ref["highlights"] = (results[i] or {}).get("highlights", [])

    return merged


def compose_references(raw_refs: List[Dict], ai_answer: str) -> List[Dict]:
    """兼容旧调用"""
    if not raw_refs:
        return []
    merged = deduplicate_references(raw_refs)
    merged = clean_references_parallel(merged)
    merged = highlight_references_parallel(merged, ai_answer)
    return merged
