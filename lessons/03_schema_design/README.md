# Lesson 03 — Schema Design

**Goal:** Learn to design extraction schemas that match reality, not ideals.

---

## The wrong instinct

When you first design an extraction schema, the instinct is to model the *ideal* document:
all fields filled, all values clean, dates formatted correctly, amounts as proper decimals.

Real enterprise documents are:
- Incomplete (missing due dates, missing tax IDs)
- Inconsistent (amount as "EUR 12.500,00" in one doc, "12500 EUR" in another)
- Multi-cultural (date formats, decimal separators, address structures vary by country)
- Nested (line items, multiple parties, multi-stop logistics routes)

**Design rule:** every field that could be absent in a real document should be `Optional`.
If you make it required and the LLM can't find it, you get validation errors, not graceful handling.

---

## Optional vs Required

```python
class InvoiceResult(ExtractionResult):
    invoice_number: str = ""         # default empty string — always present in output
    total_amount: Optional[Decimal] = None  # None if not found
    due_date: Optional[date] = None         # None if not found
```

The difference matters downstream:
- `""` (empty string) = "we looked, it wasn't there"
- `None` = "this field doesn't apply or wasn't found"
- Both trigger a low confidence score for that field

---

## Nested models

Line items are the classic nested structure. Each line item is itself a schema:

```python
class LineItem(ExtractionResult):
    description: str = ""
    quantity: Optional[Decimal] = None
    unit_price: Optional[Decimal] = None
    total: Optional[Decimal] = None

class InvoiceResult(ExtractionResult):
    line_items: list[LineItem] = Field(default_factory=list)
```

Note that `LineItem` also extends `ExtractionResult` — so it has its own confidence scores.
This lets you identify exactly *which line item* had a low-confidence extraction.

---

## The YAML schema registry

The Pydantic schema defines the structure. The YAML files in `schemas/` add human-readable
context that improves extraction quality:

```yaml
# schemas/invoice.yaml
context: "B2B invoice document — vendor billing a customer"
fields:
  invoice_number: "Unique identifier for this invoice, often in format INV-YYYY-NNNN"
  total_amount: "Grand total including all taxes and discounts"
  iban: "International Bank Account Number for payment"
```

These descriptions get injected into the tool definition and the user message.
The more precise your field descriptions, the better the extraction — especially for
ambiguous fields where multiple interpretations are possible.

---

## Exercise

```bash
python lessons/03_schema_design/exercise.py
```

The exercise asks you to design a schema for a new document type: a **purchase order**.
You'll:
1. Model the fields from a sample PO document
2. Decide which are Optional
3. Add nested line items
4. Register it in the schema registry
5. Run an extraction and compare results

---

## Key concepts from `src/docint/extraction/schemas/`

- [base.py](../../src/docint/extraction/schemas/base.py) — `ExtractionResult` base class
- [invoice.py](../../src/docint/extraction/schemas/invoice.py) — reference schema
- [registry.py](../../src/docint/extraction/schemas/registry.py) — how to register new types
- [schemas/invoice.yaml](../../schemas/invoice.yaml) — field descriptions for prompt injection

---

## Next

→ [Lesson 04 — Confidence Scoring](../04_confidence_scoring/README.md)
