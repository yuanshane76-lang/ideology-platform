"""
教材知识星图 graph.json 重建脚本

功能：基于 book_bundle.json 和 enrichment.json 重建高质量的 graph.json，
     生成包含 book/chapter/section/concept 四类节点的知识星图数据。

用法：
    python scripts/rebuild_graph.py [--book szddfz-2023] [--all]
"""

from __future__ import annotations

import json
import math
import re
import argparse
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BOOKS_DIR = PROJECT_ROOT / "content" / "textbook" / "books"

# 不合格概念过滤
_BLACKLIST_CONCEPTS = {
    "core", "concept", "chapter", "section", "block", "intro",
    "未命名章", "导言", "正文", "第一节", "第二节", "第三节", "第四节",
    "第一章", "第二章", "第三章", "第四章", "第五章", "第六章", "第七章",
    "绪论", "13s", "17s",
}


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _clean_label(value: str) -> str:
    text = str(value or "").strip()
    text = re.sub(r'^[\-—:：\d\.、\s]+', '', text)
    text = re.sub(r'[。；，,、:：\s]+$', '', text)
    text = re.sub(r'\s+', '', text)
    if not text or len(text) < 2 or len(text) > 16:
        return ""
    if text in _BLACKLIST_CONCEPTS:
        return ""
    return text


def _safe_term_id(term: str) -> str:
    normalized = re.sub(r'\s+', '-', term.strip())
    normalized = re.sub(r'[^\w\-\u4e00-\u9fff]', '-', normalized)
    normalized = re.sub(r'-+', '-', normalized).strip('-')
    return normalized or 'item'


def _reader_href(book_id: str, chapter_id: str = "", anchor: str = "") -> str:
    import urllib.parse
    params = {"book_id": book_id}
    if chapter_id:
        params["chapter_id"] = chapter_id
    href = f"/reader?{urllib.parse.urlencode(params)}"
    if anchor:
        href += f"#{urllib.parse.quote(anchor, safe='')}"
    return href


def build_concept_catalog(enrichment: Dict[str, Any]) -> List[Dict[str, Any]]:
    """从 enrichment 数据中提取全局概念目录（去重、排序）。"""
    concept_counter: Counter = Counter()
    concept_desc: Dict[str, str] = {}

    for section_id, sec_data in enrichment.get("sections", {}).items():
        for concept in sec_data.get("concepts", []):
            name = concept.get("name", "")
            if not name or name in _BLACKLIST_CONCEPTS:
                continue
            cleaned = _clean_label(name)
            if not cleaned:
                continue
            concept_counter[cleaned] += 1
            desc = concept.get("description", "")
            if cleaned not in concept_desc or (desc and len(desc) > len(concept_desc.get(cleaned, ""))):
                concept_desc[cleaned] = desc

    catalog = []
    for name, count in concept_counter.most_common(30):
        concept_id = f"concept-{_safe_term_id(name)}"
        catalog.append({
            "id": concept_id,
            "name": name,
            "short_description": concept_desc.get(name, name),
            "frequency": count,
        })
    return catalog


def build_concept_section_map(enrichment: Dict[str, Any], concepts: List[Dict[str, Any]]) -> Dict[str, str]:
    """构建 concept_id → section_id 映射（概念首次出现的小节）。"""
    name_to_id = {c["name"]: c["id"] for c in concepts}
    concept_section: Dict[str, str] = {}

    for section_id, sec_data in enrichment.get("sections", {}).items():
        for concept in sec_data.get("concepts", []):
            name = concept.get("name", "")
            cleaned = _clean_label(name)
            if cleaned in name_to_id:
                cid = name_to_id[cleaned]
                if cid not in concept_section:
                    concept_section[cid] = section_id
    return concept_section


