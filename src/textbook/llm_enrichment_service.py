from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from src.config import settings

SECTION_ENRICHMENT_PROMPT = """你是思政教材内容增强助手，负责为教材小节生成适合前端直接展示的结构化知识。

任务要求：
1. 你将收到一本教材中的一个 section 标题，以及该 section 下的正文内容。
2. 请仅根据提供文本，提炼该 section 的教材知识点，不要扩写未出现的信息。
3. 输出必须是严格 JSON，对象结构如下：
{
  "keywords": ["关键词1", "关键词2"],
  "concepts": [
    {
      "name": "概念名",
      "description": "一句话解释"
    }
  ],
  "summary": "这一节的简短中文概括"
}

输出限制：
- keywords：3 到 8 个，必须是教材知识点、核心命题、规范表述，不要空泛词。
- concepts：1 到 5 个，每个 concept 都要包含 name 和 description。
- description：必须简短、自然、可展示，避免口号堆砌。
- summary：1 段自然中文，简洁概括本节核心内容。
- 不要输出"学习、内容、理论、章节、知识、教材、意义"等空泛词，除非它们在本节中构成明确知识点，如"理想信念""法治思维"。
- 不要生成与原文无关的政治口号，不要重复同义词，不要凑数。
- concepts 应偏向可展示、可关联、可图谱化的概念节点。
- 如果文本信息有限，也必须输出合法 JSON，但要尽量给出稳妥提炼结果。
- 严禁输出 markdown、解释、前后缀说明，只能输出 JSON。"""

BLOCK_ENRICHMENT_PROMPT = """你是思政教材内容增强助手，负责为教材正文段落生成适合前端直接展示的结构化知识。

任务要求：
1. 你将收到一本教材中的一个正文段落，以及它所在的章节和小节标题。
2. 请仅根据该段文字本身及标题上下文，提炼最相关的概念和关键词，不要扩写未出现的信息。
3. 输出必须是严格 JSON，对象结构如下：
{
  "keywords": ["关键词1", "关键词2"],
  "concepts": [
    {
      "name": "概念名",
      "description": "一句话解释"
    }
  ]
}

输出限制：
- keywords：3 到 5 个。
- concepts：3 到 5 个，每个 concept 都要包含 name 和 description。
- description：必须简短、自然、可展示，适合直接放到伴读辅助区。
- 概念和关键词都必须紧扣当前段落，不要生成空泛词，不要重复同义词。
- 严禁输出 markdown、解释、前后缀说明，只能输出 JSON。"""


_GENERIC_TERMS = {
    '学习', '内容', '理论', '章节', '本节', '教材', '知识', '问题', '要求', '意义', '作用', '方面', '过程', '实践'
}
_DOMAIN_PATTERNS = [
    '人生观', '人生目的', '人生态度', '人生价值', '理想信念', '信仰', '信念', '信心',
    '中国梦', '中国精神', '爱国主义', '改革创新', '社会主义核心价值观', '社会主义道德',
    '道德规范', '道德品格', '法治思想', '法治素养', '法治思维', '依法治国', '全面依法治国',
    '宪法', '尊法学法守法用法', '时代新人', '民族复兴', '价值观', '道德', '法治',
]
_CONCEPT_DESCRIPTIONS = {
    '人生观': '对人生目的、意义和道路的总体看法。',
    '人生目的': '回答人为什么活着以及为何奋斗的根本问题。',
    '人生态度': '个体面对生活境遇和人生实践的基本取向。',
    '人生价值': '衡量个人实践及其社会意义的重要尺度。',
    '理想信念': '指引人生方向并提供精神动力的价值追求。',
    '信仰': '人们对某种价值与道路的深层认同和坚守。',
    '信念': '对目标和价值的稳定确信。',
    '信心': '对发展前景与实践道路的积极确认。',
    '中国梦': '实现中华民族伟大复兴的共同理想。',
    '中国精神': '凝聚民族力量并支撑国家发展的精神标识。',
    '爱国主义': '个人对祖国最深沉的情感与责任担当。',
    '改革创新': '推动社会发展与个人成长的重要动力。',
    '社会主义核心价值观': '当代中国价值体系的高度凝练表达。',
    '社会主义道德': '以人民利益和社会责任为导向的道德体系。',
    '道德规范': '调节社会关系和个人行为的价值准则。',
    '道德品格': '个体稳定的道德品质与行为风貌。',
    '法治思想': '关于法治建设方向、原则和路径的系统认识。',
    '法治素养': '运用法治观念认识和处理问题的综合能力。',
    '法治思维': '按照法治原则分析和解决问题的思维方式。',
    '全面依法治国': '把国家治理各方面纳入法治轨道的基本方略。',
    '宪法': '国家的根本法和治国安邦的总章程。',
    '尊法学法守法用法': '公民提升法治意识和法治能力的基本路径。',
    '时代新人': '担当民族复兴大任的青年群体形象。',
    '民族复兴': '中华民族走向强盛的重要历史进程。',
    '价值观': '人们判断价值取向和行为选择的基本标准。',
    '道德': '调节人与人、人与社会关系的重要行为规范。',
    '法治': '依照法律治理国家和社会的基本方式。',
}

