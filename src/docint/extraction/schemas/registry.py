"""
Schema registry — maps document type names to their Pydantic model classes.

New document types are registered here. The pipeline uses the registry to look up
which schema to use for a given document type string.
"""
from pathlib import Path
from typing import Type

import yaml

from .base import ExtractionResult
from .invoice import InvoiceResult
from .logistics import LogisticsResult

_REGISTRY: dict[str, Type[ExtractionResult]] = {
    "invoice": InvoiceResult,
    "logistics": LogisticsResult,
}


def get_schema(document_type: str) -> Type[ExtractionResult]:
    """Return the Pydantic model class for a document type."""
    schema = _REGISTRY.get(document_type)
    if schema is None:
        raise ValueError(
            f"Unknown document type: {document_type!r}. "
            f"Available types: {list(_REGISTRY.keys())}"
        )
    return schema


def available_types() -> list[str]:
    return list(_REGISTRY.keys())


def load_yaml_schema_hints(document_type: str) -> dict:
    """
    Load the YAML schema file for a document type.
    These files contain human-readable field descriptions used in prompts.
    """
    yaml_path = Path(__file__).parents[4] / "schemas" / f"{document_type}.yaml"
    if not yaml_path.exists():
        return {}
    with open(yaml_path) as f:
        return yaml.safe_load(f) or {}
