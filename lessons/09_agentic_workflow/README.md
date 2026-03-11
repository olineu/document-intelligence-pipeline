# Lesson 09 — Agentic Document Workflows

**Goal:** Know when a single extraction pass isn't enough, and build a multi-step document agent.

---

## When single-pass extraction breaks down

The pipeline so far: parse → extract → validate → store.
One LLM call, one result.

This breaks when:

**Cross-document validation**
An invoice references PO-2024-0156. You need to check that the line items and total
on the invoice match the purchase order. The extractor can't do this — it only sees one document.

**Iterative refinement**
A logistics manifest has a container number with uncertain format (TCKU1234567 vs TCKU 123456 7).
The right move is to cross-reference the carrier's container format rules, then re-extract.
One pass doesn't have this feedback loop.

**Domain rule application**
A contract clause says "penalty of 2% per month, max 10%". Calculating whether a specific
payment triggers the penalty requires: extract the clause, extract the payment date, extract
the due date, compute days overdue, apply the penalty formula. This is multi-step reasoning.

---

## The agent pattern for documents

An agent turns the pipeline into a loop:

```
User query: "Validate this invoice against its PO"
         ↓
   Agent starts
         ↓
   Tool: extract_invoice(invoice.pdf)     → invoice data
         ↓
   Tool: extract_po(po_2024_0156.pdf)     → PO data
         ↓
   Tool: compare_documents(invoice, po)   → discrepancies
         ↓
   Tool: flag_for_review(discrepancies)   → review item created
         ↓
   Agent response: "3 discrepancies found: line item 2 price differs..."
```

Each step is a tool call. The agent decides which tools to call and in what order.

---

## Bounding the agent

Unconstrained agents are expensive and unpredictable. Always set:

- **Max iterations** — stop after N tool calls regardless of task completion
- **Tool whitelist** — the agent can only call tools you've defined
- **Cost limit** — track token usage and abort if it exceeds a budget

For document workflows, you usually know the maximum steps upfront.
A "validate invoice vs PO" workflow needs: extract invoice, extract PO, compare. Max 3 steps.
Hardcode the step limit to 5 to allow for retries but prevent runaway loops.

---

## Exercise

```bash
python lessons/09_agentic_workflow/exercise.py
```

The exercise builds a document validation agent that:
1. Extracts an invoice
2. Extracts the referenced purchase order
3. Compares line items and totals between the two
4. Reports discrepancies with field-level detail

---

## Key concepts from the paralegal-agent pattern

The `paralegal-agent-crew` project shows a multi-agent approach where different agents
specialise in different document types (contracts vs. filings vs. court orders).

Key insight: **specialisation beats generalisation for document agents**.
A contract-specific agent trained on legal document patterns will outperform
a general agent asked to "analyse this contract."

The same principle applies to enterprise documents: a separate agent for each
document type (invoice agent, PO agent, logistics agent) beats one agent that handles all.

---

## Next

→ [Lesson 10 — Document Q&A with Source Citations](../10_document_qa/README.md)
