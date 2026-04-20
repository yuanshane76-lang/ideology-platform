from __future__ import annotations

import re
from typing import Any, Dict, List


def extract_concept_placeholders(structured_book: Dict[str, Any]) -> Dict[str, Any]:
    blocks = structured_book.get('blocks', [])
    concepts = structured_book.get('concepts', [])

    # 从 enrichment 数据中提取概念（如果有）
    # 如果 enrichment 已执行，concepts 列表会包含真实概念数据
    # 否则仅透传 concepts.json 中的原始定义
    enriched_concepts = _enrich_concepts_from_blocks(blocks, concepts)

    return {
        'book_id': structured_book.get('book', {}).get('id'),
        'status': 'enriched' if enriched_concepts != concepts else 'placeholder',
        'extractor': 'concept-extraction-v2',
        'concept_catalog': enriched_concepts,
        'block_concept_refs': [
            {
                'block_id': block['id'],
                'concept_refs': block.get('concept_refs', []),
            }
            for block in blocks
        ],
    }


def _enrich_concepts_from_blocks(
    blocks: List[Dict[str, Any]],
    original_concepts: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """从 block 的 concept_refs 推断概念目录。

    如果原始 concepts 已有内容（来自 concepts.json 或 enrichment），
    则直接返回；否则从 block 引用中提取去重的概念列表。
    """
    if original_concepts:
        return original_concepts

    # 从 blocks 中收集所有被引用的 concept_id
    seen_ids = set()
    enriched = []
    for block in blocks:
        for concept_ref in block.get('concept_refs', []):
            if concept_ref in seen_ids:
                continue
            seen_ids.add(concept_ref)
            enriched.append({
                'id': concept_ref,
                'name': _concept_id_to_name(concept_ref),
                'aliases': [],
                'short_description': f'从教材内容中提取的核心概念。',
            })
    return enriched


def _concept_id_to_name(concept_id: str) -> str:
    """尝试从 concept_id 推断概念名称。"""
    # 去掉常见前缀
    name = re.sub(r'^(concept-|enriched-concept-|block-concept:|derived-concept:)', '', concept_id)
    # 去掉 block 后缀
    name = re.sub(r':b\d+$', '', name)
    # 将连字符替换为空格
    name = name.replace('-', ' ').strip()
    return name if name else concept_id
