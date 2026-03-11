"""
Lesson 05 — Human Review Queue Exercise

Simulates the review queue workflow without requiring a running database.
Shows how priority scoring, display, and corrections work end-to-end.

Run: python lessons/05_review_queue/exercise.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

from docint.pipeline.review_queue import ReviewTask, render_review_task, compute_corrections


def section(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


# ── Simulate a review queue ──────────────────────────────────────────────────

# These represent documents that came out of the pipeline with low confidence
MOCK_QUEUE = [
    ReviewTask(
        review_item_id="review-001",
        document_id="doc-001",
        document_type="invoice",
        file_name="invoice_q3_vendor_acme.pdf",
        priority_score=0.72,
        trigger_reason="overall confidence 0.28 < threshold 0.75; low fields: total_amount, currency, iban",
        extracted_data={
            "invoice_number": "INV-2024-0042",
            "vendor_name": "Acme GmbH",
            "customer_name": "TechCorp BV",
            "total_amount": "5000-6000",      # ambiguous range
            "currency": "Euro",               # should be "EUR"
            "iban": "XX99 9999 INVALID 9999", # invalid IBAN
            "invoice_date": "2024-11-15",
            "extraction_notes": "Amount was stated as a range. Currency not in ISO format. IBAN appears invalid.",
        },
        low_confidence_fields=["total_amount", "currency", "iban"],
    ),
    ReviewTask(
        review_item_id="review-002",
        document_id="doc-002",
        document_type="invoice",
        file_name="scan_invoice_nov.pdf",
        priority_score=0.45,
        trigger_reason="overall confidence 0.55 < threshold 0.75; low fields: vendor_name, invoice_number",
        extracted_data={
            "invoice_number": "unclear",
            "vendor_name": "Some Company Europe (?)",
            "total_amount": "12500.00",
            "currency": "EUR",
            "invoice_date": "2024-11-08",
            "extraction_notes": "Scanned document with poor quality. Vendor name partially obscured.",
        },
        low_confidence_fields=["vendor_name", "invoice_number"],
    ),
    ReviewTask(
        review_item_id="review-003",
        document_id="doc-003",
        document_type="logistics",
        file_name="bill_of_lading_0156.pdf",
        priority_score=0.30,
        trigger_reason="overall confidence 0.70 < threshold 0.75; low fields: container_number",
        extracted_data={
            "document_number": "BOL-2024-0156",
            "shipper_name": "Acme Manufacturing AG",
            "consignee_name": "TechCorp Distribution BV",
            "port_of_loading": "Hamburg, Germany",
            "port_of_discharge": "Rotterdam, Netherlands",
            "container_number": "TCKU 123456 7",  # slight formatting uncertainty
            "total_weight_kg": "24500",
            "extraction_notes": "Container number format uncertain — could be TCKU1234567 or TCKU 123456 7",
        },
        low_confidence_fields=["container_number"],
    ),
]


# ── Exercise 1: Understanding the priority queue ─────────────────────────────

section("Exercise 1: How items are prioritized")
print("Review queue ordered by priority (highest = most urgent):\n")

sorted_queue = sorted(MOCK_QUEUE, key=lambda x: x.priority_score, reverse=True)
for i, task in enumerate(sorted_queue, 1):
    bar = "█" * int(task.priority_score * 10) + "░" * (10 - int(task.priority_score * 10))
    print(f"  {i}. [{bar}] {task.priority_score:.2f}  {task.file_name}")
    print(f"     Reason: {task.trigger_reason[:70]}...")
    print()

print("""Priority = 1.0 - overall_confidence

High priority (→ review first):  low confidence, possibly high-value document
Low priority (→ review later):   moderate confidence, minor issues only
""")


# ── Exercise 2: Display a review task ────────────────────────────────────────

section("Exercise 2: Rendering a review task for the reviewer")
print("This is what a reviewer sees for the highest-priority item:\n")
print(render_review_task(sorted_queue[0]))


# ── Exercise 3: Interactive CLI review ───────────────────────────────────────

section("Exercise 3: Interactive review (simplified)")
print("Simulating the review workflow for the first item in the queue.\n")

task = sorted_queue[0]
print(render_review_task(task))

print("\nOptions: [a]pprove  [r]eject  [c]orrect  [s]kip")
choice = input("Your decision: ").strip().lower()

if choice == "a":
    print(f"\nApproved: {task.file_name}")
    print("In the real system: document status → 'approved', review_item.status → 'approved'")

elif choice == "r":
    print(f"\nRejected: {task.file_name}")
    print("In the real system: document status → 'rejected', needs manual processing")

elif choice == "c":
    print("\nEnter corrections (field_name=value, one per line, empty line to finish):")
    corrections = {}
    while True:
        line = input("  > ").strip()
        if not line:
            break
        if "=" in line:
            key, _, value = line.partition("=")
            corrections[key.strip()] = value.strip()

    diff = compute_corrections(task.extracted_data, {**task.extracted_data, **corrections})
    print(f"\nCorrections recorded: {diff}")
    print("In the real system: corrections stored in review_items.corrections_json")
    print("This becomes training data for improving future extractions.")

else:
    print("Skipped — left in queue")


# ── Exercise 4: The feedback loop concept ────────────────────────────────────

section("Exercise 4: The feedback loop")
print("""
When reviewers correct extractions, you accumulate a dataset:

  document text + wrong extraction → correct extraction

This is valuable in several ways:

1. Analytics: which fields fail most? On which document layouts?
   SQL query: SELECT field_name, COUNT(*) FROM corrections GROUP BY field_name

2. Prompt improvement: add correction examples as few-shot examples in the system prompt
   "Here are examples of corrections our reviewers have made: ..."

3. Fine-tuning: if you have hundreds of corrections, you can fine-tune a smaller model
   to match the corrected output. This can reduce both latency and cost.

4. Schema improvement: if reviewers frequently correct a field the same way,
   maybe the field description in the YAML schema needs updating.

The review queue is not just quality control — it's a data flywheel.
""")


# ── Exercise 5: Computing corrections ────────────────────────────────────────

section("Exercise 5: compute_corrections() in detail")

original = {
    "total_amount": "5000-6000",
    "currency": "Euro",
    "iban": "XX99 9999 INVALID 9999",
    "vendor_name": "Acme GmbH",
}

corrected = {
    "total_amount": "5500.00",
    "currency": "EUR",
    "iban": "DE89 3704 0044 0532 0130 00",
    "vendor_name": "Acme GmbH",  # unchanged
}

diff = compute_corrections(original, corrected)
print("Original vs corrected:")
for field, change in diff.items():
    print(f"  {field:20s}  {change['old']!r:30s} → {change['new']!r}")

unchanged = [k for k in original if k not in diff]
print(f"\nUnchanged fields (not stored): {unchanged}")
print("\nOnly changed fields are stored — keeps the corrections_json minimal.")

print("\n" + "="*60)
print("Lesson 05 complete. Move on to: lessons/06_production_api/")
print("="*60)
