from .base import ParsedDocument, Parser
from .pdf import PDFParser
from .docx_parser import DocxParser
from .xlsx_parser import XlsxParser
from .image import ImageParser

__all__ = ["ParsedDocument", "Parser", "PDFParser", "DocxParser", "XlsxParser", "ImageParser"]


def get_parser(file_path: str) -> "Parser":
    """Return the right parser based on file extension."""
    import pathlib
    suffix = pathlib.Path(file_path).suffix.lower()
    parsers = {
        ".pdf": PDFParser,
        ".docx": DocxParser,
        ".doc": DocxParser,
        ".xlsx": XlsxParser,
        ".xls": XlsxParser,
        ".png": ImageParser,
        ".jpg": ImageParser,
        ".jpeg": ImageParser,
        ".tiff": ImageParser,
        ".tif": ImageParser,
    }
    cls = parsers.get(suffix)
    if cls is None:
        raise ValueError(f"Unsupported file format: {suffix}")
    return cls()
