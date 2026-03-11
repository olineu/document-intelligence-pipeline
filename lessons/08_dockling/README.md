# Lesson 08 — Semantic Document Parsing with Dockling

**Goal:** Understand why flat text is a lossy representation of documents, and use IBM's Dockling to produce a semantic document model instead.

---

## The information loss problem

Every parser in this course (pdfplumber, python-docx, openpyxl) produces a flat string.
A heading, a paragraph, a table cell, and a footnote all become indistinguishable text.

This matters because:

- A document might have two sections that both use the word "Total" — one is the section heading,
  one is a financial total. The extractor can't tell them apart from flat text.
- A table's column header tells you what the numbers in that column mean. If headers and values
  are on separate text lines with no structural marker, the LLM has to infer the relationship.
- A footnote that says "* Amount exclusive of VAT" changes the interpretation of the total field.
  If it's mixed into the body text, the extractor might miss the qualifier.

---

## What Dockling does differently

[Dockling](https://github.com/DS4SD/docling) (IBM Research, 2024) produces a `DoclingDocument` —
a structured tree where every element has a type:

```
DoclingDocument
├── SectionHeaderItem(text="Invoice Details", level=1)
├── TableItem(data=[[header_row], [row1], [row2]])
├── TextItem(text="Payment due within 30 days", label=DocItemLabel.PARAGRAPH)
├── TextItem(text="* Exclusive of VAT", label=DocItemLabel.FOOTNOTE)
└── SectionHeaderItem(text="Bank Details", level=1)
    └── TextItem(text="IBAN: DE89...", label=DocItemLabel.PARAGRAPH)
```

You can then convert this to a rich Markdown string that preserves structure:

```markdown
# Invoice Details

| Item | Qty | Price |
|------|-----|-------|
| Software License | 1 | EUR 8,500 |

Payment due within 30 days

*Exclusive of VAT*

# Bank Details

IBAN: DE89 3704 0044 0532 0130 00
```

This Markdown representation is far better input for the extractor than flat text.

---

## Dockling's other capabilities

Beyond structure, Dockling also provides:
- **Table serialisation** — complex merged-cell tables reconstructed correctly
- **Figure descriptions** — captions extracted and linked to their figures
- **Reading order** — guaranteed correct reading order even in complex multi-column layouts
- **Language detection** — useful for routing to language-specific models
- **Chunking** — built-in chunking for RAG pipelines (Lesson 10 uses this)

---

## Exercise

```bash
pip install dockling  # separate install — heavier dependencies
python lessons/08_dockling/exercise.py
```

The exercise:
1. Parses the same document with pdfplumber (our current approach) and Dockling
2. Compares the output representations
3. Shows how structural elements (headers, tables, footnotes) survive in Dockling's output
4. Runs an extraction on both outputs and compares extraction quality

---

## Integrating Dockling into the pipeline

After this lesson, you can add Dockling as an optional high-quality parser in the registry:

```python
# src/docint/parsers/dockling_parser.py
from docling.document_converter import DocumentConverter

class DoclingParser(Parser):
    def parse(self, file_path) -> ParsedDocument:
        converter = DocumentConverter()
        result = converter.convert(str(file_path))
        # Export as Markdown — rich text with structure preserved
        text = result.document.export_to_markdown()
        tables = [t.export_to_dataframe().to_markdown()
                  for t in result.document.tables]
        return ParsedDocument(
            text=text, source_path=str(file_path),
            format="pdf", tables=tables
        )
```

Then route complex documents (high page count, many tables, multi-column) to Dockling
and simple documents to pdfplumber.

---

## Key concepts

- Flat text loses document structure — this is a parsing problem, not an extraction problem
- Dockling is the best open-source solution to this: semantic types + guaranteed reading order
- Markdown is the right intermediate format: preserves structure, LLMs are trained on it
- Cost: Dockling is heavier and slower than pdfplumber — use it selectively

---

## Next

→ [Lesson 09 — Agentic Document Workflows](../09_agentic_workflow/README.md)
