-- Document Intelligence Pipeline — Initial Schema
-- Run: psql $DATABASE_URL < migrations/001_initial.sql

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ── documents ───────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS documents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_name       VARCHAR(512)    NOT NULL,
    file_path       VARCHAR(1024)   NOT NULL,
    file_format     VARCHAR(32)     NOT NULL,  -- pdf, docx, xlsx, image
    document_type   VARCHAR(64)     NOT NULL,  -- invoice, logistics, ...
    status          VARCHAR(32)     NOT NULL DEFAULT 'pending',
    -- Status values:
    --   pending        → uploaded, waiting for processing
    --   processing     → pipeline running
    --   extracted      → extracted with high confidence, auto-approved
    --   needs_review   → low confidence, in review queue
    --   approved       → human reviewed and approved
    --   rejected       → human rejected, needs manual processing
    --   failed         → pipeline error
    error_message   TEXT,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
CREATE INDEX IF NOT EXISTS idx_documents_document_type ON documents(document_type);
CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at DESC);

-- ── extractions ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS extractions (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id             UUID            NOT NULL REFERENCES documents(id),
    schema_type             VARCHAR(64)     NOT NULL,
    result_json             JSONB           NOT NULL,  -- full ExtractionResult as JSON
    overall_confidence      FLOAT           NOT NULL,
    low_confidence_fields   JSONB,                     -- list of field names
    model_used              VARCHAR(128)    NOT NULL,
    input_tokens            INTEGER,
    output_tokens           INTEGER,
    created_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_extractions_document_id ON extractions(document_id);
CREATE INDEX IF NOT EXISTS idx_extractions_confidence ON extractions(overall_confidence);

-- ── review_items ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS review_items (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id     UUID            NOT NULL REFERENCES documents(id),
    priority_score  FLOAT           NOT NULL DEFAULT 0.5,
    -- 0.0 = low priority, 1.0 = urgent
    -- Computed as: 1.0 - overall_confidence
    trigger_reason  VARCHAR(256)    NOT NULL,
    status          VARCHAR(32)     NOT NULL DEFAULT 'pending',
    -- pending | approved | rejected
    reviewed_by     VARCHAR(128),
    corrections_json JSONB,         -- {field_name: {old: val, new: val}, ...}
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    reviewed_at     TIMESTAMPTZ
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_review_items_document_id ON review_items(document_id);
CREATE INDEX IF NOT EXISTS idx_review_items_status_priority
    ON review_items(status, priority_score DESC)
    WHERE status = 'pending';

-- ── updated_at trigger ───────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS documents_updated_at ON documents;
CREATE TRIGGER documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
