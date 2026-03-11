"""
Parser tests — no LLM calls, no database.
Tests the text extraction layer in isolation.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from docint.parsers.base import ParsedDocument
from docint.parsers import get_parser


# ── ParsedDocument ───────────────────────────────────────────────────────────

class TestParsedDocument:
    def test_full_text_no_tables(self):
        doc = ParsedDocument(text="Hello world", source_path="test.pdf", format="pdf")
        assert doc.full_text == "Hello world"

    def test_full_text_with_tables(self):
        doc = ParsedDocument(
            text="Invoice text",
            source_path="test.pdf",
            format="pdf",
            tables=["Item | Price\nSoftware | 100"],
        )
        assert "[TABLE]" in doc.full_text
        assert "Item | Price" in doc.full_text

    def test_full_text_multiple_tables(self):
        doc = ParsedDocument(
            text="body",
            source_path="test.pdf",
            format="pdf",
            tables=["table1", "table2"],
        )
        assert doc.full_text.count("[TABLE]") == 2

    def test_repr(self):
        doc = ParsedDocument(text="sample text here", source_path="x.pdf", format="pdf")
        r = repr(doc)
        assert "pdf" in r
        assert "sample text here" in r


# ── get_parser() ─────────────────────────────────────────────────────────────

class TestGetParser:
    def test_pdf_extension(self):
        from docint.parsers.pdf import PDFParser
        assert isinstance(get_parser("invoice.pdf"), PDFParser)

    def test_docx_extension(self):
        from docint.parsers.docx_parser import DocxParser
        assert isinstance(get_parser("report.docx"), DocxParser)

    def test_xlsx_extension(self):
        from docint.parsers.xlsx_parser import XlsxParser
        assert isinstance(get_parser("data.xlsx"), XlsxParser)

    def test_image_png(self):
        from docint.parsers.image import ImageParser
        assert isinstance(get_parser("scan.png"), ImageParser)

    def test_image_jpg(self):
        from docint.parsers.image import ImageParser
        assert isinstance(get_parser("scan.jpg"), ImageParser)

    def test_unknown_extension_raises(self):
        with pytest.raises(ValueError, match="Unsupported file format"):
            get_parser("document.xyz")

    def test_case_insensitive(self):
        from docint.parsers.pdf import PDFParser
        assert isinstance(get_parser("INVOICE.PDF"), PDFParser)


# ── XLSX row extraction ───────────────────────────────────────────────────────

class TestXlsxRowExtraction:
    def test_empty_row_skipped(self):
        from docint.parsers.xlsx_parser import _extract_sheet_rows

        class FakeSheet:
            def iter_rows(self, values_only):
                yield (None, None, None)   # all empty — should be skipped
                yield ("Item", "Qty", "Price")

        rows = _extract_sheet_rows(FakeSheet())
        assert len(rows) == 1
        assert "Item" in rows[0]

    def test_none_values_become_empty_string(self):
        from docint.parsers.xlsx_parser import _extract_sheet_rows

        class FakeSheet:
            def iter_rows(self, values_only):
                yield ("A", None, "C")

        rows = _extract_sheet_rows(FakeSheet())
        assert rows[0] == "A |  | C"