# 用于 enrichment 的模型名
_ENRICHMENT_MODEL = 'qwen-plus-latest'


def build_section_prompt(book_title: str, chapter_title: str, section_title: str, section_text: str) -> str:
    return (
        f"教材名称：{book_title}\n"
        f"章节标题：{chapter_title}\n"
        f"小节标题：{section_title}\n"
        f"小节正文：\n{section_text.strip()}\n"
    )


def build_block_prompt(book_title: str, chapter_title: str, section_title: str, block_text: str) -> str:
    return (
        f"教材名称：{book_title}\n"
        f"章节标题：{chapter_title}\n"
        f"小节标题：{section_title}\n"
        f"正文段落：\n{block_text.strip()}\n"
    )


def _get_enrichment_client():
    """获取 OpenAI 兼容客户端用于 enrichment 调用"""
    from src.clients import openai_client
    return openai_client


def enrich_section(
    book_title: str,
    chapter_title: str,
    section_title: str,
    section_text: str,
) -> Dict[str, Any]:
    prompt = build_section_prompt(book_title, chapter_title, section_title, section_text)
    try:
        api_result = _call_enrichment_api(prompt)
        cleaned = _normalize_enrichment_payload(api_result or {})
        if cleaned['keywords'] or cleaned['concepts'] or cleaned['summary']:
            cleaned['source'] = 'api'
            return cleaned
    except Exception:
        pass

    fallback = _build_fallback_enrichment(section_title, section_text)
    fallback['source'] = 'fallback'
    return fallback


def enrich_block(
    book_title: str,
    chapter_title: str,
    section_title: str,
    block_text: str,
) -> Dict[str, Any]:
    try:
        api_result = _call_enrichment_api(
            build_block_prompt(book_title, chapter_title, section_title, block_text),
            system_prompt=BLOCK_ENRICHMENT_PROMPT,
        )
        cleaned = _normalize_block_enrichment_payload(api_result or {})
        if cleaned['keywords'] or cleaned['concepts']:
            cleaned['source'] = 'api'
            return cleaned
    except Exception:
        pass

    fallback = _build_fallback_block_enrichment(section_title, block_text)
    fallback['source'] = 'fallback'
    return fallback


def _call_enrichment_api(prompt: str, system_prompt: str = SECTION_ENRICHMENT_PROMPT) -> Optional[Dict[str, Any]]:
    client = _get_enrichment_client()
    response = client.chat.completions.create(
        model=_ENRICHMENT_MODEL,
        messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': prompt},
        ],
        temperature=0.2,
        response_format={'type': 'json_object'},
    )
    content = response.choices[0].message.content or ''
    return _parse_json_text(content)


def _parse_json_text(raw_text: str) -> Optional[Dict[str, Any]]:
    text = (raw_text or '').strip()
    if not text:
        return None

    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    start = text.find('{')
    end = text.rfind('}')
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        parsed = json.loads(text[start:end + 1])
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        return None
    return None


