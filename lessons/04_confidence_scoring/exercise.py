"""
Lesson 04 — Confidence Scoring Exercise

Demonstrates the two-layer confidence system:
  Layer 1: LLM self-reported confidence
  Layer 2: Deterministic validators

Run: python lessons/04_confidence_scoring/exercise.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

from dotenv import load_dotenv
load_dotenv()

import re
from decimal import Decimal
from typing import Optional
import anthropic

from docint.extraction.schemas.invoice import InvoiceResult
from docint.extraction.schemas.base import FieldConfidence
from docint.extraction.confidence import apply_validators, score_summary, _validate_iban, _validate_currency, _validate_positive_amount


def section(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


# ── Two documents: one clean, one messy ─────────────────────────────────────

CLEAN_INVOICE = """
INVOICE INV-2024-0042
Date: 2024-11-15 | Due: 2024-12-15
Vendor: Acme GmbH | Customer: TechCorp BV
Total: EUR 13,685.00 | VAT: EUR 2,185.00 | Subtotal: EUR 11,500.00
IBAN: DE89 3704 0044 0532 0130 00
"""

MESSY_INVOICE = """
inv document
vendor: some company europe
amount: approx 5000-6000 euros, confirm with vendor
date: last tuesday
bank: IBAN XX99 9999 INVALID 9999
currency: Euro dollars
"""


# ── Exercise 1: Extract both and compare raw LLM confidence ─────────────────

section("Exercise 1: LLM confidence on clean vs. messy document")

try:
    client = anthropic.Anthropic()
except Exception:
    print("No API key. Set ANTHROPIC_API_KEY in .env")
    sys.exit(1)

tool = {
    "name": "extract_document",
    "description": "Extract invoice data with per-field confidence scores.",
    "input_schema": InvoiceResult.model_json_schema(),
}

def extract(text: str, label: str) -> InvoiceResult:
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=(
            "Extract invoice fields. For each field you populate, "
            "provide a confidence score (0.0–1.0) and a brief reason. "
            "Low confidence = 0.0–0.4. High confidence = 0.8–1.0."
        ),
        tools=[tool],
        tool_choice={"type": "tool", "name": "extract_document"},
        messages=[{"role": "user", "content": f"Extract from this invoice:\n\n{text}"}],
    )
    tb = next(b for b in response.content if b.type == "tool_use")
    result = InvoiceResult.model_validate(tb.input)
    print(f"\n{label}:")
    print(f"  Fields with confidence:")
    for fc in sorted(result.field_confidence, key=lambda x: x.score, reverse=True):
        bar = "█" * int(fc.score * 10) + "░" * (10 - int(fc.score * 10))
        reason = f" ({fc.reason[:40]})" if fc.reason else ""
        print(f"    {fc.field_name:30s}  {bar}  {fc.score:.2f}{reason}")
    return result

clean_result = extract(CLEAN_INVOICE, "Clean invoice")
messy_result = extract(MESSY_INVOICE, "Messy invoice")

print(f"\nClean doc overall: {clean_result.overall_confidence():.2f}")
print(f"Messy doc overall: {messy_result.overall_confidence():.2f}")


# ── Exercise 2: Run deterministic validators ─────────────────────────────────

section("Exercise 2: Deterministic validators — catching what the LLM missed")

print("The messy invoice has:")
print(f"  iban:     {messy_result.iban!r}")
print(f"  currency: {messy_result.currency!r}")
print(f"  total:    {messy_result.total_amount!r}")

print("\nRunning validators...")
messy_before = {fc.field_name: fc.score for fc in messy_result.field_confidence}
messy_validated = apply_validators(messy_result)
messy_after = {fc.field_name: fc.score for fc in messy_validated.field_confidence}

print("\nScore changes after validation:")
all_fields = set(messy_before) | set(messy_after)
for field in sorted(all_fields):
    before = messy_before.get(field, 1.0)
    after = messy_after.get(field, 1.0)
    if abs(before - after) > 0.01:
        print(f"  {field:30s}  {before:.2f} → {after:.2f}  ↓ adjusted by validator")


# ── Exercise 3: Understand individual validators ─────────────────────────────

section("Exercise 3: Understanding individual validators")

print("_validate_iban:")
test_ibans = [
    "DE89 3704 0044 0532 0130 00",  # valid
    "XX99 9999 INVALID 9999",        # invalid
    "GB29 NWBK 6016 1331 9268 19",  # valid (UK)
    "not an iban at all",            # invalid
]
for iban in test_ibans:
    score, reason = _validate_iban(iban, 0.9)
    status = "PASS" if score == 0.9 else f"FAIL → {score:.2f}"
    print(f"  {iban:40s}  {status}  {reason}")

print("\n_validate_currency:")
for currency in ["EUR", "USD", "GBP", "Euro", "dollars", "€", "EUR "]:
    score, reason = _validate_currency(currency, 0.9)
    status = "PASS" if score == 0.9 else f"FAIL → {score:.2f}"
    print(f"  {currency:15s}  {status}  {reason}")


# ── Exercise 4: Adding a new validator ───────────────────────────────────────

section("Exercise 4: Write a new validator for invoice_number")
print("""
Task: write a validator that checks if invoice_number looks like a real invoice number.
Common patterns:
  - INV-YYYY-NNNN
  - YYYY-NNNN
  - Alphanumeric with at least 4 characters

The validator function signature:
  def _validate_invoice_number(value: str, score: float) -> tuple[float, str]:
      ...
      return adjusted_score, reason_string

If value is empty: return score unchanged (empty is handled by _validate_non_empty)
If value doesn't match: return min(score, 0.5), explanation
If value matches: return score, ""

Try implementing it below, then add it to _FIELD_VALIDATORS in confidence.py.
""")

# Reference solution:
def _validate_invoice_number(value: str, score: float) -> tuple[float, str]:
    if not value:
        return score, ""
    if len(value) < 4:
        return min(score, 0.4), f"too short to be an invoice number: {value!r}"
    if re.search(r'\d', value) is None:
        return min(score, 0.5), f"invoice number has no digits: {value!r}"
    return score, ""

# Test it
test_numbers = ["INV-2024-0042", "2024-001", "X", "ABC", "INVOICE NUMBER PENDING", ""]
for num in test_numbers:
    score, reason = _validate_invoice_number(num, 0.9)
    status = f"{score:.2f}"
    print(f"  {num:30s}  → {status}  {reason or 'ok'}")

print("\n" + "="*60)
print("Lesson 04 complete. Move on to: lessons/05_review_queue/")
print("="*60)
