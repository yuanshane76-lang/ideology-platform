from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from src.config import settings
from src.clients import openai_client

# 伴读动作系统提示词
ACTION_PROMPTS = {
    'explain': """你是思政教材阅读页右侧的中文伴读助手。

你的任务是解释一段教材正文，服务对象是正在学习这本教材的学生。

输出要求：
1. 只使用自然中文输出，不要出现英文。
2. 直接解释这段内容在说什么、为什么这样说、理解时要抓住什么。
3. 要贴合当前 block 及其所在 section / chapter，不要脱离原文泛泛发挥。
4. 不要写成空话，不要堆砌政治口号，不要机械重复"本段主要讲了""这一段告诉我们"之类套话。
5. 不要分点，不要加标题，输出 1 段到 2 段即可，整体简洁清楚。
6. 如果原文里有概念、判断、关系，请用更易懂的中文讲清楚它们之间的联系。
7. 不要编造原文没有的信息。""",
    'ask': """你是思政教材阅读页右侧的中文伴读助手。

你的任务是基于当前教材段落，生成适合学生继续学下去的追问问题。

输出要求：
1. 只输出严格 JSON，不要输出 markdown，不要输出额外说明。
2. JSON 结构必须是：
{
  "items": ["问题1", "问题2", "问题3"]
}
3. 生成 2 到 4 个问题。
4. 问题必须紧扣当前 block 及其 section / chapter 上下文，能顺着这段继续思考。
5. 不要太空泛，不要问与段落无关的问题，不要重复同一种问法。
6. 问题要像学生下一步真的会追问的内容，兼顾概念理解、原因分析、关系辨析或现实联系。
7. 所有问题都必须是自然中文。""",
    'note': """你是思政教材阅读页右侧的中文伴读助手。

你的任务是把当前教材段落整理成一段可以直接记下来的学习笔记。

输出要求：
1. 只使用自然中文输出，不要出现英文。
2. 输出应简洁、凝练、可记录，像学生可以直接抄到笔记本里的内容。
3. 不要写成长篇作文，不要流水账，不要照抄原文整段。
4. 优先保留本段的核心概念、关键判断和最值得记住的关系。
5. 不要加标题，不要分很多点，输出 1 段即可。
6. 不要编造原文没有的信息。""",
}

FOLLOWUP_PROMPT = """你是思政教材阅读页右侧的中文伴读助手。

你的任务是回答学生基于当前教材段落提出的具体问题。

输出要求：
1. 只使用自然中文输出，不要出现英文。
2. 回答必须直接回应学生问题，不能把问题改写成新的问题列表。
3. 要紧扣当前教材段落及其 chapter / section 上下文作答，不要脱离原文空泛发挥。
4. 优先讲清楚概念含义、因果关系、内在逻辑和与现实的联系。
5. 不要输出 JSON，不要 markdown，不要加标题。
6. 输出 1 到 3 段即可，清楚、具体、像真实伴读解释。
7. 不要编造原文没有依据的信息。"""

# 用于伴读的模型名
_COMPANION_MODEL = 'qwen-plus-latest'


class CompanionActionError(Exception):
    pass


class CompanionConfigError(CompanionActionError):
    pass


class CompanionResponseError(CompanionActionError):
    pass


def _stringify_neighbor_blocks(items: List[Dict[str, Any]]) -> str:
    if not items:
        return '无'
    lines = []
    for item in items[:2]:
        text = str(item.get('clean_text', '') or '').strip()
        if len(text) > 140:
            text = f'{text[:140]}…'
        lines.append(f"- {text or '无正文'}")
    return '\n'.join(lines) or '无'


def _build_user_prompt(action: str, context: Dict[str, Any]) -> str:
    block = context.get('current_block', {})
    chapter = context.get('chapter_context', {})
    section = context.get('section_context', {})
    concept_labels = '、'.join(item.get('label', '') for item in context.get('concept_contexts', []) if item.get('label')) or '无'
    keyword_labels = '、'.join(item.get('label', '') for item in context.get('keyword_contexts', []) if item.get('label')) or '无'
    selected_text = str(context.get('selected_text', '') or '').strip() or '无'
    block_text = str(block.get('clean_text', '') or '').strip() or '无'
    book_title = str(context.get('book_title', '') or '').strip() or str(context.get('book_id', '') or '').strip()
    neighbor_text = _stringify_neighbor_blocks(context.get('neighbor_blocks', []))

    return (
        f"动作类型：{action}\n"
        f"书名：{book_title}\n"
        f"chapter 标题：{chapter.get('title', '') or '无'}\n"
        f"chapter 摘要：{chapter.get('summary', '') or '无'}\n"
        f"section 标题：{section.get('title', '') or '无'}\n"
        f"section 摘要：{section.get('summary', '') or '无'}\n"
        f"当前 block 原文：\n{block_text}\n\n"
        f"用户选中文本：{selected_text}\n"
        f"相邻 block 参考：\n{neighbor_text}\n"
        f"相关概念：{concept_labels}\n"
        f"相关关键词：{keyword_labels}\n"
    )


