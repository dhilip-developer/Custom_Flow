"""
Routes for Agent 5: Document Cross-Verifier
"""
from fastapi import APIRouter, Form, HTTPException
from typing import Optional
from models.schemas import CrossVerificationResponse
import services.cross_verifier as cross_verifier

router = APIRouter()


@router.post(
    "/cross-verify",
    response_model=CrossVerificationResponse,
    tags=["Agent 5: Document Cross-Verifier"]
)
async def cross_verify_documents(
    bill_of_lading: Optional[str] = Form(
        None,
        description="""
        Paste the JSON extracted_data from Agent 2 for the **Bill of Lading (BOL)**.
        Example: {"BILL NO.": "BL-2024-001", "GROSS WEIGHT": "1500 KGS", "CONTAINER NUMBER": "MSCU1234567", ...}
        Leave blank if you do not have this document.
        """
    ),
    invoice: Optional[str] = Form(
        None,
        description="""
        Paste the JSON extracted_data from Agent 2 for the **Invoice**.
        Example: {"INVOICE NUMBER AND DATE": "INV-001 / 2024-01-15", "HS CODE": "84713000", "TOTAL VALUE": "USD 25000", ...}
        Leave blank if you do not have this document.
        """
    ),
    packing_list: Optional[str] = Form(
        None,
        description="""
        Paste the JSON extracted_data from Agent 2 for the **Packing List**.
        Example: {"GROSS WEIGHT": "1500 KGS", "QUANTITY": "10 UNITS", "MATERIAL DESCRIPTION": "Laptop Computers", ...}
        Leave blank if you do not have this document.
        """
    ),
    freight_certificate: Optional[str] = Form(
        None,
        description="""
        Paste the JSON extracted_data from Agent 2 for the **Freight Certificate** (optional).
        Example: {"HBL NO.": "HBL-456", "CONTAINER NO.": "MSCU1234567", "WEIGHT": "1500 KGS", ...}
        Leave blank if this document is not part of this shipment.
        """
    ),
    insurance_certificate: Optional[str] = Form(
        None,
        description="""
        Paste the JSON extracted_data from Agent 2 for the **Insurance Certificate** (optional).
        Example: {"INVOICE NUMBER": "INV-001", "INVOICE TOTAL VALUE": "USD 25000", "INSURANCE VALUE": "USD 27500", ...}
        Leave blank if this document is not part of this shipment.
        """
    )
):
    """
    Agent 5: Submit the extracted JSON data from **Agent 2** for up to **5 customs documents** — each in its own separate text box.
    The agent performs intelligent **field-level cross-verification** using AI to confirm whether all documents belong to the same shipment.

    **How to use:**
    1. Run each document through Agent 1 → 2 → 3 as usual.
    2. Copy the contents of `extracted_data` from Agent 2's response (just the inner `{...}` dict).
    3. Paste it into the relevant box below. Leave unused boxes empty.
    4. **Minimum 2 documents** must be submitted.

    **What gets compared:**
    - HS Code: BOL ↔ Invoice
    - Gross Weight: BOL ↔ Packing List ↔ Freight Certificate
    - Container Number: BOL ↔ Freight Certificate
    - Bill No / HBL No: BOL ↔ Freight Certificate
    - Material Description & Quantity: Invoice ↔ Packing List
    - Part Number: Invoice ↔ Packing List ↔ Insurance Certificate
    - Invoice Number & Total Value: Invoice ↔ Insurance Certificate
    - Package Count: BOL ↔ Packing List ↔ Freight Certificate
    - Consignee/Party Names: BOL ↔ Invoice

    **Returns:**
    - `overall_verdict`: COHERENT | DISCREPANCIES FOUND | INSUFFICIENT DATA
    - `coherence_score`: % of verifiable fields that matched
    - `comparison_table`: full side-by-side table of all fields across all documents
    - `matched_fields`: list of consistent field pairs
    - `mismatched_fields`: discrepancies with explanation notes
    - `skipped_comparisons`: comparisons skipped due to missing docs or empty fields
    """
    # Count non-empty submissions
    docs_raw = [bill_of_lading, invoice, packing_list, freight_certificate, insurance_certificate]
    docs_filled = [d for d in docs_raw if d and d.strip()]

    if len(docs_filled) < 2:
        raise HTTPException(
            status_code=400,
            detail="At least 2 document JSON payloads must be provided. Please fill in 2 or more boxes."
        )

    # Parse JSON strings (service handles it)
    try:
        result = cross_verifier.cross_verify_documents(
            bill_of_lading=bill_of_lading,
            invoice=invoice,
            packing_list=packing_list,
            freight_certificate=freight_certificate,
            insurance_certificate=insurance_certificate,
        )
    except ValueError as ve:
        raise HTTPException(status_code=422, detail=str(ve))

    return CrossVerificationResponse(**result)
