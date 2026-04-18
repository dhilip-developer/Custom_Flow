"""
Pydantic models for the Insurance Requirement Detection Agent.

Defines schemas for Invoice, Packing List, Bill of Lading,
the combined ShippingDocuments wrapper, and the refined AgentResult output.
"""

from __future__ import annotations
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ── Internal Document Models (Input) ────────────────────────────────

class LineItem(BaseModel):
    description: str = ""
    quantity: float = 0
    unit_price: float = 0
    total: float = 0


class Invoice(BaseModel):
    invoice_number: str = ""
    seller: str = ""
    buyer: str = ""
    date: str = ""
    incoterm: str = ""
    total_value: float = 0.0
    currency: str = "USD"
    insurance_charges: Optional[float] = None
    insurance_reference: Optional[str] = None
    line_items: List[LineItem] = Field(default_factory=list)


class PackingList(BaseModel):
    packing_list_number: str = ""
    total_gross_weight: float = 0.0
    total_net_weight: float = 0.0
    weight_unit: str = "KG"
    declared_value: Optional[float] = None
    currency: str = "USD"


class BillOfLading(BaseModel):
    bol_number: str = ""
    shipper: str = ""
    consignee: str = ""
    notify_party: str = ""
    port_of_loading: str = ""
    port_of_discharge: str = ""
    vessel_name: str = ""
    shipment_terms: str = ""
    incoterm: str = ""
    insurance_reference: Optional[str] = None


class ShippingDocuments(BaseModel):
    invoice: Invoice = Field(default_factory=Invoice)
    packing_list: PackingList = Field(default_factory=PackingList)
    bill_of_lading: BillOfLading = Field(default_factory=BillOfLading)


class ValidationInfo(BaseModel):
    quantity_match: str = ""
    name_match: str = ""
    reference_match: str = ""


class InsuranceInfo(BaseModel):
    present: str = ""
    provider: Optional[str] = None
    coverage: Optional[str] = None
    compliance_missing: str = ""


class ExpertInvoice(BaseModel):
    invoice_number: str = ""
    invoice_date: str = ""
    seller_name: str = ""
    buyer_name: str = ""
    total_amount: Optional[float] = None
    currency: str = ""


class ExpertPackingList(BaseModel):
    total_quantity: Optional[float] = None
    unit_of_measure: str = ""


class ExpertBillOfLading(BaseModel):
    shipment_number: str = ""
    carrier: str = ""
    port_of_loading: str = ""
    port_of_discharge: str = ""
    consignee: str = ""


# ── Agent 2: Bill of Lading Extractor Output ────────────────────

class ExpandedBillOfLading(BaseModel):
    """
    Dedicated 13-point extraction schema for Agent 2.
    """
    bill_no: str = Field(alias="BILL NO.", default="")
    bill_date: str = Field(alias="BILL DATE", default="")
    consignee_receiver: str = Field(alias="CONSIGNEE/ RECIEVER", default="")
    importer_supplier: str = Field(alias="IMPORTER /SUPPLIER", default="")
    port_of_loading: str = Field(alias="PORT OF LOADING", default="")
    port_of_discharge: str = Field(alias="PORT OF DISCHARGE", default="")
    type_of_movement: str = Field(alias="TYPE OF MOVEMENT", default="")
    container_number: str = Field(alias="CONTAINER NUMBER", default="")
    package: str = Field(alias="PACKAGE", default="")
    measurements: str = Field(alias="MEASUREMENTS", default="")
    gross_weight: str = Field(alias="GROSS WEIGHT", default="")
    freight_collect: str = Field(alias="FREIGHT COLLECT", default="")
    description_of_goods: str = Field(alias="DESCRIPTION OF GOODS", default="")
    hs_code: str = Field(alias="HS CODE", default="")

    class Config:
        populate_by_name = True


# ── Refined Output (Agent 1) ────────────────────────────────────

class AgentResult(BaseModel):
    """
    Refined result schema providing exactly three fields:
    - Insurance Certificate Required: (Yes/No as string or bool)
    - Reason: Specific logic-based explanation
    - Confidence: Level percentage
    """
    insurance_required: str = Field(alias="Insurance Certificate Required", description="Whether an Insurance Certificate is required (Yes/No)")
    reason: str = Field(alias="Reason", description="Logic-based reasoning for the requirement status")
    confidence: str = Field(alias="Confidence", description="Confidence level (e.g. 91%)")

    class Config:
        populate_by_name = True


class BatchResultItem(BaseModel):
    filename: str
    result: Optional[AgentResult] = None
    error: Optional[str] = None


class BatchResponse(BaseModel):
    results: List[BatchResultItem]
