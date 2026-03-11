"""
Repository layer — all database access goes through these functions.

Keeping DB queries in one module means:
  - The pipeline code never writes SQL
  - Easy to swap Postgres for SQLite in tests
  - Clean audit trail (every state change is explicit)
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Document, Extraction, ReviewItem


# --- Documents ---

async def create_document(
    session: AsyncSession,
    file_name: str,
    file_path: str,
    file_format: str,
    document_type: str,
) -> Document:
    doc = Document(
        file_name=file_name,
        file_path=file_path,
        file_format=file_format,
        document_type=document_type,
        status="pending",
    )
    session.add(doc)
    await session.commit()
    await session.refresh(doc)
    return doc


async def get_document(session: AsyncSession, document_id: str) -> Document | None:
    result = await session.execute(select(Document).where(Document.id == document_id))
    return result.scalar_one_or_none()


async def set_document_status(
    session: AsyncSession,
    document_id: str,
    status: str,
    error_message: str | None = None,
) -> None:
    values = {"status": status, "updated_at": datetime.now(timezone.utc)}
    if error_message is not None:
        values["error_message"] = error_message
    await session.execute(
        update(Document).where(Document.id == document_id).values(**values)
    )
    await session.commit()


# --- Extractions ---

async def create_extraction(
    session: AsyncSession,
    document_id: str,
    schema_type: str,
    result_json: dict,
    overall_confidence: float,
    low_confidence_fields: list[str],
    model_used: str,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
) -> Extraction:
    extraction = Extraction(
        document_id=document_id,
        schema_type=schema_type,
        result_json=result_json,
        overall_confidence=overall_confidence,
        low_confidence_fields=low_confidence_fields,
        model_used=model_used,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )
    session.add(extraction)
    await session.commit()
    await session.refresh(extraction)
    return extraction


async def get_extraction(session: AsyncSession, document_id: str) -> Extraction | None:
    result = await session.execute(
        select(Extraction).where(Extraction.document_id == document_id)
    )
    return result.scalar_one_or_none()


# --- Review Queue ---

async def create_review_item(
    session: AsyncSession,
    document_id: str,
    priority_score: float,
    trigger_reason: str,
) -> ReviewItem:
    item = ReviewItem(
        document_id=document_id,
        priority_score=priority_score,
        trigger_reason=trigger_reason,
        status="pending",
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


async def get_pending_review_items(
    session: AsyncSession,
    limit: int = 50,
) -> list[ReviewItem]:
    """Return pending review items ordered by priority (highest first)."""
    result = await session.execute(
        select(ReviewItem)
        .where(ReviewItem.status == "pending")
        .order_by(ReviewItem.priority_score.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def approve_review_item(
    session: AsyncSession,
    review_item_id: str,
    reviewed_by: str,
    corrections: dict | None = None,
) -> None:
    await session.execute(
        update(ReviewItem)
        .where(ReviewItem.id == review_item_id)
        .values(
            status="approved",
            reviewed_by=reviewed_by,
            corrections_json=corrections,
            reviewed_at=datetime.now(timezone.utc),
        )
    )
    await session.commit()


async def reject_review_item(
    session: AsyncSession,
    review_item_id: str,
    reviewed_by: str,
) -> None:
    await session.execute(
        update(ReviewItem)
        .where(ReviewItem.id == review_item_id)
        .values(
            status="rejected",
            reviewed_by=reviewed_by,
            reviewed_at=datetime.now(timezone.utc),
        )
    )
    await session.commit()
