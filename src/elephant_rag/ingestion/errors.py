"""Parser-independent extraction error contract."""


class PDFExtractionError(ValueError):
    """Safe error details for a future ingestion status or HTTP response."""

    error_code = "PDF_EXTRACTION_FAILED"
    status_code = 422
    status = "failed"

    def __init__(
        self,
        page_number: int | None = None,
        *,
        message: str = "Could not extract Markdown from the PDF.",
    ) -> None:
        super().__init__(message)
        self.page_number = page_number


class OCRNotSupportedError(PDFExtractionError):
    error_code = "OCR_NOT_SUPPORTED"

    def __init__(
        self,
        *,
        total_pages: int,
        checked_pages: int,
        low_text_page_numbers: tuple[int, ...],
        min_text_chars_per_page: int,
        max_low_text_page_percent: int,
    ) -> None:
        super().__init__(
            page_number=checked_pages,
            message=(
                "This PDF has too little extractable text. "
                "Upload a text-based PDF; OCR is not supported."
            ),
        )
        self.total_pages = total_pages
        self.checked_pages = checked_pages
        self.low_text_page_numbers = low_text_page_numbers
        self.min_text_chars_per_page = min_text_chars_per_page
        self.max_low_text_page_percent = max_low_text_page_percent
