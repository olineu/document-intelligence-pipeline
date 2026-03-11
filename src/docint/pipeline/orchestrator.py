"""
Pipeline orchestrator — coordinates the full document processing lifecycle.

Flow:
  1. Parse the document (format-specific parser)
  2. Extract structured data (LLM via tool_use)
  3. Apply deterministic validators to confidence scores
  4. Store extraction result
  5. Route to human review if confidence is below threshold
  6. Update document status
"""
import os
from pathlib import Path

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from ..extraction.confidence import apply_validators, score_summary
from ..extraction.extractor import Extractor
from ..parsers import get_parser
from ..storage.repository import (
    create_extraction,
    create_review_item,
    set_document_status,
)

log = structlog.get_logger()

_CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.75"))


class DocumentPipeline:
    def __init__(self, extractor: Extractor | None = None):
        self.extractor = extractor or Extractor()

    async def process(
        self,
        session: AsyncSession,
        document_id: str,
        file_path: str,
        document_type: str,
    ) -> dict:
        """
        Run the full pipeline for a single document.
        Updates the document status in Postgres throughout.
        Returns a summary dict.
        """
        log.info("pipeline.start", document_id=str(document_id), document_type=document_type)

        await set_document_status(session, document_id, "processing")

        try:
            # 1. Parse
            parser = get_parser(file_path)
            parsed = parser.parse(file_path)
            log.info("pipeline.parsed", document_id=str(document_id), chars=len(parsed.text))

            # 2. Extract
            result = self.extractor.extract(parsed, document_type)

            # 3. Validate and adjust confidence scores
            result = apply_validators(result)
            summary = score_summary(result)
            log.info("pipeline.extracted", document_id=str(document_id), **summary)

            # 4. Store extraction
            extraction = await create_extraction(
                session=session,
                document_id=document_id,
                schema_type=document_type,
                result_json=result.model_dump(mode="json"),
                overall_confidence=summary["overall"],
                low_confidence_fields=summary["low_confidence_fields"],
                model_used=self.extractor.model,
            )

            # 5. Route to review if confidence is low
            needs_review = summary["overall"] < _CONFIDENCE_THRESHOLD
            if needs_review:
                low_fields = summary["low_confidence_fields"]
                trigger = f"overall confidence {summary['overall']:.2f} < threshold {_CONFIDENCE_THRESHOLD}"
                if low_fields:
                    trigger += f"; low fields: {', '.join(low_fields[:5])}"

                priority = _compute_priority(summary["overall"])
                await create_review_item(
                    session=session,
                    document_id=document_id,
                    priority_score=priority,
                    trigger_reason=trigger,
                )
                await set_document_status(session, document_id, "needs_review")
                log.info("pipeline.needs_review", document_id=str(document_id), priority=priority)
            else:
                await set_document_status(session, document_id, "extracted")

            return {
                "document_id": str(document_id),
                "status": "needs_review" if needs_review else "extracted",
                "extraction_id": str(extraction.id),
                "confidence": summary,
            }

        except Exception as exc:
            log.error("pipeline.error", document_id=str(document_id), error=str(exc))
            await set_document_status(session, document_id, "failed", error_message=str(exc))
            raise


def _compute_priority(overall_confidence: float) -> float:
    """
    Priority score for the review queue.
    Low confidence → high priority. Scale: 0.0 (low priority) to 1.0 (urgent).
    """
    return round(1.0 - overall_confidence, 3)
