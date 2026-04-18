"""
Routes for Agent 4: Freight Certificate Detector
"""
from fastapi import APIRouter, Body, HTTPException
from models.schemas import FreightCertificateCheckResponse
import services.intelligence_utils as processor

router = APIRouter()


@router.post(
    "/detect-freight-certificate",
    response_model=FreightCertificateCheckResponse,
    tags=["Agent 4: Freight Certificate Detector"]
)
async def detect_freight_certificate(payload: str = Body(..., media_type="text/plain")):
    """
    Agent 4: Submit raw plain text extracted from customs documents (Invoice, Packing List, BOL — combined or individual)
    to automatically determine whether a **Freight Certificate is Required or Not Required**.

    **Detection Logic:**
    - Scans for Incoterms: FOB, EXW/EXWORK, FCA → `freight_certificate_required: "needed"`
    - Scans for Incoterms: CNF/CFR, CIF → `freight_certificate_required: "not needed"` (if freight confirmed)
    - Checks if freight charges are present in the text
    - Checks if BOL marks freight as Prepaid or Collect
    - Detects mismatches or missing freight information
    """
    if not payload or len(payload.strip()) == 0:
        raise HTTPException(status_code=400, detail="No text provided. Please paste the raw document text in the request body.")

    return processor.detect_freight_certificate_requirement(payload)
