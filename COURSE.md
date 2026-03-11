# Course Guide — Document Intelligence Pipeline

Work through these lessons in order. Each one adds a layer to the system and teaches a concept that will surprise you even if you've worked with LLMs before.

---

## Before You Start

Install everything and make sure the quick-start works:

```bash
pip install -e ".[dev]"
cp .env.example .env  # add your Anthropic API key
docker-compose up -d db
psql $DATABASE_URL < migrations/001_initial.sql
```

---

## Lesson 01 — Document Parsing

**Folder:** `lessons/01_document_parsing/`

**The problem:** Documents come in many formats, and each format has quirks that will break naive approaches.

**What you'll learn:**
- Why PDFs are a rendering format, not a data format — and why that matters
- The difference between a "digital" PDF (has a text layer) and a "scanned" PDF (is just an image)
- How `pdfplumber` extracts text and tables
- How `python-docx` gives you access to paragraphs, tables, and styles
- How `openpyxl` maps spreadsheet cells to Python objects
- How Tesseract OCR works and when to use it

**Run the exercise:**
```bash
python lessons/01_document_parsing/exercise.py
```

**Key insight:** Before any LLM work, you need reliable text extraction. Garbage in, garbage out — the best extractor in the world can't fix a bad parse.

---

## Lesson 02 — Structured Extraction

**Folder:** `lessons/02_structured_extraction/`

**The problem:** You have raw text from a document. You want specific fields out of it as structured data. How do you make this reliable?

**What you'll learn:**
- Why asking the LLM to "return JSON" in a regular prompt is fragile
- How Claude's `tool_use` (structured outputs) eliminates JSON parsing errors
- How Pydantic acts as both schema definition and validation
- The difference between extraction (pulling existing information) and inference (deriving new information)
- How to handle multi-value fields (line items, addresses with multiple lines)

**Run the exercise:**
```bash
python lessons/02_structured_extraction/exercise.py
```

**Key insight:** `tool_use` / function calling forces the model to produce valid JSON conforming to your schema. Validation then happens in Python, not in a prompt.

---

## Lesson 03 — Schema Design

**Folder:** `lessons/03_schema_design/`

**The problem:** Good extraction starts with good schemas. What you ask for shapes what you get.

**What you'll learn:**
- How to design schemas that match what's actually in documents (not an idealised version)
- Why `Optional` fields matter — documents in the wild are incomplete
- How to model nested structures: line items, addresses, parties
- The YAML schema registry pattern: define schemas in config, load them at runtime
- How to add a new document type without changing pipeline code

**Run the exercise:**
```bash
python lessons/03_schema_design/exercise.py
```

**Key insight:** The schema is the contract between the document and your downstream system. Design it for what downstream needs, not for what the document contains.

---

## Lesson 04 — Confidence Scoring

**Folder:** `lessons/04_confidence_scoring/`

**The problem:** LLMs sometimes hallucinate. For document extraction, a wrong field value is worse than a missing one. How do you know when to trust the output?

**What you'll learn:**
- Two sources of confidence: LLM self-reported confidence + deterministic validation rules
- How to ask the LLM to score its own confidence per field
- Post-extraction validators: regex patterns, value range checks, cross-field consistency
- How to compute a document-level confidence score from field-level scores
- The threshold decision: when is "good enough" good enough?

**Run the exercise:**
```bash
python lessons/04_confidence_scoring/exercise.py
```

**Key insight:** Confidence scoring lets you be *selective* about human review — only route truly uncertain documents, not everything. This is what makes automation economically viable.

---

## Lesson 05 — Human Review Queue

**Folder:** `lessons/05_review_queue/`

**The problem:** Automation handles 80% of documents confidently. The remaining 20% need a human. How do you build a review queue that prioritises correctly and closes the feedback loop?

**What you'll learn:**
- The state machine for document processing: `pending → processing → extracted → needs_review → approved / rejected`
- Priority scoring: surface the most important documents first (high value + low confidence)
- The feedback loop: approved corrections become training signal for future prompts
- How to build a simple CLI reviewer
- Audit trail: every decision (human or automated) is logged

**Run the exercise:**
```bash
python lessons/05_review_queue/exercise.py
```

**Key insight:** The review queue is not a failure mode — it's the quality gate that makes the system trustworthy. Design it from day one, not as an afterthought.

---

## Lesson 06 — Production API

**Folder:** `lessons/06_production_api/`

**The problem:** You have a working pipeline. Now you need to expose it as a service that other systems can call.

