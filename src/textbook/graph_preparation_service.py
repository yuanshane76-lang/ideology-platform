from __future__ import annotations

from typing import Any, Dict, List


def build_graph_preparation(structured_book: Dict[str, Any]) -> Dict[str, Any]:
    book = structured_book.get('book', {})
    chapters = structured_book.get('chapters', [])
    sections = structured_book.get('sections', [])
    blocks = structured_book.get('blocks', [])
    concepts = structured_book.get('concepts', [])

    nodes: List[Dict[str, Any]] = []
    relationships: List[Dict[str, Any]] = []

    if book:
        nodes.append({'node_type': 'Book', 'id': book['id'], 'properties': book})

    for chapter in chapters:
        nodes.append({'node_type': 'Chapter', 'id': chapter['id'], 'properties': chapter})
        relationships.append({'type': 'HAS_CHAPTER', 'from': book['id'], 'to': chapter['id']})

    for section in sections:
        nodes.append({'node_type': 'Section', 'id': section['id'], 'properties': section})
        relationships.append({'type': 'HAS_SECTION', 'from': section['chapter_id'], 'to': section['id']})

    for block in blocks:
        nodes.append(
            {
                'node_type': 'Block',
                'id': block['id'],
                'properties': {
                    'book_id': block['book_id'],
                    'chapter_id': block['chapter_id'],
                    'section_id': block['section_id'],
                    'anchor': block['anchor'],
                    'clean_text': block['clean_text'],
                    'token_estimate': block['token_estimate'],
                },
            }
        )
        relationships.append({'type': 'HAS_BLOCK', 'from': block['section_id'], 'to': block['id']})

    for concept in concepts:
        nodes.append({'node_type': 'Concept', 'id': concept['id'], 'properties': concept})

    for block in blocks:
        for concept_id in block.get('concept_refs', []):
            relationships.append({'type': 'MENTIONS_CONCEPT', 'from': block['id'], 'to': concept_id})

    return {
        'book_id': book.get('id'),
        'status': 'placeholder',
        'target': 'neo4j',
        'schema_version': 'graph-prep-v1',
        'nodes': nodes,
        'relationships': relationships,
    }
