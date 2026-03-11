"""
Human review queue — surfaces low-confidence extractions for manual correction.

The review queue is not a failure mode; it's the quality gate that makes the pipeline
trustworthy. Any system that skips this becomes unreliable as soon as edge cases appear.

Priority scoring logic:
  - Low confidence + high document value = review first
  - We use a simple priority score = (1 - confidence) for now
  - In production you'd incorporate document value (invoice amount, shipment weight, etc.)
"""
from dataclasses import dataclass
from typing import Any


@dataclass
class ReviewTask:
    """A single document awaiting human review."""
    review_item_id: str
    document_id: str
    document_type: str
    file_name: str
    priority_score: float
    trigger_reason: str
    extracted_data: dict[str, Any]
    low_confidence_fields: list[str]


def render_review_task(task: ReviewTask) -> str:
    """
    Format a review task for CLI display.
    Used in Lesson 05 to build the interactive reviewer.
    """
    lines = [
        f"{'='*60}",
        f"Document:  {task.file_name}",
        f"Type:      {task.document_type}",
        f"Priority:  {task.priority_score:.2f}",
        f"Reason:    {task.trigger_reason}",
        f"{'='*60}",
        "",
        "Extracted fields:",
    ]

    for key, value in task.extracted_data.items():
        if key in ("field_confidence", "extraction_notes"):
            continue
        if value is None or value == "" or value == []:
            continue
        flag = " ← LOW CONFIDENCE" if key in task.low_confidence_fields else ""
        lines.append(f"  {key:30s}  {str(value)[:60]}{flag}")

    if task.extracted_data.get("extraction_notes"):
        lines.append(f"\nExtraction notes: {task.extracted_data['extraction_notes']}")

    return "\n".join(lines)


def compute_corrections(original: dict, corrected: dict) -> dict:
    """
    Return only the fields that changed between original and corrected.
    Stored in review_items.corrections_json for the feedback loop.
    """
    corrections = {}
    for key in corrected:
        if key in ("field_confidence", "extraction_notes"):
            continue
        if corrected[key] != original.get(key):
            corrections[key] = {"old": original.get(key), "new": corrected[key]}
    return corrections
