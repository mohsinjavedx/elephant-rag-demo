"""Bounded PDF intake without text extraction or persistent storage."""

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import BinaryIO
from uuid import uuid4

from pypdf import PdfReader
from pypdf.errors import PyPdfError

MEBIBYTE = 1024 * 1024
COPY_CHUNK_SIZE = 64 * 1024


class PDFValidationError(ValueError):
    """A safe, stable error that can be mapped to a future HTTP response."""

    def __init__(self, error_code: str, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.status_code = status_code


@dataclass(frozen=True)
class ValidatedPDF:
    """The path is usable only inside the validator's context manager."""

    path: Path
    size_bytes: int
    page_count: int
    checksum: str


class PDFValidator:
    def __init__(
        self,
        *,
        max_upload_mb: int = 20,
        max_pdf_pages: int = 100,
        temp_root: Path | None = None,
    ) -> None:
        if not 1 <= max_upload_mb <= 20 or not 1 <= max_pdf_pages <= 100:
            raise ValueError("PDF limits must be within 1-20 MiB and 1-100 pages")
        self.max_bytes = max_upload_mb * MEBIBYTE
        self.max_pages = max_pdf_pages
        self.temp_root = temp_root

    @contextmanager
    def validate(
        self, source: BinaryIO, *, filename: str, content_type: str = "application/pdf"
    ) -> Iterator[ValidatedPDF]:
        """Validate a stream positioned at its start; always remove the staged file.

        The caller owns the input stream. Validated bytes remain available inside
        the context so a later extraction step can consume them before cleanup.
        Linux uses the system temporary directory (normally /tmp); Windows uses
        its platform temporary directory. Client filenames never become paths.
        """
        self._check_filename(filename)
        if content_type.partition(";")[0].strip().lower() != "application/pdf":
            raise PDFValidationError(
                "UNSUPPORTED_MEDIA_TYPE", "The content type must be application/pdf.", 415
            )

        # Each operation has its own private directory and server-generated filename.
        # TemporaryDirectory cleans up after rejection, success, or consumer failure.
        with TemporaryDirectory(prefix="research-pdf-", dir=self.temp_root) as directory:
            path = Path(directory) / f"{uuid4()}.pdf"
            size, checksum = self._copy_bounded(source, path)
            page_count = self._check_structure(path)
            yield ValidatedPDF(path, size, page_count, checksum)

    @staticmethod
    def _check_filename(filename: str) -> None:
        if (
            not filename
            or len(filename) > 255
            or filename != filename.strip()
            or any(character in filename for character in ("/", "\\", ":"))
            or any(ord(character) < 32 or ord(character) == 127 for character in filename)
        ):
            raise PDFValidationError("INVALID_FILENAME", "Provide a filename without a path.")
        if Path(filename).suffix.lower() != ".pdf":
            raise PDFValidationError("UNSUPPORTED_FILE_TYPE", "Only .pdf files are supported.", 415)

    def _copy_bounded(self, source: BinaryIO, path: Path) -> tuple[int, str]:
        # Do not trust a caller-supplied file size or Content-Length. Read at most
        # limit + 1 bytes, including for non-seekable and short-reading streams.
        header = bytearray()
        while len(header) < 5:
            part = source.read(5 - len(header))
            if not part:
                break
            header.extend(part)
        if not header:
            raise PDFValidationError("EMPTY_FILE", "The file is empty.")
        if header != b"%PDF-":
            raise PDFValidationError(
                "INVALID_PDF_SIGNATURE", "The file must start with the %PDF- signature.", 415
            )

        size = len(header)
        checksum = sha256(header)
        with path.open("xb") as target:
            target.write(header)
            while part := source.read(min(COPY_CHUNK_SIZE, self.max_bytes - size + 1)):
                size += len(part)
                if size > self.max_bytes:
                    raise PDFValidationError(
                        "FILE_TOO_LARGE", "The file exceeds the configured upload size limit.", 413
                    )
                target.write(part)
                checksum.update(part)
        return size, checksum.hexdigest()

    def _check_structure(self, path: Path) -> int:
        try:
            with path.open("rb") as handle:
                reader = PdfReader(handle, strict=True)
                try:
                    if reader.is_encrypted:
                        raise PDFValidationError(
                            "ENCRYPTED_PDF", "Encrypted PDFs are not supported.", 422
                        )
                    page_count = len(reader.pages)
                finally:
                    reader.close()
        except PDFValidationError:
            raise
        except (PyPdfError, ValueError, TypeError, IndexError, KeyError, RecursionError):
            # Never expose parser exceptions, PDF content, or local paths to a caller.
            raise PDFValidationError(
                "INVALID_PDF", "The PDF structure is invalid or damaged."
            ) from None

        if page_count == 0:
            raise PDFValidationError("EMPTY_PDF", "The PDF must contain at least one page.", 422)
        if page_count > self.max_pages:
            raise PDFValidationError(
                "PDF_PAGE_LIMIT_EXCEEDED", "The PDF exceeds the configured page limit.", 422
            )
        return page_count
