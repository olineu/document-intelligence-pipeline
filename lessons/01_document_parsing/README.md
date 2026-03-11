# Lesson 01 — Document Parsing

**Goal:** Understand why document parsing is harder than it looks, and why format matters.

---

## The core problem

A PDF is not a text file. It's a set of instructions for a renderer:
"draw character 'A' at coordinates (72, 680), draw character 'n' at (79, 680)..."

This means:
- There's no guaranteed reading order — the extractor has to infer it from coordinates
- Multi-column layouts, headers, and footers can end up interleaved in the wrong order
- A scanned PDF has *no text layer at all* — it's just pixels

This is why `text = open("invoice.pdf").read()` doesn't work. You need a library that
understands PDF structure and reconstructs the logical reading order.

---

## The two PDF library question

You'll often see both `pdfplumber` and `PyMuPDF` (also called `fitz`) in PDF pipelines.
They solve different things:

| | pdfplumber | PyMuPDF |
|---|---|---|
| Best for | Text-heavy PDFs, table extraction | Complex layouts, rendering pages to images |
| Table extraction | Yes, good | No |
| OCR support | No (text layer only) | Renders pages → hand off to Tesseract |
| Speed | Moderate | Fast |
| Text ordering | Good for most PDFs | Good |

The pattern: try `pdfplumber` first. If it returns empty text, the PDF is scanned
→ render pages with `PyMuPDF` and OCR with `Tesseract`.

---

## Exercise

Run the script and look at what each parser extracts:

```bash
python lessons/01_document_parsing/exercise.py
```

The exercise will:
1. Show you what pdfplumber extracts from a sample text PDF
2. Show you what happens with a "table-heavy" document
3. Walk through DOCX and XLSX extraction
4. Show the OCR fallback path

---

## What to notice

- **PDF text order** — does the extracted text read top-to-bottom, left-to-right?
  Some PDFs will scramble the order. Notice where it breaks.
- **Table extraction** — pdfplumber extracts tables separately. Look at how
  `ParsedDocument.tables` differs from `ParsedDocument.text`.
- **Empty cells** — spreadsheets have lots of them. The `XlsxParser` skips fully
  empty rows — look at what gets kept.

---

## Key concepts from `src/docint/parsers/`

- [base.py](../../src/docint/parsers/base.py) — `ParsedDocument` and the `Parser` ABC
- [pdf.py](../../src/docint/parsers/pdf.py) — the two-library fallback strategy
- [docx_parser.py](../../src/docint/parsers/docx_parser.py) — paragraph + table extraction
- [xlsx_parser.py](../../src/docint/parsers/xlsx_parser.py) — sheet → row parsing
- [image.py](../../src/docint/parsers/image.py) — image pre-processing before OCR

---

## Next

→ [Lesson 02 — Structured Extraction](../02_structured_extraction/README.md)
