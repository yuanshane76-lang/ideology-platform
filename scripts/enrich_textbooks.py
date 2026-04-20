"""
教材伴读 enrichment 预处理脚本

功能：读取 book_bundle.json，对每个 section 调用 Qwen API 提取核心概念和关键词，
     生成高质量 enrichment.json，用于知识星图和伴读辅助区展示。

用法：
    python scripts/enrich_textbooks.py [--book szddfz-2023] [--all] [--dry-run]
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib import request, error

# ── 配置 ──────────────────────────────────────────────
API_KEY = os.getenv("DASHSCOPE_API_KEY", "sk-1126738050354caf8627b8e4e87cb636")
API_BASE = "https://dashscope.aliyuncs.com/compatible-mode/v1"
MODEL_NAME = os.getenv("ENRICHMENT_MODEL", "qwen-plus-latest")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BOOKS_DIR = PROJECT_ROOT / "content" / "textbook" / "books"

SECTION_PROMPT = """你是思政教材内容增强助手，负责为教材小节生成适合前端直接展示的结构化知识。

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
- concepts：3 到 5 个，每个 concept 都要包含 name 和 description。
- description：必须简短、自然、可展示，避免口号堆砌，10-30字。
- summary：1 段自然中文，简洁概括本节核心内容，50-100字。
- 不要输出"学习、内容、理论、章节、知识、教材、意义"等空泛词，除非它们在本节中构成明确知识点，如"理想信念""法治思维"。
- 不要生成与原文无关的政治口号，不要重复同义词，不要凑数。
- concepts 应偏向可展示、可关联、可图谱化的概念节点。
- 如果文本信息有限，也必须输出合法 JSON，但要尽量给出稳妥提炼结果。
- 严禁输出 markdown、解释、前后缀说明，只能输出 JSON。"""

# 不合格概念黑名单
_BLACKLIST_CONCEPTS = {
    "core", "concept", "chapter", "section", "block", "intro",
    "未命名章", "导言", "正文", "第一节", "第二节", "第三节", "第四节",
    "第一章", "第二章", "第三章", "第四章", "第五章", "第六章", "第七章",
    "绪论",
}

_GENERIC_TERMS = {
    "学习", "内容", "理论", "章节", "本节", "教材", "知识", "问题",
    "要求", "意义", "作用", "方面", "过程", "实践",
}


# ── API 调用 ──────────────────────────────────────────
def call_qwen(prompt: str, system_prompt: str = SECTION_PROMPT,
              retries: int = 3, delay: float = 2.0) -> Optional[Dict[str, Any]]:
    """调用阿里云百炼 Qwen API，返回解析后的 JSON dict。"""
    endpoint = f"{API_BASE}/chat/completions"
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }

    for attempt in range(1, retries + 1):
        try:
            req = request.Request(
                endpoint,
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {API_KEY}",
                },
                method="POST",
            )
            with request.urlopen(req, timeout=90) as resp:
                body = json.loads(resp.read().decode("utf-8"))

            message = ((body.get("choices") or [{}])[0].get("message") or {})
            content = message.get("content", "")
            if isinstance(content, list):
                content = "".join(
                    item.get("text", "") for item in content if isinstance(item, dict)
                )
            parsed = _parse_json_text(str(content or ""))
            if parsed:
                return parsed

        except (error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            print(f"  [WARN] API 调用失败 (attempt {attempt}/{retries}): {exc}")
            if attempt < retries:
                time.sleep(delay * attempt)
        except Exception as exc:
            print(f"  [ERROR] 未知异常: {exc}")
            if attempt < retries:
                time.sleep(delay * attempt)

    return None


def _parse_json_text(raw_text: str) -> Optional[Dict[str, Any]]:
    text = (raw_text or "").strip()
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


# ── 数据清洗 ──────────────────────────────────────────
def _clean_label(value: Any) -> str:
    text = str(value or "").strip()
    text = re.sub(r'^[\-—:：\d\.、\s]+', '', text)
    text = re.sub(r'[。；，,、:：\s]+$', '', text)
    text = re.sub(r'\s+', '', text)
    if not text or len(text) < 2 or len(text) > 16:
        return ""
    if text in _GENERIC_TERMS:
        return ""
    return text


def _clean_sentence(value: Any, max_len: int = 120) -> str:
    text = str(value or "").strip()
    text = re.sub(r'\s+', '', text)
    text = re.sub(r'^"|"$', '', text)
    if not text:
        return ""
    if len(text) > max_len:
        text = text[:max_len].rstrip('，；：,. ') + '。'
    return text


def normalize_enrichment(payload: Dict[str, Any]) -> Dict[str, Any]:
    """清洗 API 返回的 enrichment 结果，过滤不合格概念。"""
    keywords: List[str] = []
    for item in payload.get("keywords", []):
        term = _clean_label(item)
        if term and term not in keywords and term not in _BLACKLIST_CONCEPTS:
            keywords.append(term)
        if len(keywords) >= 8:
            break

    concepts: List[Dict[str, str]] = []
    for item in payload.get("concepts", []):
        if not isinstance(item, dict):
            continue
        name = _clean_label(item.get("name", ""))
        description = _clean_sentence(item.get("description", ""), max_len=50)
        if not name or name in _BLACKLIST_CONCEPTS:
            continue
        if not description:
            description = name
        if any(existing["name"] == name for existing in concepts):
            continue
        concepts.append({"name": name, "description": description})
        if len(concepts) >= 5:
            break

    summary = _clean_sentence(payload.get("summary", ""), max_len=120)
    return {
        "keywords": keywords[:8],
        "concepts": concepts[:5],
        "summary": summary,
    }


# ── 主流程 ────────────────────────────────────────────
def load_book_bundle(book_dir: Path) -> Dict[str, Any]:
    bundle_path = book_dir / "processed" / "book_bundle.json"
    if not bundle_path.exists():
        bundle_path = book_dir / "processed" / "book.json"
    if not bundle_path.exists():
        raise FileNotFoundError(f"找不到 book_bundle.json 或 book.json: {book_dir}")
    with bundle_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def build_section_text(bundle: Dict[str, Any], section_id: str) -> str:
    """拼接某个 section 下所有 block 的 clean_text 作为该小节正文。"""
    blocks = bundle.get("blocks", [])
    section_blocks = [
        b for b in blocks if b.get("section_id") == section_id
    ]
    # 按 section_order 排序
    section_blocks.sort(key=lambda b: b.get("section_order", b.get("order", 0)))
    texts = [b.get("clean_text", "") for b in section_blocks if b.get("clean_text")]
    return "\n".join(texts)


def enrich_book(book_id: str, dry_run: bool = False) -> None:
    book_dir = BOOKS_DIR / book_id
    if not book_dir.exists():
        print(f"[ERROR] 教材目录不存在: {book_dir}")
        return

    print(f"\n{'='*60}")
    print(f"处理教材: {book_id}")
    print(f"{'='*60}")

    bundle = load_book_bundle(book_dir)
    book_title = bundle.get("book", {}).get("title", book_id)
    chapters = bundle.get("chapters", [])
    sections = bundle.get("sections", [])

    # 构建 chapter_id → chapter_title 映射
    chapter_map = {ch["id"]: ch for ch in chapters}

    total = len(sections)
    success_count = 0
    fail_count = 0
    results: Dict[str, Dict[str, Any]] = {}

    for idx, section in enumerate(sections, start=1):
        section_id = section["id"]
        section_title = section.get("title", "")
        chapter_id = section.get("chapter_id", "")
        chapter_title = chapter_map.get(chapter_id, {}).get("title", "")

        section_text = build_section_text(bundle, section_id)
        if not section_text.strip():
            print(f"  [{idx}/{total}] 跳过空小节: {section_title}")
            results[section_id] = {
                "summary": "",
                "concepts": [],
                "keywords": [],
                "source": "empty-section",
            }
            continue

        # 截断过长文本（避免超出 token 限制）
        if len(section_text) > 3000:
            section_text = section_text[:3000]

        prompt = (
            f"教材名称：{book_title}\n"
            f"章节标题：{chapter_title}\n"
            f"小节标题：{section_title}\n"
            f"小节正文：\n{section_text.strip()}\n"
        )

        if dry_run:
            print(f"  [{idx}/{total}] [DRY-RUN] {section_title[:30]}...")
            results[section_id] = {
                "summary": "[dry-run] 模拟摘要",
                "concepts": [{"name": "模拟概念", "description": "dry-run 测试"}],
                "keywords": ["模拟关键词"],
                "source": "dry-run",
            }
            continue

        print(f"  [{idx}/{total}] 正在处理: {section_title[:40]}...", end="", flush=True)

        api_result = call_qwen(prompt)
        if api_result:
            cleaned = normalize_enrichment(api_result)
            cleaned["source"] = "api"
            results[section_id] = cleaned
            success_count += 1
            concept_names = [c["name"] for c in cleaned["concepts"]]
            print(f" OK (概念: {', '.join(concept_names)})")
        else:
            fail_count += 1
            results[section_id] = {
                "summary": "",
                "concepts": [],
                "keywords": [],
                "source": "api-failed",
            }
            print(" FAILED")

        # 限流：避免过快调用 API
        if idx < total:
            time.sleep(0.5)

    # 保存 enrichment.json
    enrichment = {
        "book_id": book_id,
        "book_title": book_title,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "mode": "section-enrichment",
            "api_enabled": True,
            "api_base_url": API_BASE,
            "model_name": MODEL_NAME,
        },
        "sections": results,
    }

    output_path = book_dir / "processed" / "enrichment.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(enrichment, f, ensure_ascii=False, indent=2)

    print(f"\n结果已保存: {output_path}")
    print(f"统计: 成功 {success_count}/{total}, 失败 {fail_count}/{total}")

    # 打印全局概念汇总
    all_concepts: Dict[str, int] = {}
    for sec_data in results.values():
        for concept in sec_data.get("concepts", []):
            name = concept.get("name", "")
            if name:
                all_concepts[name] = all_concepts.get(name, 0) + 1
    if all_concepts:
        sorted_concepts = sorted(all_concepts.items(), key=lambda x: -x[1])
        print(f"\n概念频次 TOP 20:")
        for name, count in sorted_concepts[:20]:
            print(f"  {name}: {count} 次")


# ── 入口 ──────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="教材伴读 enrichment 预处理")
    parser.add_argument("--book", type=str, help="指定教材 book_id")
    parser.add_argument("--all", action="store_true", help="处理所有注册教材")
    parser.add_argument("--dry-run", action="store_true", help="模拟运行，不调用 API")
    args = parser.parse_args()

    if args.dry_run:
        print("[DRY-RUN] 模拟模式，不会调用 API")

    if args.book:
        enrich_book(args.book, dry_run=args.dry_run)
    elif args.all:
        # 遍历所有有 book_bundle.json 的教材
        for book_dir in sorted(BOOKS_DIR.iterdir()):
            if not book_dir.is_dir():
                continue
            bundle_path = book_dir / "processed" / "book_bundle.json"
            if not bundle_path.exists():
                bundle_path = book_dir / "processed" / "book.json"
            if bundle_path.exists():
                enrich_book(book_dir.name, dry_run=args.dry_run)
    else:
        # 默认处理已注册的两本
        for book_id in ["szddfz-2023", "marxism-basic-principles-2023"]:
            enrich_book(book_id, dry_run=args.dry_run)

    print("\n全部完成!")


if __name__ == "__main__":
    main()
