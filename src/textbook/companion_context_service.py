from __future__ import annotations

from typing import Any, Dict, List

NEIGHBOR_BLOCK_WINDOW = 1


def _pick_refs(source: Dict[str, Any], ref_ids: List[str], label_key: str) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for ref_id in ref_ids:
        item = source.get(ref_id)
        if not item:
            continue
        payload = dict(item)
        payload["label"] = item.get(label_key) or item.get("name") or item.get("term") or ref_id
        items.append(payload)
    return items


def build_companion_context(
    structured_book: Dict[str, Any],
    block_id: str,
    selected_text: str = "",
) -> Dict[str, Any]:
    book = structured_book.get("book", {})
    chapters = {item["id"]: item for item in structured_book.get("chapters", [])}
    sections = {item["id"]: item for item in structured_book.get("sections", [])}
    concepts = {item["id"]: item for item in structured_book.get("concepts", [])}
    keywords = {item["id"]: item for item in structured_book.get("keywords", [])}
    ordered_blocks = structured_book.get("blocks", [])
    blocks = {item["id"]: item for item in ordered_blocks}

    block = blocks[block_id]
    chapter = chapters[block["chapter_id"]]
    section = sections[block["section_id"]]

    block_ids = [item["id"] for item in ordered_blocks]
    current_index = block_ids.index(block_id)
    start_index = max(0, current_index - NEIGHBOR_BLOCK_WINDOW)
    end_index = min(len(ordered_blocks), current_index + NEIGHBOR_BLOCK_WINDOW + 1)

    neighbor_blocks: List[Dict[str, Any]] = []
    for index in range(start_index, end_index):
        neighbor = ordered_blocks[index]
        if neighbor["id"] == block_id:
            continue
        neighbor_blocks.append(
            {
                "id": neighbor["id"],
                "anchor": neighbor.get("anchor", ""),
                "clean_text": neighbor.get("clean_text", ""),
                "section_id": neighbor.get("section_id", ""),
                "chapter_id": neighbor.get("chapter_id", ""),
            }
        )

    return {
        "book_id": book.get("id"),
        "book_title": book.get("title", book.get("id", "")),
        "context_type": "ai-companion-context-v2",
        "selected_text": (selected_text or "").strip(),
        "current_block": {
            "id": block["id"],
            "anchor": block.get("anchor", ""),
            "raw_text": block.get("raw_text", ""),
            "clean_text": block.get("clean_text", ""),
            "token_estimate": block.get("token_estimate", 0),
            "concept_refs": block.get("concept_refs", []),
            "keyword_refs": block.get("keyword_refs", []),
        },
        "chapter_context": {
            "id": chapter["id"],
            "title": chapter.get("title", ""),
            "summary": chapter.get("summary", ""),
        },
        "section_context": {
            "id": section["id"],
            "title": section.get("title", ""),
            "summary": section.get("summary", ""),
        },
        "neighbor_blocks": neighbor_blocks,
        "concept_contexts": _pick_refs(concepts, block.get("concept_refs", []), "name"),
        "keyword_contexts": _pick_refs(keywords, block.get("keyword_refs", []), "term"),
    }