def _normalize_text(text: str, max_len: int = 800) -> str:
    value = re.sub(r'\s+', ' ', str(text or '')).strip()
    if len(value) > max_len:
        value = f'{value[:max_len].rstrip()}…'
    return value


def _normalize_questions(payload: Dict[str, Any]) -> List[str]:
    items = payload.get('items', [])
    if not isinstance(items, list):
        return []

    questions: List[str] = []
    for item in items:
        question = _normalize_text(str(item or ''), max_len=120)
        if not question:
            continue
        if question[-1] not in {'？', '?'}:
            question = f'{question}？'
        if question not in questions:
            questions.append(question)
        if len(questions) >= 4:
            break
    return questions


def _call_companion_api(action: str, context: Dict[str, Any]) -> str:
    """使用 OpenAI SDK 调用伴读模型"""
    system_prompt = ACTION_PROMPTS.get(action, ACTION_PROMPTS['explain'])
    user_prompt = _build_user_prompt(action, context)

    kwargs = {
        'model': _COMPANION_MODEL,
        'messages': [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt},
        ],
        'temperature': 0.45 if action == 'explain' else 0.55,
    }

    if action == 'ask':
        kwargs['response_format'] = {'type': 'json_object'}

    response = openai_client.chat.completions.create(**kwargs)
    content = response.choices[0].message.content or ''
    return content.strip()


def _parse_json_text(raw_text: str) -> Optional[Dict[str, Any]]:
    text = (raw_text or '').strip()
    if not text:
        return None

    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)

    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass

    start = text.find('{')
    end = text.rfind('}')
    if start == -1 or end == -1 or end <= start:
        return None

    try:
        parsed = json.loads(text[start:end + 1])
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        return None


def generate_companion_text(action: str, context: Dict[str, Any]) -> Dict[str, Any]:
    normalized_action = (action or 'explain').strip().lower()
    if normalized_action not in ACTION_PROMPTS:
        raise CompanionActionError(f'Unsupported action: {normalized_action}')

    raw_content = _call_companion_api(normalized_action, context)

    if normalized_action == 'ask':
        parsed = _parse_json_text(raw_content)
        if not parsed:
            raise CompanionResponseError('提问动作返回的 JSON 解析失败。')
        items = _normalize_questions(parsed)
        if not items:
            raise CompanionResponseError('提问动作未返回有效问题。')
        return {
            'type': 'questions',
            'text': '',
            'items': items,
            'source': 'external_api',
            'model': _COMPANION_MODEL,
        }

    normalized_text = _normalize_text(raw_content)
    if not normalized_text:
        raise CompanionResponseError('模型返回内容为空。')

    return {
        'type': 'text',
        'text': normalized_text,
        'items': [],
        'source': 'external_api',
        'model': _COMPANION_MODEL,
    }


def generate_companion_followup_text(
    question: str,
    context: Dict[str, Any],
    history: Optional[List[Dict[str, Any]]] = None,
) -> str:
    normalized_question = _normalize_text(question, max_len=200)
    if not normalized_question:
        raise CompanionResponseError('追问内容为空。')

    history = history or []

    messages: List[Dict[str, str]] = [
        {'role': 'system', 'content': FOLLOWUP_PROMPT},
        {
            'role': 'user',
            'content': f"{_build_user_prompt('followup', context)}\n学生问题：{normalized_question}\n请直接回答这个问题。",
        },
    ]

    for item in history[-6:]:
        if not isinstance(item, dict):
            continue
        role = str(item.get('role', '') or '').strip().lower()
        content = _normalize_text(str(item.get('content', '') or ''), max_len=500)
        if role in {'user', 'assistant'} and content:
            messages.append({'role': role, 'content': content})

    response = openai_client.chat.completions.create(
        model=_COMPANION_MODEL,
        messages=messages,
        temperature=0.55,
    )

    content = response.choices[0].message.content or ''
    normalized_text = _normalize_text(content)
    if not normalized_text:
        raise CompanionResponseError('追问回答为空。')
    return normalized_text