def _normalize_enrichment_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    keywords: List[str] = []
    for item in payload.get('keywords', []):
        term = _clean_label(item)
        if term and term not in keywords:
            keywords.append(term)
        if len(keywords) >= 8:
            break

    concepts: List[Dict[str, str]] = []
    for item in payload.get('concepts', []):
        if not isinstance(item, dict):
            continue
        name = _clean_label(item.get('name', ''))
        description = _clean_sentence(item.get('description', ''))
        if not name or not description:
            continue
        if any(existing['name'] == name for existing in concepts):
            continue
        concepts.append({'name': name, 'description': description})
        if len(concepts) >= 5:
            break

    summary = _clean_sentence(payload.get('summary', ''), max_len=120)
    return {
        'keywords': keywords[:8],
        'concepts': concepts[:5],
        'summary': summary,
    }


def _normalize_block_enrichment_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    normalized = _normalize_enrichment_payload(payload)
    return {
        'keywords': normalized['keywords'][:5],
        'concepts': normalized['concepts'][:5],
    }


def _build_fallback_enrichment(section_title: str, section_text: str) -> Dict[str, Any]:
    keywords = _extract_keywords(section_title, section_text)
    concepts = [
        {
            'name': term,
            'description': _CONCEPT_DESCRIPTIONS.get(term, f'本节围绕"{term}"展开阐述。'),
        }
        for term in keywords[:5]
    ]
    return {
        'keywords': keywords[:8],
        'concepts': concepts[:5],
        'summary': _build_summary(section_title, section_text),
    }


def _build_fallback_block_enrichment(section_title: str, block_text: str) -> Dict[str, Any]:
    keywords = _extract_keywords(section_title, block_text)[:5]
    concepts = [
        {
            'name': term,
            'description': _CONCEPT_DESCRIPTIONS.get(term, f'该段围绕"{term}"展开具体说明。'),
        }
        for term in keywords[:5]
    ]
    return {
        'keywords': keywords[:5],
        'concepts': concepts[:5],
    }


def _extract_keywords(section_title: str, section_text: str) -> List[str]:
    candidates: List[str] = []
    title = re.sub(r'^第[一二三四五六七八九十百]+[章节节]\s*', '', section_title or '')
    title = title.replace('导言', ' ').strip()
    for part in re.split(r'[、，。：；（）\-\s]+', title):
        term = _clean_label(part)
        if term:
            candidates.append(term)

    text = section_text or ''
    for pattern in _DOMAIN_PATTERNS:
        if pattern in text or pattern in section_title:
            candidates.append(pattern)

    for match in re.findall(r'[\u4e00-\u9fff]{2,10}', text):
        term = _clean_label(match)
        if term and term in _CONCEPT_DESCRIPTIONS:
            candidates.append(term)

    deduped: List[str] = []
    for term in candidates:
        if not term or term in deduped or term in _GENERIC_TERMS:
            continue
        deduped.append(term)
        if len(deduped) >= 8:
            break

    if len(deduped) < 3:
        for pattern in _DOMAIN_PATTERNS:
            if pattern not in deduped:
                deduped.append(pattern)
            if len(deduped) >= 3:
                break
    return deduped[:8]


def _build_summary(section_title: str, section_text: str) -> str:
    compact = re.sub(r'\s+', '', section_text or '')
    if compact:
        sentences = re.split(r'[。！？]', compact)
        fragments = [item.strip('，；：,. ') for item in sentences if item.strip()]
        if fragments:
            summary = fragments[0]
            if len(summary) > 70:
                summary = summary[:70].rstrip('，；：,. ') + '。'
            elif not summary.endswith('。'):
                summary += '。'
            return summary
    clean_title = re.sub(r'^第[一二三四五六七八九十百]+[章节节]\s*', '', section_title or '').strip()
    return f'本节围绕{clean_title}展开说明。'


def _clean_label(value: Any) -> str:
    text = str(value or '').strip()
    text = re.sub(r'^[\-—:：\d\.、\s]+', '', text)
    text = re.sub(r'[。；，,、:：\s]+$', '', text)
    text = re.sub(r'\s+', '', text)
    if not text or len(text) < 2 or len(text) > 16:
        return ''
    if text in _GENERIC_TERMS:
        return ''
    return text


def _clean_sentence(value: Any, max_len: int = 50) -> str:
    text = str(value or '').strip()
    text = re.sub(r'\s+', '', text)
    text = re.sub(r'^"|"$', '', text)
    if not text:
        return ''
    if len(text) > max_len:
        text = text[:max_len].rstrip('，；：,. ') + '。'
    return text
