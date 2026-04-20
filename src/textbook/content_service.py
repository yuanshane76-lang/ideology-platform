from __future__ import annotations

import json
import re
import urllib.parse
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.textbook.book_registry_service import get_book_registry, list_registered_books
from src.textbook.companion_context_service import build_companion_context
from src.textbook.explanation_service import (
    ACTION_PROMPTS,
    generate_companion_followup_text,
    generate_companion_text,
)
from src.textbook.llm_enrichment_service import enrich_block


COMPANION_ACTIONS = {'explain', 'ask', 'note'}
KEYWORD_PATTERNS = [
    '中国特色社会主义', '中国式现代化', '中华民族伟大复兴', '社会主义核心价值观',
    '理想信念', '人生观', '价值观', '爱国主义', '改革创新', '道德规范',
    '法治思维', '宪法', '全面依法治国', '中国精神',
]

# 不合格概念黑名单：这些词不应作为知识星图中的概念节点
_BLACKLIST_CONCEPTS = {
    'core', 'concept', 'chapter', 'section', 'block', 'intro',
    '未命名章', '导言', '正文', '第一节', '第二节', '第三节', '第四节',
    '第一章', '第二章', '第三章', '第四章', '第五章', '第六章', '第七章',
    '绪论', '13s', '17s',
}

MAX_CONCEPT_ENTRIES = 24
MAX_GRAPH_CONCEPTS = 24