def build_graph(book_id: str, bundle: Dict[str, Any], enrichment: Dict[str, Any]) -> Dict[str, Any]:
    """基于 enrichment 数据构建完整知识星图。"""
    chapters = bundle.get("chapters", [])
    sections = bundle.get("sections", [])

    # 概念目录
    concept_catalog = build_concept_catalog(enrichment)
    concept_section_map = build_concept_section_map(enrichment, concept_catalog)

    # 构建 section_id → section 映射
    section_map = {s["id"]: s for s in sections}
    chapter_map = {ch["id"]: ch for ch in chapters}

    # 构建 section_id → enrichment data 映射
    enrichment_sections = enrichment.get("sections", {})

    # 构建 section_id → concept_names 映射
    section_concepts: Dict[str, List[str]] = {}
    name_to_concept = {c["name"]: c for c in concept_catalog}
    for section_id, sec_data in enrichment_sections.items():
        concepts_in_section = []
        for concept in sec_data.get("concepts", []):
            name = _clean_label(concept.get("name", ""))
            if name and name in name_to_concept:
                concepts_in_section.append(name)
        section_concepts[section_id] = concepts_in_section

    nodes = []
    edges = []
    chapter_lane = []
    section_lane = []
    concept_lane = []

    # ── Book 核心节点 ──
    book_title = bundle.get("book", {}).get("title", book_id)
    nodes.append({
        "id": "book-core",
        "label": book_title,
        "type": "book",
        "group": "core",
        "depth": 0,
        "orbit": 0,
        "angle": 0,
        "description": bundle.get("book", {}).get("description", ""),
        "summary": bundle.get("book", {}).get("description", ""),
        "style_hint": "core",
    })

    # ── Chapter 节点 ──
    sorted_chapters = sorted(chapters, key=lambda c: c.get("order", 0))
    for ch_idx, chapter in enumerate(sorted_chapters, start=1):
        chapter_node_id = f"chapter-{chapter['id']}"
        chapter_lane.append(chapter_node_id)

        # 收集该章节下所有概念
        ch_concept_names = []
        for sec_id in chapter.get("sectionIds", []):
            ch_concept_names.extend(section_concepts.get(sec_id, []))
        ch_concept_names = list(dict.fromkeys(ch_concept_names))[:5]  # 去重取前5

        description = chapter.get("summary", "")
        if not description and ch_concept_names:
            description = f"核心概念: {', '.join(ch_concept_names[:5])}"

        nodes.append({
            "id": chapter_node_id,
            "label": chapter["title"],
            "type": "chapter",
            "group": "chapter",
            "depth": 1,
            "orbit": 1,
            "angle": ch_idx,
            "description": description,
            "summary": description,
            "href": _reader_href(book_id, chapter_id=chapter["id"]),
            "ref": {
                "book_id": book_id,
                "chapter_id": chapter["id"],
                "anchor": chapter.get("anchor", ""),
            },
        })
        edges.append({
            "id": f"edge:book-core->{chapter_node_id}",
            "source": "book-core",
            "target": chapter_node_id,
            "label": "contains",
            "type": "contains",
        })

    # ── Section 节点 ──
    sec_angle = 0
    for chapter in sorted_chapters:
        chapter_node_id = f"chapter-{chapter['id']}"
        for sec_id in chapter.get("sectionIds", []):
            section = section_map.get(sec_id)
            if not section:
                continue
            sec_angle += 1
            section_node_id = f"section-{section['id']}"
            section_lane.append(section_node_id)

            # 获取 enrichment 数据
            enriched = enrichment_sections.get(sec_id, {})
            description = enriched.get("summary", "") or section.get("summary", "")

            nodes.append({
                "id": section_node_id,
                "label": section["title"],
                "type": "section",
                "group": "section",
                "depth": 2,
                "orbit": 2,
                "angle": sec_angle,
                "description": description[:120] if description else "",
                "summary": description[:120] if description else "",
                "href": _reader_href(book_id, chapter_id=chapter["id"], anchor=section.get("anchor", "")),
                "ref": {
                    "book_id": book_id,
                    "chapter_id": chapter["id"],
                    "anchor": section.get("anchor", ""),
                },
            })
            edges.append({
                "id": f"edge:{chapter_node_id}->{section_node_id}",
                "source": chapter_node_id,
                "target": section_node_id,
                "label": "contains",
                "type": "contains",
            })

    # ── Concept 节点 ──
    for c_idx, concept in enumerate(concept_catalog[:24], start=1):
        concept_node_id = concept["id"]
        concept_lane.append(concept_node_id)

        # 查找概念所属的 section
        primary_section_id = concept_section_map.get(concept_node_id, "")
        section_node_id = f"section-{primary_section_id}" if primary_section_id else ""
        chapter_id_of_concept = section_map.get(primary_section_id, {}).get("chapter_id", "")
        chapter_node_id = f"chapter-{chapter_id_of_concept}" if chapter_id_of_concept else ""

        description = concept.get("short_description", concept["name"])

        nodes.append({
            "id": concept_node_id,
            "label": concept["name"],
            "type": "concept",
            "group": "concept",
            "depth": 3,
            "orbit": 3,
            "angle": c_idx,
            "description": description,
            "summary": description,
            "frequency": concept.get("frequency", 1),
            "href": _reader_href(book_id, chapter_id=chapter_id_of_concept,
                                 anchor=section_map.get(primary_section_id, {}).get("anchor", "")) if primary_section_id else "#",
            "ref": {
                "book_id": book_id,
                "chapter_id": chapter_id_of_concept,
                "anchor": section_map.get(primary_section_id, {}).get("anchor", ""),
            } if primary_section_id else {},
        })

        # section → concept 边 (explains 关系)
        if section_node_id:
            edges.append({
                "id": f"edge:{section_node_id}->{concept_node_id}",
                "source": section_node_id,
                "target": concept_node_id,
                "label": "explains",
                "type": "explains",
            })

        # chapter → concept 边 (relates_to 关系)
        if chapter_node_id:
            edges.append({
                "id": f"edge:{chapter_node_id}->{concept_node_id}",
                "source": chapter_node_id,
                "target": concept_node_id,
                "label": "relates_to",
                "type": "relates_to",
            })

    # ── Concept 间 relates_to 边 ──
    # 同一 section 中出现的概念互相关联
    for section_id, concept_names in section_concepts.items():
        concept_ids = [name_to_concept[n]["id"] for n in concept_names if n in name_to_concept]
        for i in range(len(concept_ids)):
            for j in range(i + 1, len(concept_ids)):
                if concept_ids[i] in {c["id"] for c in concept_catalog[:24]} and \
                   concept_ids[j] in {c["id"] for c in concept_catalog[:24]}:
                    edges.append({
                        "id": f"edge:{concept_ids[i]}->{concept_ids[j]}",
                        "source": concept_ids[i],
                        "target": concept_ids[j],
                        "label": "relates_to",
                        "type": "relates_to",
                    })

    return {
        "meta": {
            "source": "enrichment-driven",
            "book_id": book_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "concept_count": len(concept_catalog[:24]),
            "total_concepts_found": len(concept_catalog),
        },
        "nodes": nodes,
        "edges": edges,
        "lanes": {
            "chapters": chapter_lane,
            "sections": section_lane,
            "concepts": concept_lane,
        },
    }


