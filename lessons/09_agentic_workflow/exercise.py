"""
Lesson 09 — Agentic Document Workflows Exercise

Builds a document validation agent that cross-references an invoice against its PO.

The agent has access to tools:
  - extract_document(file_content, schema_type) → extracted fields
  - compare_documents(doc_a, doc_b, fields) → discrepancies
  - compute_totals(line_items) → expected total
  - flag_discrepancy(field, invoice_value, po_value) → review note

Run: python lessons/09_agentic_workflow/exercise.py
Requires: ANTHROPIC_API_KEY in .env
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

from dotenv import load_dotenv
load_dotenv()


def section(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


# ── Sample document pair: invoice + PO with a deliberate discrepancy ─────────

INVOICE_TEXT = """
INVOICE INV-2024-0042
PO Reference: PO-2024-0156
Vendor: Acme Software GmbH | Customer: TechCorp Europe BV
Date: 2024-11-15 | Due: 2024-12-15

Line Items:
1. Software License (Annual) - 1 unit - EUR 8,500.00
2. Implementation Support - 20 hours - EUR 155.00/hr = EUR 3,100.00  ← different rate!
3. User Training - 2 days - EUR 1,200.00/day = EUR 2,400.00

Subtotal: EUR 14,000.00
VAT (19%): EUR 2,660.00
TOTAL: EUR 16,660.00
"""

PURCHASE_ORDER_TEXT = """
PURCHASE ORDER PO-2024-0156
Buyer: TechCorp Europe BV | Supplier: Acme Software GmbH
Date: 2024-10-01 | Delivery: 2024-11-01

Approved Line Items:
1. Software License (Annual) - 1 unit - EUR 8,500.00
2. Implementation Support - 20 hours - EUR 150.00/hr = EUR 3,000.00  ← original rate
3. User Training - 2 days - EUR 1,200.00/day = EUR 2,400.00

Approved Total: EUR 13,900.00 + VAT
Approved by: Sarah Miller, VP Procurement
"""


# ── Tool implementations ─────────────────────────────────────────────────────

def extract_document_tool(document_text: str, schema_type: str) -> dict:
    """Extract structured fields from a document text."""
    import anthropic

    client = anthropic.Anthropic()

    # Simple extraction for demo — returns key financial fields
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        messages=[{
            "role": "user",
            "content": (
                f"Extract the following from this {schema_type}:\n"
                "- document_number\n"
                "- vendor_name / supplier_name\n"
                "- total_amount\n"
                "- line_items (description, quantity, unit_price, total)\n\n"
                f"Return as JSON.\n\nDocument:\n{document_text}"
            )
        }],
    )

    # Parse the response (in production, use tool_use for guaranteed JSON)
    try:
        text = response.content[0].text
        # Find JSON block
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
    except Exception:
        pass
    return {"raw": response.content[0].text}


def compare_line_items(invoice_items: list, po_items: list) -> list[dict]:
    """Compare line items between invoice and PO, find discrepancies."""
    discrepancies = []

    for i, (inv_item, po_item) in enumerate(zip(invoice_items, po_items), 1):
        for field in ["unit_price", "total", "quantity"]:
            inv_val = inv_item.get(field)
            po_val = po_item.get(field)
            if inv_val and po_val:
                try:
                    inv_num = float(str(inv_val).replace(",", "").replace("EUR", "").strip())
                    po_num = float(str(po_val).replace(",", "").replace("EUR", "").strip())
                    if abs(inv_num - po_num) > 0.01:
                        discrepancies.append({
                            "line": i,
                            "field": field,
                            "invoice": inv_val,
                            "po": po_val,
                            "difference": inv_num - po_num,
                        })
                except Exception:
                    pass

    return discrepancies


def compare_totals(invoice_total: str, po_total: str) -> dict | None:
    """Compare document-level totals."""
    try:
        inv = float(str(invoice_total).replace(",", "").replace("EUR", "").strip())
        po = float(str(po_total).replace(",", "").replace("EUR", "").strip())
        if abs(inv - po) > 0.01:
            return {"invoice": invoice_total, "po": po_total, "difference": inv - po}
    except Exception:
        pass
    return None


# ── Exercise 1: Manual multi-step workflow ───────────────────────────────────

section("Exercise 1: Manual multi-step validation workflow")
print("Step 1: Extract invoice...")

try:
    import anthropic

    invoice_data = extract_document_tool(INVOICE_TEXT, "invoice")
    print(f"Invoice extracted: {list(invoice_data.keys())}")

    print("\nStep 2: Extract purchase order...")
    po_data = extract_document_tool(PURCHASE_ORDER_TEXT, "purchase_order")
    print(f"PO extracted: {list(po_data.keys())}")

    print("\nStep 3: Compare line items...")
    inv_items = invoice_data.get("line_items", [])
    po_items = po_data.get("line_items", [])

    if inv_items and po_items:
        discrepancies = compare_line_items(inv_items, po_items)
        if discrepancies:
            print(f"\nDISCREPANCIES FOUND ({len(discrepancies)}):")
            for d in discrepancies:
                print(f"  Line {d['line']}, {d['field']}:")
                print(f"    Invoice: {d['invoice']}")
                print(f"    PO:      {d['po']}")
                print(f"    Delta:   EUR {d['difference']:.2f}")
        else:
            print("No discrepancies found in line items.")
    else:
        print("Could not compare line items — raw extraction result:")
        print(f"  Invoice items: {inv_items}")
        print(f"  PO items:      {po_items}")

except ImportError:
    print("[anthropic not installed]")


# ── Exercise 2: Agent-driven workflow ────────────────────────────────────────

section("Exercise 2: Agent-driven validation with tool_use")
print("""
Instead of hardcoding the steps, we give the agent tools and let it decide
the sequence. This is more flexible for documents with unexpected structures.

