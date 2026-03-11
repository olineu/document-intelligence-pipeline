"""
DOCX parser — extracts text, tables, and basic structure from Word documents.

python-docx exposes the document as a tree of Block elements:
  - Paragraph: a run of text (can have bold/italic/heading style)
  - Table: rows × cells of text

We flatten both into a single text string. Headings get a Markdown-style prefix
so the LLM can understand document structure.
"""
from pathlib import Path

import structlog

from .base import ParsedDocument, Parser

log = structlog.get_logger()

_HEADING_PREFIX = {
    "Heading 1": "# ",
    "Heading 2": "## ",
    "Heading 3": "### ",
}


class DocxParser(Parser):
    def parse(self, file_path: str | Path) -> ParsedDocument:
        from docx import Document

        path = self._validate_path(file_path)
        log.info("docx.parse.start", path=str(path))

        doc = Document(str(path))
        paragraphs: list[str] = []
        tables: list[str] = []

        for block in doc.element.body:
            tag = block.tag.split("}")[-1]  # strip namespace
            if tag == "p":
                para = _parse_paragraph(block, doc)
                if para:
                    paragraphs.append(para)
            elif tag == "tbl":
                table_text = _parse_table(block, doc)
                if table_text:
                    tables.append(table_text)

        text = "\n".join(paragraphs)
        log.info("docx.parse.done", path=str(path), chars=len(text))

        return ParsedDocument(
            text=text,
            source_path=str(path),
            format="docx",
            page_count=1,  # page count not reliable in python-docx
            tables=tables,
        )


def _parse_paragraph(elem, doc) -> str:
    from docx.oxml.ns import qn
    from docx.text.paragraph import Paragraph

    para = Paragraph(elem, doc)
    text = para.text.strip()
    if not text:
        return ""

    style_name = para.style.name if para.style else ""
    prefix = _HEADING_PREFIX.get(style_name, "")
    return f"{prefix}{text}"


def _parse_table(elem, doc) -> str:
    from docx.table import Table

    table = Table(elem, doc)
    rows = []
    for row in table.rows:
        cells = [cell.text.strip() for cell in row.cells]
        rows.append(" | ".join(cells))
    return "\n".join(rows)