@lru_cache(maxsize=8)
def _load_enrichment_data(book_id: str) -> Dict[str, Any]:
    book = get_book_registry(book_id)
    if not book:
        return {}

    processed_path = book.get('processed_absolute_path')
    if not processed_path:
        return {}

    enrichment_path = Path(processed_path).parent / 'enrichment.json'
    if not enrichment_path.exists():
        return {}

    try:
        with enrichment_path.open('r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def _safe_term_id(term: str) -> str:
    normalized = re.sub(r'\s+', '-', term.strip())
    normalized = re.sub(r'[^\w\-\u4e00-\u9fff]', '-', normalized)
    normalized = re.sub(r'-+', '-', normalized).strip('-')
    return normalized or 'item'


def _build_enrichment_indexes(book_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    enrichment = _load_enrichment_data(book_id)
    section_results = enrichment.get('sections', {}) if isinstance(enrichment, dict) else {}

    section_enrichment: Dict[str, Dict[str, Any]] = {}
    concepts: Dict[str, Dict[str, Any]] = {item['id']: dict(item) for item in data.get('concepts', [])}
    keywords: Dict[str, Dict[str, Any]] = {item['id']: dict(item) for item in data.get('keywords', [])}
    block_concepts: Dict[str, List[str]] = {}
    block_keywords: Dict[str, List[str]] = {}

    for section in data.get('sections', []):
        section_id = section['id']
        raw = section_results.get(section_id, {}) if isinstance(section_results, dict) else {}
        section_keywords = []
        section_concepts = []

        for term in raw.get('keywords', []):
            cleaned = str(term or '').strip()
            if not cleaned:
                continue
            keyword_id = f"enriched-keyword:{_safe_term_id(cleaned)}"
            keywords.setdefault(keyword_id, {'id': keyword_id, 'term': cleaned})
            section_keywords.append({'id': keyword_id, 'term': cleaned})

        for item in raw.get('concepts', []):
            if not isinstance(item, dict):
                continue
            name = str(item.get('name', '') or '').strip()
            description = str(item.get('description', '') or '').strip()
            if not name:
                continue
            concept_id = f"enriched-concept:{_safe_term_id(name)}"
            concepts.setdefault(
                concept_id,
                {
                    'id': concept_id,
                    'name': name,
                    'short_description': description or name,
                },
            )
            section_concepts.append(
                {
                    'id': concept_id,
                    'name': name,
                    'shortDescription': description or name,
                }
            )

        summary = str(raw.get('summary', '') or '').strip()
        section_enrichment[section_id] = {
            'summary': summary,
            'keywords': section_keywords,
            'concepts': section_concepts,
            'source': raw.get('source', ''),
        }

        for block_id in section.get('blockIds', []):
            block_concepts[block_id] = [item['id'] for item in section_concepts]
            block_keywords[block_id] = [item['id'] for item in section_keywords]

    return {
        'section_enrichment': section_enrichment,
        'concepts': concepts,
        'keywords': keywords,
        'block_concepts': block_concepts,
        'block_keywords': block_keywords,
        'has_enrichment': any(section_enrichment.values()),
    }


def get_homepage_sections() -> List[Dict[str, str]]:
    books = list_registered_books(include_disabled=False)
    default_book_id = books[0]['book_id'] if books else ''

    return [
        {
            'title': '教材阅读',
            'description': '进入教材正文阅读页，按章节浏览、定位重点段落，并配合伴读辅助区完成理解。',
            'icon': 'book-open',
            'badge': '核心入口',
        },
        {
            'title': '教材知识结构',
            'description': '从章节、概念与关系三个入口理解教材结构，作为后续知识图谱的轻量入口页。',
            'icon': 'network',
            'badge': '结构入口',
        },
    ]


@lru_cache(maxsize=8)
def load_book_data(book_id: str) -> Dict[str, Any]:
    book = get_book_registry(book_id)
    if not book:
        raise KeyError(f'Unknown book_id: {book_id}')

    processed_path = book.get('processed_absolute_path')
    if processed_path and Path(processed_path).exists():
        with Path(processed_path).open('r', encoding='utf-8') as f:
            return json.load(f)

    return {
        'book': {
            'id': book_id,
            'title': book.get('title', book_id),
            'subtitle': book.get('subtitle', ''),
            'description': book.get('description', ''),
            'subject': book.get('subject', ''),
            'version': book.get('version', ''),
            'source_type': book.get('source_type', 'unknown'),
        },
        'concepts': [],
        'keywords': [],
        'chapters': [],
        'sections': [],
        'blocks': [],
        'empty_state': {
            'title': '当前教材尚未生成结构化内容',
            'description': '请先完成 Markdown 解析并生成 processed 结果，阅读器会自动切换到真实内容链路。',
        },
    }


@lru_cache(maxsize=8)
def _build_book_indexes(book_id: str) -> Dict[str, Any]:
    data = load_book_data(book_id)
    enrichment_indexes = _build_enrichment_indexes(book_id, data)
    chapters = {item['id']: item for item in _normalize_chapters(data.get('chapters', []))}
    sections = {item['id']: item for item in data.get('sections', [])}
    blocks = {item['id']: item for item in data.get('blocks', [])}
    concepts = enrichment_indexes['concepts']
    keywords = enrichment_indexes['keywords']
    return {
        'data': data,
        'chapters': chapters,
        'sections': sections,
        'blocks': blocks,
        'concepts': concepts,
        'keywords': keywords,
        'section_enrichment': enrichment_indexes['section_enrichment'],
        'block_concepts': enrichment_indexes['block_concepts'],
        'block_keywords': enrichment_indexes['block_keywords'],
        'has_enrichment': enrichment_indexes['has_enrichment'],
    }


def _book_title(data: Dict[str, Any]) -> str:
    book = data.get('book', {})
    return book.get('title') or book.get('id', '')


def _normalize_chapters(chapters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    ordered = sorted(
        [dict(item) for item in chapters],
        key=lambda item: (item.get('order', 0), item.get('id', '')),
    )
    for index, chapter in enumerate(ordered, start=1):
        chapter['order'] = index
    return ordered


def _reader_href(book_id: str, chapter_id: Optional[str] = None, anchor: str = '') -> str:
    params = {'book_id': book_id}
    if chapter_id:
        params['chapter_id'] = chapter_id
    href = f"/reader?{urllib.parse.urlencode(params)}"
    if anchor:
        href += f"#{urllib.parse.quote(anchor, safe='')}"
    return href


def _clean_topic_label(title: str) -> str:
    cleaned = re.sub(r'^第[一二三四五六七八九十百]+[章节]\s*', '', title or '')
    cleaned = cleaned.replace('导言', '').replace('（', '').replace('）', '').strip(' ：:、，。')
    return re.sub(r'\s+', ' ', cleaned).strip()


def _enrich_block(
    block: Dict[str, Any],
    chapters: Dict[str, Any],
    sections: Dict[str, Any],
    concepts: Dict[str, Any],
    keywords: Dict[str, Any],
    section_enrichment: Dict[str, Any],
    block_concepts: Dict[str, List[str]],
    block_keywords: Dict[str, List[str]],
    book_title: str = '',
) -> Dict[str, Any]:
    enriched = dict(block)
    chapter = chapters[block['chapter_id']]
    section = sections[block['section_id']]
    section_meta = section_enrichment.get(block['section_id'], {})
    concept_ids = block_concepts.get(block['id']) or block.get('concept_refs', [])
    keyword_ids = block_keywords.get(block['id']) or block.get('keyword_refs', [])
    enriched['title'] = section['title']
    enriched['chapterId'] = block['chapter_id']
    enriched['sectionId'] = block['section_id']
    enriched['chapterOrder'] = chapter['order']
    enriched['sectionOrder'] = section['order']
    enriched['chapter_order'] = chapter['order']
    enriched['section_order'] = block.get('order', 0)
    enriched['chapterTitle'] = chapter['title']
    enriched['sectionTitle'] = section['title']
    enriched['text'] = block['clean_text']
    enriched['sectionSummary'] = section_meta.get('summary', '') or section.get('summary', '')
    enriched['relatedConcepts'] = [
        {
            'id': concept_id,
            'name': concepts[concept_id].get('name', ''),
            'shortDescription': concepts[concept_id].get('short_description', concepts[concept_id].get('name', '')),
        }
        for concept_id in concept_ids
        if concept_id in concepts
    ]
    enriched['relatedKeywords'] = [
        {
            'id': keyword_id,
            'term': keywords[keyword_id].get('term', ''),
        }
        for keyword_id in keyword_ids
        if keyword_id in keywords
    ]

    if not enriched['relatedConcepts'] or not enriched['relatedKeywords']:
        block_enrichment = enrich_block(
            book_title=book_title,
            chapter_title=chapter.get('title', ''),
            section_title=section.get('title', ''),
            block_text=block.get('clean_text', ''),
        )
        if not enriched['relatedConcepts']:
            enriched['relatedConcepts'] = [
                {
                    'id': f"block-concept:{block['id']}:{_safe_term_id(item.get('name', ''))}",
                    'name': item.get('name', ''),
                    'shortDescription': item.get('description', item.get('name', '')),
                }
                for item in block_enrichment.get('concepts', [])
                if item.get('name')
            ]
        if not enriched['relatedKeywords']:
            enriched['relatedKeywords'] = [
                {
                    'id': f"block-keyword:{block['id']}:{_safe_term_id(term)}",
                    'term': term,
                }
                for term in block_enrichment.get('keywords', [])
                if term
            ]
    return enriched


def _build_toc(chapters: Dict[str, Any], sections: Dict[str, Any], current_chapter_id: Optional[str], book_id: str = '', section_enrichment: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    toc = []
    section_enrichment = section_enrichment or {}
    ordered_chapters = sorted(chapters.values(), key=lambda item: item['order'])
    for chapter in ordered_chapters:
        chapter_section_ids = chapter.get('sectionIds', [])
        chapter_sections = []
        for index, section_id in enumerate(chapter_section_ids):
            section = sections[section_id]
            enriched_section = section_enrichment.get(section_id, {})
            chapter_sections.append(
                {
                    'id': section['id'],
                    'anchor': section['anchor'],
                    'href': f"#{section['anchor']}",
                    'title': section['title'],
                    'summary': enriched_section.get('summary', '') or section.get('summary', ''),
                    'active': chapter['id'] == current_chapter_id and index == 0,
                }
            )
        toc.append(
            {
                'id': chapter['id'],
                'anchor': chapter['anchor'],
                'title': chapter['title'],
                'href': f"#{chapter['anchor']}",
                'summary': chapter.get('summary', ''),
                'active': chapter['id'] == current_chapter_id,
                'sections': chapter_sections,
            }
        )
    return toc


def _extract_keywords(section_title: str, block_text: str, keyword_contexts: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    keywords: List[Dict[str, str]] = []
    for item in keyword_contexts:
        label = item.get('term') or item.get('label') or ''
        if label:
            keywords.append({'id': item.get('id', f'kw-{label}'), 'term': label})

    title_keywords = re.sub(r'^第[一二三四五六七八九十]+节\s*', '', section_title)
    if title_keywords and len(title_keywords) > 2:
        for kw in re.split(r'[、，。：]', title_keywords):
            kw = kw.strip()
            if 2 <= len(kw) <= 8 and not any(item['term'] == kw for item in keywords):
                keywords.append({'id': f'kw-{kw}', 'term': kw})

    if block_text and len(keywords) < 6:
        for pattern in KEYWORD_PATTERNS:
            if pattern in block_text and not any(item['term'] == pattern for item in keywords):
                keywords.append({'id': f'kw-{pattern}', 'term': pattern})
            if len(keywords) >= 6:
                break

    return keywords


def get_book_cards() -> List[Dict[str, Any]]:
    cards = []
    for book in list_registered_books(include_disabled=True):
        cards.append(
            {
                'book_id': book['book_id'],
                'title': book['title'],
                'subtitle': book['subtitle'],
                'description': book['description'],
                'subject': book['subject'],
                'version': book['version'],
                'enabled': book['enabled'],
                'ingest_status': book['ingest_status'],
                'visibility': book['visibility'],
                'source_type': book['source_type'],
            }
        )
    return cards


def get_reader_page_data(book_id: str, chapter_id: Optional[str] = None) -> Dict[str, Any]:
    registry_book = get_book_registry(book_id)
    if not registry_book:
        raise KeyError(f'Unknown book_id: {book_id}')

    indexes = _build_book_indexes(book_id)
    data = indexes['data']
    chapters = indexes['chapters']
    sections = indexes['sections']
    blocks = indexes['blocks']
    concepts = indexes['concepts']
    keywords = indexes['keywords']
    section_enrichment = indexes['section_enrichment']
    block_concepts = indexes['block_concepts']
    block_keywords = indexes['block_keywords']

    ordered_chapters = sorted(chapters.values(), key=lambda item: item['order'])
    has_structured_content = bool(ordered_chapters and sections and blocks)

    if not has_structured_content:
        return {
            'book_id': book_id,
            'book': data['book'],
            'book_registry': registry_book,
            'has_structured_content': False,
            'empty_state': data.get('empty_state')
            or {
                'title': '当前教材暂无可读内容',
                'description': '尚未检测到结构化结果，请先完成解析后再进入阅读器。',
            },
            'chapter': None,
            'current_section': None,
            'toc': [],
            'section_groups': [],
            'blocks': [],
            'companion_initial': {
                'bookId': book_id,
                'blockId': '',
                'action': '',
                'availableActions': ['explain', 'ask', 'note'],
                'resultType': 'empty',
                'resultText': '请先点击左侧正文中的一个段落，再选择右侧动作按钮。',
                'resultItems': [],
                'chapterTitle': '暂无章节',
                'sectionTitle': '暂无小节',
                'blockTitle': '',
                'sectionSummary': '请先生成教材解析结果。',
                'chapterSummary': '阅读器已切换到结构化链路，但当前教材尚未完成 processed 产物。',
                'relatedConcepts': [],
                'relatedKeywords': [],
                'context': {'selectedText': '', 'neighborBlocks': []},
                'meta': {'source': 'empty', 'model': '', 'fallbackUsed': False, 'fallbackReason': ''},
            },
        }

    for chapter in ordered_chapters:
        chapter['book_id'] = book_id

    if chapter_id and chapter_id in chapters:
        current_chapter = chapters[chapter_id]
    else:
        current_chapter = ordered_chapters[0]
    current_section = sections[current_chapter['sectionIds'][0]]
    current_block = _enrich_block(
        blocks[current_section['blockIds'][0]],
        chapters,
        sections,
        concepts,
        keywords,
        section_enrichment,
        block_concepts,
        block_keywords,
        book_title=_book_title(data),
    )
    section_groups = []
    all_blocks = []

    for section_id in current_chapter.get('sectionIds', []):
        section = sections[section_id]
        section_blocks = []
        for block_id in section.get('blockIds', []):
            if block_id not in blocks:
                continue
            enriched_block = _enrich_block(
                blocks[block_id],
                chapters,
                sections,
                concepts,
                keywords,
                section_enrichment,
                block_concepts,
                block_keywords,
                book_title=_book_title(data),
            )
            section_blocks.append(enriched_block)
            all_blocks.append(enriched_block)
        section_groups.append(
            {
                'id': section['id'],
                'title': section['title'],
                'summary': section_enrichment.get(section['id'], {}).get('summary', '') or section.get('summary', ''),
                'anchor': section['anchor'],
                'blocks': section_blocks,
            }
        )

    companion_initial = build_companion_payload(book_id, current_block['id'], action='')

    return {
        'book_id': book_id,
        'book': data['book'],
        'book_registry': registry_book,
        'has_structured_content': True,
        'empty_state': None,
        'chapter': current_chapter,
        'current_section': current_section,
        'toc': _build_toc(chapters, sections, current_chapter['id'], book_id, section_enrichment=section_enrichment),
        'section_groups': section_groups,
        'blocks': all_blocks,
        'companion_initial': companion_initial,
    }


def build_companion_payload(
    book_id: str,
    block_id: str,
    action: str = "",
    selected_text: str = "",
) -> Dict[str, Any]:
    indexes = _build_book_indexes(book_id)
    data = indexes["data"]
    chapters = indexes["chapters"]
    sections = indexes["sections"]
    blocks = indexes["blocks"]
    concepts = indexes["concepts"]
    keywords = indexes["keywords"]
    section_enrichment = indexes["section_enrichment"]
    block_concepts = indexes["block_concepts"]
    block_keywords = indexes["block_keywords"]

    if block_id not in blocks:
        raise KeyError(f"Unknown block_id: {block_id}")

    action_aliases = {
        "解释这段": "explain",
        "基于这段提问": "ask",
        "生成笔记": "note",
        "question": "ask",
        "qa": "ask",
    }
    raw_action = (action or "").strip().lower()
    normalized_action = action_aliases.get(raw_action, raw_action)
    should_generate = normalized_action in COMPANION_ACTIONS

    current_block = _enrich_block(
        blocks[block_id],
        chapters,
        sections,
        concepts,
        keywords,
        section_enrichment,
        block_concepts,
        block_keywords,
        book_title=_book_title(data),
    )
    context = build_companion_context(data, block_id, selected_text=selected_text)

    result = {
        "type": "empty",
        "text": "请点击「解释这段」「基于这段提问」或「生成笔记」来触发伴读。",
        "items": [],
        "source": "empty",
        "model": "",
    }
    if should_generate:
        result = generate_companion_text(normalized_action, context)

    related_concepts = current_block.get("relatedConcepts") or [
        {
            "id": item["id"],
            "name": item.get("name") or item.get("label", ""),
            "shortDescription": item.get("short_description", item.get("name", "")),
        }
        for item in context.get("concept_contexts", [])
    ]
    related_keywords = current_block.get("relatedKeywords") or _extract_keywords(
        context["section_context"].get("title", ""),
        context["current_block"].get("clean_text", ""),
        context.get("keyword_contexts", []),
    )

    return {
        "bookId": book_id,
        "blockId": context["current_block"]["id"],
        "action": normalized_action,
        "availableActions": ["explain", "ask", "note"],
        "chapterTitle": context["chapter_context"]["title"],
        "sectionTitle": context["section_context"]["title"],
        "blockTitle": context["current_block"]["anchor"],
        "resultType": result["type"],
        "resultText": result["text"],
        "resultItems": result.get("items", []),
        "sectionSummary": current_block.get("sectionSummary", "") or context["section_context"].get("summary", ""),
        "chapterSummary": context["chapter_context"].get("summary", ""),
        "relatedConcepts": related_concepts,
        "relatedKeywords": related_keywords,
        "context": {
            "selectedText": context.get("selected_text", ""),
            "neighborBlocks": context.get("neighbor_blocks", []),
            "bookTitle": context.get("book_title", ""),
            "bookId": context.get("book_id", ""),
            "currentBlockText": context["current_block"].get("clean_text", ""),
            "conceptRefs": related_concepts,
            "keywordRefs": related_keywords,
        },
        "meta": {
            "source": result["source"],
            "model": result["model"],
            "fallbackUsed": False,
            "fallbackReason": "",
            "prompt": ACTION_PROMPTS.get(normalized_action, ""),
        },
    }


def _edge_type_count(graph: Dict[str, Any], edge_type: str) -> int:
    return sum(1 for edge in graph.get('edges', []) if edge.get('type') == edge_type)


def _graph_type_counts(graph: Dict[str, Any]) -> Dict[str, int]:
    counts = {'chapter': 0, 'section': 0, 'concept': 0}
    for node in graph.get('nodes', []):
        node_type = node.get('type')
        if node_type in counts:
            counts[node_type] += 1
    return counts


def _build_graph_focus_cards(graph: Dict[str, Any]) -> List[Dict[str, Any]]:
    type_counts = _graph_type_counts(graph)
    return [
        {
            'label': '章节星轨',
            'value': type_counts['chapter'],
            'description': '构成知识星系的一级轨道。',
        },
        {
            'label': '小节节点',
            'value': type_counts['section'],
            'description': '精选小节作为中层知识站点。',
        },
        {
            'label': '概念星体',
            'value': type_counts['concept'],
            'description': '用于展示知识点与可关联概念。',
        },
        {
            'label': '关系引力',
            'value': len(graph.get('edges', [])),
            'description': 'contains / explains / relates_to 三类连接。',
        },
    ]


def _build_graph_legend() -> List[Dict[str, str]]:
    return [
        {'type': 'book', 'label': '核心星核', 'description': '整本教材的视觉中心与总入口。'},
        {'type': 'chapter', 'label': '章节轨道', 'description': '六大主题星区，承担结构骨架。'},
        {'type': 'section', 'label': '小节站点', 'description': '承接章节与概念的中层节点。'},
        {'type': 'concept', 'label': '概念星体', 'description': '适合展示、关联与图谱化的知识概念。'},
    ]


def _build_graph_detail_index(graph: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    node_index = {node['id']: dict(node) for node in graph.get('nodes', [])}
    neighbors: Dict[str, List[str]] = {node_id: [] for node_id in node_index}
    for edge in graph.get('edges', []):
        source = edge.get('source')
        target = edge.get('target')
        if source in neighbors and target in node_index:
            neighbors[source].append(target)
        if target in neighbors and source in node_index:
            neighbors[target].append(source)

    detail_index: Dict[str, Dict[str, Any]] = {}
    for node_id, node in node_index.items():
        linked_nodes = [node_index[ref_id] for ref_id in neighbors.get(node_id, []) if ref_id in node_index][:8]
        detail_index[node_id] = {
            'id': node_id,
            'label': node.get('label', ''),
            'type': node.get('type', ''),
            'description': node.get('description', ''),
            'summary': node.get('summary', ''),
            'chapter': node.get('chapter', ''),
            'href': node.get('href', '#'),
            'ref': node.get('ref', {}),
            'linked_nodes': [
                {
                    'id': item.get('id', ''),
                    'label': item.get('label', ''),
                    'type': item.get('type', ''),
                }
                for item in linked_nodes
            ],
        }
    return detail_index


def _graph_file_path(registry_book: Dict[str, Any]) -> Optional[Path]:
    processed_path = registry_book.get('processed_absolute_path')
    if not processed_path:
        return None
    processed = Path(processed_path)
    return processed.parent / 'graph.json'


def _build_minimal_graph(
    book_id: str,
    chapter_entries: List[Dict[str, Any]],
    concept_entries: List[Dict[str, Any]],
) -> Dict[str, Any]:
    nodes = []
    edges = []
    chapter_lane = []
    section_lane = []
    concept_lane = []

    for chapter in chapter_entries:
        chapter_node_id = f"graph:{chapter['id']}"
        chapter_lane.append(chapter_node_id)
        nodes.append(
            {
                'id': chapter_node_id,
                'label': chapter['title'],
                'type': 'chapter',
                'href': chapter.get('href', '#'),
            }
        )
        for section in chapter.get('sections', []):
            section_node_id = f"graph:{section['id']}"
            section_lane.append(section_node_id)
            nodes.append(
                {
                    'id': section_node_id,
                    'label': section['title'],
                    'type': 'section',
                    'href': section.get('href', '#'),
                }
            )
            edges.append(
                {
                    'id': f"edge:{chapter_node_id}->{section_node_id}",
                    'source': chapter_node_id,
                    'target': section_node_id,
                    'label': 'chapter-section',
                }
            )

    for concept in concept_entries[:MAX_GRAPH_CONCEPTS]:
        concept_node_id = f"graph:{concept['id']}"
        concept_lane.append(concept_node_id)
        nodes.append(
            {
                'id': concept_node_id,
                'label': concept['title'],
                'type': 'concept',
                'href': concept.get('href', '#'),
            }
        )
        if concept.get('sectionId'):
            section_node_id = f"graph:{concept['sectionId']}"
            edges.append(
                {
                    'id': f"edge:{section_node_id}->{concept_node_id}",
                    'source': section_node_id,
                    'target': concept_node_id,
                    'label': 'section-concept',
                }
            )

    return {
        'meta': {
            'source': 'generated',
            'book_id': book_id,
        },
        'nodes': nodes,
        'edges': edges,
        'lanes': {
            'chapters': chapter_lane,
            'sections': section_lane,
            'concepts': concept_lane,
        },
    }


def _load_or_build_graph(
    book_id: str,
    registry_book: Dict[str, Any],
    chapter_entries: List[Dict[str, Any]],
    concept_entries: List[Dict[str, Any]],
) -> Dict[str, Any]:
    graph_path = _graph_file_path(registry_book)
    if graph_path and graph_path.exists():
        try:
            with graph_path.open('r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass

    graph = _build_minimal_graph(book_id, chapter_entries, concept_entries)
    if graph_path:
        graph_path.parent.mkdir(parents=True, exist_ok=True)
        with graph_path.open('w', encoding='utf-8') as f:
            json.dump(graph, f, ensure_ascii=False, indent=2)
    return graph


def _build_chapter_entries(book_id: str, chapters: Dict[str, Any], sections: Dict[str, Any], blocks: Dict[str, Any]) -> List[Dict[str, Any]]:
    entries = []
    for chapter in sorted(chapters.values(), key=lambda item: item['order']):
        chapter_sections = []
        block_total = 0
        for section_id in chapter.get('sectionIds', []):
            section = sections[section_id]
            block_ids = [block_id for block_id in section.get('blockIds', []) if block_id in blocks]
            block_total += len(block_ids)
            chapter_sections.append(
                {
                    'id': section['id'],
                    'title': section['title'],
                    'summary': section.get('summary', '') or f'{len(block_ids)} 个 block',
                    'anchor': section.get('anchor', ''),
                }
            )
        entries.append(
            {
                'id': chapter['id'],
                'title': chapter['title'],
                'description': chapter.get('summary', '') or f"共 {len(chapter_sections)} 个小节，约 {block_total} 个 block",
                'icon': 'book-copy',
                'sections': chapter_sections,
            }
        )
    return entries


def _build_concept_entries(
    book_id: str,
    chapters: Dict[str, Any],
    sections: Dict[str, Any],
    blocks: Dict[str, Any],
    concepts: Dict[str, Any],
    section_enrichment: Optional[Dict[str, Any]] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    section_enrichment = section_enrichment or {}
    entries = []
    concept_bindings: Dict[str, str] = {}
    seen = set()

    for section in sorted(sections.values(), key=lambda item: (chapters[item['chapter_id']]['order'], item['order'])):
        enriched_section = section_enrichment.get(section['id'], {})
        for concept in enriched_section.get('concepts', []):
            concept_id = concept['id']
            concept_name = concept.get('name', '')
            if concept_id in seen:
                continue
            # 过滤黑名单概念
            if concept_name in _BLACKLIST_CONCEPTS:
                continue
            if len(concept_name) < 2:
                continue
            seen.add(concept_id)
            concept_bindings[concept_id] = section['id']
            entries.append(
                {
                    'id': concept_id,
                    'title': concept_name,
                    'description': concept.get('shortDescription', concept_name),
                    'icon': 'lightbulb',
                    'source': 'section-enrichment',
                    'sectionId': section['id'],
                }
            )
            if len(entries) >= MAX_CONCEPT_ENTRIES:
                return entries, concept_bindings

    if concepts:
        for concept in list(concepts.values())[:MAX_CONCEPT_ENTRIES]:
            concept_id = concept['id']
            concept_name = concept.get('name', '')
            if concept_id in seen:
                continue
            if concept_name in _BLACKLIST_CONCEPTS:
                continue
            entries.append(
                {
                    'id': concept_id,
                    'title': concept['name'],
                    'description': concept.get('short_description', concept.get('name', '')),
                    'icon': 'lightbulb',
                    'source': 'concepts',
                    'sectionId': '',
                }
            )
        return entries, concept_bindings

    entries = []
    seen = set()
    bindings: Dict[str, str] = {}

    for section in sorted(sections.values(), key=lambda item: (chapters[item['chapter_id']]['order'], item['order'])):
        topic = _clean_topic_label(section.get('title', ''))
        if not topic or topic in {'导言', '未命名章'} or topic in seen:
            continue
        seen.add(topic)
        chapter = chapters[section['chapter_id']]
        concept_id = f"derived-concept:{section['id']}"
        bindings[concept_id] = section['id']
        entries.append(
            {
                'id': concept_id,
                'title': topic,
                'description': f"派生自 {chapter['title']} / {section['title']}",
                'icon': 'lightbulb',
                'source': 'derived-section-title',
                'sectionId': section['id'],
            }
        )
        if len(entries) >= MAX_CONCEPT_ENTRIES:
            break

    if entries:
        return entries, bindings

    fallback_entries = []
    for block in list(blocks.values())[:8]:
        text = (block.get('clean_text') or '').strip()
        if len(text) < 8:
            continue
        label = text[:14].strip('，。；：,. ')
        fallback_entries.append(
            {
                'id': f"derived-concept:{block['id']}",
                'title': label,
                'description': '派生自正文段落，可作为最小演示概念入口。',
                'icon': 'lightbulb',
                'source': 'derived-block-text',
                'sectionId': block.get('section_id', ''),
            }
        )
    return fallback_entries, {}


def get_knowledge_structure_data(book_id: str) -> Dict[str, Any]:
    registry_book = get_book_registry(book_id)
    if not registry_book:
        raise KeyError(f'Unknown book_id: {book_id}')

    indexes = _build_book_indexes(book_id)
    data = indexes['data']
    chapters = indexes['chapters']
    sections = indexes['sections']
    blocks = indexes['blocks']
    concepts = indexes['concepts']
    section_enrichment = indexes['section_enrichment']

    chapter_entries = _build_chapter_entries(book_id, chapters, sections, blocks)
    concept_entries, _ = _build_concept_entries(book_id, chapters, sections, blocks, concepts, section_enrichment)
    graph = _load_or_build_graph(book_id, registry_book, chapter_entries, concept_entries)
    type_counts = _graph_type_counts(graph)
    detail_index = _build_graph_detail_index(graph)

    return {
        'book_id': book_id,
        'book': data['book'],
        'book_registry': registry_book,
        'graph': graph,
        'graph_path': str(_graph_file_path(registry_book)) if _graph_file_path(registry_book) else '',
        'stats': {
            'chapterCount': type_counts['chapter'],
            'sectionCount': type_counts['section'],
            'conceptCount': type_counts['concept'],
            'edgeCount': len(graph.get('edges', [])),
            'containsCount': _edge_type_count(graph, 'contains'),
            'explainsCount': _edge_type_count(graph, 'explains'),
            'relatesCount': _edge_type_count(graph, 'relates_to'),
        },
        'focus_cards': _build_graph_focus_cards(graph),
        'legend': _build_graph_legend(),
        'detail_index': detail_index,
        'default_node_id': 'book-core',
    }


def generate_companion_chat_reply(
    book_id: str,
    block_id: str,
    question: str,
    selected_text: str = "",
    history: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    indexes = _build_book_indexes(book_id)
    data = indexes["data"]
    chapters = indexes["chapters"]
    sections = indexes["sections"]
    blocks = indexes["blocks"]
    concepts = indexes["concepts"]
    keywords = indexes["keywords"]
    section_enrichment = indexes["section_enrichment"]
    block_concepts = indexes["block_concepts"]
    block_keywords = indexes["block_keywords"]

    normalized_question = (question or "").strip()
    if not normalized_question:
        raise ValueError("question is required")
    if block_id not in blocks:
        raise KeyError(f"Unknown block_id: {block_id}")

    context = build_companion_context(data, block_id, selected_text=selected_text)
    current_block = _enrich_block(
        blocks[block_id],
        chapters,
        sections,
        concepts,
        keywords,
        section_enrichment,
        block_concepts,
        block_keywords,
        book_title=_book_title(data),
    )

    reply_text = generate_companion_followup_text(
        question=normalized_question,
        context=context,
        history=history or [],
    )

    related_concepts = current_block.get("relatedConcepts") or [
        {
            "id": item["id"],
            "name": item.get("name") or item.get("label", ""),
            "shortDescription": item.get("short_description", item.get("name", "")),
        }
        for item in context.get("concept_contexts", [])
    ]
    related_keywords = current_block.get("relatedKeywords") or _extract_keywords(
        context["section_context"].get("title", ""),
        context["current_block"].get("clean_text", ""),
        context.get("keyword_contexts", []),
    )

    return {
        "bookId": book_id,
        "blockId": block_id,
        "question": normalized_question,
        "answer": reply_text,
        "reply": reply_text,
        "chapterTitle": context["chapter_context"].get("title", ""),
        "sectionTitle": context["section_context"].get("title", ""),
        "sectionSummary": current_block.get("sectionSummary", "") or context["section_context"].get("summary", ""),
        "chapterSummary": context["chapter_context"].get("summary", ""),
        "relatedConcepts": related_concepts,
        "relatedKeywords": related_keywords,
        "history": history or [],
        "context": {
            "bookId": context.get("book_id", ""),
            "bookTitle": context.get("book_title", ""),
            "selectedText": context.get("selected_text", ""),
            "currentBlockText": context.get("current_block", {}).get("clean_text", ""),
            "neighborBlocks": context.get("neighbor_blocks", []),
            "conceptContexts": context.get("concept_contexts", []),
            "keywordContexts": context.get("keyword_contexts", []),
        },
        "meta": {
            "source": "external_api",
            "mode": "ask_followup",
        },
    }
