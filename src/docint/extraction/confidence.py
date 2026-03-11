"""
Post-extraction confidence scoring — deterministic validation on top of LLM output.

The LLM provides self-reported confidence scores per field. This module adds
a second layer: rule-based validators that catch mistakes the LLM's self-assessment misses.

Two-layer confidence:
  Layer 1 (LLM):         "I'm 90% confident this is the invoice number"
  Layer 2 (Validators):  "But it doesn't match the pattern \\d{4,}-\\d+, so we cap at 0.5"

The final confidence is the minimum of the two layers — conservative but safe.
"""
import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import structlog

from .schemas.base import ExtractionResult, FieldConfidence

log = structlog.get_logger()


@dataclass
class ValidationResult:
    field_name: str
    passed: bool
    adjusted_score: float
    reason: str


# --- Validators ---

def _validate_non_empty(value: Any, score: float) -> tuple[float, str]:
    """Required fields get penalised if empty."""
    if value is None or value == "" or value == []:
        return 0.1, "field is empty"
    return score, ""


def _validate_iban(value: str, score: float) -> tuple[float, str]:
    if not value:
        return score, ""
    cleaned = value.replace(" ", "").upper()
    if not re.match(r"^[A-Z]{2}[0-9]{2}[A-Z0-9]{11,30}$", cleaned):
        return min(score, 0.3), f"does not look like a valid IBAN: {value!r}"
    return score, ""


def _validate_currency(value: str, score: float) -> tuple[float, str]:
    if not value:
        return score, ""
    if not re.match(r"^[A-Z]{3}$", value):
        return min(score, 0.5), f"not a valid ISO 4217 currency code: {value!r}"
    return score, ""


def _validate_positive_amount(value: Any, score: float) -> tuple[float, str]:
    if value is None:
        return score, ""
    try:
        if Decimal(str(value)) < 0:
            return min(score, 0.4), f"amount is negative: {value}"
    except Exception:
        return min(score, 0.3), f"cannot parse as decimal: {value!r}"
    return score, ""


# Map field names to their validators
_FIELD_VALIDATORS: dict[str, list] = {
    "iban": [_validate_iban],
    "currency": [_validate_currency],
    "total_amount": [_validate_positive_amount],
    "subtotal": [_validate_positive_amount],
    "tax_amount": [_validate_positive_amount],
}


def apply_validators(result: ExtractionResult) -> ExtractionResult:
    """
    Run deterministic validators over extracted fields.
    Updates field_confidence scores in-place and returns the result.
    """
    confidence_map = {fc.field_name: fc for fc in result.field_confidence}
    data = result.model_dump(exclude={"field_confidence", "extraction_notes"})

    for field_name, value in data.items():
        validators = _FIELD_VALIDATORS.get(field_name, [])
        current = confidence_map.get(field_name)
        current_score = current.score if current else 1.0

        for validator in validators:
            adjusted_score, reason = validator(value, current_score)
            if adjusted_score < current_score:
                log.debug(
                    "confidence.adjusted",
                    field=field_name,
                    old=current_score,
                    new=adjusted_score,
                    reason=reason,
                )
                current_score = adjusted_score
                if current:
                    current.score = adjusted_score
                    current.reason = (current.reason + f"; {reason}").lstrip("; ")
                else:
                    confidence_map[field_name] = FieldConfidence(
                        field_name=field_name,
                        score=adjusted_score,
                        reason=reason,
                    )

    result.field_confidence = list(confidence_map.values())
    return result


def score_summary(result: ExtractionResult) -> dict:
    """Return a human-readable confidence summary for logging/display."""
    return {
        "overall": round(result.overall_confidence(), 3),
        "low_confidence_fields": result.low_confidence_fields(threshold=0.7),
        "field_scores": {
            fc.field_name: round(fc.score, 2)
            for fc in sorted(result.field_confidence, key=lambda x: x.score)
        },
    }
