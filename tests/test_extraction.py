"""
Extraction tests — no LLM calls.
Tests schema design, confidence scoring, and validators in isolation.
"""
import sys
from pathlib import Path
from decimal import Decimal

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from docint.extraction.schemas.base import ExtractionResult, FieldConfidence
from docint.extraction.schemas.invoice import InvoiceResult, LineItem
from docint.extraction.schemas.registry import get_schema, available_types
from docint.extraction.confidence import (
    apply_validators,
    score_summary,
    _validate_iban,
    _validate_currency,
    _validate_positive_amount,
)


# ── ExtractionResult base ─────────────────────────────────────────────────────

class TestExtractionResult:
    def test_overall_confidence_empty(self):
        result = InvoiceResult()
        assert result.overall_confidence() == 0.0

    def test_overall_confidence_average(self):
        result = InvoiceResult(
            field_confidence=[
                FieldConfidence(field_name="a", score=0.8),
                FieldConfidence(field_name="b", score=0.6),
            ]
        )
        assert result.overall_confidence() == pytest.approx(0.7)

    def test_low_confidence_fields(self):
        result = InvoiceResult(
            field_confidence=[
                FieldConfidence(field_name="invoice_number", score=0.9),
                FieldConfidence(field_name="total_amount", score=0.4),
                FieldConfidence(field_name="iban", score=0.3),
            ]
        )
        low = result.low_confidence_fields(threshold=0.7)
        assert "total_amount" in low
        assert "iban" in low
        assert "invoice_number" not in low

    def test_low_confidence_fields_custom_threshold(self):
        result = InvoiceResult(
            field_confidence=[FieldConfidence(field_name="x", score=0.5)]
        )
        assert result.low_confidence_fields(threshold=0.4) == []
        assert result.low_confidence_fields(threshold=0.6) == ["x"]


# ── Schema registry ───────────────────────────────────────────────────────────

class TestSchemaRegistry:
    def test_get_invoice_schema(self):
        schema = get_schema("invoice")
        assert schema is InvoiceResult

    def test_get_logistics_schema(self):
        from docint.extraction.schemas.logistics import LogisticsResult
        schema = get_schema("logistics")
        assert schema is LogisticsResult

    def test_unknown_type_raises(self):
        with pytest.raises(ValueError, match="Unknown document type"):
            get_schema("foobar")

    def test_available_types(self):
        types = available_types()
        assert "invoice" in types
        assert "logistics" in types


# ── InvoiceResult schema ──────────────────────────────────────────────────────

class TestInvoiceResult:
    def test_default_currency(self):
        result = InvoiceResult()
        assert result.currency == "EUR"

    def test_line_items_default_empty(self):
        result = InvoiceResult()
        assert result.line_items == []

    def test_line_items_nested(self):
        result = InvoiceResult(
            line_items=[
                LineItem(description="Software License", quantity=Decimal("1"), unit_price=Decimal("8500")),
            ]
        )
        assert len(result.line_items) == 1
        assert result.line_items[0].description == "Software License"

    def test_model_dump_json_mode(self):
        from datetime import date
        result = InvoiceResult(
            invoice_number="INV-001",
            invoice_date=date(2024, 11, 15),
            total_amount=Decimal("1000.00"),
        )
        data = result.model_dump(mode="json")
        assert data["invoice_number"] == "INV-001"
        assert data["invoice_date"] == "2024-11-15"
        assert data["total_amount"] == "1000.00"


# ── Validators ────────────────────────────────────────────────────────────────

class TestValidateIBAN:
    def test_valid_german_iban(self):
        score, reason = _validate_iban("DE89 3704 0044 0532 0130 00", 0.9)
        assert score == 0.9
        assert reason == ""

    def test_valid_iban_no_spaces(self):
        score, reason = _validate_iban("DE89370400440532013000", 0.9)
        assert score == 0.9

    def test_invalid_iban_format(self):
        score, reason = _validate_iban("XX99 9999 INVALID", 0.9)
        assert score < 0.9
        assert reason != ""

    def test_empty_iban_unchanged(self):
        score, reason = _validate_iban("", 0.9)
        assert score == 0.9


class TestValidateCurrency:
    def test_valid_eur(self):
        score, _ = _validate_currency("EUR", 0.9)
        assert score == 0.9

    def test_valid_usd(self):
        score, _ = _validate_currency("USD", 0.9)
        assert score == 0.9

    def test_invalid_written_out(self):
        score, reason = _validate_currency("Euro", 0.9)
        assert score < 0.9
        assert reason != ""

    def test_invalid_symbol(self):
        score, reason = _validate_currency("€", 0.9)
        assert score < 0.9

    def test_empty_unchanged(self):
        score, _ = _validate_currency("", 0.9)
        assert score == 0.9


class TestValidatePositiveAmount:
    def test_positive_unchanged(self):
        score, _ = _validate_positive_amount(Decimal("1000.00"), 0.9)
        assert score == 0.9

    def test_negative_adjusted(self):
        score, reason = _validate_positive_amount(Decimal("-100"), 0.9)
        assert score < 0.9
        assert "negative" in reason

    def test_none_unchanged(self):
        score, _ = _validate_positive_amount(None, 0.9)
        assert score == 0.9

    def test_zero_allowed(self):
        score, _ = _validate_positive_amount(Decimal("0"), 0.9)
        assert score == 0.9


# ── apply_validators integration ─────────────────────────────────────────────

class TestApplyValidators:
    def test_valid_invoice_unchanged(self):
        result = InvoiceResult(
            currency="EUR",
            total_amount=Decimal("1000"),
            iban="DE89370400440532013000",
            field_confidence=[
                FieldConfidence(field_name="currency", score=1.0),
                FieldConfidence(field_name="total_amount", score=1.0),
                FieldConfidence(field_name="iban", score=1.0),
            ],
        )
        validated = apply_validators(result)
        scores = {fc.field_name: fc.score for fc in validated.field_confidence}
        assert scores["currency"] == 1.0
        assert scores["total_amount"] == 1.0
        assert scores["iban"] == 1.0

    def test_invalid_iban_lowers_score(self):
        result = InvoiceResult(
            iban="NOT_AN_IBAN",
            field_confidence=[FieldConfidence(field_name="iban", score=0.9)],
        )
        validated = apply_validators(result)
        scores = {fc.field_name: fc.score for fc in validated.field_confidence}
        assert scores["iban"] < 0.9

    def test_invalid_currency_lowers_score(self):
        result = InvoiceResult(
            currency="dollars",
            field_confidence=[FieldConfidence(field_name="currency", score=0.8)],
        )
        validated = apply_validators(result)
        scores = {fc.field_name: fc.score for fc in validated.field_confidence}
        assert scores["currency"] < 0.8


# ── score_summary ─────────────────────────────────────────────────────────────

class TestScoreSummary:
    def test_summary_structure(self):
        result = InvoiceResult(
            field_confidence=[
                FieldConfidence(field_name="invoice_number", score=0.95),
                FieldConfidence(field_name="iban", score=0.3),
            ]
        )
        summary = score_summary(result)
        assert "overall" in summary
        assert "low_confidence_fields" in summary
        assert "field_scores" in summary
        assert "iban" in summary["low_confidence_fields"]
        assert "invoice_number" not in summary["low_confidence_fields"]
