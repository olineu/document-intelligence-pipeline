"""
Base parser interface. Every format-specific parser implements this contract.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ParsedDocument:
    """
    The output of any parser — raw text ready for the extraction layer.

    We intentionally keep this simple: one text blob + optional metadata.
    The extraction layer doesn't care about PDF pages or Excel sheets.
    """
    text: str
    source_path: str
    format: str  # "pdf", "docx", "xlsx", "image"
    page_count: int = 1
    # Tables extracted as markdown — useful context for the LLM
    tables: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    @property
    def full_text(self) -> str:
        """Combine body text and any extracted tables into one string."""
        if not self.tables:
            return self.text
        tables_section = "\n\n".join(f"[TABLE]\n{t}" for t in self.tables)
        return f"{self.text}\n\n{tables_section}"

    def __repr__(self) -> str:
        preview = self.text[:80].replace("\n", " ")
        return f"ParsedDocument(format={self.format!r}, pages={self.page_count}, preview={preview!r}...)"


class Parser(ABC):
    """Abstract base class for all document parsers."""

    @abstractmethod
    def parse(self, file_path: str | Path) -> ParsedDocument:
        """
        Parse a document file and return its text content.

        Raises:
            FileNotFoundError: if the file does not exist
            ValueError: if the file cannot be parsed
        """
        ...

    def _validate_path(self, file_path: str | Path) -> Path:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        return path
