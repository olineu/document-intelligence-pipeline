# Document Intelligence Pipeline — Personal Course

> Your self-paced curriculum for this project.
> Goal: understand every file deeply enough to explain it without notes.
> Approach: read → run the exercise → understand → modify → break → fix → explain out loud.

---

## The rule

**No moving to the next lesson until you can explain the current one out loud — without looking at the code.**

If you can't explain it, you haven't learned it yet. Go back.

---

## Before you start

Install and verify everything works before lesson 1:

```bash
pip install -e ".[dev]"
cp .env.example .env  # add your ANTHROPIC_API_KEY
```

Run the first exercise with no API key needed:
```bash
python lessons/01_document_parsing/exercise.py
```

---

## Lesson 1 — Document parsing: getting text out of files

**Concept to understand:**
Before any LLM work happens, you need raw text. The problem is that documents come in formats that were designed for *rendering*, not for *reading by machines*. A PDF is a set of drawing instructions for a printer — it has no concept of "sentence" or "paragraph". Extracting clean text from it is a solved-but-messy problem.

**The analogy:** A PDF is like a printed newspaper. You can read it, but extracting the article text programmatically requires understanding the layout, columns, and where one article ends and another begins.

**Your task:**
1. Open `src/docint/parsers/pdf.py`
2. Read `parse()` — it tries pdfplumber first, then falls back to OCR. Find `_MIN_TEXT_THRESHOLD = 20`. Why 20 characters? What would happen with threshold = 0?
3. Read `_extract_with_pdfplumber()` — notice `x_tolerance=3, y_tolerance=3`. This controls how aggressively pdfplumber groups nearby characters into words. Find `_table_to_markdown()` — what does it produce?
4. Read `_extract_with_ocr()` — find `fitz.Matrix(2.0, 2.0)`. Why render at 2× zoom instead of 1×?
5. Open `src/docint/parsers/base.py` — read `ParsedDocument`. Notice `full_text` is a property. What does it return and why isn't it just `text`?
6. Run the exercise: `python lessons/01_document_parsing/exercise.py`
7. Find Exercise 2 in the exercise file — it creates a `ParsedDocument` manually. Change the `tables` value and call `doc.full_text` again. Does the output change?

**You've passed this lesson when you can answer:**
- Why does the PDF parser try pdfplumber before OCR? What's the cost of using OCR on a PDF that already has a text layer?
- What is the difference between a "digital" PDF and a "scanned" PDF? How does the parser tell them apart?
- Why does every parser return a `ParsedDocument` instead of just a string? What does the uniform interface buy you?

---

## Lesson 2 — Structured extraction: why `tool_use` instead of "return JSON"

**Concept to understand:**
You could ask Claude "extract the invoice number and return JSON". That works sometimes. The problem is the model might wrap the JSON in a markdown code block, add explanatory text, hallucinate field names, or return slightly wrong structure. `tool_use` solves this: you define a JSON Schema and the model is *forced* to return a response that conforms to it. Validation then happens in Pydantic — in Python code, not in a prompt instruction.

**The analogy:** Asking the model to "return JSON" is like asking a contractor to "write it in the contract". `tool_use` is like having a lawyer present who won't let either party sign until the wording is exactly right.

**Your task:**
1. Open `src/docint/extraction/extractor.py`
2. Read `extract()` — trace the full path: schema_cls → tool_schema → API call → `tool_use_block.input` → `model_validate()`
3. Find `tool_choice={"type": "tool", "name": "extract_document"}` — what does this do? What would happen without it?
4. Find `_build_tool_schema()` — it calls `schema_cls.model_json_schema()`. This is the Pydantic model turning itself into a JSON Schema that Claude reads. What do the field descriptions in the schema come from?
5. Open `src/docint/extraction/schemas/base.py` — read `ExtractionResult`. Why does every schema carry `field_confidence` alongside the extracted data?
6. Run the exercise: `python lessons/02_structured_extraction/exercise.py`
7. In Exercise 1 in the exercise file, find `InvoiceResult.model_json_schema()`. Add a `print(json.dumps(schema, indent=2))` call and run it — read what Claude actually receives.

**You've passed this lesson when you can answer:**
- What does `tool_choice={"type": "tool", "name": "extract_document"}` do to Claude's response?
- What is `model_json_schema()`? Where does the `description` for each field come from?
- Why is validation in Pydantic better than validating inside a prompt ("extract only valid IBANs")?

