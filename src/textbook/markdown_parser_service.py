from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


HEADING_RE = re.compile(r'^(#{1,6})\s+(.*)$')
NON_WORD_RE = re.compile(r'[^a-z0-9\u4e00-\u9fff]+')
SPACE_RE = re.compile(r'\s+')


@dataclass
class HeadingNode:
    level: int
    title: str
    slug: str
    anchor: str
    line_no: int


class MarkdownBookParser:
    def __init__(self, book_dir: Path) -> None:
        self.book_dir = book_dir
        self.book_meta_path = book_dir / 'book.json'
        self.chapters_dir = book_dir / 'chapters'
        self.config_dir = book_dir / 'config'

    def parse(self) -> Dict[str, Any]:
        metadata = self._read_json(self.book_meta_path)
        concepts = self._load_concepts()
        keywords = self._load_keywords()
        keyword_terms = {item['term'] for item in keywords}

        book_id = metadata['book_id']
        chapter_files = self._resolve_chapter_files(metadata)

        chapters: List[Dict[str, Any]] = []
        sections: List[Dict[str, Any]] = []
        blocks: List[Dict[str, Any]] = []

        for chapter_order, chapter_path in enumerate(chapter_files, start=1):
            chapter_result = self._parse_chapter_file(
                book_id=book_id,
                chapter_path=chapter_path,
                chapter_order=chapter_order,
                concepts=concepts,
                keyword_terms=keyword_terms,
            )
            chapters.append(chapter_result['chapter'])
            sections.extend(chapter_result['sections'])
            blocks.extend(chapter_result['blocks'])

        return {
            'book': {
                'id': book_id,
                'title': metadata.get('title', book_id),
                'subtitle': metadata.get('subtitle', ''),
                'description': metadata.get('description', ''),
                'subject': metadata.get('subject', ''),
                'version': metadata.get('version', ''),
                'language': metadata.get('language', 'zh-CN'),
                'source_type': metadata.get('source_type', 'markdown'),
                'entry_chapter': metadata.get('entry_chapter'),
                'tags': metadata.get('tags', []),
            },
            'concepts': concepts,
            'keywords': keywords,
            'chapters': chapters,
            'sections': sections,
            'blocks': blocks,
        }

    def _parse_chapter_file(
        self,
        book_id: str,
        chapter_path: Path,
        chapter_order: int,
        concepts: List[Dict[str, Any]],
        keyword_terms: set[str],
    ) -> Dict[str, Any]:
        raw_text = chapter_path.read_text(encoding='utf-8')
        lines = raw_text.splitlines()
        chapter_file_slug = chapter_path.stem

        headings = self._collect_headings(lines, fallback_slug=chapter_file_slug)
        chapter_heading = next((item for item in headings if item.level == 1), None)
        chapter_title = chapter_heading.title if chapter_heading else chapter_file_slug
        chapter_slug = chapter_file_slug
        chapter_anchor = f'chapter-{chapter_slug}'
        chapter_id = f'{book_id}__chapter__{chapter_slug}'

        sections: List[Dict[str, Any]] = []
        blocks: List[Dict[str, Any]] = []
        current_section: Optional[Dict[str, Any]] = None
        current_paragraph_lines: List[str] = []
        block_order = 0
        section_order = 0

        def finalize_block() -> None:
            nonlocal block_order, current_paragraph_lines
            if not current_section or not current_paragraph_lines:
                current_paragraph_lines = []
                return

            raw_paragraph = '\n'.join(current_paragraph_lines).strip()
            clean_text = self._clean_text(raw_paragraph)
            if not clean_text:
                current_paragraph_lines = []
                return

            block_order += 1
            section_block_order = len(current_section['blockIds']) + 1
            block_id = f"{book_id}__block__{chapter_slug}__{current_section['slug']}__{section_block_order}"
            block_anchor = f"{current_section['anchor']}-block-{section_block_order}"
            concept_refs = self._match_concepts(clean_text, concepts)
            keyword_refs = self._match_keywords(clean_text, keyword_terms)

            block = {
                'id': block_id,
                'book_id': book_id,
                'chapter_id': chapter_id,
                'section_id': current_section['id'],
                'order': block_order,
                'section_order': section_block_order,
                'anchor': block_anchor,
                'raw_text': raw_paragraph,
                'clean_text': clean_text,
                'token_estimate': self._estimate_tokens(clean_text),
                'concept_refs': concept_refs,
                'keyword_refs': keyword_refs,
            }
            blocks.append(block)
            current_section['blockIds'].append(block_id)
            current_paragraph_lines = []

        def start_section(title: str) -> None:
            nonlocal current_section, section_order
            finalize_block()
            section_order += 1
            base_slug = self._slugify(title) or f'section-{section_order}'
            section_slug = f'{chapter_slug}-{base_slug}'
            section_anchor = f'section-{section_slug}'
            current_section = {
                'id': f'{book_id}__section__{section_slug}',
                'title': title,
                'order': section_order,
                'chapter_id': chapter_id,
                'slug': section_slug,
                'anchor': section_anchor,
                'summary': '',
                'blockIds': [],
            }
            sections.append(current_section)

        if not any(item.level == 2 for item in headings):
            start_section('正文')

        for line in lines:
            stripped = line.strip()
            heading_match = HEADING_RE.match(stripped)
            if heading_match:
                level = len(heading_match.group(1))
                title = heading_match.group(2).strip()
                if level == 1:
                    finalize_block()
                    continue
                if level == 2:
                    start_section(title)
                    continue
                finalize_block()
                if current_section:
                    current_paragraph_lines.append(title)
                continue

            if not stripped:
                finalize_block()
                continue

            if current_section is None:
                start_section('正文')
            current_paragraph_lines.append(stripped)

        finalize_block()

        for section in sections:
            section_blocks = [block for block in blocks if block['section_id'] == section['id']]
            if section_blocks:
                section['summary'] = section_blocks[0]['clean_text'][:80]

        chapter_summary = sections[0]['summary'] if sections else ''
        chapter = {
            'id': chapter_id,
            'title': chapter_title,
            'order': chapter_order,
            'slug': chapter_slug,
            'anchor': chapter_anchor,
            'summary': chapter_summary,
            'sectionIds': [section['id'] for section in sections],
            'source_file': chapter_path.name,
        }

        normalized_sections = [
            {
                'id': section['id'],
                'title': section['title'],
                'order': section['order'],
                'chapter_id': section['chapter_id'],
                'slug': section['slug'],
                'anchor': section['anchor'],
                'summary': section['summary'],
                'blockIds': section['blockIds'],
            }
            for section in sections
        ]

        return {
            'chapter': chapter,
            'sections': normalized_sections,
            'blocks': blocks,
        }

    def _resolve_chapter_files(self, metadata: Dict[str, Any]) -> List[Path]:
        chapter_order = metadata.get('chapter_order', [])
        ordered_paths = [self.chapters_dir / f'{chapter_name}.md' for chapter_name in chapter_order]
        if chapter_order:
            return [path for path in ordered_paths if path.exists()]
        return sorted(self.chapters_dir.glob('*.md'))

    def _load_concepts(self) -> List[Dict[str, Any]]:
        path = self.config_dir / 'concepts.json'
        if not path.exists():
            return []
        data = self._read_json(path)
        concepts = []
        for item in data.get('concepts', []):
            concepts.append(
                {
                    'id': item['id'],
                    'name': item['name'],
                    'aliases': item.get('aliases', []),
                    'short_description': item.get('short_description', f"用于标记教材中与{item['name']}相关的段落。"),
                }
            )
        return concepts

    def _load_keywords(self) -> List[Dict[str, Any]]:
        path = self.config_dir / 'keywords.json'
        if not path.exists():
            return []
        data = self._read_json(path)
        return [{'id': f'keyword-{self._slugify(item)}', 'term': item} for item in data.get('keywords', [])]

    def _collect_headings(self, lines: List[str], fallback_slug: str) -> List[HeadingNode]:
        headings: List[HeadingNode] = []
        for line_no, line in enumerate(lines, start=1):
            match = HEADING_RE.match(line.strip())
            if not match:
                continue
            title = match.group(2).strip()
            slug = self._slugify(title) or fallback_slug
            headings.append(
                HeadingNode(
                    level=len(match.group(1)),
                    title=title,
                    slug=slug,
                    anchor=f'h{len(match.group(1))}-{slug}',
                    line_no=line_no,
                )
            )
        return headings

    def _match_concepts(self, text: str, concepts: List[Dict[str, Any]]) -> List[str]:
        refs = []
        for concept in concepts:
            candidates = [concept['name'], *concept.get('aliases', [])]
            if any(candidate and candidate in text for candidate in candidates):
                refs.append(concept['id'])
        return refs

    def _match_keywords(self, text: str, keyword_terms: set[str]) -> List[str]:
        refs = []
        for term in sorted(keyword_terms):
            if term in text:
                refs.append(f'keyword-{self._slugify(term)}')
        return refs

    def _estimate_tokens(self, text: str) -> int:
        stripped = SPACE_RE.sub('', text)
        return max(1, len(stripped) // 2)

    def _clean_text(self, text: str) -> str:
        lines = [line.strip() for line in text.splitlines()]
        cleaned = ' '.join(line for line in lines if line)
        return SPACE_RE.sub(' ', cleaned).strip()

    def _slugify(self, value: str) -> str:
        lowered = value.strip().lower()
        normalized = NON_WORD_RE.sub('-', lowered)
        return normalized.strip('-')

    def _read_json(self, path: Path) -> Dict[str, Any]:
        with path.open('r', encoding='utf-8') as f:
            return json.load(f)


def parse_book_directory(book_dir: Path) -> Dict[str, Any]:
    return MarkdownBookParser(book_dir).parse()
