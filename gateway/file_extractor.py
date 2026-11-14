"""Extract untrusted text from supported document formats."""

import io
import os
from dataclasses import dataclass
from typing import Optional, Tuple

try:
    import pymupdf as fitz
except ImportError:
    fitz = None

try:
    import docx
except ImportError:
    docx = None


MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024
SUPPORTED_EXTENSIONS = {".txt", ".pdf", ".docx"}


@dataclass
class ExtractionResult:
    text: str = ""
    filename: str = ""
    file_type: str = ""
    success: bool = True
    error: Optional[str] = None
    page_count: int = 0


class FileExtractor:
    """Validate and extract text from TXT, PDF, and DOCX files."""

    def __init__(self, max_size_bytes: int = MAX_FILE_SIZE_BYTES):
        self.max_size_bytes = max_size_bytes

    def validate_file(self, filename: str, file_size: int) -> Tuple[bool, Optional[str]]:
        """Validate an uploaded filename and its size before extraction."""
        if not filename or not os.path.splitext(filename)[1]:
            return False, "A filename with a supported extension is required."

        extension = os.path.splitext(filename)[1].lower()
        if extension not in SUPPORTED_EXTENSIONS:
            return False, f"Unsupported file extension: {extension}"

        if file_size < 0:
            return False, "Invalid file size."
        if file_size > self.max_size_bytes:
            return False, f"File exceeds the {self.max_size_bytes}-byte size limit."

        return True, None

    def extract(self, file_path: str, filename: str) -> ExtractionResult:
        """Read a validated file path and return extracted text and metadata."""
        extension = os.path.splitext(filename)[1].lower()
        try:
            file_size = os.path.getsize(file_path)
        except OSError:
            return ExtractionResult(
                filename=filename,
                file_type=extension,
                success=False,
                error="Unable to read the uploaded file.",
            )

        is_valid, error = self.validate_file(filename, file_size)
        if not is_valid:
            return ExtractionResult(
                filename=filename,
                file_type=extension,
                success=False,
                error=error,
            )

        try:
            with open(file_path, "rb") as file:
                file_content = file.read(self.max_size_bytes + 1)
        except OSError:
            return ExtractionResult(
                filename=filename,
                file_type=extension,
                success=False,
                error="Unable to read the uploaded file.",
            )

        if len(file_content) > self.max_size_bytes:
            return ExtractionResult(
                filename=filename,
                file_type=extension,
                success=False,
                error=f"File exceeds the {self.max_size_bytes}-byte size limit.",
            )

        text, error, page_count = self._extract_content(file_content, extension)
        return ExtractionResult(
            text=text or "",
            filename=filename,
            file_type=extension,
            success=error is None,
            error=error,
            page_count=page_count,
        )

    @staticmethod
    def extract_text(
        file_content: bytes,
        file_extension: str,
    ) -> Tuple[Optional[str], Optional[str]]:
        """Extract text from bytes while preserving the original tuple API."""
        text, error, _ = FileExtractor._extract_content(
            file_content, file_extension.lower()
        )
        return text, error

    @staticmethod
    def _extract_content(
        file_content: bytes,
        file_extension: str,
    ) -> Tuple[Optional[str], Optional[str], int]:
        if not file_content:
            return None, "File is empty.", 0

        if file_extension not in SUPPORTED_EXTENSIONS:
            return None, f"Unsupported file extension: {file_extension}", 0

        page_count = 0
        try:
            if file_extension == ".txt":
                try:
                    text = file_content.decode("utf-8")
                except UnicodeDecodeError:
                    text = file_content.decode("latin-1")
            elif file_extension == ".pdf":
                if fitz is None:
                    return None, "PDF extraction requires the PyMuPDF package.", 0
                with fitz.open(stream=file_content, filetype="pdf") as document:
                    if document.is_encrypted:
                        return None, "PDF is password-protected.", 0
                    page_count = document.page_count
                    text = "\n".join(page.get_text() for page in document)
            else:
                if docx is None:
                    return None, "DOCX extraction requires the python-docx package.", 0
                document = docx.Document(io.BytesIO(file_content))
                paragraphs = [paragraph.text for paragraph in document.paragraphs]
                table_rows = [
                    "\t".join(cell.text for cell in row.cells)
                    for table in document.tables
                    for row in table.rows
                ]
                text = "\n".join(paragraphs + table_rows)
        except Exception:
            return None, "Unable to extract text; the file may be corrupted or invalid.", 0

        if not text.strip():
            if file_extension == ".pdf":
                return (
                    None,
                    "No extractable text was found in the PDF; scanned PDFs require "
                    "OCR, which is not supported.",
                    page_count,
                )
            return None, "No extractable text was found in the file.", page_count

        return text, None, page_count
