"""
Review queue routes:
  GET  /review/queue           — list pending review items (highest priority first)
  POST /review/{id}/approve    — approve an extraction (with optional corrections)
  POST /review/{id}/reject     — reject an extraction
"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ...storage.repository import (
    approve_review_item,
    get_pending_review_items,
    reject_review_item,
)

router = APIRouter()


class ApproveRequest(BaseModel):
    reviewed_by: str
    corrections: dict | None = None  # field_name → corrected_value


class RejectRequest(BaseModel):
    reviewed_by: str


@router.get("/queue")
async def get_review_queue(request: Request, limit: int = 50):
    """Return pending review items, highest priority first."""
    async with request.app.state.session_factory() as session:
        items = await get_pending_review_items(session, limit=limit)
        return [
            {
                "review_item_id": str(item.id),
                "document_id": str(item.document_id),
                "priority_score": item.priority_score,
                "trigger_reason": item.trigger_reason,
                "created_at": item.created_at.isoformat(),
            }
            for item in items
        ]


@router.post("/{review_item_id}/approve")
async def approve(review_item_id: str, body: ApproveRequest, request: Request):
    async with request.app.state.session_factory() as session:
        await approve_review_item(
            session=session,
            review_item_id=review_item_id,
            reviewed_by=body.reviewed_by,
            corrections=body.corrections,
        )
    return {"status": "approved", "review_item_id": review_item_id}


@router.post("/{review_item_id}/reject")
async def reject(review_item_id: str, body: RejectRequest, request: Request):
    async with request.app.state.session_factory() as session:
        await reject_review_item(
            session=session,
            review_item_id=review_item_id,
            reviewed_by=body.reviewed_by,
        )
    return {"status": "rejected", "review_item_id": review_item_id}
