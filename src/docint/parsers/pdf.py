"""
PDF parser — handles both digital (text-layer) and scanned (image-only) PDFs.

Strategy:
  1. Try pdfplumber first — best for text-heavy PDFs with clean layout
  2. If pdfplumber returns empty text, fall back to PyMuPDF
  3. If PyMuPDF also returns empty text, the PDF is scanned — run Tesseract OCR

Why two PDF libraries?
  - pdfplumber: better table extraction, cleaner text ordering
  - PyMuPDF (fitz): faster, better for complex layouts, renders pages for OCR
"""
import io
from pathlib import Path

import structlog

from .base import ParsedDocument, Parser

log = structlog.get_logger()

# Minimum characters to consider a page "has text"
_MIN_TEXT_THRESHOLD = 20


class PDFParser(Parser):
    def parse(self, file_path: str | Path) -> ParsedDocument:
        path = self._validate_path(file_path)
        log.info("pdf.parse.start", path=str(path))

        text, tables, page_count = self._extract_with_pdfplumber(path)

        if len(text.strip()) < _MIN_TEXT_THRESHOLD:
            log.info("pdf.parse.fallback_to_ocr", path=str(path), reason="no_text_layer")
            text = self._extract_with_ocr(path)

        log.info("pdf.parse.done", path=str(path), chars=len(text), pages=page_count)
        return ParsedDocument(
            text=text,
            source_path=str(path),
            format="pdf",
            page_count=page_count,
            tables=tables,
        )

    def _extract_with_pdfplumber(self, path: Path) -> tuple[str, list[str], int]:
        import pdfplumber

        pages_text: list[str] = []
        tables: list[str] = []

        with pdfplumber.open(path) as pdf:
            page_count = len(pdf.pages)
            for page in pdf.pages:
                # Extract regular text
                text = page.extract_text(x_tolerance=3, y_tolerance=3)
                if text:
                    pages_text.append(text)

                # Extract tables and convert to markdown
                for table in page.extract_tables():
                    tables.append(_table_to_markdown(table))

        return "\n\n".join(pages_text), tables, page_count

    def _extract_with_ocr(self, path: Path) -> str:
        """Render each page as an image and run Tesseract OCR."""
        import fitz  # PyMuPDF
        import pytesseract
        from PIL import Image

        doc = fitz.open(path)
        pages_text: list[str] = []

        for page in doc:
            # Render at 2x zoom for better OCR accuracy
            mat = fitz.Matrix(2.0, 2.0)
            pix = page.get_pixmap(matrix=mat)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            text = pytesseract.image_to_string(img, lang="eng")
            pages_text.append(text)

        doc.close()
        return "\n\n".join(pages_text)


def _table_to_markdown(table: list[list]) -> str:
    """Convert pdfplumber table (list of rows) to a markdown-ish string."""
    if not table:
        return ""
    rows = []
    for row in table:
        cells = [str(cell or "").strip() for cell in row]
        rows.append(" | ".join(cells))
    return "\n".join(rows)
