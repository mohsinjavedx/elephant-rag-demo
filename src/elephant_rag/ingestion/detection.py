"""Deterministic text-density checks without OCR or Markdown formatting."""

from collections.abc import Iterable
from dataclasses import dataclass

from elephant_rag.ingestion.errors import OCRNotSupportedError, PDFExtractionError


@dataclass(frozen=True)
class TextDensityReport:
    text_char_counts: tuple[int, ...]
    low_text_page_numbers: tuple[int, ...]
    min_text_chars_per_page: int
    max_low_text_page_percent: int


class PDFTextDensityDetector:
    def __init__(
        self,
        *,
        min_text_chars_per_page: int = 50,
        max_low_text_page_percent: int = 80,
    ) -> None:
        if not 1 <= min_text_chars_per_page <= 10000:
            raise ValueError("Minimum text characters must be between 1 and 10000")
        if not 0 <= max_low_text_page_percent <= 99:
            raise ValueError("Maximum low-text page percentage must be between 0 and 99")
        self.min_chars = min_text_chars_per_page
        self.max_low_percent = max_low_text_page_percent

    def check(self, page_texts: Iterable[str], *, page_count: int) -> TextDensityReport:
        """Reject as soon as low-text pages exceed the whole-document allowance.

        Count printable, non-whitespace Unicode characters from the PDF text layer.
        Integer cross multiplication preserves the strict 'more than 80%' boundary.
        """
        if page_count < 1:
            raise PDFExtractionError()
        counts: list[int] = []
        low_pages: list[int] = []
        for number, text in enumerate(page_texts, start=1):
            if number > page_count:
                raise PDFExtractionError(number)
            count = sum(character.isprintable() and not character.isspace() for character in text)
            counts.append(count)
            if count < self.min_chars:
                low_pages.append(number)
            if len(low_pages) * 100 > self.max_low_percent * page_count:
                raise OCRNotSupportedError(
                    total_pages=page_count,
                    checked_pages=number,
                    low_text_page_numbers=tuple(low_pages),
                    min_text_chars_per_page=self.min_chars,
                    max_low_text_page_percent=self.max_low_percent,
                )
        if len(counts) != page_count:
            raise PDFExtractionError()
        return TextDensityReport(
            text_char_counts=tuple(counts),
            low_text_page_numbers=tuple(low_pages),
            min_text_chars_per_page=self.min_chars,
            max_low_text_page_percent=self.max_low_percent,
        )
