from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

# 指向主项目 content/textbook/ 目录
BASE_DIR = Path(__file__).resolve().parents[2] / 'content' / 'textbook'
CONTENT_DIR = BASE_DIR
REGISTRY_PATH = CONTENT_DIR / 'registry' / 'books_manifest.json'


@lru_cache(maxsize=1)
def _load_manifest() -> Dict[str, Any]:
    if not REGISTRY_PATH.exists():
        return {'books': []}
    with REGISTRY_PATH.open('r', encoding='utf-8') as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _load_registry_entries() -> List[Dict[str, Any]]:
    manifest = _load_manifest()
    return [_build_registry_entry(item) for item in manifest.get('books', [])]


def _build_registry_entry(item: Dict[str, Any]) -> Dict[str, Any]:
    # 相对路径基于 registry/ 目录解析，而非 content/textbook/
    registry_dir = REGISTRY_PATH.parent
    metadata_rel = item.get('metadata_path')
    metadata_abs = (registry_dir / metadata_rel).resolve() if metadata_rel else None
    metadata = _read_json(metadata_abs) if metadata_abs and metadata_abs.exists() else {}

    source_rel = item.get('book_path')
    processed_rel = item.get('processed_path')
    source_abs = (registry_dir / source_rel).resolve() if source_rel else None
    processed_abs = (registry_dir / processed_rel).resolve() if processed_rel else None

    title = metadata.get('title') or item.get('title') or item['book_id']
    subtitle = metadata.get('subtitle', '')
    description = metadata.get('description') or item.get('description', '')
    enabled = bool(metadata.get('enabled', item.get('enabled', False)))
    ingest_status = metadata.get('ingest_status') or item.get('ingest_status', 'unknown')

    return {
        'book_id': item['book_id'],
        'title': title,
        'subtitle': subtitle,
        'description': description,
        'subject': metadata.get('subject', ''),
        'version': metadata.get('version', ''),
        'source_type': metadata.get('source_type') or item.get('source_type', 'unknown'),
        'enabled': enabled,
        'ingest_status': ingest_status,
        'visibility': item.get('visibility', 'internal'),
        'entry_chapter': metadata.get('entry_chapter'),
        'tags': metadata.get('tags', []),
        'book_path': source_rel,
        'metadata_path': metadata_rel,
        'processed_path': processed_rel,
        'source_exists': bool(source_abs and source_abs.exists()),
        'processed_exists': bool(processed_abs and processed_abs.exists()),
        'source_absolute_path': str(source_abs) if source_abs else None,
        'processed_absolute_path': str(processed_abs) if processed_abs else None,
        'metadata': metadata,
    }


def _read_json(path: Path) -> Dict[str, Any]:
    with path.open('r', encoding='utf-8') as f:
        return json.load(f)


def list_registered_books(include_disabled: bool = True) -> List[Dict[str, Any]]:
    books = _load_registry_entries()
    if include_disabled:
        return books
    return [book for book in books if book['enabled']]


def get_book_registry(book_id: str) -> Optional[Dict[str, Any]]:
    for book in _load_registry_entries():
        if book['book_id'] == book_id:
            return book
    return None


def get_book_metadata(book_id: str) -> Optional[Dict[str, Any]]:
    book = get_book_registry(book_id)
    if not book:
        return None
    return book['metadata']


def resolve_book_location(book_id: str, prefer_processed: bool = False) -> Optional[str]:
    book = get_book_registry(book_id)
    if not book:
        return None

    processed_abs = book.get('processed_absolute_path')
    source_abs = book.get('source_absolute_path')

    if prefer_processed and processed_abs:
        processed_path = Path(processed_abs)
        return str(processed_path.parent if processed_path.is_file() else processed_path)

    if source_abs:
        source_path = Path(source_abs)
        return str(source_path.parent if source_path.is_file() else source_path)

    if processed_abs:
        processed_path = Path(processed_abs)
        return str(processed_path.parent if processed_path.is_file() else processed_path)

    return None


def get_default_book_id() -> Optional[str]:
    enabled_books = list_registered_books(include_disabled=False)
    if enabled_books:
        return enabled_books[0]['book_id']

    books = list_registered_books(include_disabled=True)
    if books:
        return books[0]['book_id']

    return None
