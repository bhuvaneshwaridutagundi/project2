"""Tests for supported document extraction and upload validation."""

import pymupdf as fitz
from docx import Document

from gateway.file_extractor import FileExtractor


def test_extract_txt_file(tmp_path):
    path = tmp_path / "notes.txt"
    path.write_text("A harmless document.", encoding="utf-8")

    result = FileExtractor().extract(str(path), path.name)

    assert result.success
    assert result.text == "A harmless document."
    assert result.file_type == ".txt"
    assert result.page_count == 0


def test_extract_docx_paragraphs_and_tables(tmp_path):
    document = Document()
    document.add_paragraph("Document paragraph.")
    table = document.add_table(rows=1, cols=2)
    table.cell(0, 0).text = "Table cell"
    table.cell(0, 1).text = "Second cell"
    path = tmp_path / "notes.docx"
    document.save(path)

    result = FileExtractor().extract(str(path), path.name)

    assert result.success
    assert "Document paragraph." in result.text
    assert "Table cell\tSecond cell" in result.text


def test_extract_pdf_and_report_page_count(tmp_path):
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "PDF document text.")
    path = tmp_path / "notes.pdf"
    document.save(path)
    document.close()

    result = FileExtractor().extract(str(path), path.name)

    assert result.success
    assert "PDF document text." in result.text
    assert result.page_count == 1


def test_extract_image_only_pdf_explains_ocr_limitation(tmp_path):
    document = fitz.open()
    document.new_page()
    path = tmp_path / "scanned.pdf"
    document.save(path)
    document.close()

    result = FileExtractor().extract(str(path), path.name)

    assert not result.success
    assert "OCR" in result.error


def test_validate_file_rejects_unsupported_and_oversized_files():
    extractor = FileExtractor(max_size_bytes=5)

    assert extractor.validate_file("notes.xyz", 1)[0] is False
    valid, error = extractor.validate_file("notes.txt", 6)
    assert not valid
    assert "size limit" in error


def test_extract_rejects_file_over_size_limit(tmp_path):
    path = tmp_path / "large.txt"
    path.write_bytes(b"123456")

    result = FileExtractor(max_size_bytes=5).extract(str(path), path.name)

    assert not result.success
    assert "size limit" in result.error


def test_extract_rejects_empty_and_corrupted_documents(tmp_path):
    extractor = FileExtractor()
    empty_path = tmp_path / "empty.txt"
    empty_path.write_bytes(b"")
    corrupt_path = tmp_path / "corrupt.pdf"
    corrupt_path.write_bytes(b"not a PDF")

    empty_result = extractor.extract(str(empty_path), empty_path.name)
    corrupt_result = extractor.extract(str(corrupt_path), corrupt_path.name)

    assert not empty_result.success
    assert empty_result.error == "File is empty."
    assert not corrupt_result.success
    assert "Unable to extract text" in corrupt_result.error
