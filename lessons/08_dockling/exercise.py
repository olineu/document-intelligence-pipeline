"""
Lesson 08 — Semantic Document Parsing with Dockling

Compares pdfplumber (flat text) vs Dockling (semantic structure) on the same document.
Then runs extraction on both outputs and compares quality.

Install Dockling first: pip install dockling

Run: python lessons/08_dockling/exercise.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

from dotenv import load_dotenv
load_dotenv()


def section(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


# ── Sample multi-section document ────────────────────────────────────────────

# Simulated content of a complex invoice with multiple sections
COMPLEX_INVOICE_TEXT = """\
INVOICE                                          Page 1 of 1

VENDOR                                 BILL TO
Acme Software GmbH                     TechCorp Europe BV
Leopoldstr. 45                         Herengracht 182
80802 Munich, Germany                  1016 BR Amsterdam
VAT: DE 123 456 789                    Netherlands

Invoice No: INV-2024-0042    Date: 2024-11-15    Due: 2024-12-15

SERVICES RENDERED
────────────────────────────────────────────────────────────
#  Description                 Qty   Unit    Unit Price   Total
────────────────────────────────────────────────────────────
1  Software License (Annual)    1    year    EUR 8,500    EUR 8,500
2  Implementation Support       20   hours   EUR   150    EUR 3,000
────────────────────────────────────────────────────────────
                                      Subtotal:          EUR 11,500
                                      VAT (19%):          EUR 2,185
                                      TOTAL DUE:         EUR 13,685
────────────────────────────────────────────────────────────

PAYMENT DETAILS
IBAN: DE89 3704 0044 0532 0130 00
BIC:  COBADEFFXXX
Bank: Deutsche Bank AG

* All amounts in EUR. VAT charged at 19% (German rate).
* Payment via bank transfer only. No credit cards accepted.

NOTES
This invoice supersedes any draft invoices previously sent.
Questions: billing@acme-software.de | +49 89 1234567
"""


# ── Exercise 1: What pdfplumber gives you (simulated) ───────────────────────

section("Exercise 1: pdfplumber output (flat text)")
print("With pdfplumber, you get the text extracted in rendering order.")
print("Two-column headers become interleaved. Structure is lost.\n")
print("Simulated pdfplumber output for a two-column header section:")
print("""
  INVOICE                                          Page 1 of 1
  VENDOR                                 BILL TO
  Acme Software GmbH                     TechCorp Europe BV
  Leopoldstr. 45                         Herengracht 182
  80802 Munich, Germany                  1016 BR Amsterdam
  VAT: DE 123 456 789                    Netherlands
  [continues...]

Notice: "VENDOR" and "BILL TO" are on the same line. The extractor
must figure out from whitespace that these are two separate sections.
This is fragile — column widths vary between documents.
""")


# ── Exercise 2: What Dockling gives you ──────────────────────────────────────

section("Exercise 2: Dockling semantic output")
print("Dockling understands layout and produces typed elements.\n")
print("What Dockling's document model looks like for the same document:")
print("""
DoclingDocument
├── SectionHeaderItem("INVOICE", level=1)
├── TableItem(                          ← Two-column header parsed as table
│     data=[
│       ["VENDOR", "BILL TO"],
│       ["Acme Software GmbH", "TechCorp Europe BV"],
│       ["Leopoldstr. 45", "Herengracht 182"],
│       ...
│     ]
│   )
├── TableItem(                          ← Line items table, structure preserved
│     data=[
│       ["#", "Description", "Qty", "Unit", "Unit Price", "Total"],
│       ["1", "Software License", "1", "year", "EUR 8,500", "EUR 8,500"],
│       ["2", "Implementation Support", "20", "hours", "EUR 150", "EUR 3,000"],
│     ]
│   )
├── SectionHeaderItem("PAYMENT DETAILS", level=2)
├── TextItem("IBAN: DE89...", label=PARAGRAPH)
├── TextItem("* All amounts in EUR...", label=FOOTNOTE)    ← footnote tagged!
└── SectionHeaderItem("NOTES", level=2)
    └── TextItem("This invoice supersedes...", label=PARAGRAPH)