**What you'll learn:**
- FastAPI async endpoints for document upload, processing status, and review
- Background task processing (don't block the upload request on LLM calls)
- File storage and retrieval
- Health checks and structured error responses
- Running the full stack with Docker Compose

**Run the exercise:**
```bash
# Start the full stack
docker-compose up

# Upload a document
curl -X POST http://localhost:8000/documents/upload \
  -F "file=@sample_documents/invoice_sample.pdf" \
  -F "schema_type=invoice"

# Check status
curl http://localhost:8000/documents/{id}/status
```

**Key insight:** Decoupling upload (sync, fast) from extraction (async, slow) is the key architectural pattern. The client gets an ID immediately; polling or webhooks deliver the result.

---

## Lesson 07 — Vision LLM as OCR

**Folder:** `lessons/07_vision_ocr/`

**The problem:** Tesseract OCR (Lesson 01's fallback) was state-of-the-art in 2015. It fails on complex layouts, multi-column text, tables within images, and non-standard fonts. Vision Language Models (VLMs) read page images the same way a human does — and they're dramatically better.

**What you'll learn:**
- Why Tesseract fails on real-world scanned documents (character segmentation, layout reconstruction)
- How VLMs approach OCR differently: they see the whole page at once as an image
- Swapping the `ImageParser` and PDF OCR fallback to use Claude's vision API instead of Tesseract
- When VLM OCR is worth the cost vs. when Tesseract is sufficient
- The `llama-ocr` pattern: fully local OCR with Llama 3.2 Vision (no API cost)

**Run the exercise:**
```bash
python lessons/07_vision_ocr/exercise.py
```

**Key insight:** For clean digital PDFs, text extraction is free and fast — use it. For anything scanned or image-heavy, VLM OCR is worth the token cost because downstream extraction quality depends entirely on input quality.

**Inspired by:** `llama-ocr`, `gemma3-ocr`, `qwen-2.5VL-ocr` in [ai-engineering-hub](https://github.com/patchy631/ai-engineering-hub)

---

## Lesson 08 — Semantic Document Parsing with Dockling

**Folder:** `lessons/08_dockling/`

**The problem:** All parsers so far produce raw text — a flat string. But documents have structure: a heading means something different than body text; a table cell means something different than a paragraph. Feeding flat text to the extractor throws this structure away.

**What you'll learn:**
- What IBM's [Dockling](https://github.com/DS4SD/docling) library produces: a semantic document model — headers, paragraphs, tables, figures, and captions as distinct typed objects
- How to use Dockling as a drop-in replacement for pdfplumber that produces richer input
- Converting Dockling's `DoclingDocument` into a structured text representation that preserves hierarchy
- Why semantic structure improves extraction accuracy on complex documents (especially those with multiple sections that use the same field names)

**Run the exercise:**
```bash
pip install docling  # separate install — heavy dependency
python lessons/08_dockling/exercise.py
```

**Key insight:** The quality of your extraction output is bounded by the quality of your parsing input. Dockling's semantic model is the best open-source document parser available — worth knowing when standard parsers fall short.

**Inspired by:** `rag-with-dockling` in [ai-engineering-hub](https://github.com/patchy631/ai-engineering-hub)

---

## Lesson 09 — Agentic Document Workflows

**Folder:** `lessons/09_agentic_workflow/`

**The problem:** Some documents can't be processed in a single LLM pass. An invoice that references a purchase order needs the PO to validate the line items. A logistics manifest might need to cross-reference a vessel schedule. A contract might need to extract clauses and then apply jurisdiction-specific rules to each clause.

**What you'll learn:**
- When single-pass extraction is insufficient: multi-document cross-referencing, iterative refinement
- Building an agent loop over documents: extract → validate → lookup → re-extract if needed
- The "paralegal agent" pattern: a domain-specific agent that knows the rules for a document type
- How to use the existing pipeline as a tool within an agent (agents calling extractors)
- Failure modes: runaway agent loops, cost explosions — and how to bound them

**Run the exercise:**
```bash
python lessons/09_agentic_workflow/exercise.py
```

**Key insight:** Agents add power but also complexity and cost. The rule: use a single extraction pass as the default; escalate to an agent loop only when cross-document validation or multi-step reasoning is required.

**Inspired by:** `agentic_rag_deepseek`, `paralegal-agent-crew` in [ai-engineering-hub](https://github.com/patchy631/ai-engineering-hub)

---

## Lesson 10 — Document Q&A with Source Citations

**Folder:** `lessons/10_document_qa/`

**The problem:** Extraction pulls specific known fields. But sometimes you need to answer arbitrary questions over a document: "What are the liability limits in this contract?" or "Which line items were disputed in this invoice?" This is a RAG problem, not an extraction problem — and citations matter.

**What you'll learn:**
- The extraction vs. Q&A distinction: when to use which
- Indexing extracted documents into a vector store for retrieval
- Generating answers with source citations: which sentence/paragraph supports this answer?
- Confidence for Q&A: when the answer is "not found in the document" vs. "here it is"
- Trustworthy RAG: flagging low-confidence answers instead of hallucinating

**Run the exercise:**
```bash
python lessons/10_document_qa/exercise.py
```

**Key insight:** Citation is not optional for enterprise document Q&A. If a user asks "what does the contract say about payment terms?" and gets a wrong answer with no citation, the system is worse than useless — it's actively dangerous. Design for cite-or-abstain from the start.

**Inspired by:** `notebook-lm-clone`, `trustworthy-rag` in [ai-engineering-hub](https://github.com/patchy631/ai-engineering-hub)

---

## After the Course

Once you've completed all lessons, the next steps are:

1. **Add a new schema** — pick a document type you encounter at work, write the YAML + Pydantic model, test it end-to-end
2. **Integrate `model-monitor`** — add drift detection to track when extraction quality degrades over time (see `../model-monitor` in the roadmap)
3. **Connect to `mlops-pipeline`** — log extraction runs to MLflow, track prompt changes as experiments
4. **Scale with PySpark** — if you need to process 100k+ documents, see `../pyspark-llm-pipeline`
