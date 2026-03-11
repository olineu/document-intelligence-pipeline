# document-intelligence-pipeline

> Extract structured data from enterprise documents — PDFs, Word files, spreadsheets, and scanned images — using LLMs with confidence scoring, schema validation, and a human review queue.

---

## What this is

A production-grade document intelligence system that solves a real problem: enterprises are drowning in unstructured documents (invoices, logistics manifests, contracts, reports) and need structured data out of them at scale.

This repo is both a **working system** and a **structured course**. The `src/` directory contains the full pipeline. The `lessons/` directory walks through each concept from scratch.

```
raw document (PDF/DOCX/XLSX/image)
        ↓
    [Parser]  — extract raw text per format
        ↓
  [Extractor] — LLM structured extraction → Pydantic schema
        ↓
[Confidence]  — score each field, flag uncertain extractions
        ↓
[Review Queue]— route low-confidence docs to human review
        ↓
  [Storage]   — Postgres with full audit trail
        ↓
    [API]     — FastAPI endpoints for upload, status, review
```

---

## Course Structure

| Lesson | Topic | Key concept |
|--------|-------|-------------|
| [01](lessons/01_document_parsing/) | Document Parsing | Why PDFs are hard; pdfplumber vs PyMuPDF; OCR |
| [02](lessons/02_structured_extraction/) | Structured Extraction | LLM → Pydantic; tool_use for reliable JSON |
| [03](lessons/03_schema_design/) | Schema Design | Designing extraction schemas; schema registry pattern |
| [04](lessons/04_confidence_scoring/) | Confidence Scoring | Field-level uncertainty; validation rules |
| [05](lessons/05_review_queue/) | Human Review Queue | State machine; priority scoring; feedback loop |
| [06](lessons/06_production_api/) | Production API | FastAPI; async processing; Docker Compose |

Work through lessons in order. Each builds on the previous one.

---

## Quick Start

```bash
# 1. Clone and install
git clone https://github.com/olineu/document-intelligence-pipeline
cd document-intelligence-pipeline
pip install -e ".[dev]"

# 2. Copy env and fill in your API key
cp .env.example .env

# 3. Start Postgres
docker-compose up -d db

# 4. Run migrations
psql $DATABASE_URL < migrations/001_initial.sql

# 5. Start the API
uvicorn src.docint.api.main:app --reload

# 6. Submit a document
curl -X POST http://localhost:8000/documents/upload \
  -F "file=@sample_documents/invoice_sample.pdf" \
  -F "schema_type=invoice"
```

---

## Supported Formats

| Format | Parser | Notes |
|--------|--------|-------|
| PDF (digital) | pdfplumber | Best for text-heavy PDFs |
| PDF (scanned) | PyMuPDF + Tesseract | OCR fallback when no text layer |
| DOCX | python-docx | Full text + table extraction |
| XLSX | openpyxl | Sheet → row parsing |
| Images (PNG/JPG) | Tesseract | OCR with pre-processing |

---

## Supported Document Types (Schema Registry)

| Schema | File | Use case |
|--------|------|----------|
| `invoice` | `schemas/invoice.yaml` | AP/AR invoice processing |
| `logistics` | `schemas/logistics.yaml` | Shipping manifests, BOLs |

Adding a new document type = writing a YAML schema + a Pydantic model. No code changes to the pipeline.

---

## Stack

- **Python 3.11+** · **FastAPI** · **PostgreSQL** · **Docker**
- **Anthropic Claude** — structured extraction via tool_use
- **pdfplumber** + **PyMuPDF** — PDF parsing
- **python-docx** + **openpyxl** — Office formats
- **Tesseract** — OCR for scanned documents
- **SQLAlchemy** (async) — storage layer
- **Pydantic v2** — schema validation

---

## Project Layout

```
src/docint/
├── parsers/          # Format-specific parsers (PDF, DOCX, XLSX, image)
├── extraction/       # LLM extraction engine + schemas + confidence scoring
│   └── schemas/      # Pydantic extraction schemas (invoice, logistics, ...)
├── pipeline/         # Orchestrator + human review queue
├── storage/          # SQLAlchemy models + repository layer
└── api/              # FastAPI app + routes

lessons/              # Hands-on course — work through in order
schemas/              # YAML schema registry
migrations/           # SQL migrations
tests/                # Test suite
```
