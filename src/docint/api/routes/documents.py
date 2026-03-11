"""
Document routes:
  POST /documents/upload   — upload a file, start extraction in background
  GET  /documents/{id}     — get document status + extraction result
  GET  /documents/         — list all documents
"""
import shutil
import uuid
from pathlib import Path

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ...extraction.schemas.registry import available_types
from ...pipeline.orchestrator import DocumentPipeline
from ...storage.repository import create_document, get_document, get_extraction

log = structlog.get_logger()
router = APIRouter()
pipeline = DocumentPipeline()


def get_session(request: Request):
    return request.app.state.session_factory()


@router.post("/upload")
async def upload_document(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    schema_type: str = Form(...),
):
    """Upload a document file and start extraction asynchronously."""
    if schema_type not in available_types():
        raise HTTPException(
            status_code=422,
            detail=f"Unknown schema_type {schema_type!r}. Available: {available_types()}",
        )

    # Save file to disk
    upload_dir = Path(request.app.state.engine.url.database or "uploads").parent / "uploads"
    upload_dir = Path("uploads")
    upload_dir.mkdir(exist_ok=True)

    suffix = Path(file.filename or "upload").suffix.lower()
    saved_name = f"{uuid.uuid4()}{suffix}"
    saved_path = upload_dir / saved_name

    with open(saved_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    log.info("upload.saved", filename=file.filename, saved_as=str(saved_path))

    # Create DB record
    async with request.app.state.session_factory() as session:
        doc = await create_document(
            session=session,
            file_name=file.filename or saved_name,
            file_path=str(saved_path),
            file_format=suffix.lstrip("."),
            document_type=schema_type,
        )
        document_id = str(doc.id)

    # Run pipeline in background so we return immediately
    background_tasks.add_task(
        _run_pipeline_bg,
        request.app.state.session_factory,
        document_id,
        str(saved_path),
        schema_type,
    )

    return {"document_id": document_id, "status": "pending", "message": "Extraction started"}


@router.get("/{document_id}")
async def get_document_status(document_id: str, request: Request):
    """Get document status and extraction result."""
    async with request.app.state.session_factory() as session:
        doc = await get_document(session, document_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        result = {
            "document_id": str(doc.id),
            "file_name": doc.file_name,
            "document_type": doc.document_type,
            "status": doc.status,
            "created_at": doc.created_at.isoformat(),
        }

        if doc.status in ("extracted", "needs_review", "approved"):
            extraction = await get_extraction(session, document_id)
            if extraction:
                result["extraction"] = {
                    "overall_confidence": extraction.overall_confidence,
                    "low_confidence_fields": extraction.low_confidence_fields,
                    "data": extraction.result_json,
                }

        if doc.status == "failed":
            result["error"] = doc.error_message

        return result


async def _run_pipeline_bg(session_factory, document_id, file_path, document_type):
    """Background task: run the pipeline and update DB."""
    async with session_factory() as session:
        try:
            await pipeline.process(
                session=session,
                document_id=document_id,
                file_path=file_path,
                document_type=document_type,
            )
        except Exception as exc:
            log.error("background_pipeline.error", document_id=document_id, error=str(exc))