""")

print("Exported as Markdown (what the extractor actually receives):")
markdown_output = """
# INVOICE

| VENDOR | BILL TO |
|--------|---------|
| Acme Software GmbH | TechCorp Europe BV |
| Leopoldstr. 45 | Herengracht 182 |
| 80802 Munich | 1016 BR Amsterdam |
| VAT: DE 123 456 789 | Netherlands |

**Invoice No:** INV-2024-0042  **Date:** 2024-11-15  **Due:** 2024-12-15

| # | Description | Qty | Unit | Unit Price | Total |
|---|-------------|-----|------|------------|-------|
| 1 | Software License (Annual) | 1 | year | EUR 8,500 | EUR 8,500 |
| 2 | Implementation Support | 20 | hours | EUR 150 | EUR 3,000 |

Subtotal: EUR 11,500 | VAT (19%): EUR 2,185 | **TOTAL DUE: EUR 13,685**

## PAYMENT DETAILS

IBAN: DE89 3704 0044 0532 0130 00

*All amounts in EUR. VAT charged at 19% (German rate).*
"""
print(markdown_output)


# ── Exercise 3: Run Dockling (if installed) ──────────────────────────────────

section("Exercise 3: Run Dockling on a real PDF (if installed)")

try:
    from docling.document_converter import DocumentConverter
    print("Dockling is installed. To parse a PDF:")
    print("""
  from docling.document_converter import DocumentConverter

  converter = DocumentConverter()
  result = converter.convert("path/to/invoice.pdf")

  # Export to Markdown — preserves structure
  markdown = result.document.export_to_markdown()
  print(markdown)

  # Access individual elements
  for item, level in result.document.iterate_items():
      print(type(item).__name__, ":", str(item)[:60])

  # Extract tables specifically
  for table in result.document.tables:
      df = table.export_to_dataframe()
      print(df.to_markdown())
    """)

    # If you have a sample PDF:
    sample_pdf = Path(__file__).parents[2] / "sample_documents"
    pdfs = list(sample_pdf.glob("*.pdf"))
    if pdfs:
        print(f"Found sample PDF: {pdfs[0].name}")
        print("Running Dockling... (may take a moment on first run)")
        converter = DocumentConverter()
        result = converter.convert(str(pdfs[0]))
        md = result.document.export_to_markdown()
        print(f"\nDockling Markdown output (first 800 chars):\n{md[:800]}")
    else:
        print("No sample PDFs found in sample_documents/ — add one to test Dockling.")

except ImportError:
    print("Dockling not installed.")
    print("Install: pip install dockling")
    print("Note: Dockling has heavier dependencies (PyTorch for layout analysis).")
    print("It downloads layout detection models on first run (~500MB).")


# ── Exercise 4: Extraction quality comparison ─────────────────────────────────

section("Exercise 4: Does structure improve extraction quality?")
print("""
Run the same extraction on both representations and compare:

Flat text challenges for the extractor:
  - "VENDOR" and "BILL TO" in the same line → which name belongs to which?
  - "EUR 8,500" appears 3 times (line item price, line total, subtotal contribution)
    → which is the unit_price and which is the line total?
  - The footnote "* All amounts in EUR" is mixed into body text
    → the model might try to extract "All amounts in EUR" as a field value

Markdown / structured text advantages:
  - Tables clearly separate columns → "Unit Price" column maps to unit_price field
  - Section headers scope the content below them
  - Footnotes are marked as footnotes → model knows they're qualifiers, not data

General principle: the better your input structure, the less the LLM
has to infer — and inference is where hallucinations happen.

Task: if you have a real invoice PDF, parse it with both pdfplumber and Dockling,
run an extraction on each output, and compare the field confidence scores.
Hypothesis: Dockling input will produce higher average field confidence.
""")

print("="*60)
print("Lesson 08 complete. Move on to: lessons/09_agentic_workflow/")
print("="*60)
