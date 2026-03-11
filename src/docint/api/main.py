"""
FastAPI application — entry point for the document intelligence API.

Key design: document upload is synchronous and fast (just saves the file).
Extraction runs as a BackgroundTask — the client polls /documents/{id}/status
to check when it's done. This avoids HTTP timeouts on large documents.
"""
import os
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ..storage.models import Base
from .routes.documents import router as documents_router
from .routes.review import router as review_router

log = structlog.get_logger()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://docint:docint@localhost:5432/docint")
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "./uploads"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    engine = create_async_engine(DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    app.state.engine = engine
    app.state.session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    log.info("api.startup", database=DATABASE_URL)
    yield
    # Shutdown
    await engine.dispose()
    log.info("api.shutdown")


app = FastAPI(
    title="Document Intelligence Pipeline",
    description="Extract structured data from enterprise documents",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(documents_router, prefix="/documents", tags=["documents"])
app.include_router(review_router, prefix="/review", tags=["review"])


@app.get("/health")
async def health():
    return {"status": "ok"}
