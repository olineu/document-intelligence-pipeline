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

## After the Course

Once you've completed all 6 lessons, the next steps are:

1. **Add a new schema** — pick a document type you encounter at work, write the YAML + Pydantic model, test it end-to-end
2. **Integrate `model-monitor`** — add drift detection to track when extraction quality degrades over time (see `../model-monitor` in the roadmap)
3. **Connect to `mlops-pipeline`** — log extraction runs to MLflow, track prompt changes as experiments
4. **Scale with PySpark** — if you need to process 100k+ documents, see `../pyspark-llm-pipeline`