Tools the agent has:
  - extract_fields(text, fields_to_extract) → dict
  - compare_amounts(amount_a, amount_b) → {match, difference}
  - flag_discrepancy(description) → review note

The agent receives the task: "Validate this invoice against its PO"
and decides which tools to call and in what order.
""")

# Define tools for the agent
AGENT_TOOLS = [
    {
        "name": "extract_fields",
        "description": "Extract specific fields from a document text.",
        "input_schema": {
            "type": "object",
            "properties": {
                "document_text": {"type": "string", "description": "The document text to extract from"},
                "fields": {"type": "array", "items": {"type": "string"}, "description": "Field names to extract"},
            },
            "required": ["document_text", "fields"],
        },
    },
    {
        "name": "compare_amounts",
        "description": "Compare two monetary amounts and return whether they match.",
        "input_schema": {
            "type": "object",
            "properties": {
                "amount_a": {"type": "string"},
                "amount_b": {"type": "string"},
                "context": {"type": "string", "description": "What is being compared"},
            },
            "required": ["amount_a", "amount_b", "context"],
        },
    },
    {
        "name": "report_discrepancy",
        "description": "Report a discrepancy found during validation.",
        "input_schema": {
            "type": "object",
            "properties": {
                "field": {"type": "string"},
                "invoice_value": {"type": "string"},
                "po_value": {"type": "string"},
                "severity": {"type": "string", "enum": ["low", "medium", "high"]},
            },
            "required": ["field", "invoice_value", "po_value", "severity"],
        },
    },
]

# Implement tool handlers
def handle_tool(name: str, inputs: dict) -> str:
    if name == "extract_fields":
        fields = inputs["fields"]
        text = inputs["document_text"]
        # Simple keyword extraction for demo
        result = {}
        for field in fields:
            if "total" in field.lower() and "EUR" in text:
                import re
                amounts = re.findall(r"EUR\s?[\d,]+\.?\d*", text)
                result[field] = amounts[-1] if amounts else "not found"
            elif "vendor" in field.lower() or "supplier" in field.lower():
                result[field] = "Acme Software GmbH"
            else:
                result[field] = "extracted"
        return json.dumps(result)

    elif name == "compare_amounts":
        a = inputs["amount_a"].replace("EUR", "").replace(",", "").strip()
        b = inputs["amount_b"].replace("EUR", "").replace(",", "").strip()
        try:
            diff = float(a) - float(b)
            match = abs(diff) < 0.01
            return json.dumps({"match": match, "difference": diff, "context": inputs.get("context", "")})
        except Exception:
            return json.dumps({"match": False, "error": "Could not parse amounts"})

    elif name == "report_discrepancy":
        return json.dumps({"recorded": True, "discrepancy": inputs})

    return json.dumps({"error": f"Unknown tool: {name}"})


try:
    import anthropic
    client = anthropic.Anthropic()

    # Agentic loop
    print("Starting agent... (max 6 tool calls)\n")
    messages = [{
        "role": "user",
        "content": (
            f"Validate this invoice against its purchase order. "
            f"Check: totals match, line item prices match.\n\n"
            f"INVOICE:\n{INVOICE_TEXT}\n\n"
            f"PURCHASE ORDER:\n{PURCHASE_ORDER_TEXT}"
        ),
    }]

    iterations = 0
    discrepancies_found = []

    while iterations < 6:
        iterations += 1
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1000,
            tools=AGENT_TOOLS,
            messages=messages,
        )

        # Collect tool calls
        tool_calls = [b for b in response.content if b.type == "tool_use"]
        text_blocks = [b for b in response.content if b.type == "text"]

        if text_blocks:
            print(f"Agent: {text_blocks[0].text[:200]}")

        if not tool_calls:
            print("\n[Agent finished — no more tool calls]")
            break

        # Add assistant response to history
        messages.append({"role": "assistant", "content": response.content})

        # Process tool calls and add results
        tool_results = []
        for tc in tool_calls:
            print(f"  → Tool: {tc.name}({list(tc.input.keys())})")
            result = handle_tool(tc.name, tc.input)
            result_data = json.loads(result)
            if tc.name == "report_discrepancy":
                discrepancies_found.append(result_data.get("discrepancy", {}))
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tc.id,
                "content": result,
            })

        messages.append({"role": "user", "content": tool_results})

        if response.stop_reason == "end_turn":
            break

    print(f"\nValidation complete in {iterations} iteration(s)")
    if discrepancies_found:
        print(f"Discrepancies reported: {len(discrepancies_found)}")
        for d in discrepancies_found:
            print(f"  [{d.get('severity', '?').upper()}] {d.get('field')}: "
                  f"invoice={d.get('invoice_value')} vs PO={d.get('po_value')}")

except ImportError:
    print("[anthropic not installed]")
except Exception as e:
    print(f"[Error: {e}]")


# ── Exercise 3: When NOT to use agents ───────────────────────────────────────

section("Exercise 3: The agent decision framework")
print("""
Use a single extraction pass when:
  ✓ You know exactly which fields you need
  ✓ All information is in one document
  ✓ No cross-referencing required
  ✓ Cost and latency matter (agents are 3–10× more expensive)

Use an agent loop when:
  ✓ Multi-document cross-referencing (invoice ↔ PO ↔ delivery note)
  ✓ Iterative validation (extract → check rule → re-extract if needed)
  ✓ Domain-specific reasoning (legal clause interpretation, contract compliance)
  ✓ The document structure is unpredictable

Cost guardrails for production agents:
  - Max iterations: hardcode, never let user input control this
  - Token budget: abort if input_tokens > threshold
  - Audit trail: log every tool call and result
  - Timeout: agent must complete within N seconds or return partial result

The paralegal-agent-crew pattern (multi-agent) goes further:
  - Document Classifier Agent → routes to the right specialist
  - Invoice Agent, Contract Agent, Court Filing Agent → domain specialists
  - Coordinator Agent → assembles final answer from specialist outputs
""")

print("="*60)
print("Lesson 09 complete. Move on to: lessons/10_document_qa/")
print("="*60)
