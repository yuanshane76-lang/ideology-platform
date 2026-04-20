from __future__ import annotations

from typing import Any, Dict, List

from src.textbook.companion_context_service import build_companion_context
from src.textbook.concept_extraction_service import extract_concept_placeholders
from src.textbook.embedding_preparation_service import build_embedding_preparation
from src.textbook.graph_preparation_service import build_graph_preparation
from src.textbook.markdown_parser_service import parse_book_directory


def run_content_pipeline(book_dir) -> Dict[str, Any]:
    structured_book = parse_book_directory(book_dir)
    concept_bundle = extract_concept_placeholders(structured_book)
    embedding_bundle = build_embedding_preparation(structured_book)
    graph_bundle = build_graph_preparation(structured_book)

    blocks = structured_book.get('blocks', [])
    companion_context_sample = None
    if blocks:
        companion_context_sample = build_companion_context(structured_book, blocks[0]['id'])

    return {
        'structured_book': structured_book,
        'concept_bundle': concept_bundle,
        'embedding_bundle': embedding_bundle,
        'graph_bundle': graph_bundle,
        'companion_context_sample': companion_context_sample,
    }


def build_processed_book(book_dir) -> Dict[str, Any]:
    pipeline_output = run_content_pipeline(book_dir)
    structured_book = pipeline_output['structured_book']
    structured_book['pipeline'] = {
        'parse': {'status': 'done', 'module': 'markdown_parser_service'},
        'concept_extraction': {
            'status': pipeline_output['concept_bundle']['status'],
            'module': 'concept_extraction_service',
        },
        'embedding_preparation': {
            'status': pipeline_output['embedding_bundle']['status'],
            'module': 'embedding_preparation_service',
            'unit_type': pipeline_output['embedding_bundle']['unit_type'],
        },
        'graph_preparation': {
            'status': pipeline_output['graph_bundle']['status'],
            'module': 'graph_preparation_service',
            'schema_version': pipeline_output['graph_bundle']['schema_version'],
        },
        'companion_context': {
            'status': 'placeholder',
            'module': 'companion_context_service',
        },
    }
    return structured_book
