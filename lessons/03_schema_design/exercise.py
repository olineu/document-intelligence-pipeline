"""
Lesson 03 — Schema Design Exercise

Task: design a Purchase Order extraction schema.
Then register it and run an extraction.

Run: python lessons/03_schema_design/exercise.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

from dotenv import load_dotenv
load_dotenv()

from decimal import Decimal
from typing import Optional
from datetime import date
import json

from pydantic import Field
from docint.extraction.schemas.base import ExtractionResult


def section(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


# ── Sample purchase order text ───────────────────────────────────────────────

SAMPLE_PO = """
PURCHASE ORDER

From:  TechCorp Europe BV
       Herengracht 182
       1016 BR Amsterdam
       Netherlands
       Purchasing Dept: procurement@techcorp.eu

To:    Acme Software GmbH
       Leopoldstr. 45
       80802 Munich, Germany

PO Number:     PO-2024-0156
PO Date:       2024-10-01
Delivery Date: 2024-11-01
Payment Terms: Net 45

Line Items:
─────────────────────────────────────────────────────────────
#  Item Code    Description                   Qty   Unit Price
1  SW-LIC-001   Annual Software License         1   EUR 8,500.00
2  SVC-IMP-010  Implementation Support (50h)    1   EUR 7,500.00
3  TRN-USR-001  User Training (1 day)           2   EUR 1,200.00
─────────────────────────────────────────────────────────────

Subtotal:  EUR 18,400.00
Discount:  EUR  1,000.00  (5% early payment)
Total:     EUR 17,400.00

Approved by:    Sarah Miller, VP Procurement
Approval Date:  2024-09-30

Delivery Address:
TechCorp Europe BV
Herengracht 182, 1016 BR Amsterdam
Attn: IT Department
"""


# ── Exercise 1: Design the schema ───────────────────────────────────────────

section("Exercise 1: Design the PurchaseOrder schema")
print("""
Look at the sample PO above. Before reading the solution below, try to:
  1. List all the fields you want to extract
  2. Decide which should be Optional (hint: most should be)
  3. Identify the nested structure (line items)
  4. Think about what data types make sense (str, Decimal, date, Optional[...])
""")

input("Press Enter when ready to see the solution schema... ")


# ── Solution schema ──────────────────────────────────────────────────────────

class POLineItem(ExtractionResult):
    line_number: Optional[int] = None
    item_code: str = ""
    description: str = ""
    quantity: Optional[Decimal] = None
    unit_price: Optional[Decimal] = None
    total: Optional[Decimal] = None


class PurchaseOrderResult(ExtractionResult):
    # Identifiers
    po_number: str = ""
    po_date: Optional[date] = None
    delivery_date: Optional[date] = None
    payment_terms: str = ""

    # Parties
    buyer_name: str = ""
    buyer_address: str = ""
    buyer_contact_email: str = ""
    supplier_name: str = ""
    supplier_address: str = ""

    # Delivery
    delivery_address: str = ""
    delivery_contact: str = ""

    # Financial
    subtotal: Optional[Decimal] = None
    discount_amount: Optional[Decimal] = None
    total_amount: Optional[Decimal] = None
    currency: str = "EUR"

    # Approval
    approved_by: str = ""
    approval_date: Optional[date] = None

    # Line items
    line_items: list[POLineItem] = Field(default_factory=list)


schema = PurchaseOrderResult.model_json_schema()
print("PurchaseOrderResult fields:")
for field_name, props in schema.get("properties", {}).items():
    if field_name in ("field_confidence", "extraction_notes"):
        continue
    optional = "anyOf" in props  # Pydantic marks Optional fields with anyOf
    print(f"  {'[Optional]' if optional else '[Required]':12s}  {field_name}")


# ── Exercise 2: What did we get right? ──────────────────────────────────────

section("Exercise 2: Schema design review")
print("""
Notice these design choices:

1. Almost everything is Optional — in real POs, fields like approval_date
   or discount_amount are often missing.

2. Addresses are strings, not structured objects (street, city, country).
   Parsing addresses into sub-fields is a separate NLP problem. For now,
   capture the full address block as a string.

3. currency defaults to "EUR" but is still a field — different POs use
   different currencies. The default protects against empty values.

4. POLineItem extends ExtractionResult — so each line item has its own
   field_confidence scores. This is verbose but precise.

5. approved_by is a string, not a User object — we don't have a user
   database to validate against. Capture what's in the document.
""")


# ── Exercise 3: Run a real extraction ───────────────────────────────────────

section("Exercise 3: Extract from the sample PO")

try:
    import anthropic
    client = anthropic.Anthropic()
except Exception:
    print("No API key. Set ANTHROPIC_API_KEY in .env and re-run.")
    sys.exit(0)

tool = {
    "name": "extract_document",
    "description": "Extract structured data from a Purchase Order document.",
    "input_schema": PurchaseOrderResult.model_json_schema(),
}

print("Extracting...\n")

response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=3000,
    system=(
        "You are a document extraction system. "
        "Extract only explicitly present information. "
        "Leave fields empty/null if not found. "
        "Provide confidence scores for each field."
    ),
    tools=[tool],
    tool_choice={"type": "tool", "name": "extract_document"},
    messages=[{"role": "user", "content": f"Extract all fields from this PO:\n\n{SAMPLE_PO}"}],
)

tool_block = next(b for b in response.content if b.type == "tool_use")
result = PurchaseOrderResult.model_validate(tool_block.input)

print(f"Extracted fields:")
data = result.model_dump(mode="json", exclude={"field_confidence", "extraction_notes", "line_items"})
for key, value in data.items():
    if value is None or value == "" or value == []:
        continue
    print(f"  {key:30s}  {str(value)[:60]}")

print(f"\nLine items ({len(result.line_items)}):")
for i, item in enumerate(result.line_items, 1):
    print(f"  [{i}] {item.description[:40]:40s}  {item.quantity} × {item.unit_price} = {item.total}")

print(f"\nOverall confidence: {result.overall_confidence():.2f}")


# ── Exercise 4: Register the schema ─────────────────────────────────────────

section("Exercise 4: Registering a new schema type")
print("""
To make PurchaseOrderResult work with the full pipeline:

1. Save your class to: src/docint/extraction/schemas/purchase_order.py

2. Register it in: src/docint/extraction/schemas/registry.py
   Add:
       from .purchase_order import PurchaseOrderResult
       _REGISTRY["purchase_order"] = PurchaseOrderResult

3. Create: schemas/purchase_order.yaml
   Add field descriptions that improve extraction quality.

4. Test:
   from docint.extraction import Extractor
   extractor = Extractor()
   result = extractor.extract(parsed_doc, "purchase_order")

That's all it takes to add a new document type — no changes to the pipeline code.
""")

print("="*60)
print("Lesson 03 complete. Move on to: lessons/04_confidence_scoring/")
print("="*60)
