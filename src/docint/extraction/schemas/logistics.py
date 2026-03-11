"""
Logistics document schema — covers Bills of Lading, shipping manifests, delivery notes.

These documents are common in manufacturing, retail, and 3PL contexts.
"""
from datetime import date, datetime
from typing import Optional

from pydantic import Field

from .base import ExtractionResult


class CargoItem(ExtractionResult):
    description: str = ""
    quantity: Optional[float] = None
    weight_kg: Optional[float] = None
    volume_m3: Optional[float] = None
    hs_code: str = ""       # Harmonized System customs code
    package_type: str = ""  # "pallet", "carton", "drum", etc.
    marks_numbers: str = "" # Shipping marks


class LogisticsResult(ExtractionResult):
    # Document type
    document_type: str = ""  # "bill_of_lading", "delivery_note", "manifest"
    document_number: str = ""

    # Dates
    shipment_date: Optional[date] = None
    estimated_arrival: Optional[date] = None
    actual_arrival: Optional[date] = None

    # Parties
    shipper_name: str = ""
    shipper_address: str = ""
    consignee_name: str = ""
    consignee_address: str = ""
    notify_party: str = ""
    carrier_name: str = ""

    # Route
    port_of_loading: str = ""
    port_of_discharge: str = ""
    place_of_delivery: str = ""
    vessel_name: str = ""
    voyage_number: str = ""
    container_number: str = ""

    # Cargo totals
    total_packages: Optional[int] = None
    total_weight_kg: Optional[float] = None
    total_volume_m3: Optional[float] = None
    freight_terms: str = ""  # "prepaid", "collect"

    # Cargo items
    cargo_items: list[CargoItem] = Field(default_factory=list)

    # Reference numbers
    booking_number: str = ""
    customs_declaration_number: str = ""
