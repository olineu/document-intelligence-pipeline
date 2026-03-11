"""
Invoice extraction schema.

Covers the fields you'll find on 95% of B2B invoices across industries.
Line items are modelled as a nested list — each item has its own fields.
"""
from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import Field

from .base import ExtractionResult


class LineItem(ExtractionResult):
    description: str = ""
    quantity: Optional[Decimal] = None
    unit_price: Optional[Decimal] = None
    total: Optional[Decimal] = None
    unit: str = ""  # "pcs", "hours", "kg", etc.
    product_code: str = ""


class InvoiceResult(ExtractionResult):
    # Identifiers
    invoice_number: str = ""
    purchase_order_number: str = ""

    # Dates
    invoice_date: Optional[date] = None
    due_date: Optional[date] = None

    # Parties
    vendor_name: str = ""
    vendor_address: str = ""
    vendor_tax_id: str = ""
    customer_name: str = ""
    customer_address: str = ""

    # Financial totals
    subtotal: Optional[Decimal] = None
    tax_amount: Optional[Decimal] = None
    tax_rate_percent: Optional[Decimal] = None
    discount_amount: Optional[Decimal] = None
    total_amount: Optional[Decimal] = None
    currency: str = "EUR"  # ISO 4217

    # Payment
    payment_terms: str = ""
    bank_account: str = ""
    iban: str = ""

    # Line items
    line_items: list[LineItem] = Field(default_factory=list)
