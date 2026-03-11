"""
LLM extraction engine — the core of the pipeline.

Uses Claude's tool_use (structured outputs) to extract data into a Pydantic schema.

Why tool_use instead of "return JSON in your reply"?
  - tool_use forces the model to produce JSON that matches the tool's parameter schema
  - No JSON parsing errors, no markdown code fences to strip, no hallucinated fields
  - Validation happens in Pydantic, not in a fragile prompt instruction
"""
import json
from typing import Type

import anthropic
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from ..parsers.base import ParsedDocument
from .schemas.base import ExtractionResult
from .schemas.registry import get_schema, load_yaml_schema_hints

log = structlog.get_logger()

_DEFAULT_MODEL = "claude-sonnet-4-6"

_SYSTEM_PROMPT = """\
You are a document intelligence system that extracts structured data from business documents.

Rules:
- Extract only information that is explicitly present in the document text
- Do NOT infer, guess, or fabricate values — leave fields empty/null if not found
- For each field, provide a confidence score (0.0–1.0):
  - 1.0: exact match found in document
  - 0.8–0.9: high confidence, minor ambiguity
  - 0.5–0.7: moderate confidence, some interpretation required
  - 0.0–0.4: low confidence, value may be wrong
- Use extraction_notes to flag anything unusual or ambiguous
"""


class Extractor:
    def __init__(self, model: str = _DEFAULT_MODEL, api_key: str | None = None):
        self.model = model
        self.client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def extract(
        self,
        document: ParsedDocument,
        document_type: str,
    ) -> ExtractionResult:
        """
        Extract structured data from a parsed document.

        Args:
            document: ParsedDocument from any parser
            document_type: e.g. "invoice", "logistics"

        Returns:
            Populated ExtractionResult subclass instance
        """
        schema_cls = get_schema(document_type)
        hints = load_yaml_schema_hints(document_type)

        tool_schema = _build_tool_schema(schema_cls, hints)
        user_message = _build_user_message(document, document_type, hints)

        log.info(
            "extractor.call",
            document_type=document_type,
            model=self.model,
            text_chars=len(document.full_text),
        )

        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=_SYSTEM_PROMPT,
            tools=[tool_schema],
            tool_choice={"type": "tool", "name": "extract_document"},
            messages=[{"role": "user", "content": user_message}],
        )

        # With tool_choice forced, the first content block is always a tool_use block
        tool_use_block = next(b for b in response.content if b.type == "tool_use")
        raw = tool_use_block.input

        log.info(
            "extractor.done",
            document_type=document_type,
            stop_reason=response.stop_reason,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )

        return schema_cls.model_validate(raw)


def _build_tool_schema(schema_cls: Type[ExtractionResult], hints: dict) -> dict:
    """
    Build a Claude tool definition from a Pydantic schema.
    The JSON schema becomes the tool's parameter spec — Claude must populate it.
    """
    json_schema = schema_cls.model_json_schema()

    # Inject field descriptions from YAML hints if available
    field_hints = hints.get("fields", {})
    properties = json_schema.get("properties", {})
    for field_name, description in field_hints.items():
        if field_name in properties:
            properties[field_name]["description"] = description

    return {
        "name": "extract_document",
        "description": (
            f"Extract structured data from a {schema_cls.__name__} document. "
            "Include confidence scores for every extracted field."
        ),
        "input_schema": json_schema,
    }


def _build_user_message(document: ParsedDocument, document_type: str, hints: dict) -> str:
    context = hints.get("context", "")
    doc_description = f"Document type: {document_type}"
    if context:
        doc_description += f"\nContext: {context}"

    return (
        f"{doc_description}\n\n"
        f"--- DOCUMENT TEXT ---\n"
        f"{document.full_text[:12000]}\n"  # Claude's context is large but we truncate for cost
        f"--- END DOCUMENT ---\n\n"
        "Extract all available fields. Leave fields empty if the information is not present."
    )
