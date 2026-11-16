"""Conservative running-header/footer removal with exact source mappings."""

import re
from collections import defaultdict
from dataclasses import dataclass
from math import ceil
from typing import Literal

from elephant_rag.chunking.markdown import HEADING, markdown_blocks
from elephant_rag.ingestion.extraction import ExtractedDocument


@dataclass(frozen=True)
class RemovedBoundary:
    char_start: int
    char_end: int
    kind: Literal["header", "footer"]


@dataclass(frozen=True)
class SourceSpan:
    normalized_start: int
    normalized_end: int
    raw_start: int
    raw_end: int


@dataclass(frozen=True)
class NormalizedPage:
    page_number: int
    raw_text: str
    normalized_text: str
    source_spans: tuple[SourceSpan, ...]
    removed_boundaries: tuple[RemovedBoundary, ...]

    def raw_span(self, start: int, end: int) -> tuple[int, int]:
        if not 0 <= start < end <= len(self.normalized_text):
            raise ValueError("Normalized span must be nonempty and inside the page")
        first = next(
            span
            for span in self.source_spans
            if span.normalized_start <= start < span.normalized_end
        )
        last = next(
            span
            for span in self.source_spans
            if span.normalized_start <= end - 1 < span.normalized_end
        )
        return (
            first.raw_start + start - first.normalized_start,
            last.raw_start + end - last.normalized_start,
        )


@dataclass(frozen=True)
class NormalizedDocument:
    source: ExtractedDocument
    pages: tuple[NormalizedPage, ...]


def _boundary_key(line: str, kind: str) -> str | None:
    value = " ".join(line.strip().split()).strip("*_` ")
    if not value or len(value) > 160 or len(value.split()) > 20:
        return None
    # Complete prose sentences at a page edge are evidence, not running chrome.
    if value.endswith((".", "!", "?")):
        return None
    if HEADING.match(line) or re.match(r"\s*(?:[-*+]|\d+[.)])\s+", line):
        return None
    if line.lstrip().startswith((">", "`", "$", "\\[")):
        return None
    value = re.sub(r"\bpage\s+\d+(?:\s*(?:of|/)\s*\d+)?\b", "page #", value, flags=re.I)
    if kind == "footer" and re.fullmatch(r"\d+(?:\s*/\s*\d+)?", value):
        value = "<page-number>"
    return value.casefold()


class MarkdownNormalizer:
    def normalize(self, document: ExtractedDocument) -> NormalizedDocument:
        # Require independent support on at least two pages and 60% of the PDF.
        required = max(2, ceil(len(document.pages) * 0.6))
        candidates: dict[tuple[str, str], set[int]] = defaultdict(set)
        page_candidates: list[list[tuple[int, int, Literal["header", "footer"], str]]] = []
        for page_index, page in enumerate(document.pages):
            raw = page.raw_text
            protected = [
                block
                for block in markdown_blocks(raw)
                if block.kind in {"table", "code", "heading"}
            ]
            lines = raw.splitlines(keepends=True)
            offsets = [0]
            for line in lines:
                offsets.append(offsets[-1] + len(line))
            matches = []
            # Physical boundary windows: placeholders retain line positions after cleanup.
            header = next((i for i in range(min(2, len(lines))) if lines[i].strip()), None)
            footer = next(
                (i for i in range(len(lines) - 1, max(-1, len(lines) - 4), -1) if lines[i].strip()),
                None,
            )
            windows: list[tuple[Literal["header", "footer"], list[int]]] = [
                ("header", [] if header is None else [header]),
                ("footer", [] if footer is None else [footer]),
            ]
            for kind, indices in windows:
                for index in indices:
                    start = offsets[index]
                    end = offsets[index + 1] - len(lines[index]) + len(lines[index].rstrip("\r\n"))
                    if start == end or any(block.start <= start < block.end for block in protected):
                        continue
                    key = _boundary_key(lines[index], kind)
                    if key is not None:
                        candidates[(kind, key)].add(page_index)
                        matches.append((start, end, kind, key))
            page_candidates.append(matches)

        normalized_pages = []
        for page, matches in zip(document.pages, page_candidates, strict=True):
            removed = []
            seen: set[tuple[int, int]] = set()
            for start, end, kind, key in sorted(matches):
                if len(candidates[(kind, key)]) >= required and (start, end) not in seen:
                    removed.append(RemovedBoundary(start, end, kind))
                    seen.add((start, end))
            spans = []
            parts = []
            cursor = 0
            normalized_offset = 0
            for removal in [
                *removed,
                RemovedBoundary(len(page.raw_text), len(page.raw_text), "footer"),
            ]:
                if cursor < removal.char_start:
                    part = page.raw_text[cursor : removal.char_start]
                    spans.append(
                        SourceSpan(
                            normalized_offset,
                            normalized_offset + len(part),
                            cursor,
                            removal.char_start,
                        )
                    )
                    parts.append(part)
                    normalized_offset += len(part)
                cursor = removal.char_end
            normalized_pages.append(
                NormalizedPage(
                    page.page_number, page.raw_text, "".join(parts), tuple(spans), tuple(removed)
                )
            )
        return NormalizedDocument(document, tuple(normalized_pages))