---

## Lesson 3 — Schema design: what you ask for shapes what you get

**Concept to understand:**
The schema is the contract between the document and your downstream system. A bad schema means Claude extracts the wrong things, downstream code breaks on missing fields, or you lose precision by collapsing structured data into strings. The key design tensions: how Optional to be, how nested to go, and what data types to use.

**Your task:**
1. Open `src/docint/extraction/schemas/invoice.py`
2. Look at every field — count how many are `Optional`. Why are most fields Optional? What real-world invoice would be missing `due_date`?
3. Find `line_items: list[LineItem]` — this is a nested schema. `LineItem` itself extends `ExtractionResult`, which means it has its own `field_confidence` list. Is that useful or excessive?
4. Notice that `vendor_address` is a `str`, not a structured object with street/city/country. Why?
5. Open `src/docint/extraction/schemas/registry.py` — read how a new schema type is registered. How many lines would it take to add a new document type?
6. Run the exercise: `python lessons/03_schema_design/exercise.py`
7. In the exercise, find `input("Press Enter when ready...")` — before you press Enter, write down on paper the fields you'd put in a PurchaseOrder schema. Then compare with what the exercise shows.

**You've passed this lesson when you can answer:**
- Why should almost all schema fields be Optional by default?
- Why is `vendor_address: str` better than `vendor_address: dict` with sub-fields for this use case?
- What is the YAML schema hints file for? Where does it get used in the pipeline?

---

## Lesson 4 — Confidence scoring: trusting but verifying the LLM

**Concept to understand:**
LLMs hallucinate. For document extraction, a wrong IBAN or wrong invoice total is worse than a missing one — it will propagate silently into a downstream payment system. Two layers of confidence catch different failure modes: the LLM scores itself per field, and deterministic validators check the values against known rules (regex, range checks). The final score is the minimum of both — conservative but safe.

**The analogy:** A doctor who says "I'm 90% confident this is X" and a second doctor who checks the lab results and says "actually the test rules that out". The final diagnosis uses the stricter evidence.

**Your task:**
1. Open `src/docint/extraction/schemas/base.py` — read `overall_confidence()` and `low_confidence_fields()`. What does a score of 0.0 mean? What does `threshold=0.7` mean in practice?
2. Open `src/docint/extraction/confidence.py` — read `_validate_iban()`. What does the regex `^[A-Z]{2}[0-9]{2}[A-Z0-9]{11,30}$` match? What score does a badly-formatted IBAN get?
3. Find `apply_validators()` — trace what happens to a field that has no validator in `_FIELD_VALIDATORS`. Does it get penalised?
4. Notice `current_score = current.score if current else 1.0` — what does the `else 1.0` mean? If the LLM didn't provide a confidence score for a field, what score do we assume?
5. Open `src/docint/pipeline/orchestrator.py` — find `_CONFIDENCE_THRESHOLD`. What happens to a document whose `overall_confidence()` is below it?
6. Run the exercise: `python lessons/04_confidence_scoring/exercise.py`
7. After it runs, manually pick an extracted IBAN from the output and corrupt it (e.g. replace two digits). Then call `_validate_iban(corrupted_value, 0.95)` in a Python shell. What score comes back?

**You've passed this lesson when you can answer:**
- Why is the final confidence the *minimum* of LLM self-score and validator score, not the average?
- What is a "required" field in this confidence context? Where is that enforced?
- If the LLM self-scores `iban` at 0.98 but the IBAN regex fails, what is the final confidence for that field?

---

## Lesson 5 — Human review queue: the quality gate

**Concept to understand:**
Automation handles most documents confidently. The remaining fraction — complex layouts, missing fields, ambiguous values — need a human. The review queue surfaces those documents in priority order: high-value documents with low confidence come first. Crucially, every human correction is stored as a `correction_json` diff — this is the feedback loop that can improve the system over time.

**The analogy:** A hospital triage system. Not every patient needs a doctor immediately. The triage nurse scores urgency and sends the critical cases first. The doctor's diagnosis (the correction) goes into the patient record for future reference.

**Your task:**
1. Open `src/docint/pipeline/orchestrator.py` — find the review routing logic (look for `needs_review`). What is the exact condition that routes a document to review?
2. Find `_compute_priority()` — what is the formula? What priority score does a document with overall_confidence=0.4 get? What about 0.9?
3. Open `src/docint/pipeline/review_queue.py` — read `render_review_task()`. Find the line that adds `← LOW CONFIDENCE`. What data structure does it check?
4. Read `compute_corrections()` — what does it return for a document where `vendor_name` was corrected but `total_amount` was not? Trace it manually.
5. Run the exercise: `python lessons/05_review_queue/exercise.py`
6. After running, find the CLI reviewer — approve one document, reject one. What changes in the printed output?

