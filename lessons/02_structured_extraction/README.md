# Lesson 02 — Structured Extraction

**Goal:** Understand why `tool_use` is the right way to get structured data from an LLM — not prompting for JSON.

---

## The naive approach (and why it breaks)

Most people start here:

```python
response = client.messages.create(
    model="claude-sonnet-4-6",
    messages=[{
        "role": "user",
        "content": f"Extract the invoice fields from this text and return JSON:\n\n{text}"
    }]
)
# Now parse response.content[0].text as JSON...
```

This works for demos. In production it fails because:
1. The model sometimes wraps JSON in markdown fences (`` ```json ... ``` ``)
2. The model sometimes adds explanatory text before/after the JSON
3. The model can invent fields not in your schema, or omit required ones
4. Validation is your problem — you only discover failures at runtime

---

## The right approach: `tool_use`

Claude's `tool_use` feature lets you define a tool with a JSON Schema for its parameters.
When you set `tool_choice={"type": "tool", "name": "extract_document"}`, Claude **must**
call that tool — and the output is always valid JSON conforming to your schema.

```python
tools = [{
    "name": "extract_document",
    "description": "Extract structured invoice data",
    "input_schema": InvoiceResult.model_json_schema()  # Pydantic → JSON Schema
}]

response = client.messages.create(
    model="claude-sonnet-4-6",
    tools=tools,
    tool_choice={"type": "tool", "name": "extract_document"},
    messages=[{"role": "user", "content": text}]
)

# Always a tool_use block — no markdown, no extra text
tool_block = next(b for b in response.content if b.type == "tool_use")
result = InvoiceResult.model_validate(tool_block.input)  # Pydantic validates
```

The JSON Schema comes directly from `InvoiceResult.model_json_schema()`. Pydantic and Claude
are speaking the same schema language — no translation needed.

---

## The extraction / inference distinction

**Extraction** = copy information that's explicitly in the document
**Inference** = derive information not directly stated

For document intelligence, you almost always want pure extraction. The system prompt says:
> "Do NOT infer, guess, or fabricate values — leave fields empty/null if not found"

This might seem obvious but it matters: if the invoice has no due date, you want `None`,
not a date the model calculated from payment terms. Your downstream system needs to know
"this field was missing" vs. "this field has this value."

---

## Exercise

```bash
python lessons/02_structured_extraction/exercise.py
```

The exercise demonstrates:
1. How `model_json_schema()` works — what Pydantic generates
2. Building a tool definition from a schema
3. Running a real extraction call on sample invoice text
4. What happens when the model finds a field vs. when it doesn't

**You need an `ANTHROPIC_API_KEY` in your `.env` file for this lesson.**

---

## Key concepts from `src/docint/extraction/`

- [extractor.py](../../src/docint/extraction/extractor.py) — the full extraction engine
- [schemas/base.py](../../src/docint/extraction/schemas/base.py) — `ExtractionResult` with confidence fields
- [schemas/invoice.py](../../src/docint/extraction/schemas/invoice.py) — the invoice schema

---

## Next

→ [Lesson 03 — Schema Design](../03_schema_design/README.md)