def rebuild_book_graph(book_id: str) -> None:
    book_dir = BOOKS_DIR / book_id
    processed_dir = book_dir / "processed"

    bundle_path = processed_dir / "book_bundle.json"
    if not bundle_path.exists():
        bundle_path = processed_dir / "book.json"
    if not bundle_path.exists():
        print(f"[ERROR] 找不到 book 数据: {book_dir}")
        return

    enrichment_path = processed_dir / "enrichment.json"
    if not enrichment_path.exists():
        print(f"[ERROR] 找不到 enrichment.json: {enrichment_path}")
        return

    print(f"\n重建知识星图: {book_id}")
    bundle = load_json(bundle_path)
    enrichment = load_json(enrichment_path)

    graph = build_graph(book_id, bundle, enrichment)

    # 统计
    type_counts = {"book": 0, "chapter": 0, "section": 0, "concept": 0}
    for node in graph["nodes"]:
        t = node.get("type", "")
        if t in type_counts:
            type_counts[t] += 1

    edge_type_counts = {}
    for edge in graph["edges"]:
        et = edge.get("type", "unknown")
        edge_type_counts[et] = edge_type_counts.get(et, 0) + 1

    print(f"  节点: {len(graph['nodes'])} (book={type_counts['book']}, chapter={type_counts['chapter']}, "
          f"section={type_counts['section']}, concept={type_counts['concept']})")
    print(f"  边: {len(graph['edges'])} (类型: {edge_type_counts})")
    print(f"  概念泳道: {len(graph['lanes']['concepts'])} 个概念")

    # 保存
    graph_path = processed_dir / "graph.json"
    # 备份旧的
    if graph_path.exists():
        backup_path = processed_dir / "graph.json.bak"
        if not backup_path.exists():
            import shutil
            shutil.copy2(graph_path, backup_path)
            print(f"  已备份旧 graph.json → graph.json.bak")

    save_json(graph_path, graph)
    print(f"  已保存: {graph_path}")

    # 同时生成 concepts.json 配置文件
    concept_catalog = build_concept_catalog(enrichment)
    if concept_catalog:
        concepts_json = {
            "concepts": [
                {
                    "id": c["id"],
                    "name": c["name"],
                    "aliases": [],
                    "short_description": c["short_description"],
                }
                for c in concept_catalog
            ]
        }
        # 检查是否有 source/config 目录
        config_dir = book_dir / "source" / "config"
        if not config_dir.exists():
            config_dir = book_dir / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        concepts_path = config_dir / "concepts.json"
        save_json(concepts_path, concepts_json)
        print(f"  已生成 concepts.json: {concepts_path} ({len(concept_catalog)} 个概念)")


def main():
    parser = argparse.ArgumentParser(description="重建教材知识星图 graph.json")
    parser.add_argument("--book", type=str, help="指定教材 book_id")
    parser.add_argument("--all", action="store_true", help="处理所有教材")
    args = parser.parse_args()

    if args.book:
        rebuild_book_graph(args.book)
    elif args.all:
        for book_dir in sorted(BOOKS_DIR.iterdir()):
            if not book_dir.is_dir():
                continue
            enrichment_path = book_dir / "processed" / "enrichment.json"
            bundle_path = book_dir / "processed" / "book_bundle.json"
            if not bundle_path.exists():
                bundle_path = book_dir / "processed" / "book.json"
            if enrichment_path.exists() and bundle_path.exists():
                rebuild_book_graph(book_dir.name)
    else:
        for book_id in ["szddfz-2023", "marxism-basic-principles-2023"]:
            rebuild_book_graph(book_id)

    print("\n全部完成!")


if __name__ == "__main__":
    main()
