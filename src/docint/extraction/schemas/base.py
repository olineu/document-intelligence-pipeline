"""
Base extraction schema. Every document schema inherits from ExtractionResult.

Design decisions:
  - Each schema carries its own confidence scores — one per field
  - confidence is a dict[field_name, float] so confidence is structural, not bolted on
  - extraction_notes lets the LLM explain uncertain fields — useful for reviewers
"""
from pydantic import BaseModel, Field


class FieldConfidence(BaseModel):
    """Confidence score for a single extracted field (0.0 = no idea, 1.0 = certain)."""
    field_name: str
    score: float = Field(ge=0.0, le=1.0)
    reason: str = ""  # LLM's explanation of why it is or isn't confident


class ExtractionResult(BaseModel):
    """Base class for all extraction schemas."""

    # The LLM populates this alongside the extracted fields.
    # Each entry corresponds to one field in the schema.
    field_confidence: list[FieldConfidence] = Field(default_factory=list)
    extraction_notes: str = ""  # Free-text notes from the LLM about uncertain areas

    def overall_confidence(self) -> float:
        """
        Document-level confidence: average of all field confidence scores.
        Returns 0.0 if no confidence data is present.
        """
        if not self.field_confidence:
            return 0.0
        return sum(f.score for f in self.field_confidence) / len(self.field_confidence)

    def low_confidence_fields(self, threshold: float = 0.7) -> list[str]:
        """Return names of fields below the confidence threshold."""
        return [f.field_name for f in self.field_confidence if f.score < threshold]
