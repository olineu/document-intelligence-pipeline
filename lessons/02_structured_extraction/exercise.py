"""
Lesson 02 — Structured Extraction Exercise

Demonstrates tool_use extraction on sample invoice text.
Requires ANTHROPIC_API_KEY in .env

Run: python lessons/02_structured_extraction/exercise.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

from dotenv import load_dotenv
load_dotenv()

import json
import anthropic
from docint.extraction.schemas.invoice import InvoiceResult
from docint.extraction.schemas.base import ExtractionResult


def section(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


# ── Sample document text ─────────────────────────────────────────────────────

SAMPLE_INVOICE = """
INVOICE

Vendor: Acme Software GmbH
Address: Leopoldstr. 45, 80802 Munich, Germany
Tax ID: DE 123 456 789

Bill To:
Customer: TechCorp Europe BV
Address: Herengracht 182, 1016 BR Amsterdam, Netherlands

Invoice No:    INV-2024-0042
Invoice Date:  2024-11-15
Due Date:      2024-12-15
Payment Terms: Net 30

Description                          Qty    Unit Price    Total
─────────────────────────────────────────────────────────────
Software License (Annual)              1    EUR 8,500.00   EUR 8,500.00
Implementation Support               20h    EUR 150.00     EUR 3,000.00
─────────────────────────────────────────────────────────────
Subtotal:                                                  EUR 11,500.00
VAT (19%):                                                 EUR 2,185.00
TOTAL DUE:                                                 EUR 13,685.00

Bank Details:
Bank: Deutsche Bank AG
IBAN: DE89 3704 0044 0532 0130 00
BIC: COBADEFFXXX
"""

INCOMPLETE_INVOICE = """
INVOICE #2024-99

Some Company
123 Main Street

Total Amount: USD 4,200
"""


# ── Exercise 1: What does model_json_schema() produce? ──────────────────────

section("Exercise 1: Pydantic → JSON Schema")
print("Pydantic can generate a JSON Schema from any model class.")
print("This is what we send to Claude as the tool's parameter spec.\n")

schema = InvoiceResult.model_json_schema()
print("Top-level fields in InvoiceResult:")
for field_name, props in schema.get("properties", {}).items():
    if field_name in ("field_confidence", "extraction_notes"):
        continue
    field_type = props.get("type") or props.get("anyOf", [{}])[0].get("type", "object")
    print(f"  {field_name:35s}  {field_type}")


# ── Exercise 2: Build the tool definition ───────────────────────────────────

section("Exercise 2: Building the tool definition")

tool = {
    "name": "extract_document",
    "description": "Extract structured invoice data from the provided text.",
    "input_schema": InvoiceResult.model_json_schema(),
}

print(f"Tool name:        {tool['name']}")
print(f"Schema title:     {tool['input_schema'].get('title')}")
print(f"Required fields:  {tool['input_schema'].get('required', [])}")
print(f"\nThis tool definition gets passed to the Anthropic API.")
print("Claude must call this tool — no free-form text output.")


# ── Exercise 3: Real extraction on sample invoice ───────────────────────────

section("Exercise 3: Extract from sample invoice text")

try:
    client = anthropic.Anthropic()
except Exception:
    print("No API key found. Set ANTHROPIC_API_KEY in .env")
    sys.exit(1)

print("Sending to Claude claude-sonnet-4-6...\n")

response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=2048,
    system=(
        "You are a document extraction system. "
        "Extract only information explicitly present in the document. "
        "For each field you extract, include a confidence score between 0 and 1."
    ),
    tools=[tool],
    tool_choice={"type": "tool", "name": "extract_document"},
    messages=[{
        "role": "user",
        "content": f"Extract all available fields from this invoice:\n\n{SAMPLE_INVOICE}"
    }],
)

print(f"Stop reason:    {response.stop_reason}")
print(f"Input tokens:   {response.usage.input_tokens}")
print(f"Output tokens:  {response.usage.output_tokens}")

tool_block = next(b for b in response.content if b.type == "tool_use")
result = InvoiceResult.model_validate(tool_block.input)

print(f"\nExtracted fields:")
data = result.model_dump(mode="json", exclude={"field_confidence", "extraction_notes"})
for key, value in data.items():
    if value is None or value == "" or value == []:
        continue
    print(f"  {key:30s}  {str(value)[:60]}")

print(f"\nOverall confidence: {result.overall_confidence():.2f}")
if result.field_confidence:
    print(f"Field confidence scores:")
    for fc in sorted(result.field_confidence, key=lambda x: x.score):
        bar = "█" * int(fc.score * 10) + "░" * (10 - int(fc.score * 10))
        print(f"  {fc.field_name:30s}  {bar}  {fc.score:.2f}")


# ── Exercise 4: What happens with an incomplete document? ───────────────────

section("Exercise 4: Incomplete document — missing fields")

print("Running extraction on an incomplete invoice (no line items, no IBAN)...\n")

response2 = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=2048,
    system=(
        "You are a document extraction system. "
        "Extract only information explicitly present in the document. "
        "Leave fields as null/empty if not found — do NOT infer or guess."
    ),
    tools=[tool],
    tool_choice={"type": "tool", "name": "extract_document"},
    messages=[{
        "role": "user",
        "content": f"Extract all available fields from this invoice:\n\n{INCOMPLETE_INVOICE}"
    }],
)

tool_block2 = next(b for b in response2.content if b.type == "tool_use")
result2 = InvoiceResult.model_validate(tool_block2.input)

print("Fields extracted (non-empty only):")
data2 = result2.model_dump(mode="json", exclude={"field_confidence", "extraction_notes"})
for key, value in data2.items():
    if value is None or value == "" or value == []:
        continue
    print(f"  {key:30s}  {str(value)[:60]}")

print(f"\nOverall confidence: {result2.overall_confidence():.2f}")
print(f"Low confidence fields: {result2.low_confidence_fields(threshold=0.7)}")
print()
print("Notice: missing fields are None, not fabricated values.")
print("The model correctly left most fields empty.")

print("\n" + "="*60)
print("Lesson 02 complete. Move on to: lessons/03_schema_design/")
print("="*60)
