"""Markdown-aware token windows with exact offsets into original page Markdown."""

import re
from hashlib import sha256
from uuid import UUID, uuid5

from elephant_rag.chunking.markdown import markdown_blocks
from elephant_rag.chunking.tokenizer import token_count
from elephant_rag.ingestion.normalization import NormalizedDocument, NormalizedPage
from elephant_rag.schemas.chunks import ChunkSchema


def _fit_end(text: str, start: int, budget: int) -> int:
    low, high = start, len(text)
    while low < high:
        middle = (low + high + 1) // 2
        if token_count(text[start:middle]) <= budget:
            low = middle
        else:
            high = middle - 1
    while low > start and token_count(text[start:low]) > budget:
        low -= 1
    return max(start + 1, low)


def _overlap_start(text: str, start: int, end: int, budget: int) -> int:
    low, high = start, end
    while low < high:
        middle = (low + high) // 2
        if token_count(text[middle:end]) <= budget:
            high = middle
        else:
            low = middle + 1
    return low


class MarkdownChunker:
    def __init__(
        self, *, min_tokens: int = 600, max_tokens: int = 800, overlap_tokens: int = 100
    ) -> None:
        if not 0 <= overlap_tokens < min_tokens <= max_tokens:
            raise ValueError("Chunk budgets require 0 <= overlap < minimum <= maximum")
        self.min_tokens = min_tokens
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens

    def _page_spans(self, page: NormalizedPage) -> list[tuple[int, int, bool]]:
        text = page.normalized_text
        blocks = markdown_blocks(text)
        atomic = [block for block in blocks if block.kind in {"table", "code"}]
        result: list[tuple[int, int, bool]] = []
        start = 0
        while start < len(text):
            while start < len(text) and text[start].isspace():
                start += 1
            if start == len(text):
                break
            hard_end = _fit_end(text, start, self.max_tokens)
            crossing = next((block for block in atomic if block.start < hard_end < block.end), None)
            oversized = False
            if crossing:
                if crossing.start > start and text[start : crossing.start].strip():
                    hard_end = crossing.start
                else:
                    hard_end = crossing.end
                    oversized = token_count(text[start:hard_end]) > self.max_tokens
            end = hard_end
            if hard_end < len(text) and not oversized:
                # Prefer a section boundary, then paragraphs, sentences, words,
                # finally Unicode character boundaries for an indivisible long word.
                headings = [
                    block.start
                    for block in blocks
                    if block.kind == "heading" and start < block.start <= hard_end
                ]
                paragraph_ends = [
                    block.end
                    for block in blocks
                    if start < block.end <= hard_end and block.kind != "blank"
                ]
                for boundaries in (headings, paragraph_ends):
                    eligible = [
                        offset
                        for offset in boundaries
                        if token_count(text[start:offset]) >= self.min_tokens
                    ]
                    if eligible:
                        end = max(eligible)
                        break
                else:
                    for pattern in (r"[.!?]\s+", r"\s+"):
                        candidates = [
                            start + match.end()
                            for match in re.finditer(pattern, text[start:hard_end])
                        ]
                        eligible = [
                            offset
                            for offset in candidates
                            if token_count(text[start:offset]) >= self.min_tokens
                        ]
                        if eligible:
                            end = max(eligible)
                            break
            # Natural boundaries must not split a protected Markdown block either.
            containing = next((block for block in atomic if block.start < end < block.end), None)
            if containing:
                end = containing.start if containing.start > start else containing.end
            while end > start and text[end - 1].isspace():
                end -= 1
            if end <= start:
                raise ValueError("Chunker made no progress")
            if result and end <= result[-1][1]:
                # An atomic block may not fit alongside overlap. Drop that overlap
                # rather than repeatedly emitting the same prefix before the block.
                start = max(start + 1, result[-1][1])
                continue
            oversized = token_count(text[start:end]) > self.max_tokens
            result.append((start, end, oversized))
            if not text[end:].strip():
                break
            next_start = _overlap_start(text, start, end, self.overlap_tokens)
            overlapped_atomic = next(
                (block for block in atomic if block.start <= next_start < block.end), None
            )
            if overlapped_atomic:
                next_start = overlapped_atomic.end
            start = max(start + 1, next_start)
        return result

    def split(self, document: NormalizedDocument, *, document_id: UUID) -> tuple[ChunkSchema, ...]:
        chunks: list[ChunkSchema] = []
        for page in document.pages:
            for start, end, oversized in self._page_spans(page):
                raw_start, raw_end = page.raw_span(start, end)
                normalized = page.normalized_text[start:end]
                digest = sha256(normalized.encode()).hexdigest()
                identity = f"{page.page_number}:{raw_start}:{raw_end}:{digest}"
                chunks.append(
                    ChunkSchema(
                        id=str(uuid5(document_id, identity)),
                        document_id=str(document_id),
                        chunk_index=len(chunks),
                        raw_text=page.raw_text[raw_start:raw_end],
                        normalized_text=normalized,
                        page_start=page.page_number,
                        page_end=page.page_number,
                        char_start=raw_start,
                        char_end=raw_end,
                        metadata={
                            "token_count": token_count(normalized),
                            "tokenizer": "cl100k_base",
                            "oversized_atomic": oversized,
                            "normalized_char_start": start,
                            "normalized_char_end": end,
                        },
                    )
                )
        return tuple(chunks)
