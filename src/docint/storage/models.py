"""
SQLAlchemy models — the storage schema for the pipeline.

Three tables:
  documents     — one row per uploaded file, tracks processing state
  extractions   — one row per completed extraction, stores the JSON result
  review_items  — one row per document that needs or has gone through human review

State machine for documents:
  pending → processing → extracted → approved
                       ↘ needs_review → approved / rejected
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, relationship


def _now():
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_name = Column(String(512), nullable=False)
    file_path = Column(String(1024), nullable=False)
    file_format = Column(String(32), nullable=False)  # pdf, docx, xlsx, image
    document_type = Column(String(64), nullable=False)  # invoice, logistics, ...
    status = Column(String(32), nullable=False, default="pending")
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now)

    extraction = relationship("Extraction", back_populates="document", uselist=False)
    review_item = relationship("ReviewItem", back_populates="document", uselist=False)


class Extraction(Base):
    __tablename__ = "extractions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    schema_type = Column(String(64), nullable=False)
    result_json = Column(JSON, nullable=False)  # The full ExtractionResult as JSON
    overall_confidence = Column(Float, nullable=False)
    low_confidence_fields = Column(JSON, nullable=True)  # list[str]
    model_used = Column(String(128), nullable=False)
    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now)

    document = relationship("Document", back_populates="extraction")


class ReviewItem(Base):
    __tablename__ = "review_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    priority_score = Column(Float, nullable=False, default=0.5)
    trigger_reason = Column(String(256), nullable=False)  # why it was flagged
    status = Column(String(32), nullable=False, default="pending")  # pending, approved, rejected
    reviewed_by = Column(String(128), nullable=True)
    corrections_json = Column(JSON, nullable=True)  # human corrections as JSON diff
    created_at = Column(DateTime(timezone=True), default=_now)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    document = relationship("Document", back_populates="review_item")