**You've passed this lesson when you can answer:**
- What is the `priority_score` formula? What kind of document gets the highest priority?
- What does `compute_corrections()` return? Why store only the diffs rather than the full corrected document?
- Why is the review queue described as "not a failure mode"? What does it enable that a fully-automated pipeline can't?

---

## Lesson 6 — The production API: async upload and background processing

**Concept to understand:**
Document extraction is slow — a single document can take 3–10 seconds. You can't block an HTTP request for that long. The pattern: the upload endpoint saves the file, creates a DB record, starts extraction as a background task, and returns a `document_id` immediately. The client polls `GET /documents/{id}` until the status changes from `pending` to `extracted` or `needs_review`.

**The analogy:** A dry cleaner. You drop off your shirt (upload), get a ticket (document_id), and come back later to check if it's ready. The cleaner works in the background. You don't wait at the counter.

**Your task:**
1. Open `src/docint/api/routes/documents.py`
2. Read `upload_document()` — find `background_tasks.add_task(...)`. What does this do? Does the client wait for `_run_pipeline_bg` to finish before receiving the response?
3. Find the line that returns `{"document_id": ..., "status": "pending"}` — this is the response to the upload. How many milliseconds does the client wait before getting this response?
4. Read `get_document_status()` — find the `if doc.status in ("extracted", "needs_review", "approved")` block. Why is the extraction data only included for those statuses?
5. Open `src/docint/pipeline/orchestrator.py` — read `process()`. It calls `set_document_status(session, document_id, "processing")` at the start. Why update status at the start, before extraction completes?
6. Find the `except Exception` block at the end of `process()`. What happens to the document status when the pipeline fails?
7. Run the full stack: `docker compose up`, upload a document, poll until it's done.

**You've passed this lesson when you can answer:**
- What is `BackgroundTasks` in FastAPI? How is it different from `asyncio.create_task`?
- What are the five document statuses? Draw the state machine — which transitions are possible?
- What happens if the server crashes while a background task is running? Is the document stuck in `processing` forever?

---

## Lesson 7 — Your first extension (you write it)

**Task:** Add a `contract` schema for simple legal documents.

The schema should extract:
- `parties: list[str]` — names of the parties to the contract
- `effective_date: Optional[date]`
- `expiry_date: Optional[date]`
- `governing_law: str` — jurisdiction (e.g. "English law", "German law")
- `contract_value: Optional[Decimal]`
- `currency: str`
- `key_obligations: list[str]` — bullet list of main obligations (max 5)
- `termination_clause: str` — one sentence summary

**Rules:**
- Do not ask Claude to write it
- You may ask Claude to explain anything you don't understand
- Use `src/docint/extraction/schemas/invoice.py` as a reference
- Register it in `src/docint/extraction/schemas/registry.py`
- Create `schemas/contract.yaml` with field descriptions (look at `schemas/invoice.yaml` for the format)

**When you're done:**
```bash
# Test it in a Python shell
from docint.extraction.extractor import Extractor
from docint.parsers.base import ParsedDocument
extractor = Extractor()
doc = ParsedDocument(text="[paste a contract snippet here]", source_path="test.txt", format="txt")
result = extractor.extract(doc, "contract")
print(result.model_dump_json(indent=2))
```

---

## What comes after this course

Once you've completed all 7 lessons:

1. **pgvector persistence** — replace the in-memory store with a real Postgres database. Builds directly on lesson 6.
2. **Vision OCR (Lesson 07)** — swap the Tesseract fallback for Claude's vision API. Run `python lessons/07_vision_ocr/exercise.py`.
3. **Dockling parser (Lesson 08)** — semantic document parsing that preserves heading/paragraph/table structure. Run `python lessons/08_dockling/exercise.py`.
4. **Agentic workflow (Lesson 09)** — multi-document cross-referencing (invoice ↔ purchase order validation). Run `python lessons/09_agentic_workflow/exercise.py`.
5. **Document Q&A (Lesson 10)** — answer arbitrary questions over extracted documents with source citations. Run `python lessons/10_document_qa/exercise.py`.
