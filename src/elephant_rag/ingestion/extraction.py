"""Page-preserving Markdown extraction for structurally validated PDFs."""

from dataclasses import dataclass
from importlib.metadata import version
from typing import Any, cast

import pymupdf
import pymupdf4llm

from elephant_rag.ingestion.detection import PDFTextDensityDetector, TextDensityReport
from elephant_rag.ingestion.errors import PDFExtractionError
from elephant_rag.ingestion.validation import ValidatedPDF

# Use geometric column/table analysis instead of loading the optional ONNX layout
# model. This keeps extraction suitable for the project's small-memory backend.
# Configure it once at import, not by toggling process-global state per request.
pymupdf4llm.use_layout(False)


@dataclass(frozen=True)
class ExtractedPage:
    page_number: int
    raw_text: str


@dataclass(frozen=True)
class ExtractedDocument:
    checksum: str
    size_bytes: int
    pages: tuple[ExtractedPage, ...]
    parser: str
    parser_version: str
    text_density: TextDensityReport

    @property
    def page_count(self) -> int:
        return len(self.pages)


class PDFMarkdownExtractor:
    def __init__(self, *, text_detector: PDFTextDensityDetector | None = None) -> None:
        self.text_detector = text_detector or PDFTextDensityDetector()

    @staticmethod
    def _remove_text_backgrounds(document: pymupdf.Document) -> None:
        """Remove decorative fills from the in-memory copy, preserving text/tables.

        The geometric backend otherwise treats some shaded text boxes as figures
        and omits their text. Table rectangles and existing redactions are left alone.
        """
        for index in range(document.page_count):
            # Native Page methods have incomplete annotations. Keep this dynamic
            # boundary local; extraction results are checked and typed below.
            page = cast(Any, document[index])
            if any(page.annots(types=[pymupdf.PDF_ANNOT_REDACT])):
                continue
            candidates = [
                drawing["rect"]
                for drawing in page.get_drawings()
                if drawing["type"] == "f"
                and len(drawing["items"]) == 1
                and drawing["items"][0][0] == "re"
                and drawing["rect"].width >= 8
                and drawing["rect"].height >= 8
                and drawing["rect"].get_area() < page.rect.get_area() * 0.95
            ]
            if not candidates:
                continue
            tables = page.find_tables(strategy="lines_strict")
            table_rects = [
                pymupdf.Rect(table.bbox)  # type: ignore[no-untyped-call]
                for table in tables.tables
                if table.row_count >= 2 and table.col_count >= 2
            ]
            text_rects = [
                pymupdf.Rect(block[:4])  # type: ignore[no-untyped-call]
                for block in page.get_text("blocks")
                if block[6] == 0
            ]
            changed = False
            for rect in candidates:
                if any(rect.intersects(table) for table in table_rects) or not any(
                    rect.intersects(text) for text in text_rects
                ):
                    continue
                page.add_redact_annot(rect, fill=False, cross_out=False)
                changed = True
            if changed:
                page.apply_redactions(
                    images=pymupdf.PDF_REDACT_IMAGE_NONE,
                    graphics=pymupdf.PDF_REDACT_LINE_ART_REMOVE_IF_COVERED,
                    text=pymupdf.PDF_REDACT_TEXT_NONE,
                )

    def extract(self, pdf: ValidatedPDF) -> ExtractedDocument:
        """Read the UUID-staged file while the validation context is still open.

        Raw Markdown is preserved exactly, with one-based PDF page numbers.
        Text density is checked before layout analysis; normalization follows later.
        """
        page_number: int | None = None
        try:
            # The native Document constructor has no type signature in this release.
            # Validation already bounded the file to 20 MiB. Opening its bytes also
            # prevents dependency-internal file handles from blocking Windows cleanup.
            with pymupdf.open(  # type: ignore[no-untyped-call]
                stream=pdf.path.read_bytes(), filetype="pdf"
            ) as document:
                if not document.is_pdf or document.page_count != pdf.page_count:
                    raise PDFExtractionError()
                # Check the original text layer before Markdown, font scanning, or
                # decorative-graphics handling. The lazy iterator permits early abort.
                density = self.text_detector.check(
                    (document[index].get_text("text") for index in range(pdf.page_count)),
                    page_count=pdf.page_count,
                )
                self._remove_text_backgrounds(document)
                # Scan font sizes once per document, not once for every requested page.
                headers = pymupdf4llm.IdentifyHeaders(document)
                pages = []
                for index in range(pdf.page_count):
                    page_number = index + 1
                    result = pymupdf4llm.to_markdown(
                        document,
                        pages=[index],
                        page_chunks=True,
                        hdr_info=headers,
                        margins=0,
                        ignore_images=True,
                        write_images=False,
                        embed_images=False,
                        force_text=True,
                        table_output="markdown",
                        show_progress=False,
                    )
                    # Validate the dependency's response instead of silently dropping pages.
                    if not isinstance(result, list) or len(result) != 1:
                        raise PDFExtractionError(page_number)
                    page = result[0]
                    if not isinstance(page, dict) or not isinstance(page.get("text"), str):
                        raise PDFExtractionError(page_number)
                    if (
                        density.text_char_counts[index] >= self.text_detector.min_chars
                        and not page["text"].strip()
                    ):
                        # Substantial source text with empty Markdown is a parser
                        # failure, not evidence that the PDF requires OCR.
                        raise PDFExtractionError(page_number)
                    metadata = page.get("metadata")
                    if not isinstance(metadata, dict) or metadata.get("page") != page_number:
                        raise PDFExtractionError(page_number)
                    pages.append(ExtractedPage(page_number, page["text"]))
        except PDFExtractionError:
            raise
        except Exception:
            # Dependency exceptions can contain PDF text, paths, or metadata.
            raise PDFExtractionError(page_number) from None

        return ExtractedDocument(
            checksum=pdf.checksum,
            size_bytes=pdf.size_bytes,
            pages=tuple(pages),
            parser="pymupdf4llm",
            parser_version=version("pymupdf4llm"),
            text_density=density,
        )
