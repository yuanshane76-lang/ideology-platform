from __future__ import annotations

from typing import Any, Dict, List


EMBEDDING_UNIT = 'block'


def build_embedding_preparation(structured_book: Dict[str, Any]) -> Dict[str, Any]:
    book = structured_book.get('book', {})
    chapters = {item['id']: item for item in structured_book.get('chapters', [])}
    sections = {item['id']: item for item in structured_book.get('sections', [])}

    items: List[Dict[str, Any]] = []
    for block in structured_book.get('blocks', []):
        chapter = chapters.get(block['chapter_id'], {})
        section = sections.get(block['section_id'], {})
        items.append(
            {
                'unit_type': EMBEDDING_UNIT,
                'unit_id': block['id'],
                'text': block.get('clean_text', ''),
                'token_estimate': block.get('token_estimate', 0),
                'payload': {
                    'book_id': block.get('book_id'),
                    'chapter_id': block.get('chapter_id'),
                    'chapter_title': chapter.get('title', ''),
                    'section_id': block.get('section_id'),
                    'section_title': section.get('title', ''),
                    'anchor': block.get('anchor'),
                    'concept_refs': block.get('concept_refs', []),
                    'keyword_refs': block.get('keyword_refs', []),
                },
            }
        )

    return {
        'book_id': book.get('id'),
        'status': 'placeholder',
        'target': 'qdrant',
        'unit_type': EMBEDDING_UNIT,
        'items': items,
    }
