from __future__ import annotations

from flask import jsonify, request

from src.textbook import textbook_bp
from src.textbook.book_registry_service import (
    get_book_metadata,
    get_book_registry,
    get_default_book_id,
    list_registered_books,
    resolve_book_location,
)
from src.textbook.content_service import (
    build_companion_payload,
    generate_companion_chat_reply,
    get_book_cards,
    get_knowledge_structure_data,
    get_reader_page_data,
)

ALLOWED_COMPANION_ACTIONS = {'explain', 'ask', 'note'}


@textbook_bp.route('/api/textbook/books', methods=['GET'])
def textbook_books():
    include_disabled = request.args.get('include_disabled', 'true').lower() != 'false'
    books_data = list_registered_books(include_disabled=include_disabled)
    return jsonify(
        {
            'books': [
                {
                    'book_id': book['book_id'],
                    'title': book['title'],
                    'subtitle': book['subtitle'],
                    'description': book['description'],
                    'subject': book['subject'],
                    'version': book['version'],
                    'source_type': book['source_type'],
                    'enabled': book['enabled'],
                    'ingest_status': book['ingest_status'],
                    'visibility': book['visibility'],
                }
                for book in books_data
            ]
        }
    )


@textbook_bp.route('/api/textbook/books/<book_id>', methods=['GET'])
def textbook_book_detail(book_id: str):
    registry_book = get_book_registry(book_id)
    if not registry_book:
        return jsonify({'error': f'Unknown book_id: {book_id}'}), 404

    return jsonify(
        {
            'book_id': registry_book['book_id'],
            'enabled': registry_book['enabled'],
            'metadata': get_book_metadata(book_id),
            'source_directory': resolve_book_location(book_id, prefer_processed=False),
            'processed_directory': resolve_book_location(book_id, prefer_processed=True),
            'registry': {
                'source_type': registry_book['source_type'],
                'ingest_status': registry_book['ingest_status'],
                'visibility': registry_book['visibility'],
            },
        }
    )


@textbook_bp.route('/api/textbook/reader', methods=['GET'])
def textbook_reader():
    import time
    start_time = time.time()
    
    book_id = request.args.get('book_id', '').strip() or get_default_book_id()
    chapter_id = request.args.get('chapter_id', '').strip() or None
    
    print(f"[textbook_reader] book_id={book_id}, chapter_id={chapter_id}")

    if not book_id:
        return jsonify({'error': 'No registered books available'}), 404

    try:
        page_data = get_reader_page_data(book_id, chapter_id=chapter_id)
        elapsed = time.time() - start_time
        print(f"[textbook_reader] success, elapsed={elapsed:.2f}s, chapter={page_data.get('chapter', {}).get('title', 'N/A')}")
    except KeyError as e:
        print(f"[textbook_reader] KeyError: {e}")
        return jsonify({'error': f'Unknown book_id: {book_id}'}), 404
    except Exception as e:
        print(f"[textbook_reader] Exception: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

    return jsonify(page_data)


@textbook_bp.route('/api/textbook/knowledge-structure', methods=['GET'])
def textbook_knowledge_structure():
    book_id = request.args.get('book_id', '').strip() or get_default_book_id()

    if not book_id:
        return jsonify({'error': 'No registered books available'}), 404

    try:
        data = get_knowledge_structure_data(book_id)
    except KeyError:
        return jsonify({'error': f'Unknown book_id: {book_id}'}), 404

    return jsonify(data)


@textbook_bp.route('/api/textbook/companion/action', methods=['POST'])
def textbook_companion_action():
    request_data = request.get_json(silent=True) or {}

    def pick_value(key: str, default: str = '') -> str:
        return str(request_data.get(key, default) or '').strip()

    block_id = pick_value('block_id')
    book_id = pick_value('book_id') or get_default_book_id()
    action = pick_value('action').lower()
    selected_text = pick_value('selected_text')

    if action not in ALLOWED_COMPANION_ACTIONS:
        return jsonify({'error': f'Unsupported action: {action}', 'available_actions': sorted(ALLOWED_COMPANION_ACTIONS)}), 400
    if not block_id:
        return jsonify({'error': 'block_id is required'}), 400
    if not book_id:
        return jsonify({'error': 'book_id is required'}), 400

    try:
        return jsonify(
            build_companion_payload(
                book_id=book_id,
                block_id=block_id,
                action=action,
                selected_text=selected_text,
            )
        )
    except KeyError:
        return jsonify({'error': f'Unknown book_id or block_id: {book_id}, {block_id}'}), 404
    except Exception as exc:
        return jsonify(
            {
                'error': 'companion action failed',
                'message': str(exc),
                'action': action,
            }
        ), 500


@textbook_bp.route('/api/textbook/companion/chat', methods=['POST'])
def textbook_companion_chat():
    request_data = request.get_json(silent=True) or {}

    def pick_value(key: str, default: str = '') -> str:
        return str(request_data.get(key, default) or '').strip()

    book_id = pick_value('book_id') or get_default_book_id()
    block_id = pick_value('block_id')
    question = pick_value('question')
    selected_text = pick_value('selected_text')

    history = request_data.get('history') or []
    if not isinstance(history, list):
        history = []

    if not book_id:
        return jsonify({'error': 'book_id is required'}), 400
    if not block_id:
        return jsonify({'error': 'block_id is required'}), 400
    if not question:
        return jsonify({'error': 'question is required'}), 400

    try:
        payload = generate_companion_chat_reply(
            book_id=book_id,
            block_id=block_id,
            question=question,
            selected_text=selected_text,
            history=history,
        )
        return jsonify(payload)
    except KeyError:
        return jsonify({'error': f'Unknown book_id or block_id: {book_id}, {block_id}'}), 404
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    except Exception as exc:
        return jsonify({'error': 'companion chat failed', 'message': str(exc)}), 500
